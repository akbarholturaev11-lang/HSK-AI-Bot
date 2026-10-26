"""Read-only legacy study evidence for the Smart Reminder migration.

This is an internal observation service, not an authentication adapter or send
permission. Callers must authorize the canonical account before exposing a
snapshot. No legacy writer/scheduler uses this service yet. It deliberately
cannot declare an account migrated or authorize any new notification.
"""

from dataclasses import dataclass, field

from sqlalchemy import or_, select

from app.db.models.account_deletion import AccountDeletionRequest
from app.db.models.android_push import AndroidPushToken
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.desktop import DesktopDevice
from app.db.models.user import User


EVIDENCE_VERSION = 1
MAX_DEVICE_OBSERVATIONS = 128
KNOWN_ACCOUNT_STATES = frozenset({"active", "trial", "free", "expired"})


class LegacyEvidenceUnavailable(ValueError):
    """Stable internal refusal code; contains no account/provider secrets."""


@dataclass(frozen=True)
class TelegramStudyEvidence:
    transport_present: bool
    transport_blocked: bool
    setting_enabled: bool | None
    saved_time_local: str | None
    saved_offset_minutes: int | None
    study_state: str
    # Neither progress.updated_at nor a saved time proves an intentional lock
    # or a timestamped OFF. The legacy default False is not an OFF action log.
    manual_lock_proven: bool = field(default=False, init=False)
    action_timestamp: None = field(default=None, init=False)


@dataclass(frozen=True)
class AndroidStudyEvidence:
    device_id: str
    revoked: bool
    push_registered: bool
    mirrored_setting_enabled: bool | None
    # These facts are absent from the legacy schema. Account-notice permission,
    # app version and recent activity cannot fill them in.
    study_consent: str = field(default="unknown", init=False)
    study_os_permission: str = field(default="unknown", init=False)
    server_claim_capability: str = field(default="unknown", init=False)
    action_timestamp: None = field(default=None, init=False)


@dataclass(frozen=True)
class LegacyStudyEvidence:
    user_id: int
    telegram: TelegramStudyEvidence
    android: tuple[AndroidStudyEvidence, ...]
    motivation_enabled: bool | None
    cutover_blockers: tuple[str, ...]
    evidence_version: int = field(default=EVIDENCE_VERSION, init=False)
    dispatch_allowed: bool = field(default=False, init=False)


class SmartReminderLegacyEvidenceService:
    """Project only existing facts, with canonical ownership and zero writes.

    A fresh observation is required for each review. It is not cached, stored
    as consent, or used as a transactional eligibility decision. In particular
    this cannot fence an old installation that disappeared from the database.
    """

    def __init__(self, session):
        self.session = session

    async def snapshot(self, user_id: int) -> LegacyStudyEvidence:
        if type(user_id) is not int or user_id <= 0:
            raise LegacyEvidenceUnavailable("canonical_user_id_required")

        # Column projections avoid stale ORM identity-map state and never load
        # FCM tokens, Telegram IDs, names or installation hashes into a report.
        # An observational read must not flush a caller's pending ORM writes.
        with self.session.no_autoflush:
            account = (await self.session.execute(select(
                User.status,
                (User.telegram_id > 0).label("has_telegram"),
                User.bot_blocked_at.is_not(None).label("bot_blocked"),
            ).where(User.id == user_id))).mappings().one_or_none()
            if account is None:
                raise LegacyEvidenceUnavailable("account_not_found")
            if account["status"] == "blocked":
                raise LegacyEvidenceUnavailable("account_blocked")
            if account["status"] not in KNOWN_ACCOUNT_STATES:
                raise LegacyEvidenceUnavailable("account_state_unknown")

            deletion = await self.session.scalar(select(AccountDeletionRequest.id).where(
                AccountDeletionRequest.status == "submitted",
                or_(AccountDeletionRequest.active_user_id == user_id,
                    AccountDeletionRequest.user_id == user_id),
            ).limit(1))
            if deletion is not None:
                raise LegacyEvidenceUnavailable("account_deletion_pending")

            progress = (await self.session.execute(select(
                CourseProgress.reminder_enabled,
                CourseProgress.reminder_time,
                CourseProgress.reminder_tz_offset,
            ).where(CourseProgress.user_id == user_id))).mappings().one_or_none()
            motivation = await self.session.scalar(select(
                CourseMiniAppProfile.notifications_enabled,
            ).where(CourseMiniAppProfile.user_id == user_id))

            # Include revoked, old and tokenless Android installs. No version,
            # last-seen, ON/OFF or token filter can prove an old offline sender
            # stopped. Desktop devices are not Android study endpoints in V1.
            devices = (await self.session.execute(select(
                DesktopDevice.id,
                DesktopDevice.revoked_at.is_not(None).label("revoked"),
                AndroidPushToken.device_id.is_not(None).label("push_registered"),
                AndroidPushToken.study_reminders_enabled,
            ).outerjoin(
                AndroidPushToken, AndroidPushToken.device_id == DesktopDevice.id,
            ).where(
                DesktopDevice.user_id == user_id,
                DesktopDevice.platform == "android",
            ).order_by(DesktopDevice.id).limit(MAX_DEVICE_OBSERVATIONS + 1))).mappings().all()
            if len(devices) > MAX_DEVICE_OBSERVATIONS:
                # Truncation could hide a competing old sender.
                raise LegacyEvidenceUnavailable("device_inventory_over_limit")

        enabled = progress["reminder_enabled"] if progress else None
        saved_time = progress["reminder_time"] if progress else None
        offset = progress["reminder_tz_offset"] if progress else None
        has_telegram = bool(account["has_telegram"])
        state = "unknown"
        if enabled is False:
            state = "not_enabled"
        elif enabled is True and saved_time is not None and has_telegram:
            state = "legacy_on"
        blockers = ["smart_dispatch_not_implemented", "legacy_fleet_fencing_unverified"]
        if devices:
            blockers.append("legacy_android_sender_possible")
        return LegacyStudyEvidence(
            user_id=user_id,
            telegram=TelegramStudyEvidence(
                transport_present=has_telegram,
                transport_blocked=bool(account["bot_blocked"]),
                setting_enabled=enabled,
                saved_time_local=saved_time.isoformat() if saved_time is not None else None,
                saved_offset_minutes=offset * 60 if type(offset) is int and -12 <= offset <= 14 else None,
                study_state=state,
            ),
            android=tuple(AndroidStudyEvidence(
                device_id=row["id"], revoked=row["revoked"],
                push_registered=row["push_registered"],
                mirrored_setting_enabled=row["study_reminders_enabled"],
            ) for row in devices),
            motivation_enabled=motivation,
            cutover_blockers=tuple(blockers),
        )

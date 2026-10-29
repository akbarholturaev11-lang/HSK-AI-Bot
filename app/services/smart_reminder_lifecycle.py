"""Study-only OFF/lifecycle invalidation; no enrollment, provider or commit.

All mutations lock user first. Legacy vetoes are suppression at the existing
sender boundary, not a shared reservation or proof that an offline APK stopped.
"""
from datetime import datetime, timezone

from sqlalchemy import delete, or_, select, update

from app.db.models.account_deletion import AccountDeletionRequest
from app.db.models.android_push import AndroidPushToken
from app.db.models.course_progress import CourseProgress
from app.db.models.desktop import DesktopDevice
from app.db.models.smart_reminder import (
    SmartReminderAttempt, SmartReminderCapability, SmartReminderConsent,
    SmartReminderJob, SmartReminderPreference, SmartReminderRouting,
)
from app.db.models.user import User
from app.services.smart_reminder_legacy_evidence import KNOWN_ACCOUNT_STATES

PREF = SmartReminderPreference.__table__
JOB = SmartReminderJob.__table__
ATTEMPT = SmartReminderAttempt.__table__
ACTIVE_JOBS = ("shadow", "pending", "claimed")
EXTERNAL_ATTEMPTS = ("in_flight", "provider_accepted", "client_posted_unverified", "verified_shown", "unknown")


class SmartReminderLifecycleService:
    def __init__(self, session):
        self.session = session

    async def lock_user(self, user_id):
        with self.session.no_autoflush:
            return await self.session.scalar(select(User.id).where(User.id == user_id).with_for_update())

    async def invalidate(self, user_id, *, reason, advance=True, device_id=None, clear_capabilities=False):
        with self.session.no_autoflush:
            if await self.lock_user(user_id) is None:
                return
            pref = (await self.session.execute(select(PREF).where(
                PREF.c.user_id == user_id).with_for_update())).mappings().one_or_none()
            if advance and pref is not None:
                await self.session.execute(update(PREF).where(PREF.c.user_id == user_id).values(
                    revision=PREF.c.revision + 1, grant_epoch=PREF.c.grant_epoch + 1,
                    updated_at=datetime.now(timezone.utc)))
            # A prepared alternate is revoked even if an earlier attempt is
            # already externalized. Never relabel accepted/in-flight/unknown IO.
            owned_jobs = select(JOB.c.id).where(JOB.c.user_id == user_id)
            await self.session.execute(update(ATTEMPT).where(
                ATTEMPT.c.job_id.in_(owned_jobs), ATTEMPT.c.state == "prepared",
            ).values(state="cancelled", reason_code=reason))
            await self.session.execute(update(JOB).where(
                JOB.c.user_id == user_id, JOB.c.state.in_(ACTIVE_JOBS),
            ).values(lease_token=None, lease_expires_at=None))
            external = select(ATTEMPT.c.id).where(
                ATTEMPT.c.job_id == JOB.c.id, ATTEMPT.c.state.in_(EXTERNAL_ATTEMPTS),
            ).exists()
            await self.session.execute(update(JOB).where(
                JOB.c.user_id == user_id, JOB.c.state.in_(ACTIVE_JOBS), ~external,
            ).values(state="cancelled", reason_code=reason, updated_at=datetime.now(timezone.utc)))
            if device_id is not None or clear_capabilities:
                capability = delete(SmartReminderCapability).where(SmartReminderCapability.user_id == user_id)
                if not clear_capabilities:
                    capability = capability.where(SmartReminderCapability.device_id == device_id)
                await self.session.execute(capability)

    async def disable_legacy(self, user_id, *, channel=None, device_id=None):
        with self.session.no_autoflush:
            await self.lock_user(user_id)
            if channel in (None, "telegram"):
                await self.session.execute(update(CourseProgress.__table__).where(
                    CourseProgress.user_id == user_id).values(reminder_enabled=False))
            if channel in (None, "android"):
                devices = select(DesktopDevice.id).where(DesktopDevice.user_id == user_id)
                if device_id is not None:
                    devices = devices.where(DesktopDevice.id == device_id)
                await self.session.execute(update(AndroidPushToken.__table__).where(
                    AndroidPushToken.device_id.in_(devices)).values(study_reminders_enabled=False))

    async def legacy_veto(self, user_id, channel, *, device_id=None, lock=False):
        """Fresh configuration OFF veto; allowing legacy grants no dispatch."""
        with self.session.no_autoflush:
            if lock:
                await self.lock_user(user_id)
            account = (await self.session.execute(select(
                User.status, (User.telegram_id > 0).label("transport"),
                User.bot_blocked_at.is_not(None).label("bot_blocked"),
            ).where(User.id == user_id))).mappings().one_or_none()
            if account is None or account["status"] not in KNOWN_ACCOUNT_STATES:
                return True
            if channel == "telegram" and (not account["transport"] or account["bot_blocked"]):
                return True
            if channel == "android":
                device = await self.session.scalar(select(DesktopDevice.id).where(
                    DesktopDevice.id == device_id, DesktopDevice.user_id == user_id,
                    DesktopDevice.platform == "android", DesktopDevice.revoked_at.is_(None)))
                if device is None:
                    return True
                permission = await self.session.scalar(select(SmartReminderCapability.study_notifications_allowed).where(
                    SmartReminderCapability.user_id == user_id,
                    SmartReminderCapability.device_id == device_id))
                if permission is False:
                    return True
            pending = await self.session.scalar(select(AccountDeletionRequest.id).where(
                AccountDeletionRequest.status == "submitted",
                or_(AccountDeletionRequest.user_id == user_id, AccountDeletionRequest.active_user_id == user_id),
            ).limit(1))
            if pending is not None:
                return True
            master = await self.session.scalar(select(PREF.c.master_enabled).where(PREF.c.user_id == user_id))
            if master is False:
                return True
            source_key = "intent:telegram" if channel == "telegram" else "intent:android:" + str(device_id)
            rows = (await self.session.execute(select(
                SmartReminderConsent.state, SmartReminderConsent.source, SmartReminderConsent.source_key,
            ).where(SmartReminderConsent.user_id == user_id, SmartReminderConsent.channel == channel,
                    SmartReminderConsent.device_id == device_id))).mappings().all()
            current = next((r for r in rows if r["source_key"] == source_key and r["source"] == "user_intent"), None)
            if current is not None:
                return current["state"] == "off" or any(
                    r["state"] == "off" and not r["source"].startswith("legacy_") and r["source_key"] != source_key
                    for r in rows)
            return any(r["state"] == "off" for r in rows)

    async def legacy_send_veto(self, user_id, channel, *, device_id=None):
        """Routing affects sends, never silently edits consent/settings mirrors."""
        if await self.legacy_veto(user_id, channel, device_id=device_id):
            return True
        with self.session.no_autoflush:
            # Sticky even when review expires or the new switch is off.
            return await self.session.scalar(select(SmartReminderRouting.user_id).where(
                SmartReminderRouting.user_id == user_id)) is not None

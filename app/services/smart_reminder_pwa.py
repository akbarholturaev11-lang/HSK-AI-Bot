"""Single-destination PWA adapter for the existing Smart study job ledger."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
from uuid import uuid4

from sqlalchemy import select, update

from app.db.models.account_deletion import AccountDeletionRequest
from app.db.models.course_progress import CourseProgress
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.learner_pwa_push import LearnerPwaPushSubscription
from app.db.models.smart_reminder import SmartReminderAttempt, SmartReminderPreference, SmartReminderJob
from app.db.models.user import User
from app.services.course_notification_service import CourseNotificationService
from app.services.learner_pwa_push import (
    PushKeys, SubscribeRequest, _PUSH_PATH, _validate_subscription, sender_config,
)
from app.services.learner_pwa_push_copy import fallback_copy, push_copy
from app.services.notification_template_service import KEY_SMART_STUDY, NotificationTemplateService
from app.services.smart_reminder_destination import PWA_POLICY_VERSION
from app.services.smart_reminder_preferences import SmartReminderPreferencesService, _utc, pwa_study_consent
from app.services.smart_reminder_shadow_queue import ATTEMPT, JOB
from app.services.user_access_state_service import UserAccessState, UserAccessStateService
from app.services.webpush_transport import send_webpush


logger = logging.getLogger(__name__)
_LEASE = timedelta(seconds=45)


@dataclass(frozen=True)
class PwaReminderResult:
    reason: str
    job_id: str | None = None
    state: str | None = None


def _status(exc):
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(getattr(exc, "response", None), "status_code", None)
    return status if type(status) is int and 100 <= status <= 599 else None


def _outcome(status):
    if status in (200, 201, 202):
        return "provider_accepted", "provider_accepted"
    if status in (404, 410) or (status is not None and 400 <= status < 500 and status not in (408, 429)):
        return "definite_failure", "cancelled"
    return "unknown", "unknown"


class SmartReminderPwaService:
    """Dispatch the already-selected PWA job once; never enqueue a mirror/retry."""

    def __init__(self, settings_obj, sessions, *, clock=None, sender=None):
        self.settings, self.sessions = settings_obj, sessions
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.sender = sender or send_webpush

    def _now(self):
        return _utc(self.clock())

    async def dispatch(self, planner, actor, job_id, device_id, *, history_since):
        config = sender_config(self.settings)
        if config is None:
            return PwaReminderResult("pwa_push_disabled", job_id)
        private_key, subject, fernet = config
        now = self._now()
        lease_token = str(uuid4())
        async with self.sessions.begin() as session:
            # Preserve the Smart user-first lock order used by the existing
            # Android and Telegram authorization paths.
            user = (await session.execute(select(User).where(User.id == actor.user_id)
                .with_for_update())).scalar_one_or_none()
            if user is None or UserAccessStateService.classify(user) == UserAccessState.BLOCKED:
                return PwaReminderResult("smart_account_blocked", job_id)
            if await session.scalar(select(AccountDeletionRequest.id).where(
                    AccountDeletionRequest.user_id == actor.user_id,
                    AccountDeletionRequest.status.in_(("submitted", "processing"))).limit(1)):
                return PwaReminderResult("smart_account_deletion_pending", job_id)
            row = (await session.execute(select(JOB).where(
                JOB.c.user_id == actor.user_id, JOB.c.id == job_id,
            ).with_for_update())).mappings().one_or_none()
            if (row is None or row["selected_channel"] != "pwa" or
                    row["selected_device_id"] != device_id or
                    row["policy_version"] != PWA_POLICY_VERSION):
                return PwaReminderResult("pwa_job_not_selected", job_id)
            attempts = (await session.execute(select(ATTEMPT).where(
                ATTEMPT.c.job_id == job_id).with_for_update())).mappings().all()
            if attempts:
                attempt = attempts[0]
                if (len(attempts) == 1 and attempt["channel"] == "pwa" and
                        attempt["device_id"] == device_id and attempt["state"] == "in_flight" and
                        attempt["expires_at"] is not None and _utc(attempt["expires_at"]) <= now):
                    await session.execute(update(ATTEMPT).where(
                        ATTEMPT.c.id == attempt["id"], ATTEMPT.c.state == "in_flight").values(
                            state="unknown", resolved_at=now, reason_code="pwa_lease_outcome_unknown"))
                    await session.execute(update(JOB).where(
                        JOB.c.id == job_id, JOB.c.user_id == actor.user_id,
                        JOB.c.state == "claimed").values(
                            state="unknown", lease_token=None, lease_expires_at=None,
                            updated_at=now, reason_code="pwa_lease_outcome_unknown"))
                    return PwaReminderResult("pwa_outcome_unknown", job_id, "unknown")
                return PwaReminderResult("pwa_attempt_already_exists", job_id, attempt["state"])
            if (row["state"] != "pending" or row["expires_at"] is None or
                    _utc(row["expires_at"]) <= now or row["preference_revision"] < 0):
                return PwaReminderResult("pwa_job_not_due", job_id)
            # Like Telegram: a planned job waits for its frozen send time; the
            # runtime redispatches already-planned jobs on every tick.
            if row["scheduled_at"] is not None and now < _utc(row["scheduled_at"]):
                return PwaReminderResult("pwa_job_not_due", job_id, row["state"])
            pref = await SmartReminderPreferencesService(session).read(actor)
            epoch = await session.scalar(select(SmartReminderPreference.grant_epoch).where(
                SmartReminderPreference.user_id == actor.user_id))
            if (not pwa_study_consent(pref) or pref["revision"] != row["preference_revision"] or
                    (epoch or 0) != row["grant_epoch"] or pref["channel_mode"] == "manual_locked"):
                await session.execute(update(JOB).where(JOB.c.id == job_id).values(
                    state="cancelled", updated_at=now, reason_code="pwa_preference_changed"))
                return PwaReminderResult("pwa_preference_changed", job_id, "cancelled")
            if actor.access_expires_at is not None and _utc(actor.access_expires_at) <= now:
                return PwaReminderResult("smart_auth_expired", job_id)
            if await planner._reviewed(session, actor):
                await session.execute(update(JOB).where(JOB.c.id == job_id).values(
                    state="cancelled", updated_at=now, reason_code="pwa_review_unavailable"))
                return PwaReminderResult("pwa_review_unavailable", job_id, "cancelled")
            if not await NotificationTemplateService(session).is_enabled(KEY_SMART_STUDY, authorize=True):
                await session.execute(update(JOB).where(JOB.c.id == job_id).values(
                    state="cancelled", updated_at=now, reason_code="admin_study_disabled"))
                return PwaReminderResult("admin_study_disabled", job_id, "cancelled")
            rollout = getattr(planner, "rollout_reader", None)
            if rollout is not None and not await rollout(session, actor.user_id, now=now):
                await session.execute(update(JOB).where(JOB.c.id == job_id).values(
                    state="cancelled", updated_at=now, reason_code="rollout_cohort_closed"))
                return PwaReminderResult("rollout_cohort_closed", job_id, "cancelled")
            context, refused = await planner.queue._fresh(session, actor, row, now, history_since)
            if refused:
                return PwaReminderResult(refused.reason, job_id, "cancelled")
            if "pwa" not in context.permitted_channels or context.channel_mode == "manual_locked":
                await session.execute(update(JOB).where(JOB.c.id == job_id).values(
                    state="cancelled", updated_at=now, reason_code="pwa_study_unavailable"))
                return PwaReminderResult("pwa_study_unavailable", job_id, "cancelled")
            legacy = await planner._android(session)._legacy_contact(actor, row)
            if legacy:
                await session.execute(update(JOB).where(JOB.c.id == job_id).values(
                    state="cancelled", updated_at=now, reason_code=legacy))
                return PwaReminderResult(legacy, job_id, "cancelled")
            subscription = (await session.execute(select(LearnerPwaPushSubscription).join(
                DesktopDevice, DesktopDevice.id == LearnerPwaPushSubscription.device_id
            ).where(
                DesktopDevice.id == device_id, DesktopDevice.user_id == actor.user_id,
                DesktopDevice.platform == "pwa", DesktopDevice.revoked_at.is_(None),
                LearnerPwaPushSubscription.device_id == device_id,
                LearnerPwaPushSubscription.revoked_at.is_(None),
            ).with_for_update())).scalar_one_or_none()
            device = await session.get(DesktopDevice, device_id, with_for_update=True)
            live_session = await session.scalar(select(DesktopSession.id).where(
                DesktopSession.device_id == device_id, DesktopSession.revoked_at.is_(None),
                DesktopSession.expires_at > now).order_by(DesktopSession.expires_at.desc()).limit(1))
            if subscription is None or device is None or live_session is None:
                await session.execute(update(JOB).where(JOB.c.id == job_id).values(
                    state="cancelled", updated_at=now, reason_code="pwa_capability_unavailable"))
                return PwaReminderResult("pwa_capability_unavailable", job_id, "cancelled")
            try:
                raw = json.loads(fernet.decrypt(subscription.encrypted_payload.encode("ascii")).decode("ascii"))
                if not isinstance(raw, dict) or set(raw) != {"endpoint", "keys"} or not isinstance(raw["keys"], dict):
                    raise ValueError("invalid_payload")
                request = SubscribeRequest(endpoint=raw["endpoint"], keys=PushKeys(**raw["keys"]))
                if _validate_subscription(request) != subscription.endpoint_hash:
                    raise ValueError("invalid_subscription")
            except Exception:  # corrupt local data must not reach an external endpoint
                logger.warning("Smart PWA endpoint unavailable")
                await session.execute(update(JOB).where(JOB.c.id == job_id).values(
                    state="cancelled", updated_at=now, reason_code="pwa_capability_unavailable"))
                return PwaReminderResult("pwa_capability_unavailable", job_id, "cancelled")
            attempt_id = str(uuid4())
            attempt_key = hashlib.sha256((job_id + ":pwa:first").encode("ascii")).hexdigest()
            changed = await session.execute(update(JOB).where(
                JOB.c.id == job_id, JOB.c.user_id == actor.user_id,
                JOB.c.state == "pending", JOB.c.selected_channel == "pwa",
                JOB.c.selected_device_id == device_id,
                JOB.c.preference_revision == pref["revision"], JOB.c.grant_epoch == (epoch or 0),
                ~select(ATTEMPT.c.id).where(ATTEMPT.c.job_id == job_id).exists(),
            ).values(state="claimed", lease_token=lease_token,
                lease_expires_at=min(_utc(row["expires_at"]), now + _LEASE),
                updated_at=now, reason_code="pwa_provider_started"))
            if changed.rowcount != 1:
                return PwaReminderResult("pwa_job_not_claimable", job_id)
            session.add(SmartReminderAttempt(
                id=attempt_id, job_id=job_id, attempt_key=attempt_key,
                channel="pwa", device_id=device_id, grant_epoch=row["grant_epoch"],
                state="in_flight", prepared_at=now, started_at=now,
                expires_at=min(_utc(row["expires_at"]), now + _LEASE),
                reason_code="pwa_provider_started",
            ))
            await session.flush()
            language = user.language if user.language in {"uz", "ru", "tj"} else "ru"
            resolved = await NotificationTemplateService(session).resolve(KEY_SMART_STUDY, language)
            title, body = fallback_copy(KEY_SMART_STUDY, language)
            text = ""
            if resolved:
                try:
                    text = resolved["text"].format(lesson=row["lesson_order"])
                except (KeyError, IndexError, ValueError):
                    pass
            title, body = push_copy(text, title=title, body=body)
            public_payload = json.dumps({
                "title": title, "body": body, "lang": language,
                "url": _PUSH_PATH, "tag": "hsk-smart-" + job_id.replace("-", "")[:20],
            }, ensure_ascii=False, separators=(",", ":"))
            endpoint_payload = raw
        status = None
        try:
            if sender_config(self.settings) is None:
                raise RuntimeError("PWA push disabled after authorization")
            status = await self.sender(endpoint_payload, public_payload, private_key, subject)
            if type(status) is not int or not 100 <= status <= 599:
                status = None
        except Exception as exc:  # transport may have accepted before its reply was lost
            status = _status(exc)
            logger.warning("Smart PWA provider outcome unavailable; code=%s", status)
        attempt_state, job_state = _outcome(status)
        now = self._now()
        async with self.sessions.begin() as session:
            attempt = (await session.execute(select(ATTEMPT).where(
                ATTEMPT.c.job_id == job_id, ATTEMPT.c.channel == "pwa",
                ATTEMPT.c.device_id == device_id,
            ).with_for_update())).mappings().one_or_none()
            job = (await session.execute(select(JOB).where(
                JOB.c.user_id == actor.user_id, JOB.c.id == job_id,
            ).with_for_update())).mappings().one_or_none()
            if attempt is None or job is None or attempt["state"] != "in_flight" or job["lease_token"] != lease_token:
                return PwaReminderResult("pwa_outcome_already_recorded", job_id,
                    attempt["state"] if attempt else None)
            await session.execute(update(ATTEMPT).where(
                ATTEMPT.c.id == attempt["id"], ATTEMPT.c.state == "in_flight").values(
                    state=attempt_state, resolved_at=now,
                    reason_code="pwa_" + attempt_state))
            await session.execute(update(JOB).where(
                JOB.c.id == job_id, JOB.c.user_id == actor.user_id,
                JOB.c.state == "claimed", JOB.c.lease_token == lease_token,
            ).values(state=job_state, lease_token=None, lease_expires_at=None,
                updated_at=now, reason_code="pwa_" + attempt_state))
            if status in (404, 410):
                await session.execute(update(LearnerPwaPushSubscription).where(
                    LearnerPwaPushSubscription.device_id == device_id,
                    LearnerPwaPushSubscription.revoked_at.is_(None),
                ).values(revoked_at=now, updated_at=now))
            if attempt_state == "provider_accepted":
                await session.execute(update(CourseProgress).where(
                    CourseProgress.user_id == actor.user_id).values(last_reminder_sent_at=now))
        if attempt_state == "provider_accepted":
            try:
                async with self.sessions.begin() as session:
                    user = await session.get(User, actor.user_id)
                    if user is not None:
                        row = (await session.execute(select(JOB).where(JOB.c.id == job_id))).mappings().one()
                        await CourseNotificationService(session).record(
                            user, key=KEY_SMART_STUDY, lang=language,
                            title=title, body=body,
                            action="course", source="smart_pwa", level=row["course_key"],
                            lesson_order=row["lesson_order"], dedupe_key="job:" + job_id,
                            params={"template_service": KEY_SMART_STUDY, "lesson": row["lesson_order"]},
                            pwa_push_suppressed=True,
                        )
            except Exception:  # the accepted provider result stays terminal
                logger.warning("Smart PWA inbox notice could not be stored")
        observer = getattr(planner.queue, "analysis_observer", None)
        if observer is not None:
            await observer.capture_job(actor.user_id, job_id)
        return PwaReminderResult("pwa_" + attempt_state, job_id, job_state)

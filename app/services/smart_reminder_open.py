"""Authenticated client-reported opens; never display, learning or authority."""
import hashlib
import hmac
import json
import logging
import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr
from sqlalchemy import select, text

from app.db.models.smart_reminder import SmartReminderAndroidGrant, SmartReminderAttempt, SmartReminderJob
from app.services.smart_reminder_analysis import RAW_RETENTION, SmartReminderAnalysisService
from app.services.smart_reminder_policy import day_window
from app.services.smart_reminder_preferences import SmartReminderError, SmartReminderPreferencesService, _utc

UUID_PATTERN = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
logger = logging.getLogger(__name__)


class SmartOpenReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Annotated[StrictInt, Field(ge=1, le=1)]
    proof: Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]


class SmartReminderOpenService:
    def __init__(self, settings, *, clock=None):
        self.settings = settings
        self.analysis = SmartReminderAnalysisService(None, clock=clock)

    def proof(self, actor, job_id, source_id):
        """Pure optional metadata from a verified source; no SQL or credential."""
        try:
            return self._proof(actor, job_id, source_id)
        except Exception:
            logger.warning("Smart open metadata unavailable")
            return None

    def _proof(self, actor, job_id, source_id):
        if getattr(self.settings, "SMART_REMINDER_ANALYSIS_ENABLED", False) is not True:
            return None
        channel = "android" if actor.kind == "android" else "telegram" if actor.kind in {"telegram", "telegram_bot"} else None
        secret = getattr(self.settings, "DESKTOP_AUTH_SIGNING_SECRET" if channel == "android" else "BOT_TOKEN", None)
        if (channel is None or not isinstance(secret, str) or not secret or type(actor.user_id) is not int or
                actor.user_id <= 0 or any(not isinstance(v, str) or re.fullmatch(UUID_PATTERN, v) is None
                    for v in (job_id, source_id))):
            return None
        binding = ["smart-open-proof-v1", channel, actor.user_id, job_id, source_id]
        if channel == "android":
            if not actor.device_id or not actor.session_id:
                return None
            binding.extend((actor.device_id, actor.session_id))
        return hmac.new(secret.encode(), json.dumps(binding, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()

    async def record(self, session, actor, job_id, body):
        """Caller owns this observation-only transaction; source is never written."""
        def ack(reason, observed=False):
            return {"ok": True, "version": 1, "observed": observed, "reason": reason}
        if getattr(self.settings, "SMART_REMINDER_ANALYSIS_ENABLED", False) is not True:
            return ack("open_observation_disabled")
        if not isinstance(job_id, str) or re.fullmatch(UUID_PATTERN, job_id) is None:
            raise SmartReminderError("smart_request_invalid", 422)
        with session.no_autoflush:
            if session.bind.dialect.name == "postgresql":
                await session.execute(text("SET LOCAL statement_timeout = '2000'"))
            await SmartReminderPreferencesService(session)._lock(actor)
            now = self.analysis.now()
            if actor.kind == "android" and (actor.access_expires_at is None or _utc(actor.access_expires_at) <= now):
                raise SmartReminderError("smart_auth_required", 401)
            job = (await session.execute(select(SmartReminderJob.__table__).where(
                SmartReminderJob.id == job_id, SmartReminderJob.user_id == actor.user_id)
                .with_for_update())).mappings().one_or_none()
            if job is None:
                raise SmartReminderError("smart_open_unavailable", 404)
            channel = "android" if actor.kind == "android" else "telegram"
            if job["selected_channel"] != channel or not job["policy_version"].startswith("smart-" + channel + "-v1:"):
                return ack("open_source_unconfirmed")
            attempts = (await session.execute(select(SmartReminderAttempt.__table__).where(
                SmartReminderAttempt.job_id == job_id).limit(2))).mappings().all()
            if len(attempts) != 1:
                return ack("open_source_unconfirmed")
            attempt = attempts[0]
            grant = None
            if channel == "android":
                grant = (await session.execute(select(SmartReminderAndroidGrant.__table__).where(
                    SmartReminderAndroidGrant.user_id == actor.user_id, SmartReminderAndroidGrant.job_id == job_id,
                    SmartReminderAndroidGrant.device_id == actor.device_id,
                    SmartReminderAndroidGrant.session_id == actor.session_id))).mappings().one_or_none()
                if grant is None:
                    raise SmartReminderError("smart_open_unavailable", 403)
            expected = self.proof(actor, job_id, grant["id"] if grant else attempt["id"])
            if expected is None:
                return ack("open_observation_unavailable")
            if not hmac.compare_digest(body.proof, expected):
                raise SmartReminderError("smart_open_unavailable", 403)
            try:
                start, end = day_window(job["timezone_name"], job["local_day"].isoformat())
            except (KeyError, TypeError, ValueError):
                return ack("open_window_unavailable")
            if (start != _utc(job["day_start_utc"]) or end != _utc(job["day_end_utc"]) or not start <= now < end):
                return ack("open_window_unavailable")
            if (attempt["channel"] != channel or attempt["grant_epoch"] != job["grant_epoch"] or
                    attempt["started_at"] is None or attempt["resolved_at"] is None):
                return ack("open_source_unconfirmed")
            at, resolved = _utc(attempt["started_at"]), _utc(attempt["resolved_at"])
            if (not now - RAW_RETENTION < at <= resolved <= now or
                    not _utc(job["created_at"]) <= _utc(attempt["prepared_at"]) <= at or
                    not _utc(job["scheduled_at"]) <= at < _utc(attempt["expires_at"]) <= _utc(job["expires_at"])):
                return ack("open_source_unconfirmed")
            if channel == "android":
                if (attempt["state"] != "client_posted_unverified" or grant["attempt_id"] != attempt["id"] or
                        grant["device_id"] != attempt["device_id"] or grant["device_id"] != job["selected_device_id"] or
                        grant["policy_version"] != job["policy_version"] or grant["grant_epoch"] != job["grant_epoch"] or
                        grant["preference_revision"] != job["preference_revision"] or
                        grant["receipt_outcome"] != "client_posted_unverified" or grant["receipt_id"] is None or
                        grant["received_at"] is None or _utc(grant["issued_at"]) != at or
                        _utc(grant["received_at"]) != resolved or _utc(grant["expires_at"]) != _utc(attempt["expires_at"])):
                    return ack("open_source_unconfirmed")
            elif attempt["state"] != "provider_accepted" or attempt["device_id"] is not None:
                return ack("open_source_unconfirmed")
            inserted = await self.analysis._fact(session, job, attempt["id"], "client_reported_open", now,
                channel, now, reason="authenticated_client_report")
            return ack("open_observed" if inserted else "open_already_observed", True)

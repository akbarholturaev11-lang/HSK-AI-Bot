"""Dormant selected-job protocol. Caller commits before returning any grant.

No producer, trusted admission/learning readers or enabled production factory
are installed. Client capability is never admission or consent. Issuance is
irreversible evidence of possible IO: lost responses are not re-granted.
"""
from dataclasses import asdict, dataclass, replace
from datetime import datetime, time, timedelta, timezone
import hashlib
import json
import re
from types import SimpleNamespace
from typing import Annotated, Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr
from sqlalchemy import insert, select, update

from app.db.models.android_push import AndroidPushToken
from app.db.models.course_progress import CourseProgress
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.smart_reminder import SmartReminderAndroidGrant, SmartReminderCapability, SmartReminderRouting
from app.services.course_reminder_service import reminder_tz_offset
from app.services.smart_reminder_cadence import evaluate_cadence
from app.services.smart_reminder_coordination import read_d1_scope
from app.services.smart_reminder_policy import _aware_utc, day_window, evaluate, local_time_instants
from app.services.smart_reminder_policy_context import SmartReminderPolicyContextService
from app.services.smart_reminder_preferences import MAX_REVISION, SmartReminderError, SmartReminderPreferencesService, _utc
from app.services.smart_reminder_shadow_queue import ATTEMPT, JOB, SmartReminderShadowQueue
from app.services.smart_reminder_telegram import LearningCoverage, _android_inventory

GRANT = SmartReminderAndroidGrant.__table__
CAP = SmartReminderCapability.__table__
UUID_PATTERN = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
UUIDText = Annotated[StrictStr, Field(pattern="^" + UUID_PATTERN + "$")]
Counter = Annotated[StrictInt, Field(ge=0, le=MAX_REVISION)]
VERSION = "smart-android-v1"


class AndroidStudyClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: StrictInt = Field(ge=1, le=1)
    request_id: UUIDText
    local_epoch: UUIDText
    capability_generation: Counter
    preference_revision: Counter
    grant_epoch: Counter


class AndroidStudyReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: StrictInt = Field(ge=1, le=1)
    grant_id: UUIDText
    receipt_id: UUIDText
    local_epoch: UUIDText
    outcome: Literal["client_declined_before_post", "client_posted_unverified", "client_outcome_unknown"]


@dataclass(frozen=True)
class AndroidAdmission:
    """Privileged reviewed fencing input, never populated from HTTP facts."""
    user_id: int
    job_id: str
    device_id: str
    session_id: str
    generation: int
    preference_revision: int
    grant_epoch: int
    verified_at: datetime
    valid_until: datetime
    history_since: datetime
    evidence_sha256: str
    inventory_sha256: str
    legacy_quiesced: bool
    legacy_outcomes_reconciled: bool
    other_study_fenced: bool

    def __post_init__(self):
        if (type(self.user_id) is not int or self.user_id <= 0 or
                any(type(v) is not int or v < lower for v, lower in (
                    (self.generation, 1), (self.preference_revision, 0), (self.grant_epoch, 0))) or
                not self.device_id or not self.session_id or not re.fullmatch(UUID_PATTERN, self.job_id) or
                not re.fullmatch(r"[0-9a-f]{64}", self.evidence_sha256) or
                not re.fullmatch(r"[0-9a-f]{64}", self.inventory_sha256) or
                any(v is not True for v in (self.legacy_quiesced, self.legacy_outcomes_reconciled, self.other_study_fenced)) or
                not _aware_utc(self.history_since) <= _aware_utc(self.verified_at) < _aware_utc(self.valid_until)):
            raise ValueError("Explicit reviewed Android fencing required")


def denied(reason):
    return {"ok": True, "version": 1, "dispatch_allowed": False, "reason": reason}


class SmartReminderAndroidService:
    def __init__(self, session, *, enabled=False, admission_reader=None, calibration=None,
                 coverage_reader=None, clock=None):
        self.session = session
        self.enabled, self.admission_reader = enabled, admission_reader
        self.calibration, self.coverage_reader = calibration, coverage_reader
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.queue = SmartReminderShadowQueue(None, clock=self.clock)
        digest = hashlib.sha256(json.dumps(asdict(calibration), sort_keys=True, default=str).encode()).hexdigest()[:12] if calibration else None
        self.policy_version = VERSION + ":" + digest if digest else None

    def _now(self):
        return _aware_utc(self.clock())

    def _gate(self):
        if self.enabled is not True: return denied("android_dispatch_disabled")
        if self.admission_reader is None: return denied("android_admission_unavailable")
        if self.calibration is None: return denied("cadence_calibration_unconfigured")
        if self.coverage_reader is None: return denied("learning_coverage_unavailable")

    async def _auth(self, actor):
        if actor.kind != "android": raise SmartReminderError("android_device_required", 403)
        await SmartReminderPreferencesService(self.session)._lock(actor)
        now = self._now()
        if (not isinstance(actor.access_expires_at, datetime) or actor.access_expires_at.tzinfo is None or
                _aware_utc(actor.access_expires_at) <= now):
            raise SmartReminderError("smart_auth_required", 401)
        end = await self.session.scalar(select(DesktopSession.expires_at).where(
            DesktopSession.id == actor.session_id, DesktopSession.device_id == actor.device_id))
        if end is None or _utc(end) <= now: raise SmartReminderError("smart_session_revoked", 401)
        return min(_utc(end), _aware_utc(actor.access_expires_at))

    async def _capability(self, actor):
        cap = (await self.session.execute(select(CAP).where(
            CAP.c.user_id == actor.user_id, CAP.c.device_id == actor.device_id))).mappings().one_or_none()
        now = self._now()
        if (cap is None or cap["protocol_version"] != 1 or cap["generation"] < 1 or
                cap["autonomous_study_disabled"] is not True or cap["study_notifications_allowed"] is not True or
                cap["observed_at"] is None or cap["expires_at"] is None or
                not _utc(cap["observed_at"]) <= now < _utc(cap["expires_at"])):
            return None
        return cap

    async def _job(self, actor, job_id):
        if not isinstance(job_id, str) or not re.fullmatch(UUID_PATTERN, job_id):
            raise SmartReminderError("smart_request_invalid", 422)
        row = (await self.session.execute(select(JOB).where(JOB.c.id == job_id,
            JOB.c.user_id == actor.user_id, JOB.c.selected_channel == "android",
            JOB.c.selected_device_id == actor.device_id).with_for_update())).mappings().one_or_none()
        if row is None: raise SmartReminderError("android_study_job_not_found", 404)
        return row

    async def _admission(self, actor, row):
        routing = (await self.session.execute(select(SmartReminderRouting.__table__).where(
            SmartReminderRouting.user_id == actor.user_id).with_for_update())).mappings().one_or_none()
        now = self._now()
        if routing is None or routing["state"] != "held": return None
        inventory, fenced_until = await _android_inventory(self.session, actor.user_id, now)
        if inventory is None or fenced_until is None or fenced_until <= now: return None
        review = await self.admission_reader(self.session, actor, row["id"], now)
        now = self._now()
        if (not isinstance(review, AndroidAdmission) or
                review.inventory_sha256 != inventory or
                (review.user_id, review.job_id, review.device_id, review.session_id) !=
                (actor.user_id, row["id"], actor.device_id, actor.session_id) or
                (review.generation, review.preference_revision, review.grant_epoch) !=
                (routing["generation"], row["preference_revision"], row["grant_epoch"]) or
                routing["preference_revision"] != row["preference_revision"] or routing["grant_epoch"] != row["grant_epoch"] or
                not _utc(routing["held_at"]) <= _aware_utc(review.verified_at) <= now < _aware_utc(review.valid_until)):
            return None
        until = min(_aware_utc(review.valid_until), fenced_until)
        return replace(review, valid_until=until) if now < until else None

    async def mode(self, actor):
        """Sticky migration observation, never admission or posting authority."""
        with self.session.no_autoflush:
            await self._auth(actor)
            held = await self.session.scalar(select(SmartReminderRouting.user_id).where(
                SmartReminderRouting.user_id == actor.user_id))
            disabled = await self.session.scalar(select(CAP.c.autonomous_study_disabled).where(
                CAP.c.user_id == actor.user_id, CAP.c.device_id == actor.device_id))
            return {"ok": True, "version": 1, "dispatch_allowed": False,
                    "server_claim_required": held is not None or disabled is True}

    async def due(self, actor):
        with self.session.no_autoflush:
            await self._auth(actor)
            gated = self._gate()
            if gated: return gated
            cap = await self._capability(actor)
            if cap is None: return denied("android_capability_unavailable")
            pref = await SmartReminderPreferencesService(self.session).read(actor)
            if (pref["master_enabled"] is False or pref["channels"]["android"]["this_device_consent"] != "on" or
                    pref["channel_mode"] == "manual_locked" and pref["preferred_channel"] != "android"):
                return denied("android_study_unavailable")
            now = self._now()
            row = (await self.session.execute(select(JOB).where(JOB.c.user_id == actor.user_id,
                JOB.c.selected_device_id == actor.device_id, JOB.c.selected_channel == "android",
                JOB.c.policy_version == self.policy_version, JOB.c.state == "pending",
                JOB.c.scheduled_at <= now, JOB.c.expires_at > now,
                ~select(GRANT.c.id).where(GRANT.c.job_id == JOB.c.id).exists(),
            ).order_by(JOB.c.scheduled_at, JOB.c.id).limit(1))).mappings().first()
            if row is None: return denied("android_no_due_job")
            review = await self._admission(actor, row)
            if review is None: return denied("android_admission_unavailable")
            return denied("android_claim_required") | {"job_id": row["id"],
                "preference_revision": row["preference_revision"], "grant_epoch": row["grant_epoch"],
                "capability_generation": cap["generation"]}

    async def _cancel(self, row, reason, state="cancelled"):
        await self.session.execute(update(ATTEMPT).where(ATTEMPT.c.job_id == row["id"],
            ATTEMPT.c.state == "prepared", ATTEMPT.c.started_at.is_(None)).values(state="cancelled", reason_code=reason))
        await self.queue._close(self.session, row, state, reason, self._now())
        return denied(reason)

    async def _legacy_contact(self, actor, row):
        legacy = (await self.session.execute(select(CourseProgress.last_reminder_sent_at,
            CourseProgress.reminder_tz_offset).where(CourseProgress.user_id == actor.user_id))).mappings().one_or_none()
        start, end = _utc(row["day_start_utc"]), _utc(row["day_end_utc"])
        if legacy and legacy["last_reminder_sent_at"] is not None:
            at = _utc(legacy["last_reminder_sent_at"])
            offset = reminder_tz_offset(SimpleNamespace(**legacy))
            if at > self._now() or not -12 <= offset <= 14: return "legacy_contact_unknown"
            shift = timedelta(hours=offset)
            lower = datetime.combine((at+shift).date(), time.min, timezone.utc)-shift
            if start <= at < end or lower < end and lower+timedelta(days=1) > start:
                return "legacy_study_already_attempted"
        facts = (await self.session.execute(select(AndroidPushToken.last_study_push_day,
            AndroidPushToken.timezone_name).join(DesktopDevice, DesktopDevice.id == AndroidPushToken.device_id).where(
            DesktopDevice.user_id == actor.user_id, AndroidPushToken.last_study_push_day.is_not(None)).limit(129))).mappings().all()
        if len(facts) > 128: return "legacy_contact_unknown"
        for fact in facts:
            try: lower, upper = day_window(fact["timezone_name"], fact["last_study_push_day"])
            except (ValueError, KeyError, TypeError): return "legacy_contact_unknown"
            if lower < end and upper > start: return "legacy_study_already_attempted"

    async def claim(self, actor, job_id, body):
        with self.session.no_autoflush:
            auth_until = await self._auth(actor)
            gated = self._gate()
            if gated: return gated
            row = await self._job(actor, job_id)
            if await self.session.scalar(select(GRANT.c.id).where(GRANT.c.job_id == job_id)):
                return denied("android_grant_already_issued")
            if await self.session.scalar(select(GRANT.c.id).where(GRANT.c.user_id == actor.user_id,
                    GRANT.c.claim_request_id == body.request_id)):
                raise SmartReminderError("android_claim_request_conflict", 409)
            attempts = (await self.session.execute(select(ATTEMPT).where(ATTEMPT.c.job_id == job_id)
                .with_for_update())).mappings().all()
            if row["state"] != "pending" or row["policy_version"] != self.policy_version or attempts:
                return denied("android_job_not_claimable")
            now = self._now()
            if now >= _utc(row["expires_at"]): return await self._cancel(row, "android_job_expired", "expired")
            if now < _utc(row["scheduled_at"]): return denied("android_job_not_due")
            cap = await self._capability(actor)
            if cap is None: return denied("android_capability_unavailable")
            if (body.capability_generation, body.preference_revision, body.grant_epoch) != (
                    cap["generation"], row["preference_revision"], row["grant_epoch"]):
                raise SmartReminderError("android_claim_context_changed", 409)
            review = await self._admission(actor, row)
            if review is None: return denied("android_admission_unavailable")
            context, refused = await self.queue._fresh(self.session, actor, row, self._now(), review.history_since)
            if refused: return denied(refused.reason)
            if ("android" not in context.permitted_channels or
                    context.channel_mode == "manual_locked" and context.preferred_channel != "android"):
                return await self._cancel(row, "android_study_unavailable")
            legacy = await self._legacy_contact(actor, row)
            if legacy: return await self._cancel(row, legacy)
            snapshot = await SmartReminderPolicyContextService(self.session).load_cadence(actor,
                observed_at=self._now(), history_since=review.history_since, expected_level=row["course_key"])
            observed = self._now()
            coverage = await self.coverage_reader(self.session, actor, review.history_since, observed)
            if (not isinstance(coverage, LearningCoverage) or coverage.user_id != actor.user_id or
                    _aware_utc(coverage.observed_at) != observed):
                return denied("learning_coverage_unavailable")
            now = self._now()
            context = replace(context, observed_at=now)
            cadence = evaluate_cadence(replace(snapshot, policy=replace(snapshot.policy, observed_at=now),
                intents=tuple(j for j in snapshot.intents if j.job_id != job_id),
                learning_complete_since=coverage.complete_since), calibration=self.calibration, allow_elapsed_time=True)
            final = evaluate(context, allow_elapsed_time=True)
            if not final.candidate: return await self._cancel(row, final.reason)
            if cadence.reason != "shadow_candidate": return await self._cancel(row, cadence.reason)
            d1 = await read_d1_scope(self.session, actor.user_id, now)
            now = self._now()
            if d1.reason(now): return await self._cancel(row, d1.reason(now))
            final = evaluate(replace(context, observed_at=now), allow_elapsed_time=True)
            if not final.candidate: return await self._cancel(row, final.reason)
            until = min(_utc(row["expires_at"]), auth_until, _utc(cap["expires_at"]), _aware_utc(review.valid_until))
            zone = ZoneInfo(context.timezone_name)
            day = now.astimezone(zone).date().isoformat()
            for clock in (context.quiet_start, context.quiet_end):
                if clock is not None:
                    instants = local_time_instants(day, clock, zone)
                    if len(instants) != 1: return await self._cancel(row, "personal_quiet_clock_uncertain")
                    until = min([until] + [instant for instant in instants if instant > now])
            if until <= now: return denied("android_authority_expired")
            grant_id, attempt_id = str(uuid4()), str(uuid4())
            await self.session.execute(insert(ATTEMPT).values(id=attempt_id, job_id=job_id,
                attempt_key=hashlib.sha256((job_id+":android:first").encode()).hexdigest(), channel="android",
                device_id=actor.device_id, grant_epoch=row["grant_epoch"], state="in_flight",
                prepared_at=now, started_at=now, expires_at=until, reason_code="android_grant_issued"))
            await self.session.execute(insert(GRANT).values(id=grant_id, user_id=actor.user_id, job_id=job_id,
                attempt_id=attempt_id, device_id=actor.device_id, session_id=actor.session_id,
                local_epoch=body.local_epoch, claim_request_id=body.request_id, policy_version=self.policy_version,
                admission_sha256=review.evidence_sha256,
                grant_epoch=row["grant_epoch"], preference_revision=row["preference_revision"],
                capability_generation=cap["generation"], cohort_generation=review.generation,
                issued_at=now, expires_at=until))
            await self.session.execute(update(JOB).where(JOB.c.id == job_id).values(state="claimed",
                lease_token=grant_id, lease_expires_at=until, updated_at=now, reason_code="android_grant_issued"))
            finished_at = self._now()
            if finished_at >= until:
                # SQL may have waited. No grant has left this transaction yet;
                # retain its tombstone but withhold posting authority.
                await self.session.execute(update(ATTEMPT).where(ATTEMPT.c.id == attempt_id).values(
                    state="cancelled", started_at=None, resolved_at=finished_at, reason_code="android_expired_before_response"))
                await self.session.execute(update(JOB).where(JOB.c.id == job_id).values(state="expired",
                    lease_token=None, lease_expires_at=None, updated_at=finished_at, reason_code="android_expired_before_response"))
                return denied("android_expired_before_response")
            return {"ok": True, "version": 1, "dispatch_allowed": True, "reason": "android_grant_issued",
                "job_id": job_id, "grant_id": grant_id, "local_epoch": body.local_epoch,
                "issued_at": now.isoformat(), "expires_at": until.isoformat(),
                "preference_revision": row["preference_revision"], "grant_epoch": row["grant_epoch"],
                "capability_generation": cap["generation"], "local_day": row["local_day"].isoformat(),
                "timezone_name": row["timezone_name"], "course_key": row["course_key"], "lesson_order": row["lesson_order"]}

    async def receipt(self, actor, job_id, body):
        with self.session.no_autoflush:
            await self._auth(actor)
            row = await self._job(actor, job_id)
            grant = (await self.session.execute(select(GRANT).where(GRANT.c.id == body.grant_id,
                GRANT.c.job_id == job_id, GRANT.c.user_id == actor.user_id,
                GRANT.c.device_id == actor.device_id, GRANT.c.session_id == actor.session_id,
                GRANT.c.local_epoch == body.local_epoch).with_for_update())).mappings().one_or_none()
            if grant is None: raise SmartReminderError("android_grant_not_found", 404)
            if grant["receipt_id"] is not None:
                if (grant["receipt_id"], grant["receipt_outcome"]) != (body.receipt_id, body.outcome):
                    raise SmartReminderError("android_receipt_conflict", 409)
            else:
                attempt = (await self.session.execute(select(ATTEMPT).where(ATTEMPT.c.id == grant["attempt_id"],
                    ATTEMPT.c.job_id == job_id, ATTEMPT.c.channel == "android",
                    ATTEMPT.c.device_id == actor.device_id).with_for_update())).mappings().one_or_none()
                now = self._now()
                if (attempt is None or attempt["state"] not in {"in_flight", "unknown"} or
                        attempt["started_at"] is None or _utc(grant["issued_at"]) > now or
                        attempt["grant_epoch"] != grant["grant_epoch"] or row["policy_version"] != grant["policy_version"]):
                    raise SmartReminderError("android_receipt_context_changed", 409)
                state = {"client_declined_before_post":"confirmed_not_displayed",
                         "client_posted_unverified":"client_posted_unverified", "client_outcome_unknown":"unknown"}[body.outcome]
                await self.session.execute(update(GRANT).where(GRANT.c.id == grant["id"]).values(
                    receipt_id=body.receipt_id, receipt_outcome=body.outcome, received_at=now))
                await self.session.execute(update(ATTEMPT).where(ATTEMPT.c.id == grant["attempt_id"]).values(
                    state=state, resolved_at=now, reason_code=body.outcome))
                await self.session.execute(update(JOB).where(JOB.c.id == job_id).values(
                    state="cancelled" if state == "confirmed_not_displayed" else "unknown",
                    lease_token=None, lease_expires_at=None, updated_at=now, reason_code=body.outcome))
            return denied("android_receipt_recorded") | {"receipt_id": body.receipt_id, "outcome": body.outcome}

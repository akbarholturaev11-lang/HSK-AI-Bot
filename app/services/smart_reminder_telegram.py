"""Internal reviewed Telegram ownership/attempt boundary; not a live worker.

No producer, HTTP/operator endpoint or production transport is wired here.
Review attestations are privileged inputs AFTER a sticky hold/drain barrier;
they are never derived from client telemetry or missing Android inventory.
"""
from dataclasses import asdict, dataclass, replace
from datetime import datetime, time, timedelta, timezone
import hashlib
import json
import re
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import insert, select, update

from app.db.models.course_progress import CourseProgress
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.android_push import AndroidPushToken
from app.db.models.smart_reminder import SmartReminderRouting, SmartReminderPreference, SmartReminderCapability
from app.db.models.user import User
from app.services.course_reminder_service import reminder_tz_offset
from app.services.smart_reminder_cadence import evaluate_cadence
from app.services.smart_reminder_lifecycle import SmartReminderLifecycleService
from app.services.smart_reminder_policy import _aware_utc
from app.services.smart_reminder_policy_context import SmartReminderPolicyContextService
from app.services.smart_reminder_preferences import MAX_REVISION, SmartReminderError, SmartReminderPreferencesService, _utc
from app.services.smart_reminder_shadow_queue import ATTEMPT, JOB, QUEUE_VERSION, SmartReminderShadowQueue


ROUTING = SmartReminderRouting.__table__
TELEGRAM_VERSION = "smart-telegram-v1"
MAX_ROUTING_ROWS = 128  # Technical read bound, not retention or fleet proof.


def _telegram(actor):
    if (actor.kind not in {"telegram", "telegram_bot"} or
            type(actor.telegram_id) is not int or actor.telegram_id <= 0):
        raise SmartReminderError("telegram_actor_required", 401)


def _binding(actor):
    return hashlib.sha256(json.dumps([actor.user_id, actor.telegram_id]).encode()).hexdigest()


@dataclass(frozen=True)
class RoutingReview:
    user_id: int
    generation: int
    verified_at: datetime
    verified_until: datetime
    evidence_sha256: str
    legacy_quiesced: bool
    legacy_outcomes_reconciled: bool
    other_study_fenced: bool
    version: int = 1

    def __post_init__(self):
        if (type(self.version) is not int or self.version != 1 or type(self.user_id) is not int or self.user_id <= 0 or
                type(self.generation) is not int or self.generation < 1 or
                self.legacy_quiesced is not True or self.legacy_outcomes_reconciled is not True or
                self.other_study_fenced is not True or
                not isinstance(self.evidence_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", self.evidence_sha256) or
                _aware_utc(self.verified_at) >= _aware_utc(self.verified_until)):
            raise ValueError("Explicit account/generation-bound reviewed fencing evidence required")


@dataclass(frozen=True)
class TelegramResult:
    reason: str
    job_id: str | None = None
    state: str | None = None
    token: str | None = None
    lease_expires_at: datetime | None = None
    generation: int | None = None


@dataclass(frozen=True)
class TelegramEnvelope:
    """Ephemeral selected destination for a trusted internal transport only."""
    user_id: int
    job_id: str
    telegram_id: int
    level: str
    lesson_order: int
    local_day: str


@dataclass(frozen=True)
class LearningCoverage:
    """Trusted authoritative source attestation under User, never telemetry.

    The legacy reader cannot supply this. No production reader is registered;
    protocol tests use an explicit complete synthetic learning feed.
    """
    user_id: int
    complete_since: datetime
    observed_at: datetime
    source_version: str

    def __post_init__(self):
        if (type(self.user_id) is not int or self.user_id <= 0 or
                not isinstance(self.source_version, str) or not self.source_version.strip() or
                _aware_utc(self.complete_since) > _aware_utc(self.observed_at)):
            raise ValueError("Typed authoritative learning coverage required")


async def _read_routing(session, actor):
    _telegram(actor)
    pref = await SmartReminderPreferencesService(session).read(actor)  # User first.
    row = (await session.execute(select(ROUTING).where(
        ROUTING.c.user_id == actor.user_id).with_for_update())).mappings().one_or_none()
    epoch = await session.scalar(select(SmartReminderPreference.grant_epoch).where(
        SmartReminderPreference.user_id == actor.user_id))
    return pref, epoch or 0, row


async def _android_inventory(session, user_id, now):
    """Minimal non-secret drift fence, NOT proof an absent/offline APK stopped."""
    devices = (await session.execute(select(DesktopDevice.id, DesktopDevice.app_version,
        DesktopDevice.revoked_at, DesktopDevice.created_at).where(DesktopDevice.user_id == user_id,
        DesktopDevice.platform == "android").order_by(DesktopDevice.id).limit(MAX_ROUTING_ROWS+1))).mappings().all()
    if len(devices) > MAX_ROUTING_ROWS: return None, now
    ids = [r["id"] for r in devices]
    sessions = (await session.execute(select(DesktopSession.id, DesktopSession.device_id,
        DesktopSession.revoked_at, DesktopSession.expires_at, DesktopSession.created_at).where(
        DesktopSession.device_id.in_(ids)).order_by(DesktopSession.id).limit(MAX_ROUTING_ROWS+1))).mappings().all() if ids else []
    capabilities = (await session.execute(select(SmartReminderCapability.device_id,
        SmartReminderCapability.generation, SmartReminderCapability.protocol_version,
        SmartReminderCapability.autonomous_study_disabled, SmartReminderCapability.observed_at,
        SmartReminderCapability.expires_at).where(SmartReminderCapability.user_id == user_id,
        SmartReminderCapability.device_id.in_(ids)).order_by(SmartReminderCapability.device_id)
        .limit(MAX_ROUTING_ROWS+1))).mappings().all() if ids else []
    study_flags = (await session.execute(select(AndroidPushToken.device_id,
        AndroidPushToken.study_reminders_enabled).where(AndroidPushToken.device_id.in_(ids))
        .order_by(AndroidPushToken.device_id).limit(MAX_ROUTING_ROWS+1))).mappings().all() if ids else []
    if any(len(rows) > MAX_ROUTING_ROWS for rows in (sessions, capabilities, study_flags)): return None, now
    facts = {"devices":[dict(r) for r in devices],"sessions":[dict(r) for r in sessions],
             "capabilities":[dict(r) for r in capabilities],"study_flags":[dict(r) for r in study_flags]}
    digest = hashlib.sha256(json.dumps(facts,sort_keys=True,separators=(",", ":"),
        default=lambda v:_utc(v).isoformat()).encode()).hexdigest()
    caps = {r["device_id"]:r for r in capabilities}
    deadline = None
    for device in devices:
        # Historical/revoked records still enter the hash and require external
        # review. Revocation alone is NEVER the proof that they are fenced.
        if device["revoked_at"] is not None: continue
        cap = caps.get(device["id"])
        if (cap is None or cap["protocol_version"] != 1 or cap["autonomous_study_disabled"] is not True or
                cap["observed_at"] is None or not _utc(cap["observed_at"]) <= now < _utc(cap["expires_at"])):
            return digest, now
        deadline = min(deadline, _utc(cap["expires_at"])) if deadline else _utc(cap["expires_at"])
    return digest, deadline


class SmartReminderRoutingService:
    def __init__(self, sessions, *, clock=None):
        self.sessions = sessions
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    async def hold(self, actor, *, expected_generation):
        if type(expected_generation) is not int or not 0 <= expected_generation < MAX_REVISION-1:
            raise SmartReminderError("routing_generation_invalid")
        async with self.sessions.begin() as session:
            pref, epoch, row = await _read_routing(session, actor)
            if (row["generation"] if row else 0) != expected_generation:
                raise SmartReminderError("routing_generation_conflict", 409)
            now = _aware_utc(self.clock())
            inventory, _ = await _android_inventory(session, actor.user_id, now)
            values = dict(state="held", generation=expected_generation+1,
                preference_revision=pref["revision"], grant_epoch=epoch, telegram_binding=_binding(actor),
                inventory_sha256=inventory, held_at=_aware_utc(self.clock()),
                verified_at=None, verified_until=None, evidence_sha256=None)
            if row is None:
                await session.execute(insert(ROUTING).values(user_id=actor.user_id, **values))
            else:
                await session.execute(update(ROUTING).where(ROUTING.c.user_id == actor.user_id).values(**values))
            await SmartReminderLifecycleService(session).invalidate(actor.user_id, reason="routing_held", advance=False)
            return values["generation"]

    async def activate(self, actor, review: RoutingReview):
        async with self.sessions.begin() as session:
            pref, epoch, row = await _read_routing(session, actor)
            now = _aware_utc(self.clock())
            inventory, fence_until = await _android_inventory(session, actor.user_id, now)
            if (row is None or row["state"] != "held" or review.user_id != actor.user_id or
                    review.generation != row["generation"] or row["telegram_binding"] != _binding(actor) or
                    row["preference_revision"] != pref["revision"] or row["grant_epoch"] != epoch or
                    inventory is None or inventory != row["inventory_sha256"] or
                    fence_until is not None and _aware_utc(review.verified_until) > fence_until or
                    not _utc(row["held_at"]) <= _aware_utc(review.verified_at) <= now < _aware_utc(review.verified_until)):
                raise SmartReminderError("routing_review_stale", 409)
            if (pref["master_enabled"] is False or pref["channels"]["telegram"]["consent"] != "on" or
                    not pref["channels"]["telegram"]["transport_available"]):
                raise SmartReminderError("telegram_study_unavailable", 409)
            await session.execute(update(ROUTING).where(ROUTING.c.user_id == actor.user_id).values(
                state="telegram", verified_at=review.verified_at, verified_until=review.verified_until,
                evidence_sha256=review.evidence_sha256))
            return review.generation


class SmartReminderTelegramService:
    def __init__(self, settings, sessions, *, calibration=None, coverage_reader=None, clock=None):
        self.settings, self.sessions, self.calibration = settings, sessions, calibration
        # A future reviewed read-only canonical feed; no production implementation
        # is installed. It must not own commit or perform provider/network IO.
        self.coverage_reader = coverage_reader
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.queue = SmartReminderShadowQueue(sessions, clock=self.clock)
        digest = hashlib.sha256(json.dumps(asdict(calibration), sort_keys=True, default=str).encode()).hexdigest()[:12] if calibration else None
        self.policy_version = TELEGRAM_VERSION+":"+digest if digest else None

    def _gate(self):
        if getattr(self.settings, "SMART_REMINDER_TELEGRAM_ENABLED", False) is not True:
            return TelegramResult("telegram_dispatch_disabled")
        if self.calibration is None:
            return TelegramResult("cadence_calibration_unconfigured")
        if self.coverage_reader is None:
            return TelegramResult("learning_coverage_unavailable")

    def _now(self):
        return _aware_utc(self.clock())

    async def _cohort(self, session, actor):
        pref, _, row = await _read_routing(session, actor)
        now = self._now()
        inventory, fence_until = await _android_inventory(session, actor.user_id, now)
        if (row is None or row["state"] != "telegram" or row["telegram_binding"] != _binding(actor) or
                inventory is None or inventory != row["inventory_sha256"] or
                fence_until is not None and now >= fence_until or
                row["verified_at"] is None or not _utc(row["verified_at"]) <= now < _utc(row["verified_until"])):
            raise SmartReminderError("telegram_cohort_unavailable", 409)
        if (pref["master_enabled"] is False or pref["channels"]["telegram"]["consent"] != "on" or
                not pref["channels"]["telegram"]["transport_available"]):
            raise SmartReminderError("telegram_study_unavailable", 409)
        return row

    @staticmethod
    async def _job(session, actor, job_id):
        return (await session.execute(select(JOB).where(
            JOB.c.user_id == actor.user_id, JOB.c.id == job_id).with_for_update())).mappings().one_or_none()

    @staticmethod
    async def _attempt(session, row):
        return (await session.execute(select(ATTEMPT).where(ATTEMPT.c.job_id == row["id"])
            .with_for_update())).mappings().all()

    @staticmethod
    def _prepared(attempt, row, now):
        return (attempt["state"] == "prepared" and attempt["started_at"] is None and
                attempt["channel"] == "telegram" and attempt["device_id"] is None and
                attempt["grant_epoch"] == row["grant_epoch"] and _utc(attempt["prepared_at"]) <= now and
                _utc(attempt["expires_at"]) == _utc(row["expires_at"]) and
                attempt["attempt_key"] == hashlib.sha256((row["id"]+":telegram:first").encode()).hexdigest())

    async def _cancel(self, session, row, reason, state="cancelled"):
        await session.execute(update(ATTEMPT).where(ATTEMPT.c.job_id == row["id"],
            ATTEMPT.c.state == "prepared", ATTEMPT.c.started_at.is_(None)).values(state="cancelled", reason_code=reason))
        result = await self.queue._close(session, row, state, reason, self._now())
        return TelegramResult(result.reason, row["id"], result.state)

    async def _fresh(self, session, actor, row, cohort, since):
        context, refused = await self.queue._fresh(session, actor, row, self._now(), since)
        if refused:
            await session.execute(update(ATTEMPT).where(ATTEMPT.c.job_id == row["id"],
                ATTEMPT.c.state == "prepared", ATTEMPT.c.started_at.is_(None)).values(
                    state="cancelled", reason_code=refused.reason))
            return TelegramResult(refused.reason, row["id"], refused.state)
        # Known legacy provider acceptance is not invisible merely because it
        # predates the Smart ledger. Preserve its observed coarse-day ownership
        # too; unknown historical outcomes still require external reconciliation.
        legacy = (await session.execute(select(CourseProgress.last_reminder_sent_at,
            CourseProgress.reminder_tz_offset).where(CourseProgress.user_id == actor.user_id))).mappings().one_or_none()
        if legacy and legacy["last_reminder_sent_at"] is not None:
            at = _utc(legacy["last_reminder_sent_at"])
            offset = reminder_tz_offset(SimpleNamespace(**legacy))
            if at > self._now() or not -12 <= offset <= 14:
                return await self._cancel(session, row, "legacy_contact_unknown")
            try:
                shift = timedelta(hours=offset)
                start = datetime.combine((at+shift).date(), time.min, timezone.utc)-shift
                end = start+timedelta(days=1)
            except OverflowError:
                return await self._cancel(session, row, "legacy_contact_unknown")
            if (_utc(row["day_start_utc"]) <= at < _utc(row["day_end_utc"]) or
                    start < _utc(row["day_end_utc"]) and end > _utc(row["day_start_utc"])):
                return await self._cancel(session, row, "legacy_study_already_attempted")
        snapshot = await SmartReminderPolicyContextService(session).load_cadence(
            actor, observed_at=self._now(), history_since=since, expected_level=row["course_key"])
        now = self._now()
        coverage = await self.coverage_reader(session, actor, since, now)
        if coverage is not None and (not isinstance(coverage, LearningCoverage) or
                coverage.user_id != actor.user_id or _aware_utc(coverage.observed_at) != now):
            raise SmartReminderError("learning_coverage_invalid", 409)
        # All canonical learning writers serialize on the held User lock. Recheck
        # the current clock after read IO; crossing day/quiet/expiry stays a veto.
        now = self._now()
        snapshot = replace(snapshot, policy=replace(snapshot.policy, observed_at=now),
                           intents=tuple(j for j in snapshot.intents if j.job_id != row["id"]),
                           learning_complete_since=coverage.complete_since if coverage else None)
        decision = evaluate_cadence(snapshot, calibration=self.calibration, allow_elapsed_time=True)
        if now >= _utc(row["expires_at"]):
            return await self._cancel(session, row, "telegram_expired", "expired")
        if now >= _utc(cohort["verified_until"]):
            return await self._cancel(session, row, "routing_review_expired")
        if decision.reason != "shadow_candidate":
            return await self._cancel(session, row, decision.reason)

    async def prepare(self, actor, *, expires_at, history_since, expected_level):
        if refused := self._gate(): return refused
        # Do not reserve for an unreviewed cohort. Close this transaction before
        # entering the existing queue's transaction, then revalidate on adoption.
        async with self.sessions.begin() as session:
            await self._cohort(session, actor)
        reserved = await self.queue.reserve(actor, expires_at=expires_at, history_since=history_since, expected_level=expected_level)
        if not reserved.job_id: return TelegramResult(reserved.reason)
        async with self.sessions.begin() as session:
            cohort = await self._cohort(session, actor)
            row = await self._job(session, actor, reserved.job_id)
            if row["policy_version"] == self.policy_version:
                return TelegramResult("telegram_already_planned", row["id"], row["state"])
            if (row["policy_version"] != QUEUE_VERSION or row["state"] != "shadow" or
                    row["lease_token"] is not None or await self._attempt(session, row)):
                return TelegramResult("telegram_day_not_adoptable", row["id"], row["state"])
            if refused := await self._fresh(session, actor, row, cohort, history_since): return refused
            changed = await session.execute(update(JOB).where(JOB.c.id == row["id"], JOB.c.state == "shadow",
                JOB.c.policy_version == QUEUE_VERSION, JOB.c.lease_token.is_(None)).values(
                    state="pending", policy_version=self.policy_version, selected_channel="telegram",
                    reason_code="telegram_planned", updated_at=self._now()))
            if changed.rowcount != 1: return TelegramResult("telegram_day_not_adoptable", row["id"])
            return TelegramResult("telegram_planned", row["id"], "pending")

    async def claim(self, actor, job_id, *, history_since, lease_for):
        if refused := self._gate(): return refused
        if not isinstance(lease_for, timedelta) or lease_for <= timedelta(0):
            raise ValueError("Explicit positive technical lease required")
        async with self.sessions.begin() as session:
            cohort = await self._cohort(session, actor)
            row = await self._job(session, actor, job_id)
            now = self._now()
            if row is None: return TelegramResult("telegram_job_not_found")
            if row["policy_version"] != self.policy_version or row["selected_channel"] != "telegram":
                return TelegramResult("foreign_job_policy", job_id, row["state"])
            attempts = await self._attempt(session, row)
            if len(attempts) > 1 or any(not self._prepared(a, row, now) for a in attempts):
                return TelegramResult("telegram_attempt_not_replayable", job_id, row["state"])
            if row["state"] not in {"pending", "claimed"}:
                return TelegramResult("telegram_job_terminal", job_id, row["state"])
            if now < _utc(row["scheduled_at"]): return TelegramResult("telegram_not_due", job_id, row["state"])
            if row["lease_token"] and _utc(row["lease_expires_at"]) > now:
                return TelegramResult("telegram_lease_busy", job_id, row["state"])
            if refused := await self._fresh(session, actor, row, cohort, history_since): return refused
            now = self._now()
            until = now + min(lease_for, _utc(row["expires_at"])-now, _utc(cohort["verified_until"])-now)
            if until <= now: return await self._cancel(session, row, "telegram_expired", "expired")
            token = str(uuid4())
            changed = await session.execute(update(JOB).where(JOB.c.id == job_id,
                JOB.c.user_id == actor.user_id, JOB.c.state == row["state"],
                JOB.c.lease_token == row["lease_token"]).values(
                state="claimed", lease_token=token, lease_expires_at=until, updated_at=now))
            if changed.rowcount != 1: return TelegramResult("telegram_lease_busy", job_id)
            if not attempts:
                await session.execute(insert(ATTEMPT).values(id=str(uuid4()), job_id=job_id,
                    attempt_key=hashlib.sha256((job_id+":telegram:first").encode()).hexdigest(),
                    channel="telegram", device_id=None, grant_epoch=row["grant_epoch"], state="prepared",
                    prepared_at=now, expires_at=row["expires_at"], reason_code="telegram_prepared"))
            return TelegramResult("telegram_claimed", job_id, "claimed", token, until, cohort["generation"])

    async def dispatch(self, actor, lease, send, *, history_since):
        if refused := self._gate(): return refused
        async with self.sessions.begin() as session:
            cohort = await self._cohort(session, actor)
            row = await self._job(session, actor, lease.job_id)
            now = self._now()
            if (row is None or row["policy_version"] != self.policy_version or row["selected_channel"] != "telegram" or
                    row["state"] != "claimed" or not lease.token or row["lease_token"] != lease.token or
                    row["lease_expires_at"] is None or _utc(row["lease_expires_at"]) <= now or
                    cohort["generation"] != lease.generation):
                return TelegramResult("telegram_lease_lost", lease.job_id)
            attempts = await self._attempt(session, row)
            if len(attempts) != 1 or not self._prepared(attempts[0], row, now):
                return TelegramResult("telegram_attempt_not_replayable", lease.job_id)
            if refused := await self._fresh(session, actor, row, cohort, history_since): return refused
            now = self._now()
            if _utc(row["lease_expires_at"]) <= now:
                return TelegramResult("telegram_lease_lost", lease.job_id)
            attempt_id = attempts[0]["id"]
            changed = await session.execute(update(ATTEMPT).where(ATTEMPT.c.id == attempt_id, ATTEMPT.c.state == "prepared",
                ATTEMPT.c.started_at.is_(None)).values(state="in_flight", started_at=now, reason_code="telegram_started"))
            if changed.rowcount != 1: return TelegramResult("telegram_attempt_not_replayable", lease.job_id)
            envelope = TelegramEnvelope(actor.user_id, row["id"], actor.telegram_id,
                                        row["course_key"], row["lesson_order"], row["local_day"].isoformat())
        # Authorization is committed. OFF/kill after this boundary cannot recall
        # provider IO; the durable marker forbids every retry/alternate.
        try:
            receipt = await send(envelope)
        except Exception:
            return await self._finish(actor.user_id, lease.job_id, attempt_id, accepted=False)
        accepted = type(getattr(receipt, "message_id", None)) is int and receipt.message_id > 0
        return await self._finish(actor.user_id, lease.job_id, attempt_id, accepted=accepted)

    async def _finish(self, user_id, job_id, attempt_id, *, accepted):
        # Record already-authorized external facts even after OFF/block/hold;
        # never run eligibility again to erase an uncertain provider boundary.
        async with self.sessions.begin() as session:
            await session.execute(select(User.id).where(User.id == user_id).with_for_update())
            attempt = (await session.execute(select(ATTEMPT).join(JOB, JOB.c.id == ATTEMPT.c.job_id).where(
                JOB.c.user_id == user_id, JOB.c.id == job_id, ATTEMPT.c.id == attempt_id)
                .with_for_update())).mappings().one_or_none()
            if attempt is None: return TelegramResult("telegram_record_missing", job_id)
            if attempt["state"] != "in_flight":
                return TelegramResult("telegram_outcome_already_recorded", job_id)
            now = self._now()
            state = "provider_accepted" if accepted else "unknown"
            await session.execute(update(ATTEMPT).where(ATTEMPT.c.id == attempt_id,
                ATTEMPT.c.state == "in_flight").values(state=state, resolved_at=now, reason_code="telegram_"+state))
            await session.execute(update(JOB).where(JOB.c.user_id == user_id, JOB.c.id == job_id).values(
                state=state, lease_token=None, lease_expires_at=None, updated_at=now, reason_code="telegram_"+state))
            if accepted:
                await session.execute(update(CourseProgress).where(CourseProgress.user_id == user_id).values(last_reminder_sent_at=now))
            return TelegramResult("telegram_"+state, job_id, state)

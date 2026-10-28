"""Durable shadow evaluation ownership, never a delivery/endpoint grant.

Own short transactions; commit/close before an optional observational sink.
No API, scheduler, provider adapter or runtime calibration enables this queue.
"""
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import insert, or_, select, update

from app.db.models.smart_reminder import SmartReminderAttempt, SmartReminderJob
from app.db.models.user import User
from app.services.smart_reminder_cadence import evaluate_cadence
from app.services.smart_reminder_coordination import read_d1_scope
from app.services.smart_reminder_lifecycle import EXTERNAL_ATTEMPTS
from app.services.smart_reminder_policy import _aware_utc, evaluate
from app.services.smart_reminder_policy_context import SmartReminderPolicyContextService
from app.services.smart_reminder_preferences import SmartReminderError, SmartReminderPreferencesService, _utc


QUEUE_VERSION = "smart-queue-shadow-v1"
JOB = SmartReminderJob.__table__
ATTEMPT = SmartReminderAttempt.__table__
MAX_DUE_BATCH = 128  # Technical bounded work, not cadence/retention policy.


@dataclass(frozen=True)
class ShadowHandle:
    user_id: int
    job_id: str


@dataclass(frozen=True)
class ShadowResult:
    reason: str
    job_id: str | None = None
    state: str | None = None
    policy_reason: str | None = None
    lease_token: str | None = None
    lease_expires_at: datetime | None = None
    dispatch_allowed: bool = field(default=False, init=False)


def day_window(zone_name, local_day):
    """Freeze actual IANA midnight instants, never UTC start plus 24 hours."""
    zone = ZoneInfo(zone_name)
    day = date.fromisoformat(local_day)
    start = datetime.combine(day, time.min, zone).astimezone(timezone.utc)
    end = datetime.combine(day + timedelta(days=1), time.min, zone).astimezone(timezone.utc)
    if start >= end:
        raise ValueError("Local calendar day has no positive UTC interval")
    return start, end


class SmartReminderShadowQueue:
    def __init__(self, sessions, *, clock=None):
        self.sessions = sessions
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def _now(self):
        return _aware_utc(self.clock())

    @staticmethod
    async def _job(session, actor, job_id):
        # P1 locks User then preference first; no job-first claim/deadlock.
        await SmartReminderPreferencesService(session).read(actor)
        return (await session.execute(select(JOB).where(
            JOB.c.id == job_id, JOB.c.user_id == actor.user_id).with_for_update())).mappings().one_or_none()

    @staticmethod
    def _result(row, reason, *, policy_reason=None):
        return ShadowResult(reason, row["id"], row["state"], policy_reason)

    @staticmethod
    async def _close(session, row, state, reason, now):
        changed = await session.execute(update(JOB).where(
            JOB.c.id == row["id"], JOB.c.user_id == row["user_id"], JOB.c.state == row["state"],
            JOB.c.lease_token == row["lease_token"],
        ).values(
            state=state, reason_code=reason, lease_token=None, lease_expires_at=None, updated_at=now))
        if changed.rowcount != 1:
            return ShadowResult("shadow_lease_lost", row["id"], row["state"])
        return ShadowResult(reason, row["id"], state, reason)

    async def _attempt_guard(self, session, row, now):
        external = await session.scalar(select(ATTEMPT.c.id).where(
            ATTEMPT.c.job_id == row["id"], or_(ATTEMPT.c.started_at.is_not(None),
                                             ATTEMPT.c.state.in_(EXTERNAL_ATTEMPTS))).limit(1))
        if external is not None:
            # Never turn uncertain or already accepted external IO back into
            # pending/shadow. Preserve every attempt fact exactly as stored.
            state = row["state"] if row["state"] in {"provider_accepted", "unknown", "completed"} else "unknown"
            return await self._close(session, row, state, "external_outcome_preserved", now)
        any_attempt = await session.scalar(select(ATTEMPT.c.id).where(ATTEMPT.c.job_id == row["id"]).limit(1))
        if any_attempt is not None:
            await session.execute(update(ATTEMPT).where(
                ATTEMPT.c.job_id == row["id"], ATTEMPT.c.state == "prepared").values(
                    state="cancelled", reason_code="shadow_attempt_present"))
            return await self._close(session, row, "cancelled", "shadow_attempt_present", now)

    async def reserve(self, actor, *, history_since, expected_level, expires_at):
        expiry = _aware_utc(expires_at)
        since = _aware_utc(history_since)
        async with self.sessions.begin() as session:
            await SmartReminderPreferencesService(session).read(actor)
            now = self._now()  # The User lock may have waited: never reuse a pre-lock clock.
            d1 = await read_d1_scope(session, actor.user_id, now)
            if d1.reason(now):
                return ShadowResult(d1.reason(now))
            snapshot = await SmartReminderPolicyContextService(session).load_cadence(
                actor, observed_at=now, history_since=since, expected_level=expected_level)
            decision = evaluate(snapshot.policy)
            if not decision.candidate:
                return ShadowResult(decision.reason)
            start, end = day_window(snapshot.policy.timezone_name, decision.local_day)
            if since > start:
                return ShadowResult("queue_history_incomplete")
            if not decision.scheduled_at < expiry <= end:
                return ShadowResult("queue_expiry_outside_day")
            existing_query = select(JOB).where(JOB.c.user_id == actor.user_id, JOB.c.category == "study", or_(
                JOB.c.local_day == date.fromisoformat(decision.local_day),
                (JOB.c.day_start_utc < end) & (JOB.c.day_end_utc > start)))
            existing = (await session.execute(existing_query.with_for_update().limit(1))).mappings().first()
            if existing is not None:
                return self._result(existing, "account_day_already_owned")
            cadence = evaluate_cadence(snapshot)
            values = dict(
                id=str(uuid4()), user_id=actor.user_id, category="study",
                local_day=date.fromisoformat(decision.local_day), timezone_name=snapshot.policy.timezone_name,
                day_start_utc=start, day_end_utc=end, scheduled_at=decision.scheduled_at, expires_at=expiry,
                state="shadow", policy_version=QUEUE_VERSION, preference_revision=decision.revision,
                grant_epoch=decision.grant_epoch, course_key=decision.level,
                lesson_order=decision.target_lesson_order, reason_code=cadence.reason,
                selected_channel=None, selected_device_id=None, created_at=now, updated_at=now,
            )
            # User locking serializes PostgreSQL writers; the unique constraint
            # is the final refusal guard for an inconsistent external writer.
            # No savepoint as first write: SQLite legacy transaction control
            # could otherwise release it before the outer transaction commits.
            await session.execute(insert(JOB).values(**values))
            return ShadowResult("shadow_reserved", values["id"], "shadow", cadence.reason)

    async def due(self, *, limit):
        if type(limit) is not int or not 1 <= limit <= MAX_DUE_BATCH:
            raise ValueError("A bounded due batch is required")
        now = self._now()
        async with self.sessions() as session:
            rows = (await session.execute(select(JOB.c.user_id, JOB.c.id).where(
                JOB.c.policy_version == QUEUE_VERSION, JOB.c.state == "shadow", JOB.c.scheduled_at <= now,
                JOB.c.expires_at > now,
                or_(JOB.c.lease_token.is_(None), JOB.c.lease_expires_at <= now),
            ).order_by(JOB.c.scheduled_at, JOB.c.id).limit(limit))).all()
            return tuple(ShadowHandle(row.user_id, row.id) for row in rows)

    async def expire_due(self, *, limit):
        """Internal expiry-only maintenance; no client/session authority minted."""
        if type(limit) is not int or not 1 <= limit <= MAX_DUE_BATCH:
            raise ValueError("A bounded expiry batch is required")
        now = self._now()
        async with self.sessions() as session:
            handles = (await session.execute(select(JOB.c.user_id, JOB.c.id).where(
                JOB.c.policy_version == QUEUE_VERSION, JOB.c.state == "shadow", JOB.c.expires_at <= now,
            ).order_by(JOB.c.scheduled_at, JOB.c.id).limit(limit))).all()
        results = []
        for handle in handles:
            async with self.sessions.begin() as session:
                await session.execute(select(User.id).where(User.id == handle.user_id).with_for_update())
                now = self._now()
                row = (await session.execute(select(JOB).where(
                    JOB.c.id == handle.id, JOB.c.user_id == handle.user_id).with_for_update())).mappings().one_or_none()
                if (row is None or row["policy_version"] != QUEUE_VERSION or row["state"] != "shadow"
                        or _utc(row["expires_at"]) > now):
                    continue
                guarded = await self._attempt_guard(session, row, now)
                results.append(guarded or await self._close(session, row, "expired", "shadow_expired", now))
        return tuple(results)

    async def _fresh(self, session, actor, row, now, since):
        d1 = await read_d1_scope(session, actor.user_id, now)
        if d1.reason(now):
            return None, await self._close(session, row, "cancelled", d1.reason(now), now)
        if _aware_utc(since) > _utc(row["day_start_utc"]):
            return None, await self._close(session, row, "cancelled", "queue_history_incomplete", now)
        context = await SmartReminderPolicyContextService(session).load(
            actor, observed_at=now, history_since=since, expected_level=row["course_key"])
        if (context.revision != row["preference_revision"] or context.grant_epoch != row["grant_epoch"]):
            return None, await self._close(session, row, "cancelled", "shadow_preference_changed", now)
        # Retain NOW's verified goal/activity, never rewind to the old clock to
        # make a late tick pass. Frozen expiry is checked by the caller.
        decision = evaluate(context, allow_elapsed_time=True)
        if not decision.candidate:
            return None, await self._close(session, row, "cancelled", decision.reason, now)
        if (context.timezone_name != row["timezone_name"] or decision.local_day != row["local_day"].isoformat()
                or decision.scheduled_at != _utc(row["scheduled_at"])
                or decision.target_lesson_order != row["lesson_order"]):
            return None, await self._close(session, row, "cancelled", "shadow_context_changed", now)
        return context, None

    async def claim(self, actor, job_id, *, history_since, lease_for):
        if not isinstance(lease_for, timedelta) or lease_for <= timedelta(0):
            raise ValueError("Explicit positive technical lease duration required")
        async with self.sessions.begin() as session:
            row = await self._job(session, actor, job_id)
            now = self._now()
            if row is None:
                return ShadowResult("shadow_job_not_found")
            if row["policy_version"] != QUEUE_VERSION:
                return self._result(row, "foreign_job_policy")
            guarded = await self._attempt_guard(session, row, now)
            if guarded:
                return guarded
            if row["state"] != "shadow":
                return self._result(row, "shadow_job_terminal")
            if now >= _utc(row["expires_at"]):
                return await self._close(session, row, "expired", "shadow_expired", now)
            if now < _utc(row["scheduled_at"]):
                return self._result(row, "shadow_not_due")
            if row["lease_token"] and _utc(row["lease_expires_at"]) > now:
                return self._result(row, "shadow_lease_busy")
            context, refused = await self._fresh(session, actor, row, now, history_since)
            if refused:
                return refused
            now = self._now()  # Validation IO may also have crossed a deadline.
            if now >= _utc(row["expires_at"]):
                return await self._close(session, row, "expired", "shadow_expired", now)
            final = evaluate(replace(context, observed_at=now), allow_elapsed_time=True)
            if not final.candidate:
                return await self._close(session, row, "cancelled", final.reason, now)
            token = str(uuid4())
            until = now + min(lease_for, _utc(row["expires_at"]) - now)
            changed = await session.execute(update(JOB).where(
                JOB.c.id == job_id, JOB.c.user_id == actor.user_id, JOB.c.state == "shadow",
                or_(JOB.c.lease_token.is_(None), JOB.c.lease_expires_at <= now),
            ).values(
                lease_token=token, lease_expires_at=until, updated_at=now))
            if changed.rowcount != 1:
                return self._result(row, "shadow_lease_busy")
            return ShadowResult("shadow_claimed", job_id, "shadow", row["reason_code"], token, until)

    async def finish(self, actor, job_id, token, *, history_since):
        async with self.sessions.begin() as session:
            row = await self._job(session, actor, job_id)
            now = self._now()
            if row is None:
                return ShadowResult("shadow_job_not_found")
            if row["policy_version"] != QUEUE_VERSION:
                return self._result(row, "foreign_job_policy")
            guarded = await self._attempt_guard(session, row, now)
            if guarded:
                return guarded
            if row["state"] != "shadow" or not token or row["lease_token"] != token:
                return self._result(row, "shadow_lease_lost")
            if now >= _utc(row["expires_at"]):
                return await self._close(session, row, "expired", "shadow_expired", now)
            if row["lease_expires_at"] is None or _utc(row["lease_expires_at"]) <= now:
                return self._result(row, "shadow_lease_lost")
            _, refused = await self._fresh(session, actor, row, now, history_since)
            if refused:
                return refused
            snapshot = await SmartReminderPolicyContextService(session).load_cadence(
                actor, observed_at=now, history_since=history_since, expected_level=row["course_key"])
            # Cadence gates creation of a NEW intent; this job already owns its
            # day. Exclude only itself for the observational cadence readout.
            snapshot = replace(snapshot, intents=tuple(j for j in snapshot.intents if j.job_id != job_id))
            now = self._now()
            if now >= _utc(row["expires_at"]):
                return await self._close(session, row, "expired", "shadow_expired", now)
            if _utc(row["lease_expires_at"]) <= now:
                return self._result(row, "shadow_lease_lost")
            snapshot = replace(snapshot, policy=replace(snapshot.policy, observed_at=now))
            final = evaluate(snapshot.policy, allow_elapsed_time=True)
            if not final.candidate:
                return await self._close(session, row, "cancelled", final.reason, now)
            cadence = evaluate_cadence(snapshot, allow_elapsed_time=True)
            closed = await self._close(session, row, "completed", cadence.reason, now)
            if closed.reason == "shadow_lease_lost":
                return closed
            return ShadowResult("shadow_evaluated", job_id, "completed", cadence.reason)

    async def run_one(self, actor, job_id, *, history_since, lease_for, observe=None):
        claimed = await self.claim(actor, job_id, history_since=history_since, lease_for=lease_for)
        if claimed.reason != "shadow_claimed":
            return claimed
        finished = await self.finish(actor, job_id, claimed.lease_token, history_since=history_since)
        # Both SQL contexts have exited and COMMITTED. This is observational
        # output only, with no provider/endpoint grant; never retry on sink error.
        if observe is not None and finished.reason == "shadow_evaluated":
            await observe(finished)
        return finished

    async def drain(self, actor_for, *, history_since, lease_for, limit, observe=None):
        await self.expire_due(limit=limit)
        results = []
        for handle in await self.due(limit=limit):
            try:
                actor = await actor_for(handle.user_id)
                if actor.user_id != handle.user_id:
                    results.append(ShadowResult("shadow_actor_owner_mismatch"))
                    continue
                results.append(await self.run_one(actor, handle.job_id, history_since=history_since,
                                                  lease_for=lease_for, observe=observe))
            except SmartReminderError as exc:
                results.append(ShadowResult(exc.code))
            except Exception:
                # No raw exceptions/credentials in a persisted or public report.
                # A claim crash retries after lease; a sink crash does not.
                results.append(ShadowResult("shadow_worker_failed"))
        return tuple(results)

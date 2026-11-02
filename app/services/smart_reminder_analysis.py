"""Source-derived analysis only; never authority, learning or display proof.

Capture owns a separate transaction after delivery commits. Optional source
hooks/retention are disabled by default. Retention never deletes source evidence.
"""
from datetime import datetime, timedelta, timezone
import asyncio
import hashlib
import logging
import math

from sqlalchemy import delete, func, or_, select, text, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.models.account_deletion import AccountDeletionRequest
from app.db.models.smart_reminder import SmartReminderAndroidGrant, SmartReminderAttempt, SmartReminderJob
from app.db.models.smart_reminder_analysis import SmartReminderAnalysisEvent, SmartReminderAnalysisMonthly
from app.db.models.user import User
from app.services.smart_reminder_policy import _aware_utc
from app.services.smart_reminder_preferences import _utc

EVENT = SmartReminderAnalysisEvent.__table__
MONTHLY = SmartReminderAnalysisMonthly.__table__
RAW_RETENTION = timedelta(days=90)  # Owner D21; not operational grant/day/OFF retention.
MAX_BATCH = 128  # Bounded work, not product cadence or experiment calibration.
UNAVAILABLE_OUTCOMES = ("verified_shown", "read", "opened", "attributed_server_learning")
logger = logging.getLogger(__name__)


def oldest_month(now):
    """Current UTC month and eleven earlier buckets; never unbounded history."""
    serial = now.year * 12 + now.month - 1 - 11
    year, month = divmod(serial, 12)
    return now.date().replace(year=year, month=month + 1, day=1)


class SmartReminderAnalysisService:
    def __init__(self, sessions, *, clock=None):
        self.sessions = sessions
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def now(self):
        return _aware_utc(self.clock())

    @staticmethod
    def _insert(session, table):
        dialect = session.bind.dialect.name
        if dialect not in {"sqlite", "postgresql"}:
            raise RuntimeError("Unsupported Smart analysis dialect")
        return (pg_insert if dialect == "postgresql" else sqlite_insert)(table)

    async def _fact(self, session, job, source_id, stage, at, channel, now):
        if at is None or channel not in {"none", "telegram", "android"}:
            return 0
        at = _utc(at)
        if not now - RAW_RETENTION < at <= now:
            return 0  # Expired replay cannot resurrect detail or increment totals.
        key = hashlib.sha256(("smart-analysis-v1:" + source_id + ":" + stage).encode()).hexdigest()
        inserted = await session.scalar(self._insert(session, EVENT).values(user_id=job["user_id"],
            event_key=key, job_id=job["id"], stage=stage, channel=channel,
            reason_code="stored_" + stage, occurred_at=at, expires_at=at + RAW_RETENTION)
            .on_conflict_do_nothing(index_elements=["user_id", "event_key"]).returning(EVENT.c.event_key))
        if inserted is None:
            return 0
        month = at.date().replace(day=1)
        await session.execute(self._insert(session, MONTHLY).values(month=month, stage=stage,
            channel=channel, fact_count=1).on_conflict_do_update(index_elements=["month", "stage", "channel"],
                set_={"fact_count": MONTHLY.c.fact_count + 1}))
        return 1

    async def capture_job(self, user_id, job_id):
        """Internal committed-source capture. No client event/outcome input."""
        async with self.sessions.begin() as session:
            with session.no_autoflush:
                owner = await session.scalar(select(User.id).where(User.id == user_id).with_for_update())
                if owner is None:
                    return 0
                pending = await session.scalar(select(AccountDeletionRequest.id).where(
                    AccountDeletionRequest.status == "submitted", or_(AccountDeletionRequest.user_id == owner,
                        AccountDeletionRequest.active_user_id == owner)).limit(1))
                if pending is not None:
                    return 0
                job = (await session.execute(select(SmartReminderJob.__table__).where(
                    SmartReminderJob.id == job_id, SmartReminderJob.user_id == owner).with_for_update())).mappings().one_or_none()
                if job is None:
                    return 0
                # Shadow evaluation is not real delivery. Unknown/new policy
                # families require their own reviewed source adapter.
                channel = job["selected_channel"]
                if channel not in {"android", "telegram"} or not job["policy_version"].startswith(
                        "smart-" + channel + "-v1:"):
                    return 0
                attempts = (await session.execute(select(SmartReminderAttempt.__table__).where(
                    SmartReminderAttempt.job_id == job_id).order_by(SmartReminderAttempt.id).with_for_update())).mappings().all()
                grants = (await session.execute(select(SmartReminderAndroidGrant.__table__).where(
                    SmartReminderAndroidGrant.job_id == job_id, SmartReminderAndroidGrant.user_id == owner))).mappings().all()
                now = self.now()  # Resample after waiting on the canonical owner.
                count = await self._fact(session, job, job_id, "reserved", job["created_at"],
                    job["selected_channel"] or "none", now)
                if job["state"] in {"cancelled", "expired"}:
                    count += await self._fact(session, job, job_id, job["state"], job["updated_at"],
                        job["selected_channel"] or "none", now)
                for attempt in attempts:
                    count += await self._fact(session, job, attempt["id"], "in_flight",
                        attempt["started_at"], attempt["channel"], now)
                    stage = {"provider_accepted": "provider_accepted", "unknown": "outcome_unknown",
                        "definite_failure": "definite_failure"}.get(attempt["state"])
                    if attempt["channel"] == "android":
                        grant = next((g for g in grants if g["attempt_id"] == attempt["id"] and
                            g["device_id"] == attempt["device_id"] and g["receipt_id"] is not None), None)
                        if grant is not None:
                            expected = {"client_declined_before_post": "confirmed_not_displayed",
                                "client_posted_unverified": "client_posted_unverified", "client_outcome_unknown": "unknown"}
                            if expected.get(grant["receipt_outcome"]) == attempt["state"]:
                                stage = "outcome_unknown" if attempt["state"] == "unknown" else attempt["state"]
                                count += await self._fact(session, job, attempt["id"], stage,
                                    grant["received_at"], "android", now)
                                continue
                    if stage is not None:
                        count += await self._fact(session, job, attempt["id"], stage,
                            attempt["resolved_at"], attempt["channel"], now)
                return count

    async def retention(self, *, execute=False, limit=128):
        """One explicit bounded page; default returns anonymous counts only."""
        if type(execute) is not bool or type(limit) is not int or not 1 <= limit <= MAX_BATCH:
            raise ValueError("Bounded Smart analysis retention limit required")
        async with self.sessions.begin() as session:
            if session.bind.dialect.name == "postgresql":
                if not execute:
                    await session.execute(text("SET TRANSACTION READ ONLY"))
                await session.execute(text("SET LOCAL statement_timeout = '5000'"))
            now = self.now()
            expired = EVENT.c.expires_at <= now
            old_month = MONTHLY.c.month < oldest_month(now)
            counts = {"expired_raw": await session.scalar(select(func.count()).select_from(EVENT).where(expired)),
                "expired_monthly": await session.scalar(select(func.count()).select_from(MONTHLY).where(old_month)),
                "removed_raw": 0, "removed_monthly": 0, "mode": "purge" if execute else "count_only"}
            if execute:
                # Delete only selected expired analysis keys. No source rows,
                # user lock or lock-order inversion with delivery/purge writers.
                keys = select(EVENT.c.user_id, EVENT.c.event_key).where(expired).order_by(
                    EVENT.c.expires_at, EVENT.c.user_id, EVENT.c.event_key).limit(limit)
                months = select(MONTHLY.c.month, MONTHLY.c.stage, MONTHLY.c.channel).where(old_month).order_by(
                    MONTHLY.c.month, MONTHLY.c.stage, MONTHLY.c.channel).limit(limit)
                counts["removed_raw"] = (await session.execute(delete(EVENT).where(
                    tuple_(EVENT.c.user_id, EVENT.c.event_key).in_(keys)))).rowcount
                counts["removed_monthly"] = (await session.execute(delete(MONTHLY).where(
                    tuple_(MONTHLY.c.month, MONTHLY.c.stage, MONTHLY.c.channel).in_(months)))).rowcount
            return counts


class SmartReminderAnalysisObserver:
    """Bounded optional observation; no caller transaction or provider IO."""

    def __init__(self, settings, sessions, *, clock=None, timeout=2, interval=60, batch=128):
        if (any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0
                for v in (timeout, interval)) or type(batch) is not int or not 1 <= batch <= MAX_BATCH):
            raise ValueError("Positive bounded analysis worker settings required")
        self.settings = settings
        self.service = SmartReminderAnalysisService(sessions, clock=clock)
        self.timeout, self.interval, self.batch = timeout, interval, batch

    @property
    def enabled(self):
        return getattr(self.settings, "SMART_REMINDER_ANALYSIS_ENABLED", False) is True

    async def capture_job(self, user_id, job_id):
        if not self.enabled:
            return None
        try:
            return await asyncio.wait_for(self.service.capture_job(user_id, job_id), timeout=self.timeout)
        except Exception:
            # No exception/SQL/actor/credential content; missing capture is not
            # a measured zero. Cancellation remains cancellation.
            logger.warning("Smart analysis capture unavailable")
            return None

    async def tick(self):
        if not self.enabled:
            return None
        return await asyncio.wait_for(self.service.retention(execute=True, limit=self.batch), timeout=self.timeout)

    async def run_retention(self):
        while self.enabled:
            try:
                await self.tick()
            except Exception:
                logger.warning("Smart analysis retention unavailable")
            await asyncio.sleep(self.interval)

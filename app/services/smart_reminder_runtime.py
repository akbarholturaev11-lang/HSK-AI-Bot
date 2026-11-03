"""Explicit reviewed-cohort runtime; disabled by default in production.

Supplied readers/transport are privileged dependencies, never client evidence.
This module does not establish fencing, complete learning or live calibration.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from functools import partial
import logging
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select

from app.db.models.smart_reminder import SmartReminderRouting
from app.db.models.user import User
from app.services.smart_reminder_android import SmartReminderAndroidService, read_android_admission
from app.services.smart_reminder_cadence import OBSERVED_RULES
from app.services.smart_reminder_planner import PlanningResult, SmartReminderPlanner
from app.services.smart_reminder_policy import _aware_utc, day_window
from app.services.smart_reminder_policy_context import read_observed_learning
from app.services.smart_reminder_preferences import SmartReminderPreferencesService, _utc
from app.services.smart_reminder_shadow_queue import JOB
from app.services.smart_reminder_shadow_worker import SmartReminderShadowWorker
from app.services.smart_reminder_telegram_content import send_telegram_content


logger = logging.getLogger(__name__)


class SmartReminderRuntime:
    def __init__(self, settings, sessions, *, enabled=False, calibration=None,
                 history_window=None, coverage_reader=None, android_admission_reader=None,
                 telegram_send=None, clock=None, interval=60, timeout=30, batch=16):
        if (interval <= 0 or timeout <= 0 or type(batch) is not int or not 1 <= batch <= 128 or
                history_window is not None and (not isinstance(history_window, timedelta) or history_window <= timedelta(0))):
            raise ValueError('Positive bounded runtime settings required')
        self.settings, self.sessions, self.enabled = settings, sessions, enabled
        self.calibration, self.history_window = calibration, history_window
        self.coverage_reader, self.android_admission_reader = coverage_reader, android_admission_reader
        self.telegram_send = telegram_send
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.interval, self.timeout, self.batch = interval, timeout, batch
        self._cursor, self._ticking = 0, asyncio.Lock()
        self._host = None
        self._actors = SmartReminderShadowWorker(settings, sessions, clock=self.clock)

    def bind(self, app):
        if self._host is not None and self._host is not app:
            raise ValueError('Runtime already belongs to another host')
        self._host = app

    @property
    def telegram_ready(self):
        return callable(self.telegram_send) and getattr(self.settings, 'SMART_REMINDER_TELEGRAM_ENABLED', False) is True

    @property
    def ready(self):
        return (self.enabled is True and self.calibration is not None and self.history_window is not None and
                callable(self.coverage_reader) and (callable(self.android_admission_reader) or self.telegram_ready) and
                (self._host is None or getattr(self._host.state, 'smart_reminder_runtime', None) is self))

    async def _coverage(self, *args):
        if not self.ready: return None
        result = await self.coverage_reader(*args)
        return result if self.ready else None

    async def _admission(self, *args):
        if not self.ready or not callable(self.android_admission_reader): return None
        result = await self.android_admission_reader(*args)
        return result if self.ready else None

    def android(self, session):
        # Original receipts remain available even when new issuance is disabled.
        return SmartReminderAndroidService(session, enabled=self.ready,
            calibration=self.calibration, clock=self.clock, coverage_reader=self._coverage,
            admission_reader=self._admission if callable(self.android_admission_reader) else None)

    def _planner(self):
        return SmartReminderPlanner(self.settings, self.sessions, enabled=self.ready,
            calibration=self.calibration, coverage_reader=self._coverage, clock=self.clock,
            android_admission_reader=self._admission if callable(self.android_admission_reader) else None)

    async def _page(self):
        now = _aware_utc(self.clock())
        routing = SmartReminderRouting
        query = select(routing.user_id).where(routing.verified_at <= now, routing.verified_until > now,
            or_(and_(routing.state == 'held', callable(self.android_admission_reader)),
                and_(routing.state == 'telegram', self.telegram_ready))).order_by(routing.user_id).limit(self.batch)
        async with self.sessions() as session:
            rows = (await session.scalars(query.where(routing.user_id > self._cursor))).all()
            if not rows and self._cursor:
                rows = (await session.scalars(query)).all()
        return rows

    async def _account(self, user_id):
        if not self.ready: return PlanningResult('runtime_disabled')
        actor = await self._actors.actor_for(user_id)
        planner = self._planner()
        now = _aware_utc(self.clock())
        since = now - self.history_window
        async with self.sessions.begin() as session:
            pref = await SmartReminderPreferencesService(session).read(actor)
            level = await session.scalar(select(User.level).where(User.id == user_id))
            reviewed_until = await session.scalar(select(SmartReminderRouting.verified_until).where(
                SmartReminderRouting.user_id == user_id))
            versions = (self.android(session).policy_version, planner.telegram.policy_version)
            # Existing due work must not depend on another successful reserve:
            # reserve intentionally refuses a newly requested time in the past.
            pending = (await session.execute(select(JOB).where(JOB.c.user_id == user_id,
                JOB.c.category == 'study', JOB.c.state.in_(('pending', 'claimed')),
                JOB.c.policy_version.in_(versions), JOB.c.expires_at > self.clock(),
                JOB.c.selected_channel.in_(('android', 'telegram')))
                .order_by(JOB.c.scheduled_at, JOB.c.id).limit(1))).mappings().first()
        if not self.ready: return PlanningResult('runtime_disabled')
        if pending is not None:
            result = PlanningResult('already_planned', pending['id'], pending['selected_channel'], pending['selected_device_id'])
        else:
            now = _aware_utc(self.clock())
            zone = pref['timezone_name']
            if not zone or reviewed_until is None: return PlanningResult('planner_review_unavailable')
            _, end = day_window(zone, now.astimezone(ZoneInfo(zone)).date().isoformat())
            expiry = min(end, _utc(reviewed_until))
            if expiry <= now: return PlanningResult('planner_review_unavailable')
            result = await planner.prepare(actor, history_since=since, expected_level=level, expires_at=expiry)
        if (result.reason not in {'planned', 'already_planned'} or result.channel != 'telegram' or
                not self.ready or not self.telegram_ready):
            return result
        async with self.sessions() as session:
            telegram_actor = await planner._telegram_actor(session, user_id)
        lease = await planner.telegram.claim(telegram_actor, result.job_id, history_since=since,
            lease_for=timedelta(seconds=self.timeout))
        if lease.reason != 'telegram_claimed': return lease

        async def send(envelope):
            if not self.ready or not self.telegram_ready:
                raise RuntimeError('Smart runtime stopped before transport')
            return await self.telegram_send(envelope)

        return await planner.telegram.dispatch(telegram_actor, lease, send, history_since=since)

    async def _tick(self):
        results = []
        for user_id in await self._page():
            if not self.ready: break
            self._cursor = user_id
            try:
                results.append(await self._account(user_id))
            except Exception:
                # No account, destination, token, SQL error or reader content.
                logger.warning('Smart runtime account unavailable')
        return tuple(results)

    async def tick(self):
        if not self.ready or self._ticking.locked(): return ()
        async with self._ticking:
            return await asyncio.wait_for(self._tick(), timeout=self.timeout)

    async def run(self):
        while self.ready:
            try:
                await self.tick()
            except asyncio.TimeoutError:
                logger.warning('Smart runtime tick timed out')
            except Exception:
                logger.warning('Smart runtime tick unavailable')
            await asyncio.sleep(self.interval)


def registered_runtime(app, settings, sessions):
    runtime = getattr(getattr(app, 'state', None), 'smart_reminder_runtime', None)
    if (isinstance(runtime, SmartReminderRuntime) and runtime.settings is settings and
            runtime.sessions is sessions and (runtime._host is None or runtime._host is app)):
        return runtime


def build_rules_runtime(settings, sessions, bot):
    """D25 profile and actual readers; creates no consent, cohort or review.

    A single shared startup switch selects the runtime. Existing persisted
    cohort/fencing and the separate Telegram transport switch remain required.
    """
    if getattr(settings, 'SMART_REMINDER_ENABLED', False) is not True:
        return None
    window = timedelta(days=30)
    return SmartReminderRuntime(settings, sessions, enabled=True, calibration=OBSERVED_RULES,
        history_window=window, coverage_reader=read_observed_learning,
        android_admission_reader=partial(read_android_admission, history_window=window),
        telegram_send=partial(send_telegram_content, bot))


def android_delivery(app, session, settings, sessions):
    runtime = registered_runtime(app, settings, sessions)
    return runtime.android(session) if runtime is not None else SmartReminderAndroidService(session)

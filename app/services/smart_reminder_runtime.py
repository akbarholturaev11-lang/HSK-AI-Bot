"""Reviewed-cohort runtime with the automatic four-stage rollout.

Supplied readers/transport are privileged dependencies, never client evidence.
Each tick refreshes the rollout heartbeat, advances automatic admission for the
open cohorts (see smart_reminder_rollout) and serves reviewed accounts only.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from functools import partial
import logging
from zoneinfo import ZoneInfo

from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy import and_, or_, select

from app.db.models.smart_reminder import SmartReminderRouting
from app.db.models.user import User
from app.services.smart_reminder_android import SmartReminderAndroidService, read_android_admission
from app.services.smart_reminder_cadence import OBSERVED_RULES
from app.services.smart_reminder_planner import PlanningResult, SmartReminderPlanner
from app.services.smart_reminder_policy import _aware_utc, day_window
from app.services.smart_reminder_policy_context import read_observed_learning
from app.services.smart_reminder_preferences import SmartReminderError, SmartReminderPreferencesService, _utc
from app.services.smart_reminder_rollout import (
    COHORT_COUNT, SmartReminderAdmissionService, SmartReminderRolloutService, rollout_cohort,
)
from app.services.smart_reminder_shadow_queue import JOB
from app.services.smart_reminder_destination import PWA_POLICY_VERSION
from app.services.smart_reminder_pwa import SmartReminderPwaService
from app.services.smart_reminder_shadow_worker import SmartReminderShadowWorker
from app.services.smart_reminder_telegram_content import send_telegram_content


logger = logging.getLogger(__name__)
ADMISSION_BATCH = 8


class SmartReminderRuntime:
    def __init__(self, settings, sessions, *, enabled=False, calibration=None,
                 history_window=None, coverage_reader=None, android_admission_reader=None,
                 telegram_send=None, clock=None, interval=60, timeout=30, batch=16, admission=False):
        if (interval <= 0 or timeout <= 0 or type(batch) is not int or not 1 <= batch <= 128 or
                history_window is not None and (not isinstance(history_window, timedelta) or history_window <= timedelta(0))):
            raise ValueError('Positive bounded runtime settings required')
        self.settings, self.sessions, self.enabled = settings, sessions, enabled
        self.calibration, self.history_window = calibration, history_window
        self.coverage_reader, self.android_admission_reader = coverage_reader, android_admission_reader
        self.telegram_send = telegram_send
        # Explicit: only the production rules runtime moves accounts itself.
        self.admission = admission is True
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.interval, self.timeout, self.batch = interval, timeout, batch
        self._cursor, self._ticking = 0, asyncio.Lock()
        self._admission_cursors = {}
        self._host = None
        self._actors = SmartReminderShadowWorker(settings, sessions, clock=self.clock)
        # Follow the runtime clock even when a host replaces it after construction.
        self.rollout = SmartReminderRolloutService(sessions, clock=lambda: self.clock(), interval=interval, timeout=timeout)

    def bind(self, app):
        if self._host is not None and self._host is not app:
            raise ValueError('Runtime already belongs to another host')
        self._host = app

    @property
    def telegram_ready(self):
        return callable(self.telegram_send) and getattr(self.settings, 'SMART_REMINDER_TELEGRAM_ENABLED', False) is True

    @property
    def pwa_ready(self):
        from app.services.learner_pwa_push import sender_config
        return sender_config(self.settings) is not None

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
            admission_reader=self._admission if callable(self.android_admission_reader) else None,
            rollout_reader=self.rollout.allowed)

    def _planner(self):
        return SmartReminderPlanner(self.settings, self.sessions, enabled=self.ready,
            calibration=self.calibration, coverage_reader=self._coverage, clock=self.clock,
            android_admission_reader=self._admission if callable(self.android_admission_reader) else None,
            rollout_reader=self.rollout.allowed)

    async def _page(self, stage):
        now = _aware_utc(self.clock())
        routing = SmartReminderRouting
        query = select(routing.user_id).where(routing.verified_at <= now, routing.verified_until > now,
            or_(and_(routing.state == 'held', callable(self.android_admission_reader)),
                and_(routing.state == 'telegram', or_(self.telegram_ready, self.pwa_ready)))).order_by(
                    routing.user_id).limit(self.batch * COHORT_COUNT)
        async with self.sessions() as session:
            rows = (await session.scalars(query.where(routing.user_id > self._cursor))).all()
            if not rows and self._cursor:
                rows = (await session.scalars(query)).all()
        if not rows:
            self._cursor = 0
            return []
        selected = [user_id for user_id in rows if rollout_cohort(user_id) < stage][:self.batch]
        self._cursor = selected[-1] if len(selected) == self.batch else rows[-1]
        return selected

    async def _mark_blocked(self, user_id):
        from app.services.bot_block_status_service import BotBlockStatusService
        async with self.sessions.begin() as session:
            user = await session.get(User, user_id, with_for_update=True)
            if user is not None:
                await BotBlockStatusService(session).mark_user_blocked(user, reason='smart_study_forbidden')

    async def _account(self, user_id):
        if not self.ready: return PlanningResult('runtime_disabled')
        actor = await self._actors.actor_for(user_id)
        planner = self._planner()
        now = _aware_utc(self.clock())
        since = now - self.history_window
        async with self.sessions.begin() as session:
            if not await self.rollout.allowed(session, user_id, now=now):
                return PlanningResult('rollout_cohort_closed')
            pref = await SmartReminderPreferencesService(session).read(actor)
            level = await session.scalar(select(User.level).where(User.id == user_id))
            reviewed_until = await session.scalar(select(SmartReminderRouting.verified_until).where(
                SmartReminderRouting.user_id == user_id))
            versions = (self.android(session).policy_version, planner.telegram.policy_version, PWA_POLICY_VERSION)
            # Existing due work must not depend on another successful reserve:
            # reserve intentionally refuses a newly requested time in the past.
            pending = (await session.execute(select(JOB).where(JOB.c.user_id == user_id,
                JOB.c.category == 'study', JOB.c.state.in_(('pending', 'claimed')),
                JOB.c.policy_version.in_(versions), JOB.c.expires_at > self.clock(),
                JOB.c.selected_channel.in_(('android', 'telegram', 'pwa')))
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
        if result.reason not in {'planned', 'already_planned'} or not self.ready:
            return result
        if result.channel == 'pwa':
            return await SmartReminderPwaService(self.settings, self.sessions,
                clock=self.clock).dispatch(planner, actor, result.job_id, result.device_id,
                    history_since=since)
        if result.channel != 'telegram' or not self.telegram_ready:
            return result
        async with self.sessions() as session:
            telegram_actor = await planner._telegram_actor(session, user_id)
        lease = await planner.telegram.claim(telegram_actor, result.job_id, history_since=since,
            lease_for=timedelta(seconds=self.timeout))
        if lease.reason != 'telegram_claimed': return lease

        async def send(envelope):
            if not self.ready or not self.telegram_ready:
                raise RuntimeError('Smart runtime stopped before transport')
            try:
                return await self.telegram_send(envelope)
            except TelegramForbiddenError:
                # A definite learner refusal: later passes skip the account.
                # The attempt itself stays unknown and is never retried.
                try:
                    await self._mark_blocked(envelope.user_id)
                except Exception:
                    logger.warning('Smart runtime block status unavailable')
                raise

        return await planner.telegram.dispatch(telegram_actor, lease, send, history_since=since)

    async def _tick(self):
        stage = await self.rollout.heartbeat()
        if stage < 1:
            return ()
        if self.admission:
            try:
                await SmartReminderAdmissionService(self.sessions, clock=self.clock,
                    telegram_ready=self.telegram_ready,
                    android_ready=callable(self.android_admission_reader), batch=ADMISSION_BATCH,
                    cursors=self._admission_cursors).step(stage)
            except Exception:
                logger.warning('Smart runtime admission unavailable')
                await self.rollout.account_failed()
        results = []
        for user_id in await self._page(stage):
            if not self.ready: break
            try:
                results.append(await self._account(user_id))
            except SmartReminderError:
                # An ordinary per-account guard (no actor, deletion pending...).
                continue
            except Exception:
                # No account, destination, token, SQL error or reader content.
                logger.warning('Smart runtime account unavailable')
                await self.rollout.account_failed()
        return tuple(results)

    async def tick(self):
        if not self.ready or self._ticking.locked(): return ()
        async with self._ticking:
            try:
                result = await asyncio.wait_for(self._tick(), timeout=self.timeout)
            except asyncio.TimeoutError:
                await self.rollout.tick_finished(timed_out=True)
                raise
            await self.rollout.tick_finished(timed_out=False)
            return result

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
    """D25 profile and actual readers with automatic staged admission.

    A single shared startup switch selects the runtime. Admission creates no
    consent; it holds, drains and reviews accounts of the open rollout cohorts
    whose existing preference and Android inventory allow it. The separate
    Telegram transport switch remains required for Telegram sends.
    """
    if getattr(settings, 'SMART_REMINDER_ENABLED', False) is not True:
        return None
    window = timedelta(days=30)
    return SmartReminderRuntime(settings, sessions, enabled=True, calibration=OBSERVED_RULES,
        history_window=window, coverage_reader=read_observed_learning,
        android_admission_reader=partial(read_android_admission, history_window=window),
        telegram_send=partial(send_telegram_content, bot), admission=True)


def android_delivery(app, session, settings, sessions):
    runtime = registered_runtime(app, settings, sessions)
    return runtime.android(session) if runtime is not None else SmartReminderAndroidService(session)

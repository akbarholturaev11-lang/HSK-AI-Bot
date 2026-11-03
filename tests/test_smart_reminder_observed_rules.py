"""D25 ordinary rules with real persisted learning/readers; no live providers."""
from dataclasses import asdict, replace
from datetime import timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, event, select, update

from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.smart_reminder import SmartReminderPreference, SmartReminderRouting
from app.db.models.user import User
from app.db.models.voice_practice_session import VoicePracticeSession
from app.services.smart_reminder_cadence import OBSERVED_RULES, evaluate_cadence
from app.services.smart_reminder_policy_context import ObservedLearning, read_observed_learning
from app.services.smart_reminder_preferences import SmartReminderActor
from app.services.smart_reminder_runtime import build_rules_runtime
from app.services.smart_reminder_shadow_queue import ATTEMPT, JOB
from app.services.smart_reminder_telegram import _with_learning
from tests import test_smart_reminder_cadence as cadence
from tests import test_smart_reminder_native_admission as admission
from tests import test_smart_reminder_planner as planner
from tests import test_smart_reminder_runtime as host
from tests import test_smart_reminder_voice_activity as voice
from tests.test_smart_reminder_legacy_backfill import PG_URL


class ProfileTests(unittest.TestCase):
    def decision(self, **changes):
        return evaluate_cadence(cadence.context(complete=False, observed_sources=True, **changes),
            calibration=OBSERVED_RULES)

    def test_explicit_profile_and_positive_source_pair_required(self):
        self.assertEqual(self.decision().reason, 'shadow_candidate')
        self.assertEqual(evaluate_cadence(cadence.context(complete=False),
            calibration=OBSERVED_RULES).reason, 'learning_coverage_unknown')
        self.assertEqual(evaluate_cadence(cadence.context(complete=False, observed_sources=True),
            calibration=cadence.QA).reason, 'learning_coverage_unknown')
        self.assertEqual(set(asdict(OBSERVED_RULES)), set(asdict(cadence.QA)))
        self.assertEqual((OBSERVED_RULES.minimum_learning_days, OBSERVED_RULES.weekly_maximum,
            OBSERVED_RULES.maximum_unsuccessful, OBSERVED_RULES.backoff_factor), (3, 3, 5, 2))

    def test_no_negative_history_or_failure_inference(self):
        d = self.decision(intents=(cadence.intent(3, external=True, state='unknown'),))
        self.assertEqual((d.reason, d.weekly_intents), ('shadow_candidate', 1))
        self.assertIsNone(d.abnormal_inactivity)
        self.assertIsNone(d.unsuccessful_count)
        self.assertFalse(d.dispatch_allowed)

    def test_positive_return_without_click_or_xp_suppresses_same_day(self):
        self.assertEqual(self.decision(observed_activity_at=cadence.NOW).reason, 'personal_cadence_cooldown')
        self.assertEqual(self.decision(observed_activity_at=cadence.NOW+timedelta(seconds=1)).reason,
            'cadence_source_coverage_limited')

    def test_three_distinct_days_and_approved_extended_history(self):
        cold=self.decision(studies=cadence.history((3,4)))
        self.assertEqual(cold.reason, 'shadow_candidate')
        self.assertIsNone(cold.observed_gap_days)
        self.assertEqual(self.decision(studies=cadence.history((3,4,5))).reason, 'shadow_candidate')
        self.assertEqual(self.decision(studies=cadence.history((31,32,33))).reason, 'shadow_candidate')

    def test_day_one_uses_saved_time_without_inventing_habit_or_negative_outcomes(self):
        d=self.decision(studies=())
        self.assertEqual((d.reason,d.eligibility.time_source,d.eligibility.time_local),
            ('shadow_candidate','saved',cadence.context().policy.saved_time))
        self.assertIsNone(d.observed_gap_days)
        self.assertIsNone(d.unsuccessful_count)
        self.assertEqual(self.decision(studies=(),observed_activity_at=cadence.NOW).reason,
            'personal_cadence_cooldown')

    def test_verified_shown_series_keeps_strict_negative_feed_requirement(self):
        self.assertEqual(self.decision(studies=cadence.history((10,11,12)),
            intents=(cadence.intent(3, shown=True),)).reason, 'learning_coverage_unknown')

    def test_day_week_quiet_off_and_goal_guards_remain(self):
        self.assertEqual(self.decision(intents=(cadence.intent(0),)).reason, 'account_day_already_owned')
        self.assertEqual(self.decision(intents=tuple(cadence.intent(n, external=True, state='unknown')
            for n in (1,2,3))).reason, 'weekly_study_budget')
        for changes, reason in (({'master_enabled':False}, 'master_off'),
                ({'plan_completed':True}, 'plan_completed')):
            c = replace(cadence.context(complete=False, observed_sources=True),
                policy=replace(cadence.context().policy, **changes))
            self.assertEqual(evaluate_cadence(c, calibration=OBSERVED_RULES).reason, reason)

    def test_evidence_cannot_cross_account_window_profile_or_overflow(self):
        actor = SmartReminderActor(1, 'telegram', telegram_id=3001)
        since = cadence.NOW-timedelta(days=30)
        e = ObservedLearning(1, since, cadence.NOW)
        c = cadence.context(complete=False)
        self.assertIsNotNone(_with_learning(c, e, actor, since, cadence.NOW, OBSERVED_RULES))
        for bad, profile in ((replace(e,user_id=2), OBSERVED_RULES),
                (replace(e,history_since=since+timedelta(seconds=1)), OBSERVED_RULES),
                (replace(e,coverage_limits=('scored_events_over_limit',)), OBSERVED_RULES), (e,cadence.QA)):
            self.assertIsNone(_with_learning(c,bad,actor,since,cadence.NOW,profile))


class ReaderChecks:
    postgres = False

    async def asyncSetUp(self):
        cls = voice.PostgreSQLVoiceTests if self.postgres else voice.SQLiteVoiceTests
        self.v = cls(methodName='test_actual_server_turn_and_end_count_without_click_or_completed_unit')
        await self.v.asyncSetUp()
        self.q = self.v.case
        self.actor = SmartReminderActor(1, 'android', device_id='device-1', session_id='session-1')

    async def asyncTearDown(self): await self.v.asyncTearDown()

    async def read(self):
        async with self.q.sessions.begin() as s:
            return await read_observed_learning(s, self.actor, self.v.at-timedelta(hours=1),
                self.v.at+timedelta(seconds=1))

    async def test_failed_grade_and_completed_voice_are_positive_activity_without_fresh_xp(self):
        await self.v.quiz()
        before = await self.v.storage.rows(CourseXpEvent.__table__)
        d = await self.read()
        self.assertEqual(d.latest_activity_at, self.v.at)
        self.assertFalse(d.limited)
        await self.v.voice(ended_at=self.v.at+timedelta(seconds=1))
        self.assertEqual((await self.read()).latest_activity_at, self.v.at+timedelta(seconds=1))
        self.assertEqual(await self.v.storage.rows(CourseXpEvent.__table__), before)
        self.assertFalse(hasattr(d, 'complete_since'))

    async def test_canonical_learning_xp_excludes_rewards_foreign_and_future(self):
        async with self.q.sessions.begin() as s:
            for uid, kind, at in ((1,'training',self.v.at), (1,'reward_chest',self.v.at+timedelta(seconds=1)),
                    (2,'lesson',self.v.at+timedelta(seconds=1)), (1,'test',self.v.at+timedelta(seconds=2))):
                s.add(CourseXpEvent(user_id=uid,activity_type=kind,activity_ref=uuid4().hex,xp=1,
                    created_at=at,activity_date=at.date(),week_start=at.date()-timedelta(days=at.weekday())))
        self.assertEqual((await self.read()).latest_activity_at, self.v.at)

    async def test_read_never_flushes_writes_exports_or_private_voice_fields(self):
        await self.v.voice()
        sql=[]
        def capture(conn,cursor,statement,parameters,ctx,many): sql.append(statement.lower())
        event.listen(self.q.engine.sync_engine,'before_cursor_execute',capture)
        try:
            async with self.q.sessions() as s:
                user = await s.get(User,1)
                original = user.language
                user.language = 'ru' if original!='ru' else 'uz'
                d = await read_observed_learning(s,self.actor,self.v.at-timedelta(hours=1),self.v.at)
                self.assertEqual(d.latest_activity_at,self.v.at)
                self.assertTrue(s.dirty)
        finally: event.remove(self.q.engine.sync_engine,'before_cursor_execute',capture)
        self.assertFalse(any(x.lstrip().startswith(('insert','update','delete')) for x in sql))
        voice_sql=[x for x in sql if 'voice_practice_sessions' in x]
        self.assertTrue(voice_sql)
        self.assertFalse(any('history' in x or 'corrections' in x for x in voice_sql))
        async with self.q.sessions() as s: self.assertEqual((await s.get(User,1)).language,original)

    async def test_overflow_is_explicit_and_disables_ordinary_use(self):
        with patch('app.services.smart_reminder_policy_context.MAX_POLICY_ROWS',1):
            await self.v.quiz()
            await self.v.quiz()
            self.assertTrue((await self.read()).limited)


class SQLiteReaderTests(ReaderChecks,unittest.IsolatedAsyncioTestCase): pass


@unittest.skipUnless(PG_URL,'Disposable loopback PostgreSQL required')
class PostgreSQLReaderTests(ReaderChecks,unittest.IsolatedAsyncioTestCase): postgres=True


class StartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_single_switch_is_exact_and_does_no_sql_or_provider_io(self):
        sessions,bot=Mock(),Mock()
        for value in (None,False,1,'true'):
            self.assertIsNone(build_rules_runtime(SimpleNamespace(SMART_REMINDER_ENABLED=value),sessions,bot))
        r=build_rules_runtime(SimpleNamespace(SMART_REMINDER_ENABLED=True),sessions,bot)
        self.assertTrue(r.ready)
        self.assertFalse(r.telegram_ready)
        self.assertIs(r.calibration,OBSERVED_RULES)
        self.assertIs(r.coverage_reader,read_observed_learning)
        sessions.assert_not_called();self.assertEqual(bot.mock_calls,[])


class NativeChecks:
    postgres=False

    async def asyncSetUp(self):
        cls=admission.PostgreSQLNativeAdmissionTests if self.postgres else admission.SQLiteNativeAdmissionTests
        self.f=cls(methodName='test_native_only_review_source_runtime_real_auth_and_original_receipt_after_hold')
        await self.f.asyncSetUp();self.q=self.f.q;self.p=self.f.p
        async with self.q.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(telegram_id=None))
        await self.f.prepare_review()
        self.q.settings.SMART_REMINDER_ENABLED=True
        self.r=build_rules_runtime(self.q.settings,self.q.sessions,Mock())
        self.r.clock=lambda:self.q.tick
        self.r._actors.clock=self.r.clock
        app=FastAPI();app.state.smart_reminder_runtime=self.r;self.r.bind(app)
        host.attach_actual_main_router(app,self.q.sessions,self.q.settings)
        await self.q.client.aclose()
        self.q.client=AsyncClient(transport=ASGITransport(app=app),base_url='https://observed.test')

    async def asyncTearDown(self): await self.f.asyncTearDown()

    async def test_real_native_only_review_reader_plan_claim_and_immutable_receipt(self):
        planned,=await self.r.tick()
        self.assertEqual((planned.reason,planned.channel,planned.device_id),('planned','android','device-1'))
        self.q.job_id=planned.job_id;self.q.tick=self.p.due_clock
        grant=await self.q.claim();self.assertTrue(grant['dispatch_allowed'])
        self.r.enabled=False
        receipt,body=await self.q.receipt(grant)
        retry,_=await self.q.receipt(grant,body=body)
        self.assertEqual(receipt,retry)

    async def test_current_positive_return_after_plan_suppresses_claim(self):
        planned,=await self.r.tick();self.q.job_id=planned.job_id;self.q.tick=self.p.due_clock
        async with self.q.sessions.begin() as s:
            s.add(VoicePracticeSession(id=str(uuid4()),user_id=1,role='friend',level='hsk1',
                language='uz',voice='female',mode='turn',status='completed',turn_count=1,
                started_at=self.q.tick-timedelta(seconds=10),ended_at=self.q.tick,history=[],corrections=[]))
        grant=await self.q.claim()
        self.assertFalse(grant['dispatch_allowed'])
        self.assertEqual(grant['reason'],'personal_cadence_cooldown')
        self.assertEqual(await self.q.rows(ATTEMPT),[])

    async def test_missing_persisted_review_does_no_planning(self):
        async with self.q.sessions.begin() as s:
            await s.execute(update(SmartReminderRouting).values(verified_at=None,verified_until=None,evidence_sha256=None))
        self.assertEqual(await self.r.tick(),())
        self.assertEqual(await self.q.rows(JOB),[])

    async def test_day_one_manual_time_reaches_actual_native_claim_without_learning_history(self):
        async with self.q.sessions.begin() as s:
            await s.execute(delete(CourseXpEvent).where(CourseXpEvent.user_id==1))
            await s.execute(delete(CourseMiniAppEvent).where(CourseMiniAppEvent.user_id==1))
            await s.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id==1)
                .values(time_mode='manual_locked',manual_time_local=self.p.due_clock.time().replace(tzinfo=None)))
        planned,=await self.r.tick()
        self.assertEqual(planned.reason,'planned')
        self.q.job_id=planned.job_id;self.q.tick=self.p.due_clock
        self.assertTrue((await self.q.claim())['dispatch_allowed'])


class SQLiteNativeTests(NativeChecks,unittest.IsolatedAsyncioTestCase): pass


@unittest.skipUnless(PG_URL,'Disposable loopback PostgreSQL required')
class PostgreSQLNativeTests(NativeChecks,unittest.IsolatedAsyncioTestCase): postgres=True


class TelegramChecks:
    postgres=False

    async def asyncSetUp(self):
        cls=planner.PostgreSQLTelegramPlannerTests if self.postgres else planner.SQLiteTelegramPlannerTests
        self.p=cls(methodName='test_real_tg_plan_has_no_attempt_until_existing_claim_and_dispatch')
        await self.p.asyncSetUp();self.q=self.p.q
        self.q.settings.SMART_REMINDER_ENABLED=True
        self.r=build_rules_runtime(self.q.settings,self.q.sessions,self.q.bot)
        self.r.clock=lambda:self.q.tick;self.r._actors.clock=self.r.clock

    async def asyncTearDown(self): await self.p.asyncTearDown()

    async def test_actual_source_and_registered_bot_callback_send_once_after_committed_claim(self):
        planned,=await self.r.tick();self.assertEqual(planned.reason,'telegram_not_due')
        async def provider(*args,**kwargs):
            async with self.q.sessions.begin() as s:
                await s.execute(select(User).where(User.id==1).with_for_update())
                row=(await s.execute(select(ATTEMPT))).mappings().one()
                self.assertEqual(row['state'],'in_flight')
                self.assertIsNotNone(row['started_at'])
            return SimpleNamespace(message_id=123)
        self.q.bot.send_message.side_effect=provider
        self.q.tick=self.q.tick.replace(hour=14,minute=1)
        sent,=await self.r.tick()
        self.assertEqual(sent.reason,'telegram_provider_accepted')
        await self.r.tick()
        self.assertEqual(self.q.bot.send_message.await_count,1)

    async def test_unknown_outcome_of_registered_sender_is_never_retried(self):
        await self.r.tick();self.q.tick=self.q.tick.replace(hour=14,minute=1)
        self.q.bot.send_message.side_effect=TimeoutError('synthetic')
        sent,=await self.r.tick();self.assertEqual(sent.reason,'telegram_unknown')
        await self.r.tick();self.assertEqual(self.q.bot.send_message.await_count,1)

    async def test_day_one_saved_time_sends_without_invented_learning_history(self):
        async with self.q.sessions.begin() as s:
            await s.execute(delete(CourseXpEvent).where(CourseXpEvent.user_id==1))
            await s.execute(delete(CourseMiniAppEvent).where(CourseMiniAppEvent.user_id==1))
        planned,=await self.r.tick();self.assertEqual(planned.reason,'telegram_not_due')
        self.q.tick=self.q.tick.replace(hour=14,minute=1)
        sent,=await self.r.tick()
        self.assertEqual(sent.reason,'telegram_provider_accepted')
        self.assertEqual(self.q.bot.send_message.await_count,1)


class SQLiteTelegramTests(TelegramChecks,unittest.IsolatedAsyncioTestCase): pass


@unittest.skipUnless(PG_URL,'Disposable loopback PostgreSQL required')
class PostgreSQLTelegramTests(TelegramChecks,unittest.IsolatedAsyncioTestCase): postgres=True

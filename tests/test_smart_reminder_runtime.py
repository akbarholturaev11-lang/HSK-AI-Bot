"""Real reviewed runtime flows; all proof/readers/providers are synthetic."""
import ast
import asyncio
import contextlib
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, select, update

from app.api.smart_reminder import create_smart_reminder_router
from app.db.models.smart_reminder import SmartReminderRouting
from app.services.smart_reminder_android import GRANT
from app.services.smart_reminder_runtime import SmartReminderRuntime, android_delivery, registered_runtime, build_rules_runtime
from app.services.smart_reminder_shadow_queue import ATTEMPT, JOB
from tests import test_smart_reminder_planner as fixtures
from tests.test_smart_reminder_cadence import QA
from tests.test_smart_reminder_legacy_backfill import PG_URL


MAIN = Path(__file__).resolve().parents[1] / 'app/main.py'


async def historical_unknown(q, channel):
    """Synthetic original prior-day source facts, never a new delivery claim."""
    start=q.tick.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(days=1)
    job_id,attempt_id=str(uuid4()),str(uuid4())
    scheduled=start+timedelta(hours=14)
    async with q.sessions.begin() as s:
        await s.execute(insert(JOB).values(id=job_id,user_id=1,local_day=start.date(),timezone_name='Etc/UTC',
            day_start_utc=start,day_end_utc=start+timedelta(days=1),scheduled_at=scheduled,
            expires_at=start+timedelta(days=1),state='unknown',policy_version='synthetic-original',
            preference_revision=2,grant_epoch=1,course_key='hsk1',lesson_order=5,
            selected_channel=channel,selected_device_id='device-1' if channel=='android' else None))
        await s.execute(insert(ATTEMPT).values(id=attempt_id,job_id=job_id,attempt_key=uuid4().hex,
            channel=channel,device_id='device-1' if channel=='android' else None,grant_epoch=1,
            state='client_posted_unverified' if channel=='android' else 'provider_accepted',
            prepared_at=scheduled-timedelta(seconds=1),started_at=scheduled,
            resolved_at=scheduled+timedelta(seconds=1),expires_at=start+timedelta(days=1)))
    return job_id,attempt_id


def attach_actual_main_router(host, sessions, settings):
    node = next(n for n in ast.parse(MAIN.read_text()).body if isinstance(n, ast.Expr) and
        isinstance(n.value, ast.Call) and any(isinstance(a, ast.Call) and
        isinstance(a.func, ast.Name) and a.func.id == 'create_smart_reminder_router' for a in n.value.args))
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(MAIN), 'exec'), dict(
        app=host, async_session_maker=sessions, settings=settings, android_delivery=android_delivery,
        create_smart_reminder_router=create_smart_reminder_router))


class HostTests(unittest.IsolatedAsyncioTestCase):
    async def test_absent_disabled_and_incomplete_runtime_does_no_sql_or_io(self):
        sessions=Mock(side_effect=AssertionError('SQL must remain unused'))
        reader=AsyncMock()
        base=dict(calibration=QA,history_window=timedelta(days=30),coverage_reader=reader,
            android_admission_reader=reader)
        for overrides in ({}, {'enabled':1}, {'enabled':True,'calibration':None},
                {'enabled':True,'history_window':None}, {'enabled':True,'coverage_reader':None},
                {'enabled':True,'android_admission_reader':None}):
            runtime=SmartReminderRuntime(SimpleNamespace(),sessions,**(base|overrides))
            self.assertFalse(runtime.ready)
            self.assertEqual(await runtime.tick(),())
            await runtime.run()
        sessions.assert_not_called();reader.assert_not_called()

    async def test_registration_is_bound_to_the_actual_host_settings_and_database(self):
        settings,sessions=SimpleNamespace(),Mock()
        runtime=SmartReminderRuntime(settings,sessions)
        host=FastAPI();host.state.smart_reminder_runtime=runtime
        self.assertIs(registered_runtime(host,settings,sessions),runtime)
        self.assertIsNone(registered_runtime(host,SimpleNamespace(),sessions))
        self.assertIsNone(registered_runtime(host,settings,Mock()))
        self.assertIsNone(registered_runtime(object(),settings,sessions))
        self.assertEqual(android_delivery(host,None,settings,Mock())._gate()['reason'],'android_dispatch_disabled')
        runtime.bind(host)
        other=FastAPI();other.state.smart_reminder_runtime=runtime
        self.assertIsNone(registered_runtime(other,settings,sessions))

    async def test_removing_host_registration_revokes_running_runtime_at_fresh_boundaries(self):
        reader=AsyncMock()
        runtime=SmartReminderRuntime(SimpleNamespace(),Mock(),enabled=True,calibration=QA,
            history_window=timedelta(days=30),coverage_reader=reader,android_admission_reader=reader)
        host=FastAPI();host.state.smart_reminder_runtime=runtime;runtime.bind(host)
        self.assertTrue(runtime.ready)
        host.state.smart_reminder_runtime=None
        self.assertFalse(runtime.ready)
        self.assertIsNone(await runtime._coverage(None))
        self.assertIsNone(await runtime._admission(None))
        self.assertEqual(await runtime.tick(),())
        reader.assert_not_called()

    async def test_timeout_and_parent_cancellation_release_the_tick(self):
        runtime=SmartReminderRuntime(SimpleNamespace(),Mock(),enabled=True,calibration=QA,
            history_window=timedelta(days=30),coverage_reader=AsyncMock(),android_admission_reader=AsyncMock(),timeout=.01)
        cleaned=asyncio.Event()
        async def blocked():
            try: await asyncio.Event().wait()
            finally: cleaned.set()
        runtime._page=blocked
        with self.assertRaises(asyncio.TimeoutError): await runtime.tick()
        self.assertTrue(cleaned.is_set());self.assertFalse(runtime._ticking.locked())
        task=asyncio.create_task(runtime.tick());await asyncio.sleep(0);task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task
        self.assertFalse(runtime._ticking.locked())

    async def test_actual_main_lifespan_starts_and_awaits_runtime_without_shadow_competitor(self):
        await self.exercise_lifespan(configured=False)

    async def test_actual_main_lifespan_builds_rules_runtime_from_explicit_switch(self):
        await self.exercise_lifespan(configured=True)

    async def exercise_lifespan(self, *, configured):
        settings=SimpleNamespace(SMART_REMINDER_SHADOW_ENABLED=True,SMART_REMINDER_ANALYSIS_ENABLED=False,
            SMART_REMINDER_ENABLED=configured,ADMIN_PWA_ENABLED=False,ADMIN_PWA_PUSH_ENABLED=False)
        sessions=Mock()
        runtime=SmartReminderRuntime(settings,sessions,enabled=True,calibration=QA,
            history_window=timedelta(days=30),coverage_reader=AsyncMock(),android_admission_reader=AsyncMock())
        host=FastAPI()
        if not configured: host.state.smart_reminder_runtime=runtime
        started,stopped=asyncio.Event(),asyncio.Event()
        async def block(*args): await asyncio.Event().wait()
        async def run():
            started.set()
            try: await block()
            finally: stopped.set()
        runtime.run=run
        async def configured_run(self): await run()
        shadow=Mock(side_effect=AssertionError('competing shadow worker'))
        namespace=dict(asynccontextmanager=contextlib.asynccontextmanager,FastAPI=FastAPI,asyncio=asyncio,
            contextlib=contextlib,init_db=AsyncMock(),_seed_lessons=block,dp=SimpleNamespace(start_polling=block),
            bot=SimpleNamespace(session=SimpleNamespace(close=AsyncMock())),_background_scheduler=block,
            _desktop_auth_retention_scheduler=block,settings=settings,async_session_maker=sessions,
            registered_runtime=registered_runtime,build_rules_runtime=build_rules_runtime,SmartReminderShadowWorker=shadow,sender_config=lambda s:None,
            learner_pwa_sender_config=lambda s:None,dispatch_learner_pwa_push_batch=AsyncMock(return_value={"claimed":0}),
            _study_ai_tasks=set(),admin_pwa_due_campaigns=SimpleNamespace(close=AsyncMock()),
            engine=SimpleNamespace(dispose=AsyncMock()))
        for name in ('statistics','analytics','feedback'):
            namespace['admin_pwa_'+name+'_reader']=SimpleNamespace(aclose=AsyncMock())
        node=next(n for n in ast.parse(MAIN.read_text()).body if isinstance(n,ast.AsyncFunctionDef) and n.name=='lifespan')
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(MAIN),'exec'),namespace)
        with patch.object(SmartReminderRuntime,'run',configured_run):
            async with namespace['lifespan'](host):
                await asyncio.wait_for(started.wait(),1)
                if configured:
                    self.assertIs(host.state.smart_reminder_runtime.calibration,
                        build_rules_runtime(settings,sessions,None).calibration)
                    self.assertIs(host.state.smart_reminder_runtime._host,host)
        self.assertTrue(stopped.is_set());shadow.assert_not_called();sessions.assert_not_called()


class NativeRuntimeChecks:
    postgres=False

    async def asyncSetUp(self):
        cls=fixtures.PostgreSQLNativePlannerTests if self.postgres else fixtures.SQLiteNativePlannerTests
        self.p=cls(methodName='test_repeat_and_restart_acknowledge_selection_without_reranking')
        await self.p.asyncSetUp();self.q=self.p.q

    async def asyncTearDown(self): await self.p.asyncTearDown()

    def runtime(self,**options):
        return SmartReminderRuntime(self.q.settings,self.q.sessions,**(dict(enabled=True,calibration=QA,
            history_window=timedelta(days=30),coverage_reader=self.q.learning,
            android_admission_reader=self.p.admission,clock=lambda:self.q.tick)|options))

    async def test_reviewed_tick_and_actual_main_authenticated_claim_receipt_after_pause(self):
        runtime=self.runtime();host=FastAPI();host.state.smart_reminder_runtime=runtime
        attach_actual_main_router(host,self.q.sessions,self.q.settings)
        await self.q.client.aclose()
        self.q.client=AsyncClient(transport=ASGITransport(app=host),base_url='https://runtime.test')
        planned,=await runtime.tick()
        self.assertEqual((planned.reason,planned.device_id),('planned','device-1'))
        await self.p.no_delivery()
        self.q.job_id=planned.job_id;self.q.tick=self.p.due_clock
        due=await self.q.client.get(fixtures.native.BASE+'/due',headers=await self.q.bearer(1))
        self.assertEqual(due.json()['job_id'],planned.job_id)
        grant=await self.q.claim();self.assertTrue(grant['dispatch_allowed'])
        runtime.enabled=False
        self.assertEqual(await runtime.tick(),())
        self.assertFalse((await self.q.claim())['dispatch_allowed'])
        receipt,_=await self.q.receipt(grant)
        self.assertEqual(receipt['outcome'],'client_posted_unverified')
        self.assertEqual(len(await self.q.rows(GRANT)),1)

    async def test_restart_after_due_uses_original_selection_without_reserving_again(self):
        original,=await self.runtime().tick()
        self.q.tick=self.p.due_clock+timedelta(seconds=1)
        with patch('app.services.smart_reminder_planner.SmartReminderPlanner.prepare',side_effect=AssertionError('new reservation')):
            result,=await self.runtime().tick()
        self.assertEqual((result.reason,result.job_id),('already_planned',original.job_id))
        self.assertEqual(len(await self.q.rows(JOB)),1);await self.p.no_delivery()

    async def test_prior_day_posted_unknown_allows_new_native_plan_claim_without_replay(self):
        old_id,attempt_id=await historical_unknown(self.q,'android')
        original=(await self.q.rows(ATTEMPT))[0]
        planned,=await self.runtime().tick()
        self.assertEqual(planned.reason,'planned');self.assertNotEqual(planned.job_id,old_id)
        self.q.job_id=planned.job_id;self.q.tick=self.p.due_clock
        grant=await self.q.claim();self.assertTrue(grant['dispatch_allowed'])
        await self.q.receipt(grant)
        old=next(j for j in await self.q.rows(JOB) if j['id']==old_id)
        attempt=next(a for a in await self.q.rows(ATTEMPT) if a['id']==attempt_id)
        self.assertEqual(old['state'],'unknown');self.assertEqual(attempt,original)
        self.assertEqual(len(await self.q.rows(GRANT)),1)

    async def test_unreviewed_or_expired_routing_is_not_polled(self):
        async with self.q.sessions.begin() as s:
            await s.execute(update(SmartReminderRouting).values(verified_at=None,verified_until=None,evidence_sha256=None))
        self.assertEqual(await self.runtime().tick(),())
        self.assertEqual(await self.q.rows(JOB),[])
        await self.p.reviewed();self.q.tick=self.q.expiry
        self.assertEqual(await self.runtime().tick(),());await self.p.no_delivery()

    async def test_rotating_bounded_pages_do_not_starve_later_reviewed_accounts(self):
        async with self.q.sessions.begin() as s:
            first=(await s.execute(select(SmartReminderRouting.__table__))).mappings().one()
            s.add(SmartReminderRouting(**(dict(first)|{'user_id':2})))
        runtime=self.runtime(batch=1);runtime._account=AsyncMock(return_value='observed')
        for _ in range(3):self.assertEqual(await runtime.tick(),('observed',))
        self.assertEqual([call.args[0] for call in runtime._account.await_args_list],[1,2,1])
        self.assertEqual(await self.q.rows(JOB),[])

    async def test_reader_failure_is_sanitized_and_leaves_no_delivery(self):
        async def failed(*args):raise RuntimeError('synthetic-private-reader-body')
        runtime=self.runtime(android_admission_reader=failed)
        with self.assertLogs('app.services.smart_reminder_runtime',level='WARNING') as logs:
            self.assertEqual(await runtime.tick(),())
        self.assertEqual(logs.output,['WARNING:app.services.smart_reminder_runtime:Smart runtime account unavailable'])
        await self.p.no_delivery()

    async def test_runtime_pause_during_reader_prevents_pending_binding(self):
        runtime=None
        async def learning(*args):
            result=await self.q.learning(*args)
            runtime.enabled=False
            return result
        runtime=self.runtime(coverage_reader=learning)
        result,=await runtime.tick()
        self.assertEqual(result.reason,'learning_coverage_unavailable')
        self.assertEqual((await self.q.rows(JOB))[0]['state'],'shadow')
        await self.p.no_delivery()


class SQLiteNativeRuntimeTests(NativeRuntimeChecks,unittest.IsolatedAsyncioTestCase):pass


@unittest.skipUnless(PG_URL,'Disposable loopback PostgreSQL required')
class PostgreSQLNativeRuntimeTests(NativeRuntimeChecks,unittest.IsolatedAsyncioTestCase):postgres=True


class TelegramRuntimeChecks:
    postgres=False

    async def asyncSetUp(self):
        cls=fixtures.PostgreSQLTelegramPlannerTests if self.postgres else fixtures.SQLiteTelegramPlannerTests
        self.p=cls(methodName='test_real_tg_plan_has_no_attempt_until_existing_claim_and_dispatch')
        await self.p.asyncSetUp();self.q=self.p.q

    async def asyncTearDown(self):await self.p.asyncTearDown()

    def runtime(self,**options):
        return SmartReminderRuntime(self.q.settings,self.q.sessions,**(dict(enabled=True,calibration=QA,
            history_window=timedelta(days=30),coverage_reader=self.q.service.coverage_reader,
            telegram_send=self.q.send,clock=lambda:self.q.tick)|options))

    async def test_future_plan_then_due_restart_commits_before_provider_and_never_replays(self):
        planned,=await self.runtime().tick()
        self.assertEqual(planned.reason,'telegram_not_due');self.q.bot.send_message.assert_not_called()
        job=(await self.q.rows(JOB))[0]
        self.q.tick=self.q.tick.replace(hour=14,minute=1)
        with patch('app.services.smart_reminder_planner.SmartReminderPlanner.prepare',side_effect=AssertionError('new reservation')):
            sent,=await self.runtime().tick()
        self.assertEqual(sent.reason,'telegram_provider_accepted')
        self.assertEqual(self.q.bot.send_message.await_count,1)
        self.assertEqual(len(await self.q.rows(ATTEMPT)),1)
        await self.runtime().tick()
        self.assertEqual(self.q.bot.send_message.await_count,1)
        self.assertEqual((await self.q.rows(JOB))[0]['id'],job['id'])

    async def test_unknown_transport_outcome_never_retries_after_restart(self):
        await self.runtime().tick();self.q.tick=self.q.tick.replace(hour=14,minute=1)
        send=AsyncMock(side_effect=RuntimeError('private provider error'))
        result,=await self.runtime(telegram_send=send).tick()
        self.assertEqual(result.reason,'telegram_unknown')
        await self.runtime(telegram_send=send).tick()
        self.assertEqual(send.await_count,1)
        self.assertEqual((await self.q.rows(ATTEMPT))[0]['state'],'unknown')

    async def test_prior_day_accepted_unknown_allows_new_tg_intent_without_old_retry(self):
        old_id,attempt_id=await historical_unknown(self.q,'telegram')
        original=(await self.q.rows(ATTEMPT))[0]
        planned,=await self.runtime().tick();self.assertEqual(planned.reason,'telegram_not_due')
        self.q.tick=self.q.tick.replace(hour=14,minute=1)
        result,=await self.runtime().tick()
        self.assertEqual(result.reason,'telegram_provider_accepted')
        self.assertEqual(self.q.bot.send_message.await_count,1)
        self.assertEqual(len(await self.q.rows(ATTEMPT)),2)
        self.assertEqual(next(j for j in await self.q.rows(JOB) if j['id']==old_id)['state'],'unknown')
        self.assertEqual(next(a for a in await self.q.rows(ATTEMPT) if a['id']==attempt_id),original)

    async def test_unstarted_expired_lease_can_resume_without_another_attempt(self):
        await self.runtime().tick();self.q.tick=self.q.tick.replace(hour=14,minute=1)
        job=(await self.q.rows(JOB))[0]
        lease=await self.q.claim(job['id'])
        self.assertEqual(lease.reason,'telegram_claimed')
        self.q.tick+=timedelta(seconds=31)
        result,=await self.runtime().tick()
        self.assertEqual(result.reason,'telegram_provider_accepted')
        self.assertEqual(len(await self.q.rows(ATTEMPT)),1)
        self.assertEqual(self.q.bot.send_message.await_count,1)

    async def test_cancellation_after_io_started_never_replays(self):
        await self.runtime().tick();self.q.tick=self.q.tick.replace(hour=14,minute=1)
        started=asyncio.Event()
        async def hanging(envelope):
            started.set();await asyncio.Event().wait()
        task=asyncio.create_task(self.runtime(telegram_send=hanging).tick())
        await asyncio.wait_for(started.wait(),5);task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertEqual((await self.q.rows(ATTEMPT))[0]['state'],'in_flight')
        await self.runtime().tick();self.q.bot.send_message.assert_not_called()

    async def test_disabled_provider_or_missing_sender_does_zero_runtime_work(self):
        runtime=self.runtime(telegram_send=None)
        self.assertEqual(await runtime.tick(),());self.assertEqual(await self.q.rows(JOB),[])
        self.q.settings.SMART_REMINDER_TELEGRAM_ENABLED=False
        self.assertEqual(await self.runtime().tick(),());self.assertEqual(await self.q.rows(JOB),[])

    async def test_independent_runtime_instances_do_not_send_twice(self):
        if not self.postgres:self.skipTest('Independent PostgreSQL transactions required')
        await self.runtime().tick();self.q.tick=self.q.tick.replace(hour=14,minute=1)
        await asyncio.gather(self.runtime().tick(),self.runtime().tick())
        self.assertEqual(self.q.bot.send_message.await_count,1)
        self.assertEqual(len(await self.q.rows(ATTEMPT)),1)


class SQLiteTelegramRuntimeTests(TelegramRuntimeChecks,unittest.IsolatedAsyncioTestCase):pass


@unittest.skipUnless(PG_URL,'Disposable loopback PostgreSQL required')
class PostgreSQLTelegramRuntimeTests(TelegramRuntimeChecks,unittest.IsolatedAsyncioTestCase):postgres=True

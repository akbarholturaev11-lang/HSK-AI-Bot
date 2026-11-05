"""Persisted native proof source; synthetic external review, real SQL/auth."""
from dataclasses import replace
import asyncio
from datetime import datetime, timedelta, timezone
from functools import partial
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, insert, select, update

from app.db.models.desktop import DesktopSession
from app.db.models.smart_reminder import SmartReminderCapability, SmartReminderPreference, SmartReminderRouting
from app.db.models.user import User
from app.services.smart_reminder_android import GRANT, read_android_admission
from app.services.smart_reminder_preferences import SmartReminderActor, SmartReminderError, SmartReminderPatch, SmartReminderPreferencesService
from app.services.smart_reminder_runtime import SmartReminderRuntime
from app.services.smart_reminder_shadow_queue import ATTEMPT, JOB
from app.services.smart_reminder_telegram import RoutingReview, SmartReminderRoutingService
from tests import test_smart_reminder_planner as fixtures
from tests import test_smart_reminder_runtime as runtime_fixture
from tests.test_smart_reminder_cadence import QA
from tests.test_smart_reminder_legacy_backfill import PG_URL


class ReaderGateTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_configuration_clock_or_non_native_input_never_reads_sql(self):
        session=Mock();actor=SmartReminderActor(1,'android',device_id='d',session_id='s')
        now=datetime.now(timezone.utc);job_id=str(uuid4())
        for value in (None,True,timedelta(0),timedelta(days=-1)):
            with self.assertRaises(ValueError):
                await read_android_admission(session,actor,job_id,now,history_window=value)
        with self.assertRaises(ValueError):
            await read_android_admission(session,actor,job_id,now.replace(tzinfo=None),history_window=timedelta(days=30))
        self.assertIsNone(await read_android_admission(session,actor,'invalid',now,history_window=timedelta(days=30)))
        self.assertIsNone(await read_android_admission(session,replace(actor,kind='telegram'),job_id,now,
            history_window=timedelta(days=30)))
        self.assertEqual(session.mock_calls,[])


class NativeAdmissionChecks:
    postgres=False

    async def asyncSetUp(self):
        cls=fixtures.PostgreSQLNativePlannerTests if self.postgres else fixtures.SQLiteNativePlannerTests
        self.p=cls(methodName='test_repeat_and_restart_acknowledge_selection_without_reranking')
        await self.p.asyncSetUp();self.q=self.p.q;self.actor=self.p.actor
        self.routing=SmartReminderRoutingService(self.q.sessions,clock=lambda:self.q.tick)
        self.reader=partial(read_android_admission,history_window=timedelta(days=30))
        self.q.options['admission_reader']=self.reader
        await runtime_fixture.open_rollout(self.q.sessions,self.q.tick)

    async def asyncTearDown(self):await self.p.asyncTearDown()

    async def hold(self):
        self.generation=await self.routing.hold(self.actor,expected_generation=1)
        self.review=RoutingReview(1,self.generation,self.q.tick,self.q.expiry,'d'*64,True,True,True)

    async def prepare_review(self):
        await self.hold()
        await self.routing.review_android(self.actor,self.review)

    async def reserve(self):
        result=await self.p.planner().queue.reserve(self.actor,history_since=self.q.since,
            expected_level='hsk1',expires_at=self.q.expiry)
        self.assertIsNotNone(result.job_id);self.job_id=result.job_id

    async def read(self,actor=None,job_id=None):
        async with self.q.sessions.begin() as session:
            return await self.reader(session,actor or self.actor,job_id or self.job_id,self.q.tick)

    def runtime(self):
        return SmartReminderRuntime(self.q.settings,self.q.sessions,enabled=True,calibration=QA,
            history_window=timedelta(days=30),coverage_reader=self.q.learning,
            android_admission_reader=self.reader,clock=lambda:self.q.tick)

    async def test_native_only_review_source_runtime_real_auth_and_original_receipt_after_hold(self):
        async with self.q.sessions.begin() as session:
            await session.execute(update(User).where(User.id==1).values(telegram_id=None))
        await self.prepare_review()
        host=FastAPI();host.state.smart_reminder_runtime=self.runtime()
        runtime_fixture.attach_actual_main_router(host,self.q.sessions,self.q.settings)
        await self.q.client.aclose()
        self.q.client=AsyncClient(transport=ASGITransport(app=host),base_url='https://native-proof.test')
        planned,=await host.state.smart_reminder_runtime.tick()
        self.assertEqual((planned.reason,planned.device_id),('planned','device-1'))
        await self.p.no_delivery()
        self.q.job_id=planned.job_id;self.q.tick=self.p.due_clock
        grant=await self.q.claim();self.assertTrue(grant['dispatch_allowed'])
        receipt,body=await self.q.receipt(grant)
        before=await self.q.rows(GRANT)
        await self.routing.hold(self.actor,expected_generation=self.generation)
        repeated,_=await self.q.receipt(grant,body=body)
        self.assertEqual(repeated,receipt);self.assertEqual(await self.q.rows(GRANT),before)
        async with self.q.sessions() as session:
            self.assertIsNone(await session.scalar(select(User.telegram_id).where(User.id==1)))
        self.assertEqual(len(before),1)

    async def test_unreviewed_hold_cannot_supply_proof_and_exact_review_retry_does_not_rewrite(self):
        await self.hold();await self.reserve()
        self.assertIsNone(await self.read())
        await self.routing.review_android(self.actor,self.review)
        before=await self.q.rows(SmartReminderRouting.__table__)
        self.assertEqual(await self.routing.review_android(self.actor,self.review),self.generation)
        self.assertEqual(await self.q.rows(SmartReminderRouting.__table__),before)
        with self.assertRaisesRegex(SmartReminderError,'routing_review_stale'):
            await self.routing.review_android(self.actor,replace(self.review,evidence_sha256='e'*64))
        proof=await self.read()
        self.assertEqual((proof.user_id,proof.job_id,proof.device_id,proof.session_id),
            (1,self.job_id,'device-1','session-1'))
        self.assertEqual((proof.generation,proof.evidence_sha256,proof.valid_until),
            (self.generation,'d'*64,self.q.expiry))
        self.assertTrue(all((proof.legacy_quiesced,proof.legacy_outcomes_reconciled,proof.other_study_fenced)))
        await self.p.no_delivery()

    async def test_native_and_telegram_review_cannot_be_substituted(self):
        await self.prepare_review();await self.reserve()
        with self.assertRaises(SmartReminderError):
            await self.routing.activate(self.actor,self.review)
        telegram=SmartReminderActor(1,'telegram_bot',telegram_id=3001)
        with self.assertRaises(SmartReminderError):
            await self.routing.activate(telegram,self.review)
        with self.assertRaises(SmartReminderError):
            await self.routing.review_android(self.actor,SimpleNamespace(**self.review.__dict__))
        # A Telegram-style held hash, even with populated metadata, cannot be
        # read as proof that review_android accepted the native account.
        async with self.q.sessions.begin() as session:
            await session.execute(update(SmartReminderRouting).values(telegram_binding='a'*64))
        self.assertIsNone(await self.read())

    async def test_inventory_change_after_hold_requires_a_new_hold(self):
        await self.hold()
        async with self.q.sessions.begin() as session:
            await session.execute(update(SmartReminderCapability).where(SmartReminderCapability.user_id==1)
                .values(generation=2))
        with self.assertRaisesRegex(SmartReminderError,'routing_review_stale'):
            await self.routing.review_android(self.actor,self.review)
        self.assertIsNone((await self.q.rows(SmartReminderRouting.__table__))[0]['verified_at'])

    async def test_review_window_cannot_precede_hold_be_future_or_outlive_inventory(self):
        await self.hold()
        for changes in ({'verified_at':self.q.tick-timedelta(seconds=1)},
                {'verified_at':self.q.tick+timedelta(seconds=1)},
                {'verified_until':self.q.expiry+timedelta(seconds=1)}):
            with self.subTest(changes=changes),self.assertRaisesRegex(SmartReminderError,'routing_review_stale'):
                await self.routing.review_android(self.actor,replace(self.review,**changes))
        self.assertIsNone((await self.q.rows(SmartReminderRouting.__table__))[0]['verified_at'])

    async def test_concurrent_different_reviews_have_one_winner_without_proof_overwrite(self):
        if not self.postgres:self.skipTest('Independent PostgreSQL User row locks required')
        await self.hold()
        results=await asyncio.gather(self.routing.review_android(self.actor,self.review),
            self.routing.review_android(self.actor,replace(self.review,evidence_sha256='e'*64)),return_exceptions=True)
        self.assertEqual(sum(type(v) is int for v in results),1)
        self.assertEqual(sum(isinstance(v,SmartReminderError) for v in results),1)
        row=(await self.q.rows(SmartReminderRouting.__table__))[0]
        self.assertEqual(row['evidence_sha256'],'d'*64 if type(results[0]) is int else 'e'*64)

    async def test_stored_review_drift_epoch_and_expiry_never_supply_fresh_admission(self):
        await self.prepare_review();await self.reserve()
        self.assertIsNotNone(await self.read())
        async with self.q.sessions.begin() as session:
            await session.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id==1)
                .values(grant_epoch=2))
        self.assertIsNone(await self.read())
        async with self.q.sessions.begin() as session:
            await session.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id==1)
                .values(grant_epoch=1))
            await session.execute(update(SmartReminderCapability).where(SmartReminderCapability.user_id==1)
                .values(generation=2))
        self.assertIsNone(await self.read())
        self.q.tick=self.q.expiry
        self.assertIsNone(await self.read())

    async def test_lease_or_any_existing_attempt_is_not_fresh_admission(self):
        await self.prepare_review();await self.reserve()
        async with self.q.sessions.begin() as session:
            await session.execute(update(JOB).where(JOB.c.id==self.job_id).values(
                lease_token=str(uuid4()),lease_expires_at=self.q.tick+timedelta(seconds=15)))
        self.assertIsNone(await self.read())
        async with self.q.sessions.begin() as session:
            await session.execute(update(JOB).where(JOB.c.id==self.job_id).values(lease_token=None,lease_expires_at=None))
            await session.execute(insert(ATTEMPT).values(id=str(uuid4()),job_id=self.job_id,attempt_key=uuid4().hex,
                channel='android',device_id='device-1',grant_epoch=1,state='prepared',prepared_at=self.q.tick,
                expires_at=self.q.expiry))
        self.assertIsNone(await self.read())
        self.assertEqual(await self.q.rows(GRANT),[])

    async def test_real_most_used_selected_device_gets_proof_without_foreign_rebinding(self):
        await self.p.second_phone();await self.prepare_review()
        result,=await self.runtime().tick()
        self.assertEqual((result.reason,result.device_id),('planned','device-2'))
        self.assertIsNone(await self.read(job_id=result.job_id))
        self.q.job_id=result.job_id;self.q.tick=self.p.due_clock
        await self.q.claim(uid=1,status=404)
        grant=await self.q.claim(uid=2)
        self.assertTrue(grant['dispatch_allowed']);await self.q.receipt(grant,uid=2)
        self.assertEqual(len(await self.q.rows(GRANT)),1)

    async def test_permission_loss_and_real_off_invalidate_without_new_proof(self):
        await self.prepare_review();await self.reserve()
        async with self.q.sessions.begin() as session:
            await session.execute(update(SmartReminderCapability).where(SmartReminderCapability.user_id==1)
                .values(study_notifications_allowed=False))
        self.assertIsNone(await self.read())
        async with self.q.sessions.begin() as session:
            await SmartReminderPreferencesService(session).patch(self.actor,SmartReminderPatch(
                request_id=str(uuid4()),expected_revision=2,master_enabled=False))
        self.assertIsNone(await self.read())
        self.assertEqual(await self.q.rows(GRANT),[])

    async def test_reader_does_not_flush_commit_write_or_select_transport_credentials(self):
        await self.prepare_review();await self.reserve()
        statements=[]
        def capture(c,cursor,sql,parameters,ctx,many):statements.append(sql.lower())
        event.listen(self.q.engine.sync_engine,'before_cursor_execute',capture)
        try:
            async with self.q.sessions() as session:
                other=await session.get(User,2);other.full_name='unsaved owned QA edit'
                self.assertIsNotNone(await self.reader(session,self.actor,self.job_id,self.q.tick))
                self.assertIn(other,session.dirty)
                self.assertTrue(session.in_transaction())
                await session.rollback()
        finally:event.remove(self.q.engine.sync_engine,'before_cursor_execute',capture)
        self.assertFalse(any(s.lstrip().startswith(('insert','update','delete')) for s in statements))
        self.assertFalse(any('select android_push_tokens.token' in s or 'select desktop_sessions.refresh_token_hash' in s
            for s in statements))
        self.assertIsNone(await self.read(job_id=str(uuid4())))


class SQLiteNativeAdmissionTests(NativeAdmissionChecks,unittest.IsolatedAsyncioTestCase):pass


@unittest.skipUnless(PG_URL,'Disposable loopback PostgreSQL required')
class PostgreSQLNativeAdmissionTests(NativeAdmissionChecks,unittest.IsolatedAsyncioTestCase):postgres=True

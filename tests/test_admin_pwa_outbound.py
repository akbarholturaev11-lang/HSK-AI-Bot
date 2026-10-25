"""Exact queued copy/audience and one durable claim before any provider IO."""
import asyncio
from datetime import datetime,timedelta,timezone
import hashlib
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport,AsyncClient
from pydantic import ValidationError
from sqlalchemy import event,func,select

from app.admin_api import pwa_outbound as api
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_outbound import (AdminPwaOutboundJob as Job,AdminPwaOutboundRecipient as Recipient,
    AdminPwaOutboundEvent)
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.payment import Payment
from app.db.models.user import User
from scripts.admin_pwa_outbound_retention import run as retention
from tests import test_admin_pwa_payment_review as fixtures
from tests import test_admin_pwa_settings as proofs
from tests import test_admin_pwa_settings_postgres as pg


class OutboundTests(fixtures.PaymentFixtures,unittest.IsolatedAsyncioTestCase):
    asyncSetUp=fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown=fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def prepare(self,**overrides):
        values=dict(kind='direct',user_id=2,texts=dict(uz='PRIVATE UZ',ru='PRIVATE RU',tj='PRIVATE TJ'))|overrides
        async with self.sessions() as db:
            result=await api.prepare_message(db,session_cookie=getattr(self,'cookie',fixtures.COOKIE),
                request=api.PrepareMessage(**values),settings_obj=self.settings)
        return api.MessageCommand.model_validate(result['execute_payload'])

    async def proof(self,command,*,signed=False):
        proxy=command if isinstance(command,api.MessageCommand) else SimpleNamespace(operation=command.operation_payload)
        return await proofs.AdminPwaSettingsTests.proof(self,proxy,signed=signed)

    async def execute(self,command,proof):
        async with self.sessions() as db:
            return await api.execute_message(db,session_cookie=getattr(self,'cookie',fixtures.COOKIE),
                request=api.ExecuteMessage(**command.model_dump(),step_up_id=proof),settings_obj=self.settings)

    async def dispatch(self,job,emitter,**extra):
        return await api.dispatch_message_batch(job_id=job,session_factory=self.sessions,settings_obj=self.settings,
            emit=emitter,**extra)

    async def test_signed_job_commits_before_single_attempt_and_never_copies_message_into_audit(self):
        command=await self.prepare();proof=await self.proof(command,signed=True);saved=await self.execute(command,proof)
        job=saved['job']['job_id']
        async def send(message):
            self.assertEqual((message.user_id,message.telegram_id),(2,2002))
            async with self.sessions() as db:
                self.assertEqual((await db.get(Recipient,(job,2))).status,'attempting')
                self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,'consumed')
                self.assertIsNotNone(await db.get(AdminPwaCommandAudit,job))
        emit=AsyncMock(side_effect=send)
        self.assertTrue(await self.dispatch(job,emit));self.assertFalse(await self.dispatch(job,emit))
        emit.assert_awaited_once()
        with self.assertRaises(api.CommandError):await self.execute(command,proof)
        async with self.sessions() as db:
            self.assertEqual((await db.get(Recipient,(job,2))).status,'attempted')
            self.assertNotIn('PRIVATE',(await db.get(AdminPwaCommandAudit,job)).result_json)
            self.assertEqual((await db.get(Payment,self.payment_id)).payment_status,'pending')
            self.assertEqual((await db.get(User,2)).status,'free')

    async def test_provider_timeout_or_partial_failure_is_uncertain_and_never_retried(self):
        command=await self.prepare();job=(await self.execute(command,await self.proof(command)))['job']['job_id']
        emit=AsyncMock(side_effect=RuntimeError('synthetic network uncertainty'))
        await self.dispatch(job,emit);await self.dispatch(job,emit)
        emit.assert_awaited_once()
        async with self.sessions() as db:
            self.assertEqual((await db.get(Recipient,(job,2))).status,'uncertain')
            self.assertEqual((await db.get(Job,job)).status,'complete')

    async def test_content_tamper_or_audience_change_rolls_back_without_job_or_spending_proof(self):
        command=await self.prepare();proof=await self.proof(command)
        changed=command.model_copy(update={'texts':api.MessageTexts(uz='changed',ru='changed',tj='changed')})
        with self.assertRaises(api.CommandError) as denied:await self.execute(changed,proof)
        self.assertEqual(denied.exception.status,403)
        async with self.sessions() as db:
            (await db.get(User,2)).language='uz';await db.commit()
        with self.assertRaises(api.CommandError) as stale:await self.execute(command,proof)
        self.assertEqual(stale.exception.status,409)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(Job)),0)
            self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,'verified')

    async def test_changed_recipient_and_revoked_session_stop_queued_work(self):
        command=await self.prepare();job=(await self.execute(command,await self.proof(command)))['job']['job_id']
        async with self.sessions() as db:
            (await db.get(User,2)).status='blocked';await db.commit()
        emit=AsyncMock();await self.dispatch(job,emit);emit.assert_not_awaited()
        async with self.sessions() as db:self.assertEqual((await db.get(Recipient,(job,2))).status,'skipped')
        command=await self.prepare(kind='test',user_id=None)
        job=(await self.execute(command,await self.proof(command)))['job']['job_id']
        async with self.sessions() as db:
            (await db.get(AdminPwaSession,self.session_id)).revoked_at=datetime.now(timezone.utc);await db.commit()
        await self.dispatch(job,emit);emit.assert_not_awaited()
        async with self.sessions() as db:self.assertEqual((await db.get(Recipient,(job,101))).status,'pending')

    async def test_eligible_broadcast_test_and_native_target_are_distinct_and_bounded(self):
        broadcast=await self.prepare(kind='broadcast',user_id=None)
        self.assertEqual(broadcast.audience_count,1)
        test=await self.prepare(kind='test',user_id=None)
        self.assertEqual(test.audience_count,1);self.assertNotEqual(test.audience_hash,broadcast.audience_hash)
        with self.assertRaises(api.CommandError):await self.prepare(user_id=1)
        with self.assertRaises(api.CommandError):await self.prepare(user_id=101)
        async with self.sessions() as db:
            db.add_all([User(telegram_id=10000+i,status='free') for i in range(1001)]);await db.commit()
        with self.assertRaises(api.CommandError) as too_many:await self.prepare(kind='broadcast',user_id=None)
        self.assertEqual(str(too_many.exception),'admin_pwa_message_too_many_targets')

    async def test_audit_failure_rolls_back_proof_and_job(self):
        command=await self.prepare();proof=await self.proof(command)
        def fail(mapper,connection,row):raise RuntimeError('synthetic audit failure')
        event.listen(AdminPwaCommandAudit,'before_insert',fail)
        try:
            with self.assertRaises(RuntimeError):await self.execute(command,proof)
        finally:event.remove(AdminPwaCommandAudit,'before_insert',fail)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(Job)),0)
            self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,'verified')

    async def test_new_session_needs_exact_signed_resume_and_resume_never_retries_attempting(self):
        command=await self.prepare(kind='broadcast',user_id=None)
        job=(await self.execute(command,await self.proof(command)))['job']['job_id']
        self.cookie='N'*64;new_session=str(uuid4())
        async with self.sessions() as db:
            (await db.get(AdminPwaSession,self.session_id)).revoked_at=datetime.now(timezone.utc)
            db.add(AdminPwaSession(id=new_session,user_id=101,auth_method='webauthn',
                token_hash=hashlib.sha256(self.cookie.encode()).hexdigest(),expires_at=datetime.now(timezone.utc)+timedelta(hours=1)))
            await db.commit()
        self.session_id=new_session
        async with self.sessions() as db:
            with self.assertRaises(api.CommandError):
                await api.authorize_message_run(db,session_cookie=self.cookie,request=api.RunMessage(job_id=job),settings_obj=self.settings)
        async with self.sessions() as db:
            prepared=await api.prepare_message_control(db,session_cookie=self.cookie,
                request=api.PrepareMessageControl(job_id=job,operation='resume'),settings_obj=self.settings)
        control=api.MessageControlCommand(**prepared['operation']['payload']);proof=await self.proof(control)
        async with self.sessions() as db:
            await api.execute_message_control(db,session_cookie=self.cookie,
                request=api.ExecuteMessageControl(**control.model_dump(),step_up_id=proof),settings_obj=self.settings)
        emit=AsyncMock();await self.dispatch(job,emit);emit.assert_awaited_once()
        await self.dispatch(job,emit);emit.assert_awaited_once()

    async def test_expiry_purges_only_private_payload_and_keeps_immutable_command_evidence(self):
        command=await self.prepare();job=(await self.execute(command,await self.proof(command)))['job']['job_id']
        async with self.sessions() as db:
            (await db.get(Job,job)).expires_at=datetime.now(timezone.utc)-timedelta(seconds=1);await db.commit()
        self.assertEqual((await retention(self.sessions))['candidates_in_page'],1)
        self.assertEqual((await retention(self.sessions,execute=True))['removed'],1)
        async with self.sessions() as db:
            self.assertIsNone(await db.get(Job,job));self.assertIsNotNone(await db.get(AdminPwaCommandAudit,job))
            self.assertEqual(await db.scalar(select(func.count()).select_from(Recipient)),0)

    async def test_stop_during_provider_io_cancels_remaining_targets_with_idempotent_real_session_audit(self):
        async with self.sessions() as db:
            db.add(User(id=3,telegram_id=2003,status='free'));await db.commit()
        command=await self.prepare(kind='broadcast',user_id=None)
        job=(await self.execute(command,await self.proof(command)))['job']['job_id']
        async def send(message):
            async with self.sessions() as db:
                result=await api.stop_message(db,session_cookie=fixtures.COOKIE,
                    request=api.RunMessage(job_id=job),settings_obj=self.settings)
                self.assertEqual(result['job']['status'],'closed')
        emit=AsyncMock(side_effect=send);await self.dispatch(job,emit);emit.assert_awaited_once()
        async with self.sessions() as db:
            await api.stop_message(db,session_cookie=fixtures.COOKIE,request=api.RunMessage(job_id=job),settings_obj=self.settings)
        async with self.sessions() as db:
            states=(await db.scalars(select(Recipient.status).where(Recipient.job_id==job))).all()
            self.assertEqual(sorted(states),['attempted','skipped'])
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaOutboundEvent)),1)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)),1)
            self.assertEqual((await db.get(Job,job)).status,'closed')

    async def test_stale_claim_can_be_closed_without_retrying_unknown_provider_effect(self):
        command=await self.prepare();job=(await self.execute(command,await self.proof(command)))['job']['job_id']
        async with self.sessions() as db:
            parent=await db.get(Job,job);parent.status='running';parent.started_at=datetime.now(timezone.utc)-timedelta(minutes=3)
            (await db.get(Recipient,(job,2))).status='attempting';await db.commit()
        async with self.sessions() as db:
            result=await api.prepare_message_control(db,session_cookie=fixtures.COOKIE,
                request=api.PrepareMessageControl(job_id=job,operation='close'),settings_obj=self.settings)
        control=api.MessageControlCommand(**result['operation']['payload']);proof=await self.proof(control)
        async with self.sessions() as db:
            await api.execute_message_control(db,session_cookie=fixtures.COOKIE,
                request=api.ExecuteMessageControl(**control.model_dump(),step_up_id=proof),settings_obj=self.settings)
        emit=AsyncMock();self.assertFalse(await self.dispatch(job,emit));emit.assert_not_awaited()
        async with self.sessions() as db:
            self.assertEqual((await db.get(Recipient,(job,2))).status,'uncertain')

    async def test_http_strict_origin_flags_and_large_copy_uses_compact_proof(self):
        command=await self.prepare(texts=dict(uz='汉'*3000,ru='я'*3000,tj='қ'*3000))
        self.assertLess(len(str(command.operation()).encode()),4096)
        await self.execute(command,await self.proof(command,signed=True))
        for change in ({'kind':'sql'},{'kind':'direct','user_id':True},{'kind':'test','user_id':2},
                       {'filters':{'sql':'SELECT *'}},{'texts':{'uz':'x','ru':'ok','tj':'ok'}}):
            with self.assertRaises(ValidationError):api.PrepareMessage(**({'kind':'direct','user_id':2,
                'texts':dict(uz='text',ru='text',tj='text')}|change))
        app=FastAPI();app.include_router(api.create_admin_pwa_outbound_router(settings_obj=self.settings,session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app),base_url='https://hskai.app',
                headers={'origin':'https://hskai.app'},cookies={api.ADMIN_PWA_COOKIE_NAME:fixtures.COOKIE}) as client:
            self.assertEqual((await client.post('/api/admin/v1/messages/read',json={},headers={'origin':'https://evil.invalid'})).status_code,403)
            self.settings.ADMIN_PWA_ENABLED=False
            for endpoint in ('read','prepare','save','run','stop','prepare-control','control'):
                self.assertEqual((await client.post('/api/admin/v1/messages/'+endpoint,json={})).status_code,404)


@unittest.skipUnless(os.environ.get('ADMIN_PWA_TEST_DATABASE_URL'),'requires disposable PostgreSQL')
class OutboundPostgresTests(fixtures.PaymentFixtures,unittest.IsolatedAsyncioTestCase):
    asyncSetUp=pg.AdminPwaSettingsPostgresTests.asyncSetUp
    asyncTearDown=pg.AdminPwaSettingsPostgresTests.asyncTearDown
    prepare=OutboundTests.prepare
    proof=OutboundTests.proof
    execute=OutboundTests.execute
    dispatch=OutboundTests.dispatch

    async def test_workers_share_one_durable_provider_claim(self):
        command=await self.prepare();job=(await self.execute(command,await self.proof(command)))['job']['job_id']
        entered,release=asyncio.Event(),asyncio.Event()
        async def hold(message):entered.set();await asyncio.wait_for(release.wait(),5)
        emit=AsyncMock(side_effect=hold);task=asyncio.create_task(self.dispatch(job,emit))
        try:
            await asyncio.wait_for(entered.wait(),5)
            self.assertFalse(await self.dispatch(job,emit));emit.assert_awaited_once()
            release.set();await asyncio.wait_for(task,5)
        finally:
            release.set()
            if not task.done():task.cancel();await asyncio.gather(task,return_exceptions=True)
        async with self.sessions() as db:self.assertEqual((await db.get(Recipient,(job,2))).status,'attempted')

    async def test_account_purge_removes_private_direct_payload_but_preserves_command_audit(self):
        from app.repositories.user_repo import UserRepository
        command=await self.prepare();job=(await self.execute(command,await self.proof(command)))['job']['job_id']
        async with self.sessions() as db:
            self.assertTrue(await UserRepository(db).delete_by_user_id(2));await db.commit()
        async with self.sessions() as db:
            self.assertIsNone(await db.get(Job,job));self.assertIsNone(await db.get(Recipient,(job,2)))
            self.assertIsNotNone(await db.get(AdminPwaCommandAudit,job))

    async def test_deleted_broadcast_recipient_is_reported_without_retry_and_stop_evidence_survives_expiry(self):
        from app.repositories.user_repo import UserRepository
        command=await self.prepare(kind='broadcast',user_id=None)
        job=(await self.execute(command,await self.proof(command)))['job']['job_id']
        async with self.sessions() as db:
            self.assertTrue(await UserRepository(db).delete_by_user_id(2));await db.commit()
        async with self.sessions() as db:
            result=await api.stop_message(db,session_cookie=fixtures.COOKIE,
                request=api.RunMessage(job_id=job),settings_obj=self.settings)
            self.assertEqual(result['job']['counts']['removed'],1)
            self.assertEqual(result['job']['status'],'closed')
        emit=AsyncMock();self.assertFalse(await self.dispatch(job,emit));emit.assert_not_awaited()
        async with self.sessions() as db:
            (await db.get(Job,job)).expires_at=datetime.now(timezone.utc)-timedelta(seconds=1);await db.commit()
        self.assertEqual((await retention(self.sessions,execute=True))['removed'],1)
        async with self.sessions() as db:
            self.assertIsNotNone(await db.get(AdminPwaCommandAudit,job))
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaOutboundEvent)),1)

    async def test_actual_migration_preserves_content_free_stop_evidence_after_private_cleanup(self):
        import importlib.util
        from pathlib import Path
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        async with self.sessions() as db:
            db.add(AdminPwaOutboundEvent(id=str(uuid4()),job_id=str(uuid4()),actor_user_id=101,
                operation='stop',created_at=datetime.now(timezone.utc)))
            await db.commit()
        path=Path(__file__).resolve().parents[1]/'alembic/versions/0129_admin_pwa_outbound.py'
        spec=importlib.util.spec_from_file_location('pwa_outbound_migration',path)
        migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
        async with self.engine.begin() as connection:
            def downgrade(sync):
                with Operations.context(MigrationContext.configure(sync)):migration.downgrade()
            with self.assertRaisesRegex(RuntimeError,'Archive private outbound state'):
                await connection.run_sync(downgrade)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaOutboundEvent)),1)

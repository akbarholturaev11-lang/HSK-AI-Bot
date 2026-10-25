"""Genuine proof-bound payout completion, private uploads and durable notices."""
import asyncio
from datetime import datetime, timedelta, timezone
import io
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import event,func,select

from app.admin_api import pwa_payout_completion as api
from app.admin_api.pwa_outbound import dispatch_message_batch
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_outbound import AdminPwaOutboundJob, AdminPwaOutboundRecipient
from app.db.models.admin_pwa_payout_proof import AdminPwaPayoutProof as Proof
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.partner import PartnerPayout
from app.db.models.payment import Payment
from app.db.models.user import User
from tests import test_admin_pwa_payment_review as fixtures
from tests import test_admin_pwa_partner_payouts as payouts
from tests import test_admin_pwa_settings_postgres as pg


def image_bytes():
    out=io.BytesIO();Image.new('RGB',(40,30),'#24637b').save(out,format='PNG');return out.getvalue()


class CompletionTests(fixtures.PaymentFixtures,unittest.IsolatedAsyncioTestCase):
    asyncSetUp=fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown=fixtures.AdminPwaPaymentReviewTests.asyncTearDown
    seed_partner=payouts.PayoutTests.seed_partner
    seed_payout=payouts.PayoutTests.seed_payout
    proof=payouts.PayoutTests.proof

    async def setup_payout(self, *, recipient=True):
        payout=await self.seed_payout(status='processing',processing_by_telegram_id=9001)
        if recipient:
            async with self.sessions() as db:
                db.add(User(id=3,telegram_id=7001,status='free',language='ru'));await db.commit()
        return payout

    def app(self,upload=None,loader=None):
        app=FastAPI();app.include_router(api.create_admin_pwa_payout_completion_router(
            settings_obj=self.settings,session_factory=self.sessions,upload=upload,loader=loader))
        return app

    async def stage(self,payout,upload=None):
        upload=upload or AsyncMock(return_value='SERVER_OWNED_PROVIDER_PROOF')
        async with AsyncClient(transport=ASGITransport(app=self.app(upload)),base_url='https://hskai.app',
            cookies={api.ADMIN_PWA_COOKIE_NAME:fixtures.COOKIE},headers={'origin':'https://hskai.app'}) as client:
            result=await client.post(f'/api/admin/v1/partner-payouts/{payout}/proof',content=image_bytes(),
                                    headers={'content-type':'image/png'})
            self.assertEqual(result.status_code,200,result.text)
        self.assertNotIn('SERVER_OWNED_PROVIDER_PROOF',result.text)
        self.assertNotIn('PRIVATE',result.text)
        return result.json()['proof_id']

    async def prepare(self,payout,proof):
        async with self.sessions() as db:
            result=await api.prepare_completion(db,session_cookie=fixtures.COOKIE,
                request=api.PrepareCompletion(payout_id=payout,proof_id=proof),settings_obj=self.settings)
        return api.CompletionCommand.model_validate(result['execute_payload'])

    async def execute(self,command,step):
        async with self.sessions() as db:
            return await api.execute_completion(db,session_cookie=fixtures.COOKIE,
                request=api.ExecuteCompletion(**command.model_dump(),step_up_id=step),settings_obj=self.settings)

    async def test_real_signed_completion_and_notice_claim_once_preserve_payment_and_access(self):
        payout=await self.setup_payout();asset=await self.stage(payout)
        command=await self.prepare(payout,asset);step=await self.proof(command,signed=True)
        result=await self.execute(command,step);self.assertEqual(result['payout']['status'],'paid')
        with self.assertRaises(api.CommandError):await self.execute(command,step)
        async with self.sessions() as db:
            row=await db.get(PartnerPayout,payout)
            self.assertEqual(row.proof_screenshot_file_id,'SERVER_OWNED_PROVIDER_PROOF')
            self.assertEqual((await db.get(Proof,asset)).status,'used')
            self.assertEqual((await db.get(Payment,self.payment_id)).payment_status,'pending')
            self.assertEqual((await db.get(User,3)).status,'free')
            audit=await db.get(AdminPwaCommandAudit,result['command_id'])
            self.assertNotIn('SERVER_OWNED_PROVIDER_PROOF',audit.result_json)
            self.assertNotIn('PRIVATE',audit.result_json)
        async def emit(message):
            self.assertEqual(message.telegram_id,7001)
            self.assertEqual(message.photo_file_id,'SERVER_OWNED_PROVIDER_PROOF')
            async with self.sessions() as db:
                self.assertEqual((await db.get(AdminPwaOutboundRecipient,(result['job_id'],3))).status,'attempting')
            raise TimeoutError('synthetic unknown network result')
        sender=AsyncMock(side_effect=emit)
        for _ in range(2):await dispatch_message_batch(job_id=result['job_id'],session_factory=self.sessions,
            settings_obj=self.settings,emit=sender)
        sender.assert_awaited_once()
        async with self.sessions() as db:self.assertEqual((await db.get(PartnerPayout,payout)).status,'paid')

    async def test_upload_claim_precedes_provider_io_and_no_db_image_blob_is_stored(self):
        payout=await self.setup_payout()
        async def upload(value):
            self.assertEqual(value.actor_telegram_id,9001);self.assertEqual(value.raw,image_bytes())
            async with self.sessions() as db:
                row=await db.scalar(select(Proof));self.assertEqual(row.status,'uploading')
                self.assertEqual(row.byte_count,len(image_bytes()))
            return 'SERVER_OWNED_PROVIDER_PROOF'
        await self.stage(payout,AsyncMock(side_effect=upload))
        self.assertNotIn('attachment_bytes',Proof.__table__.columns)

    async def test_mismatched_expired_used_or_foreign_proof_cannot_complete(self):
        payout=await self.setup_payout();asset=await self.stage(payout)
        command=await self.prepare(payout,asset);step=await self.proof(command)
        with self.assertRaises(api.CommandError) as tamper:
            await self.execute(command.model_copy(update={'proof_hash':'0'*64}),step)
        self.assertEqual(tamper.exception.status,403)
        async with self.sessions() as db:
            (await db.get(Proof,asset)).actor_user_id=2;await db.commit()
        with self.assertRaises(api.CommandError):await self.execute(command,step)
        async with self.sessions() as db:
            proof=await db.get(Proof,asset);proof.actor_user_id=101;proof.expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
            await db.commit()
        with self.assertRaises(api.CommandError):await self.prepare(payout,asset)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp,step)).status,'verified')
            self.assertEqual((await db.get(PartnerPayout,payout)).status,'processing')

    async def test_audit_failure_rolls_back_financial_completion_asset_and_notice(self):
        payout=await self.setup_payout();asset=await self.stage(payout)
        command=await self.prepare(payout,asset);step=await self.proof(command)
        with patch.object(api,'AdminPwaCommandAudit',side_effect=RuntimeError('synthetic audit failure')):
            with self.assertRaises(RuntimeError):await self.execute(command,step)
        async with self.sessions() as db:
            self.assertEqual((await db.get(Proof,asset)).status,'ready')
            self.assertEqual((await db.get(PartnerPayout,payout)).status,'processing')
            self.assertEqual((await db.get(AdminPwaStepUp,step)).status,'verified')
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaOutboundJob)),0)

    async def test_changed_recipient_or_destination_requires_new_review_and_missing_recipient_does_not_invent_delivery(self):
        payout=await self.setup_payout();asset=await self.stage(payout)
        command=await self.prepare(payout,asset);step=await self.proof(command)
        async with self.sessions() as db:
            (await db.get(User,3)).status='blocked';await db.commit()
        with self.assertRaises(api.CommandError) as changed:await self.execute(command,step)
        self.assertEqual(changed.exception.status,409)
        command=await self.prepare(payout,asset)
        result=await self.execute(command,await self.proof(command))
        self.assertIsNone(result['job_id']);self.assertEqual(result['payout']['status'],'paid')

    async def test_private_preview_rechecks_live_authority_after_provider_io(self):
        payout=await self.setup_payout();asset=await self.stage(payout)
        async def load(file_id):
            async with self.sessions() as db:
                (await db.get(AdminPwaSession,self.session_id)).revoked_at=datetime.now(timezone.utc);await db.commit()
            return image_bytes()
        async with AsyncClient(transport=ASGITransport(app=self.app(loader=load)),base_url='https://hskai.app',
            cookies={api.ADMIN_PWA_COOKIE_NAME:fixtures.COOKIE}) as client:
            response=await client.get('/api/admin/v1/payout-proofs/'+asset)
            self.assertEqual(response.status_code,401);self.assertNotEqual(response.content,image_bytes())

    async def test_expiry_cleanup_keeps_paid_proof_command_and_pending_notice(self):
        from scripts.admin_pwa_payout_proof_retention import run
        payout=await self.setup_payout();asset=await self.stage(payout)
        command=await self.prepare(payout,asset);result=await self.execute(command,await self.proof(command))
        async with self.sessions() as db:
            (await db.get(Proof,asset)).expires_at=datetime.now(timezone.utc)-timedelta(seconds=1);await db.commit()
        self.assertEqual((await run(self.sessions))['candidates_in_page'],1)
        self.assertEqual((await run(self.sessions,execute=True))['removed'],1)
        self.assertEqual((await run(self.sessions,execute=True))['removed'],0)
        async with self.sessions() as db:
            self.assertIsNone(await db.get(Proof,asset))
            self.assertEqual((await db.get(PartnerPayout,payout)).proof_screenshot_file_id,'SERVER_OWNED_PROVIDER_PROOF')
            self.assertIsNotNone(await db.get(AdminPwaCommandAudit,result['command_id']))
            self.assertIsNotNone(await db.get(AdminPwaOutboundJob,result['job_id']))

    async def test_upload_guards_bounds_failed_provider_and_shared_quota(self):
        payout=await self.setup_payout();sender=AsyncMock(side_effect=TimeoutError())
        async with AsyncClient(transport=ASGITransport(app=self.app(sender)),base_url='https://hskai.app',
            cookies={api.ADMIN_PWA_COOKIE_NAME:fixtures.COOKIE},headers={'origin':'https://hskai.app','content-type':'image/png'}) as client:
            url=f'/api/admin/v1/partner-payouts/{payout}/proof'
            for raw in (b'<svg>bad</svg>',b'x'*(api.MAX_BYTES+1)):
                self.assertEqual((await client.post(url,content=raw)).status_code,400)
            sender.assert_not_awaited()
            self.assertEqual((await client.post(url,content=image_bytes(),headers={'origin':'https://evil.invalid'})).status_code,403)
            for _ in range(20):
                self.assertEqual((await client.post(url,content=image_bytes())).status_code,503)
            self.assertEqual((await client.post(url,content=image_bytes())).status_code,429)
            self.assertEqual(sender.await_count,20)
            self.settings.ADMIN_PWA_ENABLED=False
            self.assertEqual((await client.post(url,content=image_bytes())).status_code,404)
        async with self.sessions() as db:
            self.assertEqual((await db.get(PartnerPayout,payout)).status,'processing')
            self.assertEqual(await db.scalar(select(func.count()).select_from(Proof).where(Proof.status=='failed')),20)


@unittest.skipUnless(os.environ.get('ADMIN_PWA_TEST_DATABASE_URL'),'requires disposable PostgreSQL')
class CompletionPostgresTests(CompletionTests):
    asyncSetUp=pg.AdminPwaSettingsPostgresTests.asyncSetUp
    asyncTearDown=pg.AdminPwaSettingsPostgresTests.asyncTearDown

    async def test_two_distinct_exact_proofs_cannot_complete_payout_twice(self):
        payout=await self.setup_payout();asset=await self.stage(payout);command=await self.prepare(payout,asset)
        steps=[await self.proof(command),await self.proof(command)]
        results=await asyncio.gather(*(self.execute(command,step) for step in steps),return_exceptions=True)
        self.assertEqual(sum(isinstance(value,dict) for value in results),1)
        self.assertEqual(next(value for value in results if isinstance(value,api.CommandError)).status,409)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)),1)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaOutboundJob)),1)

    async def test_step_expiry_during_real_payout_row_wait_rolls_back_completion(self):
        payout=await self.setup_payout();asset=await self.stage(payout)
        command=await self.prepare(payout,asset);step=await self.proof(command)
        waiting=asyncio.Event();advanced=False
        class Clock(datetime):
            @classmethod
            def now(cls,tz=None):return datetime.now(tz)+(timedelta(minutes=3) if advanced else timedelta())
        def observe(conn,cursor,statement,params,context,many):
            if (asyncio.current_task().get_name()=='waiting-payout-proof' and 'FROM partner_payouts' in statement
                    and 'FOR UPDATE' in statement):waiting.set()
        event.listen(self.engine.sync_engine,'before_cursor_execute',observe)
        task=None
        try:
            async with self.sessions() as blocker:
                async with blocker.begin():
                    await blocker.scalar(select(PartnerPayout).where(PartnerPayout.id==payout).with_for_update())
                    with patch.object(api,'datetime',Clock):
                        task=asyncio.create_task(self.execute(command,step),name='waiting-payout-proof')
                        await asyncio.wait_for(waiting.wait(),5);advanced=True
                        await blocker.commit()
                        with self.assertRaises(api.CommandError) as denied:await asyncio.wait_for(task,5)
                        self.assertEqual(denied.exception.status,403)
        finally:
            event.remove(self.engine.sync_engine,'before_cursor_execute',observe)
            if task is not None and not task.done():task.cancel();await asyncio.gather(task,return_exceptions=True)
        async with self.sessions() as db:
            self.assertEqual((await db.get(PartnerPayout,payout)).status,'processing')
            self.assertEqual((await db.get(Proof,asset)).status,'ready')
            self.assertEqual((await db.get(AdminPwaStepUp,step)).status,'verified')

    async def test_actual_migration_refuses_nonempty_private_proof_metadata(self):
        import importlib.util
        from pathlib import Path
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        payout=await self.setup_payout();asset=await self.stage(payout)
        path=Path(__file__).resolve().parents[1]/'alembic/versions/0130_admin_pwa_payout_proofs.py'
        spec=importlib.util.spec_from_file_location('pwa_payout_proof_migration',path)
        migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
        async with self.engine.begin() as connection:
            def downgrade(sync):
                with Operations.context(MigrationContext.configure(sync)):migration.downgrade()
            with self.assertRaisesRegex(RuntimeError,'Archive payout proof references'):
                await connection.run_sync(downgrade)
        async with self.sessions() as db:self.assertEqual((await db.get(Proof,asset)).status,'ready')

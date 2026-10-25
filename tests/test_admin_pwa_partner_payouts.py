"""Payout state remains exact, owner-reserved and independent of money transfer."""
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import event, func, select

from app.admin_api import pwa_partner_payouts as api
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.admin_pwa_webauthn import AdminPwaCredential
from app.db.models.partner import PartnerPayout
from app.db.models.payment import Payment
from app.db.models.portfolio import PortfolioTransaction
from app.db.models.user import User
from app.repositories.partner_repo import PartnerRepository
from tests import test_admin_pwa_payment_review as fixtures
from tests import test_admin_pwa_partners as partners
from tests import test_admin_pwa_settings as proofs
from tests import test_admin_pwa_settings_postgres as pg


class PayoutTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp=fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown=fixtures.AdminPwaPaymentReviewTests.asyncTearDown
    seed_partner=partners.PartnerTests.seed_partner

    async def seed_payout(self,**overrides):
        partner=await self.seed_partner()
        values=dict(partner_id=partner,amount_usd=Decimal('10.00'),exchange_rate=Decimal('10.9000'),
            local_amount=Decimal('109.00'),local_currency='TJS',status='pending',payment_method='bank',
            account_details='PRIVATE payout details',holder_name='PRIVATE holder',
            recipient_qr_code_file_id='PRIVATE telegram reference')|overrides
        async with self.sessions() as db:
            row=PartnerPayout(**values);db.add(row);await db.flush();payout=row.id;await db.commit()
        return payout

    async def prepare(self,payout,operation='deadline',days=3):
        async with self.sessions() as db:
            result=await api.prepare_payout(db,session_cookie=fixtures.COOKIE,
                request=api.PreparePayout(payout_id=payout,operation=operation,days=days),settings_obj=self.settings)
        return api.PayoutCommand.model_validate(result['operation']['payload'])

    async def proof(self,command,*,signed=False):
        return await proofs.AdminPwaSettingsTests.proof(self,
            SimpleNamespace(operation=command.operation_payload),signed=signed)

    async def execute(self,command,proof):
        async with self.sessions() as db:
            return await api.execute_payout(db,session_cookie=fixtures.COOKIE,
                request=api.ExecutePayout(**command.model_dump(),step_up_id=proof),settings_obj=self.settings)

    async def test_exact_signed_deadline_reservation_release_and_rejection_do_not_move_money(self):
        payout=await self.seed_payout();command=await self.prepare(payout);proof=await self.proof(command,signed=True)
        result=await self.execute(command,proof)
        self.assertEqual(result['payout']['deadline_at'],command.deadline_at)
        with self.assertRaises(api.CommandError):await self.execute(command,proof)
        for operation,expected in (('claim','processing'),('release','deadline_set'),('reject','rejected')):
            command=await self.prepare(payout,operation,None)
            self.assertEqual((await self.execute(command,await self.proof(command)))['payout']['status'],expected)
        async with self.sessions() as db:
            row=await db.get(PartnerPayout,payout)
            self.assertEqual(row.amount_usd,Decimal('10.00'));self.assertEqual(row.local_amount,Decimal('109.00'))
            self.assertIsNone(row.proof_screenshot_file_id)
            self.assertEqual(await db.scalar(select(func.count()).select_from(PortfolioTransaction)),0)
            self.assertEqual((await db.get(Payment,self.payment_id)).payment_status,'pending')
            self.assertEqual((await db.get(User,1)).status,'free')
            audits=(await db.scalars(select(AdminPwaCommandAudit))).all()
            self.assertEqual(len(audits),4);self.assertNotIn('PRIVATE',str([r.result_json for r in audits]))

    async def test_foreign_reservation_and_closed_payout_cannot_be_overridden(self):
        payout=await self.seed_payout(status='processing',processing_by_telegram_id=99999)
        for operation in ('claim','release','reject','deadline'):
            with self.assertRaises(api.CommandError) as denied:
                await self.prepare(payout,operation,1 if operation=='deadline' else None)
            self.assertEqual(denied.exception.status,409)
        async with self.sessions() as db:
            row=await db.get(PartnerPayout,payout);row.status='paid';await db.commit()
        with self.assertRaises(api.CommandError):await self.prepare(payout,'reject',None)

    async def test_tamper_or_changed_destination_rejects_without_spending_proof(self):
        payout=await self.seed_payout();command=await self.prepare(payout);proof=await self.proof(command)
        changed=command.model_copy(update={'deadline_at':(datetime.fromisoformat(command.deadline_at)+timedelta(days=1)).isoformat()})
        with self.assertRaises(api.CommandError) as denied:await self.execute(changed,proof)
        self.assertEqual(denied.exception.status,403)
        async with self.sessions() as db:
            (await db.get(PartnerPayout,payout)).account_details='changed destination';await db.commit()
        with self.assertRaises(api.CommandError) as stale:await self.execute(command,proof)
        self.assertEqual(stale.exception.status,409)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,'verified')
            self.assertEqual((await db.get(PartnerPayout,payout)).status,'pending')

    async def test_audit_failure_rolls_back_reservation_and_proof(self):
        payout=await self.seed_payout();command=await self.prepare(payout,'claim',None);proof=await self.proof(command)
        with patch.object(api,'AdminPwaCommandAudit',side_effect=RuntimeError('synthetic audit failure')):
            with self.assertRaises(RuntimeError):await self.execute(command,proof)
        async with self.sessions() as db:
            row=await db.get(PartnerPayout,payout);self.assertEqual(row.status,'pending')
            self.assertIsNone(row.processing_by_telegram_id)
            self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,'verified')

    async def test_bounded_metadata_page_and_strict_transport(self):
        payout=await self.seed_payout();statements=[]
        def collect(conn,cursor,statement,params,context,many):statements.append(statement.lower())
        app=FastAPI();app.include_router(api.create_admin_pwa_partner_payouts_router(
            settings_obj=self.settings,session_factory=self.sessions))
        event.listen(self.engine.sync_engine,'before_cursor_execute',collect)
        try:
            async with AsyncClient(transport=ASGITransport(app=app),base_url='https://hskai.app',
                    headers={'origin':'https://hskai.app'},cookies={ADMIN_PWA_COOKIE_NAME:fixtures.COOKIE}) as client:
                result=await client.post('/api/admin/v1/partner-payouts/read',json={})
                self.assertEqual(result.status_code,200);self.assertNotIn('PRIVATE',result.text)
                self.assertNotIn('account_details',' '.join(statements));statements.clear()
                detail=await client.post('/api/admin/v1/partner-payouts/read',json={'payout_id':payout})
                self.assertTrue(detail.json()['payout']['has_qr'])
                self.assertNotIn('telegram reference',detail.text)
                self.assertIn('no-store',detail.headers['cache-control'])
                self.assertEqual((await client.post('/api/admin/v1/partner-payouts/read',json={'all':True})).status_code,400)
                self.assertEqual((await client.post('/api/admin/v1/partner-payouts/read',json={},headers={'origin':'https://evil.invalid'})).status_code,403)
                self.settings.admin_id_list=[]
                self.assertEqual((await client.post('/api/admin/v1/partner-payouts/read',json={})).status_code,401)
                self.settings.ADMIN_PWA_ENABLED=False
                self.assertEqual((await client.post('/api/admin/v1/partner-payouts/read',json={})).status_code,404)
        finally:event.remove(self.engine.sync_engine,'before_cursor_execute',collect)
        self.assertFalse(any(q.lstrip().startswith(('insert ','update ','delete ')) for q in statements))
        for change in ({'days':True},{'days':1.0},{'days':2},{'operation':'paid'},
                       {'days':None},{'operation':'reject','days':1}):
            with self.assertRaises(ValidationError):
                api.PreparePayout(**({'payout_id':1,'operation':'deadline','days':1}|change))


@unittest.skipUnless(os.environ.get('ADMIN_PWA_TEST_DATABASE_URL'),'requires disposable PostgreSQL')
class PayoutPostgresTests(fixtures.PaymentFixtures,unittest.IsolatedAsyncioTestCase):
    asyncSetUp=pg.AdminPwaSettingsPostgresTests.asyncSetUp
    asyncTearDown=pg.AdminPwaSettingsPostgresTests.asyncTearDown
    seed_partner=PayoutTests.seed_partner
    seed_payout=PayoutTests.seed_payout
    prepare=PayoutTests.prepare
    proof=PayoutTests.proof
    execute=PayoutTests.execute

    async def test_two_admins_cannot_reserve_one_payout(self):
        payout=await self.seed_payout();command=await self.prepare(payout,'claim',None);proof=await self.proof(command)
        cookie='Z'*64;session_id,step_id=str(uuid4()),str(uuid4());now=datetime.now(timezone.utc)
        self.settings.admin_id_list.append(9002)
        async with self.sessions() as db:
            db.add(User(id=202,telegram_id=9002,status='active'));await db.flush()
            db.add(AdminPwaSession(id=session_id,user_id=202,token_hash=hashlib.sha256(cookie.encode()).hexdigest(),
                auth_method='webauthn',created_at=now,expires_at=now+timedelta(hours=1)))
            db.add(AdminPwaCredential(id=str(uuid4()),user_id=202,credential_id=b'second-payout-admin',
                public_key=b'verified-fixture',user_handle=b'second-payout-admin',sign_count=0,
                device_type='single_device',backed_up=False,created_at=now));await db.flush()
            operation=command.operation_payload()
            db.add(AdminPwaStepUp(id=step_id,session_id=session_id,user_id=202,action=operation['action'],target=operation['target'],
                payload_hash=api.operation_digest(**operation),challenge=b'Q'*32,status='verified',credential_id=b'second-payout-admin',
                verified_at=now,created_at=now,expires_at=now+timedelta(seconds=50)));await db.commit()
        async def second():
            async with self.sessions() as db:
                return await api.execute_payout(db,session_cookie=cookie,
                    request=api.ExecutePayout(**command.model_dump(),step_up_id=step_id),settings_obj=self.settings)
        results=await asyncio.gather(self.execute(command,proof),second(),return_exceptions=True)
        self.assertEqual(sum(isinstance(r,dict) for r in results),1)
        self.assertEqual(next(r for r in results if isinstance(r,api.CommandError)).status,409)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)),1)
            self.assertEqual((await db.get(PartnerPayout,payout)).status,'processing')

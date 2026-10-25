"""Partner state decisions preserve shared credit and account invariants."""
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import event, func, select

from app.admin_api import pwa_partners as api
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.partner import Partner, PartnerCredit
from app.db.models.payment import Payment
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.partner_service import PARTNER_SIGNUP_BONUS_USD_KEY
from tests import test_admin_pwa_payment_review as fixtures
from tests import test_admin_pwa_settings as proofs
from tests import test_admin_pwa_settings_postgres as pg


class PartnerTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def seed_partner(self, **overrides):
        values = dict(user_telegram_id=7001, status='pending', promotion_channel='PRIVATE promotion',
                      audience_size='1000', contact_username='PRIVATE contact') | overrides
        async with self.sessions() as db:
            row = Partner(**values); db.add(row); await db.flush(); result = row.id; await db.commit()
        return result

    async def prepare(self, partner_id, operation='approve'):
        async with self.sessions() as db:
            result = await api.prepare_partner(db, session_cookie=fixtures.COOKIE,
                request=api.PreparePartner(partner_id=partner_id, operation=operation), settings_obj=self.settings)
        return api.PartnerCommand.model_validate(result['operation']['payload'])

    async def proof(self, command, *, signed=False):
        return await proofs.AdminPwaSettingsTests.proof(self,
            SimpleNamespace(operation=command.operation_payload), signed=signed)

    async def execute(self, command, proof):
        async with self.sessions() as db:
            return await api.execute_partner(db, session_cookie=fixtures.COOKIE,
                request=api.ExecutePartner(**command.model_dump(), step_up_id=proof), settings_obj=self.settings)

    async def test_approve_real_signature_bonus_once_block_unblock_and_no_account_payment_change(self):
        partner = await self.seed_partner()
        async with self.sessions() as db:
            await BotSettingRepository(db).set(PARTNER_SIGNUP_BONUS_USD_KEY, '2.50'); await db.commit()
        command = await self.prepare(partner); proof = await self.proof(command, signed=True)
        result = await self.execute(command, proof)
        with self.assertRaises(api.CommandError): await self.execute(command, proof)
        self.assertEqual(result['partner']['status'], 'active')
        for operation in ('block', 'unblock'):
            command = await self.prepare(partner, operation)
            await self.execute(command, await self.proof(command))
        with self.assertRaises(api.CommandError): await self.prepare(partner, 'approve')
        async with self.sessions() as db:
            credits = (await db.scalars(select(PartnerCredit))).all()
            self.assertEqual(len(credits), 1); self.assertEqual(credits[0].amount_usd, Decimal('2.50'))
            self.assertTrue(credits[0].is_locked)
            self.assertEqual((await db.get(User, 1)).status, 'free')
            self.assertEqual((await db.get(Payment, self.payment_id)).payment_status, 'pending')
            audits = (await db.scalars(select(AdminPwaCommandAudit))).all()
            self.assertEqual(len(audits), 3)
            self.assertNotIn('PRIVATE', str([r.result_json for r in audits]))

    async def test_bonus_change_or_decision_tamper_cannot_execute_old_confirmation(self):
        partner = await self.seed_partner(); command = await self.prepare(partner); proof = await self.proof(command)
        with self.assertRaises(api.CommandError) as denied:
            await self.execute(command.model_copy(update={'operation': 'reject'}), proof)
        self.assertEqual(denied.exception.status, 403)
        async with self.sessions() as db:
            await BotSettingRepository(db).set(PARTNER_SIGNUP_BONUS_USD_KEY, '3.00'); await db.commit()
        with self.assertRaises(api.CommandError) as stale: await self.execute(command, proof)
        self.assertEqual(stale.exception.status, 409)
        async with self.sessions() as db:
            self.assertEqual((await db.get(Partner, partner)).status, 'pending')
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, 'verified')

    async def test_reject_and_atomic_audit_failure(self):
        partner = await self.seed_partner(); command = await self.prepare(partner, 'reject'); proof = await self.proof(command)
        with patch.object(api, 'AdminPwaCommandAudit', side_effect=RuntimeError('synthetic audit failure')):
            with self.assertRaises(RuntimeError): await self.execute(command, proof)
        async with self.sessions() as db:
            self.assertEqual((await db.get(Partner, partner)).status, 'pending')
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, 'verified')
        self.assertEqual((await self.execute(command, proof))['partner']['status'], 'rejected')
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(PartnerCredit)), 0)

    async def test_page_and_detail_reads_are_bounded_read_only_and_omit_transport_ids(self):
        for i in range(35): await self.seed_partner(user_telegram_id=7100+i)
        statements = []
        def collect(conn, cursor, statement, params, context, many): statements.append(statement.lower())
        event.listen(self.engine.sync_engine, 'before_cursor_execute', collect)
        try:
            async with self.sessions() as db:
                first = await api.read_partners(db, session_cookie=fixtures.COOKIE,
                    request=api.PartnerRead(), settings_obj=self.settings)
            async with self.sessions() as db:
                second = await api.read_partners(db, session_cookie=fixtures.COOKIE,
                    request=api.PartnerRead(before_id=first['next_before_id']), settings_obj=self.settings)
        finally: event.remove(self.engine.sync_engine, 'before_cursor_execute', collect)
        self.assertEqual((len(first['items']), len(second['items'])), (30, 5))
        self.assertNotIn('user_telegram_id', str(first))
        self.assertFalse(any(q.lstrip().startswith(('update ', 'insert ', 'delete ')) for q in statements))
        self.assertFalse(any('promotion_channel' in q or 'partner_credits' in q for q in statements))

    async def test_transport_strict_schema_origin_authority_and_flags(self):
        for request in ({'partner_id':True,'operation':'approve'}, {'partner_id':1,'operation':'pay'},
                        {'partner_id':1,'operation':'approve','bonus':100}):
            with self.assertRaises(ValidationError): api.PreparePartner(**request)
        app = FastAPI(); app.include_router(api.create_admin_pwa_partners_router(
            settings_obj=self.settings, session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app), base_url='https://hskai.app',
                headers={'origin':'https://hskai.app'}, cookies={ADMIN_PWA_COOKIE_NAME:fixtures.COOKIE}) as client:
            self.assertEqual((await client.post('/api/admin/v1/partners/read', json={'all':True})).status_code, 400)
            self.assertEqual((await client.post('/api/admin/v1/partners/read', json={},
                headers={'origin':'https://evil.invalid'})).status_code, 403)
            self.settings.admin_id_list=[]
            self.assertEqual((await client.post('/api/admin/v1/partners/read', json={})).status_code, 401)
            self.settings.ADMIN_PWA_ENABLED=False
            self.assertEqual((await client.post('/api/admin/v1/partners/read', json={})).status_code, 404)


@unittest.skipUnless(os.environ.get('ADMIN_PWA_TEST_DATABASE_URL'), 'requires disposable PostgreSQL')
class PartnerPostgresTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = pg.AdminPwaSettingsPostgresTests.asyncSetUp
    asyncTearDown = pg.AdminPwaSettingsPostgresTests.asyncTearDown
    seed_partner = PartnerTests.seed_partner
    prepare = PartnerTests.prepare
    proof = PartnerTests.proof
    execute = PartnerTests.execute

    async def test_proof_expiring_while_partner_is_locked_cannot_approve(self):
        partner = await self.seed_partner(); command = await self.prepare(partner); proof = await self.proof(command)
        async with self.sessions() as db:
            (await db.get(AdminPwaStepUp, proof)).expires_at = datetime.now(timezone.utc) + timedelta(seconds=.5)
            await db.commit()
        original = api._state; waiting = asyncio.Event(); task = None
        async def observe(db, partner_id, *, lock=False):
            if lock: waiting.set()
            return await original(db, partner_id, lock=lock)
        try:
            async with self.sessions() as legacy:
                async with legacy.begin():
                    await legacy.scalar(select(Partner).where(Partner.id == partner).with_for_update())
                    with patch.object(api, '_state', observe):
                        task = asyncio.create_task(self.execute(command, proof))
                        await asyncio.wait_for(waiting.wait(), 5)
                        self.assertFalse(task.done())
                        await asyncio.sleep(.55)
            with self.assertRaises(api.CommandError) as denied: await asyncio.wait_for(task, 5)
            self.assertEqual(denied.exception.status, 403)
            async with self.sessions() as db:
                self.assertEqual((await db.get(Partner, partner)).status, 'pending')
                self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, 'verified')
                self.assertEqual(await db.scalar(select(func.count()).select_from(PartnerCredit)), 0)
        finally:
            if task and not task.done(): task.cancel(); await asyncio.gather(task, return_exceptions=True)

    async def test_legacy_status_write_invalidates_waiting_confirmation(self):
        partner = await self.seed_partner(); command = await self.prepare(partner); proof = await self.proof(command)
        original = api._state; waiting = asyncio.Event(); task = None
        async def observe(db, partner_id, *, lock=False):
            if lock: waiting.set()
            return await original(db, partner_id, lock=lock)
        try:
            async with self.sessions() as legacy:
                async with legacy.begin():
                    row = await legacy.scalar(select(Partner).where(Partner.id == partner).with_for_update())
                    row.status='rejected'; await legacy.flush()
                    with patch.object(api, '_state', observe):
                        task=asyncio.create_task(self.execute(command, proof))
                        await asyncio.wait_for(waiting.wait(), 5)
                        self.assertFalse(task.done())
            with self.assertRaises(api.CommandError) as stale: await asyncio.wait_for(task, 5)
            self.assertEqual(stale.exception.status, 409)
            async with self.sessions() as db:
                self.assertEqual((await db.get(Partner, partner)).status, 'rejected')
                self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, 'verified')
                self.assertEqual(await db.scalar(select(func.count()).select_from(PartnerCredit)), 0)
        finally:
            if task and not task.done(): task.cancel(); await asyncio.gather(task, return_exceptions=True)

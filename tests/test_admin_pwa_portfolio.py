"""Manual financial facts are exact, atomic and independent of entitlements."""
import asyncio
import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import event, func, select

from app.admin_api import pwa_portfolio as api
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.payment import Payment
from app.db.models.portfolio import PortfolioTransaction
from app.db.models.user import User
from app.services import portfolio_service
from tests import test_admin_pwa_payment_review as fixtures
from tests import test_admin_pwa_settings as proof_fixtures
from tests import test_admin_pwa_settings_postgres as pg


class PortfolioTests(fixtures.PaymentFixtures,unittest.IsolatedAsyncioTestCase):
    asyncSetUp=fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown=fixtures.AdminPwaPaymentReviewTests.asyncTearDown
    proof=proof_fixtures.AdminPwaSettingsTests.proof

    async def prepare(self,**overrides):
        values={'transaction_type':'expense','amount_minor':1299,'currency':'TJS','note':'PRIVATE invoice note'}|overrides
        async with self.sessions() as db:
            result=await api.prepare_portfolio(db,session_cookie=fixtures.COOKIE,
                request=api.PreparePortfolio(**values),settings_obj=self.settings)
        return api.PortfolioCommand.model_validate(result['operation']['payload'])

    async def execute(self,command,proof):
        async with self.sessions() as db:
            return await api.execute_portfolio(db,session_cookie=fixtures.COOKIE,
                request=api.ExecutePortfolio(**command.model_dump(),step_up_id=proof),settings_obj=self.settings)

    async def test_real_signed_entry_reuses_conversion_without_payment_access_or_duplicate(self):
        command=await self.prepare();proof=await self.proof(command,signed=True)
        result=await self.execute(command,proof)
        self.assertEqual(result['transaction']['amount_minor'],1299)
        with self.assertRaises(api.CommandError):
            await self.execute(command,proof)
        async with self.sessions() as db:
            row=await db.get(PortfolioTransaction,result['transaction']['id'])
            self.assertEqual(row.original_amount,12.99);self.assertEqual(row.original_currency,'TJS')
            self.assertEqual(format(row.amount_usd,'.17g'),command.expected_usd)
            self.assertEqual(row.source,'manual_expense');self.assertIsNone(row.payment_id)
            self.assertEqual((await db.get(Payment,self.payment_id)).payment_status,'pending')
            self.assertEqual((await db.get(User,1)).status,'free')
            audit=await db.get(AdminPwaCommandAudit,result['command_id'])
            self.assertNotIn('PRIVATE',audit.result_json);self.assertEqual(audit.action,'portfolio.add')
            self.assertEqual(await db.scalar(select(func.count()).select_from(PortfolioTransaction)),1)

    async def test_conversion_change_and_payload_tamper_reject_without_consuming_proof(self):
        command=await self.prepare();proof=await self.proof(command)
        changed=command.model_copy(update={'amount_minor':1300})
        with self.assertRaises(api.CommandError) as tampered:
            await self.execute(changed,proof)
        self.assertEqual(tampered.exception.status,403)
        with patch.object(portfolio_service,'USD_TO_SOMONI',portfolio_service.USD_TO_SOMONI+1):
            with self.assertRaises(api.CommandError) as stale:
                await self.execute(command,proof)
        self.assertEqual(stale.exception.status,409)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(PortfolioTransaction)),0)
            self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,'verified')

    async def test_audit_failure_rolls_back_entry_and_proof(self):
        command=await self.prepare(currency='USD');proof=await self.proof(command)
        with patch.object(api,'AdminPwaCommandAudit',side_effect=RuntimeError('synthetic audit failure')):
            with self.assertRaises(RuntimeError):
                await self.execute(command,proof)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(PortfolioTransaction)),0)
            self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,'verified')

    async def test_manual_keysets_never_sync_or_query_payments_and_do_not_return_admin_identifiers(self):
        async with self.sessions() as db:
            db.add_all([PortfolioTransaction(transaction_type='profit',source='manual_profit',amount_usd=1,
                original_amount=1,original_currency='USD',note='QA') for _ in range(35)])
            await db.commit()
        statements=[]
        def record(conn,cursor,statement,parameters,context,many):statements.append(statement.lower())
        event.listen(self.engine.sync_engine,'before_cursor_execute',record)
        try:
            async with self.sessions() as db:
                first=await api.read_portfolio(db,session_cookie=fixtures.COOKIE,
                    request=api.PortfolioRead(),settings_obj=self.settings)
            async with self.sessions() as db:
                second=await api.read_portfolio(db,session_cookie=fixtures.COOKIE,
                    request=api.PortfolioRead(before_id=first['next_before_id']),settings_obj=self.settings)
        finally:event.remove(self.engine.sync_engine,'before_cursor_execute',record)
        self.assertEqual((len(first['items']),len(second['items'])),(30,5))
        self.assertFalse(any('from payments' in q or q.lstrip().startswith(('update ','insert ','delete ')) for q in statements))
        self.assertNotIn('admin_telegram_id',str(first));self.assertNotIn('user_telegram_id',str(first))
        self.assertFalse({r['id'] for r in first['items']} & {r['id'] for r in second['items']})

    async def test_strict_money_auth_and_origin(self):
        base={'transaction_type':'profit','amount_minor':100,'currency':'USD','note':'QA'}
        for changed in ({'amount_minor':True},{'amount_minor':1.5},{'amount_minor':'100'},
                        {'amount_minor':0},{'amount_minor':100_000_001},{'currency':'BTC'},
                        {'note':'x'},{'note':'\ud800'},{'target_user_id':1}):
            with self.assertRaises(ValidationError):api.PreparePortfolio.model_validate(base|changed)
        app=FastAPI();app.include_router(api.create_admin_pwa_portfolio_router(
            settings_obj=self.settings,session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app),base_url='https://hskai.app',
                headers={'origin':'https://hskai.app'},cookies={ADMIN_PWA_COOKIE_NAME:fixtures.COOKIE}) as client:
            self.assertEqual((await client.post('/api/admin/v1/portfolio/read',json={'all':True})).status_code,400)
            self.assertEqual((await client.post('/api/admin/v1/portfolio/prepare',json=base,
                headers={'origin':'https://evil.invalid'})).status_code,403)
            self.settings.admin_id_list=[]
            self.assertEqual((await client.post('/api/admin/v1/portfolio/read',json={})).status_code,401)
            self.settings.ADMIN_PWA_ENABLED=False
            self.assertEqual((await client.post('/api/admin/v1/portfolio/read',json={})).status_code,404)

    async def test_legacy_subcent_values_are_not_displayed_as_zero(self):
        async with self.sessions() as db:
            db.add(PortfolioTransaction(transaction_type='expense',source='manual_expense',amount_usd=0.000000001,
                original_amount=0.001,original_currency='USD',note='Legacy precision'))
            await db.commit()
        async with self.sessions() as db:
            result=await api.read_portfolio(db,session_cookie=fixtures.COOKIE,
                request=api.PortfolioRead(),settings_obj=self.settings)
        self.assertEqual(result['items'][0]['amount'],'0.001')
        self.assertGreater(float(result['items'][0]['amount_usd']),0)


@unittest.skipUnless(os.environ.get('ADMIN_PWA_TEST_DATABASE_URL'),'requires disposable PostgreSQL')
class PortfolioPostgresTests(fixtures.PaymentFixtures,unittest.IsolatedAsyncioTestCase):
    asyncSetUp=pg.AdminPwaSettingsPostgresTests.asyncSetUp
    asyncTearDown=pg.AdminPwaSettingsPostgresTests.asyncTearDown
    prepare=PortfolioTests.prepare
    proof=PortfolioTests.proof
    execute=PortfolioTests.execute

    async def test_two_workers_cannot_append_twice_with_one_proof(self):
        command=await self.prepare();proof=await self.proof(command)
        results=await asyncio.gather(self.execute(command,proof),self.execute(command,proof),return_exceptions=True)
        self.assertEqual(sum(isinstance(r,dict) for r in results),1)
        denied=next(r for r in results if isinstance(r,api.CommandError));self.assertEqual(denied.status,403)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(PortfolioTransaction)),1)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)),1)

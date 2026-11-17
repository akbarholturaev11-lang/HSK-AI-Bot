"""Real PostgreSQL concurrency for lava.top activation (row locks, unique keys).

Skipped unless LAVA_TEST_DATABASE_URL points to a disposable database, e.g.
postgresql+asyncpg://postgres@127.0.0.1:55439/lavaconc . All tables in that
database are dropped and recreated.
"""
import asyncio
import os
import unittest
from datetime import timedelta, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.lava import LavaInvoice, LavaWebhookEvent
from app.db.models.payment import Payment
from app.db.models.user import User
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.lava import events
from app.services.lava.checkout import LavaCheckoutService
from app.services.lava.config import LavaConfigService, config_from_dict
from app.services.lava.reconcile import LavaReconcileWorker
from tests.lava_fakes import OFFER_ID, WEBHOOK_SECRET, FakeLava, make_runtime, payment_webhook

URL = os.environ.get("LAVA_TEST_DATABASE_URL", "")


@unittest.skipUnless(URL.startswith("postgresql+asyncpg://"), "LAVA_TEST_DATABASE_URL not set")
class LavaPostgresConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(URL, pool_size=10)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(User(id=1, telegram_id=1001, full_name="Learner", language="uz", status="free"))
            await LavaConfigService(session).save(config_from_dict({
                "checkout_mode": "both", "currency": "USD",
                "plans": {"1_month": {"enabled": True, "offer_id": OFFER_ID}},
            }))
            await session.commit()
        self.fake = FakeLava()
        self.runtime = make_runtime(self.sessions, self.fake)
        patcher = patch.object(AIUsageBudgetService, "_live_or_manual_usd_rates",
                               new=AsyncMock(return_value={"tjs": 10, "cny": 7}))
        patcher.start()
        self.addCleanup(patcher.stop)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _paid_contract(self):
        started = await LavaCheckoutService(self.runtime).start(
            self.sessions, user_id=1, plan_type="1_month", email="b@x.co", source="miniapp", language="uz")
        contract = started["payment_url"].rsplit("/", 1)[1]
        self.fake.complete(contract)
        return contract

    async def _counts(self):
        async with self.sessions() as session:
            payments = await session.scalar(select(func.count(Payment.id)))
            user = await session.get(User, 1)
            return payments, user

    async def test_concurrent_webhooks_recheck_and_reconcile_grant_once(self):
        contract = await self._paid_contract()
        raw = payment_webhook("payment.success", contract, email="b@x.co")
        worker = LavaReconcileWorker(self.runtime, instance_id="pg")
        results = await asyncio.gather(
            events.ingest(self.runtime, raw, api_key_header=WEBHOOK_SECRET, client_ip=None),
            events.ingest(self.runtime, raw, api_key_header=WEBHOOK_SECRET, client_ip=None),
            events.verify_and_apply(self.runtime, contract),
            events.verify_and_apply(self.runtime, contract),
            worker.check_open_invoices(),
            return_exceptions=True,
        )
        self.assertFalse([r for r in results if isinstance(r, Exception)], results)
        payments, user = await self._counts()
        self.assertEqual(payments, 1)
        end = user.end_date if user.end_date.tzinfo else user.end_date.replace(tzinfo=timezone.utc)
        start = user.start_date if user.start_date.tzinfo else user.start_date.replace(tzinfo=timezone.utc)
        self.assertEqual((end - start).days, 30)
        async with self.sessions() as session:
            self.assertEqual(await session.scalar(select(func.count(LavaWebhookEvent.id))), 1)
            row = (await session.execute(select(LavaInvoice))).scalar_one()
            self.assertEqual((row.status, row.granted_days), ("paid", 30))

    async def test_concurrent_renewal_deliveries_extend_once(self):
        contract = await self._paid_contract()
        await events.verify_and_apply(self.runtime, contract)
        _, before = await self._counts()
        renewal = self.fake.add_renewal(contract)
        raw = payment_webhook("subscription.recurring.payment.success", renewal, parent=contract, email="b@x.co")
        await asyncio.gather(*[events.ingest(self.runtime, raw, api_key_header=WEBHOOK_SECRET, client_ip=None)
                               for _ in range(3)],
                             events.verify_and_apply(self.runtime, renewal, expected_parent=contract, renewal=True))
        payments, after = await self._counts()
        self.assertEqual(payments, 2)
        self.assertEqual(after.end_date - before.end_date, timedelta(days=30))

    async def test_native_exit_claim_and_provider_verification_share_one_canonical_offer(self):
        from app.db.models.pwa_exit_offer import PwaExitOffer
        from app.services.pwa_exit_offer_service import PwaExitOfferService
        async with self.sessions() as db:
            await LavaConfigService(db).save(config_from_dict({
                "checkout_mode":"both", "currency":"USD",
                "plans":{"1_month":{"enabled":True,"offer_id":OFFER_ID,
                                      "price":{"amount":"10.00","currency":"USD"}}},
                "promo_codes":{"exit_offer:20":"NATIVEEXIT20"},
            }))
            await db.commit()
        self.fake.promo_codes["NATIVEEXIT20"] = 20
        async def action(kind):
            async with self.sessions() as db:
                user = await db.get(User,1)
                value = await PwaExitOfferService(db,self.runtime.settings).action(user,action=kind)
                await db.commit()
                return value
        first, second = await asyncio.gather(action("view"),action("view"))
        self.assertEqual(first["expires_at"],second["expires_at"])
        await action("claim")
        checkout = await LavaCheckoutService(self.runtime).start(
            self.sessions,user_id=1,plan_type="1_month",email="native@example.com",
            source="android",language="uz",context_mode="exit_discount")
        contract=checkout["payment_url"].rsplit("/",1)[1]
        self.fake.complete(contract)
        await asyncio.gather(events.verify_and_apply(self.runtime,contract),
                             events.verify_and_apply(self.runtime,contract))
        payments,_=await self._counts()
        self.assertEqual(1,payments)
        async with self.sessions() as db:
            self.assertEqual(1,await db.scalar(select(func.count(PwaExitOffer.user_id))))
            self.assertIsNotNone((await db.get(PwaExitOffer,1)).consumed_at)
            invoice=await db.scalar(select(LavaInvoice).where(LavaInvoice.contract_id==contract))
            self.assertEqual(("android",20,30),(invoice.source,invoice.discount_percent,invoice.granted_days))
        self.assertFalse((await action("view"))["available"])

    async def test_reconcile_lease_has_a_single_runner(self):
        first = LavaReconcileWorker(self.runtime, instance_id="a")
        second = LavaReconcileWorker(self.runtime, instance_id="b")
        self.assertTrue(await first._acquire_lease())
        self.assertFalse(await second._acquire_lease())
        # Locking/join SQL of every reconcile job is valid on PostgreSQL.
        contract = await self._paid_contract()
        await events.verify_and_apply(self.runtime, contract)
        self.fake.add_renewal(contract)
        self.assertEqual(await first.check_subscriptions(), 1)
        await first.alert_overdue_renewals()
        self.assertEqual(await first.drain_events(), 0)


if __name__ == "__main__":
    unittest.main()

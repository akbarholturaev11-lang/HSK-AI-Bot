"""In-app discounts reach lava.top only through admin-mapped promo codes."""
import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.lava import LavaInvoice
from app.db.models.payment import Payment
from app.db.models.portfolio import PortfolioTransaction
from app.db.models.user import User
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.discount_service import DiscountChoice, DiscountService
from app.services.lava import events
from app.services.lava.checkout import LavaCheckoutError, LavaCheckoutService
from app.services.lava.config import LavaConfigError, LavaConfigService, config_from_dict
from tests.lava_fakes import OFFER_ID, WEBHOOK_SECRET, FakeLava, make_runtime, payment_webhook

REFERRAL = DiscountChoice(source="referral", percent=20, title="Referral 3/3")


def _config(promo_codes=None, enabled=("1_month", "3_months")):
    return config_from_dict({
        "checkout_mode": "both", "currency": "USD",
        "plans": {plan: {"enabled": True, "offer_id": OFFER_ID,
                         "price": {"amount": {"1_month": "7.90", "3_months": "19.00"}[plan], "currency": "USD"}}
                  for plan in enabled},
        "promo_codes": promo_codes or {},
    })


class LavaPromoCodeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(User(id=1, telegram_id=1001, full_name="Learner", language="uz", status="free",
                             discount_eligible=True, discount_used=False))
            await LavaConfigService(session).save(_config({"referral:20": "HSKREF20"}))
            await session.commit()
        self.fake = FakeLava()
        self.fake.prices.update({"MONTHLY": "7.90", "PERIOD_90_DAYS": "19.00"})
        self.fake.promo_codes = {"HSKREF20": 20}
        self.runtime = make_runtime(self.sessions, self.fake)
        self.service = LavaCheckoutService(self.runtime)
        for patcher in (
            patch.object(AIUsageBudgetService, "_live_or_manual_usd_rates",
                         new=AsyncMock(return_value={"tjs": 10, "cny": 7})),
            patch.object(DiscountService, "get_best_discount", new=AsyncMock(return_value=REFERRAL)),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _block(self, mode="subscription"):
        async with self.sessions() as session:
            user = await session.get(User, 1)
            return await self.service.overview_block(session, user, supports_lava=True, context_mode=mode)

    def test_promo_code_validation_follows_lava_rules(self):
        self.assertEqual(_config({"admin_campaign:30": "SPRING-30"}).promo_code("admin_campaign", 30), "SPRING-30")
        for bad in ({"referral:20": "x"}, {"referral:20": "bad code!"}, {"other:20": "OKCODE"},
                    {"referral:0": "OKCODE"}, {"referral:95": "OKCODE"}):
            with self.subTest(bad=bad), self.assertRaises(LavaConfigError):
                _config(bad)

    async def test_overview_shows_discounted_lava_price_only_with_a_mapped_code(self):
        block = await self._block()
        month = next(plan for plan in block["plans"] if plan["plan_type"] == "1_month")
        self.assertEqual((month["discount_percent"], month["base_amount"], month["amount"]), (20, "7.90", "6.32"))
        async with self.sessions() as session:
            await LavaConfigService(session).save(_config())
            await session.commit()
        block = await self._block()
        self.assertNotIn("discount_percent", block["plans"][0])
        self.assertEqual(block["plans"][0]["amount"], "7.90")

    async def test_discount_flow_without_mapping_stays_manual(self):
        async with self.sessions() as session:
            await LavaConfigService(session).save(_config())
            await session.commit()
        with patch.object(DiscountService, "get_feedback_price_discount",
                          new=AsyncMock(return_value=DiscountChoice(source="feedback_price_offer", percent=20))):
            self.assertIsNone(await self._block("feedback_discount"))
            with self.assertRaises(LavaCheckoutError) as ctx:
                await self.service.start(self.sessions, user_id=1, plan_type="1_month", email="a@b.co",
                                         source="miniapp", language="uz", context_mode="feedback_discount")
        self.assertEqual(ctx.exception.code, "discount_unavailable")

    async def test_promo_checkout_activates_with_discount_and_marks_referral_used(self):
        started = await self.service.start(self.sessions, user_id=1, plan_type="1_month", email="a@b.co",
                                           source="miniapp", language="uz")
        self.assertEqual(self.fake.last_create_body["promoCode"], "HSKREF20")
        self.assertEqual(started["amount"], "6.32")
        contract = started["payment_url"].rsplit("/", 1)[1]
        self.fake.complete(contract)
        result = await events.ingest(self.runtime, payment_webhook("payment.success", contract, amount="6.32"),
                                     api_key_header=WEBHOOK_SECRET, client_ip=None)
        self.assertEqual(result[1]["result"], "applied")
        async with self.sessions() as session:
            payment = (await session.execute(select(Payment))).scalar_one()
            user = await session.get(User, 1)
            invoice = (await session.execute(select(LavaInvoice))).scalar_one()
            profit = (await session.execute(select(PortfolioTransaction))).scalar_one()
        self.assertEqual((payment.discount_source, payment.discount_percent, payment.local_amount),
                         ("referral", 20, "6.32"))
        self.assertTrue(user.discount_used)
        self.assertIsNone(invoice.review_reason)  # expected 6.32 == paid 6.32
        # Exact decimal revenue, not the rounded integer column.
        self.assertAlmostEqual(profit.amount_usd, 6.32, places=2)

    async def test_renewal_after_promo_is_full_price_without_mismatch_alert(self):
        started = await self.service.start(self.sessions, user_id=1, plan_type="1_month", email="a@b.co",
                                           source="miniapp", language="uz")
        parent = started["payment_url"].rsplit("/", 1)[1]
        self.fake.complete(parent)
        await events.verify_and_apply(self.runtime, parent)
        renewal = self.fake.add_renewal(parent)
        self.fake.invoices[renewal]["amount"] = "7.90"
        await events.verify_and_apply(self.runtime, renewal, expected_parent=parent, renewal=True)
        async with self.sessions() as session:
            payments = list((await session.execute(select(Payment).order_by(Payment.id))).scalars())
            renewal_row = (await session.execute(select(LavaInvoice).where(LavaInvoice.kind == "renewal"))).scalar_one()
        self.assertEqual([(p.discount_source, p.local_amount) for p in payments],
                         [("referral", "6.32"), ("none", "7.90")])
        self.assertIsNone(renewal_row.review_reason)

    async def test_unknown_code_in_lava_fails_closed_and_alerts_admin(self):
        self.fake.promo_codes = {}
        with self.assertRaises(LavaCheckoutError) as ctx:
            await self.service.start(self.sessions, user_id=1, plan_type="1_month", email="a@b.co",
                                     source="miniapp", language="uz")
        self.assertEqual(ctx.exception.code, "provider_unavailable")
        self.assertIn("promo_rejected", [code for code, _ in self.runtime.notifier.alerts])


if __name__ == "__main__":
    unittest.main()

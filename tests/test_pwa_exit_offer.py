"""PWA 20% exit offer: server ownership, one-time claim and verified Lava grant."""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.pwa_exit_offer import PwaExitOffer
from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from app.db.models.lava import LavaInvoice
from app.db.models.user import User
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.discount_service import DiscountChoice, DiscountService
from app.services.lava import events
from app.services.lava.checkout import LavaCheckoutError, LavaCheckoutService
from app.services.lava.config import LavaConfigService, config_from_dict
from app.services.pwa_exit_offer_service import PwaExitOfferService
from tests.lava_fakes import FakeLava, OFFER_ID, make_runtime


def config(promo="HSKEXIT20"):
    return config_from_dict({
        "checkout_mode": "both", "currency": "USD",
        "plans": {
            "1_month": {"enabled": True, "offer_id": OFFER_ID,
                        "price": {"amount": "10.00", "currency": "USD"}},
            "12_months": {"enabled": True, "offer_id": OFFER_ID,
                          "price": {"amount": "90.00", "currency": "USD"}}
        },
        "promo_codes": {"exit_offer:20": promo} if promo else {},
    })


class PwaExitOfferTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as db:
            db.add(User(id=1, telegram_id=1001, full_name="Student", language="ru", status="free"))
            await LavaConfigService(db).save(config())
            await db.commit()
        self.fake = FakeLava()
        self.fake.promo_codes = {"HSKEXIT20": 20}
        self.runtime = make_runtime(self.sessions, self.fake)
        self.checkout = LavaCheckoutService(self.runtime)
        for patcher in (
            patch.object(AIUsageBudgetService, "_live_or_manual_usd_rates",
                         new=AsyncMock(return_value={"tjs": 10, "cny": 7})),
            patch.object(DiscountService, "get_best_discount",
                         new=AsyncMock(return_value=DiscountChoice())),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def action(self, verb):
        async with self.sessions() as db:
            user = await db.get(User, 1)
            answer = await PwaExitOfferService(db, self.runtime.settings).action(user, action=verb)
            await db.commit()
            return answer

    async def test_x_intent_required_and_offer_is_one_time(self):
        self.assertFalse((await self.action("claim"))["available"])
        viewed = await self.action("view")
        self.assertTrue(viewed["available"])
        self.assertFalse(viewed["accepted"])
        self.assertTrue((await self.action("claim"))["accepted"])
        again = await self.action("view")
        self.assertEqual(viewed["expires_at"], again["expires_at"])
        async with self.sessions() as db:
            user = await db.get(User, 1)
            self.assertTrue(await PwaExitOfferService(db, self.runtime.settings).active(user))
            row = await db.get(PwaExitOffer, 1)
            row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await db.commit()
        self.assertFalse((await self.action("view"))["available"])

    async def test_missing_provider_mapping_never_offers_discount(self):
        async with self.sessions() as db:
            await LavaConfigService(db).save(config(promo=""))
            await db.commit()
        self.assertFalse((await self.action("view"))["available"])

    async def test_unclaimed_mode_fails_closed(self):
        with self.assertRaises(LavaCheckoutError) as caught:
            await self.checkout.start(self.sessions, user_id=1, plan_type="1_month",
                                      email="student@example.com", source="pwa",
                                      language="ru", context_mode="exit_discount")
        self.assertEqual(caught.exception.code, "discount_unavailable")
        await self.action("view")
        with self.assertRaises(LavaCheckoutError) as caught:
            await self.checkout.start(self.sessions, user_id=1, plan_type="1_month",
                                      email="student@example.com", source="pwa",
                                      language="ru", context_mode="exit_discount")
        self.assertEqual(caught.exception.code, "discount_unavailable")

    async def test_discount_is_pwa_only_and_real_provider_invoice(self):
        await self.action("view")
        await self.action("claim")
        with self.assertRaises(LavaCheckoutError) as caught:
            await self.checkout.start(self.sessions, user_id=1, plan_type="1_month",
                                      email="student@example.com", source="miniapp",
                                      language="ru", context_mode="exit_discount")
        self.assertEqual(caught.exception.code, "invalid_request")
        async with self.sessions() as db:
            user = await db.get(User, 1)
            block = await self.checkout.overview_block(
                db, user, supports_lava=True, context_mode="exit_discount"
            )
        month = next(p for p in block["plans"] if p["plan_type"] == "1_month")
        self.assertEqual((month["base_amount"], month["amount"], month["discount_percent"]),
                         ("10.00", "8.00", 20))
        created = await self.checkout.start(
            self.sessions, user_id=1, plan_type="1_month",
            email="student@example.com", source="pwa",
            language="ru", context_mode="exit_discount",
            analytics_attempt_id="inline-unit-1",
            analytics_source="v3_locked_lesson",
        )
        self.assertEqual(created["amount"], "8.00")
        self.assertEqual(self.fake.last_create_body["promoCode"], "HSKEXIT20")
        async with self.sessions() as db:
            self.assertIsNone((await db.get(PwaExitOffer, 1)).consumed_at)
            invoice = await db.get(LavaInvoice, created["checkout_id"])
            self.assertEqual(invoice.pwa_inline_attempt_id, "inline-unit-1")
            self.assertEqual(invoice.pwa_inline_source, "v3_locked_lesson")
        contract = created["payment_url"].rsplit("/", 1)[1]
        self.fake.complete(contract)
        result = await events.verify_and_apply(self.runtime, contract)
        self.assertEqual(result[0], "applied")
        async with self.sessions() as db:
            self.assertIsNotNone((await db.get(PwaExitOffer, 1)).consumed_at)
            user = await db.get(User, 1)
            self.assertFalse(await PwaExitOfferService(db, self.runtime.settings).active(user))
            paid = (await db.execute(select(ConversionFunnelEvent).where(
                ConversionFunnelEvent.event_name == "pwa_pro_checkout_paid",
            ))).scalars().all()
            self.assertEqual(len(paid), 1)
            self.assertEqual(paid[0].source, "v3_locked_lesson")
            self.assertIn('"attempt_id": "inline-unit-1"', paid[0].payload_json)
        # Webhook/provider retry must not add a second conversion.
        await events.verify_and_apply(self.runtime, contract)
        async with self.sessions() as db:
            paid = (await db.execute(select(ConversionFunnelEvent.id).where(
                ConversionFunnelEvent.event_name == "pwa_pro_checkout_paid",
            ))).scalars().all()
            self.assertEqual(len(paid), 1)

    async def test_provider_mode_guard_and_expired_offer_cannot_be_reused(self):
        await self.action("view")
        await self.action("claim")
        async with self.sessions() as db:
            row = await db.get(PwaExitOffer, 1)
            row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await db.commit()
        with self.assertRaises(LavaCheckoutError) as caught:
            await self.checkout.start(self.sessions, user_id=1, plan_type="1_month",
                                      email="student@example.com", source="pwa",
                                      language="ru", context_mode="exit_discount")
        self.assertEqual(caught.exception.code, "discount_unavailable")


if __name__ == "__main__":
    unittest.main()

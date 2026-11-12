"""Native Direct transport: real shared invoice/offer ledger, no PWA credential fallback."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from app.db.models.user import User
from app.db.models.lava import LavaInvoice
from app.db.models.pwa_exit_offer import PwaExitOffer
from app.db.models.subscription_entry_event import SubscriptionEntryEvent
from app.services.desktop_auth_service import DesktopAuthService, DesktopAuthError
from app.services.lava.config import LavaConfigService
from app.services.conversion_funnel_service import ConversionFunnelService
from tests import test_lava_checkout_api as base
from tests.test_pwa_exit_offer import config


class AndroidLavaCheckoutTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await base.LavaCheckoutApiTests.asyncSetUp(self)
        async with self.sessions() as db:
            await LavaConfigService(db).save(config())
            db.add(User(id=2, telegram_id=None, full_name="Native owner", language="tj", status="free"))
            await db.commit()
        self.fake.promo_codes["HSKEXIT20"] = 20
        self.actor = 1
        self.platform = "android"
        async def authenticate(token):
            if token != "verified":
                raise DesktopAuthError("desktop_auth_invalid", status_code=401)
            async with self.sessions() as db:
                user = await db.get(User, self.actor)
                return SimpleNamespace(user=user, device=SimpleNamespace(platform=self.platform))
        self.auth = patch.object(DesktopAuthService, "authenticate", side_effect=authenticate)
        self.auth.start(); self.addCleanup(self.auth.stop)
        self.events = patch.object(ConversionFunnelService, "record", new=AsyncMock(return_value=True))
        self.funnel = self.events.start(); self.addCleanup(self.events.stop)

    async def asyncTearDown(self):
        await base.LavaCheckoutApiTests.asyncTearDown(self)

    async def post(self, action, body=None, **headers):
        return await self.client.post("/api/v3/android/subscription/lava/" + action,
            json=body or {}, headers={"Authorization": "Bearer verified", "X-HSK-Android-Channel": "direct",
                                    "X-HSK-Lava-Capability": "1", **headers})

    async def test_direct_round_trip_reconciles_owner_and_records_android_source(self):
        overview = await self.post("overview", {"origin": "course_limit"})
        self.assertEqual(200, overview.status_code)
        plans = overview.json()["lava"]["plans"]
        self.assertEqual(["1_month", "12_months"], [p["plan_type"] for p in plans])
        self.assertEqual("10.00", plans[0]["amount"])
        async with self.sessions() as db:
            entry = await db.scalar(select(SubscriptionEntryEvent))
            self.assertEqual((1, "android_course_limit", "lava", "android"),
                             (entry.user_id, entry.source, entry.payment_method, entry.client))
        start = await self.post("start", {"plan_type": "1_month", "email": "native@example.com"})
        self.assertEqual(200, start.status_code)
        value = start.json(); checkout = value["checkout_id"]
        self.assertEqual("no-store", start.headers["cache-control"])
        pending = await self.post("status", {"checkout_id": checkout})
        self.assertEqual("pending", pending.json()["status"])
        lost_reply = (await self.post("overview")).json()["lava"]
        self.assertEqual(checkout, lost_reply["pending_checkout_id"])
        self.actor = 2
        self.assertEqual(404, (await self.post("status", {"checkout_id": checkout})).status_code)
        self.assertEqual(404, (await self.post("cancel")).status_code)
        self.actor = 1
        self.fake.complete(value["payment_url"].rsplit("/", 1)[1])
        async with self.sessions() as db:
            (await db.get(LavaInvoice, checkout)).last_checked_at = None
            await db.commit()
        paid = await self.post("status", {"checkout_id": checkout})
        self.assertEqual("paid", paid.json()["status"])
        self.assertTrue(paid.json()["pro_until"])
        self.assertTrue((await self.post("cancel")).json()["ok"])
        async with self.sessions() as db:
            row = await db.get(LavaInvoice, checkout)
            self.assertEqual("android", row.source)
            self.assertIsNotNone(row.payment_id)
            self.assertEqual("cancelled", row.subscription_status)
        self.assertEqual("android", self.funnel.call_args.kwargs["payload"]["transport"])
        self.assertEqual("checkout_opened", self.funnel.call_args.kwargs["event_name"])

    async def test_real_android_funnel_storage_and_financial_owner_reach_existing_admin_source_group(self):
        from app.db.models.conversion_funnel_event import ConversionFunnelEvent
        from app.db.models.payment import Payment
        from app.admin_api.pwa_analytics_finance import source_group
        self.events.stop()
        await self.post("overview", {"origin":"course_limit"})
        with patch("app.services.conversion_funnel_service.async_session_maker", self.sessions):
            started = await self.post("start", {"plan_type":"1_month", "email":"a@b.co"})
        self.assertEqual(200, started.status_code, started.text)
        value = started.json()
        self.fake.complete(value["payment_url"].rsplit("/",1)[1])
        self.assertEqual("paid", (await self.post("status", {"checkout_id":value["checkout_id"]})).json()["status"])
        async with self.sessions() as db:
            event = await db.scalar(select(ConversionFunnelEvent).where(ConversionFunnelEvent.event_name == "checkout_opened"))
            self.assertEqual((1,"android_subscription"), (event.user_id,event.source))
            self.assertEqual("android", __import__("json").loads(event.payload_json)["transport"])
            self.assertEqual("android_subscription", await db.scalar(select(source_group(SubscriptionEntryEvent.source))))
            invoice = await db.get(LavaInvoice, value["checkout_id"])
            payment = await db.get(Payment, invoice.payment_id)
            self.assertEqual((1,"lava","approved"), (payment.user_id,payment.payment_method,payment.payment_status))

    async def test_rejects_play_wrong_platform_mixed_identity_and_client_owner(self):
        for headers in ({"X-HSK-Android-Channel": "play"}, {"X-HSK-Android-Channel": ""},
                        {"X-HSK-Lava-Capability": ""}, {"Cookie": "forged=pwa"},
                        {"X-Telegram-Init-Data": "signed"}, {"Authorization": "Bearer bad"}):
            with self.subTest(headers=headers):
                self.assertIn((await self.post("overview", **headers)).status_code, (401, 422))
        self.platform = "macos"
        self.assertEqual(403, (await self.post("overview")).status_code)
        self.platform = "android"
        self.assertEqual(422, (await self.post("start", {"plan_type":"1_month", "email":"a@b.co", "user_id":2})).status_code)
        self.assertEqual(422, (await self.post("overview", {"origin":"hsk30_onboarding"})).status_code)
        self.assertEqual(400, (await self.post("start", {"plan_type":"hsk30_unlock", "email":"a@b.co"})).status_code)

    async def test_native_only_owner_exit_offer_is_shared_and_consumed_after_verified_payment(self):
        self.actor = 2
        refused = await self.post("start", {"plan_type":"1_month", "email":"a@b.co", "mode":"exit_discount"})
        self.assertEqual(409, refused.status_code)
        view = (await self.post("exit-offer", {"action":"view"})).json()
        claim = (await self.post("exit-offer", {"action":"claim"})).json()
        self.assertEqual(view["expires_at"], claim["expires_at"])
        self.assertTrue(claim["accepted"])
        from app.services.pwa_exit_offer_service import PwaExitOfferService
        async with self.sessions() as db:
            owner = await db.get(User, 2)
            self.assertTrue(await PwaExitOfferService(db, self.runtime.settings).active(owner))
        offer = (await self.post("overview", {"mode":"exit_discount"})).json()["lava"]["plans"][0]
        self.assertEqual(("8.00",20), (offer["amount"], offer["discount_percent"]))
        started = (await self.post("start", {"plan_type":"1_month", "email":"a@b.co", "mode":"exit_discount"})).json()
        self.fake.complete(started["payment_url"].rsplit("/",1)[1])
        self.assertEqual("paid", (await self.post("status", {"checkout_id":started["checkout_id"]})).json()["status"])
        async with self.sessions() as db:
            self.assertIsNotNone((await db.get(PwaExitOffer, 2)).consumed_at)
        self.assertFalse((await self.post("exit-offer", {"action":"view"})).json()["available"])

    async def test_sales_disabled_does_not_hide_or_stop_existing_invoice_reconciliation(self):
        start = (await self.post("start", {"plan_type":"1_month", "email":"a@b.co"})).json()
        self.runtime.settings.LAVA_ENABLED = False
        restored = (await self.post("overview")).json()["lava"]
        self.assertEqual(start["checkout_id"], restored["pending_checkout_id"])
        self.assertEqual(("manual_only", []), (restored["mode"], restored["plans"]))
        self.assertEqual(409, (await self.post("start", {"plan_type":"1_month", "email":"a@b.co"})).status_code)
        self.fake.complete(start["payment_url"].rsplit("/",1)[1])
        self.assertEqual("paid", (await self.post("status", {"checkout_id":start["checkout_id"]})).json()["status"])

    async def test_flags_and_uncertain_provider_attempt_cannot_create_a_second_invoice(self):
        self.runtime.settings.LAVA_ENABLED = False
        self.assertIsNone((await self.post("overview")).json()["lava"])
        self.assertEqual(409, (await self.post("start", {"plan_type":"1_month", "email":"a@b.co"})).status_code)
        self.assertFalse((await self.post("exit-offer", {"action":"view"})).json()["available"])
        self.runtime.settings.LAVA_ENABLED = True
        started = (await self.post("start", {"plan_type":"1_month", "email":"a@b.co"})).json()
        async with self.sessions() as db:
            row = await db.get(LavaInvoice, started["checkout_id"])
            row.status = "failed"; row.review_reason = "create_uncertain"
            await db.commit()
        self.assertEqual("checkout_needs_review", (await self.post("overview")).json()["lava"]["blocked_reason"])
        self.assertEqual(409, (await self.post("start", {"plan_type":"1_month", "email":"a@b.co"})).status_code)
        self.assertEqual(1, len(self.fake.invoices))

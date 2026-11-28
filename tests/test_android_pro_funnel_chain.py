"""Real Android bearer → UI event → invoice → verified ledger → Admin, on PG.

Uses the existing isolated PWA/Lava fixture, with a native Google session on
the canonical account without Telegram. Only provider verification is doubled;
intake authentication, persistence, payment application and Admin reads are real.
"""
import asyncio
import json
import unittest
from unittest.mock import patch
from uuid import uuid4
from types import SimpleNamespace
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from app.admin_api.pwa_analytics_transport import create_admin_pwa_analytics_router
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME

from sqlalchemy import func, select

from app.db.models.conversion_funnel_event import ConversionFunnelEvent as Funnel
from app.db.models.lava import LavaInvoice
from app.db.models.user import User
from app.services.desktop_auth_service import DesktopAuthService
from tests import test_pwa_browser_auth as pwa
from tests.test_pwa_pro_funnel_chain import PwaProFunnelChainTests as Fixture, URL, ADMIN_ORIGIN, ADMIN_COOKIE, ADMIN_TELEGRAM_ID
from tests.lava_fakes import WEBHOOK_SECRET, payment_webhook, refund_webhook


@unittest.skipUnless(URL.startswith("postgresql+asyncpg://"), "set ANALYTICS_TEST_DATABASE_URL")
class AndroidProFunnelChainTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = Fixture.asyncSetUp
    asyncTearDown = Fixture.asyncTearDown
    webhook = Fixture.webhook

    async def admin_read(self, platform):
        admin_settings = SimpleNamespace(ADMIN_PWA_ENABLED=True, ADMIN_PWA_PUBLIC_ORIGIN=ADMIN_ORIGIN,
                                         admin_id_list=[ADMIN_TELEGRAM_ID])
        app = FastAPI()
        app.include_router(create_admin_pwa_analytics_router(settings_obj=admin_settings,
                                                             session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app), base_url=ADMIN_ORIGIN) as admin:
            response = await admin.post("/api/admin/v1/analytics",
                                        json={"section": "funnel", "platform": platform, "period": "weekly"},
                                        headers={"Origin": ADMIN_ORIGIN,
                                                 "Cookie": ADMIN_PWA_COOKIE_NAME + "=" + ADMIN_COOKIE})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def native_headers(self):
        started = await self.client.post("/api/v3/native-auth/oauth/start", json={
            "provider": "google", "platform": "android", "app_version": "1.8.0",
            "installation_key": uuid4().hex * 2, "language": "uz", "mode": "browser_redirect"})
        self.assertEqual(started.status_code, 200, started.text)
        result = started.json()
        state = result["authorize_url"].split("state=", 1)[1].split("&", 1)[0]
        with patch("app.services.google_auth.exchange_code", return_value="verified-provider-fixture"), \
                patch("app.services.google_auth.verify_desktop_id_token", return_value=pwa.identity()):
            callback = await self.client.get("/api/v3/native-auth/oauth/callback/google",
                                              params={"state": state, "code": "fixture"})
        self.assertEqual(callback.status_code, 200, callback.text)
        async with self.sessions() as db:
            linked = await DesktopAuthService(db, self.settings).poll_link(
                link_request_id=result["link_request_id"], polling_secret=result["polling_secret"])
        return {"Authorization": "Bearer " + linked["access_token"],
                "X-HSK-Android-Channel": "direct", "X-HSK-Lava-Capability": "1"}

    async def ui(self, headers, event="android_pro_opened", attempt="native-buy", number=1, **extra):
        return await self.client.post("/api/v3/android/subscription/inline-event", headers=headers, json={
            "event": event, "source": "course_limit", "attempt_id": attempt,
            "event_id": f"{attempt}:{number}", "plan_type": "1_month", "method": "lava", **extra})

    async def test_native_routes_reach_android_and_overall_only(self):
        headers = await self.native_headers()
        overview = await self.client.post("/api/v3/android/subscription/lava/overview", headers=headers, json={"origin": "course_limit"})
        self.assertEqual(overview.json()["pro_analytics_version"], 1)
        self.assertEqual((await self.ui(headers, attempt="native-browse")).status_code, 200)
        # Concurrent replay is one stored UI event under the canonical user lock.
        replies = await asyncio.gather(*(self.ui(headers) for _ in range(4)))
        self.assertEqual(sum(r.json()["recorded"] for r in replies), 1)
        self.assertEqual((await self.ui(headers, event="android_pro_plan_selected", number=2)).status_code, 200)
        for event in ("android_pro_checkout_started", "android_pro_checkout_paid", "pwa_pro_opened"):
            self.assertEqual((await self.ui(headers, event=event)).status_code, 422)
        started = await self.client.post("/api/v3/android/subscription/lava/start", headers=headers, json={
            "plan_type": "1_month", "email": "native@example.com", "attempt_id": "native-buy",
            "ui_source": "course_limit"})
        self.assertEqual(started.status_code, 200, started.text)
        before = (await self.admin_read("android"))["metrics"]["android_pro_attempt_funnel"]
        self.assertEqual([r["attempts"] for r in before["steps"]], [2, 1, 1, 0])
        # Reading/reopening a pending invoice is not a verified paid conversion.
        for _ in range(2):
            status = await self.client.post("/api/v3/android/subscription/lava/status", headers=headers,
                                              json={"checkout_id": started.json()["checkout_id"]})
            self.assertEqual(status.json()["status"], "pending")
        contract = started.json()["payment_url"].rsplit("/", 1)[1]
        self.fake.complete(contract)
        raw = payment_webhook("payment.success", contract, email="native@example.com")
        await self.webhook(raw)
        # Duplicate callback does not create another grant or paid event.
        duplicate = await self.client.post("/api/payments/lava/webhook", content=raw,
                               headers={"X-Api-Key": WEBHOOK_SECRET, "Content-Type": "application/json"})
        self.assertEqual(duplicate.status_code, 200)
        async with self.sessions() as db:
            rows = (await db.scalars(select(Funnel).where(Funnel.event_name.like("android_pro_%")))).all()
            self.assertEqual({r.user_id for r in rows}, {2})
            self.assertEqual(sum(r.event_name == "android_pro_checkout_paid" for r in rows), 1)
            invoice = await db.get(LavaInvoice, started.json()["checkout_id"])
            self.assertEqual((invoice.android_inline_attempt_id, invoice.android_inline_source),
                             ("native-buy", "course_limit"))
            self.assertIsNone((await db.get(User, 2)).telegram_id)
        for platform in ("overall", "android"):
            view = await self.admin_read(platform)
            metric = view["metrics"]["android_pro_attempt_funnel"]
            self.assertEqual([r["attempts"] for r in metric["steps"]], [2, 1, 1, 1])
            self.assertEqual(view["metric_states"]["android_pro_attempt_funnel"]["state"], "available")
            for private in ("native-buy", "native@example.com", contract):
                self.assertNotIn(private, json.dumps(view))
        for platform in ("iphone_pwa", "telegram"):
            view = await self.admin_read(platform)
            self.assertNotIn("android_pro_attempt_funnel", view["metrics"])
            self.assertEqual(view["metric_states"]["android_pro_attempt_funnel"]["state"], "not_applicable")
        self.assertEqual((await self.admin_read("iphone_pwa"))["metrics"]["pwa_pro_attempt_funnel"]["attempts"], 0)
        await self.webhook(refund_webhook(email="native@example.com"))
        reversed_metric = (await self.admin_read("android"))["metrics"]["android_pro_attempt_funnel"]
        self.assertEqual((reversed_metric["steps"][3]["attempts"], reversed_metric["reversed"]), (1, 1))

    async def test_native_intake_rejects_unsafe_inputs_and_isolates_accounts(self):
        headers = await self.native_headers()
        for override, expected in (({"X-HSK-Android-Channel": "play"}, 422),
                                   ({"Authorization": "Bearer invalid"}, 401),
                                   ({"Cookie": "hskai-pwa=anything"}, 422),
                                   ({"X-Telegram-Init-Data": "anything"}, 422)):
            response = await self.ui({**headers, **override})
            self.assertEqual(response.status_code, expected, response.text)
        for values in ({"source": "profile_subscription"}, {"source": "hsk30_settings"},
                       {"user_id": 1}, {"email": "private@example.com"},
                       {"event_id": "different-attempt:1"}, {"method": "invented"},
                       {"plan_type": "invented"}, {"attempt_id": "x" * 61},
                       {"source": "x" * 1100}):
            self.assertIn((await self.ui(headers, **values)).status_code, (413, 422))
        self.assertEqual((await self.ui(headers)).status_code, 200)
        async with self.sessions() as db:
            auth = DesktopAuthService(db, self.settings)
            link = await auth.start_link(platform="android", app_version="1.8.0", installation_key=uuid4().hex * 2)
            await auth.approve_link(display_code=link["display_code"], telegram_id=1001)
            other = await auth.poll_link(link_request_id=link["link_request_id"], polling_secret=link["polling_secret"])
        response = await self.ui({**headers, "Authorization": "Bearer " + other["access_token"]})
        self.assertTrue(response.json()["recorded"])
        async with self.sessions() as db:
            count = await db.scalar(select(func.count()).select_from(Funnel).where(Funnel.event_name == "android_pro_opened"))
            self.assertEqual(count, 2)  # same event ID on different canonical accounts

    async def test_optional_started_observer_timeout_keeps_real_invoice_and_ledger_truth(self):
        headers = await self.native_headers()
        async def slow_observer(*args, **kwargs):
            await asyncio.sleep(10)
        with patch("app.services.android_pro_analytics.record_started", side_effect=slow_observer), \
                patch("app.api.lava_checkout._ANDROID_EVENT_WRITE_TIMEOUT", .01):
            response = await self.client.post("/api/v3/android/subscription/lava/start", headers=headers, json={
                "plan_type": "1_month", "email": "native@example.com", "attempt_id": "native-lost-ui",
                "ui_source": "course_limit"})
        self.assertEqual(response.status_code, 200, response.text)
        contract = response.json()["payment_url"].rsplit("/", 1)[1]
        self.fake.complete(contract)
        await self.webhook(payment_webhook("payment.success", contract, email="native@example.com"))
        metric = (await self.admin_read("android"))["metrics"]["android_pro_attempt_funnel"]
        # PWA max-stage semantics: a later trusted stage implies earlier ones,
        # even if optional observations were lost. No second invoice or grant.
        self.assertEqual([step["attempts"] for step in metric["steps"]], [1, 1, 1, 1])
        self.assertEqual(metric["unlinked"], 0)

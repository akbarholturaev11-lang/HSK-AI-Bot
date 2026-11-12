"""Chain test (task 4.2): the iPhone PWA Pro inline funnel from real routes to Admin.

The PWA learner's UI stages go through the cookie + CSRF inline-event route,
the checkout through the PWA Lava start route, and payment and refund through
the provider webhook route. A Telegram Mini App Lava payment in the same window
must not reach the PWA funnel. Admin reads go through the cookie-authenticated
analytics API under every filter.
Run with ANALYTICS_TEST_DATABASE_URL pointing at a disposable PostgreSQL DB.
"""
import hashlib
import hmac
import json
import os
import time
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import urlencode
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import tests.test_pwa_browser_auth as pwa
from app.admin_api.pwa_analytics_transport import create_admin_pwa_analytics_router
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.api.lava_checkout import create_lava_router
from app.api.native_oauth import create_native_oauth_router
from app.api.pwa_auth import create_pwa_auth_router
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.conversion_funnel_event import ConversionFunnelEvent as Funnel
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.identity_link_service import IdentityLinkService
from app.services.lava.config import LavaConfigService, config_from_dict
from tests.lava_fakes import OFFER_ID, WEBHOOK_SECRET, FakeLava, make_runtime, payment_webhook, refund_webhook

URL = os.environ.get("ANALYTICS_TEST_DATABASE_URL", "")
ADMIN_ORIGIN = "https://hskai.app"
ADMIN_COOKIE = "C" * 64
TELEGRAM_ID, ADMIN_TELEGRAM_ID = 1001, 9001
PWA_EMAIL, MINIAPP_EMAIL = "buyer@example.com", "mini@example.com"
FILTERS = ("overall", "android", "telegram", "iphone_pwa")


@unittest.skipUnless(URL.startswith("postgresql+asyncpg://"), "set ANALYTICS_TEST_DATABASE_URL for the chain tests")
class PwaProFunnelChainTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.schema = "pwa_pro_chain_" + uuid4().hex
        self.engine = create_async_engine(URL, connect_args={"server_settings": {"search_path": self.schema}})
        async with self.engine.begin() as connection:
            await connection.execute(text("CREATE SCHEMA " + self.schema))
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.settings = pwa.settings()
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            db.add_all([pwa.user(1, TELEGRAM_ID), pwa.user(2, None), pwa.user(101, ADMIN_TELEGRAM_ID)])
            await db.flush()
            db.add(AdminPwaSession(id=str(uuid4()), user_id=101, auth_method="webauthn",
                                   token_hash=hashlib.sha256(ADMIN_COOKIE.encode()).hexdigest(),
                                   created_at=now, expires_at=now + timedelta(hours=1)))
            await LavaConfigService(db).save(config_from_dict({
                "checkout_mode": "both", "currency": "USD",
                "plans": {"1_month": {"enabled": True, "offer_id": OFFER_ID}}}))
            await db.commit()
            # The PWA learner signs in with Google; that identity owns account 2.
            await IdentityLinkService(db, self.settings).link_to_user(pwa.identity(), user_id=2)
            await db.commit()

        self.fake = FakeLava()
        self.runtime = make_runtime(self.sessions, self.fake)
        self.stack = ExitStack()
        self.stack.enter_context(patch.object(AIUsageBudgetService, "_live_or_manual_usd_rates",
                                              new=AsyncMock(return_value={"tjs": 10, "cny": 7})))
        for target in ("app.services.conversion_funnel_service.async_session_maker",
                       "app.services.entitlements.shadow.async_session_maker"):
            self.stack.enter_context(patch(target, self.sessions))

        learner = FastAPI()
        learner.include_router(create_native_oauth_router(session_factory=self.sessions, settings_obj=self.settings))
        learner.include_router(create_pwa_auth_router(session_factory=self.sessions, settings_obj=self.settings,
                                                      bot=SimpleNamespace()))
        learner.include_router(create_lava_router(runtime_getter=lambda: self.runtime,
                                                  session_factory=self.sessions, settings_obj=self.settings))
        self.client = AsyncClient(transport=ASGITransport(app=learner), base_url=pwa.ORIGIN)

    async def asyncTearDown(self):
        await self.client.aclose()
        self.stack.close()
        async with self.engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA IF EXISTS " + self.schema + " CASCADE"))
        await self.engine.dispose()

    async def pwa_headers(self):
        started = await self.client.post("/api/v3/pwa-auth/start", headers={"Origin": pwa.ORIGIN},
                                          json={"provider": "google", "language": "uz"})
        self.assertEqual(started.status_code, 200, started.text)
        state = started.json()["authorize_url"].split("state=", 1)[1].split("&", 1)[0]
        from app.services import google_auth
        with patch.object(google_auth, "exchange_code", return_value="google-id-token"), \
                patch.object(google_auth, "verify_desktop_id_token", return_value=pwa.identity()):
            await self.client.get("/api/v3/native-auth/oauth/callback/google",
                                  params={"state": state, "code": "auth-code"})
        session = await self.client.get("/api/v3/pwa-auth/session")
        self.assertEqual(session.status_code, 200, session.text)
        return {"Origin": pwa.ORIGIN, "X-HSK-PWA-CSRF": session.json()["csrf"]}

    def telegram_headers(self):
        values = {"auth_date": str(int(time.time())), "user": json.dumps({"id": TELEGRAM_ID})}
        secret = hmac.new(b"WebAppData", self.settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
        check = "\n".join(f"{k}={v}" for k, v in sorted(values.items()))
        values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        return {"X-Telegram-Init-Data": urlencode(values)}

    async def ui(self, headers, event, attempt, number, expected=200):
        response = await self.client.post("/api/v3/pwa/subscription/inline-event", headers=headers, json={
            "event": event, "source": "v3_locked_lesson", "attempt_id": attempt,
            "event_id": f"{attempt}:{number}", "plan_type": "1_month", "method": "lava"})
        self.assertEqual(response.status_code, expected, response.text)

    async def pay(self, start_path, headers, body, email):
        started = await self.client.post(start_path, headers=headers, json={
            "plan_type": "1_month", "email": email, "language": "uz", **body})
        self.assertEqual(started.status_code, 200, started.text)
        contract = started.json()["payment_url"].rsplit("/", 1)[1]
        self.fake.complete(contract)
        await self.webhook(payment_webhook("payment.success", contract, email=email))

    async def webhook(self, raw):
        hook = await self.client.post("/api/payments/lava/webhook", content=raw,
                                      headers={"X-Api-Key": WEBHOOK_SECRET, "Content-Type": "application/json"})
        self.assertEqual((hook.status_code, hook.json()["result"]), (200, "applied"), hook.text)

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

    async def pwa_funnel(self, platform="iphone_pwa"):
        return (await self.admin_read(platform))["metrics"]["pwa_pro_attempt_funnel"]

    async def test_pwa_routes_reach_the_pwa_pro_funnel_under_overall_and_pwa_only(self):
        headers = await self.pwa_headers()
        # A learner who only looked, then one attempt that reaches checkout.
        await self.ui(headers, "pwa_pro_opened", "att-browse-1", 1)
        await self.ui(headers, "pwa_pro_opened", "att-buy-1", 1)
        await self.ui(headers, "pwa_pro_plan_selected", "att-buy-1", 2)
        # The browser can never claim a payment.
        await self.ui(headers, "pwa_pro_checkout_paid", "att-buy-1", 3, expected=422)
        started = await self.client.post("/api/v3/pwa/subscription/lava/start", headers=headers, json={
            "plan_type": "1_month", "email": PWA_EMAIL, "language": "uz",
            "attempt_id": "att-buy-1", "ui_source": "v3_locked_lesson"})
        self.assertEqual(started.status_code, 200, started.text)
        # Until the provider confirms, the checkout is not paid.
        self.assertEqual([step["attempts"] for step in (await self.pwa_funnel())["steps"]], [2, 1, 1, 0])

        contract = started.json()["payment_url"].rsplit("/", 1)[1]
        self.fake.complete(contract)
        await self.webhook(payment_webhook("payment.success", contract, email=PWA_EMAIL))
        # A Telegram Mini App Lava payment in the same window is not a PWA attempt.
        await self.pay("/api/subscription-miniapp/lava/start", self.telegram_headers(), {}, MINIAPP_EMAIL)

        async with self.sessions() as db:
            names = (await db.execute(select(Funnel.event_name, Funnel.user_id).where(
                Funnel.event_name.like("pwa_pro_%")).order_by(Funnel.id))).all()
        # The routes and the ledger wrote every stage on the PWA account.
        self.assertEqual([name for name, _ in names], ["pwa_pro_opened", "pwa_pro_opened", "pwa_pro_plan_selected",
                                                      "pwa_pro_checkout_started", "pwa_pro_checkout_paid"])
        self.assertEqual({uid for _, uid in names}, {2})

        views = {platform: await self.admin_read(platform) for platform in FILTERS}
        expected = {"attempts": 2, "steps": [{"key": "opened", "attempts": 2}, {"key": "plan_selected", "attempts": 1},
                                             {"key": "checkout_started", "attempts": 1}, {"key": "paid", "attempts": 1}],
                    "reversed": 0, "unlinked": 0}
        for platform in ("overall", "iphone_pwa"):
            self.assertEqual(views[platform]["metrics"]["pwa_pro_attempt_funnel"], expected, platform)
            self.assertEqual(views[platform]["metric_states"]["pwa_pro_attempt_funnel"],
                             {"state": "available", "reason": None}, platform)
            encoded = json.dumps(views[platform])
            for secret in ("att-browse-1", "att-buy-1", contract, PWA_EMAIL):
                self.assertNotIn(secret, encoded)
        for platform in ("android", "telegram"):
            self.assertNotIn("pwa_pro_attempt_funnel", views[platform]["metrics"])
            self.assertEqual(views[platform]["metric_states"]["pwa_pro_attempt_funnel"],
                             {"state": "not_applicable", "reason": "not_applicable"}, platform)

        # A full provider refund keeps the paid stage and counts the reversal.
        await self.webhook(refund_webhook(email=PWA_EMAIL))
        refunded = await self.pwa_funnel()
        self.assertEqual((refunded["steps"][3]["attempts"], refunded["reversed"]), (1, 1))


if __name__ == "__main__":
    unittest.main()

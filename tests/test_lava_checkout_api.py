"""HTTP contract of the lava.top checkout adapters and overview block."""
import json
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api import lava_checkout
from app.api.lava_checkout import attach_lava_block, create_lava_router
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.user import User
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.lava.config import LavaConfigService, config_from_dict
from tests.lava_fakes import OFFER_ID, WEBHOOK_SECRET, FakeLava, make_runtime, payment_webhook


class LavaCheckoutApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(User(id=1, telegram_id=1001, full_name="Learner", language="ru", status="free"))
            await LavaConfigService(session).save(config_from_dict({
                "checkout_mode": "both", "currency": "USD",
                "plans": {"1_month": {"enabled": True, "offer_id": OFFER_ID}},
            }))
            await session.commit()
        self.fake = FakeLava()
        self.runtime = make_runtime(self.sessions, self.fake)
        self.runtime.settings.BOT_TOKEN = "token"
        app = FastAPI()
        app.include_router(create_lava_router(runtime_getter=lambda: self.runtime,
                                              session_factory=self.sessions, settings_obj=self.runtime.settings))
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="https://hsk.example")
        patchers = [
            patch.object(lava_checkout, "extract_verified_webapp_user_id",
                         side_effect=lambda init, token: 1001 if init == "signed" else None),
            patch.object(AIUsageBudgetService, "_live_or_manual_usd_rates",
                         new=AsyncMock(return_value={"tjs": 10, "cny": 7})),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _post(self, path, body, *, init="signed"):
        return await self.client.post(path, content=json.dumps(body),
                                      headers={"Content-Type": "application/json", "X-Telegram-Init-Data": init})

    async def test_miniapp_start_status_and_webhook_round_trip(self):
        response = await self._post("/api/subscription-miniapp/lava/start",
                                    {"plan_type": "1_month", "email": "a@b.co"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["payment_url"].startswith("https://pay.lava.top/"))
        self.assertEqual(response.headers["cache-control"], "no-store")
        contract = data["payment_url"].rsplit("/", 1)[1]
        self.fake.complete(contract)
        hook = await self.client.post("/api/payments/lava/webhook", content=payment_webhook("payment.success", contract),
                                      headers={"X-Api-Key": WEBHOOK_SECRET, "Content-Type": "application/json"})
        self.assertEqual((hook.status_code, hook.json()["result"]), (200, "applied"))
        status = await self._post("/api/subscription-miniapp/lava/status", {"checkout_id": data["checkout_id"]})
        self.assertEqual(status.json()["status"], "paid")

    async def test_unauthenticated_or_malformed_requests_are_refused(self):
        self.assertEqual((await self._post("/api/subscription-miniapp/lava/start",
                                           {"plan_type": "1_month", "email": "a@b.co"}, init="bad")).status_code, 401)
        self.assertEqual((await self._post("/api/subscription-miniapp/lava/start",
                                           {"plan_type": "1_month", "email": "a@b.co", "x": 1})).status_code, 422)
        self.assertEqual((await self._post("/api/subscription-miniapp/lava/start",
                                           {"plan_type": "10_days", "email": "a@b.co"})).status_code, 400)
        other = await self._post("/api/subscription-miniapp/lava/status", {"checkout_id": 999})
        self.assertEqual(other.status_code, 404)
        hook = await self.client.post("/api/payments/lava/webhook", content=b"{}",
                                      headers={"X-Api-Key": "nope"})
        self.assertEqual(hook.status_code, 401)
        oversized = await self.client.post("/api/payments/lava/webhook", content=b"x" * (70 * 1024),
                                           headers={"X-Api-Key": WEBHOOK_SECRET})
        self.assertEqual(oversized.status_code, 413)

    async def test_webhook_disabled_without_secret(self):
        self.runtime.settings.LAVA_WEBHOOK_SECRET = ""
        hook = await self.client.post("/api/payments/lava/webhook", content=b"{}", headers={"X-Api-Key": ""})
        self.assertEqual(hook.status_code, 404)

    async def test_return_page_is_neutral_and_localized(self):
        page = await self.client.get("/pay/lava/return?lang=uz&status=success&invoiceId=x")
        self.assertEqual(page.status_code, 200)
        self.assertIn("To'lov tekshirilmoqda", page.text.replace("&#x27;", "'"))
        self.assertNotIn("invoiceId", page.text)
        self.assertEqual(page.headers["x-frame-options"], "DENY")

    async def test_overview_block_only_for_plain_subscription_and_supporting_clients(self):
        async with self.sessions() as session:
            user = await session.get(User, 1)
            base = {"ok": True, "prices": {"visa": {}}}
            self.assertNotIn("lava", await attach_lava_block(session, self.runtime, user, dict(base),
                                                             mode="subscription", supports_lava=False))
            self.assertNotIn("lava", await attach_lava_block(session, self.runtime, user, dict(base),
                                                             mode="referral_discount", supports_lava=True))
            self.assertNotIn("lava", await attach_lava_block(session, self.runtime, user, dict(base),
                                                             mode="hsk30_unlock", supports_lava=True))
            result = await attach_lava_block(session, self.runtime, user, dict(base), mode="", supports_lava=True)
        self.assertEqual(result["lava"]["mode"], "both")
        self.assertEqual([plan["plan_type"] for plan in result["lava"]["plans"]], ["1_month"])
        self.assertEqual(result["prices"], {"visa": {}})


if __name__ == "__main__":
    unittest.main()

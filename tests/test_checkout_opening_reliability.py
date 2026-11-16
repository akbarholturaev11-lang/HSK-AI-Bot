"""A checkout opening is the anchor of one payment attempt.

Every later stage (instructions, receipt, screenshot, approval) joins the base
`checkout_opened` row by owner + attempt_id: the stage routes answer 409
without it, and the Admin attempt funnel drops the whole attempt. These tests
pin that one failed opening write neither loses the attempt nor blocks the
payment overview, and that the recovery never writes the opening twice.
PWA and Android routes are covered beside their own route tests.
"""
import hashlib
import hmac
import json
import time
import unittest
from unittest.mock import AsyncMock, patch
from urllib.parse import urlencode

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from app.db.models.user import User
from app.services.conversion_funnel_service import ConversionFunnelService
from tests.checkout_funnel_faults import FlakyFunnelSessions
from tests.test_pwa_browser_auth import user

FUNNEL_SESSIONS = "app.services.conversion_funnel_service.async_session_maker"
FUNNEL_LOGGER = "app.services.conversion_funnel_service"
BOT_TOKEN = "9123456:synthetic-test-only-unusable-token"
ATTEMPT = "sub-1794800000000-a1b2c3d4"


async def _openings(sessions, attempt=ATTEMPT):
    async with sessions() as db:
        rows = (await db.execute(
            select(ConversionFunnelEvent.payload_json).where(
                ConversionFunnelEvent.event_name == "checkout_opened",
            ).order_by(ConversionFunnelEvent.id)
        )).scalars().all()
    payloads = [json.loads(row) for row in rows]
    mine = [p for p in payloads if p.get("attempt_id") == attempt]
    return [p for p in mine if "stage" not in p], [p for p in mine if "stage" in p]


class _Db(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as db:
            db.add_all([user(1, 1001), user(2, 1002)])
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()


class CheckoutOpeningRecordTests(_Db):
    async def open(self, flaky, payload=None):
        async with self.sessions() as db:
            learner = await db.get(User, 1)
        with patch(FUNNEL_SESSIONS, flaky):
            return await ConversionFunnelService().record_checkout_opened(
                user=learner, telegram_id=1001, source="v3_paywall",
                payload=payload or {"attempt_id": ATTEMPT, "mode": "subscription",
                                    "transport": "iphone_pwa"},
            )

    async def test_normal_path_is_one_write_and_no_extra_query(self):
        flaky = FlakyFunnelSessions(self.sessions)
        self.assertTrue(await self.open(flaky))
        self.assertEqual(flaky.calls, 1)
        self.assertEqual(len((await _openings(self.sessions))[0]), 1)

    async def test_dropped_write_is_retried_once(self):
        flaky = FlakyFunnelSessions(self.sessions, drop={1})
        with self.assertLogs(FUNNEL_LOGGER, level="WARNING") as logs:
            self.assertTrue(await self.open(flaky))
        self.assertEqual(flaky.calls, 3)  # write, absence check, single retry
        self.assertEqual(len((await _openings(self.sessions))[0]), 1)
        self.assertIn("checkout_opened_recovered", "\n".join(logs.output))

    async def test_applied_commit_with_lost_ack_is_not_written_twice(self):
        flaky = FlakyFunnelSessions(self.sessions, lost_ack={1})
        self.assertTrue(await self.open(flaky))
        self.assertEqual(flaky.calls, 2)  # write, check finds it: no retry
        self.assertEqual(len((await _openings(self.sessions))[0]), 1)

    async def test_persistent_failure_is_reported_and_never_raised(self):
        flaky = FlakyFunnelSessions(self.sessions, drop={1, 3})
        with self.assertLogs(FUNNEL_LOGGER, level="ERROR") as logs:
            self.assertFalse(await self.open(flaky))
        self.assertEqual(flaky.calls, 3)  # exactly one retry, no loop
        self.assertEqual((await _openings(self.sessions))[0], [])
        self.assertIn("checkout_opened_lost", "\n".join(logs.output))

    async def test_unknown_state_never_retries_blind(self):
        # The first commit may have been applied; the absence check itself
        # fails, so a blind retry could double the opening. It must not run.
        flaky = FlakyFunnelSessions(self.sessions, lost_ack={1}, drop={2})
        with self.assertLogs(FUNNEL_LOGGER, level="ERROR"):
            self.assertFalse(await self.open(flaky))
        self.assertEqual(flaky.calls, 2)
        self.assertEqual(len((await _openings(self.sessions))[0]), 1)

    async def test_opening_without_attempt_is_not_retried(self):
        flaky = FlakyFunnelSessions(self.sessions, drop={1})
        with self.assertLogs(FUNNEL_LOGGER, level="ERROR"):
            self.assertFalse(await self.open(
                flaky, {"attempt_id": None, "mode": "subscription", "transport": "telegram"}))
        self.assertEqual(flaky.calls, 1)

    async def test_other_opening_of_same_attempt_does_not_hide_this_one(self):
        # Only this exact opening counts as already written: an earlier
        # opening of the same attempt in another mode keeps its own row.
        await self.open(FlakyFunnelSessions(self.sessions), {
            "attempt_id": ATTEMPT, "mode": "subscription", "transport": "telegram"})
        flaky = FlakyFunnelSessions(self.sessions, drop={1})
        with self.assertLogs(FUNNEL_LOGGER, level="WARNING"):
            self.assertTrue(await self.open(flaky, {
                "attempt_id": ATTEMPT, "mode": "hsk30_unlock", "transport": "telegram"}))
        modes = [p["mode"] for p in (await _openings(self.sessions))[0]]
        self.assertEqual(modes, ["subscription", "hsk30_unlock"])


class MiniAppCheckoutOpeningTests(_Db):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        from app.config import settings as main_settings
        with patch.object(main_settings, "BOT_TOKEN", BOT_TOKEN):
            import app.main as main
        self.main = main
        app = FastAPI()
        app.add_api_route("/api/subscription-miniapp/overview",
                          main.subscription_miniapp_overview, methods=["POST"])
        app.add_api_route("/api/subscription-miniapp/event",
                          main.subscription_miniapp_event, methods=["POST"])
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="https://miniapp.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await super().asyncTearDown()

    @staticmethod
    def signed(telegram_id):
        values = {"auth_date": str(int(time.time())), "user": json.dumps({"id": telegram_id})}
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        check = "\n".join(f"{k}={v}" for k, v in sorted(values.items()))
        values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        return {"X-Telegram-Init-Data": urlencode(values)}

    async def checkout(self, flaky):
        main = self.main
        stage = {"attempt_id": ATTEMPT, "stage": "payment_instructions_viewed",
                 "plan_type": "1_month", "payment_method": "visa", "mode": "subscription"}
        with patch.object(main.settings, "BOT_TOKEN", BOT_TOKEN), \
                patch.object(main, "async_session_maker", self.sessions), \
                patch(FUNNEL_SESSIONS, flaky), \
                patch.object(main.SubscriptionMiniAppService, "overview", new_callable=AsyncMock,
                             return_value={"ok": True, "mode": "subscription", "pending_payment": None,
                                           "prices": {"visa": {"1_month": {"final_amount": 89}}}}), \
                patch.object(main.SubscriptionChurnService, "mark_subscription_miniapp_opened",
                             new_callable=AsyncMock), \
                patch.object(main, "attach_lava_block", new_callable=AsyncMock,
                             side_effect=lambda _db, _runtime, _user, result, **_kw: result):
            opened = await self.client.post(
                "/api/subscription-miniapp/overview", headers=self.signed(1001),
                json={"source": "v3_paywall", "mode": "subscription", "attempt_id": ATTEMPT})
            event = await self.client.post(
                "/api/subscription-miniapp/event", headers=self.signed(1001), json=stage)
            foreign = await self.client.post(
                "/api/subscription-miniapp/event", headers=self.signed(1002), json=stage)
        return opened, event, foreign

    async def test_one_failed_opening_write_keeps_the_attempt(self):
        opened, event, foreign = await self.checkout(FlakyFunnelSessions(self.sessions, drop={1}))
        # Payment overview is untouched by the analytics failure.
        self.assertEqual(opened.status_code, 200, opened.text)
        self.assertEqual(opened.json()["prices"]["visa"]["1_month"]["final_amount"], 89)
        # Before the fix this stage answered 409 and the attempt was lost.
        self.assertEqual(event.status_code, 200, event.text)
        self.assertTrue(event.json()["ok"])
        self.assertEqual(foreign.status_code, 409)  # another account, same attempt id
        base, stages = await _openings(self.sessions)
        self.assertEqual(len(base), 1)
        self.assertEqual(base[0]["transport"], "telegram")
        self.assertEqual([s["stage"] for s in stages], ["payment_instructions_viewed"])

    async def test_lost_opening_never_blocks_payment_or_fabricates_stages(self):
        flaky = FlakyFunnelSessions(self.sessions, drop={1, 3})
        with self.assertLogs(FUNNEL_LOGGER, level="ERROR"):
            opened, event, _ = await self.checkout(flaky)
        self.assertEqual(opened.status_code, 200, opened.text)
        self.assertTrue(opened.json()["ok"])
        self.assertEqual(event.status_code, 409)
        self.assertEqual(await _openings(self.sessions), ([], []))


class CheckoutRouteSourceTests(unittest.TestCase):
    """Every route that opens a stage-tracked attempt uses the checked writer."""

    def test_opening_routes_use_checked_writer(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        sources = {
            "app/main.py": '@app.post("/api/subscription-miniapp/overview")',
            "app/api/pwa_auth.py": '@router.post("/api/v3/pwa/subscription/overview")',
            "app/services/desktop_subscription_service.py": "async def _record_checkout_opened(",
        }
        for path, anchor in sources.items():
            body = (root / path).read_text(encoding="utf-8").split(anchor, 1)[1]
            ends = [body.find(mark) for mark in ("\n    @router.", "\n@app.", "\n    async def ", "\n    def ")]
            body = body[:min(end for end in ends if end > 0)]
            self.assertIn(".record_checkout_opened(", body, path)
            # No unchecked opening write remains beside it.
            self.assertNotIn(".record(", body, path)


if __name__ == "__main__":
    unittest.main()

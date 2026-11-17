"""lava.top approvals reuse the manual-approval delivery: Telegram, Android
FCM and learner iPhone PWA push; revocation notices are Telegram messages."""
import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.user import User
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.lava import events
from app.services.lava.checkout import LavaCheckoutService
from app.services.lava.config import LavaConfigService, config_from_dict
from app.services.lava.notify import LavaNotifier
from app.services.payment_notify_service import PaymentNotifyService
from tests.lava_fakes import OFFER_ID, WEBHOOK_SECRET, FakeLava, make_runtime, payment_webhook, refund_webhook


class LavaNotificationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
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

    async def _pay(self):
        started = await LavaCheckoutService(self.runtime).start(
            self.sessions, user_id=1, plan_type="1_month", email="b@x.co", source="miniapp", language="uz")
        contract = started["payment_url"].rsplit("/", 1)[1]
        self.fake.complete(contract)
        return await events.ingest(self.runtime, payment_webhook("payment.success", contract, email="b@x.co"),
                                   api_key_header=WEBHOOK_SECRET, client_ip=None)

    async def test_main_wires_lava_approval_to_existing_delivery(self):
        from tests.test_main_imports import MainModuleImportTests
        main = MainModuleImportTests._import_main()
        self.assertIs(main.lava_runtime.on_approved, main._lava_on_approved)
        self.assertIsInstance(main.lava_runtime.notifier, LavaNotifier)
        self.runtime.on_approved = main._lava_on_approved
        with (
            patch.object(main, "async_session_maker", self.sessions),
            patch.object(main.ConversionFunnelService, "record", new=AsyncMock(return_value=True)) as funnel,
            patch.object(main.CourseMiniAppAnalyticsService, "record_server_event",
                         new=AsyncMock(return_value={"recorded": False})),
            patch.object(PaymentNotifyService, "_android_push", new=AsyncMock()) as native_push,
            patch.object(main.bot, "send_message", new=AsyncMock()) as telegram,
        ):
            status, body = await self._pay()
        self.assertEqual((status, body["result"]), (200, "applied"))
        telegram.assert_awaited()
        self.assertEqual(telegram.await_args.kwargs["chat_id"], 1001)
        native_push.assert_awaited()
        payment = native_push.await_args.args[0]
        self.assertEqual((payment.payment_method, payment.payment_status), ("lava", "approved"))
        self.assertEqual(native_push.await_args.args[1], "approved")
        sources = [call.kwargs.get("source") for call in funnel.await_args_list]
        self.assertIn("lava_payment_approve", sources)

    async def test_native_and_pwa_push_fanout_for_lava_payment(self):
        from app.config import settings
        captured = {}

        async def on_approved(session, result):
            captured["payment"] = result.payment
            captured["user"] = result.user

        self.runtime.on_approved = on_approved
        await self._pay()
        android = AsyncMock()
        with (
            patch("app.services.payment_notify_service.AndroidPaymentPushService.notify", new=android),
            patch("app.services.learner_pwa_push.enqueue_event", new=AsyncMock(return_value=1)) as pwa,
            patch.object(settings, "PWA_AUTH_ENABLED", True),
            patch.object(settings, "PWA_PUSH_ENABLED", True),
        ):
            async with self.sessions() as session:
                await PaymentNotifyService(session)._android_push(captured["payment"], "approved",
                                                                  user=captured["user"])
        android.assert_awaited_once()
        self.assertEqual(android.await_args.kwargs["status"], "approved")
        self.assertEqual(android.await_args.kwargs["user_id"], 1)
        pwa.assert_awaited_once()
        self.assertEqual((pwa.await_args.kwargs["source"], pwa.await_args.kwargs["user_id"]), ("payment", 1))

    async def test_refund_notice_is_sent_to_the_owner_in_their_language(self):
        bot = AsyncMock()
        self.runtime.notifier = LavaNotifier(bot=bot, admin_ids=[9001])
        await self._pay()
        status, body = await events.ingest(self.runtime, refund_webhook(email="b@x.co"),
                                           api_key_header=WEBHOOK_SECRET, client_ip=None)
        self.assertEqual(body["result"], "applied")
        chats = [call.kwargs["chat_id"] for call in bot.send_message.await_args_list]
        self.assertIn(1001, chats)  # learner notice
        self.assertIn(9001, chats)  # admin alert
        learner_text = next(call.kwargs["text"] for call in bot.send_message.await_args_list
                            if call.kwargs["chat_id"] == 1001)
        self.assertIn("qaytarildi", learner_text)


if __name__ == "__main__":
    unittest.main()

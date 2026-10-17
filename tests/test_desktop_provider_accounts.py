"""Provider-only sessions retain canonical ownership across native APIs."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.android_features import create_android_features_router
from app.api.desktop_course import create_desktop_course_router
from app.api.desktop_practice import create_desktop_practice_router
from app.api.desktop_rating import create_desktop_rating_router
from app.api.desktop_referral import create_desktop_referral_router
from app.api.desktop_subscription import create_desktop_subscription_router
from app.api.desktop_voice import create_desktop_voice_router
from app.db.base import Base
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_progress import CourseProgress
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.payment import Payment
from app.db.models.ai_usage import AIUsageBudget
from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from app.db.models.subscription_entry_event import SubscriptionEntryEvent
from app.db.models.user import User
from app.services.desktop_auth_service import DesktopAuthService
from app.services.desktop_subscription_service import DesktopSubscriptionError, DesktopSubscriptionService
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.admin_notify_service import AdminNotifyService
from app.services.subscription_miniapp_service import PAYMENT_DETAILS_KEY, SubscriptionMiniAppService


PNG_1X1_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class DesktopProviderAccountTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.settings = SimpleNamespace(
            DESKTOP_AUTH_SIGNING_SECRET="desktop-provider-test-" + "x" * 48,
            BOT_USERNAME="test_bot",
        )
        self.headers = {}
        self.android_headers = {}
        async with self.sessions() as session:
            for uid, platform in ((1, "macos"), (2, "windows")):
                session.add(User(id=uid, telegram_id=None, full_name=f"Provider {uid}",
                                 language="uz", level="hsk1", status="free"))
                await session.flush()
                device = DesktopDevice(id=f"device-{uid}", user_id=uid, telegram_id=None,
                    platform=platform, app_version="1.4.3", installation_key_hash=f"key-{uid}")
                session.add(device)
                await session.flush()
                auth_session = DesktopSession(id=f"session-{uid}", device_id=device.id,
                    refresh_token_hash=f"refresh-{uid}",
                    expires_at=datetime.now(timezone.utc) + timedelta(days=30))
                session.add(auth_session)
                await session.flush()
                token, _ = DesktopAuthService(session, self.settings)._access_token(
                    desktop_session=auth_session, device=device)
                self.headers[uid] = {"Authorization": "Bearer " + token}
                android_device = DesktopDevice(id=f"android-device-{uid}", user_id=uid,
                    telegram_id=None, platform="android", app_version="1.4.3",
                    installation_key_hash=f"android-key-{uid}")
                session.add(android_device)
                await session.flush()
                android_session = DesktopSession(id=f"android-session-{uid}",
                    device_id=android_device.id, refresh_token_hash=f"android-refresh-{uid}",
                    expires_at=datetime.now(timezone.utc) + timedelta(days=30))
                session.add(android_session)
                await session.flush()
                token, _ = DesktopAuthService(session, self.settings)._access_token(
                    desktop_session=android_session, device=android_device)
                self.android_headers[uid] = {"Authorization": "Bearer " + token}
            await BotSettingRepository(session).set(PAYMENT_DETAILS_KEY, "TEST BANK DETAILS")
            await session.commit()
        self.funnel_patch = patch("app.services.conversion_funnel_service.async_session_maker", self.sessions)
        self.funnel_patch.start()
        self.practice = SimpleNamespace(start=AsyncMock(return_value={"ok": True, "questions": []}))
        self.voice = SimpleNamespace(user_status=AsyncMock(return_value={"ok": True}))
        self.bot = SimpleNamespace(get_me=AsyncMock(return_value=SimpleNamespace(username="test_bot")))
        app = FastAPI()
        common = {"session_factory": self.sessions, "settings_obj": self.settings}
        app.include_router(create_desktop_course_router(**common))
        app.include_router(create_desktop_rating_router(**common))
        app.include_router(create_desktop_referral_router(**common))
        app.include_router(create_desktop_subscription_router(**common, bot=self.bot))
        app.include_router(create_android_features_router(**common, bot=self.bot))
        app.include_router(create_desktop_practice_router(**common, service_factory=lambda _: self.practice))
        app.include_router(create_desktop_voice_router(**common, service_factory=lambda _: self.voice))
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="https://desktop.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        self.funnel_patch.stop()
        await self.engine.dispose()

    async def test_course_completion_and_replay_are_isolated_for_two_null_telegram_accounts(self):
        payload = {"lesson_order": 1, "event_id": "provider-desktop-shared-event", "mistakes": []}
        for uid in (1, 2):
            course = await self.client.get("/api/v3/desktop/course/map", headers=self.headers[uid])
            self.assertEqual(course.status_code, 200, course.text)
            self.assertEqual(course.json()["user"]["name"], f"Provider {uid}")
            result = await self.client.post("/api/v3/desktop/course/complete", headers=self.headers[uid], json=payload)
            self.assertEqual(result.status_code, 200, result.text)
            self.assertFalse(result.json().get("duplicate", False))
            replay = await self.client.post("/api/v3/desktop/course/complete", headers=self.headers[uid], json=payload)
            self.assertEqual(replay.status_code, 200, replay.text)
            self.assertTrue(replay.json()["duplicate"])
        async with self.sessions() as session:
            rows = (await session.scalars(select(CourseProgress))).all()
            self.assertEqual({row.user_id for row in rows}, {1, 2})
            self.assertTrue(all(row.completed_lessons_count == 1 for row in rows))
            events = (await session.scalars(select(CourseMiniAppEvent).where(
                CourseMiniAppEvent.event_name == "lesson_completed"))).all()
            self.assertEqual({row.user_id for row in events}, {1, 2})
            self.assertTrue(all(row.telegram_id is None for row in events))

    async def test_practice_voice_rating_receive_the_authenticated_user(self):
        response = await self.client.post("/api/v3/desktop/practice/start", headers=self.headers[1],
            json={"mode": "training", "skill": "pinyin", "level": "hsk1", "language": "uz"})
        self.assertEqual(response.status_code, 200, response.text)
        actor = self.practice.start.await_args.args[0]
        self.assertIsInstance(actor, User)
        self.assertEqual(actor.id, 1)
        self.assertIsNone(actor.telegram_id)
        response = await self.client.get("/api/v3/desktop/voice/status", headers=self.headers[2])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.voice.user_status.await_args.args[0].id, 2)
        response = await self.client.get("/api/v3/desktop/rating/leaderboard", headers=self.headers[1])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["ok"])

    async def test_two_provider_checkouts_keep_payments_preview_and_legacy_telegram_separate(self):
        async with self.sessions() as session:
            session.add(User(id=3, telegram_id=1, full_name="Real Telegram learner", status="free"))
            legacy = Payment(user_id=3, user_telegram_id=1, plan_type="1_month", amount=95,
                             currency="TJS", payment_status="pending")
            session.add(legacy)
            await session.commit()
            legacy_id = legacy.id
            self.assertEqual((await SubscriptionMiniAppService(session).overview(1))["pending_payment"]["id"], legacy_id)
        payment_ids = {}
        with patch.object(AdminNotifyService, "notify_payment_review", new=AsyncMock(return_value="RECEIPT_FILE")) as delivery:
            for uid in (1, 2):
                overview = await self.client.get("/api/v3/desktop/subscription/overview", headers=self.headers[uid])
                self.assertEqual(overview.status_code, 200, overview.text)
                self.assertTrue(overview.json()["checkout_allowed"])
                self.assertIsNone(overview.json()["pending_payment"])
                self.assertFalse(overview.json()["discount"]["referral_20_available"])
                self.assertIn("?ref=", overview.json()["discount"]["referral_link"])
                quote = await self.client.post("/api/v3/desktop/subscription/quote", headers=self.headers[uid],
                    json={"plan_type": "1_month", "payment_method": "visa", "card_country": "tj"})
                self.assertEqual(quote.status_code, 200, quote.text)
                body = {"plan_type": "1_month", "payment_method": "visa", "card_country": "tj",
                        "screenshot_data_url": PNG_1X1_DATA_URL, "attempt_id": overview.json()["attempt_id"]}
                submitted = await self.client.post("/api/v3/desktop/subscription/submit", headers=self.headers[uid], json=body)
                self.assertEqual(submitted.status_code, 200, submitted.text)
                payment_ids[uid] = submitted.json()["payment_id"]
                duplicate = await self.client.post("/api/v3/desktop/subscription/submit", headers=self.headers[uid], json=body)
                self.assertEqual(duplicate.status_code, 200, duplicate.text)
                self.assertTrue(duplicate.json()["already_pending"])
                self.assertEqual(duplicate.json()["payment_id"], payment_ids[uid])
                pending = await self.client.get("/api/v3/desktop/subscription/overview", headers=self.headers[uid])
                self.assertEqual(pending.json()["pending_payment"]["id"], payment_ids[uid])
            self.assertEqual(delivery.await_count, 2)
            self.assertEqual({call.kwargs["user"].id for call in delivery.await_args_list}, {1, 2})
        self.assertEqual(len(set(payment_ids.values()) | {legacy_id}), 3)
        async with self.sessions() as session:
            for uid, payment_id in payment_ids.items():
                payment = await session.get(Payment, payment_id)
                user = await session.get(User, uid)
                budget = await session.scalar(select(AIUsageBudget).where(AIUsageBudget.payment_id == payment_id))
                self.assertEqual(payment.user_id, uid)
                self.assertIsNone(payment.user_telegram_id)
                self.assertEqual(user.payment_preview_payment_id, payment_id)
                self.assertFalse(user.payment_preview_available)
                self.assertEqual((budget.user_id, budget.total_budget_usd), (uid, 0.5))
                self.assertIsNone(budget.user_telegram_id)
            events = (await session.scalars(select(ConversionFunnelEvent).where(
                ConversionFunnelEvent.event_name == "payment_screenshot_submitted"))).all()
            self.assertEqual({event.user_id for event in events}, {1, 2})
            self.assertTrue(all(event.telegram_id is None for event in events))
            self.assertEqual(await session.scalar(select(func.count()).select_from(Payment)), 3)
        response = await self.client.get("/api/v3/desktop/referral/overview", headers=self.headers[1])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["invited"], 0)
        self.assertIn("?ref=", response.json()["link"])

    async def test_android_direct_provider_checkout_and_currency_stay_canonical(self):
        headers = self.android_headers[1]
        changed = await self.client.put("/api/v3/android/subscription/currency-preference",
            headers=headers, json={"currency": "USD"})
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()["display_currency"], "USD")
        selected = changed.json()["prices"]["visa"]["1_month"]
        self.assertEqual(selected["display_currency"], "USD")
        other = await self.client.get("/api/v3/android/subscription/currency-preference",
            headers=self.android_headers[2])
        self.assertEqual(other.status_code, 200, other.text)
        self.assertIsNone(other.json()["currency"])
        overview = await self.client.get("/api/v3/android/subscription/checkout/overview", headers=headers)
        self.assertEqual(overview.status_code, 200, overview.text)
        self.assertTrue(overview.json()["checkout_allowed"])
        self.assertEqual(overview.json()["preferred_currency"], "USD")
        self.assertTrue(overview.json()["attempt_id"].startswith("android-"))
        body = {"plan_type": "1_month", "payment_method": "visa", "card_country": "tj"}
        quote = await self.client.post("/api/v3/android/subscription/checkout/quote", headers=headers, json=body)
        self.assertEqual(quote.status_code, 200, quote.text)
        self.assertEqual(quote.json()["quote"]["final_amount"], selected["final_amount"])
        body.update(screenshot_data_url=PNG_1X1_DATA_URL, attempt_id=overview.json()["attempt_id"])
        with patch.object(AdminNotifyService, "notify_payment_review", new=AsyncMock(return_value="ANDROID_RECEIPT")) as delivery:
            submitted = await self.client.post("/api/v3/android/subscription/checkout/submit", headers=headers, json=body)
            self.assertEqual(submitted.status_code, 200, submitted.text)
            duplicate = await self.client.post("/api/v3/android/subscription/checkout/submit", headers=headers, json=body)
            self.assertEqual(duplicate.status_code, 200, duplicate.text)
            self.assertEqual(submitted.json()["payment_id"], duplicate.json()["payment_id"])
            delivery.assert_awaited_once()
        pending_currency = await self.client.put("/api/v3/android/subscription/currency-preference",
            headers=headers, json={"currency": "RUB"})
        self.assertEqual(pending_currency.status_code, 409, pending_currency.text)
        async with self.sessions() as session:
            user = await session.get(User, 1)
            payment = await session.get(Payment, submitted.json()["payment_id"])
            self.assertEqual(user.subscription_currency, "USD")
            self.assertEqual((payment.user_id, payment.user_telegram_id, payment.source), (1, None, "android"))
            self.assertEqual(payment.amount, quote.json()["quote"]["final_amount"])
            self.assertEqual(payment.currency, selected["currency"])
            self.assertEqual(payment.local_currency, "TJS")
            self.assertEqual(user.payment_preview_payment_id, payment.id)
            events = (await session.scalars(select(ConversionFunnelEvent).where(
                ConversionFunnelEvent.event_name == "payment_screenshot_submitted"))).all()
            self.assertEqual([(event.user_id, event.telegram_id, event.source) for event in events], [(1, None, "android_subscription")])
            entries = (await session.scalars(select(SubscriptionEntryEvent))).all()
            self.assertEqual([(entry.user_id, entry.telegram_id, entry.source) for entry in entries], [(1, None, "android_subscription")])

    async def test_provider_admin_delivery_failure_rolls_back_receipt_and_preview(self):
        with patch.object(AdminNotifyService, "notify_payment_review", new=AsyncMock(side_effect=RuntimeError("test delivery failure"))):
            response = await self.client.post("/api/v3/desktop/subscription/submit", headers=self.headers[1],
                json={"plan_type": "1_month", "payment_method": "visa", "card_country": "tj",
                      "screenshot_data_url": PNG_1X1_DATA_URL})
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json()["error"], "admin_notification_failed")
        async with self.sessions() as session:
            user = await session.get(User, 1)
            self.assertTrue(user.payment_preview_available)
            self.assertIsNone(user.payment_preview_payment_id)
            self.assertEqual(await session.scalar(select(func.count()).select_from(Payment)), 0)
            self.assertEqual(await session.scalar(select(func.count()).select_from(AIUsageBudget)), 0)

    async def test_provider_hsk30_checkout_obeys_the_server_feature_flag(self):
        async with self.sessions() as session:
            service = DesktopSubscriptionService(session, self.settings, bot=self.bot)
            token = self.headers[1]["Authorization"].removeprefix("Bearer ")
            with self.assertRaises(DesktopSubscriptionError) as raised:
                await service.overview(token, entry_source="desktop_hsk30_onboarding")
            self.assertEqual(raised.exception.code, "hsk30_disabled")
            for method, args in ((service.quote, {"plan_type": "hsk30_unlock", "payment_method": "visa", "card_country": "tj"}),
                                 (service.submit, {"plan_type": "hsk30_unlock", "payment_method": "visa", "card_country": "tj", "screenshot_data_url": "unused"})):
                with self.assertRaises(DesktopSubscriptionError) as raised:
                    await method(token, **args)
                self.assertEqual(raised.exception.code, "hsk30_disabled")
            self.assertEqual(await session.scalar(select(func.count()).select_from(Payment)), 0)

    async def test_checkout_refreshes_actor_and_never_treats_internal_id_as_telegram(self):
        async with self.sessions() as session:
            stale = await session.get(User, 1)
        async with self.sessions() as session:
            (await session.get(User, 1)).status = "blocked"
            await session.commit()
        async with self.sessions() as session:
            service = SubscriptionMiniAppService(session)
            for actor, expected in ((stale, "user_blocked"), (1, "access_start_first"), (None, "access_start_first"), (0, "access_start_first")):
                with self.subTest(actor_type=type(actor).__name__):
                    response = await service.submit(telegram_id=actor, plan_type="1_month", payment_method="visa",
                        card_country="tj", screenshot_data_url=PNG_1X1_DATA_URL, bot=self.bot)
                    self.assertEqual(response, {"ok": False, "error": expected})
            self.assertEqual(await session.scalar(select(func.count()).select_from(Payment)), 0)

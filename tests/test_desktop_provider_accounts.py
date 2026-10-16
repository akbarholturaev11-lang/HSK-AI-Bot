"""Provider-only desktop sessions retain canonical ownership across native APIs."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

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
from app.db.models.user import User
from app.services.desktop_auth_service import DesktopAuthService
from app.services.desktop_subscription_service import DesktopSubscriptionError, DesktopSubscriptionService


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
            await session.commit()
        self.practice = SimpleNamespace(start=AsyncMock(return_value={"ok": True, "questions": []}))
        self.voice = SimpleNamespace(user_status=AsyncMock(return_value={"ok": True}))
        self.bot = SimpleNamespace(get_me=AsyncMock(return_value=SimpleNamespace(username="test_bot")))
        app = FastAPI()
        common = {"session_factory": self.sessions, "settings_obj": self.settings}
        app.include_router(create_desktop_course_router(**common))
        app.include_router(create_desktop_rating_router(**common))
        app.include_router(create_desktop_referral_router(**common))
        app.include_router(create_desktop_subscription_router(**common, bot=self.bot))
        app.include_router(create_desktop_practice_router(**common, service_factory=lambda _: self.practice))
        app.include_router(create_desktop_voice_router(**common, service_factory=lambda _: self.voice))
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="https://desktop.test")

    async def asyncTearDown(self):
        await self.client.aclose()
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

    async def test_provider_checkout_never_reads_or_writes_telegram_payment_records(self):
        with patch("app.services.subscription_miniapp_service.SubscriptionMiniAppService.overview", AsyncMock()) as overview:
            response = await self.client.get("/api/v3/desktop/subscription/overview", headers=self.headers[1])
            self.assertEqual(response.status_code, 200, response.text)
            self.assertFalse(response.json()["checkout_allowed"])
            self.assertEqual(response.json()["read_only_reason"], "payment_telegram_required")
            self.assertEqual(response.json()["prices"], {})
            overview.assert_not_awaited()
        async with self.sessions() as session:
            service = DesktopSubscriptionService(session, self.settings, bot=self.bot)
            token = self.headers[1]["Authorization"].removeprefix("Bearer ")
            for method, args in ((service.quote, {"plan_type": "1_month", "payment_method": "visa", "card_country": "tj"}),
                                 (service.submit, {"plan_type": "1_month", "payment_method": "visa", "card_country": "tj", "screenshot_data_url": "unused"})):
                with self.assertRaises(DesktopSubscriptionError) as raised:
                    await method(token, **args)
                self.assertEqual(raised.exception.code, "payment_telegram_required")
            self.assertEqual(await session.scalar(select(func.count()).select_from(Payment)), 0)
        response = await self.client.get("/api/v3/desktop/referral/overview", headers=self.headers[1])
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["error"], "desktop_referral_telegram_required")

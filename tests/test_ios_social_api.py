import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.ios_social import create_ios_social_router


class IOSSocialTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_rating_uses_shared_gamification_service(self):
        user = SimpleNamespace(id=7, telegram_id=123)
        context = SimpleNamespace(user=SimpleNamespace(telegram_id=123))
        service = SimpleNamespace(leaderboard=AsyncMock(return_value={
            "rank": 2, "league": "silver", "league_size": 20,
            "weekly_xp": 340, "daily_xp": 40, "streak": 5,
            "leaderboard": [{
                "telegram_id": 123, "rank": 2, "name": "Akbar",
                "username": "", "xp": 340, "course_level": "hsk3",
                "is_paid": False, "is_current_user": True,
            }],
        }))
        session = MagicMock()
        session.commit = AsyncMock()

        @asynccontextmanager
        async def session_factory():
            yield session

        app = FastAPI()
        app.include_router(create_ios_social_router(
            session_factory=session_factory,
            settings_obj=SimpleNamespace(DESKTOP_AUTH_SIGNING_SECRET="secret"),
            gamification_service_factory=lambda *_: service,
        ))

        with (
            patch("app.api.ios_social.DesktopAuthService.authenticate",
                  new=AsyncMock(return_value=context)),
            patch("app.api.ios_social.UserRepository.get_by_telegram_id",
                  new=AsyncMock(return_value=user)),
        ):
            async with AsyncClient(transport=ASGITransport(app=app),
                                   base_url="https://testserver") as client:
                response = await client.get(
                    "/api/v3/ios/rating/leaderboard?tz=480",
                    headers={"Authorization": "Bearer token"},
                )

        self.assertEqual(200, response.status_code)
        self.assertEqual(2, response.json()["rank"])
        self.assertNotIn("telegram_id", response.json()["leaderboard"][0])
        service.leaderboard.assert_awaited_once_with(
            user, limit=50, timezone_offset_minutes=480
        )

    async def test_referral_uses_shared_referral_service(self):
        user = SimpleNamespace(id=7, telegram_id=123, referral_code="ABC123")
        context = SimpleNamespace(user=SimpleNamespace(telegram_id=123))
        service = SimpleNamespace(
            list_miniapp_referrals=AsyncMock(return_value=[{
                "name": "Friend", "status": "active", "joined_at": "2026-09-01",
                "activated_at": "2026-09-02", "course_level": "hsk1",
                "completed_lessons": 2, "is_paid": False,
            }]),
            get_trial_activation_progress=AsyncMock(return_value=1),
        )
        session = MagicMock()
        session.commit = AsyncMock()

        @asynccontextmanager
        async def session_factory():
            yield session

        app = FastAPI()
        app.include_router(create_ios_social_router(
            session_factory=session_factory,
            settings_obj=SimpleNamespace(
                DESKTOP_AUTH_SIGNING_SECRET="secret",
                BOT_USERNAME="hsk_ai_bot",
            ),
            referral_service_factory=lambda *_: service,
        ))

        with (
            patch("app.api.ios_social.DesktopAuthService.authenticate",
                  new=AsyncMock(return_value=context)),
            patch("app.api.ios_social.UserRepository.get_by_telegram_id",
                  new=AsyncMock(return_value=user)),
        ):
            async with AsyncClient(transport=ASGITransport(app=app),
                                   base_url="https://testserver") as client:
                response = await client.get(
                    "/api/v3/ios/referral/overview?tz=480",
                    headers={"Authorization": "Bearer token"},
                )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("ABC123", payload["code"])
        self.assertEqual(1, payload["activated"])
        self.assertEqual("Friend", payload["items"][0]["name"])
        self.assertNotIn("telegram_id", payload["items"][0])


if __name__ == "__main__":
    unittest.main()

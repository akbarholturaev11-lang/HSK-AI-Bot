"""A lost onboarding POST response must not force a second write.

The confirmation route is read-only. Its payload is the persisted user level
and profile preferences, not a client-submitted success flag.
"""
import os
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# The main module constructs an aiogram Bot at import time. This is a fake
# syntactically valid test token; no network calls are made by these tests.
os.environ.setdefault("BOT_TOKEN", "123456:AA_MiniAppOnboardingTestToken")

from app import main as main_module


class OnboardingSaveConfirmationApiTests(unittest.IsolatedAsyncioTestCase):
    async def get_status(
        self, *, user=None, profile=None, telegram_id=123,
        foundation=None,
    ):
        if user is None:
            user = SimpleNamespace(id=4, telegram_id=123, level="nhsk1")
        if foundation is None:
            foundation = {"required": False, "completed": False}
        session = SimpleNamespace(
            execute=AsyncMock(return_value=SimpleNamespace(
                scalar_one_or_none=lambda: profile,
            )),
            commit=AsyncMock(),
        )

        @asynccontextmanager
        async def session_factory():
            yield session

        app = FastAPI()
        app.add_api_route(
            "/api/miniapp/onboarding/status",
            main_module.miniapp_onboarding_status,
            methods=["GET"],
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test",
        ) as client:
            with (
                patch.object(
                    main_module, "extract_verified_webapp_user_id",
                    return_value=telegram_id,
                ),
                patch.object(main_module, "async_session_maker", session_factory),
                patch.object(
                    main_module, "UserRepository",
                    return_value=SimpleNamespace(
                        get_by_telegram_id=AsyncMock(return_value=user),
                    ),
                ),
                patch.object(
                    main_module.CourseMiniAppProfileService,
                    "foundation_status",
                    new=AsyncMock(return_value=foundation),
                ),
            ):
                response = await client.get(
                    "/api/miniapp/onboarding/status",
                    headers={"X-Telegram-Init-Data": "valid"},
                )
        return response, session

    async def test_completed_hsk30_choice_is_confirmed_without_any_write(self):
        saved = SimpleNamespace(
            onboarding_completed_at=datetime.now(timezone.utc),
            goal="daily_communication",
            daily_minutes=10,
            start_mode="lesson_1",
        )
        response, session = await self.get_status(profile=saved)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.json(), {
            "ok": True,
            "saved": True,
            "level": "nhsk1",
            "profile": {
                "goal": "daily_communication",
                "daily_minutes": 10,
                "start_mode": "lesson_1",
            },
            "foundation_required": False,
        })
        session.commit.assert_not_awaited()

    async def test_unfinished_profile_is_not_mistaken_for_a_saved_choice(self):
        saved = SimpleNamespace(
            onboarding_completed_at=None,
            goal="hsk_exam", daily_minutes=10, start_mode="lesson_1",
        )
        response, session = await self.get_status(profile=saved)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["saved"])
        self.assertIsNone(response.json()["profile"])
        session.commit.assert_not_awaited()

    async def test_missing_profile_is_not_success(self):
        response, _ = await self.get_status(profile=None)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["saved"])

    async def test_beginner_recovery_preserves_starter_foundation(self):
        user = SimpleNamespace(id=4, telegram_id=123, level="beginner")
        saved = SimpleNamespace(
            onboarding_completed_at=datetime.now(timezone.utc),
            goal="hsk_exam", daily_minutes=10, start_mode="lesson_1",
        )
        response, _ = await self.get_status(
            profile=saved, user=user,
            foundation={"required": True, "completed": False},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["foundation_required"])

    async def test_invalid_telegram_session_is_rejected(self):
        response, session = await self.get_status(telegram_id=None)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "invalid_telegram_init_data")
        session.execute.assert_not_awaited()

    async def test_unknown_telegram_user_is_rejected(self):
        # Explicitly bypass the default mock user in the helper.
        session = SimpleNamespace(execute=AsyncMock(), commit=AsyncMock())

        @asynccontextmanager
        async def sf():
            yield session

        app = FastAPI()
        app.add_api_route(
            "/api/miniapp/onboarding/status",
            main_module.miniapp_onboarding_status, methods=["GET"],
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test",
        ) as client:
            with (
                patch.object(main_module, "extract_verified_webapp_user_id", return_value=123),
                patch.object(main_module, "async_session_maker", sf),
                patch.object(
                    main_module, "UserRepository",
                    return_value=SimpleNamespace(
                        get_by_telegram_id=AsyncMock(return_value=None),
                    ),
                ),
            ):
                response = await client.get(
                    "/api/miniapp/onboarding/status",
                    headers={"X-Telegram-Init-Data": "valid"},
                )
        self.assertEqual(response.status_code, 403)
        session.execute.assert_not_awaited()


class MiniAppOnboardingSaveRecoveryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path("app/static/course_v3_onboarding.html").read_text(
            encoding="utf-8",
        )

    def test_retry_checks_server_before_repeating_post(self):
        self.assertIn("if(saveNeedsVerification){", self.html)
        self.assertIn("confirmSavedOnServer(payload).then(function(saved)", self.html)
        self.assertIn('"/api/miniapp/onboarding/status?"', self.html)
        self.assertIn('postJson("/api/miniapp/onboarding",payload,controller?controller.signal:undefined,false)', self.html)

    def test_success_requires_saved_preferences_and_matching_level(self):
        self.assertIn("data&&data.ok&&data.saved&&data.profile", self.html)
        self.assertIn("var samePreferences=", self.html)
        self.assertIn("if(!sameLevel||!samePreferences)return null", self.html)

    def test_local_draft_is_only_removed_on_confirmed_success(self):
        self.assertEqual(
            self.html.count('localStorage.removeItem("hsk_v3_onb_goal")'), 1,
        )
        self.assertIn("if(saved)go(saved)", self.html)
        self.assertIn("else fail(reason)", self.html)

    def test_failure_is_diagnosable_without_leaking_auth_secrets(self):
        self.assertIn('error_name:"OnboardingSaveResponseError"', self.html)
        self.assertIn("recovered:!!recovered", self.html)
        self.assertNotIn('error_message:INIT_DATA', self.html)


if __name__ == "__main__":
    unittest.main()

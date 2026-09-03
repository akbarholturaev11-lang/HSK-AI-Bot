"""Regression coverage for the Android feature adapter.

The adapter owns no business logic of its own — it authenticates a bearer
token and forwards to the canonical services. These tests therefore protect
the two things that *are* the adapter's responsibility:

1. Nothing is reachable without a valid Android bearer token.
2. Subscription is never sold inside the Android app. The app is handed off to
   the Telegram bot, which offers the existing subscription Mini App, and the
   adapter never grants access by itself.
"""

import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.android_features import (
    _bot_url,
    _service_response,
    _subscription_payload,
    create_android_features_router,
)
from app.db.base import Base
from app.db.models.user import User
from app.services.desktop_auth_service import DesktopAuthService


def _settings(bot_username="pomp_test_bot"):
    return SimpleNamespace(
        DESKTOP_AUTH_SIGNING_SECRET="android-features-test-secret-" + "x" * 40,
        DESKTOP_AUTH_LINK_TTL_SECONDS=600,
        DESKTOP_AUTH_ACCESS_TTL_SECONDS=900,
        DESKTOP_AUTH_REFRESH_TTL_DAYS=30,
        BOT_USERNAME=bot_username,
    )


def _user(user_id: int, telegram_id: int, name: str) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
        telegram_id=telegram_id,
        full_name=name,
        language="uz",
        level="hsk3",
        learning_mode="course",
        voice_mode="none",
        status="free",
        payment_status="none",
        question_limit=5,
        questions_used=0,
        bonus_questions=0,
        bonus_questions_used=0,
        discount_referral_count=0,
        discount_eligible=False,
        discount_used=False,
        daily_practice_streak=0,
        created_at=now,
        last_active_at=now,
    )


class AndroidBotUrlTests(unittest.TestCase):
    def test_username_forms_resolve_to_one_link(self):
        self.assertEqual("https://t.me/pomp_bot", _bot_url(_settings("pomp_bot")))
        self.assertEqual("https://t.me/pomp_bot", _bot_url(_settings("@pomp_bot")))
        self.assertEqual("https://t.me/pomp_bot", _bot_url(_settings("  pomp_bot  ")))

    def test_missing_username_yields_no_link_instead_of_a_broken_one(self):
        # A "https://t.me/" button would dead-end the learner, so the absence
        # of a username has to stay visible to the caller.
        self.assertEqual("", _bot_url(_settings("")))
        self.assertEqual("", _bot_url(_settings(None)))
        self.assertEqual("", _bot_url(SimpleNamespace()))


class AndroidLimitPassthroughTests(unittest.TestCase):
    """The client shows WHEN the limit reopens, so the instant must survive."""

    @staticmethod
    def _body(response):
        return json.loads(bytes(response.body).decode("utf-8"))

    def test_the_reset_instant_reaches_the_client(self):
        response = _service_response(
            {
                "ok": False,
                "error": "free_feature_limit_reached",
                "reset_at": "2026-09-16T00:00:00+00:00",
                "lifetime": False,
            }
        )
        self.assertEqual(403, response.status_code)
        body = self._body(response)
        self.assertEqual("2026-09-16T00:00:00+00:00", body["reset_at"])
        self.assertFalse(body["lifetime"])

    def test_a_lifetime_limit_reports_no_reset_instead_of_a_wrong_one(self):
        response = _service_response(
            {"ok": False, "error": "free_feature_limit_reached", "reset_at": None, "lifetime": True}
        )
        body = self._body(response)
        self.assertIsNone(body["reset_at"])
        self.assertTrue(body["lifetime"])

    def test_other_failures_are_unchanged(self):
        response = _service_response({"ok": False, "error": "mistake_review_empty"})
        self.assertEqual(404, response.status_code)
        self.assertEqual({"ok": False, "error": "mistake_review_empty"}, self._body(response))


class AndroidSubscriptionPayloadTests(unittest.TestCase):
    def test_checkout_is_never_offered_inside_the_app(self):
        payload = _subscription_payload(
            _user(1, 1001, "Account A"),
            {"subscription": {"until": None}},
            _settings(),
        )
        self.assertFalse(payload["checkout_allowed"])
        self.assertEqual("telegram_bot", payload["billing"]["provider"])
        self.assertEqual("https://t.me/pomp_test_bot", payload["billing"]["bot_url"])
        self.assertTrue(payload["billing"]["configured"])
        self.assertFalse(payload["access"]["is_paid"])

    def test_handoff_is_reported_unconfigured_without_a_bot_username(self):
        payload = _subscription_payload(
            _user(1, 1001, "Account A"),
            {"subscription": {}},
            _settings(""),
        )
        self.assertFalse(payload["billing"]["configured"])
        self.assertEqual("", payload["billing"]["bot_url"])
        self.assertIn("BOT_USERNAME", payload["billing"]["required_external_config"])


class AndroidSubscriptionHandoffApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(_user(1, 1001, "Account A"))
            await session.commit()
        self.bot = SimpleNamespace(send_message=AsyncMock())

    async def asyncTearDown(self):
        await self.engine.dispose()

    def _client(self, settings_obj=None, bot=...):
        app = FastAPI()
        app.include_router(
            create_android_features_router(
                session_factory=self.sessions,
                settings_obj=settings_obj or _settings(),
                bot=self.bot if bot is ... else bot,
            )
        )
        return AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://android.test",
        )

    async def _token(self, installation="i" * 48):
        async with self.sessions() as session:
            auth = DesktopAuthService(session, _settings())
            started = await auth.start_link(
                platform="android",
                app_version="1.1.0",
                installation_key=installation,
            )
            await auth.approve_link(
                display_code=started["display_code"],
                telegram_id=1001,
            )
            linked = await auth.poll_link(
                link_request_id=started["link_request_id"],
                polling_secret=started["polling_secret"],
            )
            return linked["access_token"]

    async def test_handoff_sends_the_menu_and_returns_the_bot_link(self):
        token = await self._token()
        async with self._client() as client:
            with patch(
                "app.api.android_features.StudyMiniAppService.send_subscription_menu",
                AsyncMock(return_value=True),
            ) as send:
                response = await client.post(
                    "/api/v3/android/subscription/open",
                    headers={"Authorization": f"Bearer {token}"},
                )

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertTrue(body["message_sent"])
        self.assertEqual("https://t.me/pomp_test_bot", body["bot_url"])
        self.assertEqual(1, send.await_count)
        # The adapter must not invent its own subscription copy or keyboard.
        self.assertEqual(1001, send.await_args.args[1])

    async def test_a_failed_message_still_hands_the_learner_the_bot_link(self):
        # Telegram can refuse the message (the user blocked the bot, a network
        # hiccup). Opening the bot chat still reaches the same menu, so the
        # button must not dead-end.
        token = await self._token()
        async with self._client() as client:
            with patch(
                "app.api.android_features.StudyMiniAppService.send_subscription_menu",
                AsyncMock(return_value=False),
            ):
                response = await client.post(
                    "/api/v3/android/subscription/open",
                    headers={"Authorization": f"Bearer {token}"},
                )

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertFalse(body["message_sent"])
        self.assertEqual("https://t.me/pomp_test_bot", body["bot_url"])

    async def test_handoff_requires_a_bearer_token(self):
        async with self._client() as client:
            response = await client.post("/api/v3/android/subscription/open")
        self.assertEqual(401, response.status_code)
        self.assertFalse(response.json()["ok"])
        self.bot.send_message.assert_not_awaited()

    async def test_handoff_rejects_a_forged_token(self):
        async with self._client() as client:
            response = await client.post(
                "/api/v3/android/subscription/open",
                headers={"Authorization": "Bearer not-a-real-token"},
            )
        self.assertEqual(401, response.status_code)
        self.bot.send_message.assert_not_awaited()

    async def test_identity_is_never_taken_from_the_query_string(self):
        token = await self._token()
        async with self._client() as client:
            response = await client.post(
                "/api/v3/android/subscription/open?telegram_id=9999",
                headers={"Authorization": f"Bearer {token}"},
            )
        self.assertEqual(422, response.status_code)
        self.bot.send_message.assert_not_awaited()

    async def test_handoff_fails_closed_without_a_bot_username(self):
        token = await self._token()
        async with self._client(settings_obj=_settings("")) as client:
            response = await client.post(
                "/api/v3/android/subscription/open",
                headers={"Authorization": f"Bearer {token}"},
            )
        # No link to send the learner to: say so rather than opening
        # "https://t.me/" and losing them.
        self.assertEqual(503, response.status_code)
        self.assertFalse(response.json()["ok"])

    async def test_a_missing_bot_still_returns_the_link(self):
        # The worker that serves the API may run without a bot instance; the
        # learner can still open the chat themselves.
        token = await self._token()
        async with self._client(bot=None) as client:
            response = await client.post(
                "/api/v3/android/subscription/open",
                headers={"Authorization": f"Bearer {token}"},
            )
        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertFalse(body["message_sent"])
        self.assertEqual("https://t.me/pomp_test_bot", body["bot_url"])

    async def test_overview_reports_the_handoff_and_never_a_checkout(self):
        token = await self._token()
        async with self._client() as client:
            response = await client.get(
                "/api/v3/android/subscription/overview",
                headers={"Authorization": f"Bearer {token}"},
            )
        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertFalse(body["checkout_allowed"])
        self.assertEqual("telegram_bot", body["billing"]["provider"])
        self.assertEqual("https://t.me/pomp_test_bot", body["billing"]["bot_url"])
        self.assertFalse(body["access"]["is_paid"])


class AndroidFeatureAuthTests(unittest.IsolatedAsyncioTestCase):
    """Every feature route is bearer-only; none of them accept an anonymous call."""

    ROUTES = (
        ("GET", "/api/v3/android/profile"),
        ("GET", "/api/v3/android/subscription/overview"),
        ("POST", "/api/v3/android/subscription/open"),
        ("POST", "/api/v3/android/practice/start"),
        ("POST", "/api/v3/android/practice/complete"),
        ("GET", "/api/v3/android/mistakes"),
        ("POST", "/api/v3/android/mistakes/review/start"),
        ("POST", "/api/v3/android/mistakes/review/answer"),
        ("POST", "/api/v3/android/mistakes/review/complete"),
        ("GET", "/api/v3/android/rating/leaderboard"),
        ("GET", "/api/v3/android/referral/overview"),
        ("GET", "/api/v3/android/voice/status"),
        ("POST", "/api/v3/android/voice/session/start"),
        ("POST", "/api/v3/android/voice/message"),
        ("POST", "/api/v3/android/voice/session/end"),
    )

    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        app = FastAPI()
        app.include_router(
            create_android_features_router(
                session_factory=self.sessions,
                settings_obj=_settings(),
                bot=SimpleNamespace(send_message=AsyncMock()),
            )
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://android.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def test_the_adapter_exposes_exactly_the_known_routes(self):
        app = FastAPI()
        router = create_android_features_router(
            session_factory=self.sessions,
            settings_obj=_settings(),
        )
        app.include_router(router)
        exposed = {
            (method, route.path)
            for route in router.routes
            for method in route.methods
            if method != "HEAD"
        }
        self.assertEqual(set(self.ROUTES), exposed)

    #: Routes that take no request body, so the bearer check is the first gate.
    BODYLESS_ROUTES = (
        ("GET", "/api/v3/android/profile"),
        ("GET", "/api/v3/android/subscription/overview"),
        ("POST", "/api/v3/android/subscription/open"),
        ("GET", "/api/v3/android/mistakes"),
        ("GET", "/api/v3/android/rating/leaderboard"),
        ("GET", "/api/v3/android/referral/overview"),
        ("GET", "/api/v3/android/voice/status"),
    )

    async def test_no_route_does_any_work_without_a_bearer_token(self):
        # Routes carrying a body validate it before the bearer check, so an
        # anonymous call is refused as 422 rather than 401. Either way it is
        # refused and nothing runs — that is the invariant worth pinning.
        for method, path in self.ROUTES:
            with self.subTest(route=f"{method} {path}"):
                response = await self.client.request(method, path, json={})
                self.assertIn(response.status_code, (401, 422))
                self.assertFalse(response.json().get("ok", False))

    async def test_bodyless_routes_reject_anonymous_callers_as_unauthorised(self):
        for method, path in self.BODYLESS_ROUTES:
            with self.subTest(route=f"{method} {path}"):
                response = await self.client.request(method, path)
                self.assertEqual(401, response.status_code)
                self.assertFalse(response.json()["ok"])


if __name__ == "__main__":
    unittest.main()

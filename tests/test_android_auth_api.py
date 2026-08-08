"""Regression coverage for the native Android device-link adapter.

These tests protect two things at once:

1. Android works — the platform is accepted, the bot names the right device,
   the code never leaks into the deep link and analytics stay in their own
   namespace.
2. Desktop did not regress — macOS and Windows keep working and keep emitting
   the exact ``desktop_*`` event names admin statistics already depend on.
"""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.android_auth import AndroidLinkStartRequest, create_android_auth_router
from app.api.desktop_auth import DesktopLinkStartRequest
from app.bot.handlers import desktop_auth as desktop_auth_handler
from app.db.base import Base
from app.db.models.course_miniapp_event import (
    COURSE_MINIAPP_EVENT_NAMES,
    CourseMiniAppEvent,
)
from app.db.models.user import User
from app.services.desktop_auth_service import (
    DESKTOP_PLATFORMS,
    MOBILE_PLATFORMS,
    NATIVE_PLATFORMS,
    DesktopAuthError,
    DesktopAuthService,
    analytics_prefix,
)


def _settings():
    return SimpleNamespace(
        DESKTOP_AUTH_SIGNING_SECRET="android-auth-test-secret-" + "x" * 40,
        DESKTOP_AUTH_LINK_TTL_SECONDS=600,
        DESKTOP_AUTH_ACCESS_TTL_SECONDS=900,
        DESKTOP_AUTH_REFRESH_TTL_DAYS=30,
        BOT_USERNAME="pomp_test_bot",
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


class AndroidPlatformAllowlistTests(unittest.TestCase):
    def test_android_is_native_but_not_desktop(self):
        self.assertIn("android", NATIVE_PLATFORMS)
        self.assertIn("android", MOBILE_PLATFORMS)
        # Desktop-only consumers (downloads, release manifest, desktop admin
        # statistics) must not silently start counting Android.
        self.assertNotIn("android", DESKTOP_PLATFORMS)
        self.assertEqual({"macos", "windows"}, DESKTOP_PLATFORMS)

    def test_analytics_prefix_separates_android_from_desktop(self):
        self.assertEqual("android", analytics_prefix("android"))
        self.assertEqual("desktop", analytics_prefix("macos"))
        self.assertEqual("desktop", analytics_prefix("windows"))
        self.assertEqual("desktop", analytics_prefix(None))

    def test_android_event_names_are_allowlisted_and_never_desktop_named(self):
        for name in (
            "android_session_linked",
            "android_first_open",
            "android_app_opened",
            "android_update_installed",
        ):
            self.assertIn(name, COURSE_MINIAPP_EVENT_NAMES)

    def test_android_start_payload_rejects_other_platforms(self):
        # The Android endpoint may only ever start an Android link.
        with self.assertRaises(ValidationError):
            AndroidLinkStartRequest(
                platform="windows",
                app_version="1.0.0",
                installation_key="k" * 48,
            )
        # The desktop endpoint stays closed to Android.
        with self.assertRaises(ValidationError):
            DesktopLinkStartRequest(
                platform="android",
                app_version="1.0.0",
                installation_key="k" * 48,
            )


class AndroidAuthServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all(
                [_user(1, 1001, "Account A"), _user(2, 1002, "Account B")]
            )
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _start(self, session, *, platform, installation_key="i" * 48):
        return await DesktopAuthService(session, _settings()).start_link(
            platform=platform,
            app_version="1.0.0",
            installation_key=installation_key,
        )

    async def _link(self, session, *, platform, telegram_id=1001):
        service = DesktopAuthService(session, _settings())
        started = await self._start(session, platform=platform)
        await service.approve_link(
            display_code=started["display_code"],
            telegram_id=telegram_id,
        )
        linked = await service.poll_link(
            link_request_id=started["link_request_id"],
            polling_secret=started["polling_secret"],
        )
        return service, started, linked

    async def _event_names(self, session, telegram_id=1001):
        result = await session.execute(
            select(CourseMiniAppEvent.event_name).where(
                CourseMiniAppEvent.telegram_id == telegram_id
            )
        )
        return set(result.scalars().all())

    async def test_every_native_platform_can_start_a_link(self):
        for index, platform in enumerate(sorted(NATIVE_PLATFORMS)):
            with self.subTest(platform=platform):
                async with self.sessions() as session:
                    started = await self._start(
                        session,
                        platform=platform,
                        installation_key=f"{index}" * 48,
                    )
                self.assertEqual("pending", started["status"])
                self.assertEqual(8, len(started["display_code"]))

    async def test_unknown_platform_is_rejected(self):
        async with self.sessions() as session:
            for platform in ("ios", "linux", "web", "", "ANDROID "):
                with self.subTest(platform=platform):
                    with self.assertRaises(DesktopAuthError) as rejected:
                        await self._start(session, platform=platform)
                    self.assertEqual(
                        "desktop_platform_invalid",
                        rejected.exception.code,
                    )

    async def test_android_display_code_never_reaches_the_deep_link(self):
        async with self.sessions() as session:
            started = await self._start(session, platform="android")

        self.assertEqual(
            "https://t.me/pomp_test_bot?start=desktop_link",
            started["bot_deep_link"],
        )
        self.assertNotIn(started["display_code"], started["bot_deep_link"])
        self.assertNotIn(started["polling_secret"], started["bot_deep_link"])

    async def test_android_link_emits_android_analytics_only(self):
        async with self.sessions() as session:
            service, _started, linked = await self._link(
                session,
                platform="android",
            )
            self.assertEqual("linked", linked["status"])
            await service.bootstrap(linked["access_token"], app_version="1.0.0")
            names = await self._event_names(session)

        self.assertIn("android_session_linked", names)
        self.assertIn("android_first_open", names)
        self.assertIn("android_app_opened", names)
        self.assertFalse({name for name in names if name.startswith("desktop_")})

    async def test_desktop_link_still_emits_desktop_analytics(self):
        async with self.sessions() as session:
            service, _started, linked = await self._link(
                session,
                platform="macos",
            )
            await service.bootstrap(linked["access_token"], app_version="1.0.0")
            names = await self._event_names(session)

        self.assertIn("desktop_session_linked", names)
        self.assertIn("desktop_first_open", names)
        self.assertIn("desktop_app_opened", names)
        self.assertFalse({name for name in names if name.startswith("android_")})

    async def test_android_bootstrap_returns_the_canonical_account(self):
        async with self.sessions() as session:
            service, _started, linked = await self._link(
                session,
                platform="android",
            )
            bootstrap = await service.bootstrap(linked["access_token"])

        self.assertTrue(bootstrap["authenticated"])
        self.assertEqual("android", bootstrap["device"]["platform"])
        # The HSK level comes from the canonical user, never from the client.
        self.assertEqual("hsk3", bootstrap["user"]["level"])
        self.assertEqual("uz", bootstrap["user"]["language"])
        self.assertFalse(bootstrap["user"]["is_paid"])

    async def test_android_refresh_rotates_and_detects_reuse(self):
        async with self.sessions() as session:
            service, _started, linked = await self._link(
                session,
                platform="android",
            )
            first = linked["refresh_token"]
            rotated = await service.refresh(first)
            self.assertNotEqual(first, rotated["refresh_token"])

            with self.assertRaises(DesktopAuthError) as reused:
                await service.refresh(first)
            self.assertEqual(
                "desktop_refresh_reuse_detected",
                reused.exception.code,
            )

            with self.assertRaises(DesktopAuthError) as revoked:
                await service.refresh(rotated["refresh_token"])
            self.assertEqual("desktop_session_revoked", revoked.exception.code)

    async def test_android_installation_cannot_silently_switch_account(self):
        async with self.sessions() as session:
            await self._link(session, platform="android", telegram_id=1001)

            service = DesktopAuthService(session, _settings())
            second = await self._start(session, platform="android")
            await service.approve_link(
                display_code=second["display_code"],
                telegram_id=1002,
            )
            with self.assertRaises(DesktopAuthError) as bound:
                await service.poll_link(
                    link_request_id=second["link_request_id"],
                    polling_secret=second["polling_secret"],
                )
            self.assertEqual(
                "desktop_device_bound_to_other_user",
                bound.exception.code,
            )

    async def test_android_logout_revokes_the_session(self):
        async with self.sessions() as session:
            service, _started, linked = await self._link(
                session,
                platform="android",
            )
            await service.revoke(linked["access_token"], revoke_device=False)
            with self.assertRaises(DesktopAuthError) as revoked:
                await service.bootstrap(linked["access_token"])
            self.assertEqual("desktop_session_revoked", revoked.exception.code)


class AndroidAuthApiTests(unittest.IsolatedAsyncioTestCase):
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

        app = FastAPI()
        app.include_router(
            create_android_auth_router(
                session_factory=self.sessions,
                settings_obj=_settings(),
            )
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://android.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def test_link_start_returns_no_store_and_no_code_in_link(self):
        response = await self.client.post(
            "/api/v3/android-auth/link/start",
            json={
                "platform": "android",
                "app_version": "1.0.0",
                "installation_key": "k" * 48,
            },
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual("no-store", response.headers.get("Cache-Control"))
        payload = response.json()
        self.assertNotIn(payload["display_code"], payload["bot_deep_link"])

    async def test_extra_fields_and_short_installation_key_are_rejected(self):
        for body in (
            {
                "platform": "android",
                "app_version": "1.0.0",
                "installation_key": "k" * 48,
                "telegram_id": 1001,
            },
            {
                "platform": "android",
                "app_version": "1.0.0",
                "installation_key": "short",
            },
        ):
            with self.subTest(body=sorted(body)):
                response = await self.client.post(
                    "/api/v3/android-auth/link/start",
                    json=body,
                )
                self.assertEqual(422, response.status_code)
                self.assertEqual(
                    {"ok": False, "error": "desktop_request_invalid"},
                    response.json(),
                )

    async def test_bootstrap_requires_a_bearer_token(self):
        response = await self.client.get("/api/v3/android/bootstrap")
        self.assertEqual(401, response.status_code)
        self.assertFalse(response.json()["ok"])
        self.assertEqual("no-store", response.headers.get("Cache-Control"))


class AndroidBotConfirmationTests(unittest.IsolatedAsyncioTestCase):
    """The Telegram confirmation must name the real device, in all languages."""

    class _State:
        def __init__(self):
            self.state = None
            self.data = {}

        async def get_state(self):
            return self.state

        async def get_data(self):
            return dict(self.data)

        async def set_state(self, state):
            self.state = getattr(state, "state", state)

        async def update_data(self, **kwargs):
            self.data.update(kwargs)

        async def clear(self):
            self.state = None
            self.data = {}

    class _Message:
        def __init__(self, text=None):
            self.text = text
            self.from_user = SimpleNamespace(id=1001)
            self.answers = []

        async def answer(self, text, **kwargs):
            self.answers.append((text, kwargs))

    def test_platform_labels_cover_every_native_platform(self):
        for platform in NATIVE_PLATFORMS:
            with self.subTest(platform=platform):
                label = desktop_auth_handler._platform_label(platform)
                self.assertTrue(label)
                self.assertNotEqual("Pomp HSK AI", label)
        self.assertEqual("Android", desktop_auth_handler._platform_label("android"))
        self.assertEqual("Mac", desktop_auth_handler._platform_label("macos"))
        self.assertEqual("Windows", desktop_auth_handler._platform_label("windows"))

    def test_every_language_has_desktop_and_mobile_wording(self):
        for language, copy in desktop_auth_handler._COPY.items():
            with self.subTest(language=language):
                for key in (
                    "confirm_desktop",
                    "confirm_mobile",
                    "ok_desktop",
                    "ok_mobile",
                ):
                    self.assertIn(key, copy)
                    self.assertTrue(copy[key].strip())

    async def _confirmation_text(self, language, platform):
        state = self._State()
        start = self._Message("/start desktop_link")
        typed = self._Message("hsk4827x")
        preview = AsyncMock(
            return_value={
                "platform": platform,
                "app_version": "1.0.0",
                "display_code": "HSK4827X",
            }
        )
        with patch.object(
            desktop_auth_handler,
            "_language",
            new=AsyncMock(return_value=language),
        ), patch.object(desktop_auth_handler, "DesktopAuthService") as service:
            service.return_value.link_preview = preview
            await desktop_auth_handler.begin_desktop_link(start, state, object())
            await desktop_auth_handler.receive_desktop_link_code(
                typed,
                state,
                object(),
            )
        self.assertEqual(1, len(typed.answers))
        return typed.answers[0][0]

    async def test_android_confirmation_says_android_in_all_languages(self):
        for language in ("uz", "ru", "tj"):
            with self.subTest(language=language):
                text = await self._confirmation_text(language, "android")
                self.assertIn("<b>Android</b>", text)
                # The historic "Mac or else Windows" shortcut would have shown
                # an Android phone as a Windows computer.
                self.assertNotIn("Windows", text)
                self.assertIn("HSK4827X", text)

    async def test_desktop_confirmation_wording_is_unchanged(self):
        text = await self._confirmation_text("uz", "macos")
        self.assertIn("Qurilma: <b>Mac</b>", text)
        self.assertNotIn("Android", text)


if __name__ == "__main__":
    unittest.main()

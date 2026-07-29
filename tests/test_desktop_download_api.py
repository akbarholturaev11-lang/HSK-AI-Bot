import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.desktop_download import (
    DesktopDownloadStartedRequest,
    create_desktop_download_router,
)
from app.db.base import Base
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.user import User
from app.services.desktop_download_service import (
    DesktopDownloadError,
    DesktopDownloadService,
    DesktopReleaseConfig,
)


def _settings(**overrides):
    values = {
        "BOT_TOKEN": "test-token",
        "MINI_APP_BASE_URL": "https://app.example.test/course-v3.html",
        "DESKTOP_DOWNLOADS_ENABLED": True,
        "DESKTOP_DOWNLOAD_BASE_URL": "https://app.example.test",
        "DESKTOP_MAC_DOWNLOAD_URL": (
            "https://releases.example.test/Pomp-HSK-AI-universal.dmg"
        ),
        "DESKTOP_WINDOWS_DOWNLOAD_URL": (
            "https://releases.example.test/Pomp-HSK-AI-x64-setup.exe"
        ),
        "DESKTOP_MAC_VERSION": "1.0.0",
        "DESKTOP_WINDOWS_VERSION": "1.0.0",
        "DESKTOP_DOWNLOAD_RATE_LIMIT_COUNT": 3,
        "DESKTOP_DOWNLOAD_RATE_LIMIT_WINDOW_SECONDS": 900,
        "DESKTOP_DOWNLOAD_AUTH_MAX_AGE_SECONDS": 300,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _user() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=1,
        telegram_id=1001,
        full_name="Desktop Student",
        language="uz",
        level="hsk1",
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


class DesktopDownloadServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(_user())
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    def test_release_config_is_fail_closed_and_requires_installer_suffix(self):
        disabled = DesktopReleaseConfig.from_settings(
            _settings(DESKTOP_DOWNLOADS_ENABLED=False)
        )
        insecure = DesktopReleaseConfig.from_settings(
            _settings(DESKTOP_MAC_DOWNLOAD_URL="http://example.test/Pomp.dmg")
        )
        wrong_suffix = DesktopReleaseConfig.from_settings(
            _settings(DESKTOP_WINDOWS_DOWNLOAD_URL="https://example.test/Pomp.zip")
        )
        ready = DesktopReleaseConfig.from_settings(_settings())

        self.assertFalse(disabled.enabled)
        self.assertFalse(insecure.enabled and insecure.macos_url)
        self.assertIsNone(wrong_suffix.windows_url)
        self.assertTrue(ready.enabled)
        self.assertEqual(
            ready.file_name_for("macos"),
            "Pomp-HSK-AI-universal.dmg",
        )

    async def test_request_returns_tracked_download_page_and_safe_filename(self):
        async with self.sessions() as session:
            result = await DesktopDownloadService(session, _settings()).request_download(
                telegram_id=1001,
                platform="macos",
                source="profile",
                event_id="desktop-event-0001",
                language="uz",
            )

            self.assertTrue(result["ok"])
            self.assertEqual(result["platform"], "macos")
            self.assertEqual(result["file_name"], "Pomp-HSK-AI-universal.dmg")
            self.assertEqual(urlsplit(result["download_url"]).hostname, "app.example.test")
            self.assertEqual(urlsplit(result["download_url"]).path, "/desktop-download")
            self.assertEqual(result["download_url"], result["download_page_url"])
            token = parse_qs(urlsplit(result["download_url"]).query)["request"][0]
            self.assertRegex(token, r"^[0-9a-f]{32}$")
            self.assertNotIn("message_sent", result)
            self.assertNotIn("close_mini_app", result)

            event = (
                await session.execute(
                    select(CourseMiniAppEvent).where(
                        CourseMiniAppEvent.event_name
                        == "desktop_download_requested"
                    )
                )
            ).scalar_one()
            self.assertEqual(event.session_id, token)
            self.assertEqual(json.loads(event.payload_json)["entry_source"], "profile")

    async def test_same_event_reuses_token_without_duplicate_event(self):
        async with self.sessions() as session:
            service = DesktopDownloadService(session, _settings())
            first = await service.request_download(
                telegram_id=1001,
                platform="windows",
                source="home_prompt",
                event_id="desktop-event-0002",
                language="uz",
            )
            second = await service.request_download(
                telegram_id=1001,
                platform="windows",
                source="home_prompt",
                event_id="desktop-event-0002",
                language="uz",
            )
            count = (
                await session.execute(
                    select(func.count())
                    .select_from(CourseMiniAppEvent)
                    .where(
                        CourseMiniAppEvent.event_name
                        == "desktop_download_requested"
                    )
                )
            ).scalar()

            self.assertFalse(first["duplicate"])
            self.assertTrue(second["duplicate"])
            self.assertEqual(first["download_url"], second["download_url"])
            self.assertEqual(int(count or 0), 1)

    async def test_started_event_is_authenticated_request_bound_and_idempotent(self):
        async with self.sessions() as session:
            service = DesktopDownloadService(session, _settings())
            await service.request_download(
                telegram_id=1001,
                platform="macos",
                source="lesson_end_promo",
                event_id="desktop-event-0003",
                language="uz",
            )
            first = await service.mark_started(
                telegram_id=1001,
                platform="macos",
                source="lesson_end_promo",
                event_id="desktop-event-0003",
                transport="download_file",
            )
            second = await service.mark_started(
                telegram_id=1001,
                platform="macos",
                source="lesson_end_promo",
                event_id="desktop-event-0003",
                transport="download_file",
            )
            event = (
                await session.execute(
                    select(CourseMiniAppEvent).where(
                        CourseMiniAppEvent.event_name == "desktop_download_started"
                    )
                )
            ).scalar_one()

            self.assertTrue(first["recorded"])
            self.assertTrue(second["duplicate"])
            self.assertEqual(json.loads(event.payload_json)["transport"], "download_file")

            with self.assertRaises(DesktopDownloadError) as wrong_source:
                await service.mark_started(
                    telegram_id=1001,
                    platform="macos",
                    source="profile",
                    event_id="desktop-event-0003",
                    transport="open_link",
                )
            self.assertEqual(wrong_source.exception.code, "desktop_download_not_found")

    async def test_redirect_is_request_bound_and_click_is_idempotent(self):
        async with self.sessions() as session:
            service = DesktopDownloadService(session, _settings())
            result = await service.request_download(
                telegram_id=1001,
                platform="windows",
                source="ad_promo",
                event_id="desktop-event-0004",
                language="ru",
            )
            token = parse_qs(urlsplit(result["download_url"]).query)["request"][0]
            first = await service.resolve_redirect(
                platform="windows",
                request_token=token,
            )
            second = await service.resolve_redirect(
                platform="windows",
                request_token=token,
            )
            count = (
                await session.execute(
                    select(func.count())
                    .select_from(CourseMiniAppEvent)
                    .where(
                        CourseMiniAppEvent.event_name
                        == "desktop_download_link_clicked"
                    )
                )
            ).scalar()

            self.assertEqual(
                first,
                (
                    "https://releases.example.test/Pomp-HSK-AI-x64-setup.exe",
                    "Pomp-HSK-AI-x64-setup.exe",
                ),
            )
            self.assertEqual(first, second)
            self.assertEqual(int(count or 0), 1)

    async def test_public_redirect_needs_no_user_token_and_records_no_fake_install(self):
        async with self.sessions() as session:
            service = DesktopDownloadService(session, _settings())
            target = await service.resolve_redirect(
                platform="macos",
                request_token=None,
            )
            click_count = (
                await session.execute(
                    select(func.count())
                    .select_from(CourseMiniAppEvent)
                    .where(
                        CourseMiniAppEvent.event_name
                        == "desktop_download_link_clicked"
                    )
                )
            ).scalar()

            self.assertEqual(
                target,
                (
                    "https://releases.example.test/Pomp-HSK-AI-universal.dmg",
                    "Pomp-HSK-AI-universal.dmg",
                ),
            )
            self.assertEqual(int(click_count or 0), 0)

    async def test_rate_limit_blocks_only_new_event_ids(self):
        async with self.sessions() as session:
            service = DesktopDownloadService(
                session,
                _settings(DESKTOP_DOWNLOAD_RATE_LIMIT_COUNT=1),
            )
            first = await service.request_download(
                telegram_id=1001,
                platform="macos",
                source="profile",
                event_id="desktop-event-0005",
                language="uz",
            )
            retry = await service.request_download(
                telegram_id=1001,
                platform="macos",
                source="profile",
                event_id="desktop-event-0005",
                language="uz",
            )
            self.assertEqual(first["download_url"], retry["download_url"])
            with self.assertRaises(DesktopDownloadError) as caught:
                await service.request_download(
                    telegram_id=1001,
                    platform="macos",
                    source="profile",
                    event_id="desktop-event-0006",
                    language="uz",
                )
            self.assertEqual(caught.exception.code, "desktop_download_rate_limited")


class DesktopDownloadApiContractTests(unittest.TestCase):
    def test_started_transport_is_explicit_and_extra_fields_are_forbidden(self):
        payload = DesktopDownloadStartedRequest(
            platform="macos",
            source="profile",
            event_id="desktop-event-0007",
            transport="open_link",
        )
        self.assertEqual(payload.transport, "open_link")
        with self.assertRaises(Exception):
            DesktopDownloadStartedRequest(
                platform="macos",
                source="profile",
                event_id="desktop-event-0007",
                transport="browser",
            )

    def test_router_exposes_direct_download_contract_endpoints(self):
        class _Factory:
            def __call__(self):
                raise AssertionError("not called during route inspection")

        paths = {
            route.path
            for route in create_desktop_download_router(
                session_factory=_Factory(),
                settings_obj=_settings(),
            ).routes
        }
        self.assertIn("/api/v3/desktop-download/request", paths)
        self.assertIn("/api/v3/desktop-download/started", paths)
        self.assertIn("/api/v3/desktop-download/public-status", paths)
        self.assertIn("/downloads/macos", paths)
        self.assertIn("/downloads/windows", paths)

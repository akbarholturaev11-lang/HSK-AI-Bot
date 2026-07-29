import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.user import User
from app.api.desktop_auth import (
    DesktopLinkStartRequest,
    DesktopRefreshRequest,
    create_desktop_auth_router,
)
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService


def _settings():
    return SimpleNamespace(
        DESKTOP_AUTH_SIGNING_SECRET="desktop-auth-test-secret-" + "x" * 40,
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


class DesktopAuthServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all([_user(1, 1001, "Account A"), _user(2, 1002, "Account B")])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _start(self, session, installation_key="i" * 48):
        return await DesktopAuthService(session, _settings()).start_link(
            platform="macos",
            app_version="0.1.0",
            installation_key=installation_key,
        )

    async def _link(self, session, telegram_id=1001, installation_key="i" * 48):
        service = DesktopAuthService(session, _settings())
        started = await self._start(session, installation_key)
        await service.approve_link(
            display_code=started["display_code"],
            telegram_id=telegram_id,
        )
        linked = await service.poll_link(
            link_request_id=started["link_request_id"],
            polling_secret=started["polling_secret"],
        )
        return service, started, linked

    async def test_wrong_polling_secret_and_consumed_code_replay_are_rejected(self):
        async with self.sessions() as session:
            service = DesktopAuthService(session, _settings())
            started = await self._start(session)
            with self.assertRaises(DesktopAuthError) as wrong:
                await service.poll_link(
                    link_request_id=started["link_request_id"],
                    polling_secret="z" * 48,
                )
            self.assertEqual(wrong.exception.code, "desktop_link_invalid")

            await service.approve_link(
                display_code=started["display_code"],
                telegram_id=1001,
            )
            linked = await service.poll_link(
                link_request_id=started["link_request_id"],
                polling_secret=started["polling_secret"],
            )
            self.assertEqual(linked["status"], "linked")
            with self.assertRaises(DesktopAuthError) as replay:
                await service.poll_link(
                    link_request_id=started["link_request_id"],
                    polling_secret=started["polling_secret"],
                )
            self.assertEqual(replay.exception.code, "desktop_link_consumed")

    async def test_link_requires_preview_then_explicit_approve_or_cancel(self):
        async with self.sessions() as session:
            service = DesktopAuthService(session, _settings())
            started = await self._start(session)
            preview = await service.link_preview(
                display_code=started["display_code"],
                telegram_id=1001,
            )
            self.assertEqual(preview["platform"], "macos")
            self.assertEqual(preview["app_version"], "0.1.0")

            pending = await service.poll_link(
                link_request_id=started["link_request_id"],
                polling_secret=started["polling_secret"],
            )
            self.assertEqual(pending["status"], "pending")
            with self.assertRaises(DesktopAuthError) as forwarded:
                await service.approve_link(
                    display_code=started["display_code"],
                    telegram_id=1002,
                )
            self.assertEqual(forwarded.exception.code, "desktop_link_invalid")

            await service.cancel_link(
                display_code=started["display_code"],
                telegram_id=1001,
            )
            with self.assertRaises(DesktopAuthError) as cancelled:
                await service.poll_link(
                    link_request_id=started["link_request_id"],
                    polling_secret=started["polling_secret"],
                )
            self.assertEqual(cancelled.exception.code, "desktop_link_invalid")

        handler = Path("app/bot/handlers/desktop_auth.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("link_preview(", handler)
        self.assertIn("desktop_link:approve:", handler)
        self.assertIn("desktop_link:cancel:", handler)

    async def test_expired_code_and_second_account_approval_are_rejected(self):
        async with self.sessions() as session:
            service = DesktopAuthService(session, _settings())
            started = await self._start(session)
            await service.approve_link(
                display_code=started["display_code"],
                telegram_id=1001,
            )
            with self.assertRaises(DesktopAuthError) as second:
                await service.approve_link(
                    display_code=started["display_code"],
                    telegram_id=1002,
                )
            self.assertEqual(second.exception.code, "desktop_link_already_approved")

            expired = await self._start(session, "e" * 48)
            from app.db.models.desktop import DesktopLinkRequest

            item = await session.get(DesktopLinkRequest, expired["link_request_id"])
            item.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await session.commit()
            with self.assertRaises(DesktopAuthError) as caught:
                await service.approve_link(
                    display_code=expired["display_code"],
                    telegram_id=1001,
                )
            self.assertEqual(caught.exception.code, "desktop_link_expired")

    async def test_refresh_rotates_and_previous_token_reuse_revokes_session(self):
        async with self.sessions() as session:
            service, _, linked = await self._link(session)
            rotated = await service.refresh(linked["refresh_token"])
            self.assertNotEqual(
                rotated["refresh_token"],
                linked["refresh_token"],
            )
            with self.assertRaises(DesktopAuthError) as reuse:
                await service.refresh(linked["refresh_token"])
            self.assertEqual(reuse.exception.code, "desktop_refresh_reuse_detected")
            with self.assertRaises(DesktopAuthError) as revoked:
                await service.bootstrap(rotated["access_token"])
            self.assertEqual(revoked.exception.code, "desktop_session_revoked")

    async def test_linked_credentials_survive_optional_analytics_rollback(self):
        async with self.sessions() as session:
            service = DesktopAuthService(session, _settings())
            started = await self._start(session)
            await service.approve_link(
                display_code=started["display_code"],
                telegram_id=1001,
            )

            async def analytics_failure(analytics_self, **kwargs):
                await analytics_self.session.rollback()
                return {"ok": False, "recorded": False}

            with patch(
                "app.services.desktop_auth_service."
                "CourseMiniAppAnalyticsService.record_server_event",
                new=analytics_failure,
            ):
                linked = await service.poll_link(
                    link_request_id=started["link_request_id"],
                    polling_secret=started["polling_secret"],
                )
            bootstrap = await service.bootstrap(linked["access_token"])
            self.assertEqual(bootstrap["user"]["name"], "Account A")

    async def test_first_open_is_recorded_once(self):
        async with self.sessions() as session:
            service, _, linked = await self._link(session)
            first = await service.bootstrap(linked["access_token"])
            second = await service.bootstrap(linked["access_token"])
            self.assertTrue(first["first_open"])
            self.assertFalse(second["first_open"])
            count_result = await session.execute(
                select(func.count())
                .select_from(CourseMiniAppEvent)
                .where(
                    CourseMiniAppEvent.event_name == "desktop_first_open",
                    CourseMiniAppEvent.telegram_id == 1001,
                )
            )
            self.assertEqual(int(count_result.scalar() or 0), 1)

    async def test_bootstrap_records_only_real_version_upgrade_once(self):
        async with self.sessions() as session:
            service, _, linked = await self._link(session)
            initial = await service.bootstrap(
                linked["access_token"],
                app_version="0.1.0",
            )

            upgraded = await service.bootstrap(
                linked["access_token"],
                app_version="1.0.0",
            )
            repeated = await service.bootstrap(
                linked["access_token"],
                app_version="1.0.0",
            )
            downgraded = await service.bootstrap(
                linked["access_token"],
                app_version="0.9.0",
            )

            self.assertFalse(initial["version_upgraded"])
            self.assertTrue(upgraded["version_upgraded"])
            self.assertFalse(repeated["version_upgraded"])
            self.assertFalse(downgraded["version_upgraded"])
            self.assertEqual(downgraded["device"]["app_version"], "0.9.0")

            rows = (
                await session.execute(
                    select(CourseMiniAppEvent).where(
                        CourseMiniAppEvent.event_name
                        == "desktop_update_installed"
                    )
                )
            ).scalars().all()
            self.assertEqual(len(rows), 1)
            payload = json.loads(rows[0].payload_json)
            self.assertEqual(payload["from_version"], "0.1.0")
            self.assertEqual(payload["to_version"], "1.0.0")
            self.assertEqual(payload["app_version"], "1.0.0")

    async def test_account_binding_requires_explicit_device_unlink(self):
        installation_key = "b" * 48
        async with self.sessions() as session:
            service_a, _, linked_a = await self._link(
                session,
                telegram_id=1001,
                installation_key=installation_key,
            )
            service_b = DesktopAuthService(session, _settings())
            started_b = await self._start(session, installation_key)
            await service_b.approve_link(
                display_code=started_b["display_code"],
                telegram_id=1002,
            )
            with self.assertRaises(DesktopAuthError) as bound:
                await service_b.poll_link(
                    link_request_id=started_b["link_request_id"],
                    polling_secret=started_b["polling_secret"],
                )
            self.assertEqual(
                bound.exception.code,
                "desktop_device_bound_to_other_user",
            )

            await service_a.revoke(
                linked_a["access_token"],
                revoke_device=True,
            )
            started_b2 = await self._start(session, installation_key)
            await service_b.approve_link(
                display_code=started_b2["display_code"],
                telegram_id=1002,
            )
            linked_b = await service_b.poll_link(
                link_request_id=started_b2["link_request_id"],
                polling_secret=started_b2["polling_secret"],
            )
            bootstrap = await service_b.bootstrap(linked_b["access_token"])
            self.assertEqual(bootstrap["user"]["name"], "Account B")

    async def test_weak_signing_secret_fails_closed(self):
        weak = _settings()
        weak.DESKTOP_AUTH_SIGNING_SECRET = "short"
        async with self.sessions() as session:
            with self.assertRaises(DesktopAuthError) as caught:
                await DesktopAuthService(session, weak).start_link(
                    platform="macos",
                    app_version="0.1.0",
                    installation_key="i" * 48,
                )
            self.assertEqual(caught.exception.code, "desktop_auth_unavailable")

    async def test_global_link_start_cap_blocks_rotating_installation_keys(self):
        limited = _settings()
        limited.DESKTOP_AUTH_LINK_GLOBAL_RATE_LIMIT_COUNT = 1
        limited.DESKTOP_AUTH_LINK_GLOBAL_RATE_LIMIT_WINDOW_SECONDS = 60
        async with self.sessions() as session:
            service = DesktopAuthService(session, limited)
            await service.start_link(
                platform="macos",
                app_version="0.1.0",
                installation_key="a" * 48,
            )
            with self.assertRaises(DesktopAuthError) as caught:
                await service.start_link(
                    platform="windows",
                    app_version="0.1.0",
                    installation_key="b" * 48,
                )
            self.assertEqual(caught.exception.code, "desktop_link_rate_limited")

    def test_request_model_repr_does_not_expose_refresh_token(self):
        raw = "pomp_r1_" + "sensitive-token-value-" + "x" * 32
        payload = DesktopRefreshRequest(refresh_token=raw)
        self.assertNotIn(raw, repr(payload))
        self.assertNotIn(raw, payload.model_dump_json())

    def test_link_request_rejects_oversized_secret_before_service(self):
        with self.assertRaises(ValueError):
            DesktopLinkStartRequest(
                platform="macos",
                app_version="0.1.0",
                installation_key="x" * 201,
            )

    async def test_api_validation_never_echoes_secret_and_disables_cache(self):
        class _SessionFactory:
            def __call__(self):
                raise AssertionError("invalid payload must not reach the service")

        app = FastAPI()
        app.include_router(
            create_desktop_auth_router(
                session_factory=_SessionFactory(),
                settings_obj=_settings(),
            )
        )
        leaked_secret = "must-never-appear"
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="https://desktop.test",
        ) as client:
            response = await client.post(
                "/api/v3/desktop-auth/link/start",
                json={
                    "platform": "macos",
                    "app_version": "0.1.0",
                    "installation_key": leaked_secret,
                },
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {"ok": False, "error": "desktop_request_invalid"},
        )
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        self.assertNotIn(leaked_secret, response.text)

    async def test_api_rejects_oversized_body_before_service(self):
        class _SessionFactory:
            def __call__(self):
                raise AssertionError("oversized payload must not reach the service")

        app = FastAPI()
        app.include_router(
            create_desktop_auth_router(
                session_factory=_SessionFactory(),
                settings_obj=_settings(),
            )
        )
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="https://desktop.test",
        ) as client:
            response = await client.post(
                "/api/v3/desktop-auth/refresh",
                content=b'{"refresh_token":"' + (b"x" * 3000) + b'"}',
                headers={"Content-Type": "application/json"},
            )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(
            response.json(),
            {"ok": False, "error": "desktop_request_too_large"},
        )
        self.assertEqual(response.headers.get("cache-control"), "no-store")

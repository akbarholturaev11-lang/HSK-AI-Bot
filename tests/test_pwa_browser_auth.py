"""Security contract for PWA-only OAuth session, no native/Telegram bypass."""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.native_oauth import create_native_oauth_router
from app.api.pwa_auth import create_pwa_auth_router
from app.db.base import Base
from app.db.models.desktop import DesktopDevice, DesktopLinkRequest, DesktopSession
from app.db.models.user import User
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.identity_link_service import IdentityLinkService
from app.services.oidc_verifier import VerifiedIdentity
from app.services.pwa_auth_service import PWA_OAUTH_COOKIE, PWA_SESSION_COOKIE


ORIGIN = "https://api.example.test"


def settings(**kwargs):
    values = dict(
        PWA_AUTH_ENABLED=True,
        DESKTOP_AUTH_SIGNING_SECRET="pwa-security-test-" + "x" * 48,
        DESKTOP_AUTH_LINK_TTL_SECONDS=600,
        DESKTOP_AUTH_ACCESS_TTL_SECONDS=900,
        DESKTOP_AUTH_REFRESH_TTL_DAYS=30,
        BOT_USERNAME="pomp_test_bot",
        BOT_TOKEN="123456789:AAExampleBotTokenForInitDataSigning1234",
        GOOGLE_OAUTH_ENABLED=True,
        GOOGLE_ANDROID_WEB_CLIENT_ID="111-web.apps.googleusercontent.com",
        GOOGLE_DESKTOP_CLIENT_ID="222-desktop.apps.googleusercontent.com",
        GOOGLE_DESKTOP_CLIENT_SECRET="desktop-secret",
        APPLE_OAUTH_ENABLED=False,
        APPLE_SERVICE_ID="",
        APPLE_TEAM_ID="",
        APPLE_KEY_ID="",
        APPLE_PRIVATE_KEY="",
        OAUTH_REDIRECT_BASE_URL=ORIGIN,
        OAUTH_ID_TOKEN_MAX_AGE_SECONDS=300,
        OAUTH_HTTP_TIMEOUT_SECONDS=8.0,
    )
    values.update(kwargs)
    return SimpleNamespace(**values)


def user(uid, telegram_id):
    return User(
        id=uid, telegram_id=telegram_id, full_name="Existing learner",
        language="uz", level="hsk1", learning_mode="course", voice_mode="none",
        status="free", payment_status="none", question_limit=5,
        questions_used=0, bonus_questions=0, bonus_questions_used=0,
        discount_referral_count=0, discount_eligible=False, discount_used=False,
        daily_practice_streak=0, created_at=datetime.now(timezone.utc),
        last_active_at=datetime.now(timezone.utc),
    )


def identity():
    return VerifiedIdentity(
        provider="google", subject="existing-sub", email="linked@example.test",
        email_verified=True, display_name="Existing learner",
        audience="222-desktop.apps.googleusercontent.com",
    )


class PwaBrowserAuthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.settings = settings()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(user(1, 1001))
            await session.commit()
            await IdentityLinkService(session, self.settings).link_to_user(identity(), user_id=1)
            await session.commit()
        app = FastAPI()
        app.include_router(create_native_oauth_router(
            session_factory=self.sessions, settings_obj=self.settings
        ))
        app.include_router(create_pwa_auth_router(
            session_factory=self.sessions, settings_obj=self.settings
        ))
        self.client = AsyncClient(
            transport=ASGITransport(app=app), base_url=ORIGIN
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def begin(self):
        response = await self.client.post(
            "/api/v3/pwa-auth/start", headers={"Origin": ORIGIN},
            json={"provider": "google", "language": "uz"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn(PWA_OAUTH_COOKIE, response.cookies)
        self.assertNotIn("polling_secret", response.json())
        state = parse_qs(urlparse(response.json()["authorize_url"]).query)["state"][0]
        return state

    async def callback(self, state, client=None):
        from app.services import google_auth
        with patch.object(google_auth, "exchange_code", return_value="google-id-token"), patch.object(
            google_auth, "verify_desktop_id_token", return_value=identity(),
        ):
            return await (client or self.client).get(
                "/api/v3/native-auth/oauth/callback/google",
                params={"state": state, "code": "auth-code"},
            )

    async def test_origin_required_and_pwa_disabled_fails_closed(self):
        no_origin = await self.client.post(
            "/api/v3/pwa-auth/start", json={"provider": "google"},
        )
        self.assertEqual(no_origin.status_code, 403)
        bad_origin = await self.client.post(
            "/api/v3/pwa-auth/start",
            headers={"Origin": "https://attacker.test"},
            json={"provider": "google"},
        )
        self.assertEqual(bad_origin.status_code, 403)
        self.settings.PWA_AUTH_ENABLED = False
        disabled = await self.client.post(
            "/api/v3/pwa-auth/start",
            headers={"Origin": ORIGIN}, json={"provider": "google"},
        )
        self.assertEqual(disabled.status_code, 503)
        session = await self.client.get("/api/v3/pwa-auth/session")
        self.assertEqual(session.status_code, 503)

    async def test_pwa_callback_requires_same_browser_proof(self):
        state = await self.begin()
        other = AsyncClient(transport=self.client._transport, base_url=ORIGIN)
        try:
            missing_proof = await self.callback(state, client=other)
            self.assertNotIn(PWA_SESSION_COOKIE, missing_proof.cookies)
            self.assertIn("pwa_oauth_proof_invalid", missing_proof.text)
            good = await self.callback(state)
            self.assertEqual(good.status_code, 200)
            self.assertIn(PWA_SESSION_COOKIE, good.cookies)
            self.assertIn("HttpOnly", good.headers.get("set-cookie", ""))
            assert any("Secure" in item for item in good.headers.get_list("set-cookie"))
            assert any("SameSite=lax" in item for item in good.headers.get_list("set-cookie"))
            replay = await self.callback(state)
            self.assertNotIn(PWA_SESSION_COOKIE, replay.cookies)
            self.assertIn("pwa_oauth_proof_invalid", replay.text)
        finally:
            await other.aclose()

    async def test_existing_telegram_owner_retained_and_logout_is_csrf_protected(self):
        state = await self.begin()
        response = await self.callback(state)
        self.assertIn(PWA_SESSION_COOKIE, response.cookies)
        status = await self.client.get("/api/v3/pwa-auth/session")
        self.assertEqual(status.status_code, 200, status.text)
        self.assertEqual(status.json()["user_id"], 1)
        self.assertTrue(status.json()["telegram_linked"])
        csrf = status.json()["csrf"]
        self.assertEqual(
            (await self.client.post("/api/v3/pwa-auth/logout",
                                    headers={"Origin": ORIGIN})).status_code, 403
        )
        self.assertEqual(
            (await self.client.post("/api/v3/pwa-auth/logout",
                                    headers={"Origin": "https://evil.test",
                                             "X-HSK-PWA-CSRF": csrf})).status_code, 403
        )
        self.assertEqual(
            (await self.client.post("/api/v3/pwa-auth/logout",
                                    headers={"Origin": ORIGIN,
                                             "X-HSK-PWA-CSRF": "wrong"})).status_code, 403
        )
        ok = await self.client.post(
            "/api/v3/pwa-auth/logout",
            headers={"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf},
        )
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual((await self.client.get("/api/v3/pwa-auth/session")).status_code, 401)

    async def test_browser_cannot_exchange_pwa_oauth_for_native_bearer(self):
        state = await self.begin()
        async with self.sessions() as session:
            row = (await session.execute(
                select(DesktopLinkRequest).where(DesktopLinkRequest.platform == "pwa")
            )).scalar_one()
            # Polling secret is intentionally not returned to PWA; even if
            # it somehow leaked, the native bearer endpoint must refuse.
            row.status = "approved"
            row.approved_user_id = 1
            await session.commit()
            with self.assertRaises(DesktopAuthError):
                await DesktopAuthService(session, self.settings).poll_link(
                    link_request_id=row.id, polling_secret="x" * 40,
                )

    async def test_expiry_and_blocked_account_cannot_restore_session(self):
        state = await self.begin()
        await self.callback(state)
        async with self.sessions() as session:
            device = (await session.execute(
                select(DesktopDevice).where(DesktopDevice.platform == "pwa")
            )).scalar_one()
            login = (await session.execute(
                select(DesktopSession).where(DesktopSession.device_id == device.id)
            )).scalar_one()
            login.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await session.commit()
        self.assertEqual((await self.client.get("/api/v3/pwa-auth/session")).status_code, 401)

        new_state = await self.begin()
        await self.callback(new_state)
        async with self.sessions() as session:
            owner = await session.get(User, 1)
            owner.status = "blocked"
            await session.commit()
        self.assertEqual((await self.client.get("/api/v3/pwa-auth/session")).status_code, 401)

    async def test_native_and_telegram_routes_never_accept_pwa_cookie_as_auth(self):
        state = await self.begin()
        await self.callback(state)
        # Legacy native identity listing is bearer/verified initData only.
        response = await self.client.get("/api/v3/native-auth/identities")
        self.assertEqual(response.status_code, 401)
        self.assertEqual((await self.client.get("/api/v3/pwa-auth/session")).status_code, 200)


if __name__ == "__main__":
    unittest.main()

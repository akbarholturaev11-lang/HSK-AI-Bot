"""Transport-level contract for the Google / Apple sign-in endpoints.

The two properties worth protecting here:

1. No endpoint on this router ever returns a session token. Sign-in finishes on
   the existing ``link/status`` endpoint, so there stays exactly one
   token-minting path in the codebase.
2. Everything fails closed — unconfigured providers, tampered state, replayed
   state, oversized bodies and missing bearer tokens all refuse rather than
   guess.
"""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.native_oauth import create_native_oauth_router
from app.db.base import Base
from app.db.models.desktop import DesktopLinkRequest
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.identity_link_service import IdentityLinkService
from app.services.native_oauth_service import NativeOAuthService
from app.services.oidc_verifier import OidcVerificationError, VerifiedIdentity


SECRET = "native-oauth-test-secret-" + "x" * 40
INSTALLATION_KEY = "k" * 48
BOT_TOKEN = "123456789:AAExampleBotTokenForInitDataSigning1234"


def _settings(**overrides):
    base = dict(
        DESKTOP_AUTH_SIGNING_SECRET=SECRET,
        DESKTOP_AUTH_LINK_TTL_SECONDS=600,
        DESKTOP_AUTH_ACCESS_TTL_SECONDS=900,
        DESKTOP_AUTH_REFRESH_TTL_DAYS=30,
        BOT_USERNAME="pomp_test_bot",
        BOT_TOKEN=BOT_TOKEN,
        GOOGLE_OAUTH_ENABLED=True,
        GOOGLE_ANDROID_WEB_CLIENT_ID="111-web.apps.googleusercontent.com",
        GOOGLE_DESKTOP_CLIENT_ID="222-desktop.apps.googleusercontent.com",
        GOOGLE_DESKTOP_CLIENT_SECRET="desktop-secret",
        APPLE_OAUTH_ENABLED=False,
        APPLE_SERVICE_ID="",
        APPLE_TEAM_ID="",
        APPLE_KEY_ID="",
        APPLE_PRIVATE_KEY="",
        OAUTH_REDIRECT_BASE_URL="https://api.example.test",
        OAUTH_ID_TOKEN_MAX_AGE_SECONDS=300,
        OAUTH_HTTP_TIMEOUT_SECONDS=8.0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


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


def _verified(subject="sub-alice", provider="google", name="Alice"):
    return VerifiedIdentity(
        provider=provider,
        subject=subject,
        email="alice@example.com",
        email_verified=True,
        display_name=name,
        audience="111-web.apps.googleusercontent.com",
    )


class _Base(unittest.IsolatedAsyncioTestCase):
    settings_overrides: dict = {}

    async def asyncSetUp(self):
        self.settings = _settings(**self.settings_overrides)
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all([_user(1, 1001, "Alice"), _user(2, 1002, "Bob")])
            await session.commit()

        app = FastAPI()
        app.include_router(
            create_native_oauth_router(
                session_factory=self.sessions, settings_obj=self.settings
            )
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=app), base_url="http://oauth.test"
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    def _start_body(self, **overrides):
        body = {
            "platform": "android",
            "app_version": "1.5.3",
            "installation_key": INSTALLATION_KEY,
            "provider": "google",
            "mode": "native_id_token",
        }
        body.update(overrides)
        return body

    async def _bearer(self, telegram_id=1001):
        """Mint a real session the way the existing link flow does.

        Each account gets its own installation key: one device may only ever be
        bound to one user, so sharing a key here would (correctly) trip
        ``desktop_device_bound_to_other_user``.
        """

        async with self.sessions() as session:
            service = DesktopAuthService(session, self.settings)
            started = await service.start_link(
                platform="android",
                app_version="1.5.3",
                installation_key=f"dev{telegram_id}".ljust(48, "b"),
            )
            await service.approve_link(
                display_code=started["display_code"], telegram_id=telegram_id
            )
            linked = await service.poll_link(
                link_request_id=started["link_request_id"],
                polling_secret=started["polling_secret"],
            )
        return {"Authorization": f"Bearer {linked['access_token']}"}


class ProviderAvailabilityTests(_Base):
    async def test_configured_provider_is_offered(self):
        response = await self.client.get("/api/v3/native-auth/providers")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["providers"], ["google"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    async def test_apple_is_hidden_while_unconfigured(self):
        response = await self.client.get("/api/v3/native-auth/providers")
        self.assertNotIn("apple", response.json()["providers"])


class UnconfiguredProviderTests(_Base):
    settings_overrides = {"GOOGLE_OAUTH_ENABLED": False}

    async def test_provider_list_is_empty(self):
        response = await self.client.get("/api/v3/native-auth/providers")
        self.assertEqual(response.json()["providers"], [])

    async def test_start_fails_closed_with_503(self):
        response = await self.client.post(
            "/api/v3/native-auth/oauth/start", json=self._start_body()
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"], "oauth_provider_unconfigured")
        self.assertEqual(response.headers["Cache-Control"], "no-store")


class OAuthStartTests(_Base):
    async def test_native_mode_returns_a_nonce_and_no_authorize_url(self):
        response = await self.client.post(
            "/api/v3/native-auth/oauth/start", json=self._start_body()
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "pending")
        self.assertIn("nonce", payload)
        self.assertNotIn("authorize_url", payload)
        # Never a Telegram artefact, and never a token.
        for leaked in ("display_code", "bot_deep_link", "access_token", "refresh_token"):
            self.assertNotIn(leaked, payload)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    async def test_browser_mode_returns_a_pinned_authorize_url(self):
        response = await self.client.post(
            "/api/v3/native-auth/oauth/start",
            json=self._start_body(platform="macos", mode="browser_redirect"),
        )
        self.assertEqual(response.status_code, 200)
        url = response.json()["authorize_url"]
        self.assertTrue(url.startswith("https://accounts.google.com/o/oauth2/v2/auth?"))
        self.assertIn("code_challenge_method=S256", url)
        self.assertIn("222-desktop.apps.googleusercontent.com", url)
        # The desktop client secret must never reach a URL.
        self.assertNotIn("desktop-secret", url)

    async def test_credential_manager_mode_is_android_and_google_only(self):
        for label, body in (
            ("desktop platform", self._start_body(platform="macos")),
            ("apple provider", self._start_body(provider="apple")),
        ):
            with self.subTest(case=label):
                response = await self.client.post(
                    "/api/v3/native-auth/oauth/start", json=body
                )
                self.assertEqual(response.status_code, 422)
                self.assertIn(
                    response.json()["error"],
                    {"oauth_mode_unsupported", "oauth_provider_unsupported"},
                )

    async def test_unknown_provider_is_refused_by_the_schema(self):
        response = await self.client.post(
            "/api/v3/native-auth/oauth/start",
            json=self._start_body(provider="facebook"),
        )
        self.assertEqual(response.status_code, 422)

    async def test_start_row_is_a_provider_row_not_a_telegram_one(self):
        await self.client.post(
            "/api/v3/native-auth/oauth/start", json=self._start_body()
        )
        async with self.sessions() as session:
            row = (
                await session.execute(select(DesktopLinkRequest))
            ).scalars().one()
        self.assertEqual(row.flow, "google")
        self.assertEqual(row.intent, "signin")
        self.assertIsNone(row.bind_user_id)


class OAuthAssertTests(_Base):
    async def _start(self):
        response = await self.client.post(
            "/api/v3/native-auth/oauth/start", json=self._start_body()
        )
        return response.json()

    async def test_unknown_identity_is_told_to_use_telegram_first(self):
        started = await self._start()
        with patch(
            "app.services.google_auth.verify_android_id_token",
            return_value=_verified(),
        ):
            response = await self.client.post(
                "/api/v3/native-auth/oauth/assert",
                json={
                    "link_request_id": started["link_request_id"],
                    "polling_secret": started["polling_secret"],
                    "provider": "google",
                    "id_token": "t" * 64,
                },
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["error"], "oauth_telegram_account_required"
        )

    async def test_linked_identity_approves_the_row_without_returning_tokens(self):
        async with self.sessions() as session:
            await IdentityLinkService(session, self.settings).link_to_user(
                _verified(), user_id=1
            )
            await session.commit()

        started = await self._start()
        with patch(
            "app.services.google_auth.verify_android_id_token",
            return_value=_verified(),
        ):
            response = await self.client.post(
                "/api/v3/native-auth/oauth/assert",
                json={
                    "link_request_id": started["link_request_id"],
                    "polling_secret": started["polling_secret"],
                    "provider": "google",
                    "id_token": "t" * 64,
                },
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "approved")
        self.assertNotIn("access_token", payload)
        self.assertNotIn("refresh_token", payload)

        # The row is now exchangeable through the EXISTING link/status path.
        async with self.sessions() as session:
            linked = await DesktopAuthService(session, self.settings).poll_link(
                link_request_id=started["link_request_id"],
                polling_secret=started["polling_secret"],
            )
        self.assertEqual(linked["status"], "linked")
        self.assertIn("access_token", linked)

    async def test_wrong_polling_secret_is_refused(self):
        started = await self._start()
        response = await self.client.post(
            "/api/v3/native-auth/oauth/assert",
            json={
                "link_request_id": started["link_request_id"],
                "polling_secret": "z" * 48,
                "provider": "google",
                "id_token": "t" * 64,
            },
        )
        self.assertEqual(response.status_code, 401)

    async def test_a_failed_assertion_burns_the_row(self):
        """Single-shot verification is what caps ID token brute force."""

        started = await self._start()
        with patch(
            "app.services.google_auth.verify_android_id_token",
            side_effect=OidcVerificationError("oidc_token_invalid"),
        ):
            first = await self.client.post(
                "/api/v3/native-auth/oauth/assert",
                json={
                    "link_request_id": started["link_request_id"],
                    "polling_secret": started["polling_secret"],
                    "provider": "google",
                    "id_token": "t" * 64,
                },
            )
        self.assertEqual(first.status_code, 401)

        with patch(
            "app.services.google_auth.verify_android_id_token",
            return_value=_verified(),
        ):
            second = await self.client.post(
                "/api/v3/native-auth/oauth/assert",
                json={
                    "link_request_id": started["link_request_id"],
                    "polling_secret": started["polling_secret"],
                    "provider": "google",
                    "id_token": "t" * 64,
                },
            )
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["error"], "desktop_link_consumed")

    async def test_oversized_body_is_refused(self):
        started = await self._start()
        response = await self.client.post(
            "/api/v3/native-auth/oauth/assert",
            json={
                "link_request_id": started["link_request_id"],
                "polling_secret": started["polling_secret"],
                "provider": "google",
                "id_token": "t" * 20000,
            },
        )
        self.assertEqual(response.status_code, 413)


class OAuthCallbackTests(_Base):
    async def _browser_start(self):
        response = await self.client.post(
            "/api/v3/native-auth/oauth/start",
            json=self._start_body(platform="macos", mode="browser_redirect"),
        )
        payload = response.json()
        async with self.sessions() as session:
            state = NativeOAuthService(session, self.settings).state(
                payload["link_request_id"]
            )
        return payload, state

    async def test_callback_page_carries_no_token_or_user_data(self):
        async with self.sessions() as session:
            await IdentityLinkService(session, self.settings).link_to_user(
                _verified(), user_id=1
            )
            await session.commit()
        payload, state = await self._browser_start()

        with patch(
            "app.services.google_auth.exchange_code", return_value="id-token"
        ), patch(
            "app.services.google_auth.verify_desktop_id_token",
            return_value=_verified(),
        ):
            response = await self.client.get(
                "/api/v3/native-auth/oauth/callback/google",
                params={"state": state, "code": "auth-code"},
            )
        self.assertEqual(response.status_code, 200)
        body = response.text
        for leaked in ("alice@example.com", "Alice", "id-token", "auth-code", state):
            self.assertNotIn(leaked, body)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")

    async def test_tampered_state_is_refused(self):
        payload, state = await self._browser_start()
        link_id, _, mac = state.partition(".")
        forged = f"{link_id}.{'a' * len(mac)}"
        with patch("app.services.google_auth.exchange_code") as exchange:
            response = await self.client.get(
                "/api/v3/native-auth/oauth/callback/google",
                params={"state": forged, "code": "auth-code"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("oauth_state_invalid", response.text)
        exchange.assert_not_called()

    async def test_state_from_another_request_cannot_be_replayed(self):
        async with self.sessions() as session:
            await IdentityLinkService(session, self.settings).link_to_user(
                _verified(), user_id=1
            )
            await session.commit()
        payload, state = await self._browser_start()

        with patch(
            "app.services.google_auth.exchange_code", return_value="id-token"
        ), patch(
            "app.services.google_auth.verify_desktop_id_token",
            return_value=_verified(),
        ):
            first = await self.client.get(
                "/api/v3/native-auth/oauth/callback/google",
                params={"state": state, "code": "auth-code"},
            )
            self.assertIn("ok", first.text)
            second = await self.client.get(
                "/api/v3/native-auth/oauth/callback/google",
                params={"state": state, "code": "auth-code"},
            )
        self.assertIn("desktop_link_consumed", second.text)

    async def test_provider_cancellation_is_shown_without_touching_the_row(self):
        payload, state = await self._browser_start()
        response = await self.client.get(
            "/api/v3/native-auth/oauth/callback/google",
            params={"state": state, "error": "access_denied"},
        )
        self.assertIn("oauth_cancelled", response.text)


class IdentityManagementTests(_Base):
    async def test_identity_routes_require_a_bearer_token(self):
        for method, path, body in (
            ("get", "/api/v3/native-auth/identities", None),
            (
                "post",
                "/api/v3/native-auth/identities/link/start",
                self._start_body(),
            ),
            (
                "post",
                "/api/v3/native-auth/identities/unlink",
                {"identity_id": "x"},
            ),
        ):
            with self.subTest(path=path):
                call = getattr(self.client, method)
                response = await (call(path) if body is None else call(path, json=body))
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.headers["Cache-Control"], "no-store")

    async def test_listing_reports_telegram_and_masks_the_email(self):
        async with self.sessions() as session:
            await IdentityLinkService(session, self.settings).link_to_user(
                _verified(), user_id=1
            )
            await session.commit()
        headers = await self._bearer()

        response = await self.client.get(
            "/api/v3/native-auth/identities", headers=headers
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["telegram_linked"])
        self.assertEqual(payload["identities"][0]["provider"], "google")
        self.assertEqual(
            payload["identities"][0]["email_masked"], "a***e@example.com"
        )
        self.assertNotIn("alice@example.com", response.text)
        self.assertNotIn("subject_hash", response.text)

    async def test_link_start_creates_a_bound_link_row(self):
        headers = await self._bearer()
        response = await self.client.post(
            "/api/v3/native-auth/identities/link/start",
            json=self._start_body(),
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        async with self.sessions() as session:
            row = (
                await session.execute(
                    select(DesktopLinkRequest).where(
                        DesktopLinkRequest.intent == "link"
                    )
                )
            ).scalars().one()
        self.assertEqual(row.intent, "link")
        self.assertEqual(row.flow, "google")
        self.assertEqual(row.bind_user_id, 1)

    async def test_a_link_row_can_never_be_exchanged_for_a_session(self):
        """The guard that keeps 'connect Google' from becoming 'sign in'."""

        headers = await self._bearer()
        started = (
            await self.client.post(
                "/api/v3/native-auth/identities/link/start",
                json=self._start_body(),
                headers=headers,
            )
        ).json()

        with patch(
            "app.services.google_auth.verify_android_id_token",
            return_value=_verified(),
        ):
            asserted = await self.client.post(
                "/api/v3/native-auth/oauth/assert",
                json={
                    "link_request_id": started["link_request_id"],
                    "polling_secret": started["polling_secret"],
                    "provider": "google",
                    "id_token": "t" * 64,
                },
            )
        self.assertEqual(asserted.json()["status"], "linked")

        from app.services.desktop_auth_service import DesktopAuthError

        async with self.sessions() as session:
            with self.assertRaises(DesktopAuthError) as blocked:
                await DesktopAuthService(session, self.settings).poll_link(
                    link_request_id=started["link_request_id"],
                    polling_secret=started["polling_secret"],
                )
        self.assertEqual(blocked.exception.code, "desktop_link_invalid")

    async def test_link_status_never_returns_tokens(self):
        headers = await self._bearer()
        started = (
            await self.client.post(
                "/api/v3/native-auth/identities/link/start",
                json=self._start_body(),
                headers=headers,
            )
        ).json()
        response = await self.client.post(
            "/api/v3/native-auth/identities/link/status",
            json={
                "link_request_id": started["link_request_id"],
                "polling_secret": started["polling_secret"],
            },
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "pending")
        self.assertNotIn("access_token", response.text)
        self.assertNotIn("refresh_token", response.text)

    async def test_another_users_link_row_is_not_readable(self):
        headers_alice = await self._bearer(telegram_id=1001)
        started = (
            await self.client.post(
                "/api/v3/native-auth/identities/link/start",
                json=self._start_body(),
                headers=headers_alice,
            )
        ).json()

        headers_bob = await self._bearer(telegram_id=1002)
        response = await self.client.post(
            "/api/v3/native-auth/identities/link/status",
            json={
                "link_request_id": started["link_request_id"],
                "polling_secret": started["polling_secret"],
            },
            headers=headers_bob,
        )
        self.assertEqual(response.status_code, 401)

    async def test_unlink_removes_the_identity_and_reports_revocations(self):
        async with self.sessions() as session:
            identity = await IdentityLinkService(
                session, self.settings
            ).link_to_user(_verified(), user_id=1)
            await session.commit()
            identity_id = identity.id
        headers = await self._bearer()

        response = await self.client.post(
            "/api/v3/native-auth/identities/unlink",
            json={"identity_id": identity_id},
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("sessions_revoked", response.json())
        async with self.sessions() as session:
            self.assertIsNone(
                (await session.execute(select(UserIdentity))).scalars().first()
            )

    async def test_unlinking_another_users_identity_reports_not_found(self):
        async with self.sessions() as session:
            identity = await IdentityLinkService(
                session, self.settings
            ).link_to_user(_verified(), user_id=2)
            await session.commit()
            identity_id = identity.id
        headers = await self._bearer(telegram_id=1001)

        response = await self.client.post(
            "/api/v3/native-auth/identities/unlink",
            json={"identity_id": identity_id},
            headers=headers,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "oauth_identity_not_found")


class MiniAppLinkTests(_Base):
    """The Telegram Mini App attaches a provider with initData, not a token.

    It is a client, not a new way in: a Mini App row can only ever be
    intent="link", so it can never be exchanged for a session.
    """

    def _init_data(self, telegram_id=1001, *, age_seconds=0):
        import hashlib
        import hmac
        import json
        import time
        from urllib.parse import urlencode

        params = {
            "auth_date": str(int(time.time()) - age_seconds),
            "user": json.dumps({"id": telegram_id, "first_name": "Alice"}),
        }
        check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
        secret = hmac.new(
            b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256
        ).digest()
        params["hash"] = hmac.new(
            secret, check.encode(), hashlib.sha256
        ).hexdigest()
        return urlencode(params)

    def _miniapp_body(self, **overrides):
        body = {
            "platform": "miniapp",
            "app_version": "1.0.0",
            "provider": "google",
            "mode": "browser_redirect",
        }
        body.update(overrides)
        return body

    async def test_miniapp_can_list_identities_with_init_data(self):
        async with self.sessions() as session:
            await IdentityLinkService(session, self.settings).link_to_user(
                _verified(), user_id=1
            )
            await session.commit()

        response = await self.client.get(
            "/api/v3/native-auth/identities",
            headers={"X-Telegram-Init-Data": self._init_data()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["identities"][0]["provider"], "google")

    async def test_miniapp_link_start_needs_no_installation_key(self):
        response = await self.client.post(
            "/api/v3/native-auth/identities/link/start",
            json=self._miniapp_body(),
            headers={"X-Telegram-Init-Data": self._init_data()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.json()["authorize_url"].startswith("https://accounts.google.com/")
        )
        async with self.sessions() as session:
            row = (
                await session.execute(
                    select(DesktopLinkRequest).where(
                        DesktopLinkRequest.platform == "miniapp"
                    )
                )
            ).scalars().one()
        self.assertEqual(row.intent, "link")
        self.assertEqual(row.bind_user_id, 1)

    async def test_a_miniapp_row_can_never_become_a_session(self):
        started = (
            await self.client.post(
                "/api/v3/native-auth/identities/link/start",
                json=self._miniapp_body(),
                headers={"X-Telegram-Init-Data": self._init_data()},
            )
        ).json()
        async with self.sessions() as session:
            with self.assertRaises(DesktopAuthError) as blocked:
                await DesktopAuthService(session, self.settings).poll_link(
                    link_request_id=started["link_request_id"],
                    polling_secret=started["polling_secret"],
                )
        self.assertEqual(blocked.exception.code, "desktop_link_invalid")

    async def test_miniapp_cannot_be_used_to_sign_in(self):
        """The anonymous sign-in endpoint must refuse the platform outright."""

        response = await self.client.post(
            "/api/v3/native-auth/oauth/start",
            json={
                "platform": "miniapp",
                "app_version": "1.0.0",
                "installation_key": INSTALLATION_KEY,
                "provider": "google",
                "mode": "browser_redirect",
            },
        )
        self.assertEqual(response.status_code, 422)

    async def test_stale_init_data_is_refused(self):
        response = await self.client.get(
            "/api/v3/native-auth/identities",
            headers={
                "X-Telegram-Init-Data": self._init_data(age_seconds=90_000)
            },
        )
        self.assertEqual(response.status_code, 401)

    async def test_forged_init_data_is_refused(self):
        response = await self.client.get(
            "/api/v3/native-auth/identities",
            headers={"X-Telegram-Init-Data": "user=%7B%22id%22%3A1001%7D&hash=deadbeef"},
        )
        self.assertEqual(response.status_code, 401)

    async def test_native_platform_still_requires_an_installation_key(self):
        response = await self.client.post(
            "/api/v3/native-auth/identities/link/start",
            json={
                "platform": "android",
                "app_version": "1.5.3",
                "provider": "google",
                "mode": "browser_redirect",
            },
            headers={"X-Telegram-Init-Data": self._init_data()},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()

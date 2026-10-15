"""Real DB/HTTP deletion contracts: proof, confirmation, retention, no auth side effects."""
import hashlib
import hmac
import json
import time
import unittest
from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlencode, urlsplit
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import MetaData, event, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.account_deletion import create_account_deletion_router
from app.api.native_oauth import create_native_oauth_router
from app.db.base import Base
from app.db.models.account_deletion import AccountDeletionRequest
from app.db.models.desktop import DesktopDevice, DesktopLinkRequest, DesktopSession
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.services.account_deletion_service import AccountDeletionError, AccountDeletionService, BROWSER_COOKIE, now
from app.services.blocked_user_guard import BlockedUserApiMiddleware
from app.services.desktop_auth_service import DesktopAuthService
from app.services.oidc_verifier import OidcVerificationError, VerifiedIdentity
from app.repositories.user_repo import UserRepository


class AccountDeletionApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.settings = SimpleNamespace(
            DESKTOP_AUTH_SIGNING_SECRET="deletion-test-secret-" + "x" * 40,
            BOT_USERNAME="test_bot", BOT_TOKEN="123456789:test-bot-token",
            GOOGLE_OAUTH_ENABLED=True, GOOGLE_DESKTOP_CLIENT_ID="browser-client",
            GOOGLE_DESKTOP_CLIENT_SECRET="test-secret", GOOGLE_ANDROID_WEB_CLIENT_ID="android-client",
            APPLE_OAUTH_ENABLED=True, APPLE_SERVICE_ID="apple-service", APPLE_TEAM_ID="team",
            APPLE_KEY_ID="key", APPLE_PRIVATE_KEY="test-key",
            OAUTH_REDIRECT_BASE_URL="https://deletion.test", admin_id_list=[],
        )
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        @event.listens_for(self.engine.sync_engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
        schema = MetaData()
        for table in Base.metadata.sorted_tables:
            table.to_metadata(schema)
        # Future provider-only schema is isolated; no login/account-creation
        # migration is needed or silently introduced by this deletion patch.
        for table in ("users", "desktop_devices"):
            schema.tables[table].c.telegram_id.nullable = True
        async with self.engine.begin() as connection:
            await connection.run_sync(schema.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all([User(id=1, telegram_id=None, full_name="Provider learner", status="free"),
                             User(id=2, telegram_id=1002, full_name="Telegram learner", status="blocked")])
            await session.flush()
            auth = DesktopAuthService(session, self.settings)
            for provider in ("google", "apple"):
                session.add(UserIdentity(id=provider, user_id=1, provider=provider,
                    subject_hash=auth.identity_subject_hash(provider, "learner-sub"),
                    email_display="learner@example.test", email_verified=True))
            for uid in (1, 2):
                session.add(DesktopDevice(id=f"device-{uid}", user_id=uid,
                    telegram_id=None if uid == 1 else 1002, installation_key_hash=f"key-{uid}",
                    platform="android", app_version="1.0"))
            await session.flush()
            for uid in (1, 2):
                session.add(DesktopSession(id=f"session-{uid}", device_id=f"device-{uid}",
                    refresh_token_hash=f"refresh-{uid}", expires_at=now() + timedelta(days=30)))
            await session.commit()
        self.notifier = AsyncMock()
        app = FastAPI()
        app.include_router(create_account_deletion_router(
            session_factory=self.sessions, settings_obj=self.settings, notifier=self.notifier))
        app.include_router(create_native_oauth_router(session_factory=self.sessions, settings_obj=self.settings))
        app.add_middleware(BlockedUserApiMiddleware, session_maker=self.sessions,
                           bot_token=self.settings.BOT_TOKEN)
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="https://deletion.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _bearer(self, uid=1):
        async with self.sessions() as session:
            auth = DesktopAuthService(session, self.settings)
            token, _ = auth._access_token(desktop_session=await session.get(DesktopSession, f"session-{uid}"),
                                         device=await session.get(DesktopDevice, f"device-{uid}"))
        return {"Authorization": "Bearer " + token}

    def _init_data(self, *, age=0):
        params = {"auth_date": str(int(time.time()) - age), "user": json.dumps({"id": 1002})}
        check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
        key = hmac.new(b"WebAppData", self.settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
        params["hash"] = hmac.new(key, check.encode(), hashlib.sha256).hexdigest()
        return {"X-Telegram-Init-Data": urlencode(params)}

    @staticmethod
    def _proof(result, **extra):
        return {"request_id": result["request_id"], "secret": result["secret"], **extra}

    async def _start(self, provider="google"):
        response = await self.client.post("/api/account-deletion/start", json={"provider": provider})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertIn("SameSite=none", response.headers["set-cookie"])
        self.assertIn("Secure", response.headers["set-cookie"])
        return response.json()

    async def _oauth_verify(self, result, provider="google", subject="learner-sub", **kwargs):
        query = parse_qs(urlsplit(result["authorize_url"]).query)
        identity = VerifiedIdentity(provider=provider, subject=subject,
            email="learner@example.test", email_verified=True, display_name="Learner", audience="browser-client")
        adapter = "google_auth" if provider == "google" else "apple_auth"
        verifier = "verify_desktop_id_token" if provider == "google" else "verify_id_token_for_service"
        with patch(f"app.services.account_deletion_service.{adapter}.exchange_code", AsyncMock(return_value="id-token")), \
             patch(f"app.services.account_deletion_service.{adapter}.{verifier}", AsyncMock(return_value=identity)) as verify:
            if provider == "google":
                response = await self.client.get("/api/v3/native-auth/oauth/callback/google",
                    params={"state": query["state"][0], "code": "code", **kwargs})
            else:
                response = await self.client.post("/api/v3/native-auth/oauth/callback/apple",
                    data={"state": query["state"][0], "code": "code", **kwargs})
        return response, verify

    async def test_provider_only_native_session_confirms_without_telegram_and_no_access_changes(self):
        prepared = await self.client.post("/api/account-deletion/prepare", json={}, headers=await self._bearer())
        self.assertEqual(prepared.status_code, 200, prepared.text)
        self.assertEqual(prepared.json()["status"], "verified")
        result = await self.client.post("/api/account-deletion/confirm", json=self._proof(prepared.json(), confirmation="DELETE"))
        self.assertEqual(result.json()["status"], "submitted")
        self.notifier.assert_awaited_once()
        async with self.sessions() as session:
            user = await session.get(User, 1)
            self.assertIsNone(user.telegram_id)
            self.assertEqual(user.status, "free")
            self.assertEqual(await session.scalar(select(func.count()).select_from(DesktopSession)), 2)
            self.assertEqual(await session.scalar(select(func.count()).select_from(UserIdentity)), 2)
        retry = await self.client.post("/api/account-deletion/confirm", json=self._proof(prepared.json(), confirmation="DELETE"))
        self.assertEqual(result.json(), retry.json())
        self.notifier.assert_awaited_once()

    async def test_public_google_and_apple_proof_do_not_create_login_or_change_identities(self):
        for provider in ("google", "apple"):
            with self.subTest(provider=provider):
                started = await self._start(provider)
                query = parse_qs(urlsplit(started["authorize_url"]).query)
                self.assertTrue(query["state"][0].startswith("delete."))
                self.assertEqual(query["redirect_uri"][0], f"https://deletion.test/api/v3/native-auth/oauth/callback/{provider}")
                response, verify = await self._oauth_verify(started, provider)
                self.assertIn("No deletion request has been submitted yet", response.text)
                self.assertEqual(verify.await_args.kwargs["nonce"], query["nonce"][0])
                self.assertNotIn(started["secret"], response.text)
                status = await self.client.post("/api/account-deletion/status", json=self._proof(started))
                self.assertEqual(status.json()["status"], "verified")
                receipt = await self.client.post("/api/account-deletion/confirm", json=self._proof(started, confirmation="DELETE"))
                self.assertEqual(receipt.json()["status"], "submitted")
        async with self.sessions() as session:
            self.assertEqual(await session.scalar(select(func.count()).select_from(DesktopLinkRequest)), 0)
            self.assertEqual(await session.scalar(select(func.count()).select_from(DesktopSession)), 2)
            self.assertEqual(await session.scalar(select(func.count()).select_from(UserIdentity)), 2)
            self.assertEqual(await session.scalar(select(func.count()).select_from(AccountDeletionRequest).where(
                AccountDeletionRequest.active_user_id == 1)), 1)

    async def test_email_match_cannot_request_another_accounts_deletion(self):
        started = await self._start()
        response, _ = await self._oauth_verify(started, subject="different-sub-same-email")
        self.assertIn("deletion_account_not_found", response.text)
        confirm = await self.client.post("/api/account-deletion/confirm", json=self._proof(started, confirmation="DELETE"))
        self.assertEqual(confirm.status_code, 409)
        self.notifier.assert_not_awaited()

    async def test_wrong_browser_cannot_complete_oauth_or_poll_or_confirm(self):
        started = await self._start()
        original = self.client.cookies.get(BROWSER_COOKIE)
        self.client.cookies.clear()
        response, verify = await self._oauth_verify(started)
        self.assertIn("deletion_browser_mismatch", response.text)
        verify.assert_not_awaited()
        for route in ("status", "confirm"):
            payload = self._proof(started, **({"confirmation": "DELETE"} if route == "confirm" else {}))
            response = await self.client.post("/api/account-deletion/" + route, json=payload)
            self.assertEqual(response.status_code, 403)
        self.client.cookies.set(BROWSER_COOKIE, original)
        response, verify = await self._oauth_verify(started)
        verify.assert_awaited_once()
        self.assertIn("Account ownership verified", response.text)

    async def test_pending_wrong_secret_missing_confirmation_and_foreign_target_are_rejected(self):
        started = await self._start()
        cases = [self._proof(started, confirmation="DELETE"),
                 self._proof(started, secret="x" * 43, confirmation="DELETE"),
                 self._proof(started), self._proof(started, confirmation="DELETE", user_id=1)]
        for payload, status in zip(cases, (409, 403, 422, 422)):
            response = await self.client.post("/api/account-deletion/confirm", json=payload)
            self.assertEqual(response.status_code, status, response.text)
        self.notifier.assert_not_awaited()

    async def test_expired_tampered_state_and_provider_replay_fail_closed(self):
        started = await self._start()
        query = parse_qs(urlsplit(started["authorize_url"]).query)
        response = await self.client.get("/api/v3/native-auth/oauth/callback/google",
            params={"state": query["state"][0] + "x", "code": "code"})
        self.assertIn("deletion_invalid", response.text)
        await self._oauth_verify(started)
        replay, verify = await self._oauth_verify(started)
        self.assertIn("deletion_invalid", replay.text)
        verify.assert_not_awaited()
        async with self.sessions() as session:
            row = await session.get(AccountDeletionRequest, started["request_id"])
            row.expires_at = now() - timedelta(seconds=1)
            await session.commit()
        response = await self.client.post("/api/account-deletion/confirm", json=self._proof(started, confirmation="DELETE"))
        self.assertEqual(response.status_code, 410)

    async def test_telegram_web_verification_and_blocked_signed_miniapp_can_submit(self):
        started = await self._start("telegram")
        self.assertIn("start=delete_", started["bot_deep_link"])
        self.assertNotIn(started["secret"], started["bot_deep_link"])
        async with self.sessions() as session:
            await AccountDeletionService(session, self.settings).verify_telegram(request_id=started["request_id"], telegram_id=1002)
        result = await self.client.post("/api/account-deletion/confirm", json=self._proof(started, confirmation="DELETE"))
        self.assertEqual(result.json()["status"], "submitted")
        prepared = await self.client.post("/api/account-deletion/prepare", json={}, headers=self._init_data())
        self.assertEqual(prepared.status_code, 200)
        result2 = await self.client.post("/api/account-deletion/confirm", json=self._proof(prepared.json(), confirmation="DELETE"))
        self.assertEqual(result.json()["due_at"], result2.json()["due_at"])
        async with self.sessions() as session:
            self.assertEqual((await session.get(User, 2)).status, "blocked")

    async def test_stale_tampered_revoked_and_missing_native_auth_are_rejected(self):
        for headers in ({}, self._init_data(age=90000), {"X-Telegram-Init-Data": "user=%7B%22id%22%3A1002%7D"}):
            response = await self.client.post("/api/account-deletion/prepare", json={}, headers=headers)
            self.assertEqual(response.status_code, 401)
        bearer = await self._bearer()
        async with self.sessions() as session:
            (await session.get(DesktopSession, "session-1")).revoked_at = now()
            await session.commit()
        response = await self.client.post("/api/account-deletion/prepare", json={}, headers=bearer)
        self.assertEqual(response.status_code, 401)

    async def test_cross_origin_oversized_extra_fields_and_unconfigured_provider_rejected(self):
        response = await self.client.post("/api/account-deletion/start", json={"provider": "google"}, headers={"Origin": "https://attacker.test"})
        self.assertEqual(response.status_code, 403)
        response = await self.client.post("/api/account-deletion/start", content="x" * 4096, headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 413)
        response = await self.client.post("/api/account-deletion/start", json={"provider": "google", "user_id": 2})
        self.assertEqual(response.status_code, 422)
        self.settings.APPLE_OAUTH_ENABLED = False
        self.assertNotIn("apple", (await self.client.get("/api/account-deletion/providers")).json()["providers"])
        response = await self.client.post("/api/account-deletion/start", json={"provider": "apple"})
        self.assertEqual(response.status_code, 503)

    async def test_tls_proxy_uses_configured_origin_and_secure_browser_cookie(self):
        async with AsyncClient(transport=self.client._transport, base_url="http://deletion.test") as proxy_client:
            response = await proxy_client.post("/api/account-deletion/start", json={"provider": "google"},
                headers={"Origin": "https://deletion.test"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Secure", response.headers["set-cookie"])
        self.assertIn("SameSite=none", response.headers["set-cookie"])
        self.assertIn("Max-Age=5184000", response.headers["set-cookie"])

    async def test_public_rate_limit_persists_and_secrets_are_only_hashes(self):
        for _ in range(12):
            started = await self._start("telegram")
        response = await self.client.post("/api/account-deletion/start", json={"provider": "telegram"})
        self.assertEqual(response.status_code, 429)
        async with self.sessions() as session:
            row = await session.get(AccountDeletionRequest, started["request_id"])
            self.assertNotEqual(row.secret_hash, started["secret"])
            self.assertNotEqual(row.browser_hash, self.client.cookies.get(BROWSER_COOKIE))

    async def test_operator_process_purges_provider_only_account_and_preserves_anonymous_receipt(self):
        prepared = (await self.client.post("/api/account-deletion/prepare", json={}, headers=await self._bearer())).json()
        await self.client.post("/api/account-deletion/confirm", json=self._proof(prepared, confirmation="DELETE"))
        async with self.sessions() as session:
            service = AccountDeletionService(session, self.settings)
            with self.assertRaises(AccountDeletionError):
                await service.process(request_id=prepared["request_id"], expected_user_id=2)
            await session.rollback()
            result = await service.process(request_id=prepared["request_id"], expected_user_id=1)
            self.assertEqual(result["status"], "completed")
            self.assertIsNone(await session.get(User, 1))
            self.assertIsNotNone(await session.get(User, 2))
            self.assertEqual(await session.scalar(select(func.count()).select_from(UserIdentity)), 0)
            self.assertIsNone(await session.get(DesktopSession, "session-1"))
            row = await session.get(AccountDeletionRequest, prepared["request_id"])
            self.assertIsNone(row.user_id)
            self.assertIsNone(row.active_user_id)
            self.assertEqual((await service.process(request_id=row.id, expected_user_id=1))["status"], "completed")
        status = await self.client.post("/api/account-deletion/status", json=self._proof(prepared))
        self.assertEqual(status.json()["status"], "completed")

    async def test_notification_failure_does_not_lose_saved_request_and_retention_keeps_overdue(self):
        self.notifier.side_effect = RuntimeError("notification failed")
        prepared = (await self.client.post("/api/account-deletion/prepare", json={}, headers=await self._bearer())).json()
        response = await self.client.post("/api/account-deletion/confirm", json=self._proof(prepared, confirmation="DELETE"))
        self.assertEqual(response.json()["status"], "submitted")
        async with self.sessions() as session:
            row = await session.get(AccountDeletionRequest, prepared["request_id"])
            row.created_at = now() - timedelta(days=90)
            row.due_at = now() - timedelta(days=60)
            await session.commit()
            await AccountDeletionService(session, self.settings).cleanup()
            self.assertIsNotNone(await session.get(AccountDeletionRequest, row.id))

    async def test_legacy_admin_purge_reconciles_receipt_and_completion_retention(self):
        prepared = (await self.client.post("/api/account-deletion/prepare", json={}, headers=await self._bearer())).json()
        await self.client.post("/api/account-deletion/confirm", json=self._proof(prepared, confirmation="DELETE"))
        async with self.sessions() as session:
            await UserRepository(session).delete_by_user_id(1)
            await session.commit()
            await AccountDeletionService(session, self.settings).cleanup()
            row = await session.get(AccountDeletionRequest, prepared["request_id"])
            self.assertEqual(row.status, "completed")
            row.created_at = now() - timedelta(days=90)
            await session.commit()
            await AccountDeletionService(session, self.settings).cleanup()
            self.assertIsNotNone(await session.get(AccountDeletionRequest, row.id))
            row.completed_at = now() - timedelta(days=31)
            request_id = row.id
            await session.commit()
            await AccountDeletionService(session, self.settings).cleanup()
            session.expire_all()
            self.assertIsNone(await session.get(AccountDeletionRequest, request_id))

"""Provider proofs cancel atomically and remain isolated by client and mode."""
import asyncio
import base64
import hashlib
import os
import re
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4
from urllib.parse import parse_qs, urlparse

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.models.desktop import DesktopDevice, DesktopLinkRequest, DesktopSession
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.services import google_auth
from app.services.desktop_auth_service import DesktopAuthError
from app.services.identity_link_service import IdentityLinkError
from app.services.native_oauth_service import NativeOAuthError, NativeOAuthService
from tests.native_postgres_deadlines import postgres_timeout
from tests import test_native_oauth_api as oauth_fixture
from tests.test_native_oauth_api import _Base, _verified, INSTALLATION_KEY
from tests.test_oidc_verifier import _Key, _Jwks, _claims


class _ProviderFixture(_Base):
    settings_overrides = {
        "APPLE_OAUTH_ENABLED": True, "APPLE_SERVICE_ID": "apple.service.test",
        "APPLE_TEAM_ID": "TESTTEAMID", "APPLE_KEY_ID": "TESTKEYID",
        "APPLE_PRIVATE_KEY": "fixture-key-not-used-by-mocked-provider",
    }

    async def _pending(self, provider="google", *, headers=None, platform="android"):
        headers = headers or await self._bearer()
        started = await self.client.post("/api/v3/native-auth/identities/link/start",
            headers=headers, json=self._start_body(provider=provider, mode="browser_redirect", platform=platform))
        self.assertEqual(started.status_code, 200, started.text)
        pending = started.json()
        async with self.sessions() as session:
            row = await session.get(DesktopLinkRequest, pending["link_request_id"])
            pending["origin_session_id"] = row.bind_session_id
            pending["state"] = NativeOAuthService(session, self.settings).state(row.id)
        return headers, pending

    async def _cancel(self, pending, headers):
        return await self.client.post("/api/v3/native-auth/identities/link/cancel",
            headers=headers, json={key: pending[key] for key in ("link_request_id", "polling_secret")})

    async def _callback(self, provider, state):
        path = "/api/v3/native-auth/oauth/callback/" + provider
        values = {"state": state, "code": "fixture-auth-code"}
        if provider == "apple":
            return await self.client.post(path, data=values)
        return await self.client.get(path, params=values)

    async def _error_callback(self, provider, state):
        path = "/api/v3/native-auth/oauth/callback/" + provider
        values = {"error": "access_denied"}
        if state is not None:
            values["state"] = state
        if provider == "apple":
            return await self.client.post(path, data=values)
        return await self.client.get(path, params=values)


class NativeReturnSettingTests(unittest.TestCase):
    def test_only_production_and_qa_schemes_are_accepted(self):
        from app.config import Settings
        for value in ("pomp-hsk-ai", "pomp-hsk-ai-qa", None, "", "http", "pomp-hsk-ai://oauth-return",
                      "pomp-hsk-ai-qa?secret=bad", "javascript:alert(1)"):
            with self.subTest(value=value):
                settings = Settings(_env_file=None, OAUTH_NATIVE_RETURN_SCHEME=value)
                self.assertEqual(settings.OAUTH_NATIVE_RETURN_SCHEME,
                    value if value in {"pomp-hsk-ai", "pomp-hsk-ai-qa"} else None)
        self.assertEqual(Settings.model_fields["OAUTH_NATIVE_RETURN_SCHEME"].default, "pomp-hsk-ai")


class NativeOAuthLifecycleTests(_ProviderFixture):
    async def test_provider_error_burns_only_a_valid_matching_signin_proof(self):
        for provider in ("google", "apple"):
            with self.subTest(provider=provider):
                started = (await self.client.post("/api/v3/native-auth/oauth/start",
                    json=self._start_body(provider=provider, mode="browser_redirect"))).json()
                async with self.sessions() as session:
                    state = NativeOAuthService(session, self.settings).state(started["link_request_id"])
                for target, proof in ((provider, None), (provider, state + "bad"),
                                      ("apple" if provider == "google" else "google", state)):
                    response = await self._error_callback(target, proof)
                    self.assertEqual(response.status_code, 200)
                    self.assertNotIn("pomp-hsk-ai://", response.text)
                    self.assertNotIn(state, response.text)
                    async with self.sessions() as session:
                        self.assertEqual((await session.get(DesktopLinkRequest, started["link_request_id"])).status, "pending")
                response = await self._error_callback(provider, state)
                self.assertIn("oauth_cancelled", response.text)
                self.assertNotIn("pomp-hsk-ai://", response.text)
                async with self.sessions() as session:
                    from app.services.desktop_auth_service import DesktopAuthService
                    with self.assertRaises(DesktopAuthError) as rejected:
                        await DesktopAuthService(session, self.settings).poll_link(
                            link_request_id=started["link_request_id"], polling_secret=started["polling_secret"])
                    self.assertEqual(rejected.exception.code, "oauth_cancelled")
                    self.assertEqual(await session.scalar(select(func.count(UserIdentity.id))), 0)
                    self.assertEqual(await session.scalar(select(func.count(DesktopSession.id))), 0)

    async def test_provider_error_is_terminal_for_both_identity_link_flows(self):
        headers = await self._bearer()
        for provider in ("google", "apple"):
            with self.subTest(provider=provider):
                _, pending = await self._pending(provider, headers=headers)
                response = await self._error_callback(provider, pending["state"])
                self.assertIn("oauth_cancelled", response.text)
                self.assertNotIn("pomp-hsk-ai://", response.text)
                status = await self.client.post("/api/v3/native-auth/identities/link/status", headers=headers,
                    json={key: pending[key] for key in ("link_request_id", "polling_secret")})
                self.assertEqual(status.json(), {"ok": True, "status": "failed", "provider": provider,
                                               "error": "oauth_cancelled"})

    async def test_cancelling_either_provider_burns_only_its_pending_proof(self):
        headers = await self._bearer()
        for provider in ("google", "apple"):
            with self.subTest(provider=provider):
                _, pending = await self._pending(provider, headers=headers)
                async with self.sessions() as session:
                    sessions_before = await session.scalar(select(func.count(DesktopSession.id)))
                cancelled = await self._cancel(pending, headers)
                self.assertEqual(cancelled.json(), {"ok": True, "status": "denied", "provider": provider})
                self.assertEqual(cancelled.headers["Cache-Control"], "no-store")
                self.assertEqual((await self._cancel(pending, headers)).json(), cancelled.json())
                with patch("app.services." + provider + "_auth.exchange_code") as exchange:
                    callback = await self._callback(provider, pending["state"])
                exchange.assert_not_called()
                self.assertIn("desktop_link_consumed", callback.text)
                self.assertNotIn("pomp-hsk-ai://", callback.text)
                status = await self.client.post("/api/v3/native-auth/identities/link/status", headers=headers,
                    json={key: pending[key] for key in ("link_request_id", "polling_secret")})
                self.assertEqual(status.json()["status"], "denied")
                async with self.sessions() as session:
                    self.assertEqual(await session.scalar(select(func.count(UserIdentity.id))), 0)
                    self.assertEqual(await session.scalar(select(func.count(User.id))), 2)
                    self.assertEqual(await session.scalar(select(func.count(DesktopSession.id))), sessions_before)

    async def test_cancel_requires_owner_originating_session_and_secret(self):
        headers, pending = await self._pending()
        bob = await self._bearer(telegram_id=1002)
        replacement = await self._bearer()
        for actor, proof in ((bob, pending), (replacement, pending),
                             (headers, dict(pending, polling_secret="wrong-secret" * 4))):
            with self.subTest(actor=actor is headers, proof=proof is pending):
                self.assertEqual((await self._cancel(proof, actor)).status_code, 401)
        async with self.sessions() as session:
            self.assertEqual((await session.get(DesktopLinkRequest, pending["link_request_id"])).status, "pending")
        self.assertEqual((await self._cancel(pending, headers)).json()["status"], "denied")

    async def test_cancel_of_linked_proof_does_not_unlink_or_revoke(self):
        headers, pending = await self._pending()
        with patch("app.services.google_auth.exchange_code", return_value="fixture-id-token"), patch(
                "app.services.google_auth.verify_desktop_id_token", return_value=_verified()):
            result = await self._callback("google", pending["state"])
        self.assertIn("oauth-return", result.text)
        self.assertEqual((await self._cancel(pending, headers)).json()["status"], "linked")
        async with self.sessions() as session:
            identity = (await session.execute(select(UserIdentity))).scalar_one()
            self.assertEqual(identity.user_id, 1)
            self.assertIsNone((await session.get(DesktopSession, pending["origin_session_id"])).revoked_at)
            self.assertEqual(await session.scalar(select(func.count(DesktopSession.id))), 1)

    async def test_cancel_cannot_burn_a_signin_row_and_cached_pending_cannot_bypass_cancel(self):
        headers, pending = await self._pending()
        signin = (await self.client.post("/api/v3/native-auth/oauth/start",
            json=self._start_body(mode="browser_redirect"))).json()
        self.assertEqual((await self._cancel(signin, headers)).status_code, 401)
        async with self.sessions() as stale:
            cached = await stale.get(DesktopLinkRequest, pending["link_request_id"])
            self.assertEqual(cached.status, "pending")
            self.assertEqual((await self._cancel(pending, headers)).json()["status"], "denied")
            with patch("app.services.google_auth.exchange_code") as exchange:
                with self.assertRaises(NativeOAuthError) as rejected:
                    await NativeOAuthService(stale, self.settings).complete_callback(
                        provider="google", state=pending["state"], code="code")
            exchange.assert_not_called()
            self.assertEqual(rejected.exception.code, "desktop_link_consumed")
        async with self.sessions() as session:
            self.assertEqual((await session.get(DesktopLinkRequest, signin["link_request_id"])).status, "pending")
            self.assertEqual(await session.scalar(select(func.count(UserIdentity.id))), 0)

    async def test_revoked_expired_device_and_blocked_origins_cannot_cancel(self):
        _, pending = await self._pending()
        now = datetime.now(timezone.utc)
        for failure in ("revoked", "expired", "device", "blocked", "installation", "platform"):
            with self.subTest(failure=failure):
                async with self.sessions() as session:
                    origin = await session.get(DesktopSession, pending["origin_session_id"])
                    device = await session.get(DesktopDevice, origin.device_id)
                    user = await session.get(User, 1)
                    origin.revoked_at = now if failure == "revoked" else None
                    origin.expires_at = now + timedelta(days=-1 if failure == "expired" else 1)
                    device.revoked_at = now if failure == "device" else None
                    device.installation_key_hash = NativeOAuthService(session, self.settings).auth._hash(
                        "installation", "z" * 48 if failure == "installation" else INSTALLATION_KEY)
                    device.platform = "macos" if failure == "platform" else "android"
                    user.status = "blocked" if failure == "blocked" else "free"
                    await session.commit()
                async with self.sessions() as session:
                    with self.assertRaises((DesktopAuthError, NativeOAuthError, IdentityLinkError)):
                        await NativeOAuthService(session, self.settings).cancel_link(
                            link_request_id=pending["link_request_id"], polling_secret=pending["polling_secret"],
                            user_id=1, session_id=pending["origin_session_id"])
                async with self.sessions() as session:
                    self.assertEqual((await session.get(DesktopLinkRequest, pending["link_request_id"])).status, "pending")

    async def test_provider_link_start_rejects_wrong_installation_or_platform_before_allocation(self):
        headers = await self._bearer()
        for changes in ({"installation_key": "wrong".ljust(48, "x")}, {"platform": "macos"}):
            with self.subTest(changes=changes):
                result = await self.client.post("/api/v3/native-auth/identities/link/start", headers=headers,
                    json=self._start_body(mode="browser_redirect", **changes))
                self.assertEqual(result.status_code, 401)
        async with self.sessions() as session:
            self.assertEqual(await session.scalar(select(func.count()).select_from(DesktopLinkRequest).where(
                DesktopLinkRequest.intent == "link")), 0)

    async def test_miniapp_cancel_uses_its_signed_actor_without_a_native_session(self):
        headers = {"X-Telegram-Init-Data": oauth_fixture.MiniAppLinkTests._init_data(self)}
        _, pending = await self._pending(headers=headers, platform="miniapp")
        self.assertIsNone(pending["origin_session_id"])
        self.assertEqual((await self._cancel(pending, headers)).json()["status"], "denied")
        async with self.sessions() as session:
            self.assertEqual(await session.scalar(select(func.count(DesktopSession.id))), 0)

    async def test_only_successful_native_callbacks_offer_the_static_handoff(self):
        for provider in ("google", "apple"):
            for platform in ("android", "macos", "windows", "miniapp"):
                with self.subTest(provider=provider, platform=platform):
                    body = self._start_body(provider=provider, platform=platform, mode="browser_redirect",
                        installation_key=(provider + platform).ljust(48, "x"))
                    headers = {}
                    path = "/api/v3/native-auth/oauth/start"
                    if platform == "miniapp":
                        headers = {"X-Telegram-Init-Data": oauth_fixture.MiniAppLinkTests._init_data(self)}
                        path = "/api/v3/native-auth/identities/link/start"
                    started = await self.client.post(path, json=body, headers=headers)
                    self.assertEqual(started.status_code, 200, started.text)
                    async with self.sessions() as session:
                        state = NativeOAuthService(session, self.settings).state(started.json()["link_request_id"])
                    verify = "verify_desktop_id_token" if provider == "google" else "verify_id_token_for_service"
                    with patch("app.services." + provider + "_auth.exchange_code", return_value="fixture-id-token"), patch(
                            "app.services." + provider + "_auth." + verify,
                            return_value=_verified(subject=provider + platform, provider=provider)):
                        callback = await self._callback(provider, state)
                    self.assertEqual(callback.status_code, 200)
                    self.assertIn('<div class="code">ok</div>', callback.text)
                    self.assertEqual("pomp-hsk-ai://oauth-return" in callback.text, platform != "miniapp")
                    for secret in (state, "fixture-auth-code", "fixture-id-token", "alice@example.com"):
                        self.assertNotIn(secret, callback.text)
                    if platform != "miniapp":
                        script = re.search(r"<script>(.*?)</script>", callback.text).group(1)
                        digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
                        self.assertIn("script-src 'sha256-" + digest + "'", callback.headers["Content-Security-Policy"])
                    self.assertEqual(callback.headers["Cache-Control"], "no-store")

    async def test_native_assert_refuses_desktop_and_miniapp_before_verifying_a_token(self):
        for platform in ("macos", "windows", "miniapp"):
            with self.subTest(platform=platform):
                body = self._start_body(platform=platform, mode="browser_redirect")
                headers = {}
                path = "/api/v3/native-auth/oauth/start"
                if platform == "miniapp":
                    path = "/api/v3/native-auth/identities/link/start"
                    headers = {"X-Telegram-Init-Data": oauth_fixture.MiniAppLinkTests._init_data(self)}
                started = (await self.client.post(path, json=body, headers=headers)).json()
                with patch("app.services.google_auth.verify_android_id_token") as verify:
                    response = await self.client.post("/api/v3/native-auth/oauth/assert", json={
                        "link_request_id": started["link_request_id"], "polling_secret": started["polling_secret"],
                        "provider": "google", "id_token": "t" * 64})
                verify.assert_not_called()
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()["error"], "oauth_mode_unsupported")

    async def test_callback_return_scheme_is_server_allowlisted_and_can_be_disabled(self):
        for scheme in ("pomp-hsk-ai-qa", "pomp-hsk-ai", None, "https://attacker.example"):
            with self.subTest(scheme=scheme):
                self.settings.OAUTH_NATIVE_RETURN_SCHEME = scheme
                started = (await self.client.post("/api/v3/native-auth/oauth/start",
                    json=self._start_body(mode="browser_redirect"))).json()
                async with self.sessions() as session:
                    state = NativeOAuthService(session, self.settings).state(started["link_request_id"])
                with patch("app.services.google_auth.exchange_code", return_value="token"), patch(
                        "app.services.google_auth.verify_desktop_id_token", return_value=_verified()):
                    result = await self._callback("google", state)
                self.assertEqual(result.status_code, 200)
                self.assertIn('<div class="code">ok</div>', result.text)
                if scheme in {"pomp-hsk-ai", "pomp-hsk-ai-qa"}:
                    self.assertIn('href="' + scheme + '://oauth-return"', result.text)
                    script = re.search(r"<script>(.*?)</script>", result.text).group(1)
                    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
                    self.assertIn("script-src 'sha256-" + digest + "'", result.headers["Content-Security-Policy"])
                else:
                    self.assertNotIn("<a ", result.text)
                    self.assertNotIn("<script>", result.text)
                self.assertNotIn("attacker.example", result.text)

    async def test_signed_tokens_must_match_the_selected_nonce_domain(self):
        key = _Key("oauth-mode-isolation")
        cache = _Jwks(key).cache()
        original_native = google_auth.verify_android_id_token
        original_browser = google_auth.verify_desktop_id_token
        async def verify_native(token, **kwargs):
            return await original_native(token, cache=cache, **kwargs)
        async def verify_browser(token, **kwargs):
            return await original_browser(token, cache=cache, **kwargs)
        async with self.sessions() as session:
            from app.services.identity_link_service import IdentityLinkService
            await IdentityLinkService(session, self.settings).link_to_user(_verified(), user_id=1)
            await session.commit()
        for mode, endpoint in (("native_id_token", "native"), ("browser_redirect", "browser"),
                               ("browser_redirect", "native"), ("native_id_token", "browser")):
            with self.subTest(mode=mode, endpoint=endpoint):
                response = await self.client.post("/api/v3/native-auth/oauth/start", json=self._start_body(mode=mode))
                started = response.json()
                audience = (self.settings.GOOGLE_ANDROID_WEB_CLIENT_ID if endpoint == "native"
                            else self.settings.GOOGLE_DESKTOP_CLIENT_ID)
                selected_nonce = (started["nonce"] if mode == "native_id_token" else
                    parse_qs(urlparse(started["authorize_url"]).query)["nonce"][0])
                token = key.sign(_claims(aud=audience, sub="sub-alice", nonce=selected_nonce))
                with patch("app.services.google_auth.verify_android_id_token", side_effect=verify_native), patch(
                        "app.services.google_auth.verify_desktop_id_token", side_effect=verify_browser), patch(
                        "app.services.google_auth.exchange_code", return_value=token):
                    if endpoint == "native":
                        result = await self.client.post("/api/v3/native-auth/oauth/assert", json={
                            "link_request_id": started["link_request_id"], "polling_secret": started["polling_secret"],
                            "provider": "google", "id_token": token})
                    else:
                        async with self.sessions() as session:
                            state = NativeOAuthService(session, self.settings).state(started["link_request_id"])
                        result = await self._callback("google", state)
                correct = (mode == "native_id_token") == (endpoint == "native")
                if correct:
                    self.assertIn("approved" if endpoint == "native" else '<div class="code">ok</div>', result.text)
                else:
                    self.assertIn("oidc_nonce_mismatch", result.text)
                    self.assertNotIn("pomp-hsk-ai://oauth-return", result.text)
                self.assertNotIn("access_token", result.text)
                self.assertNotIn("refresh_token", result.text)
                async with self.sessions() as session:
                    row = await session.get(DesktopLinkRequest, started["link_request_id"])
                    self.assertEqual(row.approved_user_id, 1 if correct else None)
                    self.assertEqual(await session.scalar(select(func.count(User.id))), 2)
                    self.assertEqual(await session.scalar(select(func.count(UserIdentity.id))), 1)
                    self.assertEqual(await session.scalar(select(func.count(DesktopSession.id))), 0)


@unittest.skipUnless(os.environ.get("NATIVE_ACCOUNT_TEST_DATABASE_URL"), "requires isolated PostgreSQL test database")
class NativeOAuthConcurrencyTests(_ProviderFixture):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        # The shared fixture inserts explicit legacy IDs; PostgreSQL sequences
        # need advancing before this suite exercises a genuinely new signup.
        async with self.engine.begin() as connection:
            await connection.execute(text("SELECT setval(pg_get_serial_sequence('users', 'id'), "
                "(SELECT max(id) FROM users), true)"))

    async def _setup_engine(self):
        self.schema = "oauth_lifecycle_" + uuid4().hex
        url = os.environ["NATIVE_ACCOUNT_TEST_DATABASE_URL"]
        self.admin = create_async_engine(url)
        async with self.admin.begin() as connection:
            await connection.execute(text(f"CREATE SCHEMA {self.schema}"))
        self.engine = create_async_engine(url,
            connect_args={"server_settings": {"search_path": self.schema + ",public"}})

    async def asyncTearDown(self):
        await super().asyncTearDown()
        async with self.admin.begin() as connection:
            await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
        await self.admin.dispose()

    async def test_provider_error_and_success_callback_cannot_both_commit(self):
        for winner in ("error", "callback"):
            with self.subTest(winner=winner):
                started = (await self.client.post("/api/v3/native-auth/oauth/start",
                    json=self._start_body(mode="browser_redirect"))).json()
                async with self.sessions() as session:
                    state = NativeOAuthService(session, self.settings).state(started["link_request_id"])
                entered, release = asyncio.Event(), asyncio.Event()
                async def exchange(*args, **kwargs):
                    if winner == "callback":
                        entered.set()
                        await release.wait()
                    return "token"
                async def callback():
                    async with self.sessions() as session:
                        return await NativeOAuthService(session, self.settings).complete_callback(
                            provider="google", state=state, code="code")
                async def error_callback():
                    async with self.sessions() as session:
                        service = NativeOAuthService(session, self.settings)
                        if winner == "error":
                            original = service._fail
                            async def fail(row, code):
                                entered.set()
                                await release.wait()
                                await original(row, code)
                            service._fail = fail
                        await service.cancel_callback(provider="google", state=state)
                with patch("app.services.google_auth.exchange_code", side_effect=exchange), patch(
                        "app.services.google_auth.verify_desktop_id_token", return_value=_verified()):
                    first = asyncio.create_task(error_callback() if winner == "error" else callback())
                    await asyncio.wait_for(entered.wait(), postgres_timeout(10))
                    second = asyncio.create_task(callback() if winner == "error" else error_callback())
                    await asyncio.sleep(0.1)
                    self.assertFalse(second.done())
                    release.set()
                    results = await asyncio.wait_for(asyncio.gather(first, second, return_exceptions=True), postgres_timeout(15))
                if winner == "error":
                    self.assertIsNone(results[0])
                else:
                    self.assertEqual(results[0]["status"], "approved")
                self.assertIsInstance(results[1], NativeOAuthError, results)
                self.assertEqual(results[1].code, "desktop_link_consumed")
                async with self.sessions() as session:
                    row = await session.get(DesktopLinkRequest, started["link_request_id"])
                    self.assertEqual(row.status, "failed" if winner == "error" else "approved")
                    self.assertEqual(await session.scalar(select(func.count(UserIdentity.id))), int(winner == "callback"))
                    self.assertEqual(await session.scalar(select(func.count(DesktopSession.id))), 0)

    async def test_cancel_and_callback_serialize_in_both_winning_orders(self):
        headers = await self._bearer()
        for winner in ("cancel", "callback"):
            with self.subTest(winner=winner):
                _, pending = await self._pending(headers=headers)
                entered, release = asyncio.Event(), asyncio.Event()
                async def exchange(*args, **kwargs):
                    if winner == "callback":
                        entered.set()
                        await release.wait()
                    return "fixture-id-token"
                async def callback():
                    async with self.sessions() as session:
                        return await NativeOAuthService(session, self.settings).complete_callback(
                            provider="google", state=pending["state"], code="fixture-code")
                async def cancel():
                    async with self.sessions() as session:
                        service = NativeOAuthService(session, self.settings)
                        if winner == "cancel":
                            original = service._link_owner
                            async def owner(row):
                                entered.set()
                                await release.wait()
                                return await original(row)
                            service._link_owner = owner
                        return await service.cancel_link(link_request_id=pending["link_request_id"],
                            polling_secret=pending["polling_secret"], user_id=1, session_id=pending["origin_session_id"])
                with patch("app.services.google_auth.exchange_code", side_effect=exchange), patch(
                        "app.services.google_auth.verify_desktop_id_token", return_value=_verified()):
                    first = asyncio.create_task(cancel() if winner == "cancel" else callback())
                    await asyncio.wait_for(entered.wait(), postgres_timeout(10))
                    second = asyncio.create_task(callback() if winner == "cancel" else cancel())
                    await asyncio.sleep(0.1)
                    self.assertFalse(second.done(), "competing proof must wait for the locked request")
                    release.set()
                    results = await asyncio.wait_for(asyncio.gather(first, second, return_exceptions=True), postgres_timeout(15))
                self.assertIsInstance(results[0], dict, results)
                if winner == "cancel":
                    self.assertEqual(results[0]["status"], "denied")
                    self.assertIsInstance(results[1], NativeOAuthError, results)
                    self.assertEqual(results[1].code, "desktop_link_consumed")
                else:
                    self.assertEqual([result["status"] for result in results], ["linked", "linked"])
                async with self.sessions() as session:
                    self.assertEqual(await session.scalar(select(func.count(UserIdentity.id))), int(winner == "callback"))
                    self.assertEqual(await session.scalar(select(func.count(DesktopSession.id))), 1)

    async def test_callback_and_cancel_wait_for_origin_revocation(self):
        headers = await self._bearer()
        for action in ("callback", "cancel"):
            with self.subTest(action=action):
                _, pending = await self._pending(headers=headers)
                async def operation():
                    async with self.sessions() as session:
                        service = NativeOAuthService(session, self.settings)
                        if action == "callback":
                            return await service.complete_callback(provider="google", state=pending["state"], code="code")
                        return await service.cancel_link(link_request_id=pending["link_request_id"],
                            polling_secret=pending["polling_secret"], user_id=1, session_id=pending["origin_session_id"])
                with patch("app.services.google_auth.exchange_code", return_value="token"), patch(
                        "app.services.google_auth.verify_desktop_id_token", return_value=_verified()):
                    async with self.sessions() as blocker:
                        origin = (await blocker.execute(select(DesktopSession).where(
                            DesktopSession.id == pending["origin_session_id"]).with_for_update())).scalar_one()
                        task = asyncio.create_task(operation())
                        await asyncio.sleep(0.1)
                        self.assertFalse(task.done(), "provider proof must wait for origin lock")
                        origin.revoked_at = datetime.now(timezone.utc)
                        await blocker.commit()
                    result = (await asyncio.wait_for(asyncio.gather(task, return_exceptions=True), postgres_timeout(15)))[0]
                self.assertIsInstance(result, (NativeOAuthError, DesktopAuthError), result)
                self.assertEqual(result.code, "desktop_session_revoked")
                async with self.sessions() as session:
                    self.assertEqual(await session.scalar(select(func.count(UserIdentity.id))), 0)
                    origin = await session.get(DesktopSession, pending["origin_session_id"])
                    origin.revoked_at = None
                    await session.commit()

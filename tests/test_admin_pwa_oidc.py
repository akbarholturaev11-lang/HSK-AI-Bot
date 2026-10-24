"""SQL-backed isolated tests for Admin PWA OIDC state; no Google network used."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.admin_api.pwa_oidc import (
    AdminPwaOidcError, finish_admin_pwa_google, start_admin_pwa_google,
)
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_approval import AdminPwaApproval
from app.db.models.admin_pwa_oauth import AdminPwaOAuthAttempt
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.services import google_auth
from app.services.oidc_verifier import VerifiedIdentity

NOW = datetime(2026, 10, 23, 16, tzinfo=timezone.utc)


class AsyncAdapter:
    def __init__(self, session):
        self.session = session

    def add(self, obj):
        self.session.add(obj)

    async def execute(self, query):
        return self.session.execute(query)

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()

    def get_bind(self):
        return self.session.get_bind()


class AdminPwaOidcTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        for table in (
            User.__table__, UserIdentity.__table__, AdminPwaSession.__table__,
            AdminPwaApproval.__table__, AdminPwaOAuthAttempt.__table__,
        ):
            table.create(self.engine)
        self.session = Session(self.engine)
        self.db = AsyncAdapter(self.session)
        self.settings = SimpleNamespace(
            ADMIN_PWA_ENABLED=True,
            ADMIN_PWA_PUBLIC_ORIGIN="https://hskai.app",
            GOOGLE_OAUTH_ENABLED=True,
            GOOGLE_DESKTOP_CLIENT_ID="admin-test-client-id",
            GOOGLE_DESKTOP_CLIENT_SECRET="test-only-client-secret",
            DESKTOP_AUTH_SIGNING_SECRET="test-only-OIDC-state-signing-" + "X" * 64,
        )
        self.seen_verifier = None
        self.seen_nonce = None

        async def test_exchange(code, *, settings_obj, redirect_uri, code_verifier):
            self.seen_verifier = code_verifier
            self.assertEqual(
                redirect_uri, "https://hskai.app/api/admin/v1/auth/google/callback"
            )
            if code != "valid-code":
                raise ValueError("test_invalid_code")
            return "fake-verified-by-patched-provider"

        async def test_verify(id_token, *, settings_obj, nonce, **kwargs):
            self.seen_nonce = nonce
            return VerifiedIdentity(
                provider="google", subject="google-subject-1",
                email=None, email_verified=True, display_name=None,
                audience=settings_obj.GOOGLE_DESKTOP_CLIENT_ID,
            )

        p1 = patch.object(google_auth, "exchange_code", new=test_exchange)
        p2 = patch.object(google_auth, "verify_desktop_id_token", new=test_verify)
        p1.start()
        p2.start()
        self.addCleanup(p1.stop)
        self.addCleanup(p2.stop)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    async def start(self):
        return await start_admin_pwa_google(
            self.db, settings_obj=self.settings, now=NOW
        )

    @staticmethod
    def state(started):
        return parse_qs(urlsplit(started.authorize_url).query)["state"][0]

    async def finish(self, started, **overrides):
        # The real callback must use a fresh database session.
        if self.session.in_transaction():
            self.session.rollback()
        return await finish_admin_pwa_google(
            self.db, settings_obj=self.settings,
            state=overrides.get("state", self.state(started)),
            code=overrides.get("code", "valid-code"),
            browser_proof=overrides.get("browser_proof", started.browser_proof),
            now=overrides.get("now", NOW),
        )

    async def test_global_start_rate_limit_fails_closed(self):
        for _ in range(60):
            await self.start()
        with self.assertRaisesRegex(AdminPwaOidcError, "rate_limited"):
            await self.start()
        self.assertEqual(
            len(self.session.execute(select(AdminPwaOAuthAttempt)).scalars().all()),
            60,
        )

    async def test_verified_google_creates_single_pending_approval_no_session(self):
        started = await self.start()
        result = await self.finish(started)
        self.assertIsNotNone(result)
        self.assertEqual(
            self.session.execute(select(AdminPwaOAuthAttempt)).scalar_one().status,
            "consumed",
        )
        self.assertEqual(
            self.session.execute(select(AdminPwaApproval)).scalar_one().status,
            "pending",
        )
        self.assertEqual(
            self.session.execute(select(AdminPwaSession)).scalars().all(), [],
        )
        self.assertIsNone(await self.finish(started))

    async def test_wrong_browser_cannot_claim_other_state(self):
        one, two = await self.start(), await self.start()
        self.assertIsNone(
            await self.finish(one, browser_proof=two.browser_proof)
        )
        self.assertIsNotNone(await self.finish(one))

    async def test_tampered_state_fails_before_provider_exchange(self):
        started = await self.start()
        state = self.state(started)
        changed = state[:-1] + ("0" if state[-1] != "0" else "1")
        self.assertIsNone(await self.finish(started, state=changed))
        self.assertIsNone(self.seen_verifier)
        self.assertIsNotNone(await self.finish(started))

    async def test_expired_state_rejected(self):
        started = await self.start()
        self.assertIsNone(
            await self.finish(started, now=NOW + timedelta(minutes=10))
        )
        self.assertEqual(
            self.session.execute(select(AdminPwaOAuthAttempt)).scalar_one().status,
            "pending",
        )

    async def test_failed_token_exchange_does_not_mint_approval(self):
        started = await self.start()
        with self.assertRaises(ValueError):
            await self.finish(started, code="wrong-code")
        self.assertEqual(
            self.session.execute(select(AdminPwaOAuthAttempt)).scalar_one().status,
            "pending",
        )
        self.assertEqual(
            self.session.execute(select(AdminPwaApproval)).scalars().all(), [],
        )
        self.assertIsNotNone(await self.finish(started))

    async def test_disabled_flag_blocks_start_and_finish(self):
        started = await self.start()
        self.settings.ADMIN_PWA_ENABLED = False
        with self.assertRaises(AdminPwaOidcError):
            await self.start()
        with self.assertRaises(AdminPwaOidcError):
            await self.finish(started)

    async def test_noncanonical_origin_rejected(self):
        for origin in (
            "http://hskai.app", "https://hskai.app/admin",
            "https://hskai.app?x=1", "https://hskai.app:8443",
            "https://[broken",
        ):
            with self.subTest(origin=origin):
                self.settings.ADMIN_PWA_PUBLIC_ORIGIN = origin
                with self.assertRaises(AdminPwaOidcError):
                    await self.start()

    async def test_verified_oidc_provider_and_audience_must_match(self):
        started = await self.start()
        for provider, audience in (
            ("apple", self.settings.GOOGLE_DESKTOP_CLIENT_ID),
            ("google", "android-client-audience"),
        ):
            async def invalid_verify(id_token, *, settings_obj, nonce, **kwargs):
                return VerifiedIdentity(
                    provider=provider, subject="google-subject-1",
                    email=None, email_verified=True, display_name=None,
                    audience=audience,
                )
            with self.subTest(provider=provider, audience=audience):
                with patch.object(
                    google_auth, "verify_desktop_id_token", new=invalid_verify
                ):
                    self.assertIsNone(await self.finish(started))
        self.assertIsNotNone(await self.finish(started))

    async def test_authorize_url_has_pkce_nonce_correct_callback_no_proof_leak(self):
        started = await self.start()
        params = parse_qs(urlsplit(started.authorize_url).query)
        self.assertEqual(
            params["redirect_uri"],
            ["https://hskai.app/api/admin/v1/auth/google/callback"],
        )
        self.assertEqual(params["code_challenge_method"], ["S256"])
        self.assertEqual(len(params["nonce"][0]), 64)
        self.assertEqual(len(params["code_challenge"][0]), 43)
        self.assertNotIn(started.browser_proof, started.authorize_url)
        self.assertIsNotNone(await self.finish(started))
        self.assertEqual(self.seen_nonce, params["nonce"][0])
        self.assertEqual(len(self.seen_verifier), 64)


if __name__ == "__main__":
    unittest.main()

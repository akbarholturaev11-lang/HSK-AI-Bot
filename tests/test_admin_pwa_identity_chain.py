"""Google OIDC -> trusted private Bot -> canonical identity link.

A service-chain test, not live Google, real aiogram/HTTP or session issuance.
Provider network verification is mocked; PostgreSQL concurrency must be tested
separately in a full deployment-like environment.
"""
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.admin_api.pwa_oidc import start_admin_pwa_google, finish_admin_pwa_google
from app.admin_api.pwa_bot_approval import (
    preview_admin_pwa_bot_request, decide_admin_pwa_bot_request,
    read_browser_pwa_approval,
)
from app.admin_api.pwa_enrollment import finalize_google_admin_enrollment
from app.db.models.admin_pwa_oauth import AdminPwaOAuthAttempt
from app.db.models.admin_pwa_approval import AdminPwaApproval
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.user_identity import UserIdentity
from app.db.models.user import User
from app.services import google_auth
from app.services.oidc_verifier import VerifiedIdentity

NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)
AUDIENCE = "test-google-web-client"


class AsyncAdapter:
    def __init__(self, session):
        self.session = session

    def add(self, item):
        self.session.add(item)

    def get_bind(self):
        return self.session.get_bind()

    async def execute(self, query):
        return self.session.execute(query)

    async def flush(self):
        self.session.flush()

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()

    @asynccontextmanager
    async def begin(self):
        with self.session.begin():
            yield self


class AdminPwaIdentityChainTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        for model in (User, UserIdentity, AdminPwaSession,
                      AdminPwaOAuthAttempt, AdminPwaApproval):
            model.__table__.create(self.engine)
        self.session = Session(self.engine)
        self.db = AsyncAdapter(self.session)
        self.session.add_all([
            User(id=101, telegram_id=9001, status="active"),
            User(id=102, telegram_id=9002, status="active"),
        ])
        self.session.commit()
        self.settings = SimpleNamespace(
            ADMIN_PWA_ENABLED=True,
            ADMIN_PWA_PUBLIC_ORIGIN="https://hskai.app",
            GOOGLE_OAUTH_ENABLED=True,
            GOOGLE_DESKTOP_CLIENT_ID=AUDIENCE,
            GOOGLE_DESKTOP_CLIENT_SECRET="test-secret-only",
            admin_id_list=[9001],
            DESKTOP_AUTH_SIGNING_SECRET="s" * 64,
        )

        async def exchange(*args, **kwargs):
            return "mock-server-verified-token"

        async def verify(*args, **kwargs):
            return VerifiedIdentity(
                provider="google", subject="actual-verified-google-sub",
                audience=AUDIENCE, email=None, email_verified=True,
                display_name=None,
            )

        for name, handler in (
            ("exchange_code", exchange),
            ("verify_desktop_id_token", verify),
        ):
            mocked = patch.object(google_auth, name, new=handler)
            mocked.start()
            self.addCleanup(mocked.stop)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    @staticmethod
    def bot_event(uid=9001):
        return SimpleNamespace(
            from_user=SimpleNamespace(id=uid, is_bot=False),
            message=SimpleNamespace(
                chat=SimpleNamespace(id=uid, type="private"),
            ),
        )

    async def create_oidc_verified_request(self):
        started = await start_admin_pwa_google(
            self.db, settings_obj=self.settings, now=NOW,
        )
        state = parse_qs(urlsplit(started.authorize_url).query)["state"][0]
        return await finish_admin_pwa_google(
            self.db, settings_obj=self.settings, state=state,
            code="mock-exchange", browser_proof=started.browser_proof, now=NOW,
        )

    async def finalize(self, pending, *, proof=None):
        if self.session.in_transaction():
            self.session.commit()  # Real route uses a fresh AsyncSession.
        return await finalize_google_admin_enrollment(
            self.db, request_id=pending.request_id,
            browser_proof=proof if proof is not None else pending.browser_proof,
            settings_obj=self.settings, now=NOW,
        )

    async def decide(self, pending, approve=True):
        return await decide_admin_pwa_bot_request(
            self.db, bot_event=self.bot_event(), request_id=pending.request_id,
            approve=approve, settings_obj=self.settings, now=NOW,
        )

    async def test_verified_chain_links_without_a_second_google_signin_or_admin_session(self):
        pending = await self.create_oidc_verified_request()
        bot = await preview_admin_pwa_bot_request(
            self.db, bot_event=self.bot_event(), request_id=pending.request_id,
            settings_obj=self.settings, now=NOW,
        )
        browser = await read_browser_pwa_approval(
            self.db, request_id=pending.request_id,
            browser_proof=pending.browser_proof, settings_obj=self.settings, now=NOW,
        )
        self.assertEqual(bot.pairing_code, browser.pairing_code)
        self.assertIsNone(await self.finalize(pending))  # Still pending.
        self.assertTrue(await self.decide(pending))
        linked = await self.finalize(pending)
        self.assertEqual((linked.user_id, linked.telegram_id), (101, 9001))
        identity = self.session.execute(select(UserIdentity)).scalar_one()
        self.assertEqual(identity.subject_hash, linked.google_subject_hash)
        self.assertEqual(identity.audience, AUDIENCE)
        self.assertEqual(identity.user_id, 101)
        self.assertIsNone(identity.email_display)
        self.assertIsNone(await self.finalize(pending))  # Replay.
        self.assertEqual(self.session.execute(select(AdminPwaSession)).scalars().all(), [])
        self.assertEqual(
            self.session.execute(select(AdminPwaApproval)).scalar_one().status,
            "consumed",
        )

    async def test_other_browser_cannot_link_even_after_bot_approval(self):
        pending = await self.create_oidc_verified_request()
        self.assertTrue(await self.decide(pending))
        self.assertIsNone(await self.finalize(pending, proof="X" * 64))
        self.assertEqual(self.session.execute(select(UserIdentity)).scalars().all(), [])
        self.assertIsNotNone(await self.finalize(pending))

    async def test_bot_denial_is_terminal_without_identity_link(self):
        pending = await self.create_oidc_verified_request()
        self.assertTrue(await self.decide(pending, approve=False))
        self.assertIsNone(await self.finalize(pending))
        self.assertEqual(self.session.execute(select(UserIdentity)).scalars().all(), [])

    async def test_privilege_revoked_after_bot_approval(self):
        pending = await self.create_oidc_verified_request()
        self.assertTrue(await self.decide(pending))
        self.settings.admin_id_list = []
        self.assertIsNone(await self.finalize(pending))
        self.assertEqual(self.session.execute(select(UserIdentity)).scalars().all(), [])


if __name__ == "__main__":
    unittest.main()

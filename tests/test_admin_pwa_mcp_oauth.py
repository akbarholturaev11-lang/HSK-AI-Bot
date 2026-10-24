"""End-to-end DB service test for unexposed MCP OAuth consent and PKCE.

This tests real SQLite transactions, hashed codes/tokens, and current admin
rights, but NOT remote ChatGPT, a public OAuth endpoint or a consent UI.
"""
import unittest
import hashlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.admin_api.pwa_mcp_oauth import (
    begin_mcp_authorization, decide_mcp_consent, exchange_mcp_code, pkce_s256,
)
from app.admin_api.pwa_mcp_resource import verify_readonly_mcp_bearer
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_mcp import AdminPwaMcpAccessGrant
from app.db.models.admin_pwa_mcp_authorization import AdminPwaMcpAuthorization
from app.db.models.user import User

NOW = datetime(2026, 10, 24, 14, tzinfo=timezone.utc)
COOKIE = "S" * 64
VERIFIER = "a" * 64
STATE = "state-" + "z" * 44
CLIENT = "pre-registered-test-client"
REDIRECT = "https://client.example/callback"
RESOURCE = "https://hskai.app/mcp"
SCOPE = "admin:analytics:read"


class McpOAuthCeremonyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            for model in (User, AdminPwaSession, AdminPwaMcpAuthorization, AdminPwaMcpAccessGrant):
                await connection.run_sync(model.__table__.create)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.csrf_by_id = {}
        self.settings = SimpleNamespace(
            ADMIN_PWA_ENABLED=True, ADMIN_PWA_MCP_ENABLED=True,
            ADMIN_PWA_MCP_RESOURCE=RESOURCE, admin_id_list=[9001],
            ADMIN_PWA_MCP_CLIENT_ID=CLIENT, ADMIN_PWA_MCP_REDIRECT_URI=REDIRECT,
        )
        async with self.sessions() as db:
            db.add(User(id=1, telegram_id=9001, status="active"))
            await db.flush()
            db.add(AdminPwaSession(
                id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                user_id=1, token_hash=hashlib.sha256(COOKIE.encode()).hexdigest(),
                auth_method="webauthn", created_at=NOW,
                expires_at=NOW + timedelta(hours=6),
            ))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def start(self, *, session_cookie=COOKIE, client_id=CLIENT,
                    redirect_uri=REDIRECT, resource=RESOURCE, scope=SCOPE,
                    state=STATE, verifier=VERIFIER, method="S256", now=NOW,
                    csrf_proof=None):
        async with self.sessions() as db:
            pending = await begin_mcp_authorization(
                db, session_cookie=session_cookie, client_id=client_id,
                redirect_uri=redirect_uri, resource=resource, scope=scope,
                state=state, code_challenge=pkce_s256(verifier) or "bad",
                code_challenge_method=method, settings_obj=self.settings, now=now,
            )
            if pending is not None:
                self.csrf_by_id[pending.request_id] = pending.csrf_proof
            return pending

    async def decide(self, request_id, *, cookie=COOKIE, approved=True, now=NOW,
                     csrf_proof="__AUTO__"):
        if csrf_proof == "__AUTO__":
            csrf_proof = self.csrf_by_id.get(request_id)
        async with self.sessions() as db:
            return await decide_mcp_consent(
                db, request_id=request_id, session_cookie=cookie,
                approved=approved, settings_obj=self.settings, now=now,
                csrf_proof=csrf_proof,
            )

    async def redeem(self, code, *, verifier=VERIFIER, client_id=CLIENT,
                     redirect_uri=REDIRECT, resource=RESOURCE, now=NOW):
        async with self.sessions() as db:
            return await exchange_mcp_code(
                db, code=code, code_verifier=verifier, client_id=client_id,
                redirect_uri=redirect_uri, resource=resource,
                settings_obj=self.settings, now=now,
            )

    async def update_row(self, model, **changes):
        async with self.sessions() as db:
            row = (await db.execute(select(model))).scalar_one()
            for key, value in changes.items():
                setattr(row, key, value)
            await db.commit()

    async def test_explicit_consent_pkce_exchange_and_token_verification(self):
        pending = await self.start()
        self.assertEqual(pending.client_id, CLIENT)
        self.assertEqual(pending.redirect_uri, REDIRECT)
        async with self.sessions() as db:
            row = await db.get(AdminPwaMcpAuthorization, pending.request_id)
            self.assertEqual(row.status, "pending")
            self.assertIsNone(row.code_hash)
            self.assertEqual(row.scope, SCOPE)
            self.assertEqual(row.pkce_challenge, pkce_s256(VERIFIER))
        issued = await self.decide(pending.request_id)
        self.assertIsNotNone(issued)
        self.assertEqual(issued.redirect_uri, REDIRECT)
        self.assertEqual(issued.state, STATE)
        self.assertNotIn(COOKIE, issued.code)
        self.assertFalse(issued.code.startswith("__Host-"))
        async with self.sessions() as db:
            row = await db.get(AdminPwaMcpAuthorization, pending.request_id)
            self.assertEqual(row.code_hash, hashlib.sha256(issued.code.encode()).hexdigest())
            self.assertNotEqual(row.code_hash, issued.code)
        token = await self.redeem(issued.code)
        self.assertIsNotNone(token)
        self.assertEqual(token.expires_in, 300)
        self.assertEqual(token.token_type, "Bearer")
        async with self.sessions() as db:
            row = (await db.execute(select(AdminPwaMcpAccessGrant))).scalar_one()
            self.assertEqual(row.consent_event_id, pending.request_id)
            self.assertEqual(row.scope, SCOPE)
            self.assertEqual(row.audience, RESOURCE)
            self.assertEqual(row.token_hash, hashlib.sha256(token.token.encode()).hexdigest())
            actor = await verify_readonly_mcp_bearer(
                db, authorization="Bearer " + token.token, settings_obj=self.settings,
                now=NOW,
            )
            self.assertEqual(actor.admin_user_id, 1)
        self.assertIsNone(await self.redeem(issued.code))


    async def test_browser_consent_csrf_is_bound_to_pending_record_and_session(self):
        pending = await self.start()
        proof = pending.csrf_proof
        self.assertGreaterEqual(len(proof), 40)
        async with self.sessions() as db:
            row = await db.get(AdminPwaMcpAuthorization, pending.request_id)
            self.assertEqual(row.consent_csrf_hash,
                             hashlib.sha256(proof.encode()).hexdigest())
            self.assertNotEqual(row.consent_csrf_hash, proof)
        self.assertIsNone(await self.decide(pending.request_id, csrf_proof=None))
        self.assertIsNone(await self.decide(pending.request_id, csrf_proof="x"*64))
        self.assertIsNone(await self.decide(pending.request_id,
                                            cookie="X"*64, csrf_proof=proof))
        issued = await self.decide(pending.request_id, csrf_proof=proof)
        self.assertIsNotNone(issued)
        self.assertIsNotNone(await self.redeem(issued.code))
        self.assertIsNone(await self.decide(pending.request_id, csrf_proof=proof))

    async def test_wrong_browser_csrf_cannot_deny_consent(self):
        pending = await self.start()
        self.assertIsNone(await self.decide(pending.request_id,
                                            approved=False, csrf_proof="x"*64))
        denied = await self.decide(pending.request_id,
                                   approved=False, csrf_proof=pending.csrf_proof)
        self.assertEqual(denied.redirect_uri, REDIRECT)
        self.assertEqual(denied.state, STATE)
        async with self.sessions() as db:
            row = await db.get(AdminPwaMcpAuthorization, pending.request_id)
            self.assertEqual(row.status, "denied")
            self.assertIsNone(row.code_hash)

    async def test_missing_explicit_consent_and_denial_fail_closed(self):
        pending = await self.start()
        denied = await self.decide(pending.request_id, approved=False)
        self.assertEqual(denied.redirect_uri, REDIRECT)
        self.assertEqual(denied.state, STATE)
        self.assertIsNone(await self.decide(pending.request_id, approved=True))
        async with self.sessions() as db:
            record = await db.get(AdminPwaMcpAuthorization, pending.request_id)
            self.assertEqual(record.status, "denied")
            self.assertIsNone(record.code_hash)
            self.assertEqual((await db.execute(select(func.count()).select_from(
                AdminPwaMcpAccessGrant))).scalar_one(), 0)

    async def test_cross_browser_cookie_no_consent_or_code(self):
        pending = await self.start()
        self.assertIsNone(await self.decide(pending.request_id, cookie="X" * 64))
        self.assertIsNotNone(await self.decide(pending.request_id))
        self.assertIsNone(await self.decide(pending.request_id))

    async def test_wrong_pkce_verifier_does_not_consume_code(self):
        pending = await self.start()
        issued = await self.decide(pending.request_id)
        self.assertIsNone(await self.redeem(issued.code, verifier="b" * 64))
        self.assertIsNotNone(await self.redeem(issued.code))

    async def test_code_rejects_changed_client_redirect_resource(self):
        pending = await self.start()
        issued = await self.decide(pending.request_id)
        self.assertIsNone(await self.redeem(issued.code, client_id="evil-client"))
        self.assertIsNone(await self.redeem(issued.code, redirect_uri="https://evil.example"))
        self.assertIsNone(await self.redeem(issued.code, resource="https://evil.example/mcp"))
        self.assertIsNotNone(await self.redeem(issued.code))

    async def test_no_client_registration_or_weak_pkce_is_denied(self):
        for kwargs in (
            {"client_id": "other-client"},
            {"redirect_uri": "https://evil.example/callback"},
            {"resource": "https://evil.example/mcp"},
            {"scope": "admin:users:read"},
            {"scope": "admin:payments:write"},
            {"state": "too-short"},
            {"method": "plain"},
            {"verifier": "weak"},
            {"session_cookie": "X" * 64},
        ):
            with self.subTest(kwargs=kwargs):
                self.assertIsNone(await self.start(**kwargs))
        async with self.sessions() as db:
            self.assertEqual((await db.execute(select(func.count()).select_from(
                AdminPwaMcpAuthorization))).scalar_one(), 0)

    async def test_expiry_admin_revocation_and_logout_before_exchange(self):
        pending = await self.start()
        issued = await self.decide(pending.request_id)
        self.assertIsNone(await self.redeem(issued.code, now=NOW + timedelta(seconds=60)))
        self.settings.admin_id_list = []
        self.assertIsNone(await self.redeem(issued.code))
        self.settings.admin_id_list = [9001]
        await self.update_row(AdminPwaSession, revoked_at=NOW)
        self.assertIsNone(await self.redeem(issued.code))

    async def test_stale_consent_cannot_issue_code(self):
        pending = await self.start()
        self.assertIsNone(await self.decide(pending.request_id, now=NOW + timedelta(minutes=3)))
        self.assertIsNotNone(await self.decide(pending.request_id, now=NOW))

    async def test_two_independent_feature_flags_disable_all(self):
        self.settings.ADMIN_PWA_MCP_ENABLED = False
        self.assertIsNone(await self.start())
        self.settings.ADMIN_PWA_MCP_ENABLED = True
        self.settings.ADMIN_PWA_ENABLED = False
        self.assertIsNone(await self.start())
        self.settings.ADMIN_PWA_ENABLED = True
        self.settings.ADMIN_PWA_MCP_CLIENT_ID = ""
        self.assertIsNone(await self.start())
        self.settings.ADMIN_PWA_MCP_CLIENT_ID = CLIENT
        self.settings.ADMIN_PWA_MCP_REDIRECT_URI = "http://client.example/callback"
        self.assertIsNone(await self.start())

    async def test_start_count_is_capped_within_one_session(self):
        for _ in range(10):
            self.assertIsNotNone(await self.start())
        self.assertIsNone(await self.start())


if __name__ == "__main__":
    unittest.main()

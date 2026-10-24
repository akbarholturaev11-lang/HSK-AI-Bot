"""SQLite-backed consent history and revocation tests (no production access)."""
import hashlib
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.admin_api.pwa_mcp_management import (
    list_mcp_consent_history, revoke_mcp_consent,
)
from app.admin_api.pwa_mcp_oauth import (
    begin_mcp_authorization, decide_mcp_consent, exchange_mcp_code, pkce_s256,
)
from app.admin_api.pwa_mcp_resource import verify_readonly_mcp_bearer
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_mcp import AdminPwaMcpAccessGrant
from app.db.models.admin_pwa_mcp_authorization import AdminPwaMcpAuthorization
from app.db.models.user import User

NOW = datetime(2026, 10, 24, 14, tzinfo=timezone.utc)
RESOURCE = "https://hskai.app/mcp"
COOKIE = "S" * 64
OTHER_COOKIE = "O" * 64
CLIENT = "registered-chatgpt-client"
REDIRECT = "https://chatgpt.example.com/callback"
VERIFIER = "v" * 64
STATE = "state-" + "x" * 44


class McpConsentManagementTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            for model in (User, AdminPwaSession, AdminPwaMcpAuthorization,
                          AdminPwaMcpAccessGrant):
                await connection.run_sync(model.__table__.create)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.settings = SimpleNamespace(
            ADMIN_PWA_ENABLED=True, ADMIN_PWA_MCP_ENABLED=True,
            ADMIN_PWA_MCP_RESOURCE=RESOURCE, admin_id_list=[9001, 9002],
            ADMIN_PWA_MCP_CLIENT_ID=CLIENT,
            ADMIN_PWA_MCP_REDIRECT_URI=REDIRECT,
        )
        async with self.sessions() as db:
            db.add_all([
                User(id=1, telegram_id=9001, status="active"),
                User(id=2, telegram_id=9002, status="active"),
            ])
            await db.flush()
            for user_id, cookie, identifier in (
                (1, COOKIE, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                (2, OTHER_COOKIE, "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            ):
                db.add(AdminPwaSession(
                    id=identifier, user_id=user_id,
                    token_hash=hashlib.sha256(cookie.encode()).hexdigest(),
                    auth_method="webauthn", created_at=NOW,
                    expires_at=NOW + timedelta(hours=6),
                ))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def create_consent(self, *, approved=True):
        async with self.sessions() as db:
            pending = await begin_mcp_authorization(
                db, session_cookie=COOKIE, client_id=CLIENT,
                redirect_uri=REDIRECT, resource=RESOURCE,
                scope="admin:analytics:read", state=STATE,
                code_challenge=pkce_s256(VERIFIER),
                code_challenge_method="S256",
                settings_obj=self.settings, now=NOW)
        if not approved:
            return pending, None
        async with self.sessions() as db:
            code = await decide_mcp_consent(
                db, request_id=pending.request_id,
                session_cookie=COOKIE, approved=True,
                csrf_proof=pending.csrf_proof,
                settings_obj=self.settings, now=NOW)
        return pending, code

    async def history(self, cookie=COOKIE):
        async with self.sessions() as db:
            return await list_mcp_consent_history(
                db, session_cookie=cookie,
                settings_obj=self.settings, now=NOW)

    async def revoke(self, identifier, cookie=COOKIE):
        async with self.sessions() as db:
            return await revoke_mcp_consent(
                db, authorization_id=identifier, session_cookie=cookie,
                settings_obj=self.settings, now=NOW)

    async def test_issued_token_is_revoked_and_metadata_has_no_secrets(self):
        pending, code = await self.create_consent()
        async with self.sessions() as db:
            token = await exchange_mcp_code(
                db, code=code.code, code_verifier=VERIFIER,
                client_id=CLIENT, redirect_uri=REDIRECT, resource=RESOURCE,
                settings_obj=self.settings, now=NOW)
        self.assertIsNotNone(token)
        history = await self.history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["id"], pending.request_id)
        self.assertTrue(history[0]["active_access"])
        self.assertEqual(history[0]["scope"], "admin:analytics:read")
        self.assertNotIn(COOKIE, str(history))
        self.assertNotIn(token.token, str(history))
        self.assertNotIn(code.code, str(history))
        self.assertNotIn(STATE, str(history))
        self.assertTrue(await self.revoke(pending.request_id))
        self.assertTrue(await self.revoke(pending.request_id))
        self.assertEqual((await self.history())[0]["status"], "revoked")
        self.assertFalse((await self.history())[0]["active_access"])
        async with self.sessions() as db:
            actor = await verify_readonly_mcp_bearer(
                db, authorization="Bearer " + token.token,
                settings_obj=self.settings, now=NOW)
            self.assertIsNone(actor)
            authorization = await db.get(AdminPwaMcpAuthorization,
                                         pending.request_id)
            self.assertIsNone(authorization.code_hash)

    async def test_revocation_invalidates_unredeemed_one_time_code(self):
        pending, code = await self.create_consent()
        self.assertTrue(await self.revoke(pending.request_id))
        async with self.sessions() as db:
            token = await exchange_mcp_code(
                db, code=code.code, code_verifier=VERIFIER,
                client_id=CLIENT, redirect_uri=REDIRECT, resource=RESOURCE,
                settings_obj=self.settings, now=NOW)
        self.assertIsNone(token)

    async def test_pending_consent_can_be_cancelled(self):
        pending, _ = await self.create_consent(approved=False)
        self.assertTrue(await self.revoke(pending.request_id))
        async with self.sessions() as db:
            decision = await decide_mcp_consent(
                db, request_id=pending.request_id, session_cookie=COOKIE,
                approved=True, csrf_proof=pending.csrf_proof,
                settings_obj=self.settings, now=NOW)
        self.assertIsNone(decision)

    async def test_cross_admin_session_and_killswitch_fail_closed(self):
        pending, _ = await self.create_consent(approved=False)
        self.assertEqual(await self.history(cookie=OTHER_COOKIE), [])
        self.assertFalse(await self.revoke(pending.request_id, OTHER_COOKIE))
        self.assertFalse(await self.revoke("not-a-uuid"))
        self.assertEqual((await self.history())[0]["status"], "pending")
        self.settings.ADMIN_PWA_MCP_ENABLED = False
        self.assertIsNone(await self.history())
        self.assertFalse(await self.revoke(pending.request_id))
        self.settings.ADMIN_PWA_MCP_ENABLED = True
        self.settings.admin_id_list = []
        self.assertIsNone(await self.history())
        self.assertFalse(await self.revoke(pending.request_id))


if __name__ == "__main__":
    unittest.main()

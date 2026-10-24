"""Real SQLite DB tests for unexposed, scoped MCP OAuth resource verifier.

The fixtures simulate an access grant from a future consented OAuth issuer.
That issuer, PKCE, HTTP MCP transport and token minting are NOT built here.
"""
import hashlib
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.admin_api.pwa_mcp_resource import (
    McpBearerDenied, McpBearerBadArguments,
    verify_readonly_mcp_bearer, read_mcp_statistics_with_verified_token,
)
from app.db.models.admin_pwa_mcp import AdminPwaMcpAccessGrant
from app.db.models.user import User

NOW = datetime.now(timezone.utc)
TOKEN = "M" * 64
RESOURCE = "https://hskai.app/mcp"
SCOPE = "admin:analytics:read"
GRANT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


class McpResourceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(User.__table__.create)
            await conn.run_sync(AdminPwaMcpAccessGrant.__table__.create)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.settings = SimpleNamespace(
            ADMIN_PWA_ENABLED=True, ADMIN_PWA_MCP_ENABLED=True,
            ADMIN_PWA_MCP_RESOURCE=RESOURCE, admin_id_list=[9001],
        )
        async with self.sessions() as db:
            db.add(User(id=1001, telegram_id=9001, status="active"))
            await db.flush()
            db.add(AdminPwaMcpAccessGrant(
                id=GRANT_ID, user_id=1001,
                token_hash=hashlib.sha256(TOKEN.encode("ascii")).hexdigest(),
                audience=RESOURCE, client_id="registered-chatgpt-test-client",
                consent_event_id=str(uuid4()),
                scope=SCOPE, created_at=NOW - timedelta(seconds=5),
                expires_at=NOW + timedelta(minutes=3),
            ))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def verify(self, token=TOKEN, *, time=NOW):
        async with self.sessions() as db:
            return await verify_readonly_mcp_bearer(
                db, authorization="Bearer " + token,
                settings_obj=self.settings, now=time,
            )

    async def change(self, cls, **attributes):
        async with self.sessions() as db:
            row = (await db.execute(select(cls))).scalar_one()
            for key, value in attributes.items():
                setattr(row, key, value)
            await db.commit()

    async def test_exact_resource_scope_hash_admin_and_consent(self):
        actor = await self.verify()
        self.assertEqual(actor.admin_user_id, 1001)
        self.assertEqual(actor.scope, SCOPE)
        self.assertEqual(actor.grant_id, GRANT_ID)
        self.assertNotEqual(
            self._hash(TOKEN), TOKEN,
        )

    @staticmethod
    def _hash(token):
        return hashlib.sha256(token.encode()).hexdigest()

    async def test_token_is_never_browser_cookie_or_arbitrary_client_value(self):
        async with self.sessions() as db:
            for header in (
                TOKEN, "bearer " + TOKEN, "Bearer ", "Basic " + TOKEN,
                "Bearer " + ("X" * 64), "Bearer " + TOKEN + "\n",
                "Bearer __Host-hskai_admin=" + TOKEN,
            ):
                with self.subTest(header=header[:20]):
                    self.assertIsNone(await verify_readonly_mcp_bearer(
                        db, authorization=header, settings_obj=self.settings, now=NOW,
                    ))

    async def test_scope_audience_and_client_mismatch_fail_closed(self):
        for cls, values in (
            (AdminPwaMcpAccessGrant, {"scope": "admin:users:read"}),
            (AdminPwaMcpAccessGrant, {"scope": "admin:payments:write"}),
            (AdminPwaMcpAccessGrant, {"audience": "https://attacker.example/mcp"}),
            (AdminPwaMcpAccessGrant, {"client_id": ""}),
            (AdminPwaMcpAccessGrant, {"consent_event_id": "forged"}),
        ):
            with self.subTest(values=values):
                async with self.sessions() as db:
                    row = (await db.execute(select(cls))).scalar_one()
                    original = {k: getattr(row, k) for k in values}
                    for k, value in values.items():
                        setattr(row, k, value)
                    await db.commit()
                self.assertIsNone(await self.verify())
                await self.change(cls, **original)

    async def test_revocation_expiration_and_suspicious_ttl(self):
        await self.change(AdminPwaMcpAccessGrant, revoked_at=NOW)
        self.assertIsNone(await self.verify())
        await self.change(AdminPwaMcpAccessGrant, revoked_at=None)
        self.assertIsNone(await self.verify(time=NOW + timedelta(minutes=3)))
        await self.change(AdminPwaMcpAccessGrant, expires_at=NOW + timedelta(minutes=7))
        self.assertIsNone(await self.verify())
        await self.change(AdminPwaMcpAccessGrant, expires_at=NOW + timedelta(minutes=2))
        self.assertIsNotNone(await self.verify())

    async def test_current_admin_block_and_disabled_killswitch(self):
        self.settings.ADMIN_PWA_ENABLED = False
        self.assertIsNone(await self.verify())
        self.settings.ADMIN_PWA_ENABLED = True
        self.settings.ADMIN_PWA_MCP_ENABLED = False
        self.assertIsNone(await self.verify())
        self.settings.ADMIN_PWA_MCP_ENABLED = True
        self.settings.ADMIN_PWA_MCP_RESOURCE = "https://hskai.app/wrong"
        self.assertIsNone(await self.verify())
        self.settings.ADMIN_PWA_MCP_RESOURCE = RESOURCE
        self.settings.admin_id_list = []
        self.assertIsNone(await self.verify())
        self.settings.admin_id_list = [9001]
        await self.change(User, status="BLOCKED")
        self.assertIsNone(await self.verify())

    async def test_read_projection_uses_only_verified_bearer(self):
        events = []

        async def fake_statistics(db, query):
            events.append(("statistics", query.platform))
            return {"available": True, "metrics": {"users_total": 4}}

        with patch("app.admin_api.pwa_mcp_resource.statistics", new=fake_statistics):
            async with self.sessions() as db:
                result = await read_mcp_statistics_with_verified_token(
                    db, authorization="Bearer " + TOKEN,
                    args={"platform": "overall", "period": "weekly"},
                    settings_obj=self.settings,
                )
        self.assertEqual(events, [("statistics", "overall")])
        self.assertEqual(result["data"]["metrics"]["users_total"], 4)
        self.assertNotIn(TOKEN, str(result))

    async def test_denied_call_cannot_reach_data_layer(self):
        touched = []

        async def fake_statistics(db, query):
            touched.append(query)
            return {}

        with patch("app.admin_api.pwa_mcp_resource.statistics", new=fake_statistics):
            async with self.sessions() as db:
                with self.assertRaises(McpBearerDenied):
                    await read_mcp_statistics_with_verified_token(
                        db, authorization="Bearer " + "X" * 64,
                        args={}, settings_obj=self.settings,
                    )
        self.assertEqual(touched, [])

    async def test_unvalidated_queries_and_mutations_not_exposed(self):
        for args in (
            {"sql": "UPDATE users SET status='pro'"},
            {"user_id": 1001},
            {"period": "unknown"},
            {"platform": "ios"},
        ):
            async with self.sessions() as db:
                with self.subTest(args=args):
                    with self.assertRaises(McpBearerBadArguments):
                        await read_mcp_statistics_with_verified_token(
                            db, authorization="Bearer " + TOKEN,
                            args=args, settings_obj=self.settings,
                        )


if __name__ == "__main__":
    unittest.main()

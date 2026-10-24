"""Actual database admission/audit, privacy, retention and fail-shut transport."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.admin_api.pwa_mcp_http import create_admin_pwa_mcp_http_router
from app.admin_api.pwa_mcp_security import (
    admit_mcp_http, consume_mcp_quota, finish_mcp_http,
)
from app.db.models.user import User
from app.db.models.admin_pwa_mcp_security import AdminPwaMcpAudit, AdminPwaMcpQuota

NOW = datetime(2026, 10, 24, 10, 0, 30, tzinfo=timezone.utc)


class McpSecurityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with self.engine.begin() as conn:
            for model in (User, AdminPwaMcpAudit, AdminPwaMcpQuota):
                await conn.run_sync(model.__table__.create)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def admit(self, now=NOW):
        async with self.sessions() as db:
            return await admit_mcp_http(db, action='mcp_post', now=now)

    async def test_shared_budget_saturates_and_only_first_denial_is_audited(self):
        with patch('app.admin_api.pwa_mcp_security._LIMITS', {'mcp_post': 2}):
            self.assertTrue((await self.admit())[0])
            self.assertTrue((await self.admit())[0])
            allowed, ticket, retry = await self.admit()
            self.assertFalse(allowed)
            self.assertIsNotNone(ticket)
            self.assertEqual(retry, 30)
            self.assertEqual(await self.admit(), (False, None, 30))
            self.assertTrue((await self.admit(NOW + timedelta(seconds=30)))[0])
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaMcpQuota)), 1)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaMcpAudit)), 4)

    async def test_retention_is_bounded_and_no_payload_or_credentials_can_be_persisted(self):
        async with self.sessions() as db:
            db.add_all([AdminPwaMcpAudit(
                id=str(uuid4()), action='token', outcome='completed', status_code=200,
                created_at=NOW - timedelta(days=8),
            ) for _ in range(110)])
            await db.commit()
        _, identifier, _ = await self.admit()
        async with self.sessions() as db:
            await finish_mcp_http(db, identifier=identifier, action='attacker-secret',
                                  status_code=400, admin_user_id=None)
        async with self.sessions() as db:
            rows = (await db.scalars(select(AdminPwaMcpAudit))).all()
            self.assertEqual(len(rows), 11)
            row = await db.get(AdminPwaMcpAudit, identifier)
            self.assertEqual(row.action, 'unknown')
            self.assertEqual(row.outcome, 'rejected')
            self.assertEqual(set(row.__table__.columns.keys()), {
                'id', 'action', 'outcome', 'status_code', 'admin_user_id', 'created_at'})

    async def test_verified_admin_bucket_is_shared_across_tokens(self):
        async def quota(key):
            async with self.sessions() as db, db.begin():
                return await consume_mcp_quota(db, key=key, limit=1, now=NOW)
        self.assertTrue((await quota('admin:1:statistics'))[0])
        self.assertFalse((await quota('admin:1:statistics'))[0])
        self.assertTrue((await quota('admin:2:statistics'))[0])

    async def test_real_http_audit_precedes_read_and_db_failure_blocks_execution(self):
        settings = SimpleNamespace(
            ADMIN_PWA_ENABLED=True, ADMIN_PWA_MCP_ENABLED=True,
            ADMIN_PWA_MCP_TRANSPORT_ENABLED=True,
            ADMIN_PWA_MCP_RESOURCE='https://hskai.app/mcp',
            ADMIN_PWA_MCP_CLIENT_ID='registered',
            ADMIN_PWA_MCP_REDIRECT_URI='https://client.example/cb')
        async with self.sessions() as db:
            db.add(User(id=1, telegram_id=9001, status='active'))
            await db.commit()
        calls = []
        async def verify(db, **kwargs):
            return SimpleNamespace(admin_user_id=1)
        async def read(db, **kwargs):
            rows = (await db.scalars(select(AdminPwaMcpAudit))).all()
            self.assertTrue(any(row.outcome == 'started' for row in rows))
            calls.append(1)
            return {'data': {'available': True}}
        app = FastAPI()
        app.include_router(create_admin_pwa_mcp_http_router(
            settings_obj=settings, session_factory=self.sessions,
            verify_service=verify, read_service=read))
        async with AsyncClient(transport=ASGITransport(app=app), base_url='https://hskai.app') as client:
            payload = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                       'params': {'name': 'hskai_statistics', 'arguments': {}}}
            headers = {'authorization': 'Bearer ' + 'B'*64,
                       'accept': 'application/json, text/event-stream',
                       'mcp-protocol-version': '2025-11-25'}
            with patch('app.admin_api.pwa_mcp_security._STATISTICS_PER_ADMIN', 1):
                self.assertEqual((await client.post('/mcp', json=payload, headers=headers)).status_code, 200)
                limited = await client.post('/mcp', json=payload, headers=headers)
                self.assertEqual(limited.status_code, 429)
                self.assertIn('retry-after', limited.headers)
            async with self.engine.begin() as conn:
                await conn.run_sync(AdminPwaMcpQuota.__table__.drop)
            self.assertEqual((await client.post('/mcp', json=payload, headers=headers)).status_code, 503)
            settings.ADMIN_PWA_MCP_ENABLED = False
            self.assertEqual((await client.post('/mcp', json=payload, headers=headers)).status_code, 404)
        self.assertEqual(calls, [1])
        async with self.sessions() as db:
            rows = (await db.scalars(select(AdminPwaMcpAudit))).all()
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(row.action == 'tools/call' and row.admin_user_id == 1 for row in rows))
            self.assertCountEqual([row.status_code for row in rows], [200, 429])


if __name__ == '__main__':
    unittest.main()

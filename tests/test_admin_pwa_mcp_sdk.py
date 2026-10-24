"""Official SDK compatibility against real OAuth/MCP ASGI + disposable SQLite.

QA-only mcp==1.27.0; no runtime dependency, external host or real ChatGPT.
"""
import hashlib
import re
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
pytest.importorskip('mcp', reason='official MCP SDK is an isolated CI QA dependency')
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.admin_api.pwa_mcp_consent_transport import create_admin_pwa_mcp_consent_router
from app.admin_api.pwa_mcp_http import create_admin_pwa_mcp_http_router
from app.admin_api.pwa_mcp_management import create_admin_pwa_mcp_management_router
from app.admin_api.pwa_mcp_oauth import pkce_s256
from app.db.base import Base
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_mcp_security import AdminPwaMcpAudit
from app.db.models.user import User

ORIGIN = 'https://hskai.app'
COOKIE = 'S'*64
VERIFIER = 'v'*64


class McpSdkCompatibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_oauth_sdk_statistics_and_owner_revocation(self):
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            settings = SimpleNamespace(
                ADMIN_PWA_ENABLED=True, ADMIN_PWA_MCP_ENABLED=True,
                ADMIN_PWA_MCP_TRANSPORT_ENABLED=True, ADMIN_PWA_PUBLIC_ORIGIN=ORIGIN,
                ADMIN_PWA_MCP_RESOURCE=ORIGIN+'/mcp', admin_id_list=[9001],
                ADMIN_PWA_MCP_CLIENT_ID='synthetic-sdk-client',
                ADMIN_PWA_MCP_REDIRECT_URI='https://registered-client.example/callback')
            async with sessions() as db:
                db.add(User(id=1, telegram_id=9001, status='active'))
                await db.flush()
                now = datetime.now(timezone.utc)
                db.add(AdminPwaSession(id=str(uuid4()), user_id=1,
                    token_hash=hashlib.sha256(COOKIE.encode()).hexdigest(),
                    auth_method='webauthn', created_at=now, expires_at=now+timedelta(hours=1)))
                await db.commit()
            app = FastAPI()
            for factory in (create_admin_pwa_mcp_consent_router, create_admin_pwa_mcp_http_router,
                            create_admin_pwa_mcp_management_router):
                app.include_router(factory(settings_obj=settings, session_factory=sessions))
            transport = ASGITransport(app=app)
            browser_headers = {'cookie':'__Host-hskai_admin='+COOKIE,
                               'origin':ORIGIN, 'sec-fetch-site':'same-origin'}
            async with AsyncClient(transport=transport, base_url=ORIGIN) as client:
                consent = await client.get('/oauth/authorize', params={
                    'response_type':'code', 'client_id':settings.ADMIN_PWA_MCP_CLIENT_ID,
                    'redirect_uri':settings.ADMIN_PWA_MCP_REDIRECT_URI,
                    'resource':ORIGIN+'/mcp', 'scope':'admin:analytics:read',
                    'state':'state-'+'s'*44, 'code_challenge':pkce_s256(VERIFIER),
                    'code_challenge_method':'S256'}, headers=browser_headers)
                self.assertEqual(consent.status_code, 200)
                identifier = re.search(r'name="request_id" value="([^"]+)"', consent.text).group(1)
                csrf = re.search(r'name="csrf" value="([^"]+)"', consent.text).group(1)
                approved = await client.post('/oauth/authorize', data={
                    'request_id':identifier, 'csrf':csrf, 'decision':'allow'}, headers=browser_headers)
                self.assertEqual(approved.status_code, 303)
                callback = parse_qs(urlsplit(approved.headers['location']).query)
                self.assertEqual(callback['iss'], [ORIGIN])
                token_form = {'grant_type':'authorization_code', 'code':callback['code'][0],
                              'code_verifier':VERIFIER, 'client_id':settings.ADMIN_PWA_MCP_CLIENT_ID,
                              'redirect_uri':settings.ADMIN_PWA_MCP_REDIRECT_URI, 'resource':ORIGIN+'/mcp'}
                issued = await client.post('/oauth/token', data=token_form)
                self.assertEqual(issued.status_code, 200)
                self.assertEqual((await client.post('/oauth/token', data=token_form)).status_code, 400)
                token = issued.json()['access_token']
                sdk_http = AsyncClient(transport=transport, headers={'Authorization':'Bearer '+token})
                async with sdk_http, streamable_http_client(ORIGIN+'/mcp',
                    http_client=sdk_http) as (read, write, _):
                    async with ClientSession(read, write) as sdk:
                        initialized = await sdk.initialize()
                        self.assertIn(initialized.protocolVersion, ('2025-06-18','2025-11-25'))
                        tools = await sdk.list_tools()
                        self.assertEqual([tool.name for tool in tools.tools], ['hskai_statistics'])
                        result = await sdk.call_tool('hskai_statistics', {'platform':'overall'})
                        self.assertFalse(result.isError)
                        self.assertEqual(result.structuredContent['metrics']['users_total'], 1)
                revoked = await client.post('/api/admin/v1/mcp/authorizations/revoke',
                    json={'authorization_id':identifier}, headers=browser_headers)
                self.assertEqual(revoked.status_code, 200)
                denied = await client.post('/mcp', json={'jsonrpc':'2.0','id':9,'method':'tools/list'}, headers={
                    'authorization':'Bearer '+token, 'accept':'application/json, text/event-stream',
                    'mcp-protocol-version':'2025-11-25'})
                self.assertEqual(denied.status_code, 401)
                self.assertIn('invalid_token', denied.headers['www-authenticate'])
            async with sessions() as db:
                rows = (await db.scalars(select(AdminPwaMcpAudit))).all()
                self.assertTrue({'consent_approved','token_issued','tools/call','consent_revoked'}.issubset(
                    {row.action for row in rows if row.admin_user_id == 1}))
        finally:
            await engine.dispose()

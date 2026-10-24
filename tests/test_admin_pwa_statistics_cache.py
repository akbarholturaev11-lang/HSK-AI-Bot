"""Daily aggregate reuse, coordinated misses and fresh authorization on hits."""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import event

from app.admin_api.pwa_mcp_resource import McpBearerDenied, read_mcp_statistics_with_verified_token
from app.admin_api.pwa_read import StatisticsRequest, create_admin_pwa_read_router
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.admin_api.pwa_statistics_cache import AdminPwaStatisticsReader, SNAPSHOT_SECONDS, StatisticsUnavailable
from app.db.models.admin_pwa_mcp import AdminPwaMcpAccessGrant
from app.db.models.payment import Payment
from app.db.models.user import User
from tests import test_admin_pwa_payment_review as fixtures


class StatisticsCacheFixtures:
    def setUp(self):
        self.clock = datetime.now(timezone.utc).timestamp()
        self.calls = 0
        self.settings = SimpleNamespace(ADMIN_PWA_ENABLED=True)
        self.reader = AdminPwaStatisticsReader(settings_obj=self.settings, session_factory=self.sessions,
            loader=self.load, clock=lambda: self.clock)

    @asynccontextmanager
    async def transaction(self):
        # The unit loader does no SQL; integration cases below use real SQL.
        yield

    async def load(self, db, query):
        self.calls += 1
        await asyncio.sleep(.01)
        return {"platform": query.platform, "period": query.period, "available": True,
                "generated_at": datetime.fromtimestamp(self.clock, timezone.utc).isoformat(),
                "metrics": {"users_total": self.calls}}

    @asynccontextmanager
    async def sessions(self):
        yield SimpleNamespace(begin=self.transaction,
            get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="sqlite")))


class StatisticsCacheTests(StatisticsCacheFixtures, unittest.IsolatedAsyncioTestCase):
    async def test_simultaneous_requests_compute_once_and_snapshot_is_reused_for_24_hours(self):
        results = await asyncio.gather(*(self.reader(StatisticsRequest()) for _ in range(20)))
        self.assertEqual(self.calls, 1)
        self.assertTrue(all(row["metrics"]["users_total"] == 1 for row in results))
        results[0]["metrics"]["users_total"] = 999
        self.clock += SNAPSHOT_SECONDS-1
        self.assertEqual((await self.reader(StatisticsRequest()))["metrics"]["users_total"], 1)
        self.assertEqual(self.calls, 1)
        self.clock += 2
        self.assertEqual((await self.reader(StatisticsRequest()))["metrics"]["users_total"], 2)
        self.assertEqual(self.calls, 2)

    async def test_variants_are_separate_no_unrequested_refresh_and_disabled_warm_cache_is_denied(self):
        for args in ({}, {"period": "monthly"}, {"platform": "android"}):
            await self.reader(StatisticsRequest(**args))
        self.assertEqual(self.calls, 3)
        self.assertEqual(len(self.reader._local), 3)
        self.settings.ADMIN_PWA_ENABLED = False
        with self.assertRaises(StatisticsUnavailable):
            await self.reader(StatisticsRequest())
        self.assertEqual(self.calls, 3)

    async def test_failed_refresh_is_not_retried_per_request(self):
        self.reader.loader = AsyncMock(side_effect=ValueError("private diagnostic"))
        for _ in range(5):
            with self.assertRaisesRegex(StatisticsUnavailable, "unavailable|cooling"):
                await self.reader(StatisticsRequest())
        self.assertEqual(self.reader.loader.await_count, 1)
        self.assertEqual(self.reader._local, {})
        self.clock += 31
        with self.assertRaises(StatisticsUnavailable):
            await self.reader(StatisticsRequest())
        self.assertEqual(self.reader.loader.await_count, 2)

    async def test_shared_failure_falls_back_to_one_local_daily_snapshot(self):
        self.reader._client = SimpleNamespace(getrange=AsyncMock(side_effect=OSError("private Redis URL")))
        for _ in range(10):
            self.assertEqual((await self.reader(StatisticsRequest()))["metrics"]["users_total"], 1)
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.reader._client.getrange.await_count, 1)

    async def test_timed_out_loader_cools_down_without_repeated_sql(self):
        async def slow(db, query):
            self.calls += 1
            await asyncio.sleep(.1)
        self.reader.loader = slow
        with patch("app.admin_api.pwa_statistics_cache._LOAD_SECONDS", .01):
            for _ in range(2):
                with self.assertRaises(StatisticsUnavailable):
                    await self.reader(StatisticsRequest())
        self.assertEqual(self.calls, 1)

    async def test_corrupt_foreign_oversized_and_expired_shared_values_are_rejected(self):
        _, envelope = await self.reader._compute(StatisticsRequest())
        for raw in (b"not-json", b"x"*(128*1024+1), b"NaN", b"[]",
                    json.dumps(envelope | {"version": 2}).encode(),
                    json.dumps(envelope | {"expires_at": self.clock}).encode(),
                    json.dumps(envelope | {"data": envelope["data"] | {"period": "monthly"}}).encode(),
                    json.dumps(envelope | {"data": envelope["data"] | {"users": [{"name": "private"}]}}).encode()):
            self.assertIsNone(self.reader._decode(raw, StatisticsRequest()))


class StatisticsCacheIntegrationTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    def app(self, reader):
        app = FastAPI()
        app.include_router(create_admin_pwa_read_router(settings_obj=self.settings,
            session_factory=self.sessions, statistics_reader=reader))
        return app

    def client(self, app):
        return AsyncClient(transport=ASGITransport(app=app), base_url="https://hskai.app",
            headers={"origin": "https://hskai.app"}, cookies={ADMIN_PWA_COOKIE_NAME: fixtures.COOKIE})

    async def test_warm_browser_and_mcp_share_one_aggregate_but_revalidate_each_actor(self):
        reader = AdminPwaStatisticsReader(settings_obj=self.settings, session_factory=self.sessions)
        aggregate_queries = []
        def observe(conn, cursor, statement, parameters, context, many):
            if "FROM ai_usage_events" in statement:
                aggregate_queries.append(statement)
        event.listen(self.engine.sync_engine, "before_cursor_execute", observe)
        try:
            async with self.client(self.app(reader)) as client:
                first = await client.post("/api/admin/v1/statistics", json={})
                self.assertEqual(first.status_code, 200, first.text)
                second = await client.post("/api/admin/v1/statistics", json={})
                self.assertEqual(first.json(), second.json())
                self.assertEqual(first.json()["snapshot"]["refresh_interval_seconds"], 86400)
                self.assertEqual((await client.post("/api/admin/v1/statistics", json={},
                    headers={"origin": "https://untrusted.example"})).status_code, 403)
                token = "R"*64
                self.settings.ADMIN_PWA_MCP_ENABLED = True
                self.settings.ADMIN_PWA_MCP_RESOURCE = "https://hskai.app/mcp"
                async with self.sessions() as db:
                    now = datetime.now(timezone.utc)
                    grant = AdminPwaMcpAccessGrant(id=str(uuid4()), user_id=101,
                        token_hash=hashlib.sha256(token.encode()).hexdigest(), audience="https://hskai.app/mcp",
                        client_id="synthetic-cache-client", consent_event_id=str(uuid4()), scope="admin:analytics:read",
                        created_at=now, expires_at=now+timedelta(minutes=3))
                    db.add(grant)
                    await db.commit()
                    grant_id = grant.id
                async with self.sessions() as db:
                    mcp = await read_mcp_statistics_with_verified_token(db, authorization="Bearer "+token,
                        args={}, settings_obj=self.settings, statistics_reader=reader)
                self.assertEqual(mcp["data"], {key: value for key, value in first.json().items() if key != "ok"})
                self.assertEqual(len(aggregate_queries), 1)
                async with self.sessions() as db:
                    (await db.get(AdminPwaMcpAccessGrant, grant_id)).revoked_at = datetime.now(timezone.utc)
                    await db.commit()
                async with self.sessions() as db:
                    with self.assertRaises(McpBearerDenied):
                        await read_mcp_statistics_with_verified_token(db, authorization="Bearer "+token,
                            args={}, settings_obj=self.settings, statistics_reader=reader)
                self.assertEqual((await client.post("/api/admin/v1/statistics", json={})).status_code, 200)
                async with self.sessions() as db:
                    grant = await db.get(AdminPwaMcpAccessGrant, grant_id)
                    grant.revoked_at = None
                    grant.expires_at = datetime.now(timezone.utc)-timedelta(seconds=1)
                    await db.commit()
                async with self.sessions() as db:
                    with self.assertRaises(McpBearerDenied):
                        await read_mcp_statistics_with_verified_token(db, authorization="Bearer "+token,
                            args={}, settings_obj=self.settings, statistics_reader=reader)
                async with self.sessions() as db:
                    (await db.get(User, 101)).status = "blocked"
                    await db.commit()
                denied = await client.post("/api/admin/v1/statistics", json={})
                self.assertEqual(denied.status_code, 401)
                self.assertEqual(len(aggregate_queries), 1)
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", observe)

    async def test_billing_and_access_reads_remain_current_while_dashboard_is_daily(self):
        reader = AdminPwaStatisticsReader(settings_obj=self.settings, session_factory=self.sessions)
        async with self.client(self.app(reader)) as client:
            first = (await client.post("/api/admin/v1/statistics", json={})).json()
            async with self.sessions() as db:
                (await db.get(Payment, self.payment_id)).amount = 150
                user = await db.get(User, 1)
                user.status = "active"
                user.payment_status = "approved"
                user.end_date = datetime.now(timezone.utc)+timedelta(days=3)
                await db.commit()
            self.assertEqual((await client.post("/api/admin/v1/statistics", json={})).json(), first)
            payments = (await client.post("/api/admin/v1/payments/list", json={})).json()
            self.assertEqual(payments["items"][0]["amount"], 150)
            profile = (await client.post("/api/admin/v1/users/detail", json={"user_id": 1})).json()
            self.assertEqual(profile["user"]["access_state"], "PRO_ACTIVE")

    async def test_auth_transaction_is_closed_before_cache_lookup(self):
        active = []
        @asynccontextmanager
        async def sessions():
            async with self.sessions() as db:
                active.append(db)
                try:
                    yield db
                finally:
                    active.remove(db)
        async def reader(query):
            self.assertEqual(active, [])
            return {"available": False, "metrics": None}
        app = FastAPI()
        app.include_router(create_admin_pwa_read_router(settings_obj=self.settings,
            session_factory=sessions, statistics_reader=reader))
        async with self.client(app) as client:
            self.assertEqual((await client.post("/api/admin/v1/statistics", json={})).status_code, 200)


@unittest.skipUnless(os.environ.get("ADMIN_PWA_TEST_REDIS_URL"), "requires isolated test Redis")
class StatisticsRedisTests(StatisticsCacheFixtures, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.namespace = "qa-"+uuid4().hex
        self.clients = [Redis.from_url(os.environ["ADMIN_PWA_TEST_REDIS_URL"]) for _ in range(2)]
        self.readers = [AdminPwaStatisticsReader(settings_obj=self.settings, session_factory=self.sessions,
            loader=self.load, redis_client=client, namespace=self.namespace, clock=lambda: self.clock)
            for client in self.clients]

    async def asyncTearDown(self):
        # Delete only keys in this test's UUID namespace; never flush Redis.
        keys = [key async for key in self.clients[0].scan_iter(match=self.readers[0].prefix+":*")]
        if keys:
            await self.clients[0].delete(*keys)
        for client in self.clients:
            await client.aclose()

    async def test_multiple_workers_share_one_refresh_and_restart_reuses_daily_snapshot(self):
        results = await asyncio.gather(*(self.readers[index % 2](StatisticsRequest()) for index in range(20)))
        self.assertEqual(self.calls, 1)
        self.assertTrue(all(row == results[0] for row in results))
        self.readers[0]._local.clear()
        self.assertEqual(await self.readers[0](StatisticsRequest()), results[0])
        self.assertEqual(self.calls, 1)

    async def test_configured_url_creates_async_client_lazily(self):
        settings = SimpleNamespace(ADMIN_PWA_ENABLED=True, REDIS_URL=os.environ["ADMIN_PWA_TEST_REDIS_URL"])
        reader = AdminPwaStatisticsReader(settings_obj=settings, session_factory=self.sessions,
            loader=self.load, namespace=self.namespace, clock=lambda: self.clock)
        self.assertIsNone(reader._client)
        try:
            await reader(StatisticsRequest())
            self.assertIsNotNone(reader._client)
            self.assertEqual(self.calls, 1)
            self.assertTrue(await self.clients[0].get(reader.prefix+":overall:weekly"))
        finally:
            await reader.aclose()

    async def test_different_variants_do_not_run_heavy_loaders_at_the_same_time(self):
        active = peak = 0
        async def load(db, query):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            try:
                return await self.load(db, query)
            finally:
                active -= 1
        for reader in self.readers:
            reader.loader = load
        await asyncio.gather(self.readers[0](StatisticsRequest()),
                             self.readers[1](StatisticsRequest(period="monthly")))
        self.assertEqual(self.calls, 2)
        self.assertEqual(peak, 1)

    async def test_failure_holds_shared_lease_instead_of_restarting_sql_on_another_worker(self):
        loader = AsyncMock(side_effect=RuntimeError("private failure"))
        for reader in self.readers:
            reader.loader = loader
        with self.assertRaises(StatisticsUnavailable):
            await self.readers[0](StatisticsRequest())
        with self.assertRaises(TimeoutError):
            await asyncio.wait_for(self.readers[1](StatisticsRequest()), timeout=.3)
        self.assertEqual(loader.await_count, 1)

    async def test_old_refresh_owner_cannot_publish_or_release_a_new_lease(self):
        from app.admin_api.pwa_statistics_cache import _PUBLISH, _RELEASE
        reader = self.readers[0]
        lease = reader.prefix+":refresh"
        key = reader.prefix+":overall:weekly"
        await self.clients[0].set(lease, "new-owner", ex=45)
        self.assertEqual(await self.clients[0].eval(_PUBLISH, 2, lease, key, "old-owner", "invalid", 86400), 0)
        self.assertEqual(await self.clients[0].eval(_RELEASE, 1, lease, "old-owner"), 0)
        self.assertEqual(await self.clients[0].get(lease), b"new-owner")
        self.assertIsNone(await self.clients[0].get(key))

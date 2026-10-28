"""Regression coverage for privileged, lease-guarded on-demand refresh."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
from types import SimpleNamespace
import unittest

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.admin_api.pwa_manual_aggregate_refresh import create_manual_aggregate_refresh_router
from app.admin_api.pwa_read import StatisticsRequest
from app.admin_api.pwa_statistics_cache import (
    AdminPwaStatisticsReader, StatisticsUnavailable, _PUBLISH, _RELEASE,
)
from tests.test_admin_pwa_daily_r2_cache import MemoryR2

SECRET = "g" * 64


class FakeRedis:
    def __init__(self):
        self.locks = {}
        self.cache = {}

    async def set(self, key, token, *, nx, ex):
        if key in self.locks:
            return False
        self.locks[key] = token
        return True

    async def eval(self, script, numkeys, *args):
        if script == _PUBLISH:
            lease, key, token, raw, ttl = args
            if self.locks.get(lease) != token:
                return 0
            self.cache[key] = raw
            del self.locks[lease]
            return 1
        if script == _RELEASE:
            lease, token = args
            if self.locks.get(lease) == token:
                del self.locks[lease]
                return 1
            return 0
        raise AssertionError("Unexpected Redis Lua script")


class ForceCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.clock = datetime.now(timezone.utc).timestamp()
        self.calls = 0
        self.store = MemoryR2()
        self.redis = FakeRedis()
        self.settings = SimpleNamespace(
            ADMIN_PWA_ENABLED=True, REDIS_URL="redis://test",
            ADMIN_PWA_R2_AGGREGATE_ENABLED=True,
        )

        @asynccontextmanager
        async def sessions():
            @asynccontextmanager
            async def transaction():
                yield
            yield SimpleNamespace(begin=transaction,
                get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="sqlite")))
        self.sessions = sessions

    async def projection(self, db, query):
        self.calls += 1
        return {
            "platform": query.platform, "period": query.period, "available": True,
            "scope": {"section": "overview"},
            "source": "users + payments + canonical learning events",
            "generated_at": datetime.fromtimestamp(self.clock, timezone.utc).isoformat(),
            "metrics": {"users_total": self.calls},
        }

    def reader(self):
        return AdminPwaStatisticsReader(
            settings_obj=self.settings, session_factory=self.sessions,
            loader=self.projection, clock=lambda: self.clock, r2_store=self.store,
            redis_client=self.redis, cache_scope="analytics_overview_v1")

    async def test_force_recomputes_unexpired_cache_and_updates_r2_and_redis(self):
        reader = self.reader()
        query = StatisticsRequest(platform="overall", period="weekly")
        first = await reader(query)
        self.assertEqual(first["metrics"]["users_total"], 1)
        next_result = await reader.refresh_now(query)
        self.assertEqual(next_result["metrics"]["users_total"], 2)
        self.assertEqual(self.calls, 2)
        mirror = await self.store.get(
            kind="statistics", namespace=reader._r2_namespace,
            variant="overall_weekly")
        self.assertEqual(json.loads(mirror)["data"]["metrics"]["users_total"], 2)
        self.assertEqual((await reader(query))["metrics"]["users_total"], 2)
        self.assertEqual(self.redis.locks, {})

    async def test_lock_held_fails_closed_without_sql_or_overwriting_r2(self):
        reader = self.reader()
        self.redis.locks[reader._lease_key] = "someone_else"
        with self.assertRaisesRegex(StatisticsUnavailable, "in progress"):
            await reader.refresh_now(StatisticsRequest())
        self.assertEqual(self.calls, 0)
        self.assertEqual(self.store.puts, 0)

    async def test_failed_r2_write_preserves_existing_cache(self):
        reader = self.reader()
        query = StatisticsRequest()
        before = await reader(query)
        stored = dict(self.store.items)
        async def broken_put(**kwargs):
            from app.admin_api.pwa_r2_aggregate_store import R2Unavailable
            raise R2Unavailable("fixture")
        self.store.put = broken_put
        with self.assertRaises(StatisticsUnavailable):
            await reader.refresh_now(query)
        self.assertEqual(self.store.items, stored)
        self.assertEqual((await reader(query))["metrics"]["users_total"],
                         before["metrics"]["users_total"])
        self.assertEqual(self.redis.locks, {})

    async def test_unconfigured_redis_or_disallowed_platform_denied(self):
        reader = self.reader()
        for query in (StatisticsRequest(platform="android"),
                      StatisticsRequest(period="all_time")):
            with self.assertRaises(StatisticsUnavailable):
                await reader.refresh_now(query)
        self.assertEqual(self.calls, 0)


class FakeOverview:
    def __init__(self):
        self.calls = []

    async def refresh_now(self, query):
        self.calls.append((query.platform, query.period))
        return {
            "available": True, "scope": {"section": "overview"},
            "generated_at": "2026-10-28T01:00:00+00:00",
            "snapshot": {"expires_at": "2026-10-29T01:00:00+00:00"},
        }


class ManualRefreshTransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.overview = FakeOverview()
        self.settings = SimpleNamespace(
            ADMIN_PWA_ENABLED=True, ADMIN_PWA_R2_AGGREGATE_ENABLED=True,
            ADMIN_PWA_PUBLIC_ORIGIN="https://hskai.app",
            ADMIN_PWA_MANUAL_AGGREGATE_REFRESH_TOKEN=SECRET,
        )
        app = FastAPI()
        app.include_router(create_manual_aggregate_refresh_router(
            settings_obj=self.settings,
            analytics_reader=SimpleNamespace(_readers={"overview": self.overview})))
        self.app = app

    async def post(self, *, url="https://hskai.app", secret=SECRET, data="{}"):
        async with AsyncClient(transport=ASGITransport(app=self.app), base_url=url) as client:
            return await client.post(
                "/api/internal/admin-pwa/analytics/refresh",
                content=data,
                headers={"Authorization": "Bearer " + secret,
                         "Content-Type": "application/json"})

    async def test_only_matching_long_secret_and_origin_can_refresh(self):
        for case in ({"secret": "wrong"}, {"url": "https://attacker.test"}):
            result = await self.post(**case)
            self.assertIn(result.status_code, (401, 403))
        self.assertEqual(self.overview.calls, [])
        result = await self.post()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.overview.calls,
                         [("overall", "weekly"), ("overall", "monthly")])
        self.assertEqual(result.json()["periods"]["weekly"]["generated_at"],
                         "2026-10-28T01:00:00+00:00")
        self.assertNotIn("metrics", result.text)

    async def test_disabled_token_or_bad_payload_fails_without_refresh(self):
        result = await self.post(data='{"section":"users"}')
        self.assertEqual(result.status_code, 400)
        self.settings.ADMIN_PWA_MANUAL_AGGREGATE_REFRESH_TOKEN = ""
        result = await self.post()
        self.assertEqual(result.status_code, 404)
        self.assertEqual(self.overview.calls, [])


if __name__ == "__main__":
    unittest.main()

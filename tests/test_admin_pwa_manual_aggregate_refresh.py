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

    async def getrange(self, key, start, end):
        raw = self.cache.get(key)
        return raw[start:end + 1] if raw is not None else None

    async def get(self, key):
        return self.cache.get(key)

    async def set(self, key, token, *, nx=False, ex):
        if nx and key in self.locks:
            return False
        if nx:
            self.locks[key] = token
        else:
            self.cache[key] = token
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
                      StatisticsRequest(platform="telegram")):
            with self.assertRaises(StatisticsUnavailable):
                await reader.refresh_now(query)
        self.assertEqual(self.calls, 0)


    async def test_other_worker_revalidates_valid_local_overview_after_60s(self):
        first = self.reader()
        other = self.reader()
        query = StatisticsRequest(platform="overall", period="weekly")
        old = await other(query)
        self.assertEqual(old["metrics"]["users_total"], 1)
        await first.refresh_now(query)
        self.assertEqual((await other(query))["metrics"]["users_total"], 1)
        self.clock += 61
        self.assertEqual((await other(query))["metrics"]["users_total"], 2)
        self.assertEqual(self.calls, 2)

    async def test_redis_cannot_downgrade_a_newer_worker_local_snapshot(self):
        reader = self.reader()
        query = StatisticsRequest(period="weekly")
        old = await reader(query)
        stale = self.redis.cache[reader.prefix + ":overall:weekly"]
        self.clock += 1
        newer = await reader.refresh_now(query)
        self.assertEqual(newer["metrics"]["users_total"], 2)
        self.assertGreater(newer["snapshot"]["expires_at"], old["snapshot"]["expires_at"])
        # Simulate Redis falling back to an older snapshot after R2 commit.
        self.redis.cache[reader.prefix + ":overall:weekly"] = stale
        self.clock += 61
        checked = await reader(query)
        self.assertEqual(checked["metrics"]["users_total"], 2)

    async def test_all_time_is_included_and_retained_in_private_r2(self):
        reader = self.reader()
        result = await reader.refresh_overview_bundle()
        self.assertEqual(set(result), {"weekly", "monthly", "all_time"})
        obj = await self.store.get(kind="statistics",
                                   namespace=reader._r2_namespace,
                                   variant="overall_all_time")
        self.assertEqual(json.loads(obj)["data"]["period"], "all_time")
        self.assertEqual(self.calls, 3)

    async def test_untrusted_projection_is_rejected_before_any_r2_write(self):
        reader = self.reader()
        async def wrong_scope(db, query):
            self.calls += 1
            return {
                "platform": query.platform, "period": query.period,
                "available": True,
                "scope": {"section": "home"},
                "source": "users + payments + canonical learning events",
                "generated_at": datetime.fromtimestamp(self.clock, timezone.utc).isoformat(),
                "metrics": {"users_total": 1},
            }
        reader.loader = wrong_scope
        with self.assertRaisesRegex(StatisticsUnavailable, "Unexpected overview"):
            await reader.refresh_now(StatisticsRequest())
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.store.puts, 0)
        self.assertEqual(self.redis.cache, {})
        self.assertEqual(self.redis.locks, {})

    async def test_bundle_is_serialized_and_cooldown_prevents_sql_flood(self):
        reader = self.reader()
        first = await reader.refresh_overview_bundle()
        self.assertEqual(set(first), {"weekly", "monthly", "all_time"})
        self.assertEqual(self.calls, 3)
        with self.assertRaisesRegex(StatisticsUnavailable, "recently completed"):
            await reader.refresh_overview_bundle()
        self.assertEqual(self.calls, 3)
        self.assertEqual(self.redis.locks, {})

    async def test_second_period_failure_is_not_reported_success(self):
        reader = self.reader()
        original = reader.loader

        async def unavailable_month(db, query):
            if query.period == "monthly":
                raise ValueError("simulated projection error")
            return await original(db, query)

        reader.loader = unavailable_month
        with self.assertRaises(StatisticsUnavailable):
            await reader.refresh_overview_bundle()
        # First period was durable, but no success cooldown was set and the
        # remaining period was never computed. The caller must see failure.
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.store.puts, 1)
        self.assertNotIn(reader.prefix + ":manual_refresh_cooldown",
                         self.redis.cache)
        self.assertEqual(self.redis.locks, {})

    async def test_redis_publication_failure_does_not_claim_success(self):
        reader = self.reader()
        query = StatisticsRequest()
        published_before = await reader(query)
        original_eval = self.redis.eval

        async def fail_publish(script, numkeys, *args):
            if script == _PUBLISH:
                return 0
            return await original_eval(script, numkeys, *args)

        self.redis.eval = fail_publish
        with self.assertRaisesRegex(StatisticsUnavailable, "lease lost"):
            await reader.refresh_now(query)
        # Mirrors can differ temporarily; an HTTP 503 must never be treated
        # as proof that R2 was unchanged.
        self.assertEqual(self.store.puts, 2)
        self.assertEqual((await reader(query))["metrics"]["users_total"],
                         published_before["metrics"]["users_total"])
        self.assertEqual(self.redis.locks, {})

    async def test_bundle_lock_held_blocks_all_periods(self):
        reader = self.reader()
        self.redis.locks[reader.prefix + ":manual_refresh_batch"] = "another_token"
        with self.assertRaisesRegex(StatisticsUnavailable, "in progress"):
            await reader.refresh_overview_bundle()
        self.assertEqual(self.calls, 0)
        self.assertEqual(self.store.puts, 0)


class FakeOverview:
    def __init__(self):
        self.calls = []

    async def refresh_overview_bundle(self):
        self.calls.extend([("overall", period) for period in ("weekly", "monthly", "all_time")])
        return {
            period: {
                "generated_at": "2026-10-28T01:00:00+00:00",
                "expires_at": "2026-10-29T01:00:00+00:00",
            } for period in ("weekly", "monthly", "all_time")
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
                         [("overall", "weekly"), ("overall", "monthly"), ("overall", "all_time")])
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

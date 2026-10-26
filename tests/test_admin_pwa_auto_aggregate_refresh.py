"""Automatic overview refresh safety: no network, credentials or database."""
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest

from app.admin_api.pwa_auto_aggregate_refresh import (
    enabled, refresh_once, overview_refresh_scheduler,
)
from app.admin_api.pwa_statistics_cache import StatisticsUnavailable

AT = datetime(2026, 10, 26, 4, 0, tzinfo=timezone.utc)


class FakeRedis:
    def __init__(self, fail=False):
        self.keys = set()
        self.fail = fail
        self.closed = 0

    async def set(self, key, value, *, ex, nx):
        if self.fail:
            raise OSError("Redis offline")
        if key in self.keys:
            return False
        self.keys.add(key)
        return True

    async def aclose(self):
        self.closed += 1


class FakeAnalytics:
    def __init__(self, namespace="a" * 24, fail=()):
        self._readers = {"overview": SimpleNamespace(_r2_namespace=namespace)}
        self.calls = []
        self.fail = fail

    async def __call__(self, query):
        self.calls.append((query.section, query.period, query.platform))
        if query.period in self.fail:
            raise StatisticsUnavailable("fixture unavailable")
        return {"ok": True}


class RefreshTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            ADMIN_PWA_AUTO_AGGREGATE_REFRESH_ENABLED=True,
            ADMIN_PWA_ENABLED=True,
            ADMIN_PWA_R2_AGGREGATE_ENABLED=True,
            REDIS_URL="redis://fake",
        )
        self.redis = FakeRedis()
        self.analytics = FakeAnalytics()
        self.factory = lambda *args, **kwargs: self.redis

    async def test_hourly_checks_all_three_overview_periods(self):
        data = await refresh_once(
            settings_obj=self.settings, analytics_reader=self.analytics,
            redis_factory=self.factory, now=AT)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["refreshed_periods"], ("weekly", "monthly", "all_time"))
        self.assertEqual(self.analytics.calls, [
            ("overview", "weekly", "overall"),
            ("overview", "monthly", "overall"),
            ("overview", "all_time", "overall"),
        ])
        self.assertEqual(self.redis.closed, 1)

    async def test_repeated_check_same_hour_does_not_query_twice(self):
        for i in range(2):
            result = await refresh_once(
                settings_obj=self.settings, analytics_reader=self.analytics,
                redis_factory=self.factory, now=AT)
        self.assertEqual(result["status"], "already_checked")
        self.assertEqual(len(self.analytics.calls), 3)
        self.assertEqual(self.redis.closed, 2)

    async def test_later_hour_rechecks_cache_without_force_recompute(self):
        for at in (AT, AT + timedelta(hours=1)):
            result = await refresh_once(
                settings_obj=self.settings, analytics_reader=self.analytics,
                redis_factory=self.factory, now=at)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(self.analytics.calls), 6)
        self.assertEqual(len(self.redis.keys), 2)

    async def test_no_redis_means_no_queries_and_no_local_fallback(self):
        self.redis.fail = True
        result = await refresh_once(
            settings_obj=self.settings, analytics_reader=self.analytics,
            redis_factory=self.factory, now=AT)
        self.assertEqual(result["status"], "redis_unavailable")
        self.assertEqual(self.analytics.calls, [])
        self.assertEqual(self.redis.closed, 1)

    async def test_bad_namespace_means_no_redis_or_db(self):
        self.analytics = FakeAnalytics(namespace="../untrusted")
        result = await refresh_once(
            settings_obj=self.settings, analytics_reader=self.analytics,
            redis_factory=self.factory, now=AT)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(self.redis.closed, 0)

    async def test_feature_is_disabled_by_default_and_by_independent_gates(self):
        for key in (
            "ADMIN_PWA_AUTO_AGGREGATE_REFRESH_ENABLED",
            "ADMIN_PWA_ENABLED",
            "ADMIN_PWA_R2_AGGREGATE_ENABLED",
            "REDIS_URL",
        ):
            original = getattr(self.settings, key)
            setattr(self.settings, key, "" if key == "REDIS_URL" else False)
            self.assertFalse(enabled(self.settings))
            result = await refresh_once(
                settings_obj=self.settings, analytics_reader=self.analytics,
                redis_factory=self.factory, now=AT)
            self.assertEqual(result["status"], "disabled")
            setattr(self.settings, key, original)
        self.assertTrue(enabled(self.settings))
        self.assertEqual(self.analytics.calls, [])

    async def test_partial_failure_does_not_prevent_next_period(self):
        self.analytics = FakeAnalytics(fail=("monthly",))
        result = await refresh_once(
            settings_obj=self.settings, analytics_reader=self.analytics,
            redis_factory=self.factory, now=AT)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["refreshed_periods"], ("weekly", "all_time"))
        self.assertEqual(len(self.analytics.calls), 3)

    async def test_scheduler_cancels_cleanly(self):
        checks = []

        async def cancel_after_start(**kwargs):
            checks.append("called")
            raise asyncio.CancelledError()

        with self.assertRaises(asyncio.CancelledError):
            await overview_refresh_scheduler(
                settings_obj=self.settings, analytics_reader=self.analytics,
                initial_delay=0, tick_seconds=0, refresh=cancel_after_start)
        self.assertEqual(checks, ["called"])

    async def test_scheduler_when_disabled_never_sleeps_or_reads(self):
        self.settings.ADMIN_PWA_AUTO_AGGREGATE_REFRESH_ENABLED = False

        async def must_not_call(**kwargs):
            self.fail("Unexpected scheduler call")

        await overview_refresh_scheduler(
            settings_obj=self.settings, analytics_reader=self.analytics,
            initial_delay=0, tick_seconds=0, refresh=must_not_call)


if __name__ == "__main__":
    unittest.main()

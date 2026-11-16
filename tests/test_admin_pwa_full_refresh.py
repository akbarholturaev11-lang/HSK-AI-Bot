"""Full analytics refresh: bounded R2 retry, section bundles, manifest and route.

The PostgreSQL class compares every bundle snapshot with the unchanged V10
projection on the golden fixture (no formula drift) and exercises the real
advisory lock. Set ANALYTICS_TEST_DATABASE_URL to a disposable *_test database.
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.admin_api import pwa_analytics_cache as analytics
from app.admin_api import pwa_feedback_analytics as feedback_module
from app.admin_api.pwa_analytics_cache import AdminPwaAnalyticsReader
from app.admin_api.pwa_feedback_analytics import FEEDBACK_DEFINITIONS
from app.admin_api.pwa_feedback_cache import AdminPwaFeedbackReader
from app.admin_api.pwa_full_refresh_manifest import (
    GROUPS, MANIFEST_VERSION, PERIODS, SECTION_ORDER, group_for, manifest,
)
from app.admin_api.pwa_manual_aggregate_refresh import create_manual_aggregate_refresh_router
from app.admin_api.pwa_r2_aggregate_store import (
    PrivateR2AggregateStore, R2Unavailable, classify_r2_failure,
)
from app.admin_api.pwa_read import StatisticsRequest
from app.admin_api.pwa_statistics_cache import AdminPwaStatisticsReader, StatisticsUnavailable
from tests.test_admin_pwa_daily_r2_cache import MemoryR2

SECRET = "f" * 64
URL = os.getenv("ANALYTICS_TEST_DATABASE_URL", "")


class ProviderError(Exception):
    """Shape of a botocore ClientError: only `response` is inspected."""

    def __init__(self, status, code="X"):
        super().__init__("provider text with admin-pwa/aggregates/v1/secret-key must never be logged")
        self.response = {"ResponseMetadata": {"HTTPStatusCode": status}, "Error": {"Code": code}}


class ReadTimeoutError(Exception):
    pass


class ConnectTimeoutError(Exception):
    pass


class FlakyR2(MemoryR2):
    """MemoryR2 whose next N get/put calls fail with a classified R2 error."""

    def __init__(self):
        super().__init__()
        self.fail = {"get": [], "put": []}
        self.calls = {"get": 0, "put": 0}

    def _maybe_fail(self, op):
        self.calls[op] += 1
        if self.fail[op]:
            failure_class = self.fail[op].pop(0)
            raise R2Unavailable("fixture", op=op, failure_class=failure_class)

    async def get(self, **kwargs):
        self._maybe_fail("get")
        return await super().get(**kwargs)

    async def put(self, **kwargs):
        self._maybe_fail("put")
        await super().put(**kwargs)


def fake_sessions():
    @asynccontextmanager
    async def sessions():
        @asynccontextmanager
        async def transaction():
            yield
        yield SimpleNamespace(begin=transaction,
                              get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="sqlite")))
    return sessions


class R2ClassificationTests(unittest.IsolatedAsyncioTestCase):
    def test_only_transient_classes_are_retryable(self):
        cases = {
            TimeoutError(): ("timeout", True),
            asyncio.TimeoutError(): ("timeout", True),
            ConnectTimeoutError(): ("connect_timeout", True),
            ReadTimeoutError(): ("read_timeout", True),
            ConnectionResetError(): ("network", True),
            ProviderError(503): ("provider_5xx", True),
            ProviderError(500, "InternalError"): ("provider_5xx", True),
            ProviderError(429, "SlowDown"): ("provider_throttled", True),
            ProviderError(403, "AccessDenied"): ("provider_4xx", False),
            ProviderError(400, "InvalidRequest"): ("provider_4xx", False),
            ValueError("bad"): ("other", False),
        }
        for exc, (failure_class, transient) in cases.items():
            self.assertEqual(classify_r2_failure(exc), failure_class, type(exc).__name__)
            self.assertEqual(R2Unavailable("x", failure_class=failure_class).transient, transient)
        self.assertFalse(R2Unavailable("legacy fixture").transient)

    async def test_store_reports_operation_and_class_without_key_or_provider_text(self):
        settings = SimpleNamespace(ADMIN_PWA_R2_AGGREGATE_ENABLED=True, ADMIN_PWA_R2_ACCOUNT_ID="a" * 32,
                                   ADMIN_PWA_R2_BUCKET="hsk-ai-statistics",
                                   ADMIN_PWA_R2_ACCESS_KEY_ID="id", ADMIN_PWA_R2_SECRET_ACCESS_KEY="secret")

        class Client:
            def get_object(self, **kwargs):
                raise ProviderError(503)

            def put_object(self, **kwargs):
                raise ReadTimeoutError()

        store = PrivateR2AggregateStore(settings_obj=settings, client=Client())
        args = {"kind": "statistics", "namespace": "0" * 24, "variant": "overall_weekly"}
        with self.assertLogs("app.admin_api.pwa_r2_aggregate_store", logging.WARNING) as logs:
            with self.assertRaises(R2Unavailable) as read:
                await store.get(**args)
            with self.assertRaises(R2Unavailable) as write:
                await store.put(**args, raw=b"{}")
        self.assertEqual((read.exception.op, read.exception.failure_class), ("get", "provider_5xx"))
        self.assertEqual((write.exception.op, write.exception.failure_class), ("put", "read_timeout"))
        self.assertIsNone(read.exception.__cause__)
        joined = "\n".join(logs.output)
        self.assertIn("class=provider_5xx", joined)
        for leaked in ("aggregates/v1", "0" * 24, "secret", "overall_weekly", "provider text"):
            self.assertNotIn(leaked, joined)

    async def test_store_missing_object_is_still_a_cache_miss(self):
        settings = SimpleNamespace(ADMIN_PWA_R2_AGGREGATE_ENABLED=True, ADMIN_PWA_R2_ACCOUNT_ID="a" * 32,
                                   ADMIN_PWA_R2_BUCKET="hsk-ai-statistics",
                                   ADMIN_PWA_R2_ACCESS_KEY_ID="id", ADMIN_PWA_R2_SECRET_ACCESS_KEY="secret")

        class Client:
            def get_object(self, **kwargs):
                raise ProviderError(404, "NoSuchKey")

        store = PrivateR2AggregateStore(settings_obj=settings, client=Client())
        self.assertIsNone(await store.get(kind="statistics", namespace="0" * 24, variant="overall_weekly"))


class Fixture:
    """Deterministic stand-in loader; every call returns a new observation."""

    def setUp(self):
        self.clock = datetime(2026, 11, 16, 6, tzinfo=timezone.utc).timestamp()
        self.store = FlakyR2()
        self.calls = []
        self.unavailable = set()
        self.settings = SimpleNamespace(ADMIN_PWA_ENABLED=True, REDIS_URL="",
                                        ADMIN_PWA_R2_AGGREGATE_ENABLED=True)

    async def loader(self, db, query, *, section="course"):
        self.calls.append((section, query.platform, query.period))
        now = datetime.fromtimestamp(self.clock, timezone.utc)
        since = None if query.period == "all_time" else (
            now - timedelta(days=7 if query.period == "weekly" else 30)).isoformat()
        data = {"platform": query.platform, "period": query.period, "since": since,
                "generated_at": now.isoformat(), "timezone": "Asia/Shanghai",
                "platform_counts_overlap": True, "available": True,
                "source": ("users + payments + canonical learning events"
                           if section in ("home", "overview") else "first-party stored aggregate projections"),
                "scope": {"section": section}, "metrics": {"value": len(self.calls)}}
        if section != "experiments":
            data["metric_states"] = {}  # V10 sections carry states; experiments does not
        if (section, query.platform, query.period) in self.unavailable:
            data.update(available=False, metrics=None, reason="not_instrumented")
        return data

    def reader(self, section="course", store=None):
        version = 3 if section == "report" else 1 if section == "experiments" else 2

        async def load(db, query):
            return await self.loader(db, query, section=section)
        reader = AdminPwaStatisticsReader(
            settings_obj=self.settings, session_factory=fake_sessions(), loader=load,
            clock=lambda: self.clock, r2_store=store or self.store,
            cache_scope=f"analytics_{section}_v{version}")
        reader._r2_retry_delays = (0, 0)
        return reader

    def stored(self, reader, variant, kind="statistics"):
        raw = self.store.items.get((kind, reader._r2_namespace, variant))
        return None if raw is None else json.loads(raw)


class BoundedRetryTests(Fixture, unittest.IsolatedAsyncioTestCase):
    async def test_transient_write_failure_is_retried_and_succeeds(self):
        reader = self.reader("funnel")
        self.store.fail["put"] = ["read_timeout", "provider_5xx"]
        result = await reader.refresh_approved_section(StatisticsRequest(period="weekly"), section="funnel")
        self.assertEqual(result["period"], "weekly")
        self.assertEqual(self.store.calls["put"], 3)
        self.assertEqual(self.stored(reader, "overall_weekly")["data"]["metrics"]["value"], 1)

    async def test_overview_bundle_retries_the_cooldown_read(self):
        reader = self.reader("overview")
        self.store.fail["get"] = ["timeout"]
        result = await reader.refresh_overview_bundle()
        self.assertEqual(set(result), set(PERIODS))
        self.assertEqual(self.store.calls["get"], 4)

    async def test_retry_is_bounded_to_three_attempts_and_keeps_old_snapshot(self):
        reader = self.reader("money")
        await reader.refresh_approved_section(StatisticsRequest(period="monthly"), section="money")
        before = dict(self.store.items)
        self.clock += 120
        self.store.fail["put"] = ["network"] * 5
        with self.assertLogs("app.admin_api.pwa_statistics_cache", logging.WARNING) as logs:
            with self.assertRaisesRegex(StatisticsUnavailable, "R2 write unavailable"):
                await reader.refresh_approved_section(StatisticsRequest(period="monthly"), section="money")
        self.assertEqual(self.store.calls["put"], 1 + 3)
        self.assertEqual(self.store.items, before)
        self.assertIn("op=put class=network attempts=3", "\n".join(logs.output))

    async def test_non_transient_and_unclassified_failures_are_not_retried(self):
        reader = self.reader("sources")
        self.store.fail["put"] = ["provider_4xx"]
        with self.assertRaises(StatisticsUnavailable):
            await reader.refresh_approved_section(StatisticsRequest(period="weekly"), section="sources")
        self.assertEqual(self.store.calls["put"], 1)

        async def legacy_put(**kwargs):
            legacy_put.calls += 1
            raise R2Unavailable("fixture")
        legacy_put.calls = 0
        self.store.put = legacy_put
        self.clock += 120
        with self.assertRaises(StatisticsUnavailable):
            await reader.refresh_approved_section(StatisticsRequest(period="weekly"), section="sources")
        self.assertEqual(legacy_put.calls, 1)

    async def test_browser_read_path_keeps_a_single_attempt(self):
        reader = self.reader("course")
        self.store.fail["get"] = ["timeout"]
        result = await reader(StatisticsRequest(period="weekly"))
        self.assertTrue(result["available"])
        self.assertEqual(self.store.calls["get"], 1)


class SectionBundleTests(Fixture, unittest.IsolatedAsyncioTestCase):
    async def test_three_windows_in_one_call_without_the_legacy_cooldown(self):
        reader = self.reader("course")
        result = await reader.refresh_section_bundle(section="course", platform="android", periods=PERIODS)
        self.assertEqual(result["status"], "refreshed")
        self.assertEqual([self.calls[i][2] for i in range(3)], list(PERIODS))
        for period in PERIODS:
            stored = self.stored(reader, "android_" + period)
            self.assertEqual(stored["data"]["period"], period)
            self.assertEqual(result["periods"][period]["generated_at"], stored["data"]["generated_at"])
            # The reader serves the fresh snapshot without another computation.
            served = await reader(StatisticsRequest(platform="android", period=period))
            self.assertEqual(served["generated_at"], stored["data"]["generated_at"])
        self.assertEqual(len(self.calls), 3)

    async def test_group_cooldown_in_process_and_across_workers(self):
        reader = self.reader("money")
        await reader.refresh_section_bundle(section="money", platform="overall", periods=PERIODS)
        with self.assertRaisesRegex(StatisticsUnavailable, "recently completed"):
            await reader.refresh_section_bundle(section="money", platform="overall", periods=PERIODS)
        other_worker = self.reader("money")
        with self.assertRaisesRegex(StatisticsUnavailable, "recently completed"):
            await other_worker.refresh_section_bundle(section="money", platform="overall", periods=PERIODS)
        # Another platform is another group; time moves the group out of cooldown.
        await reader.refresh_section_bundle(section="money", platform="telegram", periods=PERIODS)
        self.clock += 61
        again = await other_worker.refresh_section_bundle(section="money", platform="overall", periods=PERIODS)
        self.assertEqual(again["status"], "refreshed")
        self.assertEqual(len(self.calls), 9)

    async def test_two_simultaneous_refreshes_compute_once(self):
        reader = self.reader("funnel")
        results = await asyncio.gather(
            reader.refresh_section_bundle(section="funnel", platform="overall", periods=PERIODS),
            reader.refresh_section_bundle(section="funnel", platform="overall", periods=PERIODS),
            return_exceptions=True)
        self.assertEqual(sum(isinstance(r, dict) for r in results), 1)
        self.assertEqual(sum(isinstance(r, StatisticsUnavailable) for r in results), 1)
        self.assertEqual(len(self.calls), 3)

    async def test_partial_write_is_reported_and_never_success(self):
        reader = self.reader("sources")
        await reader.refresh_section_bundle(section="sources", platform="overall", periods=PERIODS)
        old_all_time = self.stored(reader, "overall_all_time")
        self.clock += 120
        original = self.store.put
        attempts = []

        async def put(**kwargs):
            attempts.append(kwargs["variant"])
            if kwargs["variant"] == "overall_monthly":
                raise R2Unavailable("fixture", op="put", failure_class="provider_4xx")
            await original(**kwargs)
        self.store.put = put
        result = await reader.refresh_section_bundle(section="sources", platform="overall", periods=PERIODS)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["periods"]["weekly"]["status"], "refreshed")
        self.assertEqual(result["periods"]["monthly"],
                         {"status": "failed", "reason": "r2_write", "failure_class": "provider_4xx"})
        self.assertEqual(result["periods"]["all_time"], {"status": "failed", "reason": "not_attempted"})
        self.assertEqual(attempts, ["overall_weekly", "overall_monthly"])
        self.assertEqual(self.stored(reader, "overall_all_time"), old_all_time)

    async def test_unavailable_window_is_reported_not_written_or_zeroed(self):
        reader = self.reader("course")
        self.unavailable = {("course", "telegram", "all_time")}
        result = await reader.refresh_section_bundle(section="course", platform="telegram", periods=PERIODS)
        self.assertEqual(result["status"], "refreshed")
        self.assertEqual(result["periods"]["all_time"], {"status": "unavailable", "reason": "not_instrumented"})
        self.assertIsNone(self.stored(reader, "telegram_all_time"))
        self.unavailable = {("course", "iphone_pwa", p) for p in PERIODS}
        result = await reader.refresh_section_bundle(section="course", platform="iphone_pwa", periods=PERIODS)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(self.store.puts, 2)

    async def test_unexpected_projection_writes_nothing(self):
        reader = self.reader("report")

        async def wrong(db, query):
            data = await self.loader(db, query, section="report")
            data["scope"] = {"section": "money"}
            return data
        reader.loader = wrong
        with self.assertRaisesRegex(StatisticsUnavailable, "Unexpected bundle projection"):
            await reader.refresh_section_bundle(section="report", platform="overall", periods=("weekly",))
        self.assertEqual(self.store.puts, 0)

    async def test_failed_cooldown_read_is_a_safe_r2_read_failure(self):
        reader = self.reader("home")
        self.store.fail["get"] = ["provider_4xx"]
        with self.assertRaisesRegex(StatisticsUnavailable, "R2 read unavailable"):
            await reader.refresh_section_bundle(section="home", platform="overall", periods=PERIODS)
        self.assertEqual((len(self.calls), self.store.puts), (0, 0))

    async def test_bundle_rejects_foreign_section_platform_or_period(self):
        reader = self.reader("course")
        for kwargs in ({"section": "money", "platform": "overall", "periods": PERIODS},
                       {"section": "course", "platform": "macos", "periods": PERIODS},
                       {"section": "course", "platform": "overall", "periods": ("daily",)},
                       {"section": "course", "platform": "overall", "periods": ("weekly", "weekly")},
                       {"section": "course", "platform": "overall", "periods": ()}):
            with self.assertRaises(StatisticsUnavailable):
                await reader.refresh_section_bundle(**kwargs)
        self.assertEqual(self.calls, [])


def feedback_payload(query, now):
    since = now - timedelta(days=7 if query.period == "weekly" else 30)
    date_basis = {"bot": "bot_feedbacks.completed_at", "release": "release_feedback_responses.completed_at",
                  "android": "admin_pwa_native_reports.created_at"}
    return {"schema": "hskai_feedback_categories_v1", "period": query.period, "source": query.source,
            "since": since.isoformat(), "until": now.isoformat(), "generated_at": now.isoformat(),
            "sample_limit_per_source": 500, "coverage": "most_recent_source_records_in_window",
            "historical_android_reports_complete": False, "definitions": FEEDBACK_DEFINITIONS,
            "sources": [{"source": source, "date_basis": date_basis[source], "records_scanned": 3,
                         "truncated": False, "categories": [{"category": "price", "count": 2}]}
                        for source in ("bot", "release", "android")]}


class FeedbackBundleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.clock = datetime(2026, 11, 16, 6, tzinfo=timezone.utc).timestamp()
        self.store = MemoryR2()
        self.calls = []

    def reader(self, loader=None):
        async def load(db, query):
            self.calls.append(query.period)
            return feedback_payload(query, datetime.fromtimestamp(self.clock, timezone.utc))
        reader = AdminPwaFeedbackReader(
            settings_obj=SimpleNamespace(ADMIN_PWA_ENABLED=True, REDIS_URL=""),
            session_factory=fake_sessions(), loader=loader or load, r2_store=self.store,
            clock=lambda: self.clock)
        reader._r2_retry_delays = (0, 0)
        return reader

    async def test_weekly_and_monthly_category_aggregates_reach_the_feedback_keys(self):
        reader = self.reader()
        result = await reader.refresh_feedback_bundle(periods=("weekly", "monthly"))
        self.assertEqual(result["status"], "refreshed")
        self.assertEqual(sorted(key[2] for key in self.store.items), ["all_monthly", "all_weekly"])
        self.assertEqual({key[0] for key in self.store.items}, {"feedback"})
        for raw in self.store.items.values():
            data = json.loads(raw)["data"]
            # Exactly the category schema: no text, account or record fields.
            self.assertEqual(set(data), {"schema", "period", "source", "since", "until", "generated_at",
                                         "sample_limit_per_source", "coverage",
                                         "historical_android_reports_complete", "definitions", "sources"})
            for item in data["sources"]:
                self.assertEqual(set(item), {"source", "date_basis", "records_scanned", "truncated",
                                             "categories"})
        with self.assertRaises(StatisticsUnavailable):
            await reader.refresh_feedback_bundle(periods=("all_time",))

    async def test_invalid_feedback_schema_writes_nothing(self):
        async def bad(db, query):
            data = feedback_payload(query, datetime.fromtimestamp(self.clock, timezone.utc))
            data["sources"][0]["comment"] = "raw text"
            return data
        reader = self.reader(loader=bad)
        with self.assertRaisesRegex(StatisticsUnavailable, "Invalid bundle projection"):
            await reader.refresh_feedback_bundle(periods=("weekly",))
        self.assertEqual(self.store.items, {})


class ManifestTests(unittest.TestCase):
    def test_manifest_covers_ten_sections_and_names_every_skipped_window(self):
        self.assertEqual(len(SECTION_ORDER), 10)
        self.assertEqual([s for s in SECTION_ORDER], list(dict.fromkeys(g["section"] for g in GROUPS)))
        self.assertEqual(len(GROUPS), 25)
        for group in GROUPS:
            self.assertEqual(set(group["periods"]) | set(group["unsupported"]), set(PERIODS))
            self.assertNotIn(group["platform"], ("macos", "windows"))
        self.assertEqual(group_for("platform", "android")["unsupported"],
                         {"monthly": "period_independent", "all_time": "period_independent"})
        self.assertEqual(group_for("experiments", "overall")["unsupported"],
                         {"all_time": "rolling_30_days_not_lifetime"})
        self.assertIsNone(group_for("home", "android"))
        self.assertIsNone(group_for("course", "macos"))
        body = json.dumps(manifest())
        self.assertIn(MANIFEST_VERSION, body)


class RouteTests(Fixture, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.settings.ADMIN_PWA_PUBLIC_ORIGIN = "https://hskai.app"
        self.settings.ADMIN_PWA_MANUAL_AGGREGATE_REFRESH_TOKEN = SECRET
        self.settings.ADMIN_PWA_FULL_REFRESH_ENABLED = True
        self.readers = {section: self.reader(section) for section in SECTION_ORDER if section != "feedback"}
        self.feedback = AdminPwaFeedbackReader(
            settings_obj=self.settings, session_factory=fake_sessions(), r2_store=self.store,
            clock=lambda: self.clock,
            loader=lambda db, query: self._feedback(query))
        self.feedback._r2_retry_delays = (0, 0)
        app = FastAPI()
        app.include_router(create_manual_aggregate_refresh_router(
            settings_obj=self.settings, analytics_reader=SimpleNamespace(_readers=self.readers),
            feedback_reader=self.feedback))
        self.app = app

    async def _feedback(self, query):
        return feedback_payload(query, datetime.fromtimestamp(self.clock, timezone.utc))

    async def post(self, data, *, secret=SECRET, url="https://hskai.app"):
        async with AsyncClient(transport=ASGITransport(app=self.app), base_url=url) as client:
            return await client.post("/api/internal/admin-pwa/analytics/refresh", content=data,
                                     headers={"Authorization": "Bearer " + secret,
                                              "Content-Type": "application/json"})

    async def test_switch_off_keeps_the_legacy_contract(self):
        self.settings.ADMIN_PWA_FULL_REFRESH_ENABLED = False
        for body in ('{"mode":"manifest"}', '{"mode":"bundle","section":"course","platform":"overall"}'):
            self.assertEqual((await self.post(body)).status_code, 400)
        self.assertEqual(self.calls, [])
        legacy = await self.post('{"section":"course","period":"weekly"}')
        self.assertEqual((legacy.status_code, legacy.json()["section"]), (200, "course"))
        overview = await self.post("{}")
        self.assertEqual(set(overview.json()["periods"]), set(PERIODS))

    async def test_manifest_then_every_group_sequentially(self):
        result = await self.post('{"mode":"manifest"}')
        self.assertEqual(result.status_code, 200)
        listed = result.json()
        self.assertEqual(listed["manifest_version"], MANIFEST_VERSION)
        statuses = {}
        for group in listed["groups"]:
            body = json.dumps({"mode": "bundle", "section": group["section"], "platform": group["platform"]},
                              separators=(",", ":"))
            self.assertLessEqual(len(body), 128)
            response = await self.post(body)
            self.assertEqual(response.status_code, 200, (group, response.text))
            reply = response.json()
            self.assertNotIn("metrics", response.text)
            self.assertEqual(reply["manifest_version"], MANIFEST_VERSION)
            statuses[group["section"], group["platform"]] = reply["status"]
            self.assertEqual(set(reply["periods"]), set(PERIODS))
            for period, why in group["unsupported"].items():
                self.assertEqual(reply["periods"][period], {"status": "unsupported", "reason": why})
        self.assertEqual(set(statuses.values()), {"refreshed"})
        self.assertEqual(len(statuses), 25)
        statistics = [key for key in self.store.items if key[0] == "statistics"]
        feedback = [key for key in self.store.items if key[0] == "feedback"]
        self.assertEqual(len(statistics), sum(len(g["periods"]) for g in GROUPS if g["section"] != "feedback"))
        self.assertEqual(len(feedback), 2)

    async def test_status_codes_for_cooldown_partial_and_read_failure(self):
        body = '{"mode":"bundle","section":"money","platform":"android"}'
        self.assertEqual((await self.post(body)).status_code, 200)
        recent = await self.post(body)
        self.assertEqual((recent.status_code, recent.json()["status"]), (429, "unchanged_recent"))
        self.store.fail["get"] = ["provider_4xx"]
        failed = await self.post('{"mode":"bundle","section":"funnel","platform":"android"}')
        self.assertEqual((failed.status_code, failed.json()["status"], failed.json()["reason"]),
                         (503, "failed", "r2_read"))
        original = self.store.put

        async def put(**kwargs):
            if kwargs["variant"].endswith("_all_time"):
                raise R2Unavailable("fixture", op="put", failure_class="provider_5xx")
            await original(**kwargs)
        self.store.put = put
        partial = await self.post('{"mode":"bundle","section":"sources","platform":"telegram"}')
        self.assertEqual((partial.status_code, partial.json()["status"]), (503, "partial"))
        self.assertEqual(partial.json()["periods"]["all_time"]["status"], "failed")
        self.assertFalse(partial.json()["ok"])

    async def test_rejects_unlisted_groups_extra_keys_and_bad_auth(self):
        for body in ('{"mode":"bundle","section":"home","platform":"android"}',
                     '{"mode":"bundle","section":"course","platform":"macos"}',
                     '{"mode":"bundle","section":"users","platform":"overall"}',
                     '{"mode":"bundle","section":"course"}',
                     '{"mode":"bundle","section":"course","platform":"overall","period":"weekly"}',
                     '{"mode":"manifest","x":1}',
                     '{"mode":"all"}'):
            self.assertEqual((await self.post(body)).status_code, 400, body)
        good = '{"mode":"bundle","section":"course","platform":"overall"}'
        self.assertEqual((await self.post(good, secret="wrong")).status_code, 401)
        self.assertEqual((await self.post(good, url="https://attacker.test")).status_code, 403)
        self.settings.ADMIN_PWA_MANUAL_AGGREGATE_REFRESH_TOKEN = ""
        self.assertEqual((await self.post(good)).status_code, 404)
        self.assertEqual(self.calls, [])


@unittest.skipUnless(URL, "set ANALYTICS_TEST_DATABASE_URL for the real PostgreSQL comparison")
class PostgresParityTests(unittest.IsolatedAsyncioTestCase):
    """Gate 2: bundle snapshots equal the unchanged V10 projections."""

    async def test_every_statistics_group_matches_the_unchanged_projection(self):
        from tests import test_admin_pwa_v10_regression as golden
        store = MemoryR2()
        clock = golden.NOW.timestamp()
        settings = SimpleNamespace(ADMIN_PWA_ENABLED=True, REDIS_URL="", ADMIN_PWA_PUBLIC_ORIGIN="https://hskai.app")
        async with golden.postgres_fixture(URL) as sessions:
            expected = await golden.capture(sessions)
            reader = AdminPwaAnalyticsReader(settings_obj=settings, session_factory=sessions,
                                             reader_options={"r2_store": store, "clock": lambda: clock})
            with patch.object(analytics, "datetime", wraps=datetime) as frozen:
                frozen.now.return_value = golden.NOW
                for group in GROUPS:
                    if group["section"] == "feedback":
                        continue
                    section_reader = reader._readers[group["section"]]
                    if group["section"] == "overview":
                        await section_reader.refresh_overview_bundle()
                    else:
                        result = await section_reader.refresh_section_bundle(
                            section=group["section"], platform=group["platform"], periods=group["periods"])
                        self.assertEqual(result["status"], "refreshed", group)
                    for period in group["periods"]:
                        raw = store.items[("statistics", section_reader._r2_namespace,
                                           group["platform"] + "_" + period)]
                        actual = golden.stable_response(json.loads(raw)["data"])
                        want = expected[group["section"], group["platform"], period]
                        self.assertEqual(actual, json.loads(json.dumps(want)), (group, period))
            await reader.aclose()

    async def test_feedback_bundle_matches_the_unchanged_loader(self):
        from tests import test_admin_pwa_v10_regression as golden
        store = MemoryR2()
        now = golden.NOW
        async with golden.postgres_fixture(URL) as sessions:
            reader = AdminPwaFeedbackReader(settings_obj=SimpleNamespace(ADMIN_PWA_ENABLED=True, REDIS_URL=""),
                                            session_factory=sessions, r2_store=store, clock=lambda: now.timestamp())
            with patch.object(feedback_module, "datetime", wraps=datetime) as frozen:
                frozen.now.return_value = now
                result = await reader.refresh_feedback_bundle(periods=("weekly", "monthly"))
                self.assertEqual(result["status"], "refreshed")
                async with sessions() as db:
                    for period in ("weekly", "monthly"):
                        query = feedback_module.FeedbackAnalyticsRequest(period=period, source="all")
                        direct = await feedback_module.feedback_analytics(db, query)
                        stored = json.loads(store.items[("feedback", reader._r2_namespace, "all_" + period)])
                        self.assertEqual(stored["data"], json.loads(json.dumps(direct)))

    async def test_advisory_lock_held_elsewhere_reports_busy(self):
        from tests import test_admin_pwa_v10_regression as golden
        store = MemoryR2()
        settings = SimpleNamespace(ADMIN_PWA_ENABLED=True, REDIS_URL="", ADMIN_PWA_PUBLIC_ORIGIN="https://hskai.app")
        async with golden.postgres_fixture(URL) as sessions:
            reader = AdminPwaAnalyticsReader(settings_obj=settings, session_factory=sessions,
                                             reader_options={"r2_store": store})
            course = reader._readers["course"]
            lock_id = int.from_bytes(hashlib.blake2b(course.prefix.encode(), digest_size=8).digest(),
                                     "big", signed=True)
            async with sessions() as holder:
                await holder.execute(text("SELECT pg_advisory_lock(:id)"), {"id": lock_id})
                try:
                    with self.assertRaisesRegex(StatisticsUnavailable, "in progress"):
                        await course.refresh_section_bundle(section="course", platform="overall",
                                                            periods=PERIODS)
                finally:
                    await holder.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": lock_id})
            self.assertEqual(store.puts, 0)
            done = await course.refresh_section_bundle(section="course", platform="overall", periods=PERIODS)
            self.assertEqual(done["status"], "refreshed")
            await reader.aclose()


if __name__ == "__main__":
    unittest.main()

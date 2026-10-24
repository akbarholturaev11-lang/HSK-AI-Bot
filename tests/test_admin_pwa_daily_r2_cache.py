"""Daily R2 cache tests use private fakes: no Cloudflare/billing/network."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import io
from types import SimpleNamespace
import unittest

from app.admin_api.pwa_feedback_analytics import FeedbackAnalyticsRequest
from app.admin_api.pwa_feedback_cache import AdminPwaFeedbackReader
from app.admin_api.pwa_r2_aggregate_store import PrivateR2AggregateStore, R2ConfigurationError
from app.admin_api.pwa_statistics_cache import AdminPwaStatisticsReader, SNAPSHOT_SECONDS
from app.admin_api.pwa_read import StatisticsRequest


class MemoryR2:
    enabled = True

    def __init__(self):
        self.items = {}
        self.gets = 0
        self.puts = 0

    async def get(self, **kwargs):
        self.gets += 1
        return self.items.get((kwargs["kind"], kwargs["namespace"], kwargs["variant"]))

    async def put(self, *, kind, namespace, variant, raw):
        self.puts += 1
        self.items[(kind, namespace, variant)] = raw


class DailyAggregateFixtures:
    def setUp(self):
        self.clock = datetime.now(timezone.utc).timestamp()
        self.counts = {"stats": 0, "feedback": 0}
        self.settings = SimpleNamespace(ADMIN_PWA_ENABLED=True, REDIS_URL="")
        self.r2 = MemoryR2()

    @asynccontextmanager
    async def sessions(self):
        @asynccontextmanager
        async def transaction():
            yield
        yield SimpleNamespace(begin=transaction,
                              get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="sqlite")))

    async def stats(self, db, query):
        self.counts["stats"] += 1
        return {"platform": query.platform, "period": query.period, "available": True,
                "generated_at": datetime.fromtimestamp(self.clock, timezone.utc).isoformat(),
                "metrics": {"users_total": self.counts["stats"]}}

    async def feedback(self, db, query):
        self.counts["feedback"] += 1
        source_keys = ("bot", "release", "android") if query.source == "all" else (query.source,)
        return {"schema": "hskai_feedback_categories_v1", "period": query.period,
                "source": query.source,
                "coverage": "most_recent_source_records_in_window",
                "sample_limit_per_source": 500,
                "historical_android_reports_complete": False,
                "generated_at": datetime.fromtimestamp(self.clock, timezone.utc).isoformat(),
                "since": datetime.fromtimestamp(self.clock-604800, timezone.utc).isoformat(),
                "until": datetime.fromtimestamp(self.clock, timezone.utc).isoformat(),
                "definitions": {"bot": "only fixed codes"},
                "sources": [{"source": source, "date_basis": "synthetic",
                             "records_scanned": 1, "truncated": False,
                             "categories": [{"category": "reported_issue" if source=="android"
                                             else "unclassified" if source=="bot" else "low_rating",
                                             "count": 1}]} for source in source_keys]}


class DailyAggregateR2Tests(DailyAggregateFixtures, unittest.IsolatedAsyncioTestCase):
    async def test_stats_existing_redis_reader_warms_from_private_r2_after_restart(self):
        args=dict(settings_obj=self.settings, session_factory=self.sessions,
                  loader=self.stats, clock=lambda: self.clock, r2_store=self.r2)
        first=AdminPwaStatisticsReader(**args)
        a=await first(StatisticsRequest())
        self.assertEqual(a["metrics"]["users_total"],1)
        self.assertEqual(self.r2.puts,1)
        second=AdminPwaStatisticsReader(**args)
        b=await second(StatisticsRequest())
        self.assertEqual(b["metrics"]["users_total"],1)
        self.assertEqual(self.counts["stats"],1)
        self.assertEqual(b["snapshot"]["refresh_interval_seconds"], SNAPSHOT_SECONDS)
        self.clock+=SNAPSHOT_SECONDS+1
        c=await second(StatisticsRequest())
        self.assertEqual(c["metrics"]["users_total"],2)
        self.assertEqual(self.counts["stats"],2)

    async def test_feedback_json_and_csv_share_one_daily_aggregate_across_workers(self):
        args=dict(settings_obj=self.settings, session_factory=self.sessions,
                  loader=self.feedback, clock=lambda: self.clock, r2_store=self.r2)
        first=AdminPwaFeedbackReader(**args)
        data=await first(FeedbackAnalyticsRequest())
        self.assertEqual(self.counts["feedback"],1)
        self.assertEqual(data["schema"],"hskai_feedback_categories_v1")
        self.assertEqual(data["snapshot"]["refresh_interval_seconds"], SNAPSHOT_SECONDS)
        restarted=AdminPwaFeedbackReader(**args)
        same=await restarted(FeedbackAnalyticsRequest())
        self.assertEqual(same,data)
        self.assertEqual(self.counts["feedback"],1)
        self.assertEqual(self.r2.gets,2)  # one initial miss, one restart warm
        self.assertEqual(self.r2.puts,1)
        other=await restarted(FeedbackAnalyticsRequest(source="bot"))
        self.assertEqual(other["source"],"bot")
        self.assertEqual(self.counts["feedback"],2)
        self.clock+=SNAPSHOT_SECONDS+1
        refreshed=await restarted(FeedbackAnalyticsRequest())
        self.assertNotEqual(refreshed["generated_at"],data["generated_at"])
        self.assertEqual(self.counts["feedback"],3)

    async def test_corrupt_private_r2_object_never_exposes_arbitrary_payload(self):
        reader=AdminPwaFeedbackReader(settings_obj=self.settings,session_factory=self.sessions,
                                      loader=self.feedback,clock=lambda:self.clock,r2_store=self.r2)
        self.r2.items[("feedback",reader._r2_namespace,"all_weekly")] = b'{"raw_feedback":"PRIVATE"}'
        data=await reader(FeedbackAnalyticsRequest())
        self.assertEqual(self.counts["feedback"],1)
        self.assertNotIn("raw_feedback",str(data))
        self.assertEqual(self.r2.puts,1)

    def test_private_r2_requires_all_config_values_before_constructing_client(self):
        cfg=SimpleNamespace(ADMIN_PWA_R2_AGGREGATE_ENABLED=True,
                            ADMIN_PWA_R2_ACCOUNT_ID="0123456789abcdef"*2,
                            ADMIN_PWA_R2_BUCKET="hsk-private-aggregate",
                            ADMIN_PWA_R2_ACCESS_KEY_ID="",
                            ADMIN_PWA_R2_SECRET_ACCESS_KEY="")
        with self.assertRaises(R2ConfigurationError):
            PrivateR2AggregateStore(settings_obj=cfg)

    async def test_r2_adapter_bounded_private_keys_and_bytes_no_public_url(self):
        class FakeBody:
            def __init__(self,raw): self.raw=raw
            def read(self,n): return self.raw[:n]
            def close(self): pass
        class FakeClient:
            def __init__(self): self.keys={};self.last=None
            def put_object(self,**kwargs):
                self.last=kwargs
                self.keys[kwargs["Key"]]=kwargs["Body"]
            def get_object(self,**kwargs):
                raw=self.keys[kwargs["Key"]]
                return {"Body":FakeBody(raw),"ContentLength":len(raw)}
        client=FakeClient()
        cfg=SimpleNamespace(ADMIN_PWA_R2_AGGREGATE_ENABLED=True,
                            ADMIN_PWA_R2_ACCOUNT_ID="0123456789abcdef"*2,
                            ADMIN_PWA_R2_BUCKET="hsk-private-aggregate",
                            ADMIN_PWA_R2_ACCESS_KEY_ID="TEST_VALUE",
                            ADMIN_PWA_R2_SECRET_ACCESS_KEY="TEST_VALUE")
        store=PrivateR2AggregateStore(settings_obj=cfg,client=client)
        payload=b'{"version":1}'
        await store.put(kind="feedback",namespace="0"*24,variant="all_weekly",raw=payload)
        self.assertEqual(await store.get(kind="feedback",namespace="0"*24,variant="all_weekly"),payload)
        self.assertEqual(client.last["CacheControl"],"private, no-store")
        self.assertEqual(client.last["ContentType"],"application/json")
        self.assertNotIn("ACL",client.last)
        with self.assertRaises(ValueError):
            await store.put(kind="feedback",namespace="0"*24,
                            variant="../forbidden",raw=payload)
        with self.assertRaises(ValueError):
            await store.put(kind="feedback",namespace="0"*24,variant="all_weekly",
                            raw=b"x"*(128*1024+1))

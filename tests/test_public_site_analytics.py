from contextlib import asynccontextmanager
from datetime import date, timedelta
from types import SimpleNamespace
import unittest

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects import postgresql
from starlette.requests import Request

from app.api.public_site import create_public_site_router, record_attributed_source_visit
from app.services.public_site_analytics_service import (
    PublicSiteAnalyticsService,
    normalize_public_site_source,
)


ORIGIN = "https://learn.example.com"


class RecordingSession:
    def __init__(self):
        self.statement = None
        self.committed = False
        self.rows = []

    async def execute(self, statement):
        self.statement = statement
        return SimpleNamespace(all=lambda: self.rows)

    async def commit(self):
        self.committed = True


class SessionFactory:
    def __init__(self):
        self.session = RecordingSession()

    @asynccontextmanager
    async def __call__(self):
        yield self.session


class PublicSiteAnalyticsTests(unittest.IsolatedAsyncioTestCase):
    def test_source_normalization(self):
        self.assertEqual(normalize_public_site_source(" Instagram "), "instagram")
        self.assertEqual(normalize_public_site_source("ig"), "instagram")
        self.assertEqual(normalize_public_site_source("TikTok"), "tiktok")
        self.assertEqual(normalize_public_site_source("yt"), "youtube")
        self.assertEqual(normalize_public_site_source("newsletter"), "other")
        self.assertIsNone(normalize_public_site_source("  "))

    async def test_record_source_visit_upserts_daily_source_count(self):
        session = RecordingSession()

        await PublicSiteAnalyticsService(session).record_source_visit(
            "instagram", today=date(2026, 10, 20)
        )

        compiled = str(session.statement.compile(dialect=postgresql.dialect()))
        self.assertIn("ON CONFLICT (visit_day, source) DO UPDATE", compiled)
        self.assertIn("visits = (public_site_traffic_daily.visits +", compiled)
        self.assertEqual(session.statement.compile().params["source"], "instagram")
        self.assertEqual(session.statement.compile().params["visits"], 1)
        self.assertTrue(session.committed)

    async def test_attributed_download_visit_is_counted(self):
        factory = SessionFactory()
        request = Request({"type": "http", "query_string": b"utm_source=instagram"})

        await record_attributed_source_visit(request, factory)

        self.assertEqual(factory.session.statement.compile().params["source"], "instagram")
        self.assertTrue(factory.session.committed)

    async def test_source_stats_returns_all_buckets_and_window_totals(self):
        session = RecordingSession()
        session.rows = [SimpleNamespace(
            source="instagram", visits_7_days=3, visits_30_days=8, visits_all_time=11
        )]

        rows = await PublicSiteAnalyticsService(session).source_stats(
            today=date(2026, 10, 20)
        )

        self.assertEqual(rows[0], {
            "source": "instagram",
            "label": "Instagram",
            "visits_7_days": 3,
            "visits_30_days": 8,
            "visits_all_time": 11,
        })
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row["visits_all_time"] == 0 for row in rows[1:]))
        params = session.statement.compile().params
        self.assertIn(date(2026, 10, 20) - timedelta(days=6), params.values())
        self.assertIn(date(2026, 10, 20) - timedelta(days=29), params.values())

    async def test_only_tagged_root_gets_are_counted(self):
        factory = SessionFactory()
        app = FastAPI()
        app.include_router(create_public_site_router(
            settings_obj=SimpleNamespace(PUBLIC_SITE_URL=ORIGIN, INDEXNOW_KEY=""),
            session_factory=factory,
        ))

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=ORIGIN
        ) as client:
            response = await client.get("/?utm_source=ig")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(factory.session.statement.compile().params["source"], "instagram")
            self.assertTrue(factory.session.committed)

            factory.session.statement = None
            factory.session.committed = False
            other_page = await client.get("/tj/?utm_source=tiktok")
            self.assertEqual(other_page.status_code, 200)
            self.assertIsNone(factory.session.statement)

            head_response = await client.head("/?utm_source=youtube")
            self.assertEqual(head_response.status_code, 200)
            self.assertIsNone(factory.session.statement)


if __name__ == "__main__":
    unittest.main()

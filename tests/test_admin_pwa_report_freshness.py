"""Task 5.2: Report freshness per platform from verified signals (design D7).

Stored-row evidence on a disposable PostgreSQL schema.
Run with ANALYTICS_TEST_DATABASE_URL.
"""
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.admin_api import pwa_analytics_cache as analytics
from app.admin_api.pwa_analytics_freshness import platform_freshness
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.course_miniapp_event import CourseMiniAppEvent as Event
from app.db.models.payment import Payment
from app.db.models.user import User
from app.services.monitoring.intake import ingest, ingest_server, parse_batch
from tests.monitoring_chain import client_event

URL = os.environ.get("ANALYTICS_TEST_DATABASE_URL", "")
NOW = datetime.now(timezone.utc).replace(microsecond=0)
ORPHAN_TELEGRAM_ID = 777001
SECRETS = (str(ORPHAN_TELEGRAM_ID), "pwa-course-v3:", "fresh-qa", '"client"', "999")


def ago(**delta):
    return NOW - timedelta(**delta)


def tagged(name, client, at, **owner):
    # The route-set final key, as the Telegram/PWA/Android routes append it.
    return Event(event_name=name, created_at=at, payload_json=json.dumps({"level": "hsk1", "client": client},
                                                                         separators=(",", ":")), **owner)


def payment(source, at, **owner):
    return Payment(amount=10, currency="USD", plan_type="1_month", payment_status="approved",
                   payment_method="lava", source=source, submitted_at=at, **owner)


@unittest.skipUnless(URL.startswith("postgresql+asyncpg://"), "set ANALYTICS_TEST_DATABASE_URL")
class ReportFreshnessTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.schema = "freshness_" + uuid4().hex
        self.engine = create_async_engine(URL, connect_args={"server_settings": {"search_path": self.schema}})
        async with self.engine.begin() as connection:
            await connection.execute(text("CREATE SCHEMA " + self.schema))
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as db:
            db.add_all([User(id=1, telegram_id=1001, status="free"), User(id=2, telegram_id=None, status="free"),
                        User(id=3, telegram_id=1003, status="free")])
            await db.flush()
            db.add_all([
                # Android went quiet ten days ago: its open and its course completion.
                Event(user_id=3, event_name="android_app_opened", source="android_app", created_at=ago(days=10)),
                Event(user_id=3, event_name="lesson_completed", source="android_course", lesson_order=1,
                      created_at=ago(days=10, hours=1)),
                # A Telegram client can write android_play_opened; it is not Android.
                Event(user_id=1, event_name="android_play_opened", created_at=ago(minutes=5)),
                # Telegram: an owned completion, and an unowned row whose Telegram ID matches nobody.
                tagged("lesson_completed", "telegram", ago(hours=1), user_id=1),
                tagged("test_completed", "telegram", ago(hours=3), telegram_id=ORPHAN_TELEGRAM_ID),
                # PWA: a route-owned map open; a Telegram lookalike without the prefix is not PWA.
                Event(user_id=2, event_name="miniapp_opened", source="pwa_course_v3",
                      dedupe_key="pwa-course-v3:fresh-qa", created_at=ago(hours=2)),
                Event(user_id=1, event_name="miniapp_opened", source="pwa_course_v3", created_at=ago(minutes=10)),
                # Server bookkeeping is no platform's activity; future rows are not counted.
                Event(user_id=1, event_name="app_telegram_feedback_reserved", source="activity_feedback_server",
                      dedupe_key="feedback:1", created_at=ago(minutes=1)),
                tagged("lesson_completed", "iphone_pwa", NOW + timedelta(hours=1), user_id=2),
                payment("android", ago(days=5), user_id=3),
                payment("miniapp", ago(hours=4), user_id=999),
                payment("telegram_bot", ago(hours=6), user_telegram_id=1001),
                payment("pwa", ago(days=1), user_id=2),
                payment("desktop", ago(minutes=1), user_id=1),
            ])
            await db.commit()
        async with self.sessions() as db, db.begin():
            data = client_event("lessons", "js_uncaught", "course_v3", "iphone_pwa")
            events, _ = parse_batch({"schema": "diag.v1", "events": [data]}, platform="iphone_pwa")
            await ingest(db, owner_user_id=2, events=events, now=ago(hours=3))
            await ingest_server(db, feature_code="lessons", failure_code="server_5xx",
                                site_code="v3_pwa_map", platform="iphone_pwa", now=ago(minutes=1))

    async def asyncTearDown(self):
        async with self.engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA IF EXISTS " + self.schema + " CASCADE"))
        await self.engine.dispose()

    async def freshness(self):
        async with self.sessions() as db:
            rows = await platform_freshness(db, now=NOW)
        return {(row["platform"], row["source"]): (datetime.fromisoformat(row["latest_at"]) if row["latest_at"] else None,
                                                   row["unresolved_owners"]) for row in rows}

    async def test_each_platform_shows_its_own_latest_record_and_unresolved_owners(self):
        self.assertEqual(await self.freshness(), {
            # The stale platform stays visible with its own old timestamp.
            ("android", "learning"): (ago(days=10), 0), ("android", "payments"): (ago(days=5), 0),
            ("telegram", "learning"): (ago(hours=1), 1), ("telegram", "payments"): (ago(hours=4), 1),
            ("iphone_pwa", "learning"): (ago(hours=2), 0), ("iphone_pwa", "payments"): (ago(days=1), 0),
            ("android", "diagnostics"): (None, 0), ("telegram", "diagnostics"): (None, 0),
            ("iphone_pwa", "diagnostics"): (ago(hours=3), 0),
        })

    async def test_a_platform_without_records_reports_none_not_zero_time(self):
        async with self.sessions() as db:
            await db.execute(text("DELETE FROM payments WHERE source = 'pwa'"))
            await db.commit()
        self.assertEqual((await self.freshness())[("iphone_pwa", "payments")], (None, 0))

    async def test_a_lookalike_before_the_clients_first_server_tag_never_dates_it(self):
        # Audit #37: a caller could store `"client":"iphone_pwa"` before route
        # tagging was live. Without a server-built PWA row it is not PWA activity.
        async with self.sessions() as db:
            db.add(tagged("lesson_started", "iphone_pwa", ago(minutes=30), user_id=2))
            await db.commit()
        self.assertEqual((await self.freshness())[("iphone_pwa", "learning")], (ago(hours=2), 0))
        async with self.sessions() as db:
            db.add(tagged("test_completed", "iphone_pwa", ago(minutes=40), user_id=2))
            await db.commit()
        # From the first server-built tagged row on, tagged starts date PWA too.
        self.assertEqual((await self.freshness())[("iphone_pwa", "learning")], (ago(minutes=30), 0))

    async def test_report_carries_it_under_overall_without_identifiers_or_payloads(self):
        async with self.sessions() as db:
            report = await analytics.section_projection(
                db, analytics.AnalyticsRequest(section="report", platform="overall", period="weekly"), section="report")
        rows = report["metrics"]["platform_freshness"]
        self.assertEqual([(row["platform"], row["source"]) for row in rows],
                         [(p, s) for p in ("android", "telegram", "iphone_pwa") for s in ("learning", "payments", "diagnostics")])
        self.assertEqual({key for row in rows for key in row}, {"platform", "source", "latest_at", "unresolved_owners"})
        encoded = json.dumps(rows)
        for secret in SECRETS:
            self.assertNotIn(secret, encoded)
        # The legacy quality list is unchanged and still counts every stored row.
        learning = next(row for row in report["metrics"]["quality"] if row["source"] == "learning")
        self.assertEqual(learning["records"], 8)


if __name__ == "__main__":
    unittest.main()

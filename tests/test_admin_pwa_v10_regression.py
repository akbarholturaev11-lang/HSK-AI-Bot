"""V10 stored-row baseline on a disposable TCP PostgreSQL database.

Set ANALYTICS_TEST_DATABASE_URL to an asyncpg URL for a fresh loopback *_test
database. This test uses an isolated schema and never loads app.main or live
data. The golden was captured at origin/main 680761f1 before any V10 repair.
It is projection evidence, not a writer-to-browser chain test.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from itertools import product
import json
import os
from pathlib import Path
from typing import get_args
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.admin_api import pwa_analytics_cache as analytics
from app.admin_api.pwa_read import read_transaction
from app.db import models  # noqa: F401 -- register ORM foreign-key targets
from app.db.base import Base
from app.db.models.ai_usage import AIUsageEvent
from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.desktop import DesktopDevice
from app.db.models.lava import LavaInvoice
from app.db.models.message import Message
from app.db.models.payment import Payment
from app.db.models.portfolio import PortfolioTransaction
from app.db.models.public_site_traffic import PublicSiteTrafficDaily
from app.db.models.subscription_entry_event import SubscriptionEntryEvent
from app.db.models.user import User
from app.db.models.user_client_presence import UserClientPresence
from app.db.models.voice_practice_session import VoicePracticeSession

NOW = datetime(2026, 11, 12, 12, tzinfo=timezone.utc)
URL = os.getenv("ANALYTICS_TEST_DATABASE_URL")
SNAPSHOT = Path(__file__).with_name("fixtures") / "admin_pwa_v10_main_680761f1.json"
PRIVATE = "synthetic-private-marker"
BASELINE = "680761f15e05f6d543da52cd021d05df41217ea3"
SINCE = {"weekly": "2026-11-05T12:00:00+00:00", "monthly": "2026-10-13T12:00:00+00:00", "all_time": None}
# Section/filter cells that task 3.2 moved from `attribution_not_audited` to a
# platform predicate. Every other cell must stay byte-identical to the golden.
NEWLY_ATTRIBUTED = frozenset(("money", platform) for platform in ("android", "telegram", "iphone_pwa"))


def ago(*, days=0, hours=0, minutes=0):
    return NOW - timedelta(days=days, hours=hours, minutes=minutes)


def stored_event(name, at, *, user_id=1, source="course_miniapp", **fields):
    payload = fields.pop("payload", {})
    return CourseMiniAppEvent(event_name=name, user_id=user_id, source=source, created_at=at,
                              payload_json=json.dumps({"note": PRIVATE, **payload}), **fields)


async def seed(sessions):
    async with sessions() as db:
        db.add_all([
            User(id=1, telegram_id=1001, full_name=PRIVATE, status="active", payment_status="approved",
                 level="hsk1", language="uz", created_at=ago(days=3), last_active_at=ago(hours=1),
                 end_date=ago(days=-2)),
            User(id=2, telegram_id=1002, status="free", level="nhsk2", language="ru",
                 created_at=ago(days=10), last_active_at=ago(days=9), bot_blocked_at=ago(days=8)),
            User(id=3, status="free", level="hsk1", language="tj", created_at=ago(days=45),
                 last_active_at=ago(days=40)),
            User(id=4, status="free", level="hsk1", language="uz", created_at=ago(days=-1)),
        ])
        await db.flush()

        # A1–A5 and A20: one account has two Android devices, Mini App presence
        # on two platforms and a PWA sign-in; inventory is separate from use.
        for device, user_id, platform, version, days in (
            ("android-a", 1, "android", "1.2.3", 0),
            ("android-b", 1, "android", "1.2.3", 1),
            ("android-old", 3, "android", "1.1.0", 40),
            ("pwa-sign-in", 1, "pwa", "0.0.0", 2),
            ("mac-old", 2, "macos", "2.0.1", 9),
            ("win-old", 2, "windows", "2.0.2", 31),
        ):
            db.add(DesktopDevice(id=device, user_id=user_id, platform=platform,
                                 app_version=version, installation_key_hash=f"{PRIVATE}-{device}",
                                 created_at=ago(days=days), last_seen_at=ago(days=days)))
        for platform, days in (("android", 0), ("ios", 2)):
            db.add(UserClientPresence(user_id=1, telegram_id=1001, surface="telegram_miniapp",
                                      platform=platform, first_seen_at=ago(days=3),
                                      last_seen_at=ago(days=days), last_foreground_at=ago(days=days)))
        db.add_all([
            stored_event("android_first_open", ago(days=2), source="android_app"),
            stored_event("android_app_opened", ago(hours=5), source="android_app"),
            stored_event("android_app_opened", ago(days=40), user_id=3, source="android_app"),
            stored_event("android_app_opened", ago(days=44), user_id=3, source="android_app"),
            stored_event("desktop_app_opened", ago(days=9), user_id=2, source="desktop_macos",
                         payload={"platform": "macos"}),
            stored_event("desktop_active_day", ago(days=11), user_id=2, source="desktop_windows",
                         payload={"platform": "windows"}),
            stored_event("miniapp_opened", ago(days=2), source="pwa_course_v3",
                         level="hsk1", session_id="pwa-map-fixture", dedupe_key="pwa-course-v3:miniapp-opened:pwa-map-fixture"),
            stored_event("miniapp_opened", ago(days=2, hours=-1), source="course_v3"),
            stored_event("miniapp_opened", ago(days=3), user_id=2, source="course_v3"),
            # The Telegram map could store the same source, but retains its own dedupe prefix.
            stored_event("miniapp_opened", ago(days=3, hours=-1), user_id=2, source="pwa_course_v3",
                         level="hsk1", session_id="telegram-map-fixture",
                         dedupe_key="course-v3:miniapp-opened:telegram-map-fixture"),
            stored_event("pwa_handoff_issued", ago(days=1, hours=1)),
            stored_event("pwa_handoff_completed", ago(days=1)),
            stored_event("android_play_opened", ago(days=1)),
        ])

        # A6–A17: legacy shared writes have no client key. Android start
        # and split-by-distribution have no writer, so don't fabricate rows.
        lesson = {"level": "hsk1", "lesson_order": 1, "session_id": "lesson-session-fixture"}
        db.add_all([
            stored_event("onboarding_completed", ago(days=2, hours=1), source="pwa_course_v3",
                         payload={"activation_variant": "direct_start_v1", "transport": "iphone_pwa"}),
            # Canonical Android guest completion belongs to activation overall, outside direct-start.
            stored_event("onboarding_completed", ago(days=5), user_id=2, source="course_onboarding",
                         dedupe_key="onboarding:2:completed", payload={"activation_variant": "native_li_guest_v1"}),
            stored_event("lesson_started", ago(days=2, minutes=59), **lesson),
            stored_event("section_started", ago(days=2, minutes=58), source="pwa_course_v3",
                         payload={"transport": "iphone_pwa"}, **lesson),
            stored_event("section_started", ago(days=2, minutes=57), source="course_miniapp", **lesson),
            stored_event("lesson_completed", ago(days=2, minutes=55), source="course_v3", **lesson),
            stored_event("lesson_completed", ago(days=2, minutes=54), source="android_course", **lesson),
            stored_event("lesson_completed", ago(days=10), user_id=None, telegram_id=1002,
                         source="course_v3", level="hsk1", lesson_order=2),
            stored_event("lesson_completed", ago(days=40), user_id=3, source="android_course",
                         level="hsk1", lesson_order=1),
            stored_event("lesson_completed", ago(days=-1), user_id=4, level="hsk1", lesson_order=3),
            stored_event("lesson_started", ago(hours=4), user_id=None, telegram_id=1999),
            stored_event("training_started", ago(hours=4), telegram_id=1002, source="smart_practice_v2"),
            stored_event("training_completed", ago(hours=3), source="smart_practice_v2"),
            stored_event("test_started", ago(days=10), user_id=2, source="course_hsk_exam"),
            stored_event("test_completed", ago(days=9), user_id=2, source="course_hsk_exam"),
            stored_event("mistake_review_started", ago(hours=7)),
            stored_event("mistake_review_completed", ago(hours=6)),
            stored_event("voice_started", ago(hours=4), source="course_voice",
                         session_id="voice-fixture", dedupe_key="voice-fixture",
                         payload={"role": "daily", "transport": "iphone_pwa"}),
            stored_event("voice_completed", ago(hours=3, minutes=58), source="course_voice",
                         session_id="voice-fixture", dedupe_key="voice-fixture",
                         payload={"duration_seconds": 120, "transport": "iphone_pwa"}),
            VoicePracticeSession(id="voice-fixture", user_id=1, role="daily", level="hsk1",
                                 language="uz", voice="default", status="completed", turn_count=1,
                                 started_at=ago(hours=4), ended_at=ago(hours=3, minutes=58), history=[PRIVATE]),
            # Entry then immediate end can still produce a completed session. It
            # counts as feature participation for this free account but adds no minutes.
            VoicePracticeSession(id="voice-zero-turn-fixture", user_id=2, role="daily", level="nhsk2",
                                 language="ru", voice="default", status="completed", turn_count=0,
                                 started_at=ago(minutes=20), ended_at=ago(minutes=19)),
            # Server-only reservation advances stored learning freshness, not activity.
            CourseMiniAppEvent(event_name="app_telegram_feedback_reserved", user_id=1,
                               source="activity_feedback_server", dedupe_key="feedback:1",
                               created_at=ago(minutes=1)),
            Message(user_id=1, role="user", content=PRIVATE, created_at=ago(hours=3)),
            Message(user_id=1, role="assistant", content=PRIVATE, created_at=ago(hours=3)),
            AIUsageEvent(user_id=1, source="qa", model="gemini-2.5-flash", billing_tier="paid_estimate",
                         cost_usd=0.25, total_tokens=120, created_at=ago(hours=3)),
            AIUsageEvent(user_telegram_id=1002, source="voice_live_audio", model="gemini-2.5-flash",
                         billing_tier="paid_estimate", cost_usd=0.10, total_tokens=40, created_at=ago(days=10)),
            AIUsageEvent(user_telegram_id=1999, source="qa", model=PRIVATE, billing_tier="unpriced",
                         total_tokens=12, created_at=ago(days=40)),
        ])
        for user_id, source, days in ((1, "pwa_course_v3", 2), (2, "course_v3", 9), (3, "android_course", 40)):
            fields = {"user_id": user_id, "source": source, "payload": {"foundation_version": 1}}
            db.add(stored_event("foundation_started", ago(days=days, hours=2), **fields))
            if user_id != 2:
                db.add(stored_event("foundation_completed", ago(days=days, hours=1), **fields))

        # F1–F8: mixed payment histories (including orphaned, pending, and
        # reversed), legacy checkout attempts and PWA Pro rows with a ledger link.
        def payment(user_id, source, at, *, status="approved", currency="USD", method="visa",
                    amount=10, telegram_id=None, **fields):
            row = Payment(user_id=user_id, user_telegram_id=telegram_id, source=source, currency=currency,
                          amount=amount, plan_type="1_month", payment_method=method, payment_status=status,
                          submitted_at=at, reviewed_at=at if status != "pending" else None, **fields)
            db.add(row)
            return row

        payment(3, "android", ago(days=42))
        payment(None, "telegram_bot", ago(days=8), currency="TJS", amount=100, telegram_id=1002)
        payment(None, "telegram_bot", ago(days=2), currency="unknown", telegram_id=1999)
        miniapp = payment(1, "miniapp", ago(hours=5))
        payment(1, "iphone_pwa", ago(hours=3), status="pending")
        payment(1, "iphone_pwa", ago(days=1), currency="TJS", amount=80)
        android = payment(1, "android", ago(hours=2), method="lava")
        pwa = payment(1, "pwa", ago(hours=1), method="lava", local_currency="USD", local_amount="7.90")
        reversed_payment = payment(2, "pwa", ago(days=9), method="lava", status="refunded")
        await db.flush()
        db.add_all([
            LavaInvoice(contract_id="android-fixture", user_id=1, source="android", currency="USD",
                        status="paid", kind="first", payment_id=android.id, paid_at=ago(hours=2),
                        created_at=ago(hours=3), updated_at=ago(hours=2)),
            LavaInvoice(contract_id="pwa-fixture", user_id=1, source="pwa", currency="USD",
                        status="paid", kind="first", payment_id=pwa.id, paid_at=ago(hours=1),
                        created_at=ago(hours=2), updated_at=ago(hours=1), pwa_inline_attempt_id="pro-fixture"),
            LavaInvoice(contract_id="refund-fixture", user_id=2, source="pwa", currency="USD",
                        status="refunded", kind="first", payment_id=reversed_payment.id, revoked_at=ago(days=8),
                        created_at=ago(days=9), updated_at=ago(days=8)),
            LavaInvoice(contract_id="renewal-fixture", user_id=2, source="miniapp", currency="USD",
                        status="paid", kind="renewal", paid_at=ago(days=8),
                        created_at=ago(days=9), updated_at=ago(days=8)),
        ])

        def funnel(name, source, attempt, at, *, payment_id=None, **payload):
            db.add(ConversionFunnelEvent(event_name=name, user_id=1, source=source,
                payment_id=payment_id, payload_json=json.dumps({"attempt_id": attempt, "note": PRIVATE, **payload}),
                created_at=at))

        funnel("checkout_opened", "subscription_miniapp", "miniapp-fixture", ago(hours=8))
        funnel("payment_screenshot_submitted", "subscription_miniapp", "miniapp-fixture",
               ago(hours=6), payment_id=miniapp.id)
        funnel("payment_approved", "subscription_miniapp", "miniapp-fixture", ago(hours=5), payment_id=miniapp.id)
        funnel("checkout_opened", "android_subscription", "android-lava-fixture", ago(hours=3))
        funnel("checkout_opened", "iphone_pwa", "pwa-manual-fixture", ago(hours=4), transport="iphone_pwa")
        for name, hour in (("opened", 6), ("plan_selected", 5), ("checkout_started", 2), ("checkout_paid", 1)):
            funnel(f"pwa_pro_{name}", "iphone_pwa", "pro-fixture", ago(hours=hour),
                   payment_id=pwa.id if name == "checkout_paid" else None, transport="iphone_pwa")

        db.add_all([
            SubscriptionEntryEvent(user_id=1, source="android_subscription", created_at=ago(days=1)),
            SubscriptionEntryEvent(user_id=1, source="iphone_pwa", created_at=ago(hours=4)),
            SubscriptionEntryEvent(user_id=None, telegram_id=1002, source="profile", created_at=ago(days=9)),
            SubscriptionEntryEvent(user_id=1, source=PRIVATE, created_at=ago(hours=7)),
            PortfolioTransaction(transaction_type="profit", source="manual_profit", amount_usd=4, created_at=ago(hours=3)),
            PortfolioTransaction(transaction_type="expense", source="marketing", note=PRIVATE, amount_usd=2,
                                 created_at=ago(days=8)),
            PublicSiteTrafficDaily(visit_day=NOW.date(), source="youtube", visits=7),
            PublicSiteTrafficDaily(visit_day=ago(days=9).date(), source="instagram", visits=3),
            stored_event("d1_recovery_assigned", ago(days=3), source="d1_recovery_v1", payload={"arm": "treatment"}),
            stored_event("d1_recovery_assigned", ago(days=9), user_id=2, source="d1_recovery_v1",
                         payload={"arm": "control"}),
        ])
        await db.commit()


@asynccontextmanager
async def postgres_fixture(url):
    parsed = urlsplit(url)
    if (parsed.scheme != "postgresql+asyncpg" or parsed.hostname not in {"127.0.0.1", "::1", "localhost"}
            or not parsed.port or not parsed.path.endswith("_test") or parsed.query or parsed.fragment):
        raise ValueError("ANALYTICS_TEST_DATABASE_URL must name a disposable *_test database over loopback TCP")
    schema = "admin_v10_test_" + uuid4().hex
    engine = create_async_engine(url, connect_args={"server_settings": {
        "search_path": schema, "timezone": "UTC",
    }})
    created = False
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f"CREATE SCHEMA {schema}"))
            await connection.run_sync(Base.metadata.create_all)
        created = True
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        await seed(sessions)
        yield sessions
    finally:
        try:
            if created:
                async with engine.begin() as connection:
                    await connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        finally:
            await engine.dispose()


def stable_response(response):
    """Only order unordered grouped SQL lists; preserve calendar and funnel order."""
    metrics = response["metrics"]
    if metrics is not None:
        for key, fields in {
            "currencies": ("currency",), "ai_models": ("model", "tier", "requests", "tokens", "usd"),
            "entries": ("source",), "attribution": ("source",), "traffic": ("source",),
        }.items():
            if isinstance(metrics.get(key), list):
                metrics[key].sort(key=lambda row: tuple(row[field] for field in fields))
        if "versions" in metrics:
            order = {"android": 0, "macos": 1, "windows": 2}
            metrics["versions"].sort(key=lambda row: (order[row["platform"]], -row["devices"], row["version"], row["accounts"]))
    return response


def projection_requests():
    fields = analytics.AnalyticsRequest.model_fields
    return product(get_args(analytics.Section), get_args(fields["platform"].annotation),
                   get_args(fields["period"].annotation))


async def capture(sessions):
    results = {}
    async with sessions() as db, read_transaction(db):
        with patch.object(analytics, "datetime", wraps=datetime) as clock:
            clock.now.return_value = NOW
            for section, platform, period in projection_requests():
                query = analytics.AnalyticsRequest(section=section, platform=platform, period=period)
                response = await analytics.section_projection(db, query, section=section)
                results[section, platform, period] = stable_response(response)
    return results


@unittest.skipUnless(URL, "set ANALYTICS_TEST_DATABASE_URL for the real PostgreSQL baseline")
class AdminPwaV10RegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_projection_matrix_matches_unchanged_main(self):
        async with postgres_fixture(URL) as sessions:
            actual = await capture(sessions)
        golden = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        self.assertEqual(golden["origin_main"], BASELINE)
        expected = {}
        # Profiles share identical bodies. Reconstruct the pinned envelope fields
        # from the listed matrix cells so even unavailable responses are compared.
        for profile in golden["profiles"]:
            body = profile["response"]
            for scope in profile["scopes"]:
                section, platform, period = case = tuple(scope.split(":"))
                self.assertNotIn(case, expected)
                expected[case] = {**body, "platform": platform, "period": period,
                    "since": SINCE[period], "generated_at": NOW.isoformat(),
                    "scope": {**body["scope"], "section": section}}
        self.assertEqual(len(expected), 162)
        self.assertEqual(actual.keys(), expected.keys())
        for case, response in actual.items():
            with self.subTest(section=case[0], platform=case[1], period=case[2]):
                self.assertNotIn(PRIVATE, json.dumps(response))
                if case[:2] in NEWLY_ATTRIBUTED:
                    # The baseline had no value here. Only the unavailable
                    # envelope may change; values are pinned in the 3.2 tests.
                    self.assertEqual((expected[case]["available"], expected[case]["reason"]),
                                     (False, "attribution_not_audited"))
                    self.assertIs(response["available"], True)
                    continue
                legacy = {key: value for key, value in response.items() if key != "metric_states"}
                self.assertEqual(legacy, expected[case])

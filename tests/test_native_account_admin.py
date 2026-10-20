"""Provider-only accounts cannot break admin lists or merge analytics users."""

import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.payment import Payment
from app.db.models.subscription_entry_event import SubscriptionEntryEvent
from app.db.models.user import User
from app.services.admin_hsk30_analytics_service import AdminHsk30AnalyticsService
from app.services.hsk30_unlock_service import HSK30_UNLOCK_PLAN_TYPE


class NativeAccountAdminTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            # Internal account 1 must never collide with another account's
            # genuine Telegram identity 1.
            session.add_all([
                User(id=uid, telegram_id=tid, full_name=name, language="uz", status="free",
                     payment_status="none", created_at=self.now, last_active_at=self.now)
                for uid, tid, name in ((1, None, "Google learner"), (2, 1, "Telegram learner"), (3, None, "Apple learner"))
            ])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_admin_search_keeps_native_accounts_and_real_payment_targets_separate(self):
        from tests.test_main_imports import MainModuleImportTests

        main = MainModuleImportTests._import_main()

        async with self.sessions() as session:
            session.add(Payment(user_telegram_id=1, plan_type="1_month", amount=100,
                                currency="TJS", payment_status="pending"))
            await session.commit()
        app = FastAPI()
        app.add_api_route("/users/search", main.admin_miniapp_users_search, methods=["POST"])
        with patch.object(main, "async_session_maker", self.sessions), \
                patch.object(main, "_admin_miniapp_user_id", return_value=777), \
                patch.object(main, "_admin_auth_error", return_value=None):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="https://admin.test") as client:
                response = await client.post("/users/search", json={"limit": 60})
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["total"], 3)
        rows = {row["name"]: row for row in payload["users"]}
        self.assertEqual(len(rows), 3)
        for name, uid in (("Google learner", 1), ("Apple learner", 3)):
            self.assertIsNone(rows[name]["id"])
            self.assertEqual(rows[name]["account_id"], uid)
            self.assertFalse(rows[name]["has_pending_payment"])
        self.assertEqual(rows["Telegram learner"]["id"], 1)
        self.assertEqual(rows["Telegram learner"]["account_id"], 2)
        self.assertTrue(rows["Telegram learner"]["has_pending_payment"])

    async def test_hsk30_funnel_counts_native_users_and_preserves_telegram_payment_resolution(self):
        async with self.sessions() as session:
            # Mixed legacy/canonical metadata for the same real Telegram user
            # must still count once, while independent NULL identities count
            # as independent learners.
            for uid, tid in ((1, None), (None, 1)):
                for offset, name in enumerate(("hsk30_promo_shown", "hsk30_promo_cta_clicked", "hsk30_level_selected", "course_track_switched")):
                    session.add(CourseMiniAppEvent(user_id=uid, telegram_id=tid, event_name=name,
                        payload_json=json.dumps({"to_track": "hsk30"}) if name == "course_track_switched" else "{}",
                        created_at=self.now - timedelta(minutes=20-offset)))
            session.add(CourseMiniAppEvent(user_id=2, telegram_id=1, event_name="hsk30_promo_shown",
                                          created_at=self.now - timedelta(minutes=21)))
            session.add(CourseMiniAppEvent(user_id=3, telegram_id=None, event_name="hsk30_level_selected",
                                          created_at=self.now - timedelta(minutes=5)))
            session.add(CourseMiniAppEvent(user_id=3, telegram_id=None, event_name="hsk30_checkout_failed",
                payload_json=json.dumps({"stage": "provider", "error": "payment_telegram_required"}),
                created_at=self.now - timedelta(minutes=4)))
            session.add(SubscriptionEntryEvent(user_id=2, telegram_id=1, source=HSK30_UNLOCK_PLAN_TYPE,
                                              mode=HSK30_UNLOCK_PLAN_TYPE, created_at=self.now - timedelta(minutes=10)))
            payment = Payment(user_telegram_id=1, plan_type=HSK30_UNLOCK_PLAN_TYPE, amount=10,
                currency="TJS", payment_status="approved", payment_method="visa",
                submitted_at=self.now - timedelta(minutes=2), reviewed_at=self.now - timedelta(minutes=1))
            session.add(payment)
            await session.flush()
            for uid, tid in ((1, None), (2, 1)):
                session.add(ConversionFunnelEvent(user_id=uid, telegram_id=tid, event_name="checkout_opened",
                    source=HSK30_UNLOCK_PLAN_TYPE, payload_json=json.dumps({"attempt_id": "shared-attempt", "mode": HSK30_UNLOCK_PLAN_TYPE}),
                    created_at=self.now - timedelta(minutes=9)))
            session.add(ConversionFunnelEvent(user_id=2, telegram_id=1, event_name="payment_screenshot_submitted",
                payment_id=payment.id, source=HSK30_UNLOCK_PLAN_TYPE,
                payload_json=json.dumps({"attempt_id": "shared-attempt", "mode": HSK30_UNLOCK_PLAN_TYPE}),
                created_at=self.now - timedelta(minutes=2)))
            await session.commit()
        async with self.sessions() as session:
            result = await AdminHsk30AnalyticsService(session).snapshot(days=30)
        self.assertEqual([stage["users"] for stage in result["course_funnel"]], [2, 2, 2, 2])
        self.assertEqual(result["promo_impressions"], 3)
        self.assertEqual(result["payment_funnel"][0]["attempts"], 2)
        self.assertEqual(result["payment_funnel"][-1]["attempts"], 1)
        self.assertEqual(result["payments"]["approved"], 1)
        rows = {row["user_id"]: row for row in result["users"]}
        self.assertEqual(set(rows), {1, 2, 3})
        self.assertEqual((rows[1]["telegram_id"], rows[1]["name"], rows[1]["status"]), (None, "Google learner", "not_submitted"))
        self.assertEqual((rows[2]["telegram_id"], rows[2]["name"], rows[2]["status"]), (1, "Telegram learner", "approved"))
        self.assertIsNone(rows[3]["telegram_id"])
        self.assertEqual(rows[3]["last_step"], "checkout_failed")
        self.assertEqual(result["checkout_failures"], [{"reason": "provider: payment_telegram_required", "count": 1}])

    async def test_hsk30_events_without_any_owner_are_skipped_without_merging_native_accounts(self):
        async with self.sessions() as session:
            session.add(CourseMiniAppEvent(user_id=None, telegram_id=None, event_name="hsk30_promo_shown"))
            session.add(ConversionFunnelEvent(user_id=None, telegram_id=None, event_name="checkout_opened",
                source=HSK30_UNLOCK_PLAN_TYPE, payload_json=json.dumps({"attempt_id": "orphan", "mode": HSK30_UNLOCK_PLAN_TYPE})))
            await session.commit()
            result = await AdminHsk30AnalyticsService(session).snapshot()
        self.assertEqual(result["users"], [])
        self.assertEqual(result["promo_impressions"], 0)
        self.assertEqual([stage["users"] for stage in result["course_funnel"]], [0, 0, 0, 0])

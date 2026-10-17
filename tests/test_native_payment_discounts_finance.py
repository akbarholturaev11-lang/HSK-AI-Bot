"""Canonical checkout discounts and finance must keep account boundaries."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.discount_campaign import DiscountCampaign
from app.db.models.payment import Payment
from app.db.models.subscription_entry_event import SubscriptionEntryEvent
from app.db.models.user import User
from app.repositories.discount_campaign_repo import DiscountCampaignRepository
from app.services.admin_finance_stats_service import AdminFinanceStatsService
from app.services.admin_notify_service import AdminNotifyService
from app.services.admin_miniapp_service import AdminMiniAppService, _no_pending_payment_filter
from app.services.discount_service import DiscountService
from app.services.subscription_entry_analytics_service import SubscriptionEntryAnalyticsService


class NativePaymentDiscountFinanceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            session.add_all([
                User(id=uid, telegram_id=tid, full_name="Learner", language="uz", level="hsk1",
                     status="active" if uid <= 3 else "free",
                     payment_status="approved" if uid <= 3 else "none",
                     end_date=self.now + timedelta(days=10), created_at=self.now, last_active_at=self.now)
                for uid, tid in ((1, None), (2, None), (3, 3003), (4, 1), (5, None))
            ])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    def payment(self, pid, uid, tid, *, amount=10, status="approved", plan="1_month", **extra):
        return Payment(id=pid, user_id=uid, user_telegram_id=tid, plan_type=plan,
                       amount=amount, currency="USD", payment_status=status,
                       submitted_at=self.now - timedelta(minutes=10),
                       reviewed_at=self.now - timedelta(minutes=1), **extra)

    async def test_campaign_history_and_quota_never_merge_null_telegram_accounts(self):
        async with self.sessions() as session:
            campaign = DiscountCampaign(id=1, title="Global offer", percent=25, quota_total=8,
                starts_at=self.now - timedelta(days=1), ends_at=self.now + timedelta(days=1))
            session.add(campaign)
            rows = [
                self.payment(1, 1, None, status="pending", discount_campaign_id=1),
                self.payment(2, 2, None, discount_campaign_id=1),
                self.payment(3, None, 3003, discount_campaign_id=1),
                self.payment(4, 2, 3003, discount_campaign_id=1),
                self.payment(5, None, 99999, discount_campaign_id=1),
                self.payment(6, 2, 99999, discount_campaign_id=1),
                self.payment(7, 2, None, status="draft", discount_campaign_id=1),
                self.payment(8, 2, None, status="draft", discount_campaign_id=1),
                self.payment(9, 1, None, status="rejected", discount_campaign_id=1),
            ]
            rows[7].submitted_at = self.now - timedelta(minutes=31)
            session.add_all(rows)
            await session.flush()
            alice, bob, newcomer = [await session.get(User, uid) for uid in (1, 2, 5)]
            repo = DiscountCampaignRepository(session)
            self.assertEqual(await repo.count_used(1), 7)
            self.assertEqual(await repo.count_used(1, exclude_user=alice), 6)
            self.assertEqual(await repo.count_used(1, exclude_user=bob), 3)
            self.assertEqual(await repo.count_used(1, exclude_user_telegram_id=3003), 6)
            self.assertEqual(await repo.count_used(1, exclude_user_telegram_id=99999), 6)
            self.assertEqual((await repo.get_user_last_usage(1, alice)).id, 1)
            self.assertEqual((await repo.get_user_last_usage(1, 3003)).id, 3)
            self.assertEqual((await repo.get_user_last_usage(1, 99999)).id, 5)
            self.assertIsNone(await repo.get_user_last_usage(1, None))
            self.assertIsNone(await repo.get_user_last_usage(1, 1))  # real TG user #1, not users.id=1
            service = DiscountService(session)
            choice = await service.get_best_admin_discount(user=newcomer, plan_type="1_month", payment_method="visa")
            self.assertEqual((choice.source, choice.percent), ("admin_campaign", 25))
            self.assertEqual((await service.get_best_admin_discount(user=alice, plan_type="1_month", payment_method="visa")).source, "none")
            campaign.quota_total = 7
            self.assertEqual((await service.get_best_admin_discount(user=newcomer, plan_type="1_month", payment_method="visa")).source, "none")

    async def test_provider_accounts_use_canonical_referral_and_skip_telegram_feedback_rows(self):
        async with self.sessions() as session:
            user = await session.get(User, 1)
            user.discount_offer_started_at = self.now
            user.discount_referral_count, user.discount_eligible = 99, True
            service = DiscountService(session)
            service.referral_repo.count_discount_qualified_since = AsyncMock(return_value=0)
            service.feedback_repo.get_available_price_offer = AsyncMock(side_effect=AssertionError("TG feedback lookup"))
            service.feedback_repo.get_latest_available_price_offer = AsyncMock(side_effect=AssertionError("TG feedback lookup"))
            self.assertEqual(await service.sync_referral_discount_progress(user), (0, False))
            self.assertIs(service.referral_repo.count_discount_qualified_since.await_args.kwargs["referrer_telegram_id"], user)
            for feedback_id in (None, 1):
                self.assertEqual((await service.get_feedback_price_discount(user=user, feedback_id=feedback_id)).source, "none")
            targeted = DiscountCampaign(title="TG only", percent=30, target_telegram_id=3003,
                starts_at=self.now - timedelta(days=1), ends_at=self.now + timedelta(days=1))
            self.assertFalse(service._matches_campaign(targeted, user, "1_month", "visa"))

    async def test_finance_merges_legacy_with_canonical_but_keeps_native_and_retained_accounts_distinct(self):
        async with self.sessions() as session:
            session.add_all([
                self.payment(1, 1, None, amount=10), self.payment(2, 1, None, amount=20),
                self.payment(3, 2, None, amount=30), self.payment(4, None, 3003, amount=40),
                self.payment(5, 3, 3003, amount=50), self.payment(6, 2, 3003, amount=5),
                self.payment(7, None, 1, amount=7), self.payment(8, None, -1, amount=8),
                self.payment(9, 9999, None, amount=9),
                self.payment(10, 1, None, amount=100, plan="hsk30_unlock"),
                self.payment(11, 2, None, amount=100, plan="hsk30_unlock"),
                SubscriptionEntryEvent(user_id=1, telegram_id=None, source="android_subscription", created_at=self.now - timedelta(days=1)),
                SubscriptionEntryEvent(user_id=2, telegram_id=None, source="desktop_subscription", created_at=self.now - timedelta(days=1)),
                SubscriptionEntryEvent(user_id=None, telegram_id=3003, source="course_locked_lesson", created_at=self.now - timedelta(days=1)),
            ])
            await session.flush()
            payload = await AdminFinanceStatsService(session).build()
            all_time = next(period for period in payload["periods"] if period["key"] == "all_time")
            self.assertEqual(all_time["finance"]["revenue_usd"], 179)
            self.assertEqual(all_time["unit"]["approved_count"], 9)
            self.assertEqual(all_time["unit"]["paying_users"], 6)
            self.assertEqual(all_time["retention"]["new_paying"], 6)
            self.assertEqual(all_time["retention"]["renewals"], 3)
            self.assertEqual(all_time["retention"]["renewed_ever"], 3)
            self.assertEqual(all_time["retention"]["active_paid_now"], 3)
            self.assertEqual(payload["hsk30_unlock"]["users"], 2)
            source_users = {row["source"]: row["paying_users"] for row in all_time["sources_paid"]}
            self.assertEqual(source_users["android_subscription"], 1)
            self.assertEqual(source_users["desktop_subscription"], 1)

    async def test_admin_receipt_labels_native_account_without_fabricating_telegram_id(self):
        service = AdminNotifyService()
        text = service.build_payment_review_text(lang="uz", telegram_id=None, user_id=42,
            full_name="Alice <native> & Bob", plan_type="1_month", amount=100, currency="TJS", payment_id=9)
        self.assertIn("Account #42", text)
        self.assertIn("Alice &lt;native&gt; &amp; Bob", text)
        self.assertNotIn("(None)", text)
        legacy = service.build_payment_review_text(lang="uz", telegram_id=3003, user_id=3,
            full_name="Legacy", plan_type="1_month", amount=100, currency="TJS", payment_id=9)
        self.assertIn("Legacy (3003)", legacy)

    async def test_admin_queue_counts_and_pending_cohorts_use_canonical_owner(self):
        async with self.sessions() as session:
            alice, bob, legacy = [await session.get(User, uid) for uid in (1, 2, 3)]
            alice.full_name, bob.full_name, legacy.full_name = "Alice", "Bob", "Legacy"
            for user in (alice, bob, legacy):
                user.created_at = self.now - timedelta(days=5)
            session.add_all([
                self.payment(1, 1, None, amount=10), self.payment(2, 2, None, amount=20),
                self.payment(3, None, 3003, amount=30), self.payment(4, 3, 3003, amount=40),
                self.payment(5, None, -1, amount=50),
                self.payment(101, 1, None, status="pending"),
                self.payment(102, 2, None, status="pending"),
                self.payment(103, None, 3003, status="pending"),
                self.payment(104, 1, 3003, status="pending"),
                self.payment(105, None, 99999, status="pending"),
            ])
            await session.flush()
            service = AdminMiniAppService(session)
            self.assertEqual(await service._approved_payment_user_count(), 4)
            self.assertEqual(await service._pending_payment_user_count(), 4)
            queue = {row["id"]: row for row in await service._latest_payments()}
            self.assertEqual((queue[104]["account_id"], queue[104]["telegram_id"], queue[104]["name"]), (1, None, "Alice"))
            self.assertEqual((queue[103]["account_id"], queue[103]["name"]), (3, "Legacy"))
            self.assertEqual(queue[102]["account_id"], 2)
            users = await service._latest_users(self.now, today_start=self.now - timedelta(days=1), hot_since=self.now - timedelta(days=2))
            pending = {row["account_id"]: row["has_pending_payment"] for row in users}
            self.assertEqual(pending, {1: True, 2: True, 3: True, 4: False, 5: False})
            free_of_pending = (await session.execute(select(User.id).where(_no_pending_payment_filter()))).scalars().all()
            self.assertEqual(set(free_of_pending), {4, 5})
            advanced = await service._payment_advanced_stats(since=None)
            self.assertEqual((advanced["paying_users"], advanced["revenue_usd"]), (4, 150))
            self.assertGreater(advanced["first_payment_time_seconds"], 0)

    async def test_entry_analytics_uses_user_metadata_and_dedupes_legacy_accounts(self):
        async with self.sessions() as session:
            alice, bob = await session.get(User, 1), await session.get(User, 2)
            service = SubscriptionEntryAnalyticsService(session)
            self.assertTrue(await service.record_entry(user=alice, telegram_id=3003, source="android_subscription"))
            self.assertTrue(await service.record_entry(user=bob, telegram_id=None, source="android_subscription"))
            session.add_all([
                SubscriptionEntryEvent(user_id=None, telegram_id=3003, source="android_subscription"),
                SubscriptionEntryEvent(user_id=3, telegram_id=3003, source="android_subscription"),
                SubscriptionEntryEvent(user_id=1, telegram_id=3003, source="android_subscription"),
                SubscriptionEntryEvent(user_id=None, telegram_id=1, source="android_subscription"),
            ])
            await session.flush()
            first = (await session.execute(select(SubscriptionEntryEvent).order_by(SubscriptionEntryEvent.id))).scalars().first()
            self.assertEqual((first.user_id, first.telegram_id), (1, None))
            self.assertEqual((await service._counts_by_source())["android_subscription"], (6, 4))
            self.assertFalse(await service.record_entry(telegram_id=None))


if __name__ == "__main__":
    unittest.main()

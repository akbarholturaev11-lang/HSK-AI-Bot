import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.ai_usage import AIUsageEvent
from app.db.models.bot_reachability_event import BotReachabilityEvent
from app.db.models.bot_outbound_event import BotOutboundEvent
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.message import Message
from app.db.models.payment import Payment
from app.db.models.portfolio import PortfolioTransaction
from app.db.models.subscription_entry_event import SubscriptionEntryEvent
from app.db.models.user import User
from app.services.admin_finance_stats_service import AdminFinanceStatsService
from app.services.admin_miniapp_service import (
    HOT_LEAD_ACTIVITY_WINDOW,
    AdminMiniAppService,
    _matured_notification_open_proxy,
    admin_miniapp_today_start,
)
from app.services.admin_stats_service import miniapp_course_stats
from app.services.bot_block_cause_service import BotBlockCauseService
from app.services.entitlements.state import EntitlementState


class _StatsDatabaseTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()


class CourseStatsIntegrityTests(_StatsDatabaseTestCase):
    async def test_section_only_user_is_not_complete_and_aliases_are_deduped(self):
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            session.add_all(
                [
                    CourseMiniAppEvent(
                        id=1,
                        telegram_id=101,
                        event_name="section_completed",
                        level="hsk1",
                        lesson_order=1,
                        created_at=now,
                    ),
                    CourseMiniAppEvent(
                        id=2,
                        telegram_id=202,
                        event_name="book_lesson_completed",
                        level="hsk1",
                        lesson_order=2,
                        created_at=now,
                    ),
                    CourseMiniAppEvent(
                        id=3,
                        telegram_id=202,
                        event_name="lesson_completed",
                        level="hsk1",
                        lesson_order=2,
                        created_at=now,
                    ),
                    # Nullable dedupe_key permits duplicate telemetry rows; the
                    # admin metric must still count one logical user+lesson.
                    CourseMiniAppEvent(
                        id=4,
                        telegram_id=202,
                        event_name="lesson_completed",
                        level="hsk1",
                        lesson_order=2,
                        created_at=now,
                    ),
                    CourseMiniAppEvent(
                        id=5,
                        telegram_id=303,
                        event_name="lesson_completed",
                        level="hsk1",
                        lesson_order=3,
                        created_at=now,
                    ),
                ]
            )
            await session.commit()

            stats = await miniapp_course_stats(session)

        self.assertEqual(stats.completed_users, 2)
        self.assertEqual(stats.completed_book_lessons, 2)
        self.assertEqual(stats.completed_sections, 1)


class PaymentPeriodIntegrityTests(_StatsDatabaseTestCase):
    async def test_status_counts_use_review_time_for_reviewed_payments(self):
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=7)
        async with self.sessions() as session:
            session.add_all(
                [
                    Payment(
                        id=1,
                        user_telegram_id=101,
                        plan_type="1_month",
                        amount=100,
                        currency="TJS",
                        payment_status="approved",
                        submitted_at=now - timedelta(days=10),
                        reviewed_at=now - timedelta(days=1),
                    ),
                    Payment(
                        id=2,
                        user_telegram_id=202,
                        plan_type="1_month",
                        amount=90,
                        currency="TJS",
                        payment_status="rejected",
                        submitted_at=now - timedelta(days=10),
                        reviewed_at=now - timedelta(days=1),
                    ),
                    Payment(
                        id=3,
                        user_telegram_id=303,
                        plan_type="10_days",
                        amount=40,
                        currency="TJS",
                        payment_status="pending",
                        submitted_at=now - timedelta(days=1),
                    ),
                    Payment(
                        id=4,
                        user_telegram_id=404,
                        plan_type="10_days",
                        amount=40,
                        currency="TJS",
                        payment_status="pending",
                        submitted_at=now - timedelta(days=10),
                    ),
                ]
            )
            await session.commit()
            service = AdminMiniAppService(session)

            status = await service._payment_status_counts(since)
            approved_users = await service._approved_payment_user_count(since)

        self.assertEqual(status["approved"]["count"], 1)
        self.assertEqual(status["rejected"]["count"], 1)
        self.assertEqual(status["pending"]["count"], 1)
        self.assertEqual(approved_users, 1)

    async def test_pending_and_hot_lead_flags_match_real_user_semantics(self):
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            session.add_all(
                [
                    User(
                        id=1,
                        telegram_id=101,
                        status="active",
                        payment_status="approved",
                        created_at=now - timedelta(days=30),
                        last_active_at=now - timedelta(hours=1),
                        end_date=now + timedelta(days=5),
                    ),
                    User(
                        id=2,
                        telegram_id=202,
                        status="trial",
                        payment_status="none",
                        created_at=now - timedelta(days=2),
                        last_active_at=now - timedelta(hours=2),
                    ),
                    User(
                        id=3,
                        telegram_id=303,
                        status="free",
                        payment_status="none",
                        created_at=now - timedelta(days=2),
                        last_active_at=now - timedelta(hours=3),
                    ),
                    Payment(
                        id=10,
                        user_telegram_id=202,
                        plan_type="1_month",
                        amount=100,
                        currency="TJS",
                        payment_status="pending",
                        submitted_at=now - timedelta(hours=1),
                    ),
                    Payment(
                        id=11,
                        user_telegram_id=202,
                        plan_type="10_days",
                        amount=40,
                        currency="TJS",
                        payment_status="pending",
                        submitted_at=now - timedelta(minutes=30),
                    ),
                ]
            )
            await session.commit()
            service = AdminMiniAppService(session)

            pending_users = await service._pending_payment_user_count()
            cards = await service._latest_users(
                now,
                today_start=admin_miniapp_today_start(now),
                hot_since=now - HOT_LEAD_ACTIVITY_WINDOW,
            )

        by_id = {card["id"]: card for card in cards}
        self.assertEqual(pending_users, 1)
        self.assertTrue(by_id[202]["has_pending_payment"])
        self.assertFalse(by_id[202]["hot_lead"])
        self.assertTrue(by_id[303]["hot_lead"])
        self.assertFalse(by_id[101]["hot_lead"])


class BotBlockCauseIntegrityTests(_StatsDatabaseTestCase):
    async def test_notification_pressure_is_ranked_from_successful_preblock_sends(self):
        now = datetime.now(timezone.utc)
        blocked_at = now - timedelta(hours=1)
        async with self.sessions() as session:
            user = User(
                id=1,
                telegram_id=101,
                status="free",
                payment_status="none",
                bot_blocked_at=blocked_at,
                bot_block_reason="my_chat_member_blocked",
                created_at=now - timedelta(days=20),
                last_active_at=now - timedelta(hours=2),
            )
            session.add(user)
            session.add(
                BotReachabilityEvent(
                    user_id=1,
                    telegram_id=101,
                    event_type="blocked",
                    source="my_chat_member_blocked",
                    created_at=blocked_at,
                )
            )
            for idx, minutes in enumerate((5, 12, 20, 28), start=1):
                session.add(
                    BotOutboundEvent(
                        id=idx,
                        user_id=1,
                        telegram_id=101,
                        source="motivation_reminder",
                        status="sent",
                        created_at=blocked_at - timedelta(minutes=minutes),
                    )
                )
            await session.commit()
            result = await BotBlockCauseService(session).analyze(user)

        self.assertEqual(result["key"], "notification_pressure")
        self.assertEqual(result["confidence"], "yuqori")
        self.assertEqual(result["data_quality"], "direct")
        self.assertTrue(any("4 ta" in item for item in result["evidence"]))

    async def test_recent_app_error_can_be_primary_probable_cause(self):
        now = datetime.now(timezone.utc)
        blocked_at = now - timedelta(hours=1)
        async with self.sessions() as session:
            user = User(
                id=2,
                telegram_id=202,
                status="free",
                payment_status="none",
                bot_blocked_at=blocked_at,
                bot_block_reason="my_chat_member_blocked",
                created_at=now - timedelta(days=10),
                last_active_at=now - timedelta(hours=1),
            )
            session.add(user)
            session.add(
                BotReachabilityEvent(
                    user_id=2,
                    telegram_id=202,
                    event_type="blocked",
                    source="my_chat_member_blocked",
                    created_at=blocked_at,
                )
            )
            session.add(
                Message(
                    user_id=2,
                    role="assistant",
                    content="APP ERROR KONTEXTI: test",
                    content_type="app_error_context",
                    created_at=blocked_at - timedelta(minutes=7),
                )
            )
            await session.commit()
            result = await BotBlockCauseService(session).analyze(user)

        self.assertEqual(result["key"], "technical_issue")
        self.assertEqual(result["confidence"], "yuqori")
        self.assertTrue(any("7 daqiqa" in item for item in result["evidence"]))

    async def test_android_activity_after_block_is_not_presented_as_product_churn(self):
        now = datetime.now(timezone.utc)
        blocked_at = now - timedelta(days=1)
        async with self.sessions() as session:
            user = User(
                id=3,
                telegram_id=303,
                status="free",
                payment_status="none",
                bot_blocked_at=blocked_at,
                bot_block_reason="my_chat_member_blocked",
                created_at=now - timedelta(days=30),
                last_active_at=now,
            )
            session.add_all(
                [
                    user,
                    BotReachabilityEvent(
                        user_id=3,
                        telegram_id=303,
                        event_type="blocked",
                        source="my_chat_member_blocked",
                        created_at=blocked_at,
                    ),
                    CourseMiniAppEvent(
                        user_id=3,
                        telegram_id=303,
                        event_name="android_app_opened",
                        source="android",
                        created_at=blocked_at + timedelta(minutes=20),
                    ),
                ]
            )
            await session.commit()
            result = await BotBlockCauseService(session).analyze(user)

        self.assertEqual(result["key"], "channel_migration")
        self.assertEqual(result["confidence"], "o'rta")
        self.assertIn("HSK AI", result["note"])
        self.assertIn("non-churn", result["note"])

    async def test_legacy_episode_caps_confidence_even_with_strong_timing_signal(self):
        now = datetime.now(timezone.utc)
        blocked_at = now - timedelta(hours=2)
        async with self.sessions() as session:
            user = User(
                id=4,
                telegram_id=404,
                status="free",
                payment_status="none",
                bot_blocked_at=blocked_at,
                bot_block_reason="motivation_reminder",
                created_at=now - timedelta(days=30),
                last_active_at=now - timedelta(days=3),
            )
            session.add(user)
            for idx, minutes in enumerate((3, 8, 14, 25), start=20):
                session.add(
                    BotOutboundEvent(
                        id=idx,
                        user_id=4,
                        telegram_id=404,
                        source="motivation_reminder",
                        status="sent",
                        created_at=blocked_at - timedelta(minutes=minutes),
                    )
                )
            await session.commit()
            result = await BotBlockCauseService(session).analyze(user)

        self.assertEqual(result["data_quality"], "legacy")
        self.assertLessEqual(result["score"], 45)
        self.assertEqual(result["confidence"], "past")


class BotReachabilityStatsIntegrityTests(_StatsDatabaseTestCase):
    async def test_summary_separates_telegram_unreachable_from_app_activity(self):
        now = datetime.now(timezone.utc)
        blocked_at = now - timedelta(days=2)
        async with self.sessions() as session:
            session.add_all(
                [
                    User(
                        id=1,
                        telegram_id=101,
                        status="free",
                        payment_status="none",
                        bot_blocked_at=blocked_at,
                        bot_block_reason="my_chat_member_blocked",
                        created_at=now - timedelta(days=30),
                        last_active_at=now - timedelta(hours=1),
                    ),
                    User(
                        id=2,
                        telegram_id=202,
                        status="free",
                        payment_status="none",
                        bot_blocked_at=blocked_at,
                        bot_block_reason="feedback_prompt",
                        created_at=now - timedelta(days=30),
                        last_active_at=now - timedelta(days=3),
                    ),
                    BotReachabilityEvent(
                        user_id=1,
                        telegram_id=101,
                        event_type="blocked",
                        source="my_chat_member_blocked",
                        created_at=blocked_at,
                    ),
                    CourseMiniAppEvent(
                        telegram_id=101,
                        user_id=1,
                        event_name="android_app_opened",
                        source="android",
                        created_at=now - timedelta(days=1),
                    ),
                ]
            )
            await session.commit()
            summary = await AdminMiniAppService(session)._bot_reachability_summary(now)

        self.assertEqual(summary["current_unreachable"], 2)
        self.assertEqual(summary["explicit_block_users_7d"], 1)
        self.assertEqual(summary["active_after_block_any"], 1)
        self.assertEqual(summary["active_after_block_android"], 1)
        self.assertEqual(summary["active_after_block_miniapp"], 0)


class EntitlementSegmentIntegrityTests(_StatsDatabaseTestCase):
    async def test_legacy_trial_status_is_free_and_real_pro_trial_is_trial(self):
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            session.add_all(
                [
                    User(
                        id=1,
                        telegram_id=101,
                        status="trial",
                        payment_status="none",
                        created_at=now - timedelta(days=5),
                        last_active_at=now,
                    ),
                    User(
                        id=2,
                        telegram_id=202,
                        status="free",
                        payment_status="none",
                        trial_used=True,
                        pro_trial_started_at=now - timedelta(days=1),
                        pro_trial_ends_at=now + timedelta(days=6),
                        created_at=now - timedelta(days=5),
                        last_active_at=now,
                    ),
                ]
            )
            await session.commit()
            counts = await AdminMiniAppService(session)._entitlement_state_counts(now)

        self.assertEqual(counts.get(EntitlementState.FREE), 1)
        self.assertEqual(counts.get(EntitlementState.TRIAL_ACTIVE), 1)


class FinanceStatsIntegrityTests(_StatsDatabaseTestCase):
    async def test_finance_reconciles_manual_profit_and_uses_prior_source(self):
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            session.add_all(
                [
                    User(
                        id=1,
                        telegram_id=101,
                        status="active",
                        payment_status="approved",
                        created_at=now - timedelta(days=100),
                        last_active_at=now - timedelta(hours=1),
                        end_date=now + timedelta(days=10),
                    ),
                    User(
                        id=2,
                        telegram_id=202,
                        status="free",
                        payment_status="none",
                        created_at=now - timedelta(days=100),
                        last_active_at=now - timedelta(days=60),
                    ),
                    SubscriptionEntryEvent(
                        id=1,
                        telegram_id=101,
                        source="locked_lesson",
                        mode="subscription",
                        created_at=now - timedelta(days=3),
                    ),
                    SubscriptionEntryEvent(
                        id=2,
                        telegram_id=101,
                        source="profile",
                        mode="subscription",
                        created_at=now - timedelta(days=1),
                    ),
                    Payment(
                        id=1,
                        user_telegram_id=101,
                        plan_type="1_month",
                        amount=100,
                        currency="USD",
                        payment_status="approved",
                        submitted_at=now - timedelta(days=2),
                        reviewed_at=now - timedelta(hours=12),
                    ),
                    Payment(
                        id=2,
                        user_telegram_id=202,
                        plan_type="10_days",
                        amount=999,
                        currency="unsupported",
                        payment_status="approved",
                        submitted_at=now - timedelta(days=2),
                        reviewed_at=now - timedelta(hours=12),
                    ),
                    AIUsageEvent(
                        id=1,
                        user_telegram_id=101,
                        source="qa",
                        model="fixture",
                        cost_usd=10.0,
                        created_at=now - timedelta(hours=8),
                    ),
                    PortfolioTransaction(
                        id=1,
                        transaction_type="profit",
                        source="manual_profit",
                        amount_usd=20.0,
                        created_at=now - timedelta(hours=7),
                    ),
                    PortfolioTransaction(
                        id=2,
                        transaction_type="expense",
                        source="manual_expense",
                        amount_usd=5.0,
                        created_at=now - timedelta(hours=6),
                    ),
                ]
            )
            await session.commit()

            payload = await AdminFinanceStatsService(session).build()

        weekly = next(item for item in payload["periods"] if item["key"] == "weekly")
        all_time = next(item for item in payload["periods"] if item["key"] == "all_time")
        locked = next(
            item
            for item in weekly["sources_paid"]
            if item["source"] == "course_locked_lesson"
        )

        self.assertEqual(weekly["finance"]["revenue_usd"], 100.0)
        self.assertEqual(weekly["finance"]["manual_profit_usd"], 20.0)
        self.assertEqual(weekly["finance"]["net_usd"], 105.0)
        self.assertEqual(weekly["finance"]["unpriced_payments"], 1)
        self.assertEqual(weekly["unit"]["arpu_users"], 1)
        self.assertEqual(weekly["unit"]["arpu_usd"], 100.0)
        self.assertEqual(locked["revenue_usd"], 100.0)
        self.assertFalse(any(row["source"] == "profile" for row in weekly["sources_paid"]))
        self.assertEqual(all_time["retention"]["inactive_paid_share_pct"], 50.0)
        self.assertIsNone(all_time["retention"]["churn_rate_pct"])

    async def test_client_business_groups_shared_schema_across_clients(self):
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            users = [
                User(
                    id=idx,
                    telegram_id=telegram_id,
                    status="active",
                    payment_status="approved",
                    created_at=now - timedelta(days=30),
                    last_active_at=now - timedelta(hours=idx),
                    end_date=now + timedelta(days=10),
                )
                for idx, telegram_id in enumerate((101, 202, 303, 404), start=1)
            ]
            session.add_all(
                users
                + [
                    SubscriptionEntryEvent(
                        id=1,
                        telegram_id=101,
                        source="v3_paywall",
                        mode="subscription",
                        created_at=now - timedelta(days=3),
                    ),
                    SubscriptionEntryEvent(
                        id=2,
                        telegram_id=202,
                        source="android_subscription",
                        mode="subscription",
                        created_at=now - timedelta(days=3),
                    ),
                    SubscriptionEntryEvent(
                        id=3,
                        telegram_id=303,
                        source="desktop_subscription",
                        mode="subscription",
                        created_at=now - timedelta(days=3),
                    ),
                    SubscriptionEntryEvent(
                        id=4,
                        telegram_id=404,
                        source="android_subscription",
                        mode="subscription",
                        created_at=now - timedelta(days=2),
                    ),
                    Payment(
                        id=1,
                        user_telegram_id=101,
                        plan_type="1_month",
                        amount=100,
                        currency="USD",
                        payment_status="approved",
                        submitted_at=now - timedelta(days=2),
                        reviewed_at=now - timedelta(days=1),
                    ),
                    Payment(
                        id=2,
                        user_telegram_id=202,
                        plan_type="1_month",
                        amount=50,
                        currency="USD",
                        payment_status="approved",
                        submitted_at=now - timedelta(days=2),
                        reviewed_at=now - timedelta(days=1),
                    ),
                    Payment(
                        id=3,
                        user_telegram_id=303,
                        plan_type="1_month",
                        amount=70,
                        currency="USD",
                        payment_status="approved",
                        submitted_at=now - timedelta(days=2),
                        reviewed_at=now - timedelta(days=1),
                    ),
                ]
            )
            await session.commit()

            payload = await AdminFinanceStatsService(session).build()

        weekly = next(item for item in payload["periods"] if item["key"] == "weekly")
        by_client = {
            row["key"]: row
            for row in weekly["client_business"]["rows"]
        }

        self.assertEqual(by_client["miniapp"]["payments"], 1)
        self.assertEqual(by_client["miniapp"]["revenue_usd"], 100.0)
        self.assertEqual(by_client["android"]["entry_users"], 2)
        self.assertEqual(by_client["android"]["payments"], 1)
        self.assertEqual(by_client["android"]["revenue_usd"], 50.0)
        self.assertEqual(by_client["desktop"]["payments"], 1)
        self.assertEqual(by_client["desktop"]["revenue_usd"], 70.0)
        # Tug'ilganidan beri yiqilardi (`7c3e03df`): bosh harfli
        # "approved Payment" kartada emas, `explain` matnida. Ikkalasi ham
        # tekshiriladi — karta pul qayerdan sanalganini aytadi, `explain`
        # esa uchala klient bitta jadvaldan o'qishini aytadi, ya'ni shu
        # testning asl da'vosini.
        self.assertIn(
            "approved payment",
            weekly["client_business"]["cards"][0]["note"],
        )
        self.assertIn(
            "approved Payment",
            weekly["client_business"]["explain"],
        )


class NotificationStatsIntegrityTests(unittest.TestCase):
    def test_recent_sends_wait_for_maturity_and_one_open_is_not_reused(self):
        now = datetime(2026, 8, 22, 12, tzinfo=timezone.utc)
        result = _matured_notification_open_proxy(
            [
                (101, now - timedelta(hours=72)),
                (202, now - timedelta(hours=1)),
            ],
            [(101, now - timedelta(hours=71))],
            now=now,
        )

        self.assertEqual(result["sent"], 1)
        self.assertEqual(result["immature_sent"], 1)
        self.assertEqual(result["opened_after"], 1)
        self.assertEqual(result["open_rate"], 100.0)

        overlapping = _matured_notification_open_proxy(
            [
                (303, now - timedelta(hours=72)),
                (303, now - timedelta(hours=60)),
            ],
            [(303, now - timedelta(hours=59))],
            now=now,
        )
        self.assertEqual(overlapping["sent"], 2)
        self.assertEqual(overlapping["opened_after"], 1)

        newer_immature = _matured_notification_open_proxy(
            [
                (404, now - timedelta(hours=60)),
                (404, now - timedelta(hours=30)),
            ],
            [(404, now - timedelta(hours=29))],
            now=now,
        )
        self.assertEqual(newer_immature["sent"], 1)
        self.assertEqual(newer_immature["immature_sent"], 1)
        self.assertEqual(newer_immature["opened_after"], 0)


if __name__ == "__main__":
    unittest.main()

"""Admin metrics count canonical learners across optional Telegram identities."""

import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.ai_usage import AIUsageEvent
from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_pilot_event import CoursePilotEvent
from app.db.models.desktop import DesktopDevice
from app.db.models.payment import Payment
from app.db.models.release_feedback import ReleaseFeedbackCampaign, ReleaseFeedbackResponse
from app.db.models.user import User
from app.db.models.voice_practice_session import VoicePracticeSession
from app.repositories.release_feedback_repo import ReleaseFeedbackRepository
from app.repositories.course_pilot_event_repo import CoursePilotEventRepository
from app.services.admin_analytics_identity import analytics_account_key
from app.services.admin_broadcast_service import AdminBroadcastService
from app.services.admin_miniapp_service import AdminMiniAppService
from app.services.admin_stats_service import feature_usage_stats, miniapp_course_stats
from app.services.android_analytics_service import AndroidAnalyticsService
from app.services.course_miniapp_admin_analytics_service import CourseMiniAppAdminAnalyticsService
from app.services.desktop_analytics_service import DesktopAnalyticsService


class NativeAccountStatisticsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.admin = None
        if os.environ.get("NATIVE_ACCOUNT_TEST_DATABASE_URL"):
            # Match existing native integration tests: every test owns a fresh
            # schema in the explicitly supplied isolated test database.
            test_url = os.environ["NATIVE_ACCOUNT_TEST_DATABASE_URL"]
            self.schema = "native_statistics_" + uuid4().hex
            self.admin = create_async_engine(test_url)
            async with self.admin.begin() as connection:
                await connection.execute(text(f"CREATE SCHEMA {self.schema}"))
            self.engine = create_async_engine(test_url,
                connect_args={"server_settings": {"search_path": self.schema + ",public"}})
        else:
            self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            session.add_all([
                User(id=uid, telegram_id=tid, full_name=name, language="uz",
                     status="free", payment_status="none", created_at=self.now - timedelta(days=20),
                     last_active_at=self.now)
                for uid, tid, name in ((1, None, "Google"), (2, 1, "Telegram"), (3, None, "Apple"))
            ])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()
        if self.admin is not None:
            async with self.admin.begin() as connection:
                await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
            await self.admin.dispose()

    def event(self, name, uid, tid=None, *, minutes=1, payload=None, **kwargs):
        return CourseMiniAppEvent(event_name=name, user_id=uid, telegram_id=tid,
            created_at=self.now - timedelta(minutes=minutes),
            payload_json=json.dumps(payload or {}), **kwargs)

    async def test_account_keys_resolve_attachment_without_id_collisions_or_orphan_merging(self):
        async with self.sessions() as session:
            rows = [(1, None), (None, 1), (2, 1), (1, 1), (3, None), (None, 3), (None, -1), (None, None)]
            session.add_all([self.event("lesson_started", uid, tid) for uid, tid in rows])
            await session.flush()
            keys = (await session.execute(select(analytics_account_key(CourseMiniAppEvent)).order_by(CourseMiniAppEvent.id))).scalars().all()
            self.assertEqual(keys, ["user:1", "user:2", "user:2", "user:1", "user:3", "telegram:3", "telegram:-1", None])
            (await session.get(User, 1)).telegram_id = 777
            session.add(self.event("lesson_started", None, 777))
            await session.flush()
            stats = await miniapp_course_stats(session)
            self.assertEqual(stats.lesson_users, 5)  # 3 current, orphan TG and retained TG.

    async def test_feature_counts_and_paid_free_segments_keep_native_owners_authoritative(self):
        async with self.sessions() as session:
            paid = await session.get(User, 1)
            paid.status, paid.payment_status, paid.end_date = "active", "approved", self.now + timedelta(days=5)
            for index, (uid, tid) in enumerate(((1, None), (2, 1), (3, None), (None, 1), (1, 1))):
                session.add(self.event("lesson_started", uid, tid))
                session.add(AIUsageEvent(user_id=uid, user_telegram_id=tid, source="qa", model="fixture", created_at=self.now))
                session.add(VoicePracticeSession(id=str(index), user_id=uid, user_telegram_id=tid,
                    role="friend", level="hsk1", language="uz", voice="alloy", started_at=self.now))
            await session.flush()
            features = await feature_usage_stats(session, self.now - timedelta(days=1), self.now - timedelta(days=7))
            for label in ("📖 Darslar", "🎤 Voice roleplay", "🤖 AI chat aktiv user"):
                row = next(row for row in features if row.label == label)
                self.assertEqual((row.today_users, row.week_users), (3, 3), label)
            service = AdminMiniAppService(session)
            self.assertEqual(await service._qa_user_count(), 3)
            adoption = await service._feature_adoption(since=None, now=self.now)
            for label in ("Darslar", "AI chat aktiv user", "Voice roleplay"):
                row = next(row for row in adoption["rows"] if row["label"] == label)
                self.assertEqual((row["paid"], row["free"]), (1, 2), label)

    async def test_logical_lesson_completions_do_not_merge_null_telegram_accounts(self):
        async with self.sessions() as session:
            for uid, tid in ((1, None), (2, 1), (3, None), (None, 1)):
                for name in ("book_lesson_completed", "lesson_completed"):
                    session.add(self.event(name, uid, tid, level="hsk1", lesson_order=1))
            session.add(self.event("lesson_completed", None, None, level="hsk1", lesson_order=1))
            await session.flush()
            stats = await miniapp_course_stats(session)
        self.assertEqual((stats.completed_users, stats.completed_book_lessons), (3, 3))

    async def test_android_active_users_and_funnel_include_provider_only_accounts(self):
        async with self.sessions() as session:
            for uid, tid in ((1, None), (2, 1), (3, None)):
                device_id = f"android-{uid}"
                session.add(DesktopDevice(id=device_id, user_id=uid, platform="android",
                    installation_key_hash=f"installation-{uid}", app_version="1.0.0", first_open_at=self.now,
                    last_seen_at=self.now, created_at=self.now - timedelta(days=2)))
                session.add(self.event("android_session_linked", uid, tid))
                session.add(self.event("android_app_opened", uid, tid, payload={"device_id": device_id}))
            session.add(self.event("android_session_linked", None, 1))
            session.add(self.event("android_app_opened", None, 1, payload={"device_id": "android-2"}))
            await session.flush()
            result = await AndroidAnalyticsService(session).snapshot(now=self.now)
        self.assertEqual(result["registry"]["installed_users"], 3)
        self.assertEqual((result["active"]["dau"], result["active"]["dau_devices"]), (3, 3))
        self.assertEqual(result["funnel"]["session_linked"], {"users": 3, "events": 4})

    async def test_desktop_mac_windows_activity_and_ordered_funnel_share_canonical_accounts(self):
        async with self.sessions() as session:
            for uid, tid in ((1, None), (2, 1), (3, None)):
                platform = "macos" if uid == 1 else "windows"
                for offset, name in enumerate(("desktop_download_requested", "desktop_download_started", "desktop_download_link_clicked", "desktop_session_linked", "desktop_first_open")):
                    session.add(self.event(name, uid, tid, minutes=10-offset, session_id=f"device-{uid}",
                        payload={"platform": platform, "app_version": "1.0.0", "device_id": f"device-{uid}"}))
            session.add(self.event("desktop_first_open", None, 1, minutes=1,
                payload={"platform": "windows", "app_version": "1.0.0", "device_id": "device-2"}))
            await session.flush()
            result = await DesktopAnalyticsService(session).snapshot(now=self.now)
        self.assertEqual(result["active"], {"dau": 3, "wau": 3, "mau": 3, "proof_events": ["desktop_first_open", "desktop_app_opened", "desktop_active_day"]})
        self.assertEqual(result["funnel"]["verified_first_open"]["users"], 3)
        self.assertEqual(result["funnel"]["verified_first_open"]["events"], 4)
        self.assertEqual(result["versions"]["known_devices_30d"], 3)
        self.assertEqual(result["platforms"]["active_users_30d"], {"macos": 1, "windows": 2, "unknown_events": 0})

    async def test_starter_and_course_user_metrics_dedupe_legacy_aliases(self):
        async with self.sessions() as session:
            for uid, tid in ((1, None), (2, 1), (3, None), (None, 1)):
                session.add(self.event("foundation_started", uid, tid, minutes=10, payload={"foundation_version": "1"}))
                session.add(self.event("foundation_completed", uid, tid, minutes=9, payload={"foundation_version": "1"}))
                session.add(self.event("section_started", uid, tid, level="hsk1", lesson_order=1))
            await session.flush()
            service = CourseMiniAppAdminAnalyticsService(session)
            unique = await service._counts_by_event(unique=True)
            foundation = await service.foundation_metrics(since=None, now=self.now)
            dropoff = await service._lesson_dropoff(since=self.now - timedelta(days=1))
        self.assertEqual(unique["section_started"], 3)
        self.assertEqual((foundation["started_users"], foundation["completed_users"]), (3, 3))
        self.assertEqual(dropoff[0].started, 3)

    async def test_activation_lesson_session_and_payment_attempts_do_not_collapse_native_users(self):
        async with self.sessions() as session:
            session.add_all([
                Payment(id=uid, user_id=uid, user_telegram_id=tid, plan_type="1_month", amount=10,
                    currency="USD", payment_status="approved")
                for uid, tid in ((1, None), (2, 1), (3, None))
            ])
            await session.flush()
            for uid, tid in ((1, None), (2, 1), (3, None)):
                session.add(self.event("onboarding_completed", uid, tid, minutes=40))
                session.add(self.event("lesson_started", uid, tid, minutes=39, session_id="same-session", level="hsk1", lesson_order=1))
                session.add(self.event("book_lesson_completed", uid, tid, minutes=35, session_id="same-session", level="hsk1", lesson_order=1))
                for offset, name in enumerate(("checkout_opened", "payment_screenshot_submitted", "payment_approved")):
                    session.add(ConversionFunnelEvent(user_id=uid, telegram_id=tid, event_name=name,
                        payment_id=uid if offset else None, payload_json=json.dumps({"attempt_id": "same-attempt"}),
                        created_at=self.now - timedelta(minutes=10-offset)))
            await session.flush()
            service = AdminMiniAppService(session)
            activation = await service._activation_stats(since=None, now=self.now)
            lesson = await service._lesson_time(since=None)
            sessions = await service._miniapp_session_time(since=None)
            funnel = await service._payment_funnel(since=None)
        self.assertEqual((activation["onboarded"], activation["lesson_started_2m"]), (3, 3))
        self.assertEqual(lesson["completed_lessons"], 3)
        self.assertEqual(sessions["sessions"], 3)
        self.assertEqual(funnel["attempts"], 3)
        self.assertEqual([step["users"] for step in funnel["steps"]], [3, 3, 3, 3, 3])

    async def test_sales_ab_keeps_native_assignment_payment_and_error_owner(self):
        async with self.sessions() as session:
            for uid, tid in ((1, None), (2, 1), (3, None)):
                session.add(self.event("sales_offer_assigned", uid, tid, minutes=10*24*60,
                    source="sales_value_v1", payload={"arm": "treatment", "assigned_mode": "ab"}))
                session.add(Payment(user_id=uid, user_telegram_id=tid, plan_type="1_month", amount=10,
                    currency="USD", payment_status="approved", submitted_at=self.now-timedelta(days=9), reviewed_at=self.now-timedelta(days=8)))
            # Same Telegram owner and same experiment cannot form a fourth assignment.
            session.add(self.event("sales_offer_assigned", None, 1, minutes=9*24*60,
                source="sales_value_v1", payload={"arm": "control", "assigned_mode": "ab"}))
            await session.flush()
            result = await AdminMiniAppService(session)._sales_value_stats(now=self.now)
        self.assertEqual((result["assigned"], result["matured"]), (3, 3))
        self.assertEqual(result["arms"]["treatment"]["approved_users"], 3)
        self.assertEqual(result["arms"]["treatment"]["revenue_by_currency"], {"USD": 30})

    async def test_retention_keeps_exact_miniapp_day_window_for_all_canonical_users(self):
        async with self.sessions() as session:
            created = self.now - timedelta(days=20)
            session.add_all([
                CourseMiniAppEvent(user_id=1, telegram_id=None, event_name="miniapp_opened", created_at=created+timedelta(hours=25)),
                CourseMiniAppEvent(user_id=None, telegram_id=1, event_name="miniapp_opened", created_at=created+timedelta(hours=26)),
                CourseMiniAppEvent(user_id=2, telegram_id=1, event_name="miniapp_opened", created_at=created+timedelta(hours=27)),
                # Preserve the existing Mini App metric; native app opens and
                # an out-of-window Mini App return do not change its numerator.
                CourseMiniAppEvent(user_id=3, telegram_id=None, event_name="android_app_opened", created_at=created+timedelta(hours=25)),
                CourseMiniAppEvent(user_id=3, telegram_id=None, event_name="miniapp_opened", created_at=created+timedelta(hours=49)),
            ])
            await session.flush()
            result = await AdminMiniAppService(session)._retention_stats(since=None, now=self.now)
        self.assertEqual((result["d1"]["eligible"], result["d1"]["retained"]), (3, 2))
        self.assertEqual((result["d7"]["eligible"], result["d7"]["retained"]), (3, 0))

    async def test_telegram_block_analysis_keeps_prior_native_activity_after_attachment(self):
        async with self.sessions() as session:
            attached = await session.get(User, 1)
            attached.telegram_id = 777
            attached.bot_blocked_at = self.now - timedelta(hours=2)
            attached.bot_block_reason = "my_chat_member_blocked"
            session.add(self.event("android_app_opened", 1, None))
            # Conflicting transport metadata cannot move another owner's open.
            session.add(self.event("desktop_app_opened", 3, 777))
            await session.flush()
            result = await AdminMiniAppService(session)._bot_reachability_summary(self.now)
        self.assertEqual(result["current_unreachable"], 1)
        self.assertEqual(result["active_after_block_any"], 1)
        self.assertEqual(result["active_after_block_android"], 1)
        self.assertEqual(result["active_after_block_desktop"], 0)

    async def test_feedback_discount_stat_counts_accounts_not_nullable_transport_ids(self):
        async with self.sessions() as session:
            session.add(ReleaseFeedbackCampaign(id=1, title="fixture", send_at=self.now))
            session.add(ReleaseFeedbackResponse(campaign_id=1, user_telegram_id=1, rating=5, discount_campaign_id=7))
            for uid, tid, status in ((1, None, "approved"), (2, 1, "approved"), (None, 1, "pending"), (3, None, "approved"), (None, -1, "approved"), (3, None, "rejected")):
                session.add(Payment(user_id=uid, user_telegram_id=tid, plan_type="1_month", amount=10,
                    currency="USD", payment_status=status, discount_campaign_id=7))
            await session.flush()
            stats = await ReleaseFeedbackRepository(session).stats(1)
        self.assertEqual(stats.discount_used, 4)  # Three accounts plus one retained history.

    async def test_pilot_course_counts_canonical_native_and_legacy_learners_once(self):
        async with self.sessions() as session:
            for uid, tid in ((1, None), (2, 1), (3, None), (None, 1)):
                for event_type in ("opened", "completed"):
                    session.add(CoursePilotEvent(user_id=uid, telegram_id=tid,
                        level="hsk1", lesson_order=1, event_type=event_type, step_name="lesson"))
            await session.flush()
            repo = CoursePilotEventRepository(session)
            self.assertEqual(await repo.distinct_user_count(), 3)
            self.assertEqual(await repo.distinct_user_count("completed"), 3)
            self.assertEqual(await repo.lesson_breakdown(), [("hsk1", 1, 3, 3)])

    async def test_broadcast_preview_and_delivery_require_real_telegram_transport(self):
        async with self.sessions() as session:
            users = (await session.execute(select(User).order_by(User.id))).scalars().all()
            self.assertEqual(AdminBroadcastService.deliverable_count(users, set()), 1)
            bot = AsyncMock()
            service = AdminBroadcastService(bot, session)
            with patch.object(service, "_encode_text", new=AsyncMock(return_value="hello")), \
                    patch("app.services.admin_broadcast_service.build_promo_button_markup", new=AsyncMock(return_value=None)), \
                    patch("app.services.admin_broadcast_service.BotBlockStatusService.handle_send_success", new=AsyncMock()):
                result = await service.deliver(users, admin_ids=set(), text="hello", content_type="text",
                    media_file_id=None, button_config=None, translate=False)
            self.assertEqual(result, (1, 0, 0))
            bot.send_message.assert_awaited_once()
            self.assertEqual(bot.send_message.await_args.args[0], 1)

    async def test_bot_broadcast_targets_and_broadcast_all_skip_provider_only_users(self):
        from app.bot.handlers import admin, admin_broadcast

        async with self.sessions() as session:
            targeted = await admin_broadcast._get_target_users(session, {})
            self.assertEqual([user.id for user in targeted], [2])
            message = SimpleNamespace(text="/broadcast_all hello", from_user=SimpleNamespace(id=999),
                bot=AsyncMock(), answer=AsyncMock())
            with patch.object(admin, "_is_admin", return_value=True):
                await admin.admin_broadcast_handler(message, session)
            message.bot.send_message.assert_awaited_once_with(chat_id=1, text="hello")
            self.assertIn("Yuborildi: 1", message.answer.await_args.args[0])

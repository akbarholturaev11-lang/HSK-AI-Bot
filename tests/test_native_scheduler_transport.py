"""Provider-only learners cannot interrupt Telegram-only scheduled delivery."""

from datetime import datetime, time, timedelta, timezone
import unittest
from unittest.mock import AsyncMock, patch

from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.bot_outbound_event import BotOutboundEvent
from app.db.models.bot_reachability_event import BotReachabilityEvent
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.user import User
from app.services.access_service import AccessService
from app.services.bot_block_status_service import BotBlockStatusService
from app.services.course_reminder_service import CourseReminderService
from app.services.motivation_reminder_service import MotivationReminderService


class NativeSchedulerTransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.now = datetime(2026, 10, 19, 9, 0, tzinfo=timezone.utc)  # Monday
        async with self.sessions() as session:
            session.add_all([User(id=uid, telegram_id=tid, status="active", language="uz",
                                  last_active_at=self.now, end_date=self.now + timedelta(days=1))
                             for uid, tid in ((1, None), (2, None), (3, 3003))])
            await session.flush()
            for uid in (1, 2, 3):
                session.add(CourseProgress(user_id=uid, level="hsk1", reminder_enabled=True,
                    reminder_time=time(9), reminder_tz_offset=0, completed_lessons_count=1))
                session.add(CourseMiniAppProfile(user_id=uid, timezone_offset_minutes=0))
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_native_users_do_not_abort_due_telegram_lesson_reminders(self):
        async with self.sessions() as session:
            bot = AsyncMock()
            with patch("app.services.course_reminder_service.datetime", wraps=datetime) as clock:
                clock.now.return_value = self.now
                with patch.object(CourseReminderService, "_build_reminder_text", new=AsyncMock(
                        return_value=("Continue lesson", {"vocab": 2, "dialogues": 1}))):
                    await CourseReminderService(session).send_due_reminders(bot)
            self.assertEqual([call.kwargs["chat_id"] for call in bot.send_message.await_args_list], [3003])
            rows = list((await session.scalars(select(CourseProgress).order_by(CourseProgress.user_id))).all())
            self.assertTrue(all(row.last_reminder_sent_at is None for row in rows[:2]))
            self.assertIsNotNone(rows[2].last_reminder_sent_at)

    async def test_weekly_reports_never_send_to_missing_telegram_transport(self):
        async with self.sessions() as session:
            bot = AsyncMock()
            with patch("app.services.course_reminder_service.datetime", wraps=datetime) as clock:
                clock.now.return_value = self.now
                with patch("app.services.course_reminder_service.CourseProgressSummaryService") as summary:
                    summary.return_value.summarize_completed_range = AsyncMock(
                        return_value={"lessons": 1, "vocab": 2, "dialogues": 1})
                    await CourseReminderService(session).send_weekly_progress_reports(bot)
            self.assertEqual([call.kwargs["chat_id"] for call in bot.send_message.await_args_list], [3003])
            rows = list((await session.scalars(select(CourseProgress).order_by(CourseProgress.user_id))).all())
            self.assertTrue(all(row.last_weekly_progress_sent_at is None for row in rows[:2]))

    async def test_motivation_loop_only_resolves_real_telegram_cohort(self):
        async with self.sessions() as session:
            service = MotivationReminderService(session)
            service._load_d1_recovery_states = AsyncMock(return_value={})
            service._handle_d1_recovery = AsyncMock(return_value="d1_control_holdout")
            with patch("app.services.motivation_reminder_service.datetime", wraps=datetime) as clock:
                clock.now.return_value = self.now
                await service.send_due_reminders(AsyncMock())
            self.assertEqual(service._load_d1_recovery_states.await_args.args[0], [3003])
            self.assertEqual(service._handle_d1_recovery.await_count, 1)
            self.assertEqual(service._handle_d1_recovery.await_args.kwargs["user"].id, 3)

    async def test_no_identity_never_queries_all_null_telegram_users_for_unblock_or_failure(self):
        async with self.sessions() as session:
            service = BotBlockStatusService(session)
            self.assertFalse(await service.mark_telegram_id_unblocked(None))
            self.assertFalse(await service.handle_send_exception(
                None, TelegramForbiddenError(method=None, message="blocked")))
            self.assertEqual(list((await session.scalars(select(BotOutboundEvent))).all()), [])
            self.assertEqual(list((await session.scalars(select(BotReachabilityEvent))).all()), [])

    async def test_native_profiles_still_participate_in_reminder_league_ranking(self):
        async with self.sessions() as session:
            profile = await session.scalar(select(CourseMiniAppProfile).where(CourseMiniAppProfile.user_id == 1))
            profile.xp_total = 100
            service = MotivationReminderService(session)
            service._load_d1_recovery_states = AsyncMock(return_value={})
            service._handle_d1_recovery = AsyncMock(return_value=None)
            service._maybe_overtaken = AsyncMock(return_value=True)
            with patch("app.services.motivation_reminder_service.datetime", wraps=datetime) as clock:
                clock.now.return_value = self.now
                await service.send_due_reminders(AsyncMock())
            self.assertEqual(service._maybe_overtaken.await_count, 1)
            self.assertEqual(service._maybe_overtaken.await_args.args[2].id, 3)
            self.assertEqual(service._maybe_overtaken.await_args.args[4], 3)
            self.assertEqual(len(service._maybe_overtaken.await_args.args[5]), 3)

    async def test_native_user_has_no_bot_reachability_episode_or_outbound_delivery(self):
        async with self.sessions() as session:
            user = await session.get(User, 1)
            service = BotBlockStatusService(session)
            await service.mark_user_blocked(user)
            await service.handle_send_success(user)
            await service.mark_user_unblocked(user)
            self.assertIsNone(user.bot_blocked_at)
            self.assertIsNone(user.bot_unblocked_at)
            self.assertIsNone(user.last_bot_block_check_at)
            self.assertEqual(list((await session.scalars(select(BotOutboundEvent))).all()), [])
            self.assertEqual(list((await session.scalars(select(BotReachabilityEvent))).all()), [])

    async def test_diagnostic_get_chat_scan_skips_unlinked_native_users(self):
        async with self.sessions() as session:
            bot = AsyncMock()
            with patch("app.services.bot_block_status_service.settings") as settings:
                settings.admin_id_list = []
                checked = await BotBlockStatusService(session).scan_due_users(bot, pause_seconds=0)
            self.assertEqual(checked, 1)
            self.assertEqual([call.args[0] for call in bot.get_chat.await_args_list], [3003])

    async def test_telegram_only_release_trial_lookup_is_guarded_for_native_account(self):
        user = User(id=1, telegram_id=None, status="active", end_date=self.now)
        session = AsyncMock()
        self.assertFalse(await AccessService(session)._has_active_release_feedback_trial(user))
        session.execute.assert_not_awaited()

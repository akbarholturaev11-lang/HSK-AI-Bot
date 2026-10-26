"""P0 regression evidence for the *legacy* Smart Reminder inputs.

These tests pin existing behavior without enabling the new Smart Reminder engine:
legacy Telegram daily/weekly senders accept active accounts only, while canceling
the inline reminder setup does not disable a saved study reminder. A future
migration must intentionally review these distinctions instead of guessing.
"""

from datetime import datetime, time, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.course_progress import CourseProgress
from app.db.models.user import User
from app.bot.handlers.course import (
    course_cancel_reminder_setup_handler,
    course_set_reminder_time_handler,
)
from app.repositories.course_progress_repo import CourseProgressRepository
from app.services.course_reminder_service import CourseReminderService
from app.services.user_access_state_service import UserAccessStateService


class SmartReminderP0LegacyRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.now = datetime(2026, 10, 19, 9, 0, tzinfo=timezone.utc)  # Monday
        # Two active accounts: paid and time-limited nonpaid. Three allowed
        # non-active lifecycle states, one blocked, one native-only account.
        status_rows = [
            (1, 3001, "active", "approved"),
            (2, 3002, "active", "none"),
            (3, 3003, "trial", "none"),
            (4, 3004, "free", "none"),
            (5, 3005, "expired", "none"),
            (6, 3006, "blocked", "none"),
            (7, None, "active", "none"),
        ]
        async with self.sessions() as session:
            for uid, telegram_id, status, payment_status in status_rows:
                session.add(
                    User(
                        id=uid,
                        telegram_id=telegram_id,
                        status=status,
                        payment_status=payment_status,
                        language="uz",
                        last_active_at=self.now,
                        end_date=self.now + timedelta(days=1)
                        if status == "active" else None,
                    )
                )
                session.add(
                    CourseProgress(
                        user_id=uid,
                        level="hsk1",
                        reminder_enabled=True,
                        reminder_time=time(9),
                        reminder_tz_offset=0,
                        completed_lessons_count=1,
                        waiting_for="none",
                    )
                )
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    def test_course_access_statuses_are_distinct_from_legacy_sender_status(self):
        for status in ("trial", "free", "expired"):
            with self.subTest(status=status):
                user = SimpleNamespace(
                    status=status, payment_status="none", end_date=None,
                    payment_preview_payment_id=None,
                )
                self.assertTrue(UserAccessStateService.can_use_course(user))
        blocked = SimpleNamespace(
            status="blocked", payment_status="none", end_date=None,
            payment_preview_payment_id=None,
        )
        self.assertFalse(UserAccessStateService.can_use_course(blocked))

    async def test_legacy_daily_sender_filters_to_active_telegram_accounts(self):
        async with self.sessions() as session:
            bot = AsyncMock()
            with patch(
                "app.services.course_reminder_service.datetime", wraps=datetime
            ) as clock, patch.object(
                CourseReminderService,
                "_build_reminder_text",
                new=AsyncMock(return_value=("Continue lesson", {"vocab": 2, "dialogues": 1})),
            ):
                clock.now.return_value = self.now
                await CourseReminderService(session).send_due_reminders(bot)

        # This is a snapshot of OLD behavior, NOT the desired Smart policy:
        # eligible trial/free/expired learners currently receive no study send.
        destinations = [
            call.kwargs["chat_id"] for call in bot.send_message.await_args_list
        ]
        self.assertEqual(destinations, [3001, 3002])

    async def test_legacy_weekly_sender_also_filters_nonactive_statuses(self):
        async with self.sessions() as session:
            bot = AsyncMock()
            with patch(
                "app.services.course_reminder_service.datetime", wraps=datetime
            ) as clock, patch(
                "app.services.course_reminder_service.CourseProgressSummaryService"
            ) as summary:
                clock.now.return_value = self.now
                summary.return_value.summarize_completed_range = AsyncMock(
                    return_value={"lessons": 1, "vocab": 2, "dialogues": 1}
                )
                await CourseReminderService(session).send_weekly_progress_reports(bot)
        destinations = [
            call.kwargs["chat_id"] for call in bot.send_message.await_args_list
        ]
        self.assertEqual(destinations, [3001, 3002])

    async def test_inline_cancel_clears_setup_but_preserves_stored_study_on(self):
        async with self.sessions() as session:
            progress = await session.scalar(
                select(CourseProgress).where(CourseProgress.user_id == 1)
            )
            progress.waiting_for = "reminder_setup"
            progress.reminder_time = time(14)
            await session.commit()

            callback = SimpleNamespace(
                from_user=SimpleNamespace(id=3001), answer=AsyncMock()
            )
            with patch("app.bot.handlers.course.CourseEngineService") as engine, patch(
                "app.bot.handlers.course.edit_callback_workflow_message",
                new_callable=AsyncMock,
            ) as render:
                engine.return_value.progress_repo = CourseProgressRepository(session)
                await course_cancel_reminder_setup_handler(callback, None, session)
                render.assert_awaited_once()
            callback.answer.assert_awaited_once()

        async with self.sessions() as session:
            persisted = await session.scalar(
                select(CourseProgress).where(CourseProgress.user_id == 1)
            )
            self.assertEqual(persisted.waiting_for, "none")
            self.assertTrue(persisted.reminder_enabled)
            self.assertEqual(persisted.reminder_time, time(14))

    async def test_inline_time_select_explicitly_saves_telegram_study_on(self):
        async with self.sessions() as session:
            progress = await session.scalar(
                select(CourseProgress).where(CourseProgress.user_id == 1)
            )
            progress.waiting_for = "reminder_setup"
            progress.reminder_enabled = False
            progress.reminder_time = None
            await session.commit()

            callback = SimpleNamespace(
                from_user=SimpleNamespace(id=3001),
                data="course:reminder_time:08:00",
                answer=AsyncMock(),
            )
            with patch("app.bot.handlers.course.CourseEngineService") as engine, patch(
                "app.bot.handlers.course.edit_callback_workflow_message",
                new_callable=AsyncMock,
            ) as render:
                engine.return_value.progress_repo = CourseProgressRepository(session)
                await course_set_reminder_time_handler(callback, None, session)
                render.assert_awaited_once()
            callback.answer.assert_awaited_once()

        async with self.sessions() as session:
            persisted = await session.scalar(
                select(CourseProgress).where(CourseProgress.user_id == 1)
            )
            self.assertTrue(persisted.reminder_enabled)
            self.assertEqual(persisted.reminder_time, time(8))
            self.assertEqual(persisted.waiting_for, "none")


if __name__ == "__main__":
    unittest.main()

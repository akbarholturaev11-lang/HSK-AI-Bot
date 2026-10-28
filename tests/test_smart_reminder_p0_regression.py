"""P0 regression evidence for the *legacy* Smart Reminder inputs.

These tests pin existing behavior without enabling the new Smart Reminder engine:
legacy Telegram daily/weekly senders accept active accounts only, while canceling
the inline reminder setup does not disable a saved study reminder. A future
migration must intentionally review these distinctions instead of guessing.
"""

from datetime import date, datetime, time, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.account_deletion import AccountDeletionRequest
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.user import User
from app.bot.handlers.messages import handle_text_message
from app.bot.handlers.course import (
    course_cancel_reminder_setup_handler,
    course_set_reminder_time_handler,
)
from app.repositories.course_progress_repo import CourseProgressRepository
from app.services.course_reminder_service import CourseReminderService
from app.services.course_gamification_service import CourseGamificationService
from app.services.course_miniapp_practice_service import CourseMiniAppPracticeService
from app.services.learning_signals import LearningSignalsService
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


    async def test_message_level_cancel_preserves_legacy_reminder_on(self):
        """The early text-message branch is a setup exit, not an OFF action."""
        async with self.sessions() as session:
            progress = await session.scalar(
                select(CourseProgress).where(CourseProgress.user_id == 1)
            )
            progress.waiting_for = "reminder_setup"
            progress.reminder_time = time(14)
            user = await session.get(User, 1)
            user.learning_mode = "qa"
            await session.commit()

            message = SimpleNamespace(
                from_user=SimpleNamespace(id=3001),
                text="❌ Отмена",
                answer=AsyncMock(),
            )
            state = SimpleNamespace(get_data=AsyncMock(return_value={}), update_data=AsyncMock())
            with patch(
                "app.bot.handlers.messages._is_admin_flow_message",
                new_callable=AsyncMock, return_value=False,
            ), patch(
                "app.bot.handlers.messages._migrate_legacy_course_mode_to_qa",
                new_callable=AsyncMock,
            ), patch(
                "app.bot.handlers.messages.bot_locale_map",
                return_value={"uz": "❌ Отмена"},
            ), patch(
                "app.bot.handlers.messages.delete_message_safely",
                new_callable=AsyncMock,
            ) as deleted, patch(
                "app.bot.handlers.messages._edit_reminder_panel",
                new_callable=AsyncMock,
            ) as panel:
                await handle_text_message(message, state, session)
                state.update_data.assert_awaited_once_with(smart_reminder_interaction=None)
                deleted.assert_awaited_once()
                panel.assert_awaited_once()

        async with self.sessions() as session:
            saved = await session.get(CourseProgress, 1)
            self.assertEqual(saved.waiting_for, "none")
            self.assertTrue(saved.reminder_enabled)
            self.assertEqual(saved.reminder_time, time(14))

    async def test_course_branch_text_cancel_preserves_legacy_reminder_on(self):
        """Exercise the second text branch without changing its old semantics."""
        async with self.sessions() as session:
            progress = await session.scalar(
                select(CourseProgress).where(CourseProgress.user_id == 1)
            )
            progress.waiting_for = "reminder_setup"
            progress.reminder_time = time(20)
            user = await session.get(User, 1)
            user.learning_mode = "course"
            await session.commit()

            message = SimpleNamespace(
                from_user=SimpleNamespace(id=3001),
                text="❌ Отмена",
                answer=AsyncMock(),
            )
            state = SimpleNamespace(get_data=AsyncMock(return_value={}), update_data=AsyncMock())
            # The early branch sees no progress; the later branch retrieves
            # the real session-backed record via its legacy course route.
            repo_instance = CourseProgressRepository(session)
            repo_instance.get_by_user_id = AsyncMock(side_effect=[None, progress])
            fake_engine = SimpleNamespace(
                progress_repo=repo_instance,
                get_current_lesson=AsyncMock(
                    return_value=(user, progress, SimpleNamespace(id=1), None)
                ),
            )
            with patch(
                "app.bot.handlers.messages._is_admin_flow_message",
                new_callable=AsyncMock, return_value=False,
            ), patch(
                "app.bot.handlers.messages._migrate_legacy_course_mode_to_qa",
                new_callable=AsyncMock,
            ), patch(
                "app.bot.handlers.messages._is_stale_course_menu_text",
                return_value=False,
            ), patch(
                "app.bot.handlers.messages._ensure_active_course_access",
                new_callable=AsyncMock, return_value=True,
            ), patch(
                "app.bot.handlers.messages._ensure_trial_lesson_access",
                new_callable=AsyncMock, return_value=True,
            ), patch(
                "app.bot.handlers.messages.CourseEngineService",
                return_value=fake_engine,
            ), patch(
                "app.bot.handlers.messages.bot_locale_map",
                return_value={"uz": "❌ Отмена"},
            ), patch(
                "app.bot.handlers.messages.delete_message_safely",
                new_callable=AsyncMock,
            ) as deleted, patch(
                "app.bot.handlers.messages._edit_reminder_panel",
                new_callable=AsyncMock,
            ) as panel:
                await handle_text_message(message, state, session)
                state.update_data.assert_awaited_once_with(smart_reminder_interaction=None)
                self.assertEqual(repo_instance.get_by_user_id.await_count, 1)
                fake_engine.get_current_lesson.assert_awaited_once()
                deleted.assert_awaited_once()
                panel.assert_awaited_once()

        async with self.sessions() as session:
            saved = await session.get(CourseProgress, 1)
            self.assertEqual(saved.waiting_for, "none")
            self.assertTrue(saved.reminder_enabled)
            self.assertEqual(saved.reminder_time, time(20))


class SmartReminderP0LearningAndDeletionEvidenceTests(unittest.IsolatedAsyncioTestCase):
    """P0 evidence boundaries, not new dispatcher or cancellation behavior."""

    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.day = date(2026, 10, 26)
        async with self.sessions() as session:
            session.add(
                User(
                    id=1, telegram_id=3001, status="active",
                    payment_status="approved", language="uz",
                )
            )
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_reward_xp_is_not_verified_study_pace(self):
        """Today's total XP is deliberately broader than verified learning."""
        async with self.sessions() as session:
            session.add(
                CourseXpEvent(
                    user_id=1, activity_type="reward_chest",
                    activity_ref="chest:today", xp=200,
                    activity_date=self.day, week_start=self.day,
                )
            )
            await session.commit()
            signals = LearningSignalsService(session)
            xp, refs, types = await signals._today(1, self.day)
            evidence, active_days = await signals._evidence_and_pace(1, self.day)

            self.assertEqual(xp, 200)
            self.assertEqual(refs, {"chest:today"})
            self.assertEqual(types, {"reward_chest"})
            self.assertEqual((evidence, active_days), (0, 0))

            session.add(
                CourseXpEvent(
                    user_id=1, activity_type="lesson",
                    activity_ref="v3-part:hsk1:1:complete", xp=20,
                    activity_date=self.day, week_start=self.day,
                )
            )
            await session.commit()
            xp, refs, types = await signals._today(1, self.day)
            evidence, active_days = await signals._evidence_and_pace(1, self.day)
            self.assertEqual(xp, 220)
            self.assertIn("lesson", types)
            self.assertEqual((evidence, active_days), (1, 1))

    async def test_practice_replay_next_day_is_not_fresh_learning(self):
        """A stable legacy session ID is not a new dated learning receipt."""
        async with self.sessions() as session:
            service = CourseMiniAppPracticeService(session)
            # Freeze only the question bank and local day. Grading, canonical
            # ownership, event dedupe and XP writes use their real SQLite paths.
            question = {
                "id": "p0-question", "level": "hsk1", "lesson": 1,
                "answer_index": 0,
            }
            with patch.object(service, "_questions", new=AsyncMock(return_value=[question])), patch.object(
                CourseGamificationService, "_local_day", return_value=self.day,
            ):
                started = await service.start(
                    3001, mode="mock", level="hsk1", lang="uz", gate_checked=True,
                )
                self.assertTrue(started["ok"])
                session_id = started["session"]["id"]
                arguments = dict(
                    session_id=session_id, mode="mock", level="hsk1", lang="uz", skill="",
                    answers=[{"question_id": question["id"], "selected_index": 0}],
                    gate_checked=True,
                )
                first = await service.complete(3001, **arguments)
            self.assertTrue(first["ok"])
            self.assertEqual(first["percent"], 100)
            self.assertGreater(first["reward"]["awarded_xp"], 0)
            events_before = list((await session.scalars(
                select(CourseMiniAppEvent).order_by(CourseMiniAppEvent.id)
            )).all())
            original_events = [(row.id, row.created_at) for row in events_before]

            next_day = self.day + timedelta(days=1)
            with patch.object(service, "_questions", new=AsyncMock(return_value=[question])), patch.object(
                CourseGamificationService, "_local_day", return_value=next_day,
            ):
                replay = await service.complete(3001, **arguments)
            self.assertTrue(replay["ok"])
            self.assertTrue(replay["reward"]["duplicate"])
            self.assertEqual(replay["reward"]["awarded_xp"], 0)

        # Reload persisted data rather than relying on the request's identity map.
        async with self.sessions() as session:
            xp = list((await session.scalars(select(CourseXpEvent))).all())
            self.assertEqual(len(xp), 1)
            self.assertEqual((xp[0].user_id, xp[0].activity_type, xp[0].activity_date),
                             (1, "test", self.day))
            self.assertEqual(xp[0].activity_ref, f"{session_id}:completed")
            events = list((await session.scalars(
                select(CourseMiniAppEvent).order_by(CourseMiniAppEvent.id)
            )).all())
            self.assertEqual([(row.id, row.created_at) for row in events], original_events)
            self.assertEqual(sum(row.event_name == "test_completed" for row in events), 1)
            signals = LearningSignalsService(session)
            self.assertEqual(await signals._today(1, next_day), (0, set(), set()))
            self.assertEqual(await signals._evidence_and_pace(1, next_day), (1, 1))

    async def test_incomplete_practice_cannot_create_learning_evidence(self):
        async with self.sessions() as session:
            service = CourseMiniAppPracticeService(session)
            question = {"id": "p0-question", "level": "hsk1", "lesson": 1, "answer_index": 0}
            with patch.object(service, "_questions", new=AsyncMock(return_value=[question])):
                started = await service.start(
                    3001, mode="mock", level="hsk1", lang="uz", gate_checked=True,
                )
                rejected = await service.complete(
                    3001, session_id=started["session"]["id"], mode="mock",
                    level="hsk1", lang="uz", skill="", answers=[], gate_checked=True,
                )
            self.assertEqual(rejected, {"ok": False, "error": "practice_answers_incomplete"})
        async with self.sessions() as session:
            self.assertEqual(list((await session.scalars(select(CourseXpEvent))).all()), [])
            events = list((await session.scalars(select(CourseMiniAppEvent))).all())
            self.assertEqual([row.event_name for row in events], ["test_started"])
            signals = LearningSignalsService(session)
            self.assertEqual(await signals._today(1, self.day), (0, set(), set()))
            self.assertEqual(await signals._evidence_and_pace(1, self.day), (0, 0))

    async def test_submitted_deletion_is_visible_while_account_still_exists(self):
        """Pending deletion is not a completed purge or a status='blocked'."""
        async with self.sessions() as session:
            submitted = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
            session.add(
                AccountDeletionRequest(
                    id="11111111-2222-3333-4444-555555555555",
                    user_id=1,
                    active_user_id=1,
                    provider="telegram",
                    status="submitted",
                    secret_hash="a" * 64,
                    client_hash="b" * 64,
                    created_at=submitted,
                    expires_at=submitted + timedelta(days=2),
                    requested_at=submitted,
                    due_at=submitted + timedelta(days=14),
                )
            )
            await session.commit()
            user = await session.get(User, 1)
            pending = await session.scalar(
                select(AccountDeletionRequest).where(
                    AccountDeletionRequest.active_user_id == user.id,
                    AccountDeletionRequest.status == "submitted",
                )
            )
            self.assertIsNotNone(user)
            self.assertEqual(user.status, "active")
            self.assertIsNotNone(pending)
            self.assertEqual(pending.user_id, user.id)
            # Smart send/claim MUST veto this row in P1/P2; no such veto
            # exists today and these P0 tests must not pretend it does.



if __name__ == "__main__":
    unittest.main()

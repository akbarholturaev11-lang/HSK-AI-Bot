import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.bot.handlers.course import _show_required_channel_for_pending_action
from app.bot.handlers.required_channel import force_sub_check
from app.bot.keyboards.onboarding import course_mode_entry_keyboard
from app.bot.middlewares.required_channel import (
    FORCE_SUB_ACTION_OPEN_COURSE,
    FORCE_SUB_ACTION_OPEN_FREE_QA,
    PENDING_FORCE_SUB_ACTION,
    PENDING_FORCE_SUB_PAYLOAD,
)
from app.services.course_miniapp_onboarding_service import CourseMiniAppOnboardingService
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService


class CourseModeEntryKeyboardTests(unittest.TestCase):
    def test_course_button_uses_callback_so_force_sub_can_run_first(self):
        keyboard = course_mode_entry_keyboard("ru")
        course_button = keyboard.inline_keyboard[0][0]
        qa_button = keyboard.inline_keyboard[1][0]

        self.assertEqual(course_button.callback_data, "mode:course")
        self.assertIsNone(course_button.web_app)
        self.assertEqual(qa_button.callback_data, "mode:free_qa")


class _FakeForceSubState:
    def __init__(self, data):
        self.data = dict(data)

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **values):
        self.data.update(values)


class RequiredChannelResumeTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _callback():
        return SimpleNamespace(
            from_user=SimpleNamespace(id=123),
            bot=SimpleNamespace(),
            answer=AsyncMock(),
            message=SimpleNamespace(
                message_id=10,
                delete=AsyncMock(),
                answer=AsyncMock(),
            ),
        )

    async def test_force_sub_check_resumes_pending_course_mode(self):
        callback = self._callback()
        state = _FakeForceSubState(
            {
                PENDING_FORCE_SUB_ACTION: FORCE_SUB_ACTION_OPEN_COURSE,
                PENDING_FORCE_SUB_PAYLOAD: {"source": "mode_course"},
            }
        )
        session = SimpleNamespace(flush=AsyncMock())
        user = SimpleNamespace(language="uz", last_active_at=None)

        with (
            patch("app.bot.handlers.required_channel.UserRepository") as user_repo_class,
            patch("app.bot.handlers.required_channel.RequiredChannelService") as service_class,
            patch("app.bot.handlers.course.show_course_level_choice", new=AsyncMock()) as show_level,
        ):
            user_repo_class.return_value.get_by_telegram_id = AsyncMock(return_value=user)
            service_class.return_value.missing_channels = AsyncMock(return_value=[])

            await force_sub_check(callback, state, session)

        show_level.assert_awaited_once()
        kwargs = show_level.await_args.kwargs
        self.assertEqual(kwargs["lang"], "uz")
        self.assertIsNone(state.data[PENDING_FORCE_SUB_ACTION])
        self.assertIsNone(state.data[PENDING_FORCE_SUB_PAYLOAD])

    async def test_force_sub_check_resumes_pending_free_qa_mode(self):
        callback = self._callback()
        state = _FakeForceSubState(
            {
                PENDING_FORCE_SUB_ACTION: FORCE_SUB_ACTION_OPEN_FREE_QA,
                PENDING_FORCE_SUB_PAYLOAD: {"source": "mode_free_qa"},
            }
        )
        session = SimpleNamespace(flush=AsyncMock())
        user = SimpleNamespace(language="uz", last_active_at=None)

        with (
            patch("app.bot.handlers.required_channel.UserRepository") as user_repo_class,
            patch("app.bot.handlers.required_channel.RequiredChannelService") as service_class,
            patch("app.bot.handlers.course.show_free_qa_level_choice", new=AsyncMock()) as show_level,
        ):
            user_repo_class.return_value.get_by_telegram_id = AsyncMock(return_value=user)
            service_class.return_value.missing_channels = AsyncMock(return_value=[])

            await force_sub_check(callback, state, session)

        show_level.assert_awaited_once()
        kwargs = show_level.await_args.kwargs
        self.assertEqual(kwargs["lang"], "uz")
        self.assertIsNone(state.data[PENDING_FORCE_SUB_ACTION])
        self.assertIsNone(state.data[PENDING_FORCE_SUB_PAYLOAD])


class RequiredChannelPromptTests(unittest.IsolatedAsyncioTestCase):
    async def test_pending_mode_required_channels_edit_current_message(self):
        callback = SimpleNamespace(
            from_user=SimpleNamespace(id=123),
            bot=SimpleNamespace(),
            answer=AsyncMock(),
            message=SimpleNamespace(
                message_id=10,
                edit_text=AsyncMock(),
                answer=AsyncMock(),
            ),
        )
        state = _FakeForceSubState({})
        session = SimpleNamespace(commit=AsyncMock(), flush=AsyncMock())
        user = SimpleNamespace(force_sub_required_at=None)

        with patch("app.bot.handlers.course.RequiredChannelService") as service_class:
            service = service_class.return_value
            service.missing_channels = AsyncMock(return_value=[SimpleNamespace()])
            service.build_required_text.return_value = "join channels"
            service.build_required_keyboard.return_value = None

            blocked = await _show_required_channel_for_pending_action(
                callback=callback,
                state=state,
                session=session,
                user=user,
                lang="uz",
                action=FORCE_SUB_ACTION_OPEN_COURSE,
                payload={"source": "mode_course"},
            )

        self.assertTrue(blocked)
        callback.message.edit_text.assert_awaited_once()
        callback.message.answer.assert_not_awaited()
        self.assertEqual(state.data[PENDING_FORCE_SUB_ACTION], FORCE_SUB_ACTION_OPEN_COURSE)


class CourseMiniAppOnboardingValidationTests(unittest.TestCase):
    def test_levels_are_normalized_without_inventing_content_levels(self):
        self.assertEqual(CourseMiniAppOnboardingService.normalize_level("Beginner"), "beginner")
        self.assertEqual(CourseMiniAppOnboardingService.content_level("beginner"), "hsk1")
        self.assertEqual(CourseMiniAppOnboardingService.render_level("hsk4", 12), "hsk4b")
        with self.assertRaises(ValueError):
            CourseMiniAppOnboardingService.normalize_level("hsk5")


class CourseMiniAppOnboardingFlowTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _profile():
        return SimpleNamespace(
            id=7,
            goal="hsk_exam",
            daily_minutes=10,
            start_mode="continue",
            timezone_offset_minutes=0,
            onboarding_completed_at=None,
        )

    @staticmethod
    async def _save_profile(profile, **values):
        profile.goal = values["goal"]
        profile.daily_minutes = values["daily_minutes"]
        profile.start_mode = values["start_mode"]
        profile.timezone_offset_minutes = values["timezone_offset_minutes"]
        if values["complete_onboarding"]:
            profile.onboarding_completed_at = datetime.now(timezone.utc)
        return profile

    async def test_new_user_gets_first_lesson_without_payment_changes(self):
        session = SimpleNamespace(commit=AsyncMock())
        service = CourseMiniAppOnboardingService(session)
        user = SimpleNamespace(
            id=4,
            telegram_id=123,
            level="beginner",
            learning_mode="qa",
            voice_mode="none",
            status="trial",
            payment_status="none",
            trial_course_lesson_id=None,
            trial_course_started_at=None,
        )
        profile = self._profile()
        progress = SimpleNamespace(level="beginner", current_lesson_id=None)
        lesson = SimpleNamespace(id=10, lesson_order=1, level="hsk1")

        service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
        service.profile_service = SimpleNamespace(
            validate_preferences=CourseMiniAppProfileService.validate_preferences,
            get_or_create=AsyncMock(return_value=profile),
            save_preferences=AsyncMock(side_effect=self._save_profile),
        )
        service.engine = SimpleNamespace(
            progress_repo=SimpleNamespace(
                get_by_user_id=AsyncMock(return_value=None),
                create=AsyncMock(return_value=progress),
                set_current_lesson_and_step=AsyncMock(),
            ),
            lesson_repo=SimpleNamespace(
                get_by_id=AsyncMock(return_value=None),
                get_first_by_level=AsyncMock(return_value=lesson),
            ),
        )
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))

        with (
            patch(
                "app.services.course_miniapp_onboarding_service.CourseTrialService"
            ) as trial_class,
            patch(
                "app.services.course_miniapp_onboarding_service.CourseMiniAppAnalyticsService",
                return_value=analytics,
            ),
        ):
            trial_class.return_value.ensure_trial_lesson = AsyncMock(return_value=True)
            result = await service.complete(
                123,
                level="beginner",
                goal="hsk_exam",
                daily_minutes=10,
                start_mode="lesson_1",
                timezone_offset_minutes=300,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["level"], "hsk1")
        self.assertEqual(result["lesson"], 1)
        self.assertEqual(user.learning_mode, "course")
        self.assertEqual(user.payment_status, "none")
        service.engine.progress_repo.set_current_lesson_and_step.assert_awaited_once()
        self.assertEqual(analytics.record_server_event.await_count, 5)

    async def test_cross_level_lesson_one_does_not_reset_existing_progress(self):
        session = SimpleNamespace(commit=AsyncMock())
        service = CourseMiniAppOnboardingService(session)
        user = SimpleNamespace(id=4, telegram_id=123, level="hsk2")
        profile = self._profile()
        progress = SimpleNamespace(level="hsk2", current_lesson_id=20)
        lesson = SimpleNamespace(id=20, lesson_order=4, level="hsk2")

        service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
        service.profile_service = SimpleNamespace(
            validate_preferences=CourseMiniAppProfileService.validate_preferences,
            get_or_create=AsyncMock(return_value=profile),
        )
        service.engine = SimpleNamespace(
            progress_repo=SimpleNamespace(get_by_user_id=AsyncMock(return_value=progress)),
            lesson_repo=SimpleNamespace(get_by_id=AsyncMock(return_value=lesson)),
        )

        result = await service.complete(
            123,
            level="hsk1",
            goal="hsk_exam",
            daily_minutes=10,
            start_mode="lesson_1",
        )

        self.assertEqual(result, {"ok": False, "error": "course_level_change_requires_placement"})
        session.commit.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()

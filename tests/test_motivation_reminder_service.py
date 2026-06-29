import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace

from app.bot.keyboards.course import course_intro_keyboard
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.services.motivation_reminder_service import MotivationReminderService, _button
from app.services.notification_template_service import (
    KEY_LESSON_UNFINISHED,
    MOTIVATION_KEYS,
    default_text,
)


class _EmptyRows:
    def all(self):
        return []


class _CaptureSession:
    def __init__(self):
        self.queries = []

    async def execute(self, query):
        self.queries.append(query)
        return _EmptyRows()


class MotivationReminderServiceTests(unittest.TestCase):
    def test_overtaken_gap_never_claims_zero_xp(self):
        self.assertEqual(MotivationReminderService._xp_gap_to_above(120, 120), 1)
        self.assertEqual(MotivationReminderService._xp_gap_to_above(135, 120), 15)

    def test_profile_offset_respects_saved_user_timezone(self):
        self.assertEqual(
            MotivationReminderService._profile_offset(
                SimpleNamespace(timezone_offset_minutes=0)
            ),
            0,
        )
        self.assertEqual(
            MotivationReminderService._profile_offset(
                SimpleNamespace(timezone_offset_minutes=300)
            ),
            300,
        )
        self.assertEqual(
            MotivationReminderService._profile_offset(
                SimpleNamespace(timezone_offset_minutes=999)
            ),
            840,
        )
        self.assertEqual(
            MotivationReminderService._profile_offset(
                SimpleNamespace(timezone_offset_minutes=None)
            ),
            300,
        )

    def test_lesson_unfinished_template_is_registered(self):
        self.assertIn(KEY_LESSON_UNFINISHED, MOTIVATION_KEYS)
        self.assertIn("{lesson}", default_text(KEY_LESSON_UNFINISHED, "uz"))

    def test_lesson_label_uses_level_and_order(self):
        event = CourseMiniAppEvent(
            telegram_id=1001,
            event_name="lesson_started",
            level="hsk2",
            lesson_order=4,
        )
        self.assertEqual(
            MotivationReminderService._lesson_label(event, "uz"),
            "HSK2 4-dars",
        )

    def test_local_day_bounds_respect_offset(self):
        start, end = MotivationReminderService._local_day_bounds_utc(
            date(2026, 6, 29),
            300,
        )
        self.assertEqual(start, datetime(2026, 6, 28, 19, 0, tzinfo=timezone.utc))
        self.assertEqual(end, datetime(2026, 6, 29, 19, 0, tzinfo=timezone.utc))

    def test_reminder_button_opens_miniapp(self):
        markup = _button("uz")
        self.assertIsNotNone(markup.inline_keyboard[0][0].web_app)

    def test_course_block_keyboard_has_miniapp_button(self):
        markup = course_intro_keyboard("uz")
        self.assertIsNotNone(markup.inline_keyboard[-1][0].web_app)


class MotivationReminderServiceQueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_reminders_are_not_limited_to_paid_active_users(self):
        session = _CaptureSession()

        await MotivationReminderService(session).send_due_reminders(SimpleNamespace())

        compiled = str(session.queries[0].compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("blocked", compiled)
        self.assertNotIn("users.status = 'active'", compiled)


class MotivationReminderServiceRankChangeTests(unittest.TestCase):
    def test_rank_passed_is_not_a_chat_notification_template(self):
        self.assertNotIn("rating_passed", MOTIVATION_KEYS)


if __name__ == "__main__":
    unittest.main()

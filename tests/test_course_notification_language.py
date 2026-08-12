"""The in-app feed must speak the language the learner is reading in now.

Notification rows keep the text as it was sent over Telegram, so switching the
app language used to leave Uzbek reminders sitting inside a Tajik interface.
`params` carries the template and its arguments so the row can be rebuilt.
"""

import unittest
from datetime import datetime, timezone

from app.services.course_notification_service import CourseNotificationService


class _Row:
    """Stand-in for CourseUserNotification: the service only reads attributes."""

    def __init__(self, *, language, title, body, params=None, key="lesson_time"):
        self.id = 1
        self.key = key
        self.language = language
        self.title = title
        self.body = body
        self.params = params
        self.action = "course"
        self.level = None
        self.lesson_order = None
        self.created_at = datetime.now(timezone.utc)


UZ_TITLE = "Dars vaqti keldi"
UZ_BODY = "O'tgan darsda siz 3 ta so'z va 2 ta dialog o'rgandingiz."
PARAMS = {"template": "course_reminder_text", "vocab": 3, "dialogues": 2}


class NotificationLanguageTests(unittest.TestCase):
    def test_same_language_is_returned_untouched(self):
        row = _Row(language="uz", title=UZ_TITLE, body=UZ_BODY, params=PARAMS)
        payload = CourseNotificationService.payload(row, "uz")
        self.assertEqual(payload["title"], UZ_TITLE)
        self.assertEqual(payload["body"], UZ_BODY)

    def test_reader_language_rebuilds_title_and_body(self):
        row = _Row(language="uz", title=UZ_TITLE, body=UZ_BODY, params=PARAMS)
        payload = CourseNotificationService.payload(row, "tj")
        self.assertEqual(payload["title"], "Вақти дарс расид")
        self.assertNotEqual(payload["body"], UZ_BODY)
        # The numbers are the learner's own progress and must survive.
        self.assertIn("3", payload["body"])
        self.assertIn("2", payload["body"])

    def test_rows_without_params_still_get_a_translated_title(self):
        row = _Row(language="uz", title=UZ_TITLE, body=UZ_BODY)
        payload = CourseNotificationService.payload(row, "ru")
        self.assertEqual(payload["title"], "Время урока")
        # No arguments were stored, so the body cannot be rebuilt.
        self.assertEqual(payload["body"], UZ_BODY)

    def test_unknown_reader_language_falls_back_to_the_stored_text(self):
        row = _Row(language="uz", title=UZ_TITLE, body=UZ_BODY, params=PARAMS)
        for reader in (None, "", "en", "zh"):
            with self.subTest(reader=reader):
                payload = CourseNotificationService.payload(row, reader)
                self.assertEqual(payload["title"], UZ_TITLE)
                self.assertEqual(payload["body"], UZ_BODY)

    def test_admin_template_uses_the_text_resolved_by_list_for_user(self):
        row = _Row(
            language="uz",
            title=UZ_TITLE,
            body=UZ_BODY,
            params={
                "template_service": "streak_risk",
                "days": 5,
                "_rendered": "Силсилаи 5 рӯза дар хатар аст.",
            },
            key="streak_risk",
        )
        payload = CourseNotificationService.payload(row, "tj")
        self.assertIn("5", payload["body"])
        self.assertNotEqual(payload["body"], UZ_BODY)

    def test_admin_template_without_resolution_keeps_the_stored_body(self):
        row = _Row(
            language="uz",
            title=UZ_TITLE,
            body=UZ_BODY,
            params={"template_service": "streak_risk", "days": 5},
            key="streak_risk",
        )
        payload = CourseNotificationService.payload(row, "tj")
        self.assertEqual(payload["body"], UZ_BODY)
        self.assertEqual(payload["title"], "Силсила дар хатар аст")

    def test_broken_template_never_empties_the_feed(self):
        row = _Row(
            language="uz",
            title=UZ_TITLE,
            body=UZ_BODY,
            params={"template": "no_such_template_key", "vocab": 3},
        )
        payload = CourseNotificationService.payload(row, "tj")
        self.assertTrue(payload["title"])
        self.assertTrue(payload["body"])


if __name__ == "__main__":
    unittest.main()

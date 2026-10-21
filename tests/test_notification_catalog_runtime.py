"""Local notification adoption preserves custom copy and delivery contracts."""
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app.services.course_notification_service import TITLE_BY_KEY, notification_title
from app.services.course_reminder_service import _reminder_keyboard
from app.services.discount_notification_service import DiscountNotificationService
from app.services.generated.notification_i18n import NOTIFICATION_MESSAGES
from app.services.motivation_reminder_service import _button
from app.services.notification_i18n import notification_message
from app.services.notification_template_service import (
    DEFAULT_TEXTS, NotificationTemplateService, default_text,
)


class NotificationCanonicalRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def test_all_legacy_titles_and_defaults_keep_exact_wording(self):
        for key, texts in TITLE_BY_KEY.items():
            for locale, text in texts.items():
                self.assertEqual(notification_title(key, locale), text)
        for key, texts in DEFAULT_TEXTS.items():
            for locale, text in texts.items():
                self.assertEqual(default_text(key, locale), text)

    def test_canonical_changes_reach_live_title_and_keyboard_consumers(self):
        with patch.dict(NOTIFICATION_MESSAGES["uz"], {
            "course.title.lesson_time": "QA title",
            "reminder.courseContinue": "QA continue",
            "reminder.continueLessonNumber": "QA {lesson}",
        }):
            self.assertEqual(notification_title("lesson_time", "uz"), "QA title")
            button = _reminder_keyboard("uz").inline_keyboard[0][0]
            self.assertEqual(button.text, "QA continue")
            self.assertEqual(button.callback_data, "course:continue")
            self.assertEqual(_button("uz", lesson=4).inline_keyboard[0][0].text, "QA 4")

    async def test_database_custom_template_keeps_precedence(self):
        service = NotificationTemplateService(None)
        service._get_row = AsyncMock(return_value=SimpleNamespace(
            enabled=True, text_uz="  authored by admin  ",
            media_type="photo", media_path="existing-image.png",
        ))
        with patch.dict(NOTIFICATION_MESSAGES["uz"], {"reminder.default.daily_goal": "QA default"}):
            result = await service.resolve("daily_goal", "uz")
            self.assertEqual(result, {"text": "authored by admin", "media_type": "photo",
                                      "media_path": "existing-image.png"})
            service._get_row.return_value.text_uz = ""
            self.assertEqual((await service.resolve("daily_goal", "uz"))["text"], "QA default")
            service._get_row.return_value.enabled = False
            self.assertIsNone(await service.resolve("daily_goal", "uz"))

    async def test_campaign_copy_precedes_fixed_labels_and_phone_body_is_preserved(self):
        service = DiscountNotificationService(None)
        campaign = SimpleNamespace(title_uz="Campaign title", title="Fallback", percent=20,
                                   reason_uz="Authored reason", reason="")
        with patch.dict(NOTIFICATION_MESSAGES["uz"], {"discount.campaignFallbackTitle": "QA fallback",
                                                     "discount.discount": "QA discount"}):
            phone = await service._notification_text(campaign, "uz", None, for_phone=True)
            self.assertEqual(phone, "<b>Campaign title</b>\nQA discount: <b>20%</b>\n\nAuthored reason")
            campaign.title_uz = campaign.title = ""
            self.assertIn("<b>QA fallback</b>", await service._notification_text(campaign, "uz", None))

    def test_missing_keys_locale_fallback_and_placeholders(self):
        self.assertEqual(notification_message("unknown", "uz", "old fallback"), "old fallback")
        self.assertEqual(notification_message("course.title.lesson_time", "unsupported"),
                         NOTIFICATION_MESSAGES["ru"]["course.title.lesson_time"])
        self.assertEqual(notification_message("reminder.continueLessonNumber", "uz", lesson=7),
                         "▶️ Davom etish · 7-dars")
        self.assertIn("{lesson}", notification_message("reminder.continueLessonNumber", "uz"))


if __name__ == "__main__":
    unittest.main()

"""Runtime contract for localized release-feedback buttons and copy."""
import unittest
from urllib.parse import parse_qs, urlparse

from app.bot.keyboards.release_feedback import (
    release_feedback_after_rating_keyboard,
    release_feedback_discount_keyboard,
    release_feedback_rating_keyboard,
)
from app.bot.utils.i18n import t
from app.services.release_feedback_service import (
    _lang,
    release_feedback_discount_text,
    release_feedback_low_rating_comment_text,
    release_feedback_optional_comment_text,
    release_feedback_prompt,
    release_feedback_thanks_text,
    release_feedback_try_already_text,
    release_feedback_try_granted_text,
)


MESSAGES = {
    "prompt": release_feedback_prompt,
    "lowRatingComment": release_feedback_low_rating_comment_text,
    "optionalComment": release_feedback_optional_comment_text,
    "thanks": release_feedback_thanks_text,
    "discount": release_feedback_discount_text,
    "tryGranted": release_feedback_try_granted_text,
    "tryAlready": release_feedback_try_already_text,
}

BUTTONS = {
    "uz": {
        "tryButton": "🚀 Sinab ko'rish",
        "discountButton": "🎁 20% chegirmani olish",
        "commentButton": "✍️ Izoh yozish",
        "skipButton": "➡️ O'tkazib yuborish",
    },
    "ru": {
        "tryButton": "🚀 Попробовать",
        "discountButton": "🎁 Получить скидку 20%",
        "commentButton": "✍️ Оставить комментарий",
        "skipButton": "➡️ Пропустить",
    },
    "tj": {
        "tryButton": "🚀 Санҷидан",
        "discountButton": "🎁 20% тахфифро гирифтан",
        "commentButton": "✍️ Шарҳ навиштан",
        "skipButton": "➡️ Гузарондан",
    },
}


class ReleaseFeedbackLocalizationTests(unittest.TestCase):
    def test_service_messages_use_local_catalog_for_all_existing_languages(self):
        for lang in ("uz", "ru", "tj"):
            for key, render in MESSAGES.items():
                with self.subTest(locale=lang, key=key):
                    self.assertEqual(
                        render(lang),
                        t(f"common.bot.releaseFeedback.{key}", lang),
                    )
        self.assertEqual(_lang("tg"), "tj")
        self.assertEqual(release_feedback_prompt("tg"), release_feedback_prompt("tj"))

    def test_rating_buttons_follow_account_language_and_keep_callbacks(self):
        for lang, labels in BUTTONS.items():
            with self.subTest(locale=lang):
                markup = release_feedback_rating_keyboard(42, lang)
                self.assertEqual(markup.inline_keyboard[0][0].text, labels["tryButton"])
                self.assertEqual(markup.inline_keyboard[0][0].callback_data, "relfb:42:try")
                self.assertEqual(
                    [button.callback_data for button in markup.inline_keyboard[1]],
                    [f"relfb:42:rate:{rating}" for rating in range(1, 6)],
                )

                after = release_feedback_after_rating_keyboard(
                    42, discount_campaign_id=None, lang=lang
                )
                self.assertEqual(after.inline_keyboard[0][0].text, labels["commentButton"])
                self.assertEqual(after.inline_keyboard[0][0].callback_data, "relfb:42:comment")
                self.assertEqual(after.inline_keyboard[1][0].text, labels["skipButton"])
                self.assertEqual(after.inline_keyboard[1][0].callback_data, "relfb:42:skip")

    def test_discount_button_text_and_destination_are_preserved(self):
        for lang, labels in BUTTONS.items():
            with self.subTest(locale=lang):
                for markup in (
                    release_feedback_discount_keyboard(81, lang),
                    release_feedback_after_rating_keyboard(
                        42, discount_campaign_id=81, lang=lang
                    ),
                ):
                    button = markup.inline_keyboard[0][0]
                    self.assertEqual(button.text, labels["discountButton"])
                    params = parse_qs(urlparse(button.web_app.url).query)
                    self.assertEqual(params["source"], ["release_feedback_discount"])
                    self.assertEqual(params["mode"], ["admin_discount"])
                    self.assertEqual(params["campaign_id"], ["81"])


if __name__ == "__main__":
    unittest.main()

"""Runtime checks for localized learner-facing promo buttons."""
import unittest

from app.bot.keyboards.promo_button import (
    build_promo_button_markup,
    default_promo_button_text,
)


LABELS = {
    "uz": {
        "subscription": "💎 Obuna",
        "partner": "🤝 Partnyor",
        "course": "📚 Kurs rejimi",
        "reminder": "⏰ Eslatma vaqti",
        "help": "❓ Yordam",
        "contact": "👤 Admin bilan aloqa",
        "profile": "👤 Profil",
        "url": "🔗 Ochish",
    },
    "ru": {
        "subscription": "💎 Подписка",
        "partner": "🤝 Партнёрство",
        "course": "📚 Режим курса",
        "reminder": "⏰ Напоминание",
        "help": "❓ Помощь",
        "contact": "👤 Связаться с админом",
        "profile": "👤 Профиль",
        "url": "🔗 Открыть",
    },
    "tj": {
        "subscription": "💎 Обуна",
        "partner": "🤝 Ҳамкорӣ",
        "course": "📚 Реҷаи курс",
        "reminder": "⏰ Вақти ёдраскунак",
        "help": "❓ Ёрдам",
        "contact": "👤 Тамос бо админ",
        "profile": "👤 Профил",
        "url": "🔗 Кушодан",
    },
}


class PromoButtonLocalizationTests(unittest.IsolatedAsyncioTestCase):
    def test_default_labels_cover_locales_and_keep_russian_fallback(self):
        for locale, actions in LABELS.items():
            for action, expected in actions.items():
                with self.subTest(locale=locale, action=action):
                    self.assertEqual(default_promo_button_text(action, locale), expected)
        self.assertEqual(default_promo_button_text("course", "tg-TJ"), LABELS["tj"]["course"])
        self.assertEqual(default_promo_button_text("course", "unsupported"), LABELS["ru"]["course"])
        self.assertEqual(default_promo_button_text("unknown", "uz"), LABELS["uz"]["url"])

    async def test_default_course_button_keeps_callback_and_custom_copy(self):
        generated = await build_promo_button_markup(
            None, {"action": "course"}, lang="tj", source="localization_test"
        )
        button = generated.inline_keyboard[0][0]
        self.assertEqual(button.text, LABELS["tj"]["course"])
        self.assertEqual(button.callback_data, "promo:action:course")

        custom = await build_promo_button_markup(
            None, {"action": "course", "text": "My custom label"},
            lang="tj", source="localization_test",
        )
        custom_button = custom.inline_keyboard[0][0]
        self.assertEqual(custom_button.text, "My custom label")
        self.assertEqual(custom_button.callback_data, "promo:action:course")


if __name__ == "__main__":
    unittest.main()

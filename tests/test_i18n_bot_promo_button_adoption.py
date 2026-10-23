"""Promo button defaults use the shared local common catalog."""
import unittest

from scripts.i18n_build_local_catalogs import ROOT, read_sources


EXPECTED = {
    "uz": {
        "bot.promoButton.subscription": "💎 Obuna",
        "bot.promoButton.partner": "🤝 Partnyor",
        "bot.promoButton.course": "📚 Kurs rejimi",
        "bot.promoButton.reminder": "⏰ Eslatma vaqti",
        "bot.promoButton.help": "❓ Yordam",
        "bot.promoButton.contact": "👤 Admin bilan aloqa",
        "bot.promoButton.profile": "👤 Profil",
        "bot.promoButton.url": "🔗 Ochish",
    },
    "ru": {
        "bot.promoButton.subscription": "💎 Подписка",
        "bot.promoButton.partner": "🤝 Партнёрство",
        "bot.promoButton.course": "📚 Режим курса",
        "bot.promoButton.reminder": "⏰ Напоминание",
        "bot.promoButton.help": "❓ Помощь",
        "bot.promoButton.contact": "👤 Связаться с админом",
        "bot.promoButton.profile": "👤 Профиль",
        "bot.promoButton.url": "🔗 Открыть",
    },
    "tj": {
        "bot.promoButton.subscription": "💎 Обуна",
        "bot.promoButton.partner": "🤝 Ҳамкорӣ",
        "bot.promoButton.course": "📚 Реҷаи курс",
        "bot.promoButton.reminder": "⏰ Вақти ёдраскунак",
        "bot.promoButton.help": "❓ Ёрдам",
        "bot.promoButton.contact": "👤 Тамос бо админ",
        "bot.promoButton.profile": "👤 Профил",
        "bot.promoButton.url": "🔗 Кушодан",
    },
}


class BotPromoButtonAdoptionTests(unittest.TestCase):
    def test_existing_default_labels_are_centralized_without_copy_changes(self):
        source = read_sources(ROOT)
        for locale, expected in EXPECTED.items():
            with self.subTest(locale=locale):
                self.assertEqual({key: source[locale][key] for key in expected}, expected)


if __name__ == "__main__":
    unittest.main()

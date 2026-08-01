import unittest
from urllib.parse import parse_qs, urlsplit

from app.bot.handlers.commands import profile_menu_keyboard


class BotProfileDesktopCtaTests(unittest.TestCase):
    EXPECTED_LABELS = {
        "uz": "💻 Kompyuter ilovasi",
        "ru": "💻 Приложение для компьютера",
        "tj": "💻 Барномаи компютерӣ",
    }

    def test_desktop_cta_is_localized_and_opens_focused_profile_web_app(self):
        for language, expected_label in self.EXPECTED_LABELS.items():
            with self.subTest(language=language):
                keyboard = profile_menu_keyboard(language)
                matching_rows = [
                    row
                    for row in keyboard.inline_keyboard
                    if any(button.text == expected_label for button in row)
                ]

                self.assertEqual(len(matching_rows), 1)
                self.assertEqual(len(matching_rows[0]), 1)
                button = matching_rows[0][0]
                self.assertIsNone(button.callback_data)
                self.assertIsNone(button.url)
                self.assertIsNotNone(button.web_app)

                parsed = urlsplit(str(button.web_app.url))
                query = parse_qs(parsed.query)
                self.assertEqual(parsed.scheme, "https")
                self.assertTrue(parsed.netloc)
                self.assertEqual(query.get("lang"), [language])
                self.assertEqual(query.get("tab"), ["profile"])
                self.assertEqual(query.get("desktop_download"), ["1"])


if __name__ == "__main__":
    unittest.main()

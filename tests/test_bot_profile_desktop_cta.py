"""The desktop client's entry point, now one level deeper.

The profile used to carry a button per device. It now carries one "HSK AI
ilovalari" button, and the device choice happens after it — so the thing worth
pinning is that the desktop CTA still exists, still opens the Mini App focused
on its download, and is still reachable in every language. A rename that
quietly dropped one of the two clients would otherwise pass unnoticed.
"""

import unittest
from urllib.parse import parse_qs, urlsplit

from app.bot.handlers.commands import (
    APPS_MENU_CALLBACK,
    apps_menu_keyboard,
    profile_menu_keyboard,
)
from app.bot.utils.i18n import t


LANGUAGES = ("uz", "ru", "tj")


class ProfileAppsEntryTests(unittest.TestCase):
    def test_the_profile_offers_one_apps_button_per_language(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                keyboard = profile_menu_keyboard(language)
                matching = [
                    button
                    for row in keyboard.inline_keyboard
                    for button in row
                    if button.callback_data == APPS_MENU_CALLBACK
                ]
                self.assertEqual(len(matching), 1)
                self.assertEqual(matching[0].text, t("apps_menu_button", language))

    def test_the_profile_no_longer_names_a_single_device(self):
        # The old buttons were per device; if one comes back the learner is
        # once again asked to pick a product before they have seen either.
        stale = {
            "💻 Kompyuter ilovasi",
            "💻 Приложение для компьютера",
            "💻 Барномаи компютерӣ",
        }
        for language in LANGUAGES:
            with self.subTest(language=language):
                labels = {
                    button.text
                    for row in profile_menu_keyboard(language).inline_keyboard
                    for button in row
                }
                self.assertFalse(labels & stale)


class DesktopCtaTests(unittest.TestCase):
    def test_the_desktop_cta_still_opens_the_focused_profile_web_app(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                keyboard = apps_menu_keyboard(language)
                matching = [
                    button
                    for row in keyboard.inline_keyboard
                    for button in row
                    if button.text == t("apps_desktop_button", language)
                ]

                self.assertEqual(len(matching), 1)
                button = matching[0]
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

"""The profile's one door to every client, and what is behind it.

The profile used to carry a button per device, then a chooser with Android on
one side and the desktop client on the other. It now carries a single "HSK AI
ilovalari" button that opens the public download page, which picks the device
itself — the bot cannot see which one is holding it.

So the thing worth pinning is that the button is a real https link to that
page, in every language, and that the page it opens still offers both desktop
clients as well as Android. A rename that quietly dropped one of them would
otherwise pass unnoticed.
"""

import unittest
import unittest.mock
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from app.bot.handlers.android_app import ANDROID_APP_CALLBACK
from app.bot.handlers.commands import apps_button, profile_menu_keyboard
from app.bot.utils.i18n import t


LANGUAGES = ("uz", "ru", "tj")
PAGE_SCRIPT = Path("app/static/desktop-download-page.js")


def _apps_buttons(language):
    return [
        button
        for row in profile_menu_keyboard(language).inline_keyboard
        for button in row
        if button.text == t("apps_menu_button", language)
    ]


class ProfileAppsEntryTests(unittest.TestCase):
    def test_the_profile_offers_one_apps_button_per_language(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                self.assertEqual(len(_apps_buttons(language)), 1)

    def test_the_button_opens_the_download_page(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                button = _apps_buttons(language)[0]
                self.assertIsNone(button.callback_data)
                self.assertIsNone(button.web_app)

                parsed = urlsplit(str(button.url))
                query = parse_qs(parsed.query)
                self.assertEqual(parsed.scheme, "https")
                self.assertTrue(parsed.netloc)
                self.assertTrue(parsed.path.endswith("/desktop-download"))
                self.assertEqual(query.get("lang"), [language])
                # No platform is pinned: the page reads the device, and a
                # forced `platform=android` would offer an iPhone an APK.
                self.assertNotIn("platform", query)

    def test_a_broken_base_url_still_leaves_a_working_button(self):
        with unittest.mock.patch(
            "app.bot.handlers.commands.apps_download_page_url",
            return_value="http://not-https.example/desktop-download",
        ):
            button = apps_button("uz")

        self.assertIsNone(button.url)
        self.assertEqual(button.callback_data, ANDROID_APP_CALLBACK)

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


class DownloadPageTests(unittest.TestCase):
    def test_the_page_still_carries_both_desktop_clients_and_android(self):
        script = PAGE_SCRIPT.read_text(encoding="utf-8")

        self.assertIn(
            'var supportedPlatforms = ["ios", "macos", "android", "windows"]',
            script,
        )


if __name__ == "__main__":
    unittest.main()

"""The profile's one door to every client, and what is behind it.

The profile used to carry a button per device, then a chooser with Android on
one side and the desktop client on the other. It now carries a single "HSK AI
ilovalari" button that opens the Mini App profile on the card holding every
client at once — macOS, Windows and Android — with Android still handed over
in this chat.

So the thing worth pinning is that the button really is a Mini App button, in
every language, aimed at the profile tab with the card focused. A rename or a
refactor that quietly dropped the focus parameter would leave a learner on the
course tab wondering what they pressed.
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


def _apps_buttons(language):
    return [
        button
        for row in profile_menu_keyboard(language).inline_keyboard
        for button in row
        if button.text == t("apps_menu_button", language)
    ]


def _assert_opens_the_card(test, button, language):
    test.assertIsNone(button.callback_data)
    test.assertIsNone(button.url)
    test.assertIsNotNone(button.web_app)

    parsed = urlsplit(str(button.web_app.url))
    query = parse_qs(parsed.query)
    test.assertEqual(parsed.scheme, "https")
    test.assertTrue(parsed.netloc)
    test.assertEqual(query.get("lang"), [language])
    test.assertEqual(query.get("tab"), ["profile"])
    test.assertEqual(query.get("desktop_download"), ["1"])


class ProfileAppsEntryTests(unittest.TestCase):
    def test_the_profile_offers_one_apps_button_per_language(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                self.assertEqual(len(_apps_buttons(language)), 1)

    def test_the_button_opens_the_mini_app_card(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                _assert_opens_the_card(self, _apps_buttons(language)[0], language)

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


class LegacyChooserTests(unittest.TestCase):
    """An old profile message still carries the chooser callback.

    Nothing produces it any more, but a learner scrolling back to last week's
    profile will press it, and it must land on the same card as today's button
    rather than spin and do nothing.
    """

    def test_the_old_callback_still_reaches_the_card(self):
        self.assertEqual(APPS_MENU_CALLBACK, "profile_menu:apps")
        for language in LANGUAGES:
            with self.subTest(language=language):
                rows = apps_menu_keyboard(language).inline_keyboard
                buttons = [button for row in rows for button in row]
                self.assertEqual(len(buttons), 1)
                _assert_opens_the_card(self, buttons[0], language)


if __name__ == "__main__":
    unittest.main()

"""Bot UI runtime consumers preserve their labels, callbacks and fallback."""
import unittest
from unittest.mock import patch


class BotCatalogRuntimeTests(unittest.TestCase):
    def test_response_states_use_local_catalog_and_keep_uzbek_fallback(self):
        from app.bot.generated.bot_i18n import BOT_MESSAGES
        from app.bot.utils.response_effect import _select_states
        self.assertEqual(_select_states("qa", 1, "uz"), (
            "Analiz qilyapman...", "Javob tayyorlayapman...", "Tekshiryapman...", "O'ylayapman..."))
        self.assertEqual(_select_states("unknown", 1, "unsupported"), _select_states("qa", 9, "uz"))
        for mode in ("qa", "course", "image", "voice", "translate"):
            for locale in ("uz", "ru", "tj"):
                self.assertEqual(len(_select_states(mode, 1, locale)), 4)
        with patch.dict(BOT_MESSAGES["ru"], {"responseEffect.analyze": "Local fixture"}):
            self.assertEqual(_select_states("qa", None, "ru")[0], "Local fixture")

    def test_understood_keyboard_uses_catalog_without_callback_changes(self):
        from app.bot.generated.bot_i18n import BOT_MESSAGES
        from app.bot.keyboards.course_context import course_understood_keyboard
        for locale, label in (("uz", "✅ Tushundim, davom etamiz"),
                              ("ru", "✅ Понял(а), продолжаем"),
                              ("tj", "✅ Фаҳмидам, давом медиҳем")):
            keyboard = course_understood_keyboard(locale, "intro")
            self.assertEqual(keyboard.inline_keyboard[0][0].text, label)
            self.assertEqual(keyboard.inline_keyboard[0][0].callback_data, "course:go_vocab")
        self.assertIsNone(course_understood_keyboard("uz", "unknown"))
        with patch.dict(BOT_MESSAGES["ru"], {"courseKeyboard.understood": "Local fixture"}):
            self.assertEqual(course_understood_keyboard("unsupported", "grammar")
                             .inline_keyboard[0][0].text, "Local fixture")


if __name__ == "__main__":
    unittest.main()

"""Regression contracts for replacing duplicate in-page Back with Telegram BackButton.

Keep the in-page fallback when running outside an authenticated Telegram Mini App.
"""
import re
import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "app" / "static"
COURSE = (STATIC / "course-v3.html").read_text(encoding="utf-8")
DICT = (STATIC / "hsk-lugat.html").read_text(encoding="utf-8")


class TelegramBackDedupTests(unittest.TestCase):
    def test_five_section_buttons_are_marked(self):
        buttons = re.findall(r'<button class="[^"]*hsk-native-back-duplicate[^"]*"[^>]*>', COURSE)
        self.assertEqual(len(buttons), 5, buttons)
        for callback in ("closeUserProfile()", "RECOG.close()", "PRON.close()",
                         "MIST.close()", "TEST.close()"):
            self.assertTrue(any(callback in button for button in buttons), callback)

    def test_two_dictionary_buttons_are_marked(self):
        buttons = re.findall(r'<button class="[^"]*hsk-native-back-duplicate[^"]*"[^>]*>', DICT)
        self.assertEqual(len(buttons), 2, buttons)
        self.assertIn('id="list-back-btn"', DICT)
        self.assertIn('id="back-btn"', DICT)

    def test_only_hide_when_native_telegram_back_is_bound(self):
        for source in (COURSE, DICT):
            self.assertIn("html.hsk-telegram-back-active .hsk-native-back-duplicate{display:none!important}", source)
            self.assertIn("tg.initData", source)
            self.assertIn("BackButton.onClick", source)
            self.assertIn("classList.toggle", source)
        self.assertIn("NavBack._telegramBackBound=true", COURSE)
        self.assertIn("can&&NavBack._telegramBackBound&&tg.initData", COURSE)
        self.assertIn("nativeBackBound=true", DICT)

    def test_existing_nested_navigation_and_gates_remain(self):
        self.assertIn('if(inner()){showHub();return}', COURSE)
        self.assertIn('if(reviewOpen()){closeReview();return}', COURSE)
        self.assertIn('if(SECTION&&SECTION.close)SECTION.close()', COURSE)
        self.assertIn('BLOCK:["#paywall.on","#levelup.on",".caa-ov.on",".caa-app.on"]', COURSE)
        self.assertIn('if(!strokeModal.classList.contains(\'hidden\')) closeStrokeOrder()', DICT)
        self.assertIn('else closeDetailView()', DICT)
        self.assertIn('goBackToStudy()', DICT)


if __name__ == "__main__":
    unittest.main()

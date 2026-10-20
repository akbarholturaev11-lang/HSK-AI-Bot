"""Lock the local-first migration of reviewed Mini App memorization labels."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/static/course_v3_memorize.html"
REVIEW = ROOT / "localization/review/miniapp_memorize_inline_triage.json"
CALL = re.compile(r"\b(?:tr|t)\s*\(\s*\{\s*(?:uz|ru|tj)\s*:")


class MemorizationInlineLocaleTriageTests(unittest.TestCase):
    def test_all_reviewed_inline_locale_calls_are_migrated(self):
        source = SOURCE.read_text(encoding="utf-8")
        review = json.loads(REVIEW.read_text(encoding="utf-8"))
        occurrences = list(CALL.finditer(source))
        self.assertEqual(review["status"], "REVIEWED_INLINE_LABELS_LOCAL_FIRST_RUNTIME_NOT_VALIDATED")
        self.assertEqual(review["source"], "app/static/course_v3_memorize.html")
        self.assertEqual(occurrences, [])
        self.assertEqual(len(review["entries"]), 9)
        self.assertEqual(len(review["migrated_keys"]), 9)
        self.assertEqual(review["remaining"], [])
        for key in review["migrated_keys"]:
            with self.subTest(key=key):
                self.assertIn(f'memoMessage("{key}"', source)

    def test_dynamic_hanzi_prompt_keeps_named_placeholder_and_original_fallbacks(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('memoMessage("memorize.prompt.confusion"', source)
        self.assertIn('.replace("{hanzi}",H)', source)
        self.assertIn('uz:"Qaysini {hanzi} bilan adashtirishingiz mumkin?"', source)
        self.assertIn('ru:"Что можно спутать с {hanzi}?"', source)
        self.assertIn('tj:"Кадомро бо {hanzi} хато кардан мумкин?"', source)

    def test_local_catalog_values_match_all_original_labels(self):
        review = json.loads(REVIEW.read_text(encoding="utf-8"))
        expected = {
            "uz": {
                "listen": "Tinglash",
                "memorize.prompt.remember": "Eslab qolish uchun",
                "memorize.prompt.confusion": "Qaysini {hanzi} bilan adashtirishingiz mumkin?",
                "memorize.complete.meaning": "ma'no",
                "memorize.complete.word": "so'z",
                "memorize.complete.sentence": "gap",
                "memorize.finish": "Tugatish",
                "memorize.returnToExercises": "Mashqlarga qaytish",
                "practice.dataNotLoaded": "Ma'lumot yuklanmadi",
            },
            "ru": {
                "listen": "Послушать",
                "memorize.prompt.remember": "Для запоминания",
                "memorize.prompt.confusion": "Что можно спутать с {hanzi}?",
                "memorize.complete.meaning": "значение",
                "memorize.complete.word": "слово",
                "memorize.complete.sentence": "предложение",
                "memorize.finish": "Завершить",
                "memorize.returnToExercises": "К упражнениям",
                "practice.dataNotLoaded": "Не удалось загрузить данные",
            },
            "tj": {
                "listen": "Гӯш кардан",
                "memorize.prompt.remember": "Барои дар хотир мондан",
                "memorize.prompt.confusion": "Кадомро бо {hanzi} хато кардан мумкин?",
                "memorize.complete.meaning": "маъно",
                "memorize.complete.word": "калима",
                "memorize.complete.sentence": "ҷумла",
                "memorize.finish": "Анҷом",
                "memorize.returnToExercises": "Ба машқҳо",
                "practice.dataNotLoaded": "Маълумот бор нашуд",
            },
        }
        for locale, expected_messages in expected.items():
            messages = json.loads(
                (ROOT / f"localization/ui/{locale}/course.json").read_text(encoding="utf-8")
            )["messages"]
            with self.subTest(locale=locale):
                for key, value in expected_messages.items():
                    self.assertEqual(messages[key], value)
        self.assertEqual(review["migrated_keys"], [
            "listen", "memorize.prompt.remember", "memorize.prompt.confusion",
            "memorize.complete.meaning", "memorize.complete.word",
            "memorize.complete.sentence", "memorize.finish",
            "memorize.returnToExercises", "practice.dataNotLoaded",
        ])


if __name__ == "__main__":
    unittest.main()

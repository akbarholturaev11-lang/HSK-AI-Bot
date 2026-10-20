"""Lock the nine reviewed Mini App memorization inline locale expressions."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/static/course_v3_memorize.html"
REVIEW = ROOT / "localization/review/miniapp_memorize_inline_triage.json"
CALL = re.compile(r"\b(?:tr|t)\s*\(\s*\{\s*(?:uz|ru|tj)\s*:")


class MemorizationInlineLocaleTriageTests(unittest.TestCase):
    def test_all_current_inline_locale_calls_have_distinct_review_entries(self):
        source = SOURCE.read_text(encoding="utf-8")
        review = json.loads(REVIEW.read_text(encoding="utf-8"))
        occurrences = list(CALL.finditer(source))
        self.assertEqual(review["status"], "SOURCE_CLASSIFIED_INLINE_CALLS_NOT_RUNTIME_VALIDATION")
        self.assertEqual(review["source"], "app/static/course_v3_memorize.html")
        self.assertEqual(len(occurrences), 9)
        self.assertEqual(len(review["entries"]), len(occurrences))
        for i, (match, item) in enumerate(zip(occurrences, review["entries"]), start=1):
            with self.subTest(ordinal=i):
                self.assertEqual(item["ordinal"], i)
                self.assertEqual(item["line"], source.count("\n", 0, match.start()) + 1)
                self.assertIn(item["anchor"], source[match.start():match.start() + 185])
                self.assertTrue(item["recommendation"])
                self.assertTrue(item["category"])

    def test_dynamic_hanzi_prompt_is_not_static_localized_copy(self):
        source = SOURCE.read_text(encoding="utf-8")
        review = json.loads(REVIEW.read_text(encoding="utf-8"))
        dynamic = [item for item in review["entries"]
                   if item["category"] == "interpolated_hanzi_prompt"]
        self.assertEqual(len(dynamic), 1)
        index = dynamic[0]["ordinal"] - 1
        start = list(CALL.finditer(source))[index].start()
        expression = source[start:start + 250]
        self.assertEqual(expression.count("+H+"), 3)
        self.assertIn("{hanzi}", dynamic[0]["recommendation"])
        self.assertEqual(len(review["entries"]) - len(dynamic), 8)


if __name__ == "__main__":
    unittest.main()

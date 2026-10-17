"""Source-only manual triage anchors for selected Mini App LANG branches."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TRIAGE = ROOT / "localization/review/miniapp_course_hotspot_triage.json"
SOURCE = ROOT / "app/static/course-v3.html"

COPY_CATEGORIES = {
    "accessibility_copy", "loading_copy", "navigation_copy", "formatted_copy",
    "profile_copy", "access_copy", "lesson_navigation_copy",
    "lesson_example_translation", "error_recovery_copy",
    "result_error_copy", "assessment_ui_copy", "quota_ui_copy",
    "time_formatting_copy", "cooldown_copy",
}
NONCOPY_CATEGORIES = {"locale_adapter", "locale_grammar", "tts_language_adapter"}


class CourseHotspotTriageTests(unittest.TestCase):
    def test_manually_reviewed_source_anchors_remain_current(self):
        triage = json.loads(TRIAGE.read_text(encoding="utf-8"))
        src = SOURCE.read_text(encoding="utf-8").splitlines()
        self.assertEqual(triage["status"], "PARTIAL_SOURCE_REVIEW_NOT_RUNTIME_VALIDATION")
        self.assertEqual(triage["source"], "app/static/course-v3.html")
        self.assertEqual(len(triage["classifications"]), 21)
        lines = set()
        categories = set()
        for item in triage["classifications"]:
            with self.subTest(line=item["line"], category=item["category"]):
                self.assertIsInstance(item["line"], int)
                self.assertTrue(1 <= item["line"] <= len(src))
                self.assertNotIn(item["line"], lines, "Duplicate manual source line")
                lines.add(item["line"])
                self.assertTrue(item["anchor"].strip())
                self.assertIn(item["anchor"], src[item["line"] - 1],
                              "Classification stale: re-review line before migration")
                self.assertEqual(item["review"], "source_classified_only")
                self.assertTrue(item["reason"].strip())
                self.assertIn(item["category"], COPY_CATEGORIES | NONCOPY_CATEGORIES)
                categories.add(item["category"])
        self.assertIn("locale_adapter", categories)
        self.assertIn("locale_grammar", categories)
        self.assertIn("tts_language_adapter", categories)
        self.assertIn("assessment_ui_copy", categories)

    def test_do_not_treat_all_locale_conditions_as_translation_literals(self):
        triage = json.loads(TRIAGE.read_text(encoding="utf-8"))
        by_category = {item["category"] for item in triage["classifications"]}
        self.assertTrue(NONCOPY_CATEGORIES <= by_category)
        self.assertIn("not 21 unique locale predicates", triage["counting_note"])
        self.assertIn("other branches and pages remain unreviewed", triage["coverage_note"])


if __name__ == "__main__":
    unittest.main()

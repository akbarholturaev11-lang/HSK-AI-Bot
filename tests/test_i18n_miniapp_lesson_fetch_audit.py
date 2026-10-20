"""P0 Mini App lesson loader: prefetch cannot become entitlement consumption."""
import json
from pathlib import Path
import unittest

from scripts.i18n_miniapp_lesson_fetch_audit import (
    PAGE, REGISTRY, ROOT, audit, audit_source, extract_calls,
)


class MiniAppLessonFetchIntentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / PAGE).read_text(encoding="utf-8")
        cls.registry = json.loads((ROOT / REGISTRY).read_text(encoding="utf-8"))

    def test_existing_six_distinct_direct_reads_are_classified(self):
        report = audit(ROOT)
        self.assertEqual(report["status"], "SOURCE_CALLS_CLASSIFIED_REVIEW_REQUIRED")
        self.assertEqual(report["classified_direct_calls"], 6)
        self.assertEqual(report["regression_failures"], [])
        expected = [
            "paywall_preview_prime",
            "audio_preload_before_continue",
            "background_nearby_prefetch",
            "skip_test_question_generation",
            "starter_foundation_content",
            "interactive_lesson_after_reservation",
        ]
        self.assertEqual([row["intent"] for row in report["calls"]], expected)
        self.assertTrue(all(row["cost_sensitive"] for row in report["calls"]))
        self.assertEqual(
            [row["line"] for row in report["calls"]],
            [2053, 2203, 3008, 3629, 3761, 4091],
        )

    def test_speculative_reads_are_not_the_reservation_flow(self):
        report = audit(ROOT)
        self.assertEqual(report["calls"][-1]["intent"],
                         "interactive_lesson_after_reservation")
        self.assertTrue(all(row["intent"] != "interactive_lesson_after_reservation"
                            for row in report["calls"][:-1]))
        self.assertIn("reserveLessonStart(l).then(function(){return loadLessonData(lv,l.n)}",
                      self.source)
        self.assertEqual(len(extract_calls(self.source)), 6)

    def test_added_background_fetch_requires_human_review(self):
        altered = self.source + '\nfunction unsafePrefetch(){loadLessonData("hsk3",50)}\n'
        report = audit_source(altered, self.registry)
        self.assertEqual(report["status"], "SOURCE_CONTRACT_REGRESSION")
        self.assertIn("unreviewed_or_missing_direct_read",
                      {row["issue"] for row in report["regression_failures"]})

    def test_interactive_access_order_change_blocks_migration(self):
        old = "reserveLessonStart(l).then(function(){return loadLessonData(lv,l.n)}"
        self.assertIn(old, self.source)
        changed = self.source.replace(old, "loadLessonData(lv,l.n)", 1)
        report = audit_source(changed, self.registry)
        self.assertIn("interactive_lesson_reservation_order_changed",
                      {row["issue"] for row in report["regression_failures"]})

    def test_shifted_source_line_requires_registry_review(self):
        shifted = "// New first line\n" + self.source
        report = audit_source(shifted, self.registry)
        self.assertIn("stale_or_unclassified_read",
                      {row["issue"] for row in report["regression_failures"]})

    def test_memory_resume_keys_need_manual_account_switch_qa(self):
        report = audit(ROOT)
        self.assertEqual(report["cache_scope"], {
            "memory_lesson_key_contains_identity": False,
            "resume_key_contains_identity": False,
            "mastery_key_contains_identity": True,
        })
        self.assertTrue(any(row["issue"] ==
                            "shared_page_lesson_cache_and_resume_identity_scope_requires_QA"
                            for row in report["review_findings"]))
        self.assertNotIn("correct_index", json.dumps(report))


if __name__ == "__main__":
    unittest.main()

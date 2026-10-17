"""Local-first P0 review queue: never confuse candidates with proven defects."""
import unittest

from scripts.i18n_review_queue import build_review_queue, provisional_area


class ReviewQueueTests(unittest.TestCase):
    def test_owner_classifies_admin_separately_from_learner_messages(self):
        self.assertEqual(provisional_area("app/bot/handlers/account_deletion.py",
                                          "bot_backend"), "learner_messaging")
        self.assertEqual(provisional_area("app/bot/handlers/admin.py",
                                          "bot_backend"), "admin_or_operator")
        self.assertEqual(provisional_area("app/static/course-v3.html",
                                          "miniapp_ui"), "learner_frontend")
        self.assertEqual(provisional_area("app/static/admin.html",
                                          "miniapp_ui"), "admin_or_operator")
        self.assertEqual(provisional_area("scripts/gen_course_v3_from_seed.py",
                                          "generators"), "content_producer")

    def test_ranked_queue_is_bounded_and_preserves_counts(self):
        report = {"schema_version": 2, "scope": "heuristic", "files": [
            {"path": "app/static/course-v3.html", "group": "miniapp_ui",
             "candidate_literals": 20, "missing_locale_maps": 0,
             "samples": [{"kind": "inline", "sample": "Kurs"}]},
            {"path": "app/bot/handlers/account_deletion.py", "group": "bot_backend",
             "candidate_literals": 7},
            {"path": "app/bot/handlers/admin.py", "group": "bot_backend",
             "candidate_literals": 50},
            {"path": "app/static/course_v3_data/hsk1/lesson_01.json",
             "group": "lesson_content", "candidate_literals": 0, "localized_maps": 20},
            {"path": "android/app/src/main/res/values/strings.xml",
             "group": "android_ui", "candidate_literals": 0},
        ]}
        out = build_review_queue(report, max_files=2)
        self.assertEqual(out["candidate_literals"], 77)
        self.assertEqual(out["scanned_files"], 5)
        self.assertEqual(out["ranked_source_files"], 3)
        self.assertEqual(out["displayed_files"], 2)
        self.assertEqual(out["queue"][0]["path"], "app/static/course-v3.html")
        self.assertEqual(out["queue"][1]["path"], "app/bot/handlers/account_deletion.py")
        self.assertTrue(all(x["manual_review"] == "unreviewed" for x in out["queue"]))
        self.assertEqual(out["areas"]["admin_or_operator"]["candidate_literals"], 50)

    def test_detects_placeholder_mismatch_even_without_literals(self):
        report = {"schema_version": 2, "files": [
            {"path": "app/static/course_v3_data/hsk1/lesson_01.json",
             "group": "lesson_content", "placeholder_mismatches": 1}
        ]}
        out = build_review_queue(report)
        self.assertEqual(out["queue"][0]["priority"], "P1")
        self.assertEqual(out["queue"][0]["placeholder_mismatches"], 1)

    def test_refuses_duplicate_files_and_invalid_schema(self):
        rows = [{"path": "x", "group": "miniapp_ui", "candidate_literals": 2}]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_review_queue({"schema_version": 2, "files": rows * 2})
        with self.assertRaisesRegex(ValueError, "schema_version"):
            build_review_queue({"schema_version": 1, "files": rows})
        with self.assertRaisesRegex(ValueError, "max_files"):
            build_review_queue({"schema_version": 2, "files": rows}, max_files=0)


if __name__ == "__main__":
    unittest.main()

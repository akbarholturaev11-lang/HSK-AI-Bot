"""No-regression source checks for the first common UI runtime adoption.

Source-only guard; actual WebView/Android/desktop visual QA is deferred until
all localization code is implemented and a controlled test cycle begins.
"""
import json
from pathlib import Path
import unittest

from scripts.i18n_baseline_guard import git_blob_sha1

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "localization/baselines/reviewed_ui_changes.json"


class ReviewedCommonUIAdoptionTests(unittest.TestCase):
    def test_exact_approved_original_and_new_ui_blobs(self):
        approved = json.loads(REVIEW.read_text(encoding="utf-8"))
        baseline = json.loads((ROOT / "localization/baselines/source_git_blobs.json")
                              .read_text(encoding="utf-8"))
        self.assertEqual(set(approved["files"]), {
            "desktop/ui/js/i18n.js", "app/static/course-v3.html",
        })
        self.assertEqual(approved["baseline_main_commit"],
                         baseline["baseline_main_commit"])
        old_by_path = {
            entry["path"]: entry["git_blob_sha1"]
            for group in baseline["sources"].values() for entry in group
        }
        for name, note in approved["files"].items():
            with self.subTest(path=name):
                self.assertEqual(note["baseline_sha1"], old_by_path[name])
                self.assertEqual(note["reviewed_sha1"],
                                 git_blob_sha1((ROOT / name).read_bytes()))
                self.assertNotEqual(note["reviewed_sha1"],
                                    note["baseline_sha1"])
                self.assertTrue(note["reason"])

    def test_desktop_adopts_generated_values_but_keeps_old_fallback(self):
        source = (ROOT / "desktop/ui/js/i18n.js").read_text(encoding="utf-8")
        self.assertIn('import "./generated/hsk-common-i18n.js";', source)
        self.assertIn("const SHARED_COMMON_KEY = Object.freeze({", source)
        self.assertIn("window.HSKAI_COMMON_I18N", source)
        self.assertIn("const template = generated ??", source)
        self.assertIn("messages[activeLanguage]?.[key] ?? messages.uz[key]", source)
        for key in ["course", "practice", "profile", "rating",
                    "subscription", "startLesson", "continueLesson",
                    "lockedLesson", "courseEmpty", "refresh", "authExpires"]:
            self.assertIn(key + ":", source)
        self.assertNotIn("/api/i18n/", source)

    def test_miniapp_loads_only_static_local_ui_bundle(self):
        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertIn(
            '<script src="/course_v3_data/hsk-common-i18n.js?v=20261017-common-v1"></script>',
            html,
        )
        self.assertLess(html.index("hsk-common-i18n.js"),
                        html.index("function commonMessage("))
        self.assertIn("window.HSKAI_COMMON_I18N", html)
        self.assertIn('commonMessage("navigation.rating",', html)
        self.assertIn('LANG==="ru"?"Рейтинг":LANG==="tj"?"Рейтинг":"Reyting"', html)
        self.assertNotIn('fetch("/api/i18n/', html)

    def test_platform_bundles_contain_only_ui_not_lessons_or_entitlements(self):
        for file in (
            "desktop/ui/js/generated/hsk-common-i18n.js",
            "app/static/course_v3_data/hsk-common-i18n.js",
        ):
            text = (ROOT / file).read_text(encoding="utf-8")
            self.assertNotIn("correct_index", text)
            self.assertNotIn("answer_key", text)
            self.assertNotIn("/course_v3_data/hsk1/lesson_", text)
            self.assertNotIn("fetch(", text)
            self.assertNotIn("BOT_TOKEN", text)


if __name__ == "__main__":
    unittest.main()

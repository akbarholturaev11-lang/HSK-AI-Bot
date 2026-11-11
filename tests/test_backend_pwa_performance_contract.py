"""Regression tests for the permanent Backend/PWA CI policy guard."""
import tempfile
import unittest
from pathlib import Path

from scripts.check_backend_pwa_performance_contract import (
    change_issues, is_backend_source, is_pwa_source, policy_issues,
)


class PerformanceContractGuardTests(unittest.TestCase):
    def test_backend_change_requires_test(self):
        self.assertEqual(len(change_issues(["app/api/new_feature.py"])), 1)
        self.assertEqual(change_issues([
            "app/api/new_feature.py", "tests/test_new_feature.py"
        ]), [])

    def test_pwa_change_requires_relevant_browser_or_ui_test(self):
        self.assertEqual(len(change_issues(["app/static/new-section.html"])), 1)
        self.assertEqual(len(change_issues([
            "app/static/new-section.html", "tests/test_random_model.py"
        ])), 1)
        self.assertEqual(change_issues([
            "app/static/new-section.html", "tests/e2e/test_new_section.py"
        ]), [])

    def test_backend_and_pwa_changes_need_both_regressions(self):
        self.assertEqual(len(change_issues([
            "app/api/pwa_auth.py", "app/static/course-v3.html",
            "tests/test_course_map_policy.py",
        ])), 1)
        self.assertEqual(change_issues([
            "app/api/pwa_auth.py", "app/static/course-v3.html",
            "tests/test_course_map_policy.py",
            "tests/e2e/test_pwa_initial_shell.py",
        ]), [])

    def test_android_native_not_gated(self):
        self.assertFalse(is_backend_source("android/app/Example.kt"))
        self.assertFalse(is_pwa_source("android/app/Example.kt"))
        self.assertEqual(change_issues(["android/app/Example.kt"]), [])

    def test_permanent_policy_links_and_sections(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            doc = root / "docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md"
            doc.parent.mkdir()
            doc.write_text("No acceptance conditions", encoding="utf-8")
            (root / "AGENTS.md").write_text("No linked policy", encoding="utf-8")
            (root / "AI_RULES.md").write_text("No linked policy", encoding="utf-8")
            self.assertTrue(policy_issues(root))

    def test_real_repository_contract(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(policy_issues(root), [])


if __name__ == "__main__":
    unittest.main()

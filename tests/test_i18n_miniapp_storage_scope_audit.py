"""Read-only source regression of identity-scoped Mini App/WebView state."""
import json
from pathlib import Path
import unittest

from scripts.i18n_miniapp_storage_scope_audit import (
    REGISTRY, ROOT, audit, audit_source,
)


class MiniAppStorageScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((ROOT / REGISTRY).read_text(encoding="utf-8"))
        cls.sources = {
            alias: (ROOT / path).read_text(encoding="utf-8")
            for alias, path in cls.registry["sources"].items()
        }

    def test_current_key_classification_is_complete_for_literal_calls(self):
        report = audit()
        self.assertEqual(report["status"], "SOURCE_REVIEW_PENDING_ACCOUNT_SWITCH_QA")
        self.assertEqual(report["classified_literal_keys"], 11)
        self.assertEqual(report["literal_storage_calls"], 22)
        self.assertEqual(report["regressions"], [])
        self.assertEqual(set(report["dynamic_cache_key_functions"]), {
            "lessonDataKey", "lessonResumeKey", "lessonMasteryKey",
            "foundationCacheKey", "studySetupTimeKey",
        })

    def test_identity_contrasts_are_preserved_and_flagged_for_qa(self):
        report = audit()
        keys = report["dynamic_cache_key_functions"]
        self.assertFalse(keys["lessonDataKey"]["local_user_scope_called"])
        self.assertFalse(keys["lessonResumeKey"]["local_user_scope_called"])
        self.assertTrue(keys["lessonMasteryKey"]["local_user_scope_called"])
        self.assertTrue(keys["foundationCacheKey"]["local_user_scope_called"])
        self.assertFalse(keys["studySetupTimeKey"]["local_user_scope_called"])
        self.assertEqual({r["id"] for r in report["risks"]}, {
            "unscoped_memorization_mastery", "unscoped_lesson_resume",
            "in_memory_lesson_data_no_identity", "unverified_user_scope_source",
        })

    def test_new_storage_key_requires_classification(self):
        source = dict(self.sources)
        source["course"] += '\nlocalStorage.setItem("new_personal_test_data", "SECRET_SAMPLE");\n'
        report = audit_source(source, self.registry)
        self.assertEqual(report["status"], "REGRESSION")
        self.assertTrue(any(x["kind"] == "new_or_extra_storage_access"
                            and x["key"] == "new_personal_test_data"
                            for x in report["regressions"]))
        self.assertNotIn("SECRET_SAMPLE", json.dumps(report))

    def test_removing_mastery_identity_scope_is_a_regression(self):
        source = dict(self.sources)
        snippet = (
            'function lessonMasteryKey(level,lessonOrder){return"hsk_v3_mastery:v"+'
            'MASTERY_VERSION+":"+localUserScope()+":"'
        )
        self.assertIn(snippet, source["course"])
        source["course"] = source["course"].replace(
            snippet, snippet.replace('localUserScope()+":"', '"shared"+":"'), 1
        )
        report = audit_source(source, self.registry)
        self.assertEqual(report["status"], "REGRESSION")
        self.assertIn("mastery_identity_scope_missing",
                      {r["kind"] for r in report["regressions"]})

    def test_literal_memorization_mastery_change_requires_review(self):
        source = dict(self.sources)
        self.assertIn('localStorage.getItem("hsk_memo")', source["memorize"])
        source["memorize"] = source["memorize"].replace(
            'localStorage.getItem("hsk_memo")',
            'localStorage.getItem("hsk_memo_account_new")', 1,
        )
        report = audit_source(source, self.registry)
        self.assertTrue(any(r["kind"] == "memorize_mastery_storage_changed"
                            for r in report["regressions"]))
        self.assertEqual(report["status"], "REGRESSION")


if __name__ == "__main__":
    unittest.main()

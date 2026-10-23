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
        self.assertEqual(report["status"], "SOURCE_IDENTITY_SCOPE_RUNTIME_QA_REQUIRED")
        self.assertEqual(report["classified_literal_keys"], 10)
        self.assertEqual(report["literal_storage_calls"], 20)
        self.assertEqual(report["regressions"], [])
        self.assertEqual(set(report["dynamic_cache_key_functions"]), {
            "lessonDataKey", "lessonResumeKey", "lessonMasteryKey",
            "foundationCacheKey", "studySetupTimeKey", "memorizationStateKey",
        })

    def test_identity_contrasts_are_preserved_and_flagged_for_qa(self):
        report = audit()
        keys = report["dynamic_cache_key_functions"]
        self.assertTrue(keys["lessonDataKey"]["local_user_scope_called"])
        self.assertTrue(keys["lessonResumeKey"]["local_user_scope_called"])
        self.assertTrue(keys["lessonMasteryKey"]["local_user_scope_called"])
        self.assertTrue(keys["foundationCacheKey"]["local_user_scope_called"])
        self.assertFalse(keys["studySetupTimeKey"]["local_user_scope_called"])
        self.assertTrue(keys["memorizationStateKey"]["local_user_scope_called"])
        self.assertIn('if(u&&u.id)return String(u.id)', self.sources["course"])
        self.assertIn('if(u&&u.id)return String(u.id)', self.sources["memorize"])
        self.assertIn('scope==="preview"?legacy:"hsk_v3_lesson_resume:v3:"+scope',
                      self.sources["course"])
        self.assertIn('scope==="preview"?"hsk_memo":"hsk_memo:v2:"+scope',
                      self.sources["memorize"])
        self.assertEqual({r["id"] for r in report["risks"]}, {
            "unverified_user_scope_source",
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

    def test_memorization_mastery_key_requires_account_scope(self):
        source = dict(self.sources)
        self.assertIn('function memorizationStateKey(){var scope=localUserScope()',
                      source["memorize"])
        source["memorize"] = source["memorize"].replace(
            'function memorizationStateKey(){var scope=localUserScope()',
            'function memorizationStateKey(){var scope="shared"', 1,
        )
        report = audit_source(source, self.registry)
        self.assertTrue(any(r["kind"] == "memorization_identity_scope_missing"
                            for r in report["regressions"]))
        self.assertEqual(report["status"], "REGRESSION")


if __name__ == "__main__":
    unittest.main()

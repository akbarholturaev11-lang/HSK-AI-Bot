"""Regression checks for Bot/Desktop local-first P0 source inventory."""
import unittest

from scripts.i18n_catalog_contract_audit import (
    ROOT, audit, bot_catalogs, comparison, desktop_catalogs, fallback_review,
    python_tables, signature,
)


class CatalogAuditTests(unittest.TestCase):
    def test_key_and_placeholder_drift_are_classified_without_string_dump(self):
        m = {
            "uz": {"greet": "Salom {name}", "only_uz": "x"},
            "ru": {"greet": "Привет {user}"},
            "tj": {"greet": "Салом {name}"},
        }
        found = comparison(m, source="fixture", table="messages")
        self.assertEqual(found["missing_keys"], [{"key": "only_uz", "absent": ["ru", "tj"]}])
        self.assertEqual([v["key"] for v in found["placeholder_drift"]], ["greet"])
        self.assertNotIn("Привет", str(found))

    def test_bot_merges_and_overrides_without_importing_module(self):
        source = '''
TEXTS = {"uz":{"k":"{name}","old":"x"},"ru":{"k":"{name}","old":"y"},"tj":{"k":"{name}","old":"z"}}
COURSE_I18N = {"uz":{"lesson":"a"},"ru":{"lesson":"b"},"tj":{"lesson":"c"}}
BONUS_I18N = {"uz":{"k":"{name}"},"ru":{"k":"{name}"},"tj":{"k":"{name}"}}
for _lang, _texts in BONUS_I18N.items():
    TEXTS.setdefault(_lang, {}).update(_texts)
'''
        res = bot_catalogs(source)
        self.assertEqual(len(res["tables"]), 3)
        self.assertEqual(len(res["detected_merges"]), 1)
        self.assertEqual(len(res["overrides"]), 3)
        self.assertEqual(res["unrecognized_merges"], [])

    def test_duplicate_python_dict_keys_are_reported(self):
        source = '''
TEXTS={"uz":{"k":"a","k":"b"},"ru":{"k":"a"},"tj":{"k":"a"}}
COURSE_I18N={"uz":{},"ru":{},"tj":{}}
'''
        _, dupes = python_tables(source)
        self.assertEqual(dupes, [{"table": "TEXTS", "locale": "uz", "key": "k"}])

    def test_desktop_multiline_values_and_missing_key(self):
        source = '''const messages = {
  uz: {
    message: "Hello {name}",
    multiline:
      "Two lines {count}",
  },
  ru: {
    message: "Привет {name}",
    multiline: "Строки {count}",
  },
  tj: {
    message: "Салом {name}",
  },
};
'''
        result = desktop_catalogs(source)["comparison"]
        self.assertEqual(result["missing_keys"], [{"key": "multiline", "absent": ["tj"]}])
        self.assertEqual(result["placeholder_drift"], [])

    def test_signature_does_not_count_escaped_double_braces(self):
        self.assertEqual(signature("{{name}} {name} {count}"), [("count", 1), ("name", 1)])

    def test_fallback_review_identifies_source_policy_conflict(self):
        source = {
            "miniapp_course": (
                'var LANG=(new URLSearchParams(location.search).get("lang")||"ru");'
                'if(d&&d.user&&d.user.language&&I18N[d.user.language])LANG=d.user.language'
            ),
            "miniapp_subscription": 'function normalizeLang(value){return "uz";}',
            "desktop": 'return SUPPORTED_LANGUAGES.has(normalized) ? normalized : "uz";',
            "bot": 'def t(key: str, lang: str = "ru", **kwargs): pass',
            "android": 'val DEFAULT = RUSSIAN',
        }
        result = fallback_review(source, {"default_locale": "uz"})
        self.assertTrue(result["inconsistent_defaults"])
        self.assertEqual(result["observed_defaults"]["miniapp_course"], "ru")
        self.assertEqual(result["observed_defaults"]["android"], "ru")
        self.assertTrue(result["miniapp_course_account_language_override"])
        with self.assertRaisesRegex(ValueError, "source changed"):
            fallback_review({**source, "miniapp_course": ""}, {"default_locale": "uz"})

    def test_real_three_locale_sources_have_parity_without_runtime_import(self):
        result = audit(ROOT)
        self.assertEqual(result["desktop"]["comparison"]["key_counts"],
                         {"uz": 828, "ru": 828, "tj": 828})
        for report in result["bot"]["tables"] + result["bot"]["effective"] + [
                result["desktop"]["comparison"]]:
            self.assertEqual(report["missing_keys"], [], report["table"])
            self.assertEqual(report["placeholder_drift"], [], report["table"])
            self.assertEqual(report["html_tag_count_drift"], [], report["table"])
        self.assertEqual(result["bot"]["duplicate_literal_keys"], [])
        self.assertEqual(result["bot"]["unrecognized_merges"], [])
        self.assertTrue(result["fallback_review"]["inconsistent_defaults"])

    def test_rejects_changed_desktop_language_structure(self):
        with self.assertRaisesRegex(ValueError, "sections changed"):
            desktop_catalogs("const messages = {uz:{a:'a'}};")


if __name__ == "__main__":
    unittest.main()

"""Exact subscription UI-only local-first catalog and runtime fallback contracts."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ("uz", "ru", "tj")


def subscription_source():
    return (ROOT / "app/static/subscription.html").read_text(encoding="utf-8")


def legacy_messages(source):
    raw = source.split("const I18N=", 1)[1].split(
        "};var SUBSCRIPTION_UI=", 1
    )[0] + "}"
    return json.loads(re.sub(
        r"([{,]\s*)([A-Za-z_$][A-Za-z0-9_$]*)(\s*:)",
        r'\1"\2"\3', raw,
    ))


class SubscriptionUIAdoptionTests(unittest.TestCase):
    def test_102_exact_strings_from_each_original_locale(self):
        source = subscription_source()
        original = legacy_messages(source)
        self.assertEqual(set(original), set(LOCALES))
        for locale in LOCALES:
            with self.subTest(locale=locale):
                inline = original[locale]
                scalar = {key: value for key, value in inline.items()
                          if isinstance(value, str)}
                self.assertEqual(len(scalar), 109)
                catalog = json.loads(
                    (ROOT / f"localization/ui/{locale}/course.json").read_text(encoding="utf-8")
                )["messages"]
                self.assertEqual(len(catalog), 815)
                for key, value in scalar.items():
                    self.assertEqual(catalog["subscriptionPage." + key], value)

    def test_preload_and_entitlement_logic_boundaries(self):
        source = subscription_source()
        self.assertLess(source.index("hsk-course-i18n.js?v=20261020-37c75ec39f2a"),
                        source.index("const I18N={"))
        self.assertIn('local["subscriptionPage."+key]', source)
        self.assertIn('if(typeof value==="string"&&value)I18N[locale][key]=value', source)
        for marker in (
            "const HSK30_UNLOCK_MODE=",
            "const state={",
            "function tr(){return I18N[state.lang]||I18N.uz}",
            "const I18N={",
            "const API=",
        ):
            self.assertIn(marker, source)
        self.assertEqual(source.count("const I18N={"), 1)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_node_executes_overlay_fallback_across_all_locales(self):
        source = subscription_source()
        inline = legacy_messages(source)
        script = "const I18N=" + source.split("const I18N=", 1)[1].split(
            "\n\nconst HSK30_UNLOCK_MODE=", 1
        )[0]
        node_script = r"""
const fs=require("fs");
const arg=JSON.parse(fs.readFileSync(0,"utf8"));
const factory=new Function("window",arg.script+"\nreturn I18N;");
const fallback=factory({});
const hydrated=factory({HSKAI_COURSE_I18N:arg.overrides});
process.stdout.write(JSON.stringify({fallback,hydrated}));
"""
        overrides = {
            locale: {
                "subscriptionPage.title": "QA TITLE " + locale,
                "subscriptionPage.renewalCurrent": "QA {date}",
                "subscriptionPage.loading": "",
            }
            for locale in LOCALES
        }
        completed = subprocess.run(
            ["node", "-e", node_script],
            input=json.dumps({"script": script, "overrides": overrides}),
            text=True, capture_output=True, timeout=20, check=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["fallback"], inline)
        expected = json.loads(json.dumps(inline))
        for locale in LOCALES:
            expected[locale]["title"] = "QA TITLE " + locale
            expected[locale]["renewalCurrent"] = "QA {date}"
        self.assertEqual(result["hydrated"], expected)


if __name__ == "__main__":
    unittest.main()

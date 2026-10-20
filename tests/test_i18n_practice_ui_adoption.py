"""Exact source parity and executable fallback for Mistakes and Pronunciation UI copy."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = {"mistakes": 53, "pronunciation": 22}
LOCALES = ("uz", "ru", "tj")


def inline_source(page):
    source = (ROOT / f"app/static/course_v3_{page}.html").read_text(encoding="utf-8")
    fragment = source.split("var L=", 1)[1].split("[LANG];", 1)[0]
    quoted = re.sub(r"([{,]\s*)([A-Za-z_]\w*)(\s*:)", r'\1"\2"\3', fragment)
    return source, json.loads(quoted)


def flatten(obj, prefix=""):
    result = {}
    for key, value in obj.items():
        if isinstance(value, str):
            result[prefix + key] = value
        else:
            if not isinstance(value, dict):
                raise AssertionError("Unexpected non-display localization value")
            result.update(flatten(value, prefix + key + "."))
    return result


class PracticeUIAdoptionTests(unittest.TestCase):
    def test_75_exact_original_labels_in_all_three_locales(self):
        for page, count in PAGES.items():
            source, original = inline_source(page)
            self.assertEqual(set(original), set(LOCALES))
            for locale in LOCALES:
                with self.subTest(page=page, locale=locale):
                    old = flatten(original[locale])
                    catalog = json.loads(
                        (ROOT / f"localization/ui/{locale}/course.json").read_text(encoding="utf-8")
                    )["messages"]
                    self.assertEqual(len(old), count)
                    self.assertEqual(len(catalog), 875)
                    for key, label in old.items():
                        self.assertEqual(catalog[f"{'mistakesPage' if page == 'mistakes' else page}.{key}"], label)
            self.assertLess(source.index("hsk-course-i18n.js?v=20261020-7eba899ffe2f"),
                            source.index("var L={"))
            self.assertEqual(source.count("var L={"), 1)

    def test_no_gate_or_practice_logic_rewritten(self):
        mistakes, _ = inline_source("mistakes")
        pronunciation, _ = inline_source("pronunciation")
        for marker in (
            "function validateQuestionContract(q){",
            "function startReview(adSupported){",
            "function submitBuilder(){",
            "function pickOption(i){",
            "function finishReview(){",
            '"/api/miniapp/mistakes/review/answer"',
        ):
            self.assertIn(marker, mistakes)
        for marker in (
            "function validatePracticeGate(o){",
            "function runGate(ref){",
            "function reportResults(){",
            "function applyScore(score,heard){",
            "function onStopped(){",
            '"/api/voice-practice/pronounce"',
        ):
            self.assertIn(marker, pronunciation)
        self.assertIn('MISTAKES_UI["mistakesPage."+key]', mistakes)
        self.assertIn('mistakesUILookup(key+"."+subkey,L[key][subkey])', mistakes)
        self.assertIn('PRONUNCIATION_UI["pronunciation."+key]', pronunciation)
        self.assertIn('if(typeof v==="string"&&v)L[key]=v', pronunciation)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_runtime_override_and_offline_fallback(self):
        # Execute only the unchanged inline L dictionary and new hydration;
        # no DOM, network, Telegram or production APIs are invoked.
        node = r"""
const fs=require("fs");
const data=JSON.parse(fs.readFileSync(0,"utf8"));
const fn=new Function("LANG","window",data.script+"\nreturn L;");
const execute=(catalog)=>fn(data.locale,{HSKAI_COURSE_I18N:catalog});
process.stdout.write(JSON.stringify({
  fallback:execute(undefined),
  hydrated:execute({[data.locale]:data.overrides})
}));
"""
        for page in PAGES:
            html, original = inline_source(page)
            snippet = html.split("var L=", 1)[1].split("\nvar tg=", 1)[0]
            script = "var L=" + snippet
            for locale in LOCALES:
                with self.subTest(page=page, locale=locale):
                    patch = (
                        {"mistakesPage.title": "QA TITLE", "mistakesPage.cats.word": "QA CATEGORY",
                         "mistakesPage.sources.lesson": "QA SOURCE", "mistakesPage.reviewSub": ""}
                        if page == "mistakes" else
                        {"pronunciation.review": "QA REVIEW", "pronunciation.listen": "QA LISTEN",
                         "pronunciation.hint": ""}
                    )
                    output = subprocess.run(
                        ["node", "-e", node],
                        input=json.dumps({"locale": locale, "script": script, "overrides": patch}),
                        text=True, capture_output=True, check=True, timeout=15,
                    )
                    actual = json.loads(output.stdout)
                    self.assertEqual(actual["fallback"], original[locale])
                    expected = json.loads(json.dumps(original[locale]))
                    if page == "mistakes":
                        expected["title"] = "QA TITLE"
                        expected["cats"]["word"] = "QA CATEGORY"
                        expected["sources"]["lesson"] = "QA SOURCE"
                    else:
                        expected["review"] = "QA REVIEW"
                        expected["listen"] = "QA LISTEN"
                    self.assertEqual(actual["hydrated"], expected)


if __name__ == "__main__":
    unittest.main()

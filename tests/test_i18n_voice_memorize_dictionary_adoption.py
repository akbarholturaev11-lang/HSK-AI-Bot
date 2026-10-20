"""Exact UZ/RU/TJ UI-copy adoption in Voice, Memorize and Dictionary, offline-first."""
import ast
import copy
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ("uz", "ru", "tj")
VERSION = "hsk-course-i18n.js?v=20261020-779fc95f8460"
DICTIONARY_VERSION = "hsk-course-i18n.js?v=20261020-779fc95f8460"
KEY_RE = re.compile(r"([{,]\s*)([A-Za-z_]\w*)(\s*:)")


def literal_object(fragment):
    """Parse only the literal UI dictionaries, never execute source or lesson code."""
    return ast.literal_eval(KEY_RE.sub(r'\1"\2"\3', fragment))


def get_pages():
    paths = {
        "voice": "app/static/course_v3_voice.html",
        "memorize": "app/static/course_v3_memorize.html",
        "dictionary": "app/static/hsk-lugat.html",
    }
    return {
        key: (ROOT / path).read_text(encoding="utf-8")
        for key, path in paths.items()
    }


def original_labels(pages):
    voice = literal_object(pages["voice"].split("var L=", 1)[1].split("[LANG];", 1)[0])
    limit = literal_object(pages["memorize"].split("var LIM=", 1)[1].split(";\n", 1)[0])
    dictionary = {}
    for name in ("practiceLabels", "memoLabels"):
        value = pages["dictionary"].split("  var " + name + " = ", 1)[1].split(";\n", 1)[0]
        dictionary[name] = literal_object(value)
    return voice, limit, dictionary


def snippet(page, source):
    if page == "voice":
        return "var L=" + source.split("var L=", 1)[1].split("\nvar tg=", 1)[0]
    if page == "memorize":
        return "var LIM=" + source.split("var LIM=", 1)[1].split("\nfunction goPremium()", 1)[0]
    return ("var practiceLabels = "
            + source.split("  var practiceLabels = ", 1)[1]
                    .split("\n  function normalizeLang(value)", 1)[0])


class VoiceMemorizeDictionaryUIAdoptionTests(unittest.TestCase):
    def test_exact_65_original_labels_across_three_locales(self):
        pages = get_pages()
        voice, limit, dictionary = original_labels(pages)
        self.assertEqual(set(voice), set(LOCALES))
        self.assertEqual(len(limit), 4)
        for locale in LOCALES:
            with self.subTest(locale=locale):
                self.assertEqual(len(voice[locale]), 47)
                self.assertEqual(len(dictionary["practiceLabels"][locale]), 7)
                self.assertEqual(len(dictionary["memoLabels"][locale]), 7)
                messages = json.loads(
                    (ROOT / f"localization/ui/{locale}/course.json").read_text(encoding="utf-8")
                )["messages"]
                self.assertEqual(len(messages), 892)
                for key, value in voice[locale].items():
                    self.assertEqual(messages["voicePage." + key], value)
                for key, labels in limit.items():
                    self.assertEqual(messages["memorizeLimit." + key], labels[locale])
                for key, value in dictionary["practiceLabels"][locale].items():
                    self.assertEqual(messages["dictionaryPractice." + key], value)
                for key, value in dictionary["memoLabels"][locale].items():
                    self.assertEqual(messages["dictionaryMemo." + key], value)

    def test_single_preloaded_static_bundle_with_original_fallback(self):
        pages = get_pages()
        for page, source in pages.items():
            with self.subTest(page=page):
                version = DICTIONARY_VERSION if page == "dictionary" else VERSION
                self.assertEqual(source.count(version), 1)
                before = ("var L=" if page == "voice" else
                          "var LIM=" if page == "memorize" else
                          "  var practiceLabels = ")
                self.assertLess(source.index(version), source.index(before))
        self.assertIn('VOICE_PAGE_UI["voicePage."+key]', pages["voice"])
        self.assertIn('if(typeof value==="string"&&value)L[key]=value', pages["voice"])
        self.assertIn('MEMORIZE_LIMIT_UI["memorizeLimit."+key]', pages["memorize"])
        self.assertIn('if(typeof value==="string"&&value)LIM[key][LANG]=value', pages["memorize"])
        self.assertIn('source["dictionaryPractice."+key]', pages["dictionary"])
        self.assertIn('source["dictionaryMemo."+key]', pages["dictionary"])

    def test_core_voice_practice_and_dictionary_paths_unchanged(self):
        pages = get_pages()
        for marker in (
            "function startSession(){",
            "function startRecording(){",
            "function sendText(){",
            "function softReset(){",
            '"/api/voice-practice/session/start"',
            '"/api/voice-practice/message"',
        ):
            self.assertIn(marker, pages["voice"])
        for marker in (
            "function validatePracticeGate(o){",
            "function runGate(ref){",
            "function startChar(){",
            '"/api/v3/practice/daily-gate"',
        ):
            self.assertIn(marker, pages["memorize"])
        for marker in (
            "function normalizeLevel(value){",
            "function normalizeFilterLevel(value){",
            "var pl = practiceLabels[currentLang] || practiceLabels.uz;",
            "var L = memoLabels[currentLang] || memoLabels.uz;",
        ):
            self.assertIn(marker, pages["dictionary"])

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_client_runtime_missing_bundle_and_qualified_override(self):
        pages = get_pages()
        voice, limit, dictionary = original_labels(pages)
        js = r"""
const fs = require("fs");
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const returns = {
    voice: "L",
    memorize: "LIM",
    dictionary: "{practiceLabels, memoLabels}"
};
const out = {};
for (const locale of ["uz", "ru", "tj"]) {
  const run = (bundle) => {
    const scope = { HSKAI_COURSE_I18N: bundle };
    return new Function("LANG", "window",
        input.script + "\nreturn " + returns[input.page] + ";")(locale, scope);
  };
  out[locale] = {
    fallback: run(undefined),
    changed: run({ [locale]: input.patches[locale] })
  };
}
process.stdout.write(JSON.stringify(out));
"""
        for page, source in pages.items():
            with self.subTest(page=page):
                patches = {
                    locale: ({
                        "voicePage.speaking": "QA SPEAKING",
                        "voicePage.listening": "",
                    } if page == "voice" else {
                        "memorizeLimit.title": "QA LIMIT",
                        "memorizeLimit.sub": "",
                    } if page == "memorize" else {
                        "dictionaryPractice.head": "QA PRACTICE",
                        "dictionaryMemo.mano": "QA COMPONENT",
                        "dictionaryMemo.misol": "",
                    })
                    for locale in LOCALES
                }
                result = subprocess.run(
                    ["node", "-e", js],
                    input=json.dumps({
                        "page": page, "script": snippet(page, source), "patches": patches
                    }, ensure_ascii=False),
                    capture_output=True, text=True, check=True, timeout=15,
                )
                actual = json.loads(result.stdout)
                for locale in LOCALES:
                    with self.subTest(page=page, locale=locale):
                        if page == "voice":
                            original = voice[locale]
                            updated = dict(original, speaking="QA SPEAKING")
                        elif page == "memorize":
                            original = limit
                            updated = copy.deepcopy(original)
                            updated["title"][locale] = "QA LIMIT"
                        else:
                            original = dictionary
                            updated = copy.deepcopy(original)
                            updated["practiceLabels"][locale]["head"] = "QA PRACTICE"
                            updated["memoLabels"][locale]["mano"] = "QA COMPONENT"
                        self.assertEqual(actual[locale]["fallback"], original)
                        self.assertEqual(actual[locale]["changed"], updated)


if __name__ == "__main__":
    unittest.main()

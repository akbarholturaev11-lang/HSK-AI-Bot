"""Exact 63-label three-locale course Voice copy and offline overlay regression."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("uz", "ru", "tj")
MAIN_COUNT = 60
LIVE_COUNT = 3


def source_parts():
    html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
    voice = html.split("var VOICE=(function(){\nvar LD=", 1)[1]
    legacy = voice.split(";\nvar LIVE_TEXT=", 1)[0]
    live = voice.split("var LIVE_TEXT=", 1)[1].split(";\nObject.keys(LIVE_TEXT)", 1)[0]
    return html, legacy, live


def js_object_to_dict(source):
    return json.loads(re.sub(
        r"([{,]\s*)([A-Za-z]\w*)(\s*:)", r'\1"\2"\3', source
    ))


class CourseVoiceInlineAdoptionTests(unittest.TestCase):
    def test_all_exact_63_ui_labels_per_locale(self):
        html, main, live = source_parts()
        original, live_text = js_object_to_dict(main), js_object_to_dict(live)
        self.assertEqual(set(original), set(LANGUAGES))
        self.assertEqual(set(live_text), set(LANGUAGES))
        self.assertEqual(len(original["ru"]), MAIN_COUNT)
        self.assertEqual(len(live_text["ru"]), LIVE_COUNT)
        reviewed_keys = set(original["ru"]) | set(live_text["ru"])
        self.assertEqual(len(reviewed_keys), 63)
        for locale in LANGUAGES:
            catalog = json.loads(
                (ROOT / f"localization/ui/{locale}/course.json").read_text(encoding="utf-8")
            )["messages"]
            self.assertEqual(len(catalog), 894)
            self.assertEqual(set(original[locale]), set(original["ru"]))
            self.assertEqual(set(live_text[locale]), set(live_text["ru"]))
            for key, value in {**original[locale], **live_text[locale]}.items():
                with self.subTest(locale=locale, key=key):
                    self.assertEqual(catalog["courseVoiceInline." + key], value)
        self.assertEqual(
            (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8").count("\n") + 1,
            8859,
        )

    def test_preload_static_catalog_before_voice_and_keep_original_runtime(self):
        html, main, live = source_parts()
        self.assertLess(
            html.index("hsk-course-i18n.js?v=20261020-eaff685fb700"),
            html.index("var VOICE=(function(){"),
        )
        self.assertIn('messages["courseVoiceInline."+key]', html)
        self.assertIn('if(typeof value==="string"&&value)LD[locale][key]=value', html)
        self.assertIn("Object.keys(LIVE_TEXT).forEach(function(k){Object.assign(LD[k],LIVE_TEXT[k])});", html)
        self.assertIn("var L=LD[LANG]||LD.ru;", html)
        for marker in (
            "function subOn(){",
            "function applySub(){",
            "function toggleSub(){",
            "function slowOn(){",
            "function esc(s){",
        ):
            self.assertIn(marker, html)

    def test_embedded_practice_dictionaries_and_accessibility_use_shared_catalog(self):
        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        for marker in (
            'adoptCourseLocaleDictionary(LD,"recognition")',
            'adoptCourseLocaleDictionary(LD,"pronunciation")',
            'adoptCourseLocaleDictionary(LD,"mistakesPage")',
            'adoptCourseLocaleDictionary(LD,"testHub")',
            'adoptCourseLocaleDictionary(EMD,"testExam")',
            'adoptCourseLocaleDictionary(PTD,"testPlacement")',
            'prefix==="testExam"&&key==="sec"?"testExamSection"',
            'courseMessage("recognition.back",L().back)',
            'courseMessage("pronunciation.back",L().back)',
            'courseMessage("say",T().say)',
            'courseMessage("sheet.closeLabel",tr({ru:',
            'courseMessage("testHub.limBack",tr({ru:',
        ):
            self.assertIn(marker, html)
        self.assertEqual(
            (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8").count("\n") + 1,
            8859,
        )
        for locale in LANGUAGES:
            catalog = json.loads(
                (ROOT / f"localization/ui/{locale}/course.json").read_text(encoding="utf-8")
            )["messages"]
            for key in (
                "recognition.back", "pronunciation.back", "say", "onboarding.back",
                "sheet.closeLabel", "testHub.limBack", "testExam.tfTrue",
                "testExamSection.listening", "testPlacement.back", "mistakesPage.cats.word",
            ):
                with self.subTest(locale=locale, key=key):
                    self.assertTrue(catalog[key])

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_embedded_dictionary_hydration_keeps_fallback_and_routes_nested_keys(self):
        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        helper_line = next(line for line in html.splitlines()
                           if "function adoptCourseLocaleDictionary(" in line)
        helper = helper_line[helper_line.index("function adoptCourseLocaleDictionary("):]
        node = r"""
const fs=require("fs");
const input=JSON.parse(fs.readFileSync(0,"utf8"));
const fn=new Function("window","dictionaries","prefix",
  input.helper+";adoptCourseLocaleDictionary(dictionaries,prefix);return dictionaries;");
const dict={uz:{title:"old",cats:{word:"old nested",empty:"keep"},sec:{listening:"old sec"}},
  ru:{title:"old ru",cats:{word:"old ru nested"},sec:{listening:"old ru sec"}},
  tj:{title:"old tj",cats:{word:"old tj nested"},sec:{listening:"old tj sec"}}};
const catalog={uz:{"mistakesPage.title":"qa", "mistakesPage.cats.word":"qa nested",
    "mistakesPage.cats.empty":"", "mistakesPage.sec.listening":"wrong namespace",
    "testExamSection.listening":"qa sec"},
  ru:{"mistakesPage.title":"qa ru", "mistakesPage.cats.word":"qa ru nested",
    "testExamSection.listening":"qa ru sec"},
  tj:{"mistakesPage.title":"qa tj", "mistakesPage.cats.word":"qa tj nested",
    "testExamSection.listening":"qa tj sec"}};
fn({HSKAI_COURSE_I18N:catalog},dict,"mistakesPage");
fn({HSKAI_COURSE_I18N:catalog},dict,"testExam");
process.stdout.write(JSON.stringify(dict));
"""
        result = subprocess.run(
            ["node", "-e", node],
            input=json.dumps({"helper": helper}),
            capture_output=True, text=True, timeout=15, check=True,
        )
        actual = json.loads(result.stdout)
        self.assertEqual(actual["uz"]["title"], "qa")
        self.assertEqual(actual["uz"]["cats"], {"word": "qa nested", "empty": "keep"})
        self.assertEqual(actual["uz"]["sec"]["listening"], "qa sec")
        self.assertEqual(actual["ru"]["title"], "qa ru")
        self.assertEqual(actual["tj"]["cats"]["word"], "qa tj nested")

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_node_executable_three_language_override_and_missing_asset_fallback(self):
        html, main, live = source_parts()
        snippet = html.split("var VOICE=(function(){\n", 1)[1].split(
            "\nvar L=LD[LANG]||LD.ru;", 1
        )[0]
        node = r"""
const fs=require("fs");
const input=JSON.parse(fs.readFileSync(0,"utf8"));
const factory=new Function("window",input.source+"\nreturn LD;");
const fallback=factory({});
const hydrated=factory({HSKAI_COURSE_I18N:input.overrides});
process.stdout.write(JSON.stringify({fallback,hydrated}));
"""
        patch = {
            locale: {
                "courseVoiceInline.listening": "QA LISTEN " + locale,
                "courseVoiceInline.startLive": "QA LIVE " + locale,
                "courseVoiceInline.turnOf": "QA {n}",
                "courseVoiceInline.micDeny": "",
            }
            for locale in LANGUAGES
        }
        p = subprocess.run(
            ["node", "-e", node], input=json.dumps(
                {"source": snippet, "overrides": patch}),
            capture_output=True, text=True, timeout=15, check=True,
        )
        result = json.loads(p.stdout)
        expected = {
            locale: {**js_object_to_dict(main)[locale],
                     **js_object_to_dict(live)[locale]}
            for locale in LANGUAGES
        }
        self.assertEqual(result["fallback"], expected)
        for locale in LANGUAGES:
            expected[locale]["listening"] = "QA LISTEN " + locale
            expected[locale]["startLive"] = "QA LIVE " + locale
            expected[locale]["turnOf"] = "QA {n}"
        self.assertEqual(result["hydrated"], expected)


if __name__ == "__main__":
    unittest.main()

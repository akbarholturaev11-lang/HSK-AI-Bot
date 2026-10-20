"""Dictionary main UI, quick stroke writer and writer errors: 29 exact labels × 3."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ("uz", "ru", "tj")
EXPECTED = {"dictionaryPage": 20, "dictionaryFastWriter": 7,
            "dictionaryWriterStatus": 2}
PLURAL_KEYS = [
    f"dictionaryPage.{name}.{category}"
    for name in ("countAll", "countResults", "strokeCount")
    for category in ("one", "few", "many")
]
VERSION = "hsk-course-i18n.js?v=20261020-779fc95f8460"


def source():
    return (ROOT / "app/static/hsk-lugat.html").read_text(encoding="utf-8")


def labels(html):
    main = html.split("  var UI = {", 1)[1].split("  };var DICTIONARY_MAIN_UI=", 1)[0]
    fast = html.split("    var labels = {", 1)[1].split(
        "    }[lang] || {};var DICTIONARY_FAST_UI=", 1)[0]
    status = html.split("    var messages = {", 1)[1].split(
        "    };var DICTIONARY_STATUS_UI=", 1)[0]
    out = {locale: {} for locale in LOCALES}
    for locale in LOCALES:
        block = re.search(
            r"(?ms)^    " + locale + r": \{(.*?)^    \}[,]?", main
        )
        if block is None:
            raise AssertionError("Main dictionary language missing: " + locale)
        out[locale]["dictionaryPage"] = {
            key: json.loads('"' + value + '"')
            for key, value in re.findall(
                r'^\s*(\w+):\s*"((?:\\.|[^"\\])*)"', block.group(1), re.M
            )
        }
        for name, fragment in (("dictionaryFastWriter", fast),
                               ("dictionaryWriterStatus", status)):
            match = re.search(r"(?m)^      " + locale + r":\{([^\n]+)\}", fragment)
            if match is None:
                raise AssertionError("Inline writer source missing " + name + "/" + locale)
            out[locale][name] = dict(re.findall(
                r"(\w+):'((?:\\.|[^'\\])*)'", match.group(1)
            ))
    return out


class DictionaryUIAdoptionTests(unittest.TestCase):
    def test_exact_29_labels_in_three_locales(self):
        original = labels(source())
        for locale in LOCALES:
            catalog = json.loads(
                (ROOT / f"localization/ui/{locale}/course.json").read_text(encoding="utf-8")
            )["messages"]
            with self.subTest(locale=locale):
                self.assertEqual(len(catalog), 892)
                for namespace, required in EXPECTED.items():
                    data = original[locale][namespace]
                    self.assertEqual(len(data), required)
                    for key, value in data.items():
                        self.assertEqual(catalog[namespace + "." + key], value)
                for key in PLURAL_KEYS:
                    self.assertTrue(catalog[key])
                self.assertEqual(
                    {name for name in re.findall(r"\{([A-Za-z][A-Za-z0-9_]*)\}",
                                                 " ".join(catalog[key] for key in PLURAL_KEYS))},
                    {"count", "level"},
                )

    def test_bundle_order_inline_fallback_and_behavior_invariants(self):
        html = source()
        self.assertEqual(html.count(VERSION), 1)
        self.assertLess(html.index(VERSION), html.index("  var UI = {"))
        self.assertIn('dict["dictionaryPage."+key]', html)
        self.assertIn('DICTIONARY_FAST_UI["dictionaryFastWriter."+key]', html)
        self.assertIn('dict["dictionaryWriterStatus."+key]', html)
        self.assertIn('if(typeof value==="string"&&value)UI[lang][key]=value', html)
        self.assertIn('if(typeof value==="string"&&value)labels[key]=value', html)
        self.assertIn('if(typeof value==="string"&&value)messages[lang][key]=value', html)
        self.assertEqual(len(html.split("\n")), 1898)
        for marker in (
            "function initFastWriter(fastParams){",
            "function normalizeLevel(value){",
            "function normalizeFilterLevel(value){",
            "function filterCountLabel(t){",
            "function writerStatus(kind){",
            "function loadStrokeData(ch, onComplete, onError, token){",
            "function renderList(",
            "var L = memoLabels[currentLang] || memoLabels.uz;",
        ):
            self.assertIn(marker, html)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_js_overrides_and_offline_fallback_all_three_languages(self):
        html = source()
        snippets = {
            "helper": "function dictionaryPluralMessage" + html.split(
                "  function dictionaryPluralMessage", 1
            )[1].split(" var UI = {", 1)[0],
            "main": html.split("  var UI = ", 1)[1].split(
                "\n  var levelLabels = ", 1
            )[0],
            "fast": html.split("    var labels = ", 1)[1].split(
                "\n    var raw = fastParams.get(", 1
            )[0],
            "status": html.split("    var messages = ", 1)[1].split(
                "\n    var language = messages[currentLang] || messages.uz;", 1
            )[0],
        }
        node = r"""
const fs=require("fs");
const v=JSON.parse(fs.readFileSync(0,"utf8"));
function execute(lang,patch) {
  const window = {HSKAI_COURSE_I18N:patch};
  const main = new Function("window","lang","var currentLang=lang;"+v.helper+"\nvar UI = "+v.main+"\nreturn UI;")(window,lang);
  const fast = new Function("lang","window","var currentLang=lang;"+v.helper+"\nvar labels = "+v.fast+"\nreturn labels;")(lang,window);
  const status = new Function("window","var messages = "+v.status+"\nreturn messages;")(window);
  return {
    main:Object.fromEntries(Object.entries(main[lang]).filter(([k,v])=>typeof v==="string")),
    dynamicFunctions:["countAll","countResults","strokes"].every(k=>typeof main[lang][k]==="function"),
    counts:[main[lang].countAll(1,"HSK 1"),main[lang].countAll(2,"HSK 2"),
      main[lang].countResults(1),main[lang].countResults(2),main[lang].countResults(5),
      main[lang].strokes(1),main[lang].strokes(2),main[lang].strokes(5)],
    fast:Object.fromEntries(Object.entries(fast).filter(([k,v])=>typeof v==="string")),
    fastDynamic:typeof fast.strokes==="function",
    fastCounts:[fast.strokes(1),fast.strokes(2),fast.strokes(5)],
    status:status[lang],
  };
}
const result={};
for(const lang of ["uz","ru","tj"]){
  const local={
    ["dictionaryPage.title"]:"QA TITLE "+lang,
    ["dictionaryPage.language"]:"",
    ["dictionaryFastWriter.play"]:"QA PLAY "+lang,
    ["dictionaryFastWriter.pause"]:"",
    ["dictionaryWriterStatus.failed"]:"QA FAILED "+lang,
    ["dictionaryWriterStatus.loading"]:"",
  };
  for(const key of ["dictionaryPage.countAll","dictionaryPage.countResults","dictionaryPage.strokeCount"]){
    for(const category of ["one","few","many"]){
      local[key+"."+category]="QA "+key.split(".").pop()+" "+category+" {count}"+
        (key.endsWith("countAll")?" {level}":"");
    }
  }
  result[lang]={
    offline:execute(lang,undefined),
    patched:execute(lang,{[lang]:local})
  };
}
process.stdout.write(JSON.stringify(result));
"""
        original = labels(html)
        result = json.loads(subprocess.run(
            ["node", "-e", node],
            input=json.dumps(snippets, ensure_ascii=False),
            text=True, capture_output=True, check=True, timeout=20
        ).stdout)
        for lang in LOCALES:
            with self.subTest(locale=lang):
                offline = result[lang]["offline"]
                patched = result[lang]["patched"]
                self.assertTrue(offline["dynamicFunctions"])
                self.assertTrue(offline["fastDynamic"])
                self.assertTrue(patched["dynamicFunctions"])
                self.assertTrue(patched["fastDynamic"])
                suffixes = {"uz": (" so'z", " natija", " chiziq"),
                            "ru": (" слов", " результатов", " черт"),
                            "tj": (" калима", " натиҷа", " хат")}[lang]
                self.assertEqual(offline["counts"], [
                    "HSK 1 · 1" + suffixes[0], "HSK 2 · 2" + suffixes[0],
                    "1" + suffixes[1], "2" + suffixes[1], "5" + suffixes[1],
                    "1" + suffixes[2], "2" + suffixes[2], "5" + suffixes[2],
                ])
                fast_suffix = {"uz": " ta chiziq", "ru": " черт", "tj": " хат"}[lang]
                self.assertEqual(offline["fastCounts"], [
                    "1" + fast_suffix, "2" + fast_suffix, "5" + fast_suffix,
                ])
                category = {"uz": "many", "ru": "one", "tj": "many"}[lang]
                self.assertEqual(patched["counts"][0],
                                 "QA countAll " + category + " 1 HSK 1")
                category_two = {"uz": "many", "ru": "few", "tj": "many"}[lang]
                self.assertEqual(patched["counts"][1],
                                 "QA countAll " + category_two + " 2 HSK 2")
                self.assertEqual(patched["counts"][2],
                                 "QA countResults " + category + " 1")
                self.assertEqual(patched["counts"][4],
                                 "QA countResults many 5")
                self.assertEqual(patched["counts"][5],
                                 "QA strokeCount " + category + " 1")
                self.assertEqual(patched["fastCounts"][0],
                                 "QA strokeCount " + category + " 1")
                self.assertEqual(offline["main"], original[lang]["dictionaryPage"])
                self.assertEqual(offline["fast"], original[lang]["dictionaryFastWriter"])
                self.assertEqual(offline["status"], original[lang]["dictionaryWriterStatus"])
                self.assertEqual(patched["main"], dict(original[lang]["dictionaryPage"],
                    title="QA TITLE " + lang))
                self.assertEqual(patched["fast"], dict(original[lang]["dictionaryFastWriter"],
                    play="QA PLAY " + lang))
                self.assertEqual(patched["status"], dict(original[lang]["dictionaryWriterStatus"],
                    failed="QA FAILED " + lang))


if __name__ == "__main__":
    unittest.main()

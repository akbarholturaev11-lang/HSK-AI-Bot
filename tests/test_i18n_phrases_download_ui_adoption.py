"""Exact UZ/RU/TJ ready-phrases and downloads UI parity and offline adoption."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ("uz", "ru", "tj")
FAMILIES = {"readyPhrases": ("UI", 15), "downloadPage": ("COPY", 79)}


def inline_dictionary(source, name):
    match = re.search(r"var " + name + r" = (\{.*?\n\s*\});", source, re.S)
    if not match:
        raise AssertionError("Original UI dictionary not found: " + name)
    body = re.sub(
        r"([{,]\s*)([A-Za-z_]\w*)(\s*:)", r'\1"\2"\3', match.group(1)
    )
    body = re.sub(r",\s*([}\]])", r"\1", body)
    return json.loads(body)


class ReadyPhrasesAndDownloadUIAdoptionTests(unittest.TestCase):
    def test_94_exact_per_locale_values(self):
        pages = {
            "readyPhrases": (ROOT / "app/static/hsk-gaplar.html").read_text(encoding="utf-8"),
            "downloadPage": (ROOT / "app/static/desktop-download-page.js").read_text(encoding="utf-8")
        }
        for family, (source_name, size) in FAMILIES.items():
            source = inline_dictionary(pages[family], source_name)
            self.assertEqual(set(source), set(LOCALES))
            for lang in LOCALES:
                with self.subTest(family=family, lang=lang):
                    items = {key: value for key, value in source[lang].items()
                             if isinstance(value, str)}
                    self.assertEqual(len(items), size)
                    catalog = json.loads(
                        (ROOT / f"localization/ui/{lang}/course.json").read_text(encoding="utf-8")
                    )["messages"]
                    self.assertEqual(len(catalog), 797)
                    for key, value in items.items():
                        self.assertEqual(catalog[family + "." + key], value)

    def test_script_order_and_unchanged_app_paths(self):
        phrases = (ROOT / "app/static/hsk-gaplar.html").read_text(encoding="utf-8")
        download_page = (ROOT / "app/static/desktop-download.html").read_text(encoding="utf-8")
        download_js = (ROOT / "app/static/desktop-download-page.js").read_text(encoding="utf-8")
        asset = "hsk-course-i18n.js?v=20261019-phrases-download-v17"
        self.assertLess(phrases.index(asset), phrases.index("var UI ="))
        self.assertIn('PHRASE_UI["readyPhrases."+key]', phrases)
        self.assertIn('UI[LANGUAGE][key]=value', phrases)
        self.assertLess(download_page.index(asset), download_page.index("desktop-download-page.js"))
        self.assertIn('DOWNLOAD_UI[language]||{}', download_js)
        self.assertIn('localized["downloadPage."+key]', download_js)
        for page, markers in (
            (phrases, ("function readSavedIds()", "function persistSavedIds()",
                       "function rank(phrase, terms)", "function searchableFields(phrase)",
                       "hsk_ai_ready_phrases:v1")),
            (download_js, ("function applyLanguage()", "function setPlatform(platform)",
                           "function setLanguage(language)", "function loadRelease()",
                           '"/api/v3/apps/public-status"')),
        ):
            for marker in markers:
                self.assertIn(marker, page)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_runtime_override_and_no_bundle_fallback(self):
        phrases = (ROOT / "app/static/hsk-gaplar.html").read_text(encoding="utf-8")
        downloads = (ROOT / "app/static/desktop-download-page.js").read_text(encoding="utf-8")
        cases = [
            ("readyPhrases", phrases.split("var UI =", 1)[1].split(
                "      var text = UI[LANGUAGE];", 1)[0], "UI",
             {"readyPhrases.title": "TEST TITLE", "readyPhrases.count": "TEST {shown}/{total}",
              "readyPhrases.search": ""},
             {"title": "TEST TITLE", "count": "TEST {shown}/{total}"}),
            ("downloadPage", downloads.split("var COPY =", 1)[1].split(
                "  var state = {", 1)[0], "COPY",
             {"downloadPage.title": "TEST DOWNLOAD", "downloadPage.version": "TEST {version}",
              "downloadPage.selectTitle": ""},
             {"title": "TEST DOWNLOAD", "version": "TEST {version}"}),
        ]
        node = r"""
const fs=require("fs");
const d=JSON.parse(fs.readFileSync(0,"utf8"));
const code=(d.family==="downloadPage"?"var supportedLanguages=['uz','ru','tj'];\n":"")
  +"var "+d.variable+" ="+d.fragment+"\nreturn "+d.variable+";";
const fn=new Function("window","LANGUAGE",code);
const fallback=fn({},d.locale)[d.locale];
const hydrated=fn({HSKAI_COURSE_I18N:{[d.locale]:d.overrides}},d.locale)[d.locale];
process.stdout.write(JSON.stringify({fallback,hydrated}));
"""
        for family, snippet, variable, overrides, expected_updates in cases:
            for locale in LOCALES:
                with self.subTest(family=family, locale=locale):
                    output = subprocess.run(
                        ["node", "-e", node],
                        input=json.dumps({
                            "family": family, "variable": variable,
                            "fragment": snippet, "overrides": overrides, "locale": locale
                        }),
                        capture_output=True, text=True, check=True, timeout=15
                    )
                    actual = json.loads(output.stdout)
                    original = inline_dictionary(
                        phrases if family == "readyPhrases" else downloads, variable
                    )[locale]
                    self.assertEqual(actual["fallback"], original)
                    expected = dict(original)
                    expected.update(expected_updates)
                    self.assertEqual(actual["hydrated"], expected)


if __name__ == "__main__":
    unittest.main()

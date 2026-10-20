"""Source-parity contract for 49 local-first Test Center UI labels."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ("uz", "ru", "tj")
FAMILIES = {
    "L": ("testHub", ("title","sub","pTitle","pSub","pBtn","exHead","eTitle","eSub",
                      "eBack","listen","read","write","q","min","start","limTitle",
                      "limSub","limPay","limBack")),
    "EM": ("testExam", ("tfTrue","tfFalse","listen","q","of","result","passed","failed",
                       "passSub","failSub","again","toList","saving","saveErr","retry",
                       "mistakes","xp")),
    "PT": ("testPlacement", ("lead","rec","recSub","back","retake","lvl")),
    "HSK30_SOON": ("testHsk30Soon", ("title","sub","back")),
}
SECTIONS = ("listening","reading","writing")


def local_dict(source, name, locale):
    block = source.split("var " + name + "={", 1)[1].split("}[LANG];", 1)[0]
    if name == "HSK30_SOON":
        m = re.search(r'(?:^|,)' + locale + r':\{([^{}]+)\}', block)
        return m.group(1) if m else ""
    match = re.search(r'^\s*' + locale + r':\{(.*)\},?\s*$', block, re.M)
    return match.group(1) if match else ""


def fields(fragment):
    return dict((k, json.loads('"' + value + '"'))
                for k,value in re.findall(r'([A-Za-z][A-Za-z0-9]*):"((?:\\.|[^"\\])*)"', fragment))


class TestCenterI18nAdoptionTests(unittest.TestCase):
    def test_all_49_labels_byte_exact_with_original_display_dictionaries(self):
        html = (ROOT / "app/static/course_v3_test.html").read_text(encoding="utf-8")
        seen = set()
        for locale in LOCALES:
            catalog = json.loads((ROOT / f"localization/ui/{locale}/course.json")
                                 .read_text(encoding="utf-8"))["messages"]
            self.assertEqual(len(catalog), 894)
            for source_name, (prefix, names) in FAMILIES.items():
                fragment = local_dict(html, source_name, locale)
                original = fields(fragment)
                # EM.sec contributes three nested fields, handled separately.
                if source_name == "EM":
                    for name in SECTIONS:
                        self.assertEqual(catalog["testExamSection." + name], original[name])
                    original = {k:v for k,v in original.items() if k not in SECTIONS}
                self.assertEqual(set(original), set(names))
                for name in names:
                    with self.subTest(locale=locale, key=prefix + "." + name):
                        self.assertEqual(catalog[prefix + "." + name], original[name])
                seen.update(prefix + "." + name for name in names)
            match = re.search(r'var MINE_T=\{ru:"([^"]+)",uz:"([^"]+)",tj:"([^"]+)"\}\[LANG\]', html)
            self.assertIsNotNone(match)
            self.assertEqual(catalog["testHub.mineLevel"],
                             match.group({"ru":1,"uz":2,"tj":3}[locale]))
        self.assertEqual(len(seen) + len(SECTIONS) + 1, 49)

    def test_bundle_precedes_test_exercise_and_all_inline_fallbacks_remain(self):
        html = (ROOT / "app/static/course_v3_test.html").read_text(encoding="utf-8")
        self.assertLess(html.index("hsk-course-i18n.js?v=20261020-eaff685fb700"),
                        html.index("var L={"))
        for name in ("L","EM","PT","HSK30_SOON"):
            self.assertEqual(html.count("var " + name + "={"), 1)
        self.assertIn("adoptTestUI(\"testHub\",L);", html)
        self.assertIn("adoptTestUI(\"testExam\",EM);", html)
        self.assertIn("adoptTestUI(\"testExamSection\",EM.sec);", html)
        self.assertIn("adoptTestUI(\"testPlacement\",PT);", html)
        self.assertIn("adoptTestUI(\"testHsk30Soon\",HSK30_SOON);", html)
        self.assertIn('MINE_T=testUiLabel("testHub.mineLevel",MINE_T);', html)
        self.assertIn('return typeof value==="string"&&value?value:fallback;', html)
        self.assertIn('document.querySelector(".top .ix").setAttribute("aria-label",L.limBack);', html)
        self.assertNotIn("fetch('/api/i18n/", html)
        for invariant in ('function validatePracticeGate(o){',
                          'function runGate(feature,ref){',
                          'function runExam(data){',
                          'function pResult(){',
                          'var QP=[',
                          'function pPick(k,el){',
                          'function startLevel(){'):
            self.assertIn(invariant, html)
        bundle = (ROOT / "app/static/course_v3_data/hsk-course-i18n.js").read_text(encoding="utf-8")
        self.assertNotIn("fetch(", bundle)
        self.assertEqual(bundle, (ROOT / "desktop/ui/js/generated/hsk-course-i18n.js")
                         .read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

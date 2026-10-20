"""Recognition exact UZ/RU/TJ UI labels and static offline fallback."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYS = ("review", "listen", "lead", "done", "doneSub",
        "again", "limitTitle", "limitSub", "premiumBtn", "back")


class RecognitionUIAdoptionTests(unittest.TestCase):
    def test_exact_localized_legacy_string_parity(self):
        html = (ROOT / "app/static/course_v3_recognition.html").read_text(encoding="utf-8")
        block = html.split("var L={", 1)[1].split("}[LANG];", 1)[0]
        for locale in ("uz", "ru", "tj"):
            with self.subTest(locale=locale):
                match = re.search(r"(?:^|,)\s*" + locale + r":\{([^{}]+)\}", block)
                self.assertIsNotNone(match)
                literal = {
                    key: json.loads('"' + value + '"')
                    for key, value in re.findall(
                        r'([A-Za-z]\w*):"((?:\\.|[^"\\])*)"', match.group(1)
                    )
                }
                self.assertEqual(set(literal), set(KEYS))
                catalog = json.loads(
                    (ROOT / f"localization/ui/{locale}/course.json").read_text(encoding="utf-8")
                )["messages"]
                self.assertEqual(len(catalog), 883)
                for key in KEYS:
                    self.assertEqual(catalog["recognition." + key], literal[key])

    def test_preloaded_local_asset_and_unchanged_practice_gate(self):
        html = (ROOT / "app/static/course_v3_recognition.html").read_text(encoding="utf-8")
        self.assertLess(
            html.index("hsk-course-i18n.js?v=20261020-96b42704ca5a"),
            html.index("var L={"),
        )
        self.assertIn('RECOGNITION_UI["recognition."+k]', html)
        self.assertIn('if(typeof v==="string"&&v)L[k]=v', html)
        for marker in (
            "function validatePracticeGate(o){",
            "function runGate(ref){",
            "function practiceGateErrorCopy(){",
            "function goPremium(){",
            "function wordSource(){",
            "function wordGate(h){",
        ):
            self.assertIn(marker, html)
        self.assertEqual(html.count("var L={"), 1)


if __name__ == "__main__":
    unittest.main()

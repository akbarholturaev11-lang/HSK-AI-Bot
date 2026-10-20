"""Source-backed P2 Mini App sheet/lesson-settings copy from offline catalogs.

Only display labels are migrated. Preserve locale fallbacks, keyboard/screen-
reader accessibility and lesson exit/entitlement logic.
"""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/static/course-v3.html"
LOCALES = ("uz", "ru", "tj")
LABELS = {
    "lessonSettings.title": {
        "ru": "Настройки урока", "tj": "Танзимоти дарс",
        "uz": "Dars sozlamalari",
    },
    "lessonSettings.exit": {
        "ru": "Выйти", "tj": "Баромадан", "uz": "Chiqish",
    },
    "sheet.dialogLabel": {
        "ru": "Диалог HSK AI", "tj": "Муколамаи HSK AI",
        "uz": "HSK AI oynasi",
    },
    "sheet.closeLabel": {
        "ru": "Закрыть", "tj": "Пӯшидан", "uz": "Yopish",
    },
}
OCCURRENCES = {
    "lessonSettings.title": 2,
    "lessonSettings.exit": 1,
    "sheet.dialogLabel": 1,
    "sheet.closeLabel": 1,
}


class MiniAppLessonSettingsLocalUIAdoptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = SOURCE.read_text(encoding="utf-8")
        cls.catalogs = {
            locale: json.loads(
                (ROOT / f"localization/ui/{locale}/course.json").read_text(encoding="utf-8")
            )["messages"]
            for locale in LOCALES
        }

    def test_exact_three_locale_copy_and_fallback_calls(self):
        self.assertEqual(len(self.html.split("\n")), 8859)
        self.assertLess(
            self.html.index("hsk-course-i18n.js"),
            self.html.index("function courseMessage(key,fallback)"),
        )
        for key, expected in LABELS.items():
            expression = (
                r'courseMessage\("' + re.escape(key) +
                r'",LANG==="ru"\?"([^"]+)":LANG==="tj"\?"([^"]+)":"([^"]+)"\)'
            )
            matches = re.findall(expression, self.html)
            with self.subTest(key=key):
                self.assertEqual(len(matches), OCCURRENCES[key])
                for values in matches:
                    original = dict(zip(("ru", "tj", "uz"), values))
                    self.assertEqual(original, expected)
                    for locale in LOCALES:
                        self.assertEqual(self.catalogs[locale][key], expected[locale])
                        self.assertEqual(len(self.catalogs[locale]), 895)

    def test_existing_sheet_accessibility_and_exit_flow_remain(self):
        source = self.html
        self.assertIn('sheet.setAttribute("aria-labelledby",title.id)', source)
        self.assertIn('sheet.setAttribute("role","dialog")', source)
        self.assertIn('sheet.setAttribute("aria-modal","true")', source)
        self.assertIn('setSheetBackgroundInert(true)', source)
        self.assertIn('focusSheetStart(sheet)', source)
        self.assertIn('sheet.setAttribute("aria-label",courseMessage("sheet.dialogLabel",', source)
        self.assertIn('close.setAttribute("aria-label",courseMessage("sheet.closeLabel",', source)
        self.assertIn('gear.setAttribute("aria-label",courseMessage("lessonSettings.title",', source)
        self.assertIn('App.requestExitFlow()', source)
        self.assertIn("reserveLessonStart(l).then(function(){return loadLessonData(lv,l.n)}", source)


if __name__ == "__main__":
    unittest.main()

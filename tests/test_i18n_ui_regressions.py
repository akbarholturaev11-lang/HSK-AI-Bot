"""Source regressions for known Mini App language mixups.

These are lightweight static guards; browser smoke tests still required.
"""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "app" / "static"


class MiniAppI18nRegressions(unittest.TestCase):
    def test_tajik_retry_uses_backend_locale_code(self):
        text = (ROOT / "course-v3.html").read_text(encoding="utf-8")
        self.assertIn('LANG==="tj"?"Такрор кардан"', text)
        self.assertNotIn('LANG==="tg"?"Такрор кардан"', text)

    def test_foundation_error_header_is_localized(self):
        text = (ROOT / "course-v3.html").read_text(encoding="utf-8")
        self.assertIn('LANG==="ru"?"Основы с нуля":LANG==="tj"?"Асосҳо аз сифр"', text)

    def test_no_data_errors_are_localized_on_all_three_practice_pages(self):
        checks = {
            "course_v3_pronunciation.html": 'practiceMessage("practice.dataNotLoaded"',
            "course_v3_recognition.html": 'practiceMessage("practice.dataNotLoaded"',
        }
        for name, expected in checks.items():
            with self.subTest(name=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertIn(expected, text)
                self.assertIn('uz:"Ma\'lumot yuklanmadi"', text)
                self.assertIn('ru:"Не удалось загрузить данные"', text)
                self.assertIn('tj:"Маълумот бор нашуд"', text)
        memorize = (ROOT / "course_v3_memorize.html").read_text(encoding="utf-8")
        self.assertIn('memoMessage("practice.dataNotLoaded"', memorize)
        self.assertIn('uz:"Ma\'lumot yuklanmadi"', memorize)
        self.assertIn('ru:"Не удалось загрузить данные"', memorize)
        self.assertIn('tj:"Маълумот бор нашуд"', memorize)


if __name__ == "__main__":
    unittest.main()

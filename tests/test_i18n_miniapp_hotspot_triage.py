"""Source-only manual triage anchors for selected Mini App LANG branches."""
import json
from collections import Counter
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TRIAGE = ROOT / "localization/review/miniapp_course_hotspot_triage.json"
SOURCE = ROOT / "app/static/course-v3.html"

COPY_CATEGORIES = {
    "accessibility_copy", "loading_copy", "navigation_copy", "formatted_copy",
    "profile_copy", "access_copy", "lesson_navigation_copy",
    "lesson_example_translation", "error_recovery_copy",
    "result_error_copy", "assessment_ui_copy", "quota_ui_copy",
    "time_formatting_copy", "cooldown_copy", "rating_copy",
    "referral_copy", "feedback_copy", "social_copy",
}
NONCOPY_CATEGORIES = {"locale_adapter", "locale_grammar", "tts_language_adapter",
                      "invariant_brand_label"}


class CourseHotspotTriageTests(unittest.TestCase):
    def test_manually_reviewed_source_anchors_remain_current(self):
        triage = json.loads(TRIAGE.read_text(encoding="utf-8"))
        src = SOURCE.read_text(encoding="utf-8").splitlines()
        self.assertEqual(triage["status"],
                         "SOURCE_CLASSIFIED_ALL_EXPLICIT_LANG_EQUALS_BRANCH_LINES_NOT_RUNTIME_VALIDATION")
        self.assertEqual(triage["source"], "app/static/course-v3.html")
        self.assertEqual(len(triage["classifications"]), 62)
        counts = Counter()
        for line, text in enumerate(src, start=1):
            counts[line] = len(re.findall(r"""\bLANG\s*===?\s*['"](?:ru|tj|uz)['"]""", text))
        actual_lines = {line for line, count in counts.items() if count}
        lines = set()
        categories = set()
        for item in triage["classifications"]:
            with self.subTest(line=item["line"], category=item["category"]):
                self.assertIsInstance(item["line"], int)
                self.assertTrue(1 <= item["line"] <= len(src))
                self.assertNotIn(item["line"], lines, "Duplicate manual source line")
                lines.add(item["line"])
                self.assertTrue(item["anchor"].strip())
                self.assertIn(item["anchor"], src[item["line"] - 1],
                              "Classification stale: re-review line before migration")
                self.assertEqual(item["review"], "source_classified_only")
                self.assertTrue(item["reason"].strip())
                self.assertIn(item["category"], COPY_CATEGORIES | NONCOPY_CATEGORIES)
                self.assertEqual(item["predicate_occurrences"], counts[item["line"]])
                categories.add(item["category"])
        self.assertIn("locale_adapter", categories)
        self.assertIn("locale_grammar", categories)
        self.assertIn("tts_language_adapter", categories)
        self.assertIn("assessment_ui_copy", categories)
        self.assertEqual(lines, actual_lines,
                         "All explicit LANG equality conditions require reviewed classifications")
        self.assertEqual(sum(counts.values()), 131)
        self.assertEqual(sum(item["predicate_occurrences"]
                             for item in triage["classifications"]), 131)

    def test_do_not_treat_all_locale_conditions_as_translation_literals(self):
        triage = json.loads(TRIAGE.read_text(encoding="utf-8"))
        by_category = {item["category"] for item in triage["classifications"]}
        self.assertTrue(NONCOPY_CATEGORIES <= by_category)
        self.assertIn("62 unique physical source lines", triage["counting_note"])
        self.assertIn("All other localized source expressions", triage["coverage_note"])


    def test_sheet_and_lesson_settings_copy_use_local_first_catalogs(self):
        """The newly reviewed settings and accessible labels prefer local bundles."""
        html = SOURCE.read_text(encoding="utf-8")
        expected = {
            "lessonSettings.title": (2, ("Dars sozlamalari", "Настройки урока", "Танзимоти дарс")),
            "lessonSettings.exit": (1, ("Chiqish", "Выйти", "Баромадан")),
            "sheet.dialogLabel": (1, ("HSK AI oynasi", "Диалог HSK AI", "Муколамаи HSK AI")),
            "sheet.closeLabel": (1, ("Yopish", "Закрыть", "Пӯшидан")),
        }
        for key, (sites, values) in expected.items():
            with self.subTest(key=key):
                self.assertEqual(html.count('courseMessage("' + key + '",LANG'), sites)
                for locale, value in zip(("uz", "ru", "tj"), values):
                    catalog = json.loads((ROOT / "localization/ui" / locale /
                                         "course.json").read_text(encoding="utf-8"))["messages"]
                    self.assertEqual(catalog[key], value)
                    self.assertEqual(len(catalog), 829)
        self.assertIn('setSheetBackgroundInert(true)', html)
        self.assertIn('focusSheetStart(sheet)', html)
        self.assertIn('App.requestExitFlow()', html)
        self.assertIn('gear.setAttribute("aria-label",courseMessage("lessonSettings.title",', html)

    def test_reviewed_rating_and_social_toasts_stay_local_first_with_exact_fallbacks(self):
        """The nine social/rating display callsites are local only, not new APIs."""
        html = SOURCE.read_text(encoding="utf-8")
        labels = {
            "rating.retryLoading": (1, "Qayta yuklash", "Повторить загрузку", "Аз нав бор кардан"),
            "rating.weeklyTopFive": (1, "Haftalik reyting · Top 5", "Недельный рейтинг · Топ 5", "Рейтинги ҳафта · Топ 5"),
            "rating.copiedToast": (1, "Nusxalandi", "Скопировано", "Нусха гирифта шуд"),
            "rating.telegramUsernameMissing": (1, "Foydalanuvchida Telegram username yo'q", "У пользователя нет Telegram username", "Корбар username-и Telegram надорад"),
            "rating.challengeNotAllowed": (1, "Bu foydalanuvchiga chaqiruv yuborib bo'lmaydi", "Этому пользователю нельзя бросить вызов", "Ба ин корбар даъват фиристодан мумкин нест"),
            "rating.challengeSendFailed": (2, "Chaqiruv yuborilmadi", "Не удалось отправить вызов", "Даъват фиристода нашуд"),
            "rating.duelRejected": (1, "Belashuv rad qilindi.", "Дуэль отклонена.", "Рақобат рад шуд."),
            "rating.weeklyHeading": (1, "Haftalik reyting", "Недельный рейтинг", "Рейтинги ҳафтаина"),
        }
        catalogs = {
            lang: json.loads((ROOT / "localization/ui" / lang / "course.json")
                             .read_text(encoding="utf-8"))["messages"]
            for lang in ("uz", "ru", "tj")
        }
        for key, (calls, uz, ru, tj) in labels.items():
            fallback = ('LANG==="ru"?' + json.dumps(ru, ensure_ascii=False)
                        + ':LANG==="tj"?' + json.dumps(tj, ensure_ascii=False)
                        + ':' + json.dumps(uz, ensure_ascii=False))
            with self.subTest(key=key):
                self.assertEqual(html.count('courseMessage("' + key + '",' + fallback + ')'), calls)
                for locale, value in (("uz", uz), ("ru", ru), ("tj", tj)):
                    self.assertEqual(catalogs[locale][key], value)
                    self.assertEqual(len(catalogs[locale]), 829)
        self.assertEqual(len(html.split("\n")), 8859)
        self.assertIn("challengeSending=false", html)
        self.assertIn("ratingRetryText()", html)

if __name__ == "__main__":
    unittest.main()

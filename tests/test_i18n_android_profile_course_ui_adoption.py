"""Exact-copy Android profile, course and lesson UI adoption from local catalogs."""
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
LOCALES = {"uz": "values", "ru": "values-ru", "tj": "values-tg"}
RESOURCES = {
    "nav_course": ("common", "hsk_common_navigation_course"),
    "nav_profile": ("common", "hsk_common_navigation_profile"),
    "nav_rating": ("common", "hsk_common_navigation_rating"),
    "profile_subscription_title": ("common", "hsk_common_navigation_subscription"),
    "skip_test_start_lesson": ("common", "hsk_common_lesson_start"),
    "course_choice_title": ("course", "hsk_course_course_picker_title"),
    "course_choice_version": ("course", "hsk_course_course_picker_version"),
    "course_choice_level": ("course", "hsk_course_course_picker_level"),
    "course_choice_confirm": ("course", "hsk_course_course_picker_confirm"),
    "today_xp": ("course", "hsk_course_xp"),
    "profile_xp": ("course", "hsk_course_xp"),
    "course_checkpoint": ("course", "hsk_course_part_sections_r"),
    "lesson_check": ("course", "hsk_course_check"),
    "lesson_grammar": ("course", "hsk_course_grammar"),
    "lesson_stat_xp": ("course", "hsk_course_level_stats_xp"),
    "lesson_stat_accuracy": ("course", "hsk_course_level_stats_acc"),
    "lesson_stat_time": ("course", "hsk_course_level_stats_time"),
    "lesson_pinyin_title": ("course", "hsk_course_pinyin_settings_h"),
    "lesson_pinyin_off": ("course", "hsk_course_pinyin_settings_off"),
    "exam_result_passed": ("course", "hsk_course_test_exam_passed"),
    "hsk30_test_soon_body": ("course", "hsk_course_test_hsk30_soon_sub"),
    "profile_accuracy_overall": ("course", "hsk_course_profile_overall"),
    "profile_accuracy_today": ("course", "hsk_course_profile_today"),
    "profile_buy_pro": ("course", "hsk_course_profile_pro"),
    "profile_course_version": ("course", "hsk_course_course_picker_version"),
    "profile_language": ("course", "hsk_course_lang"),
    "profile_notifications": ("course", "hsk_course_notif"),
    "profile_help_action": ("course", "hsk_course_help_btn"),
    "rating_level": ("course", "hsk_course_level_up_lvl"),
    "rating_you": ("course", "hsk_course_you"),
}
FILE_RESOURCES = {
    "android/app/src/main/java/com/pomp/hskai/MainActivity.kt": (
        "profile_course_version", "lesson_pinyin_title", "lesson_pinyin_off",
    ),
    "android/app/src/main/java/com/pomp/hskai/feature/course/CourseScreen.kt": (
        "nav_course", "course_choice_title", "course_choice_version",
        "course_choice_level", "course_choice_confirm", "today_xp",
        "course_checkpoint",
    ),
    "android/app/src/main/java/com/pomp/hskai/feature/course/SkipTestScreen.kt": (
        "skip_test_start_lesson",
    ),
    "android/app/src/main/java/com/pomp/hskai/feature/foundation/FoundationScreen.kt": (
        "lesson_check",
    ),
    "android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonCards.kt": (
        "lesson_grammar",
    ),
    "android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonCompletionCelebration.kt": (
        "lesson_stat_xp", "lesson_stat_accuracy", "lesson_stat_time",
    ),
    "android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonScreen.kt": (
        "nav_course", "lesson_pinyin_title",
    ),
    "android/app/src/main/java/com/pomp/hskai/feature/practice/PracticeCompletionHero.kt": (
        "exam_result_passed",
    ),
    "android/app/src/main/java/com/pomp/hskai/feature/practice/PracticeScreen.kt": (
        "hsk30_test_soon_body",
    ),
    "android/app/src/main/java/com/pomp/hskai/feature/profile/ProfileAccuracyRings.kt": (
        "profile_accuracy_overall", "profile_accuracy_today", "profile_buy_pro",
    ),
    "android/app/src/main/java/com/pomp/hskai/feature/profile/ProfilePromoCarousel.kt": (
        "profile_subscription_title", "profile_course_version",
    ),
    "android/app/src/main/java/com/pomp/hskai/feature/profile/ProfileScreen.kt": (
        "nav_profile", "profile_xp", "profile_language", "profile_course_version",
        # Support now uses the platform-owned canonical profile_support label;
        # the former exact-copy "write to admin" action is no longer rendered.
        "profile_notifications",
    ),
    "android/app/src/main/java/com/pomp/hskai/feature/rating/RatingScreen.kt": (
        "nav_rating", "profile_xp", "rating_level", "rating_you",
    ),
}


def read_strings(locale_dir, file_name):
    path = ROOT / "android/app/src/main/res" / locale_dir / file_name
    root = ET.parse(path).getroot()
    return {node.attrib["name"]: "".join(node.itertext())
            for node in root.findall("string")}


class AndroidProfileCourseCatalogTests(unittest.TestCase):
    def test_all_selected_values_match_in_all_locales(self):
        self.assertEqual(len(RESOURCES), 30)
        for locale, directory in LOCALES.items():
            original = read_strings(directory, "strings.xml")
            common = read_strings(directory, "hsk_common_i18n.xml")
            course = read_strings(directory, "hsk_course_i18n.xml")
            for old_key, (catalog, generated_key) in RESOURCES.items():
                generated = common if catalog == "common" else course
                with self.subTest(locale=locale, key=old_key):
                    self.assertIn(old_key, original)
                    self.assertIn(generated_key, generated)
                    self.assertEqual(original[old_key], generated[generated_key])

    def test_selected_sources_use_the_canonical_local_resources(self):
        for file_name, keys in FILE_RESOURCES.items():
            source = (ROOT / file_name).read_text(encoding="utf-8")
            for old_key in keys:
                generated_key = RESOURCES[old_key][1]
                with self.subTest(file=file_name, key=old_key):
                    self.assertRegex(source, rf"R\.string\.{re.escape(generated_key)}(?![A-Za-z0-9_])")
                    self.assertNotRegex(source, rf"R\.string\.{re.escape(old_key)}(?![A-Za-z0-9_])")


if __name__ == "__main__":
    unittest.main()

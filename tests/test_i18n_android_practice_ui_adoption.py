"""Exact-copy Android practice and Test Center adoption from local catalogs."""
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
LOCALES = {"uz": "values", "ru": "values-ru", "tj": "values-tg"}
RESOURCES = {
    "practice_title": ("common", "hsk_common_navigation_practice"),
    "practice_subtitle_short": ("course", "hsk_course_mashq_sub"),
    "practice_group_tests": ("course", "hsk_course_test_center"),
    "practice_mistakes_title": ("course", "hsk_course_mistakes_page_title"),
    "practice_ready_phrases_title": ("course", "hsk_course_ready_phrases_title"),
    "practice_finish": ("course", "hsk_course_mistakes_page_finish"),
    "test_center_exams_head": ("course", "hsk_course_test_hub_ex_head"),
    "test_center_placement_button": ("course", "hsk_course_test_hub_p_btn"),
    "test_center_placement_title": ("course", "hsk_course_test_hub_p_title"),
    "test_center_section_listening": ("course", "hsk_course_test_hub_listen"),
    "test_center_section_writing": ("course", "hsk_course_test_hub_write"),
    "test_center_start": ("course", "hsk_course_test_hub_start"),
    "test_center_your_level": ("course", "hsk_course_test_hub_mine_level"),
    "ready_phrases_all": ("course", "hsk_course_ready_phrases_all"),
    "ready_phrases_no_saved": ("course", "hsk_course_ready_phrases_no_saved"),
    "ready_phrases_retry": ("course", "hsk_course_ready_phrases_retry"),
    "ready_phrases_save": ("course", "hsk_course_ready_phrases_save"),
    "ready_phrases_saved": ("course", "hsk_course_ready_phrases_saved"),
    "ready_phrases_search_hint": ("course", "hsk_course_ready_phrases_search"),
    "lesson_check": ("course", "hsk_course_check"),
    "lesson_correct": ("course", "hsk_course_test_exam_tf_true"),
    "lesson_listen": ("course", "hsk_course_listen"),
    "lesson_match_pairs": ("course", "hsk_course_match_pairs"),
    "lesson_wrong": ("course", "hsk_course_test_exam_tf_false"),
}
FILE_RESOURCES = {
    "android/app/src/main/java/com/pomp/hskai/feature/practice/PracticeViewModel.kt": (
        "practice_group_tests", "practice_mistakes_title",
    ),
    "android/app/src/main/java/com/pomp/hskai/feature/practice/PracticeScreen.kt": (
        "practice_title", "practice_subtitle_short", "practice_group_tests",
        "practice_mistakes_title", "practice_ready_phrases_title", "practice_finish",
        "test_center_exams_head", "test_center_placement_button",
        "test_center_placement_title", "test_center_section_listening",
        "test_center_section_writing", "test_center_start", "test_center_your_level",
    ),
    "android/app/src/main/java/com/pomp/hskai/feature/practice/ReadyPhrasesScreen.kt": (
        "ready_phrases_all", "ready_phrases_no_saved", "ready_phrases_retry",
        "ready_phrases_save", "ready_phrases_saved", "ready_phrases_search_hint",
    ),
    "android/app/src/main/java/com/pomp/hskai/feature/practice/PracticeStage.kt": (
        "lesson_check", "lesson_correct", "lesson_wrong",
    ),
    "android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonCards.kt": (
        "lesson_check", "lesson_listen",
    ),
    "android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonScreen.kt": (
        "lesson_check", "lesson_correct", "lesson_wrong", "lesson_match_pairs",
    ),
    "android/app/src/main/java/com/pomp/hskai/feature/course/SkipTestScreen.kt": (
        "practice_finish",
    ),
}


def read_strings(locale_dir, file_name):
    path = ROOT / "android/app/src/main/res" / locale_dir / file_name
    root = ET.parse(path).getroot()
    return {node.attrib["name"]: "".join(node.itertext())
            for node in root.findall("string")}


class AndroidPracticeUICatalogTests(unittest.TestCase):
    def test_all_selected_practice_values_match_in_all_locales(self):
        self.assertEqual(len(RESOURCES), 24)
        for locale, directory in LOCALES.items():
            original = read_strings(directory, "strings.xml")
            common = read_strings(directory, "hsk_common_i18n.xml")
            course = read_strings(directory, "hsk_course_i18n.xml")
            for old_key, (catalog, generated_key) in RESOURCES.items():
                with self.subTest(locale=locale, key=old_key):
                    generated = common if catalog == "common" else course
                    self.assertIn(old_key, original)
                    self.assertIn(generated_key, generated)
                    self.assertEqual(original[old_key], generated[generated_key])

    def test_practice_sources_use_only_selected_local_resources(self):
        for file_name, keys in FILE_RESOURCES.items():
            source = (ROOT / file_name).read_text(encoding="utf-8")
            for old_key in keys:
                generated_key = RESOURCES[old_key][1]
                with self.subTest(file=file_name, key=old_key):
                    self.assertIn(f"R.string.{generated_key}", source)
                    self.assertNotRegex(source, rf"R\.string\.{re.escape(old_key)}(?![A-Za-z0-9_])")
        stage = (ROOT / "android/app/src/main/java/com/pomp/hskai/feature/practice/PracticeStage.kt").read_text(encoding="utf-8")
        lesson = (ROOT / "android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonScreen.kt").read_text(encoding="utf-8")
        practice = (ROOT / "android/app/src/main/java/com/pomp/hskai/feature/practice/PracticeScreen.kt").read_text(encoding="utf-8")
        self.assertIn("if (isCorrect)", stage)
        self.assertIn("if (answer.isCorrect)", lesson)
        self.assertIn("openGroup = PracticeGroup.TEST", practice)
        self.assertIn("state.examIndex == session.questions.lastIndex", practice)


if __name__ == "__main__":
    unittest.main()

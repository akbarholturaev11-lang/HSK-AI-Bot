import json
import unittest
from pathlib import Path


BASE = Path("app/static/course_v3_data")
EXPECTED_LESSON_COUNTS = {
    "hsk1": 15,
    "hsk2": 15,
    "hsk3": 20,
    "hsk4": 20,
}


class CourseV3StaticMapTests(unittest.TestCase):
    def test_level_maps_cover_all_lessons_without_demo_progress(self):
        for level, expected_count in EXPECTED_LESSON_COUNTS.items():
            with self.subTest(level=level):
                data = json.loads((BASE / f"{level}.json").read_text(encoding="utf-8"))
                lessons = [
                    lesson
                    for unit in data.get("units", [])
                    for lesson in unit.get("lessons", [])
                ]

                self.assertEqual(data["schema_version"], 2)
                self.assertEqual(data["level"], level)
                self.assertEqual(data["progress"]["xp"], 0)
                self.assertEqual(data["progress"]["completed"], 0)
                self.assertEqual(len(lessons), expected_count)
                self.assertEqual(lessons[0]["status"], "current")

                for lesson in lessons[:3]:
                    self.assertFalse(lesson.get("locked_premium", False))
                    self.assertTrue((BASE / level / f"lesson_{lesson['n']:02d}.json").exists())
                for lesson in lessons[3:]:
                    self.assertEqual(lesson["status"], "locked")
                    self.assertTrue(lesson.get("locked_premium", False))
                    self.assertTrue((BASE / level / f"lesson_{lesson['n']:02d}.json").exists())

    def test_course_v3_respects_selected_level_and_real_invite_format(self):
        html = Path("app/static/course-v3.html").read_text(encoding="utf-8")
        onboarding = Path("app/static/course_v3_onboarding.html").read_text(encoding="utf-8")

        self.assertIn("getSelectedLevel()", html)
        self.assertIn("localStorage.getItem(\"hsk_v3_level\")", html)
        self.assertIn('"/api/v3/map?lang="+LANG+"&level="+bootLevel', html)
        self.assertIn('"/course_v3_data/"+bootLevel+".json"', html)
        self.assertIn("App.levelPicker()", html)
        self.assertIn("/api/v3/invite?lang=", html)
        self.assertNotIn("start=ref_", html)
        self.assertIn('"&level="+sel+"&onboarded=1&tour=1"', onboarding)


if __name__ == "__main__":
    unittest.main()

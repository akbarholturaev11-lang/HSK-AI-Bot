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
        self.assertIn("if(!INIT_DATA){showAuthGate();return;}", html)
        self.assertIn('"/course_v3_data/"+lv+"/lesson_"+pad+".json"', html)
        self.assertIn("levelPicker:function", html)
        self.assertIn("/api/v3/invite?lang=", html)
        self.assertNotIn("start=ref_", html)
        self.assertIn("PRONOUNCE_LIMIT_EXCEEDED", html)
        self.assertIn("v3_pronunciation_limit", html)
        self.assertIn("Reklama bilan davom etish", html)
        self.assertIn("/api/v3/ad?placement=", html)
        self.assertIn("/api/v3/ad/view", html)
        self.assertIn("/api/v3/lesson/unlock", html)
        self.assertIn("section_completed", html)
        self.assertIn("ratingCountdownText()", html)
        self.assertIn("pendingRankUp", html)
        self.assertIn("loadLatestRating()", html)
        self.assertIn("rank:Number(u.rank||0)", html)
        self.assertIn("referralUsers=[]", html)
        self.assertIn("openRatingUser('+i+',\\'referrals\\')", html)
        self.assertIn("invitePayloadUrl()", html)
        self.assertNotIn("u.weeklyXp||u.xp||0", html)
        self.assertNotIn("meU.weeklyXp||MAP&&MAP.progress&&MAP.progress.xp", html)
        self.assertIn("awarded_xp", html)
        self.assertNotIn('["+60","XP"]', html)
        self.assertNotIn('["+200","XP"]', html)
        self.assertNotIn('["+50",lu.bonusXp]', html)
        self.assertNotIn("64 / 100", html)
        self.assertNotIn("2'+(LANG", html)
        self.assertIn("AdFlow", html)
        self.assertIn('"&level="+sel+"&onboarded=1&tour=1"', onboarding)

    def test_hsk_exam_options_hide_pinyin_and_hint_labels(self):
        html = Path("app/static/course_v3_test.html").read_text(encoding="utf-8")

        self.assertIn("function examOptionText(q,o)", html)
        self.assertIn('if(q.type==="audio_choice"||isMeaningQuestion(q))return lab||zh;', html)
        self.assertNotIn("var py=o.py?", html)
        self.assertNotIn("'<small>'+lab+'</small>'", html)


if __name__ == "__main__":
    unittest.main()

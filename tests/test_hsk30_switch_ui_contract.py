"""Regression contracts for HSK 3.0 switching and panda study entry UI."""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MINI = ROOT / "app" / "static" / "course-v3.html"
ANDROID = ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "pomp" / "hskai"


class Hsk30SwitchUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mini = MINI.read_text(encoding="utf-8")
        cls.android = (ANDROID / "feature" / "course" / "CourseScreen.kt").read_text(encoding="utf-8")

    def test_hsk30_switch_opens_level_picker_without_n1_default_or_confirmation(self):
        confirm = self.mini.split("function confirmCourseTrackSwitch(target,status){", 1)[1].split(
            "function requestCourseTrackSwitch(target){", 1
        )[0]
        self.assertIn('openHsk30LevelPicker(status);', confirm)
        self.assertNotIn("hsk30LiveLevels()[0]", confirm)
        self.assertNotIn("switchConfirmAction", confirm)

        picker = self.mini.split("function openHsk30LevelPicker(status,recommended){", 1)[1].split(
            "function openHsk30PromoLevelPicker(recommended){", 1
        )[0]
        self.assertIn("h30.level", picker)
        self.assertIn("selectHsk30PromoLevel(", picker)
        self.assertIn("HSK '+levelBand(lv)", picker)
        self.assertIn("hsk30BookHeader(status,false)", picker)
        self.assertNotIn("NEW", picker)

    def test_locked_hsk30_switch_goes_to_payment_gate_before_post(self):
        switch = self.mini.split("function switchCourseTrack(target,requestedLevel){", 1)[1].split(
            "var HSK30_PROMO_CHECKED", 1
        )[0]
        self.assertIn('target==="hsk30"&&(!access||!access.allowed)', switch)
        self.assertIn("renderHsk30AccessGate(status)", switch)
        self.assertIn("/api/v3/course-tracks/switch", switch)

    def test_android_picker_has_no_new_badges_or_secondary_confirm(self):
        picker = self.android.split("private fun Hsk30LevelChoiceDialog(", 1)[1].split(
            "private fun Hsk30PromoDialog(", 1
        )[0]
        self.assertIn('label = "HSK $band"', picker)
        self.assertIn("isNew = false", picker)
        self.assertNotIn('" · NEW"', picker)
        self.assertIn("onClick = { onChoose(level) }", picker)
        self.assertIn("if (hsk30.access.allowed)", self.android)

    def test_panda_preparing_is_only_used_for_lesson_and_practice_entry(self):
        helper = (ROOT / "app" / "static" / "assets" / "characters" / "hsk-study-preparing.js").read_text(encoding="utf-8")
        self.assertIn('HSKCharacters.render("panda","loading")', helper)
        self.assertIn('hsk-study-preparing', helper)
        for filename in ("course_v3_recognition.html", "course_v3_pronunciation.html", "course_v3_memorize.html"):
            page = (ROOT / "app" / "static" / filename).read_text(encoding="utf-8")
            self.assertIn('HSKStudyPreparing.render(LANG)', page)
        lesson = (ANDROID / "feature" / "lesson" / "LessonScreen.kt").read_text(encoding="utf-8")
        self.assertIn('state.isLoading -> LessonEntryOverlay(alpha = 1f', lesson)

    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
    def test_mini_inline_javascript_is_syntactically_valid(self):
        scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", self.mini, re.S | re.I)
        with tempfile.TemporaryDirectory() as temp:
            for index, script in enumerate(scripts):
                if not script.strip():
                    continue
                js = Path(temp) / f"inline_{index}.js"
                js.write_text(script, encoding="utf-8")
                result = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
                self.assertEqual(0, result.returncode, f"{js.name}: {result.stderr[:1000]}")


if __name__ == "__main__":
    unittest.main()

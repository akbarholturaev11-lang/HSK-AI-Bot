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

    def test_panda_stays_visible_until_hsk30_course_map_is_rendered(self):
        switch = self.mini.split("function switchCourseTrack(target,requestedLevel){", 1)[1].split(
            "var HSK30_PROMO_CHECKED", 1
        )[0]
        self.assertIn("showCourseTrackSwitchPreparing(target);", switch)
        self.assertNotIn('COURSE_TRACK_STATE=d;App.closeSheet()', switch)
        self.assertIn("return loadLevel(lv);", switch)

        load = self.mini.split("function loadLevel(lv){", 1)[1].split(
            "function applyLessonDone(", 1
        )[0]
        self.assertIn("if(!res||!res.data)hideCourseTrackSwitchPreparing();", load)
        self.assertIn('renderAll();App.show("course");', load)
        self.assertIn("hideCourseTrackSwitchPreparing();", load)
        self.assertLess(
            load.index('renderAll();App.show("course");'),
            load.index("hideCourseTrackSwitchPreparing();", load.index('renderAll();App.show("course");')),
        )

        self.assertIn("if (state.isSwitchingTrack) {", self.android)
        self.assertIn("LessonEntryOverlay(", self.android)
        self.assertIn("titleRes = R.string.course_track_preparing_title", self.android)

    def test_course_title_opens_bottom_sheet_and_restores_saved_level(self):
        self.assertIn('class="course-heading-button"', self.mini)
        self.assertIn('onclick="App.courseTrackPicker()"', self.mini)
        picker = self.mini.split("function openCourseTrackPicker(){", 1)[0].split(
            "var COURSE_PICKER_STATUS=", 1
        )[1]
        self.assertIn("COURSE_PICKER_LEVEL=coursePickerSavedLevel(track)", picker)
        self.assertIn("switchCourseTrack(track,(track===currentCourseTrack()||level!==saved)?level:null)", picker)
        self.assertIn("course-choice-sheet", picker)
        self.assertIn("showCourseTrackSwitchPreparing(target);", self.mini)

        self.assertIn("CourseChoiceSheet(", self.android)
        self.assertIn("savedLevelHsk20", self.android)
        self.assertIn("savedLevelHsk30", self.android)
        self.assertIn("onOpenCourseChoice()", self.android)

    def test_course_picker_level_buttons_fit_one_row_and_use_hsk_labels(self):
        # Legacy HSK 1–4 and new HSK 1–3 must never wrap into a second row.
        self.assertIn(
            ".course-choice-levels{display:grid;grid-template-columns:repeat(4,minmax(0,1fr))",
            self.mini,
        )
        self.assertIn(
            ".course-choice-levels.three{grid-template-columns:repeat(3,minmax(0,1fr))}",
            self.mini,
        )
        picker = self.mini.split("function renderCoursePicker(){", 1)[1].split(
            "function coursePickerSelectTrack(", 1
        )[0]
        self.assertIn('var name="HSK "+levelBand(lv)', picker)
        self.assertIn('COURSE_PICKER_TRACK==="hsk30"?" three":""', picker)
        self.assertNotIn('?"N":"HSK "', picker)

        native = self.android.split("private fun CourseChoiceSheet(", 1)[1].split(
            "private fun courseLevelLabel(", 1
        )[0]
        self.assertIn('val label = "HSK " + level.removePrefix(', native)
        self.assertIn("compact = true", native)
        self.assertIn("Modifier.weight(1f)", native)
        self.assertIn('fontSize = if (compact) 12.sp else 15.sp', native)
        self.assertIn("if (selected && !compact)", native)

    def test_consistent_hsk_bands_and_rating_only_new_badge(self):
        # Curriculum is carried separately. Learner-facing band labels stay
        # HSK 1..4 / HSK 1..3, with NEW reserved for rating presentation.
        label = self.mini.split("function courseLevelLabel(lv){", 1)[1].split(
            "function ratingLevelLabel(lv){", 1
        )[0]
        rating = self.mini.split("function ratingLevelLabel(lv){", 1)[1].split("/*", 1)[0]
        self.assertIn('return "HSK "+levelBand(', label)
        self.assertNotIn('NEW', label)
        self.assertIn('isHsk30Level(lv)?" NEW":""', rating)
        self.assertIn('ratingLevelLabel(u.level', self.mini)
        self.assertIn('courseLevelLabel((MAP&&MAP.level)||getSelectedLevel())', self.mini)
        self.assertIn('courseLevelLabel(map.level)', self.android)
        self.assertNotIn('"HSK 3.0 · N"', self.android)
        self.assertIn(
            'selectedLevel.takeIf { selectedTrack == activeTrack || it != saved(selectedTrack) }',
            self.android,
        )
        onboard = (ROOT / "app" / "static" / "course_v3_onboarding.html").read_text(encoding="utf-8")
        self.assertNotIn('isHsk30Level(key)?\'<span class="new-tag">NEW', onboard)
        self.assertNotIn('var meta=["NEW"]', onboard)
        self.assertNotIn('var h30Meta=["NEW"]', onboard)
        android_onboard = (ANDROID / "feature" / "onboarding" / "OnboardingScreen.kt").read_text(
            encoding="utf-8"
        )
        self.assertIn('LevelOption("nhsk1", "HSK 1"', android_onboard)
        self.assertNotIn('badge = if (option.isNew) copy.newBadge', android_onboard)

    def test_android_hsk30_book_art_has_native_software_renderer_and_fallback(self):
        # The bundled JPEG must remain visible on OEMs that fail to render the
        # old Compose Multiply tint. Never leave the header as a blank spacer.
        header = (
            ANDROID / "core" / "design" / "components" / "Hsk30BooksHeader.kt"
        ).read_text(encoding="utf-8")
        self.assertIn("AndroidView(", header)
        self.assertIn("ImageView.ScaleType.CENTER_CROP", header)
        self.assertIn("setLayerType(View.LAYER_TYPE_SOFTWARE, null)", header)
        self.assertIn("Hsk30BooksFallback(Modifier.matchParentSize())", header)
        self.assertIn("R.drawable.hsk30_course_books", header)
        self.assertNotIn("ColorFilter.tint", header)

    def test_android_picker_has_no_new_badges_or_secondary_confirm(self):
        picker = self.android.split("internal fun Hsk30LevelChoiceDialog(", 1)[1].split(
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

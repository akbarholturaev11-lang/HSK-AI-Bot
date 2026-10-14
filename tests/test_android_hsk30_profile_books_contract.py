"""Protect native HSK 3.0 entry parity with the Mini App."""
import unittest
from pathlib import Path

SRC = Path("android/app/src/main/java/com/pomp/hskai")
PROFILE = (SRC / "feature/profile/ProfileScreen.kt").read_text(encoding="utf-8")
PROMO = (SRC / "feature/profile/ProfilePromoCarousel.kt").read_text(encoding="utf-8")
COURSE = (SRC / "feature/course/CourseScreen.kt").read_text(encoding="utf-8")

class ProfileHsk30BookFlowTests(unittest.TestCase):
    def test_both_profile_and_settings_open_book_cover(self):
        self.assertIn("ProfileHsk30BookEntryDialog(", PROFILE)
        self.assertIn("profileHsk30BookOpen = true", PROFILE)
        self.assertIn("onOpenCourseVersion = {", PROFILE)
        self.assertNotIn("ProfileHsk30EntryConfirmDialog(", PROFILE)
        self.assertNotIn("CourseVersionPickerSheet(", PROFILE)
        self.assertIn("Hsk30BookDialog(isNew = hsk30.newBadge.isNew", PROMO)
        self.assertIn("Hsk30BookPrice(hsk30.priceDisplay)", PROMO)
        self.assertIn("Hsk30BookPrimary(", PROMO)
        self.assertIn("Hsk30BookSecondary(", PROMO)

    def test_levels_and_payment_rules_remain_server_owned(self):
        self.assertIn('hsk30.hasSavedHsk30 -> onSwitchCourseTrack("hsk30", null)', PROFILE)
        self.assertIn('onSwitchCourseTrack("hsk30", level)', PROFILE)
        self.assertIn("Hsk30LevelChoiceDialog(", PROFILE)
        self.assertIn("hsk30.access.featureEnabled", PROMO)
        self.assertIn("hsk30.access.allowed", PROMO)
        self.assertIn("hsk30.paymentEnabled", PROMO)
        self.assertIn("hsk30.priceTjs > 0", PROMO)
        self.assertIn("onUnlockHsk30()", PROFILE)
        self.assertIn('onSwitchCourseTrack("hsk20", null)', PROFILE)

    def test_course_path_keeps_its_own_compact_picker(self):
        self.assertIn("CourseChoiceSheet(", COURSE)
        self.assertIn("showCourseChoice && hsk30 != null", COURSE)
        self.assertIn("selectedTrack", COURSE)
        self.assertIn("selectedLevel", COURSE)

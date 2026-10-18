"""Contract for option and notification local-first copy; no state changes."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("uz", "ru", "tj")
LEVELS = ("beginner", "hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")
GOALS = ("hsk_exam", "daily_communication", "travel", "work_china", "study_china")
NOTIFICATIONS = {
    "notifyTitle": "title", "notifyLessons": "lessons",
    "notifyUpdates": "updates", "notifyPayments": "payments",
    "notifyAllow": "allow", "notifyLater": "later",
}


def source_catalog(locale):
    return json.loads((ROOT / f"localization/ui/{locale}/course.json").read_text(
        encoding="utf-8"))["messages"]


def localized_values(fragment):
    """Extract reviewed static ru/uz/tj literal triplet, never evaluate JS."""
    result = {}
    for locale in ("ru", "uz", "tj"):
        found = re.search(re.escape(locale) + r':"([^"]+)"', fragment)
        if found is None:
            raise AssertionError(f"Missing {locale} option literal")
        result[locale] = found.group(1)
    return result


class OnboardingOptionsTests(unittest.TestCase):
    def test_hsk_level_options_are_exact_three_locale_copies(self):
        html = (ROOT / "app/static/course_v3_onboarding.html").read_text(
            encoding="utf-8")
        level20 = html.split("var LV20=[", 1)[1].split("];", 1)[0]
        level30 = html.split("var LV30=[", 1)[1].split("];", 1)[0]
        fields = {}
        for level, body in (("beginner", level20),):
            match = re.search(r'\{k:"beginner".*?hd:(\{[^}]+\}),s:(\{[^}]+\})', body, re.S)
            self.assertIsNotNone(match)
            fields["onboardingLevel.beginner.title"] = localized_values(match.group(1))
            fields["onboardingLevel.beginner.subtitle"] = localized_values(match.group(2))
        for source in (level20, level30):
            matches = re.findall(
                r'\{k:"((?:n)?hsk[1-4])".*?,s:(\{[^}]+\})', source)
            for level, desc in matches:
                fields[f"onboardingLevel.{level}.subtitle"] = localized_values(desc)
        self.assertEqual(len(fields), 9)
        for locale in LANGUAGES:
            catalog = source_catalog(locale)
            self.assertEqual(len(catalog), 228)
            for key, values in fields.items():
                with self.subTest(locale=locale, key=key):
                    self.assertEqual(catalog[key], values[locale])

    def test_goals_are_exact_locale_copy_and_selection_ids_unchanged(self):
        html = (ROOT / "app/static/course_v3_onboarding.html").read_text(
            encoding="utf-8")
        source = html.split("var GOALS=[", 1)[1].split("];", 1)[0]
        rows = re.findall(
            r'\{k:"([^"]+)".*?hd:(\{[^}]+\}),\s*s:(\{[^}]+\})', source, re.S)
        self.assertEqual(tuple(row[0] for row in rows), GOALS)
        for goal, title, subtitle in rows:
            for locale in LANGUAGES:
                messages = source_catalog(locale)
                with self.subTest(locale=locale, goal=goal):
                    self.assertEqual(messages[f"onboardingGoal.{goal}.title"],
                                     localized_values(title)[locale])
                    self.assertEqual(messages[f"onboardingGoal.{goal}.subtitle"],
                                     localized_values(subtitle)[locale])
        self.assertIn('GOALS.some(function(o){return o.k===savedGoal})', html)
        self.assertIn('goal:goalSel', html)
        self.assertIn('level:sel', html)
        self.assertIn('adoptOnboardingOptionCopy();', html)
        self.assertIn('item.hd[LANG]=onboardingOptionMessage("onboardingGoal."+item.k+".title"', html)
        self.assertIn('item.s[LANG]=onboardingOptionMessage("onboardingGoal."+item.k+".subtitle"', html)
        self.assertIn('item.s[LANG]=onboardingOptionMessage("onboardingLevel."+item.k+".subtitle"', html)
        self.assertIn('onboardingOptionMessage("onboardingLevel.beginner.title"', html)
        self.assertIn('hsk-course-i18n.js?v=20261018-onboarding-options-v12', html)
        self.assertNotIn('fetch("/api/i18n/', html)

    def test_android_notification_strings_match_exact_native_fallbacks(self):
        native = (ROOT / "android/app/src/main/java/com/pomp/hskai/feature/onboarding/OnboardingScreen.kt").read_text(
            encoding="utf-8")
        parts = {
            "uz": native.split('"uz" -> OnboardingCopy(', 1)[1].split(")", 1)[0],
            "tj": native.split('"tg", "tj" -> OnboardingCopy(', 1)[1].split(")", 1)[0],
            "ru": native.split("else -> OnboardingCopy(", 1)[1].split(")", 1)[0],
        }
        lookups = native.split("private fun OnboardingCopy.withBundledCatalog(", 1)[1].split(
            "\n@Composable", 1)[0]
        for field, name in NOTIFICATIONS.items():
            expected = (
                field + " = localized.getString(R.string.hsk_course_onboarding_notification_"
                + name + ")"
            )
            self.assertEqual(lookups.count(expected), 1)
            for locale in LANGUAGES:
                match = re.search(r"\b" + re.escape(field) + r' = "([^"]+)"', parts[locale])
                self.assertIsNotNone(match)
                self.assertEqual(
                    source_catalog(locale)["onboardingNotification." + name],
                    match.group(1),
                )
        self.assertIn("config.setLocale(Locale.forLanguageTag(canonicalLanguage(language)))", native)
        self.assertIn("}.getOrDefault(this)", native)


if __name__ == "__main__":
    unittest.main()

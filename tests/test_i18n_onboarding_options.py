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
            self.assertEqual(len(catalog), 810)
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
            goal_key = re.sub(r"_([a-z])", lambda match: match.group(1).upper(), goal)
            for locale in LANGUAGES:
                messages = source_catalog(locale)
                with self.subTest(locale=locale, goal=goal):
                    self.assertEqual(messages[f"onboardingGoal.{goal_key}.title"],
                                     localized_values(title)[locale])
                    self.assertEqual(messages[f"onboardingGoal.{goal_key}.subtitle"],
                                     localized_values(subtitle)[locale])
        self.assertIn('GOALS.some(function(o){return o.k===savedGoal})', html)
        self.assertIn('goal:goalSel', html)
        self.assertIn('level:sel', html)
        self.assertIn('adoptOnboardingOptionCopy();', html)
        self.assertIn("function onboardingGoalCatalogId(id){", html)
        self.assertIn('item.hd[LANG]=onboardingOptionMessage("onboardingGoal."+onboardingGoalCatalogId(item.k)+".title"', html)
        self.assertIn('item.s[LANG]=onboardingOptionMessage("onboardingGoal."+onboardingGoalCatalogId(item.k)+".subtitle"', html)
        self.assertIn('item.s[LANG]=onboardingOptionMessage("onboardingLevel."+item.k+".subtitle"', html)
        self.assertIn('onboardingOptionMessage("onboardingLevel.beginner.title"', html)
        self.assertIn('hsk-course-i18n.js?v=20261018-onboarding-options-v12', html)
        self.assertNotIn('fetch("/api/i18n/', html)

    def test_android_notification_strings_match_exact_native_fallbacks(self):
        native = (ROOT / "android/app/src/main/java/com/pomp/hskai/feature/onboarding/OnboardingScreen.kt").read_text(
            encoding="utf-8")
        primer = (ROOT / "android/app/src/main/java/com/pomp/hskai/feature/onboarding/NotificationPrimerScreen.kt").read_text(
            encoding="utf-8")
        parts = {
            "uz": native.split('"uz" -> OnboardingCopy(', 1)[1].split(")", 1)[0],
            "tj": native.split('"tg", "tj" -> OnboardingCopy(', 1)[1].split(")", 1)[0],
            "ru": native.split("else -> OnboardingCopy(", 1)[1].split(")", 1)[0],
        }
        lookups = native.split("fun OnboardingCopy.withBundledCatalog(", 1)[1].split(
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
        self.assertIn("OnboardingCopy.forLanguage(language).withBundledCatalog(context, language)", primer)
        self.assertIn("val context = LocalContext.current", primer)

    def test_android_only_active_onboarding_copy_uses_local_catalog(self):
        native = (ROOT / "android/app/src/main/java/com/pomp/hskai/feature/onboarding/OnboardingScreen.kt").read_text(
            encoding="utf-8")
        parts = {
            "uz": native.split('"uz" -> OnboardingCopy(', 1)[1].split(")", 1)[0],
            "tj": native.split('"tg", "tj" -> OnboardingCopy(', 1)[1].split(")", 1)[0],
            "ru": native.split("else -> OnboardingCopy(", 1)[1].split(")", 1)[0],
        }
        lookups = native.split("fun OnboardingCopy.withBundledCatalog(", 1)[1].split(
            "\n@Composable", 1)[0]
        fields = ("beginner", "beginnerSub", "saveError")
        for field in fields:
            resource_name = re.sub(r"(?<!^)(?=[A-Z])", "_", field).lower()
            lookup = (
                field + " = localized.getString(R.string.hsk_course_android_onboarding_"
                + resource_name + ")"
            )
            self.assertEqual(lookups.count(lookup), 1)
            for locale in LANGUAGES:
                match = re.search(r"\b" + re.escape(field) + r' = "([^"]+)"', parts[locale])
                self.assertIsNotNone(match)
                catalog = source_catalog(locale)
                self.assertEqual(
                    catalog["androidOnboarding." + field], match.group(1),
                )


    def test_android_17_reviewed_option_resources_used_by_compose(self):
        native = (ROOT / "android/app/src/main/java/com/pomp/hskai/feature/onboarding/OnboardingScreen.kt").read_text(encoding="utf-8")
        level_keys = ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")
        for level in level_keys:
            self.assertIn(f'"{level}" to R.string.hsk_course_onboarding_level_{level}_subtitle,', native)
        for goal in GOALS:
            self.assertIn(f'"{goal}" to Pair(', native)
            for suffix in ("title", "subtitle"):
                self.assertIn(f"R.string.hsk_course_onboarding_goal_{goal}_{suffix}", native)
        self.assertIn("private fun Context.bundledOnboardingOptions(language: String)", native)
        self.assertIn("config.setLocale(Locale.forLanguageTag(canonicalLanguage(language)))", native)
        self.assertIn("runCatching { optionContext?.getString(resourceId) }.getOrNull()", native)
        self.assertIn("} ?: option.subtitle,", native)
        self.assertIn('} ?: (goal.titles[lang] ?: goal.titles.getValue("ru")),', native)
        self.assertIn('} ?: (goal.subtitles[lang] ?: goal.subtitles.getValue("ru")),', native)
        self.assertIn("onClick = { onSelected(option.key) }", native)
        self.assertIn("onClick = { onSelected(goal.key) }", native)

    def test_android_option_fallback_parity_for_all_three_locales(self):
        native = (ROOT / "android/app/src/main/java/com/pomp/hskai/feature/onboarding/OnboardingScreen.kt").read_text(encoding="utf-8")
        rows = re.findall(
            r'GoalOption\(\s*"([^"]+)",\s*'
            r'mapOf\("uz" to "([^"]+)", "ru" to "([^"]+)", "tg" to "([^"]+)"\),\s*'
            r'mapOf\("uz" to "([^"]+)", "ru" to "([^"]+)", "tg" to "([^"]+)"\)',
            native)
        self.assertEqual(len(rows), 5)
        for key, u_t, r_t, t_t, u_s, r_s, t_s in rows:
            canonical = re.sub(r"_([a-z])", lambda m: m.group(1).upper(), key)
            for locale, title, subtitle in (("uz", u_t, u_s),
                                            ("ru", r_t, r_s),
                                            ("tj", t_t, t_s)):
                self.assertEqual(source_catalog(locale)[f"onboardingGoal.{canonical}.title"], title)
                self.assertEqual(source_catalog(locale)[f"onboardingGoal.{canonical}.subtitle"], subtitle)
        for anchor, keys in (
            ("val descriptions = when (lang) {", ("hsk1", "hsk2", "hsk3", "hsk4")),
            ("val hsk30Descriptions = when (lang) {", ("nhsk1", "nhsk2", "nhsk3")),
        ):
            region = native.split(anchor, 1)[1].split("}", 1)[0]
            groups = re.findall(r'("uz"|"tg"|else) -> listOf\(([^)]+)\)', region)
            self.assertEqual(len(groups), 3)
            for lang, values in groups:
                locale = {"\"uz\"": "uz", "\"tg\"": "tj", "else": "ru"}[lang]
                originals = re.findall(r'"([^"]+)"', values)
                self.assertEqual(len(originals), len(keys))
                for key, value in zip(keys, originals):
                    self.assertEqual(source_catalog(locale)[f"onboardingLevel.{key}.subtitle"], value)


if __name__ == "__main__":
    unittest.main()

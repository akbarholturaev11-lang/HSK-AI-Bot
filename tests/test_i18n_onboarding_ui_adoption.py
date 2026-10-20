"""Static regression contract for 31 exact three-locale onboarding UI labels."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ("uz", "ru", "tj")
FIELDS = ("hello", "boot", "ask", "levelHint", "askVersion", "onlyHsk20", "versionHint", "books20", "books30", "start", "cont", "first", "retry", "askGoal", "goalHint", "welcomeNote", "levelNote", "goalNote", "back", "progress", "saving", "saveError", "authError", "levelError", "beginner", "beginnerSub", "selected", "courseVersion", "hsk20", "hsk30", "hsk30Disabled",)


class OnboardingCourseCatalogTests(unittest.TestCase):
    def test_31_original_ui_labels_match_generated_source_in_every_locale(self):
        html = (ROOT / "app/static/course_v3_onboarding.html").read_text(encoding="utf-8")
        block = html.split("var ONBOARDING_LEGACY={", 1)[1].split("}[LANG];", 1)[0]
        self.assertEqual(len(FIELDS), 31)
        for locale in LOCALES:
            with self.subTest(locale=locale):
                line = next(line for line in block.splitlines()
                            if line.strip().startswith(locale + ":{"))
                found = dict(re.findall(r'([A-Za-z][A-Za-z0-9]*):"([^"]*)"', line))
                self.assertEqual(set(found), set(FIELDS))
                catalog = json.loads(
                    (ROOT / f"localization/ui/{locale}/course.json").read_text(
                        encoding="utf-8"))["messages"]
                self.assertEqual(len(catalog), 895)
                for key in FIELDS:
                    self.assertEqual(catalog["onboarding." + key],
                                     json.loads('"' + found[key] + '"'))

    def test_bundle_loads_before_original_fallback_and_preserves_flow(self):
        html = (ROOT / "app/static/course_v3_onboarding.html").read_text(encoding="utf-8")
        self.assertEqual(html.count("var ONBOARDING_LEGACY={"), 1)
        self.assertLess(html.index("hsk-course-i18n.js?v=20261020-57ce728d755d"),
                        html.index("var ONBOARDING_LEGACY={"))
        self.assertIn('ONBOARDING_CATALOG["onboarding."+key]', html)
        self.assertIn('L[key]=typeof value==="string"&&value?value:ONBOARDING_LEGACY[key]', html)
        self.assertNotIn('fetch("/api/i18n/', html)
        for anchor in (
            "function onboardingPayload(){",
            "function trackOnboardingEvent(event,payload){",
            "function hsk30Enabled(){",
            "function hsk30PaymentEnabled(){",
            "function nextBtn(){",
            'postJson("/api/miniapp/onboarding",payload,controller?controller.signal:undefined,false)',
        ):
            self.assertIn(anchor, html)

    def test_browser_outputs_are_identical_static_bundles(self):
        mini = (ROOT / "app/static/course_v3_data/hsk-course-i18n.js").read_text(
            encoding="utf-8")
        desk = (ROOT / "desktop/ui/js/generated/hsk-course-i18n.js").read_text(
            encoding="utf-8")
        self.assertEqual(mini, desk)
        self.assertNotIn("fetch(", mini)
        for key in FIELDS:
            self.assertIn('"onboarding.' + key + '"', mini)


    def test_android_runtime_uses_23_exact_reviewed_onboarding_strings(self):
        native = (ROOT / "android/app/src/main/java/com/pomp/hskai/feature/onboarding/OnboardingScreen.kt").read_text(
            encoding="utf-8")
        fields = {
            "hello": "hello",
            "boot": "boot",
            "askLevel": "ask",
            "levelHint": "levelHint",
            "askVersion": "askVersion",
            "hsk20BooksDescription": "books20",
            "hsk30BooksDescription": "books30",
            "start": "start",
            "continueLabel": "cont",
            "firstLesson": "first",
            "retry": "retry",
            "askGoal": "askGoal",
            "goalHint": "goalHint",
            "welcomeNote": "welcomeNote",
            "levelNote": "levelNote",
            "goalNote": "goalNote",
            "back": "back",
            "saving": "saving",
            "selected": "selected",
            "courseVersion": "courseVersion",
            "hsk20": "hsk20",
            "hsk30": "hsk30",
            "hsk30Disabled": "hsk30Disabled",
        }
        self.assertEqual(len(fields), 23)
        self.assertIn("LocalContext.current", native)
        self.assertIn("OnboardingCopy.forLanguage(language).withBundledCatalog(context, language)", native)
        self.assertIn("config.setLocale(Locale.forLanguageTag(canonicalLanguage(language)))", native)
        self.assertIn("context.createConfigurationContext(config)", native)
        self.assertIn("}.getOrDefault(this)", native)
        bodies = {
            "uz": native.split('"uz" -> OnboardingCopy(', 1)[1].split(")", 1)[0],
            "tj": native.split('"tg", "tj" -> OnboardingCopy(', 1)[1].split(")", 1)[0],
            "ru": native.split("else -> OnboardingCopy(", 1)[1].split(")", 1)[0],
        }
        for locale in LOCALES:
            values = dict(re.findall(r'([A-Za-z][A-Za-z0-9]*) *= *"([^"]*)"', bodies[locale]))
            catalog = json.loads((ROOT / f"localization/ui/{locale}/course.json")
                                 .read_text(encoding="utf-8"))["messages"]
            for field, key in fields.items():
                with self.subTest(locale=locale, field=field):
                    self.assertEqual(values[field], catalog["onboarding." + key])
        lookups = native.split("fun OnboardingCopy.withBundledCatalog(", 1)[1].split(
            "\n@Composable", 1)[0]
        for field, key in fields.items():
            resource_key = "hsk_course_onboarding_" + re.sub(
                r"(?<!^)(?=[A-Z])", "_", key).lower()
            self.assertIn(
                field + " = localized.getString(R.string." + resource_key + ")", lookups)
        for skipped in ("versionHint",):
            self.assertNotIn(skipped + " = localized.getString", lookups)

if __name__ == "__main__":
    unittest.main()

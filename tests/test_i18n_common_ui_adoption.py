"""No-regression source checks for the first common UI runtime adoption.

Source-only guard; actual WebView/Android/desktop visual QA is deferred until
all localization code is implemented and a controlled test cycle begins.
"""
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from scripts.i18n_baseline_guard import git_blob_sha1

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "localization/baselines/reviewed_ui_changes.json"


class ReviewedCommonUIAdoptionTests(unittest.TestCase):
    def test_exact_approved_original_and_new_ui_blobs(self):
        approved = json.loads(REVIEW.read_text(encoding="utf-8"))
        baseline = json.loads((ROOT / "localization/baselines/source_git_blobs.json")
                              .read_text(encoding="utf-8"))
        self.assertEqual(set(approved["files"]), {
            "desktop/ui/js/i18n.js", "app/static/course-v3.html",
            "app/bot/utils/i18n.py",
        })
        self.assertEqual(approved["baseline_main_commit"],
                         baseline["baseline_main_commit"])
        old_by_path = {
            entry["path"]: entry["git_blob_sha1"]
            for group in baseline["sources"].values() for entry in group
        }
        for name, note in approved["files"].items():
            with self.subTest(path=name):
                self.assertEqual(note["baseline_sha1"], old_by_path[name])
                self.assertEqual(note["reviewed_sha1"],
                                 git_blob_sha1((ROOT / name).read_bytes()))
                self.assertNotEqual(note["reviewed_sha1"],
                                    note["baseline_sha1"])
                self.assertTrue(note["reason"])

    def test_desktop_adopts_generated_values_but_keeps_old_fallback(self):
        source = (ROOT / "desktop/ui/js/i18n.js").read_text(encoding="utf-8")
        self.assertIn('import "./generated/hsk-common-i18n.js";', source)
        self.assertIn("const SHARED_COMMON_KEY = Object.freeze({", source)
        self.assertIn("window.HSKAI_COMMON_I18N", source)
        self.assertIn("const template = generated ??", source)
        self.assertIn("messages[activeLanguage]?.[key] ?? messages.uz[key]", source)
        for key in ["course", "practice", "profile", "rating",
                    "subscription", "startLesson", "continueLesson",
                    "lockedLesson", "courseEmpty", "refresh", "authExpires"]:
            self.assertIn(key + ":", source)
        self.assertNotIn("/api/i18n/", source)

    def test_miniapp_loads_only_static_local_ui_bundle(self):
        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertIn(
            '<script src="/course_v3_data/hsk-common-i18n.js?v=20261017-common-v1"></script>',
            html,
        )
        self.assertLess(html.index("hsk-common-i18n.js"),
                        html.index("function commonMessage("))
        self.assertIn("window.HSKAI_COMMON_I18N", html)
        self.assertIn('commonMessage("navigation.rating",', html)
        self.assertIn('LANG==="ru"?"Рейтинг":LANG==="tj"?"Рейтинг":"Reyting"', html)
        self.assertNotIn('fetch("/api/i18n/', html)

    def test_android_navigation_resources_same_as_legacy_in_all_locales(self):
        kotlin = (ROOT / "android/app/src/main/java/com/pomp/hskai/core/navigation/MainScaffold.kt"
                  ).read_text(encoding="utf-8")
        names = ("course", "practice", "rating", "profile")
        for key in names:
            self.assertIn("R.string.hsk_common_navigation_" + key, kotlin)
        for suffix in ("", "-ru", "-tg"):
            with self.subTest(qualifier=suffix):
                root = ROOT / "android/app/src/main/res"
                original = ET.parse(root / f"values{suffix}/strings.xml").getroot()
                generated = ET.parse(root / f"values{suffix}/hsk_common_i18n.xml").getroot()
                old = {e.attrib["name"]: e.text for e in original.findall("string")}
                new = {e.attrib["name"]: e.text for e in generated.findall("string")}
                for key in names:
                    self.assertEqual(
                        new["hsk_common_navigation_" + key],
                        old["nav_" + key],
                    )

    def test_bot_common_namespace_is_local_and_preserves_legacy_translation(self):
        from app.bot.utils.i18n import t

        self.assertEqual(t("common.navigation.course", lang="uz"), "Kurs")
        self.assertEqual(t("common.navigation.practice", lang="ru"), "Практика")
        self.assertEqual(t("common.navigation.profile", lang="tj"), "Профил")
        self.assertEqual(t("common.navigation.profile", lang="tg"), "Профил")
        self.assertEqual(t("common.auth.expires", lang="ru", time="5 min"),
                         "Код действует ещё 5 min")
        self.assertEqual(t("common.not_approved", lang="uz"),
                         "common.not_approved")
        self.assertEqual(t("welcome", lang="uz", name="QA"), "Xush kelibsiz, QA!")

    def test_platform_bundles_contain_only_ui_not_lessons_or_entitlements(self):
        for file in (
            "desktop/ui/js/generated/hsk-common-i18n.js",
            "app/static/course_v3_data/hsk-common-i18n.js",
        ):
            text = (ROOT / file).read_text(encoding="utf-8")
            self.assertNotIn("correct_index", text)
            self.assertNotIn("answer_key", text)
            self.assertNotIn("/course_v3_data/hsk1/lesson_", text)
            self.assertNotIn("fetch(", text)
            self.assertNotIn("BOT_TOKEN", text)


    def test_miniapp_course_reviewed_profile_settings_copy(self):
        """Four unchanged translations / five display points, one static asset."""
        import re

        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertEqual(html.count(
            '<script src="/course_v3_data/hsk-course-i18n.js?v=20261017-course-v1"></script>'
        ), 1)
        self.assertLess(html.index("hsk-course-i18n.js"),
                        html.index("function courseMessage("))
        self.assertIn("window.HSKAI_COURSE_I18N", html)
        self.assertEqual(html.count('courseMessage("lang",t.lang)'), 2)
        self.assertEqual(html.count('courseMessage("notif",t.notif)'), 1)
        self.assertEqual(html.count('esc(courseMessage("friends",t.friends))'), 1)
        self.assertEqual(html.count('esc(courseMessage("helpTitle",t.helpTitle))'), 1)
        self.assertIn('catalog&&catalog[LANG]&&Object.prototype.hasOwnProperty.call(catalog[LANG],key)?catalog[LANG][key]:fallback', html)
        self.assertNotIn("fetch('/api/i18n/", html)
        self.assertNotIn('fetch("/api/i18n/', html)
        # Validate generated values against the actual original inline UI copy,
        # rather than relying on the extracted JSON alone.
        legacy = {
            "ru": html.splitlines()[1478],
            "uz": html.splitlines()[1479],
            "tj": html.splitlines()[1480],
        }
        for locale, inline in legacy.items():
            catalog = json.loads(
                (ROOT / f"localization/ui/{locale}/course.json").read_text(encoding="utf-8")
            )["messages"]
            for key in ("lang", "notif", "friends", "helpTitle"):
                with self.subTest(locale=locale, key=key):
                    found = re.search(r"(?:^|[,{}])" + re.escape(key) + r':"([^"]*)"', inline)
                    self.assertIsNotNone(found)
                    self.assertEqual(found.group(1), catalog[key])
        # Quiz, premium and account-state copy is deliberately not routed by
        # this very small profile/settings migration.
        self.assertNotIn('courseMessage("trialLeft"', html)
        self.assertNotIn('courseMessage("correct"', html)

    def test_miniapp_reviewed_practice_voice_help_copy(self):
        """Reviewed 24 catalog keys retain exact legacy text and local fallbacks."""
        import re

        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertEqual(len(html.splitlines()), 8712)
        expected_sites = {
        "dict": 1,
        "dictSub": 1,
        "grammar": 2,
        "help": 1,
        "helpBtn": 1,
        "helpNoContact": 1,
        "helpText": 1,
        "mashqSub": 1,
        "mistakes": 2,
        "mistakesSub": 1,
        "nav.mashq": 1,
        "nav.profile": 1,
        "pron": 3,
        "pronSub": 1,
        "readyPhrases": 1,
        "readyPhrasesSub": 1,
        "recog": 1,
        "recogSub": 1,
        "streak": 1,
        "testCenter": 3,
        "testSub": 1,
        "voiceStart": 1,
        "voiceSub": 1,
        "voiceTitle": 1
}
        for key, count in expected_sites.items():
            with self.subTest(ui_key=key):
                self.assertEqual(html.count('courseMessage("' + key + '",'), count)
        # All selected values match the three current, unchanged inline catalogs.
        lines = html.splitlines()
        legacy = {"ru": lines[1478], "uz": lines[1479], "tj": lines[1480]}
        for locale, source in legacy.items():
            catalog = json.loads(
                (ROOT / f"localization/ui/{locale}/course.json").read_text(encoding="utf-8")
            )["messages"]
            for key in expected_sites:
                with self.subTest(locale=locale, key=key):
                    field = key.split(".", 1)[1] if key.startswith("nav.") else key
                    section = (re.search(r"nav:\{([^}]+)\}", source).group(1)
                               if key.startswith("nav.") else source)
                    match = re.search(r"(?:^|[,{}])" + re.escape(field) + r':"([^"]*)"', section)
                    self.assertIsNotNone(match)
                    self.assertEqual(match.group(1), catalog[key])
        self.assertIn('window.HSKAI_COURSE_I18N', html)
        self.assertIn('return catalog&&catalog[LANG]&&Object.prototype.hasOwnProperty.call(catalog[LANG],key)?catalog[LANG][key]:fallback', html)
        for forbidden in ('courseMessage("correct"', 'courseMessage("wrong"',
                          'courseMessage("trialLeft"', 'courseMessage("payTitle"'):
            self.assertNotIn(forbidden, html)


if __name__ == "__main__":
    unittest.main()

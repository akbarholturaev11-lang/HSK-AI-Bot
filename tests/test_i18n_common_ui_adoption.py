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
            "app/static/course_v3_onboarding.html",
            "app/static/course_v3_test.html",
            "app/static/course_v3_recognition.html",
            "app/static/course_v3_mistakes.html",
            "app/static/course_v3_pronunciation.html",
            "app/static/course_v3_voice.html",
            "app/static/course_v3_memorize.html",
            "app/static/hsk-lugat.html",
            "app/static/hsk-gaplar.html",
            "app/static/desktop-download.html",
            "app/static/subscription.html",
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
                    "lockedLesson", "courseEmpty", "refresh", "authExpires",
                    "authReferralCode",
                    "authReferralHint",
                    "authReferralInvalid",
                    "authTitle",
                    "authDescription",
                    "authCodeLabel",
                    "authStart",
                    "authGoogle",
                    "authApple",
                    "authProviderWaiting",
                    "authProviderFailed",
                    "authOpen",
                    "authRetry",
                    "authStep1",
                    "authStep2",
                    "authStep3",
                    "authExpired",
                    "authCancelled",
                    "authWaiting",
                    "authTelegramOpened",
                    "authStarting",
                    "authLinked",
                    "copyCode",
                    "copied"]:
            self.assertIn(key + ":", source)
        self.assertNotIn("/api/i18n/", source)

    def test_miniapp_loads_only_static_local_ui_bundle(self):
        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertIn(
            '<script src="/course_v3_data/hsk-common-i18n.js?v=20261019-android-common-v2"></script>',
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
                         "На подтверждение входа осталось 5 min")
        self.assertEqual(t("common.not_approved", lang="uz"),
                         "common.not_approved")
        self.assertEqual(t("welcome", lang="uz", name="QA"), "Xush kelibsiz, QA!")

    def test_bot_shared_navigation_aliases_use_exact_local_catalog_values(self):
        from app.bot.generated.common_i18n import COMMON_MESSAGES
        from app.bot.generated.course_i18n import COURSE_MESSAGES
        from app.bot.utils.i18n import (
            BOT_SHARED_COMMON_KEYS, BOT_SHARED_COURSE_KEYS, TEXTS, t,
        )

        expected_common = {
            "hint_section_course_title": "navigation.course",
            "hint_section_practice_title": "navigation.practice",
            "hint_section_profile_title": "navigation.profile",
            "hint_section_rating_title": "navigation.rating",
        }
        expected_course = {"hint_section_voice_title": "nav.voice"}
        self.assertEqual(BOT_SHARED_COMMON_KEYS, expected_common)
        self.assertEqual(BOT_SHARED_COURSE_KEYS, expected_course)
        for bot_key, catalog_key, catalog in (
            *((key, value, COMMON_MESSAGES) for key, value in expected_common.items()),
            *((key, value, COURSE_MESSAGES) for key, value in expected_course.items()),
        ):
            for locale in ("uz", "ru", "tj"):
                with self.subTest(bot_key=bot_key, locale=locale):
                    self.assertEqual(
                        catalog[locale][catalog_key],
                        TEXTS[locale][bot_key],
                    )
                    self.assertEqual(t(bot_key, lang=locale), TEXTS[locale][bot_key])
        # An unrelated Bot hint remains owned by the legacy Bot table.
        self.assertEqual(t("hint_section_course_body", lang="uz"),
                         TEXTS["uz"]["hint_section_course_body"])

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
            '<script src="/course_v3_data/hsk-course-i18n.js?v=20261020-eaff685fb700"></script>'
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
            "ru": html.splitlines()[1494],
            "uz": html.splitlines()[1495],
            "tj": html.splitlines()[1496],
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
        self.assertNotIn('courseMessage("answer_key"', html)
        self.assertNotIn('courseMessage("correct_index"', html)

    def test_miniapp_reviewed_practice_voice_help_copy(self):
        """Reviewed 24 catalog keys retain exact legacy text and local fallbacks."""
        import re

        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertEqual(len(html.split("\n")), 8859)
        expected_sites = {
        "dict": 1,
        "dictSub": 1,
            "grammar": 3,
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
        legacy = {"ru": lines[1494], "uz": lines[1495], "tj": lines[1496]}
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
        for forbidden in ('courseMessage("answer_key"', 'courseMessage("correct_index"',
                          'courseMessage("payment_status"', 'courseMessage("is_paid"'):
            self.assertNotIn(forbidden, html)


    def test_miniapp_course_map_lesson_sheet_and_navigation_copy(self):
        """Lesson navigation labels use static local UI with exact fallback."""
        import re

        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertEqual(len(html.split("\n")), 8859)
        expected_counts = {
            "unit": 1, "lessons": 1, "cont": 6, "repeat": 1,
            "stage": 1, "completeOf": 1,
        }
        for key, count in expected_counts.items():
            with self.subTest(key=key):
                self.assertEqual(html.count(
                    'courseMessage("' + key + '",T().' + key + ')'
                ), count)
        self.assertEqual(
            html.count('courseMessage("nav."+st.s,T().nav[st.s])'), 1
        )
        self.assertEqual(
            html.count('courseMessage("nav."+s.dataset.i,T().nav[s.dataset.i])'), 1
        )
        legacy = {
            "ru": html.splitlines()[1494], "uz": html.splitlines()[1495],
            "tj": html.splitlines()[1496],
        }
        nav_keys = ("nav.course", "nav.mashq", "nav.profile",
                    "nav.rating", "nav.voice")
        for locale, source in legacy.items():
            catalog = json.loads(
                (ROOT / f"localization/ui/{locale}/course.json").read_text(
                    encoding="utf-8")
            )["messages"]
            for key in (*expected_counts, *nav_keys):
                with self.subTest(locale=locale, key=key):
                    attr = key.split(".", 1)[1] if key.startswith("nav.") else key
                    section = (re.search(r"nav:\{([^}]+)\}", source).group(1)
                               if key.startswith("nav.") else source)
                    found = re.search(r"(?:^|[,{}])" + re.escape(attr) + r':"([^"]*)"', section)
                    self.assertIsNotNone(found)
                    self.assertEqual(found.group(1), catalog[key])
        self.assertIn('return catalog&&catalog[LANG]&&Object.prototype.hasOwnProperty.call(catalog[LANG],key)?catalog[LANG][key]:fallback', html)
        self.assertIn('if(isPremiumLocked(l)){openLockedLessonSheet(idx);return}', html)
        self.assertNotIn('courseMessage("answer_key"', html)
        self.assertNotIn('courseMessage("correct_index"', html)


    def test_miniapp_reviewed_presentation_and_exercise_copy(self):
        """11 static display keys, 23 sites, with exact UZ/RU/TJ fallback parity."""
        import re

        source = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertEqual(len(source.split("\n")), 8859)
        selections = {
            "buildSent": 1, "dialog": 1, "listen": 2, "matchPairs": 1,
            "say": 5, "check": 2, "next": 2, "rightAns": 1,
            "you": 4,
        }
        for key, count in selections.items():
            with self.subTest(ui_key=key, expression="T"):
                self.assertEqual(source.count(
                    'courseMessage("' + key + '",T().' + key + ')'
                ), count)
        for key, count in {"you": 2, "league": 1, "xp": 1}.items():
            with self.subTest(ui_key=key, expression="t"):
                self.assertEqual(source.count(
                    'courseMessage("' + key + '",t.' + key + ')'
                ), count)

        old_copy = {"ru": source.splitlines()[1494],
                    "uz": source.splitlines()[1495],
                    "tj": source.splitlines()[1496]}
        for locale, line in old_copy.items():
            reviewed = json.loads((ROOT / f"localization/ui/{locale}/course.json")
                                  .read_text(encoding="utf-8"))["messages"]
            for key in (*selections, "league", "xp"):
                with self.subTest(lang=locale, ui_key=key):
                    found = re.search(r"(?:^|[,{}])" + re.escape(key)
                                      + r':"([^"]*)"', line)
                    self.assertIsNotNone(found)
                    self.assertEqual(found.group(1), reviewed[key])

        # The read-only static lookups are for display text only.
        # Business-state / grading branches and user entitlements remain as-is.
        for untouched in ('Flow.answered=true', 'Flow.graded=',
                          'c.correct_index', 'if(isPremiumLocked(l))',
                          '/api/voice-practice/pronounce'):
            self.assertIn(untouched, source)
        for forbidden in ('courseMessage("answer_key"', 'courseMessage("correct_index"',
                          'courseMessage("payment_status"', 'courseMessage("is_paid"'):
            self.assertNotIn(forbidden, source)


    def test_miniapp_reviewed_plan_trial_and_paywall_display_copy(self):
        """Only text lookup changes: preserve trial and paywall decision branches."""
        import re

        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertEqual(len(html.split("\n")), 8859)
        expected = {
            "planTitle": 1, "planBody": 1, "planPay": 1, "planFree": 1,
            "trialOn": 1, "trialFail": 2, "trialCta": 2,
            "paySub": 1, "subscribe": 1,
        }
        for key, count in expected.items():
            with self.subTest(key=key):
                self.assertEqual(html.count('courseMessage("' + key + '",'), count)
        for locale, line_no in (("ru", 1494), ("uz", 1495), ("tj", 1496)):
            old_copy = html.splitlines()[line_no]
            catalog = json.loads((ROOT / f"localization/ui/{locale}/course.json")
                                 .read_text(encoding="utf-8"))["messages"]
            for key in expected:
                with self.subTest(locale=locale, key=key):
                    found = re.search(r"(?:^|[,{}])" + re.escape(key) + r':"([^"]*)"',
                                      old_copy)
                    self.assertIsNotNone(found)
                    self.assertEqual(found.group(1), catalog[key])
        self.assertIn('if(isPaidUser())return;', html)
        self.assertIn('if(!TRIAL_STATE||!TRIAL_STATE.eligible)return;', html)
        self.assertIn('!isLimitPaywallContext(ctx)&&trialEligible()', html)
        self.assertIn('isLimitPaywallContext(ctx)?', html)
        for forbidden in ('courseMessage("answer_key"', 'courseMessage("correct_index"',
                          'courseMessage("payment_status"', 'courseMessage("is_paid"'):
            self.assertNotIn(forbidden, html)


    def test_miniapp_reviewed_feedback_and_trial_countdown_copy(self):
        """Static UI labels change without grading, timer or paywall decisions."""
        import re

        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertEqual(len(html.split("\n")), 8859)
        from_global = {"correct": 9, "wrong": 6}
        from_local = {
            "trialLeft": 1, "trialLeftHours": 1, "trialLeftSoon": 2,
            "lockedLesson": 1, "payTitle": 1,
        }
        for key, count in from_global.items():
            with self.subTest(key=key, source="T"):
                self.assertEqual(html.count(
                    'courseMessage("' + key + '",T().' + key + ')'
                ), count)
        for key, count in from_local.items():
            with self.subTest(key=key, source="t"):
                self.assertEqual(html.count(
                    'courseMessage("' + key + '",t.' + key + ')'
                ), count)
        for locale, index in (("ru", 1494), ("uz", 1495), ("tj", 1496)):
            inline = html.splitlines()[index]
            msgs = json.loads(
                (ROOT / f"localization/ui/{locale}/course.json").read_text(
                    encoding="utf-8")
            )["messages"]
            for key in (*from_global, *from_local):
                with self.subTest(locale=locale, key=key):
                    found = re.search(r"(?:^|[,{}])" + re.escape(key)
                                      + r':"([^"]*)"', inline)
                    self.assertIsNotNone(found)
                    self.assertEqual(msgs[key], found.group(1))
                    if "{n}" in msgs[key]:
                        self.assertEqual(msgs[key].count("{n}"), 1)
        for preserved in (
            'var ok=k===c.correct_index',
            'Flow.correct=(Flow.correct||0)+1',
            'if(!ok)rememberLessonMistake(c,',
            'if(!(ms>0))',
            'if(ms>86400000)',
            'if(hours<1)',
            'return ctx==="lockedLesson"?',
        ):
            self.assertIn(preserved, html)
        for forbidden in ('courseMessage("answer_key"',
                          'courseMessage("correct_index"',
                          'courseMessage("payment_status"',
                          'courseMessage("is_paid"'):
            self.assertNotIn(forbidden, html)


    def test_miniapp_profile_copy_moves_from_inline_to_local_catalog(self):
        """Seven existing profile labels gain local source keys with exact copy."""
        import re

        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertEqual(len(html.split("\n")), 8859)
        body = html.split("function profileCopy(){", 1)[1].split(
            "function loadProfileDetail(){", 1
        )[0]
        self.assertIn("var legacy=({", body)
        self.assertIn("})[LANG]||{};return {", body)
        fields = ("free", "trial", "today", "overall", "pro", "answers", "note")
        for name in fields:
            self.assertEqual(
                body.count('courseMessage("profile.' + name + '",legacy.' + name + ')'), 1
            )
        for locale in ("uz", "ru", "tj"):
            catalog = json.loads(
                (ROOT / f"localization/ui/{locale}/course.json").read_text(encoding="utf-8")
            )["messages"]
            original = re.search(re.escape(locale) + r':\{([^}]+)\}', body)
            self.assertIsNotNone(original)
            for name in fields:
                with self.subTest(locale=locale, label=name):
                    value = re.search(
                        r"(?:^|[,{}])" + re.escape(name) + r':"([^"]*)"',
                        original.group(1),
                    )
                    self.assertIsNotNone(value)
                    self.assertEqual(value.group(1), catalog["profile." + name])
        self.assertIn('PROFILE_DETAIL&&PROFILE_DETAIL.subscription', html)
        self.assertIn('PROFILE_DETAIL.stats&&PROFILE_DETAIL.stats.answer_accuracy', html)
        self.assertNotIn("fetch('/api/i18n/", html)


    def test_miniapp_course_picker_new_word_and_done_labels(self):
        """Picker and display-only labels use exact local copy with legacy fallback."""
        import re

        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertEqual(len(html.split("\n")), 8859)
        picker = html.split("function coursePickerCopy(){", 1)[1].split(
            "function coursePickerSavedLevel(", 1
        )[0]
        self.assertIn("var legacy={", picker)
        self.assertIn("}[LANG]||{};return {", picker)
        names = ("title", "version", "level", "note", "confirm")
        for key in names:
            with self.subTest(key=key):
                self.assertEqual(picker.count(
                    'courseMessage("coursePicker.' + key + '",legacy.' + key + ')'), 1)
        self.assertEqual(html.count('courseMessage("newWord",'), 1)
        self.assertEqual(html.count('courseMessage("lessonDone",lu.lessonH)'), 1)
        self.assertEqual(html.count('courseMessage("later",t.later)'), 1)
        for locale in ("uz", "ru", "tj"):
            messages = json.loads(
                (ROOT / f"localization/ui/{locale}/course.json").read_text(encoding="utf-8")
            )["messages"]
            inline = re.search(re.escape(locale) + r':\{([^}]+)\}', picker)
            self.assertIsNotNone(inline)
            for name in names:
                with self.subTest(locale=locale, label=name):
                    found = re.search(r"(?:^|[,{}])" + re.escape(name) + r':"([^"]*)"',
                                      inline.group(1))
                    self.assertIsNotNone(found)
                    self.assertEqual(messages["coursePicker." + name], found.group(1))
            self.assertEqual(messages["newWord"],
                             {"uz": "Yangi so'z", "ru": "Новое слово",
                              "tj": "Калимаи нав"}[locale])
            self.assertEqual(messages["later"],
                             {"uz": "Keyinroq", "ru": "Позже",
                              "tj": "Дертар"}[locale])
        self.assertIn("lessonMotivation(acc,doneCount)||lu.lessonP", html)
        self.assertIn("switchCourseTrack('hsk20',null)", html)
        self.assertIn("if(isPremiumLocked(l)){openLockedLessonSheet(idx);return}", html)
        self.assertIn("if(Flow&&Flow.graded)", html)
        # Russian lessonDoneSub differs from legacy punctuation and is NOT migrated.
        self.assertNotIn('courseMessage("lessonDoneSub"', html)


    def test_miniapp_login_and_blocked_gate_copy_from_local_assets(self):
        """Six auth/status display labels preserve exact UZ/RU/TJ inline values."""
        import re

        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertEqual(len(html.split("\n")), 8859)
        for function, prefix in (("authGateCopy", "authGate"),
                                 ("blockedGateCopy", "blockedGate")):
            view = html.split("function " + function + "(){", 1)[1].split(
                "\nfunction ", 1
            )[0]
            self.assertIn("var legacy={", view)
            self.assertIn("}[LANG]||{};return {", view)
            for name in ("title", "body", "btn"):
                self.assertEqual(
                    view.count('courseMessage("' + prefix + '.' + name +
                               '",legacy.' + name + ')'), 1)
            for locale in ("uz", "ru", "tj"):
                values = json.loads(
                    (ROOT / f"localization/ui/{locale}/course.json").read_text(
                        encoding="utf-8")
                )["messages"]
                original = re.search(
                    re.escape(locale) + r':\{([^}]+)\}', view
                )
                self.assertIsNotNone(original)
                for name in ("title", "body", "btn"):
                    with self.subTest(function=function, locale=locale, key=name):
                        field = re.search(
                            r"(?:^|[,{}])" + re.escape(name) + r':"([^"]*)"',
                            original.group(1))
                        self.assertIsNotNone(field)
                        self.assertEqual(field.group(1), values[prefix + "." + name])

        self.assertIn('var c=blockedGateCopy();', html)
        self.assertIn('var c=authGateCopy();', html)
        self.assertIn('try{if(tg&&tg.openTelegramLink)', html)
        self.assertIn('function openSupportLink(url){', html)
        self.assertIn('+(supportUrl?', html)
        self.assertIn('courseMessage("nav."+st.s,T().nav[st.s])', html)
        self.assertIn('hsk-course-i18n.js?v=20261020-eaff685fb700', html)


    def test_miniapp_notifications_and_pinyin_settings_use_local_static_text(self):
        """Eight reviewed UI keys retain exact UZ/RU/TJ original values."""
        import re

        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertEqual(len(html.split("\n")), 8859)
        groups = (
            ("confirmNotifOff:function(){", "\n  avatarEdit:function()",
             "notificationsOff", ("title", "body", "keep", "off"), "w"),
            ("pinyinSheet:function(){", "\n  setPinyin:function(",
             "pinyinSettings", ("h", "all", "nw", "off"), "t"),
        )
        for start, end, prefix, keys, local in groups:
            with self.subTest(screen=prefix):
                view = html.split(start, 1)[1].split(end, 1)[0]
                self.assertIn("var legacy=", view)
                self.assertIn("var " + local + "={", view)
                for key in keys:
                    self.assertEqual(view.count(
                        'courseMessage("' + prefix + '.' + key + '",legacy.' + key + ')'
                    ), 1)
                for locale in ("uz", "ru", "tj"):
                    source = json.loads(
                        (ROOT / f"localization/ui/{locale}/course.json").read_text(
                            encoding="utf-8")
                    )["messages"]
                    old = re.search(re.escape(locale) + r':\{([^}]+)\}', view)
                    self.assertIsNotNone(old)
                    for key in keys:
                        with self.subTest(locale=locale, key=key):
                            found = re.search(
                                r"(?:^|,)" + re.escape(key) + r':"([^"]*)"',
                                old.group(1))
                            self.assertIsNotNone(found)
                            self.assertEqual(found.group(1), source[prefix + "." + key])
        self.assertIn("App.applyNotif(false)", html)
        self.assertIn('_apiPost("/api/v3/notify",{enabled:on})', html)
        self.assertIn('localStorage.setItem("hsk_v3_pinyin",v)', html)
        self.assertIn("applyPinyinMode()", html)
        self.assertIn("hsk-course-i18n.js?v=20261020-eaff685fb700", html)
        self.assertNotIn("fetch('/api/i18n/", html)


    def test_miniapp_notification_schedule_and_avatar_copy(self):
        """Five static strings keep all UZ/RU/TJ original values and UI behavior."""
        import re

        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertEqual(len(html.split("\n")), 8859)
        schedule = html.split("function notifTimesHtml(){", 1)[1].split(
            "\nvar SHEET_RETURN_FOCUS=", 1)[0]
        self.assertIn("var legacy=", schedule)
        self.assertIn("var c={head:courseMessage(", schedule)
        for key, index in (("head", None), ("item0", 0), ("item1", 1), ("item2", 2)):
            original = "legacy.head" if index is None else "legacy.items[" + str(index) + "]"
            self.assertEqual(schedule.count(
                'courseMessage("notifTimes.' + key + '",' + original + ')'), 1)
        avatar = html.split("avatarEdit:function(){", 1)[1].split(
            "\n  /* Duolingo", 1)[0]
        self.assertEqual(avatar.count('courseMessage("avatarEdit.note",'), 1)
        for locale in ("uz", "ru", "tj"):
            catalog = json.loads(
                (ROOT / f"localization/ui/{locale}/course.json").read_text(
                    encoding="utf-8")
            )["messages"]
            match = re.search(
                re.escape(locale) + r':\{head:"([^"]+)",items:\["([^"]+)","([^"]+)","([^"]+)"\]\}',
                schedule)
            self.assertIsNotNone(match)
            for key, old in zip(("head", "item0", "item1", "item2"), match.groups()):
                with self.subTest(locale=locale, key=key):
                    self.assertEqual(catalog["notifTimes." + key], old)
            note = re.search(
                r'var note=courseMessage\("avatarEdit.note",LANG==="ru"\?"([^"]+)":LANG==="tj"\?"([^"]+)":"([^"]+)"\)',
                avatar)
            self.assertIsNotNone(note)
            self.assertEqual(catalog["avatarEdit.note"],
                             note.group({"ru": 1, "tj": 2, "uz": 3}[locale]))
        self.assertIn("App.applyNotif(false)", html)
        self.assertIn('_apiPost("/api/v3/notify",{enabled:on})', html)
        self.assertIn("myAvatarImgHtml()", html)
        self.assertIn("hsk-course-i18n.js?v=20261020-eaff685fb700", html)


    def test_miniapp_course_and_practice_error_copy_local_assets(self):
        """Local UI copy preserves all legacy fallbacks and retry/access logic."""
        import re

        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertEqual(len(html.split("\n")), 8859)
        cases = (
            ("showCourseLoadError(){", "\nfunction showCourseMapFailure(",
             "courseLoadError", ("title", "body", "btn"), "c"),
            ("showPracticeAuthRequired(elementId){", "\nfunction practiceGateErrorCopy(){",
             "practiceAuthRequired", ("body", "retry"), "copy"),
            ("practiceGateErrorCopy(){", "\n/* Mashq bo'limlarining chegara oynasi",
             "practiceGateError", ("body", "retry"), None),
        )
        for start, end, prefix, keys, local in cases:
            block = html.split(start, 1)[1].split(end, 1)[0]
            self.assertIn("legacy=", block)
            for field in keys:
                with self.subTest(screen=prefix, key=field):
                    self.assertEqual(block.count(
                        'courseMessage("' + prefix + '.' + field + '",legacy.' + field + ')'
                    ), 1)
            for locale in ("uz", "ru", "tj"):
                catalog = json.loads(
                    (ROOT / f"localization/ui/{locale}/course.json").read_text(
                        encoding="utf-8")
                )["messages"]
                old = re.search(r"(?:^|[\s,{])" + re.escape(locale) + r':\{([^}]+)\}', block)
                self.assertIsNotNone(old)
                for field in keys:
                    with self.subTest(locale=locale, screen=prefix, key=field):
                        label = re.search(
                            r"(?:^|,)" + re.escape(field) + r':"([^"]*)"',
                            old.group(1)
                        )
                        self.assertIsNotNone(label)
                        self.assertEqual(label.group(1), catalog[prefix + "." + field])
        self.assertIn('loadLevel(getSelectedLevel())', html)
        self.assertIn('if(res&&res.blocked)showBlockedGate(res.support_url)', html)
        self.assertIn('else if(res&&res.auth===false)showAuthGate()', html)
        self.assertIn('if(o.status===403&&o.j&&o.j.error==="free_feature_limit_reached")', html)
        self.assertIn('if(o.status<200||o.status>=300||!o.j||o.j.ok!==true||o.j.allowed!==true)', html)
        self.assertIn('location.reload()', html)
        self.assertIn('hsk-course-i18n.js?v=20261020-eaff685fb700', html)


    def test_miniapp_level_picker_copy_uses_reviewed_local_catalogs(self):
        """Eight HSK-band UI descriptions map to exact original three-locale copy."""
        import re

        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertEqual(len(html.split("\n")), 8859)
        view = html.split("  levelPicker:function(){", 1)[1].split(
            "\n  courseTrackPicker:function()", 1
        )[0]
        self.assertIn("var legacySub={", view)
        self.assertIn("}[LANG];var sub={", view)
        keys = ("hsk1", "hsk2", "hsk3", "hsk4",
                "nhsk1", "nhsk2", "nhsk3", "title")
        for key in keys:
            self.assertEqual(view.count(
                'courseMessage("levelPicker.' + key + '",legacySub.' + key + ')'
            ), 1)
        for locale in ("uz", "ru", "tj"):
            messages = json.loads(
                (ROOT / f"localization/ui/{locale}/course.json").read_text(
                    encoding="utf-8")
            )["messages"]
            old = re.search(re.escape(locale) + r':\{([^}]+)\}', view)
            self.assertIsNotNone(old)
            for key in keys:
                with self.subTest(locale=locale, key=key):
                    found = re.search(
                        r"(?:^|[,{}])" + re.escape(key) + r':"([^"]*)"',
                        old.group(1)
                    )
                    self.assertIsNotNone(found)
                    self.assertEqual(found.group(1), messages["levelPicker." + key])
        self.assertIn('var cur=normalizeLevel(MAP&&MAP.level||getSelectedLevel())', view)
        self.assertIn("onclick=\"App.pickLevel(", view)
        self.assertIn("pickLevel:function(lv){App.closeSheet();loadLevel(lv)}", html)
        self.assertIn('hsk-course-i18n.js?v=20261020-eaff685fb700', html)
        self.assertNotIn('fetch("/api/i18n/', html)


    def test_beginner_intro_and_grammar_tutor_labels_use_local_assets(self):
        """Ten visible captions preserve byte-identical UZ/RU/TJ legacy text."""
        import re

        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertEqual(len(html.split("\n")), 8859)
        groups = (("GRT", "grammarTutor",
                   ("teacher", "structure", "negation", "next", "done", "intro")),
                  ("BST", "beginnerIntro",
                   ("kicker", "voiceOn", "voiceOff", "replay")))
        for fn, prefix, fields in groups:
            # Each reviewed 5-line dictionary ends before the next function.
            block = "\n".join(
                html.split("function " + fn + "(){", 1)[1].split("\n", 5)[:5]
            )
            self.assertIn("var legacy=({", block)
            for key in fields:
                with self.subTest(function=fn, key=key):
                    self.assertEqual(block.count(
                        'courseMessage("' + prefix + '.' + key + '",legacy.' + key + ')'
                    ), 1)
            for locale in ("uz", "ru", "tj"):
                catalog = json.loads(
                    (ROOT / f"localization/ui/{locale}/course.json").read_text(
                        encoding="utf-8")
                )["messages"]
                inline = re.search(r"(?:^|[\s,{])" + re.escape(locale)
                                   + r':\{([^}]+)\}', block)
                self.assertIsNotNone(inline)
                for key in fields:
                    with self.subTest(function=fn, locale=locale, key=key):
                        found = re.search(r"(?:^|,)" + re.escape(key)
                                          + r':"([^"]*)"', inline.group(1))
                        self.assertIsNotNone(found)
                        self.assertEqual(found.group(1), catalog[prefix + "." + key])
        for invariant in ("var bt=BST(),gt=GRT()",
                          "var gt=GRT(),R=parseRule",
                          "if(gi===steps.length-1",
                          "if(bi===steps.length-1",
                          "function parseRule(t){"):
            self.assertIn(invariant, html)
        self.assertIn('hsk-course-i18n.js?v=20261020-eaff685fb700', html)


    def test_finish_ui_batch_31_reviewed_keys(self):
        """Static catalog parity for 30 finish/streak/parts labels across 3 locales."""
        import re

        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertEqual(len(html.split("\n")), 8859)
        groups = (
            ("partSections", ("w","p","s","r","d","x"), "m", "function partSecs(l){", "var m=", ";m={"),
            ("levelUp", ("cont","lessonH","lessonP","cpH","cpP","acc","combo","levelH","levelP","opened","xpH","xpP","lvl","bonusXp","chest"), "lu", "showLevelUp:function(type,data,extra){", "var lu=", ";lu={"),
            ("levelStats", ("xp","acc","time"), "statLbl", "showLevelUp:function(type,data,extra){", "var statLbl=", ";statLbl={"),
            ("streakDisplay", ("one","few","many","cont"), "W", "showStreakScreen:function(next){", "var W=", ";W={"),
        )
        for locale in ("uz", "ru", "tj"):
            msgs = json.loads((ROOT / f"localization/ui/{locale}/course.json")
                              .read_text(encoding="utf-8"))["messages"]
            self.assertEqual(len(msgs), 894)
            for prefix, fields, var, scope, start, end in groups:
                region = html.split(scope, 1)[1].split(start, 1)[1].split(end, 1)[0]
                original = next((line for line in region.splitlines()
                                 if locale + ":{" in line), None)
                self.assertIsNotNone(original)
                fragment = original.split(locale + ":{", 1)[1].split("},", 1)[0]
                for field in fields:
                    with self.subTest(locale=locale, key=prefix + "." + field):
                        val = re.search(r"(?:^|,)" + re.escape(field)
                                        + r':"([^"]*)"', fragment)
                        self.assertIsNotNone(val)
                        self.assertEqual(msgs[prefix + "." + field], val.group(1))
                        self.assertEqual(html.count(
                            'courseMessage("' + prefix + "." + field + '",' +
                            var + "." + field + ')'), 1)
            self.assertEqual(msgs["writerLoading"],
                             {"uz":"Yuklanmoqda...", "ru":"Загрузка...",
                              "tj":"Бор шуда истодааст..."}[locale])
            self.assertEqual(msgs["nextLessonOpen"],
                             {"uz":"Keyingi darsni ochish",
                              "ru":"Открыть следующий урок",
                              "tj":"Кушодани дарси оянда"}[locale])
        self.assertEqual(html.count('courseMessage("nextLessonOpen",'), 2)
        self.assertEqual(html.count('courseMessage("writerLoading",'), 1)
        for invariant in ("if(firstCp){", "if(Flow&&Flow.graded)",
                          "if(!ps||!n||!ps.extended)", "if(!fxOff())luRain();",
                          "function partSecs(l){", "if(isPremiumLocked(l))"):
            self.assertIn(invariant, html)
        self.assertIn("hsk-course-i18n.js?v=20261020-eaff685fb700", html)


if __name__ == "__main__":
    unittest.main()

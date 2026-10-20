"""Deterministic local-first catalog build: source, validation, four targets."""
import ast
import json
import re
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.i18n_build_local_catalogs import (
    ANDROID_TAGS, LANGUAGES, ROOT, output_files, generate, read_sources,
)


class CommonLocalCatalogTests(unittest.TestCase):
    def test_all_existing_reviewed_desktop_copy_is_ported(self):
        catalogs = read_sources(ROOT)
        self.assertEqual(set(catalogs), set(LANGUAGES))
        self.assertEqual(len(catalogs["uz"]), 102)
        self.assertEqual(set(catalogs["ru"]), set(catalogs["tj"]))
        self.assertEqual(catalogs["tj"]["navigation.profile"], "Профил")
        self.assertEqual(catalogs["ru"]["lesson.continue"], "Продолжить урок")
        self.assertEqual(catalogs["uz"]["auth.expires"], "Kirishni tasdiqlash uchun {time} qoldi")

    def test_source_strings_match_existing_desktop_three_language_baseline(self):
        source = (ROOT / "desktop/ui/js/i18n.js").read_text(encoding="utf-8")
        # Only the legacy 3-locale data object, not the adapter key map below.
        source = source.split("let activeLanguage =", 1)[0]
        mapping = {
            "course": "navigation.course",
            "practice": "navigation.practice",
            "profile": "navigation.profile",
            "rating": "navigation.rating",
            "subscription": "navigation.subscription",
            "startLesson": "lesson.start",
            "continueLesson": "lesson.continue",
            "lockedLesson": "lesson.locked",
            "courseEmpty": "lesson.notFound",
            "refresh": "common.refresh",
            "authExpires": "auth.expires",
            "authReferralCode": "desktopAuth.referralCode",
            "authReferralHint": "desktopAuth.referralHint",
            "authReferralInvalid": "desktopAuth.referralInvalid",
            "authTitle": "desktopAuth.title",
            "authDescription": "desktopAuth.description",
            "authCodeLabel": "desktopAuth.codeLabel",
            "authStart": "desktopAuth.telegramContinue",
            "authGoogle": "desktopAuth.googleContinue",
            "authApple": "desktopAuth.appleContinue",
            "authProviderWaiting": "desktopAuth.providerWaiting",
            "authProviderFailed": "desktopAuth.providerFailed",
            "authOpen": "desktopAuth.openTelegram",
            "authRetry": "desktopAuth.retry",
            "authStep1": "desktopAuth.step1",
            "authStep2": "desktopAuth.step2",
            "authStep3": "desktopAuth.step3",
            "authExpired": "desktopAuth.expired",
            "authCancelled": "desktopAuth.cancelled",
            "authWaiting": "desktopAuth.waiting",
            "authTelegramOpened": "desktopAuth.telegramOpened",
            "authStarting": "desktopAuth.starting",
            "authLinked": "desktopAuth.linked",
            "copyCode": "desktopAuth.copyCode",
            "copied": "desktopAuth.copied",
            "collapseSidebar": "desktopA11y.collapseSidebar",
            "notificationsTitle": "desktopA11y.notifications",
        }
        catalogs = read_sources(ROOT)
        for source_key, common_key in mapping.items():
            with self.subTest(key=source_key):
                pattern = re.compile(
                    r'(?m)^\s*' + re.escape(source_key) +
                    r':\s*(["\x27])([^\n]+?)\1,?'
                )
                matches = [match.group(2) for match in pattern.finditer(source)]
                self.assertEqual(
                    matches,
                    [catalogs[language][common_key] for language in LANGUAGES],
                )

    def test_committed_generated_files_match_source_byte_for_byte(self):
        self.assertEqual(generate(ROOT, check=True), [])
        self.assertEqual(len(output_files(read_sources(ROOT))), 6)

    def test_android_xml_resources_have_locale_correct_values(self):
        catalogs = read_sources(ROOT)
        for lang, tag in ANDROID_TAGS.items():
            with self.subTest(locale=lang):
                path = ROOT / f"android/app/src/main/res/values{tag}/hsk_common_i18n.xml"
                root = ET.fromstring(path.read_text(encoding="utf-8"))
                self.assertEqual(root.tag, "resources")
                strings = {
                    s.attrib["name"]: s.text for s in root.findall("string")
                }
                for key, expected in catalogs[lang].items():
                    name = "hsk_common_" + key.replace(".", "_")
                    android_value = strings[name].replace(r"\'", "'").replace(r'\"', '"')
                    self.assertEqual(android_value, expected)

    def test_bot_artifact_is_standalone_local_constant(self):
        path = ROOT / "app/bot/generated/common_i18n.py"
        module = ast.parse(path.read_text(encoding="utf-8"))
        self.assertEqual(len(module.body), 1)
        assignment = module.body[0]
        self.assertIsInstance(assignment, ast.Assign)
        data = ast.literal_eval(assignment.value)
        self.assertEqual(data, read_sources(ROOT))

    def test_browser_artifacts_match_and_are_network_free(self):
        mobile = (ROOT / "app/static/course_v3_data/hsk-common-i18n.js").read_text(encoding="utf-8")
        desktop = (ROOT / "desktop/ui/js/generated/hsk-common-i18n.js").read_text(encoding="utf-8")
        self.assertEqual(mobile, desktop)
        self.assertIn("window.HSKAI_COMMON_I18N", mobile)
        self.assertNotIn("fetch(", mobile)
        self.assertNotIn("XMLHttpRequest(", mobile)
        self.assertNotIn("import(", mobile)

    def _temp_sources(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        for lang in LANGUAGES:
            dest = root / f"localization/ui/{lang}/common.json"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / f"localization/ui/{lang}/common.json", dest)
        return temp, root

    def test_rejects_translation_placeholder_loss(self):
        temp, root = self._temp_sources()
        with temp:
            p = root / "localization/ui/ru/common.json"
            obj = json.loads(p.read_text(encoding="utf-8"))
            obj["messages"]["auth.expires"] = "Код действует ещё "
            p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Placeholder parity"):
                read_sources(root)

    def test_rejects_unsafe_html_and_invalid_keys(self):
        temp, root = self._temp_sources()
        with temp:
            p = root / "localization/ui/tj/common.json"
            obj = json.loads(p.read_text(encoding="utf-8"))
            obj["messages"]["navigation.profile"] = "<b>unsafe markup</b>"
            p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Untrusted key"):
                read_sources(root)

    def test_rejects_duplicate_json_keys(self):
        temp, root = self._temp_sources()
        with temp:
            p = root / "localization/ui/tj/common.json"
            s = p.read_text(encoding="utf-8")
            s = s.replace('"schema_version": 1,', '"schema_version": 1, "schema_version": 1,')
            p.write_text(s, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
                read_sources(root)

    def test_deterministic_generation_and_stale_output_detection(self):
        temp, root = self._temp_sources()
        with temp:
            self.assertEqual(len(generate(root, check=True)), 6)
            self.assertEqual(len(generate(root, check=False)), 6)
            self.assertEqual(generate(root, check=True), [])
            self.assertEqual(generate(root, check=False), [])
            p = root / "desktop/ui/js/generated/hsk-common-i18n.js"
            p.write_text("stale", encoding="utf-8")
            self.assertEqual(generate(root, check=True),
                             ["desktop/ui/js/generated/hsk-common-i18n.js"])
            self.assertEqual(generate(root, check=False),
                             ["desktop/ui/js/generated/hsk-common-i18n.js"])
            self.assertEqual(generate(root, check=True), [])


if __name__ == "__main__":
    unittest.main()

"""Deterministic P1 generation of course UI strings, without runtime adoption."""
import ast
import re
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.i18n_baseline_guard import git_blob_sha1

from scripts.i18n_build_course_catalogs import (
    ANDROID_TAGS, LOCALES, ROOT, android_resource_names, generate,
    output_files, read_sources,
)


class CourseLocalCatalogTests(unittest.TestCase):
    def test_reviewed_895_keys_and_six_generated_targets(self):
        catalogs = read_sources(ROOT)
        self.assertEqual(set(catalogs), set(LOCALES))
        self.assertTrue(all(len(catalogs[loc]) == 895 for loc in LOCALES))
        self.assertEqual(len(output_files(catalogs)), 6)
        self.assertEqual(generate(ROOT, check=True), [])

    def test_android_xml_contains_all_localized_strings(self):
        catalogs = read_sources(ROOT)
        for locale, tag in ANDROID_TAGS.items():
            with self.subTest(locale=locale):
                target = ROOT / f"android/app/src/main/res/values{tag}/hsk_course_i18n.xml"
                root = ET.fromstring(target.read_text(encoding="utf-8"))
                items = root.findall("string")
                actual = {node.attrib["name"]: node for node in items}
                expected = android_resource_names(catalogs[locale])
                self.assertEqual(set(actual), set(expected.values()))
                for key, name in expected.items():
                    self.assertEqual(actual[name].attrib["formatted"], "false")
                    # Android's slash-escaped apostrophe remains in XML parser output.
                    self.assertEqual((actual[name].text or "").replace(r"\'", "'"), catalogs[locale][key])
                    self.assertRegex(name, r"^hsk_course_[a-z][a-z0-9_]*$")

    def test_android_key_normalization_rejects_collisions(self):
        self.assertEqual(android_resource_names({"trialOn": "ok"}), {"trialOn": "hsk_course_trial_on"})
        with self.assertRaisesRegex(ValueError, "collision"):
            android_resource_names({"trialOn": "ok", "trial_on": "another"})

    def test_bot_artifact_local_dict_and_browser_static_parity(self):
        catalogs = read_sources(ROOT)
        src = (ROOT / "app/bot/generated/course_i18n.py").read_text(encoding="utf-8")
        module = ast.parse(src)
        self.assertEqual(len(module.body), 1)
        self.assertEqual(ast.literal_eval(module.body[0].value), catalogs)
        mobile = (ROOT / "app/static/course_v3_data/hsk-course-i18n.js").read_text(encoding="utf-8")
        desktop = (ROOT / "desktop/ui/js/generated/hsk-course-i18n.js").read_text(encoding="utf-8")
        self.assertEqual(mobile, desktop)
        self.assertIn("window.HSKAI_COURSE_I18N", mobile)
        for banned in ("fetch(", "XMLHttpRequest(", "import(", "correct_index", "answer_tokens"):
            self.assertNotIn(banned, mobile)
        self.assertTrue(all('"' + locale + '"' in mobile for locale in LOCALES))

    def test_deterministic_write_and_detect_stale_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for locale in LOCALES:
                dst = root / "localization/ui" / locale / "course.json"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / "localization/ui" / locale / "course.json", dst)
            self.assertEqual(len(generate(root, check=True)), 6)
            self.assertEqual(len(generate(root, check=False)), 6)
            self.assertEqual(generate(root, check=True), [])
            self.assertEqual(generate(root, check=False), [])
            out = root / "desktop/ui/js/generated/hsk-course-i18n.js"
            out.write_text("stale", encoding="utf-8")
            self.assertEqual(generate(root, check=True), ["desktop/ui/js/generated/hsk-course-i18n.js"])
            self.assertEqual(generate(root, check=False), ["desktop/ui/js/generated/hsk-course-i18n.js"])
            self.assertEqual(generate(root, check=True), [])


    def test_foundation_retry_and_lesson_recovery_use_local_fallbacks(self):
        """P2 recovery copy: bundled local texts, unchanged legacy fallbacks and anchors."""
        catalogs = read_sources(ROOT)
        source = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        lines = source.splitlines()
        anchors = {
            3762: ("foundation.unavailable",),
            3768: ("foundation.zeroTitle", "foundation.internetRetry"),
            3769: ("foundation.retry",),
            4073: ("lessonFlow.retry",),
            4127: ("lessonFlow.notReady",),
        }
        for line, keys in anchors.items():
            for key in keys:
                with self.subTest(line=line, key=key):
                    self.assertIn('courseMessage("' + key + '",LANG==="ru"?', lines[line - 1])
                    for locale in LOCALES:
                        self.assertIn(catalogs[locale][key], lines[line - 1])
        self.assertIn('esc(courseMessage("foundation.internetRetry"', lines[3768 - 1])
        self.assertIn('esc(courseMessage("foundation.retry"', lines[3769 - 1])
        self.assertIn("setLessonFlowControls();flowDone()", lines[4074 - 1])

    def test_practice_preparing_foundation_save_and_resource_loading_copy(self):
        """Offline catalog keeps exact legacy UI fallback and stable result flow."""
        catalogs = read_sources(ROOT)
        lines = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8").splitlines()
        anchors = {
            3196: "practice.preparing",
            3202: "practice.checkingAccess",
            3836: "foundation.saving",
            3844: "foundation.retrySave",
            3846: "foundation.saveFailed",
            4950: "foundation.zeroTitle",
            6970: "resourceFrame.loading",
        }
        for line, key in anchors.items():
            with self.subTest(line=line, key=key):
                self.assertIn('courseMessage("' + key + '",LANG==="ru"?', lines[line - 1])
                for locale in LOCALES:
                    self.assertIn(catalogs[locale][key], lines[line - 1])
        # The server-owned Foundation result decision and retry/timeout are unchanged.
        self.assertIn('result.ok!==true', lines[3842 - 1])
        self.assertIn('Foundation.finishing=false', lines[3843 - 1])
        self.assertIn('2800);return;', lines[3846 - 1])
        self.assertIn('esc(copy)', lines[3203 - 1])

    def test_course_bundle_cache_version_is_content_addressed_on_every_page(self):
        """Every static consumer must invalidate its cache on generated content changes."""
        expected_hash = git_blob_sha1(
            (ROOT / "app/static/course_v3_data/hsk-course-i18n.js").read_bytes()
        )[:12]
        pages = (
            "course-v3.html", "course_v3_memorize.html",
            "course_v3_mistakes.html", "course_v3_onboarding.html",
            "course_v3_pronunciation.html", "course_v3_recognition.html",
            "course_v3_test.html", "course_v3_voice.html",
            "desktop-download.html", "hsk-gaplar.html",
            "hsk-lugat.html", "subscription.html",
        )
        versions = set()
        for page in pages:
            source = (ROOT / "app/static" / page).read_text(encoding="utf-8")
            matches = re.findall(
                r"hsk-course-i18n\.js\?v=(\d{8})-([0-9a-f]{12})", source,
            )
            with self.subTest(page=page):
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0][1], expected_hash)
                versions.add(matches[0])
        self.assertEqual(len(versions), 1)

if __name__ == "__main__":
    unittest.main()

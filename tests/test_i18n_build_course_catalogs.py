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
    ANDROID_PWA_ONLY_PREFIX, ANDROID_TAGS, LOCALES, ROOT, android_resource_names, generate,
    output_files, read_sources,
)


def lines_containing(source: str, marker: str) -> list[str]:
    return [line for line in source.splitlines() if marker in line]


def unique_line_containing(source: str, marker: str) -> str:
    matches = lines_containing(source, marker)
    if len(matches) != 1:
        raise AssertionError(f"Expected one source line containing {marker!r}, found {len(matches)}")
    return matches[0]


class CourseLocalCatalogTests(unittest.TestCase):
    def test_reviewed_1019_keys_and_six_generated_targets(self):
        catalogs = read_sources(ROOT)
        self.assertEqual(set(catalogs), set(LOCALES))
        self.assertTrue(all(len(catalogs[loc]) == 1033 for loc in LOCALES))
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
                android_catalog = {
                    key: value for key, value in catalogs[locale].items()
                    if not key.startswith(ANDROID_PWA_ONLY_PREFIX)
                }
                expected = android_resource_names(android_catalog)
                self.assertEqual(set(actual), set(expected.values()))
                pwa_names = android_resource_names({
                    key: value for key, value in catalogs[locale].items()
                    if key.startswith(ANDROID_PWA_ONLY_PREFIX)
                })
                self.assertFalse(set(pwa_names.values()) & set(actual))
                for key, name in expected.items():
                    self.assertEqual(actual[name].attrib["formatted"], "false")
                    # Android's slash-escaped apostrophe remains in XML parser output.
                    self.assertEqual((actual[name].text or "").replace(r"\'", "'"), catalogs[locale][key])
                    self.assertRegex(name, r"^hsk_course_[a-z][a-z0-9_]*$")
        self.assertTrue(all(any(key.startswith(ANDROID_PWA_ONLY_PREFIX) for key in catalogs[loc])
                            for loc in LOCALES))

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
        anchors = {
            'courseMessage("foundation.unavailable",': ("foundation.unavailable",),
            'courseMessage("foundation.internetRetry",': (
                "foundation.zeroTitle", "foundation.internetRetry",
            ),
            'courseMessage("foundation.retry",': ("foundation.retry",),
            'courseMessage("lessonFlow.retry",': ("lessonFlow.retry",),
            'courseMessage("lessonFlow.notReady",': ("lessonFlow.notReady",),
        }
        for marker, keys in anchors.items():
            line = unique_line_containing(source, marker)
            for key in keys:
                with self.subTest(marker=marker, key=key):
                    self.assertIn('courseMessage("' + key + '",LANG==="ru"?', line)
                    for locale in LOCALES:
                        self.assertIn(catalogs[locale][key], line)
        self.assertIn('esc(courseMessage("foundation.internetRetry"',
                      unique_line_containing(source, 'courseMessage("foundation.internetRetry",'))
        self.assertIn('esc(courseMessage("foundation.retry"',
                      unique_line_containing(source, 'courseMessage("foundation.retry",'))
        self.assertIn("setLessonFlowControls();flowDone()",
                      unique_line_containing(source, "setLessonFlowControls();flowDone()"))

    def test_practice_preparing_foundation_save_and_resource_loading_copy(self):
        """Offline catalog keeps exact legacy UI fallback and stable result flow."""
        catalogs = read_sources(ROOT)
        source = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        anchors = {
            'courseMessage("practice.preparing",': "practice.preparing",
            'courseMessage("practice.checkingAccess",': "practice.checkingAccess",
            'courseMessage("foundation.saving",': "foundation.saving",
            'courseMessage("foundation.retrySave",': "foundation.retrySave",
            'courseMessage("foundation.saveFailed",': "foundation.saveFailed",
            'courseMessage("foundation.zeroTitle",': "foundation.zeroTitle",
            'courseMessage("resourceFrame.loading",': "resourceFrame.loading",
        }
        for marker, key in anchors.items():
            matching_lines = lines_containing(source, marker)
            self.assertTrue(matching_lines, f"Missing source marker: {marker}")
            with self.subTest(marker=marker, key=key):
                self.assertTrue(any('courseMessage("' + key + '",LANG==="ru"?' in line
                                    for line in matching_lines))
                for locale in LOCALES:
                    self.assertTrue(any(catalogs[locale][key] in line
                                        for line in matching_lines))
        # The server-owned Foundation result decision and retry/timeout are unchanged.
        self.assertIn('if(!result||result.ok!==true){\n      Foundation.finishing=false;', source)
        self.assertIn('2800);return;',
                      unique_line_containing(source, 'courseMessage("foundation.saveFailed",'))
        self.assertIn('esc(copy)', unique_line_containing(source, 'esc(copy)'))

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

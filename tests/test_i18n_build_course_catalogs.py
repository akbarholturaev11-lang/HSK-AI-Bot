"""Deterministic P1 generation of course UI strings, without runtime adoption."""
import ast
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.i18n_build_course_catalogs import (
    ANDROID_TAGS, LOCALES, ROOT, android_resource_names, generate,
    output_files, read_sources,
)


class CourseLocalCatalogTests(unittest.TestCase):
    def test_reviewed_117_keys_and_six_generated_targets(self):
        catalogs = read_sources(ROOT)
        self.assertEqual(set(catalogs), set(LOCALES))
        self.assertTrue(all(len(catalogs[loc]) == 117 for loc in LOCALES))
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


if __name__ == "__main__":
    unittest.main()

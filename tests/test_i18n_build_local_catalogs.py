"""Deterministic local-first catalog build: source, validation, four targets."""
import ast
import json
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
        self.assertEqual(len(catalogs["uz"]), 11)
        self.assertEqual(set(catalogs["ru"]), set(catalogs["tj"]))
        self.assertEqual(catalogs["tj"]["navigation.profile"], "Профил")
        self.assertEqual(catalogs["ru"]["lesson.continue"], "Продолжить урок")
        self.assertEqual(catalogs["uz"]["auth.expires"], "Kod {time} amal qiladi")

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
                    self.assertEqual(strings[name], expected)

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

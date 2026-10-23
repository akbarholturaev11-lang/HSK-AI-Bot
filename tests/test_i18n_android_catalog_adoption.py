"""Native XML remains byte-identical while localization/ owns its authoring."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.i18n_build_android_catalogs import ROOT, SOURCE, generate, read_sources


class AndroidCanonicalCatalogTests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        shutil.copytree(ROOT / SOURCE, root / SOURCE)
        return root

    def test_all_native_ui_resource_files_have_canonical_owners(self):
        expected = read_sources()
        self.assertEqual(len(expected), 36)
        actual = set()
        for group in ("main", "direct", "play"):
            for path in (ROOT / "android/app/src" / group / "res").glob("values*/*.xml"):
                if path.name in {"hsk_common_i18n.xml", "hsk_course_i18n.xml"}:
                    continue
                if any(e.tag in {"string", "plurals", "string-array"}
                       for e in ET.parse(path).getroot()):
                    actual.add(path.relative_to(ROOT).as_posix())
        self.assertEqual(actual, set(expected))
        self.assertEqual(generate(check=True), [])

    def test_canonical_xml_preserves_every_native_byte(self):
        for relative, raw in read_sources().items():
            with self.subTest(path=relative):
                self.assertEqual((ROOT / relative).read_bytes(), raw)

    def test_single_authoring_change_updates_only_its_native_file(self):
        root = self.fixture()
        self.assertEqual(len(generate(root, check=False)), 36)
        self.assertEqual(generate(root, check=True), [])
        path = root / SOURCE / "main/values/strings.xml"
        original = path.read_bytes()
        path.write_bytes(original.replace(b"Muammo haqida xabar berish", b"Muammo haqida xabar yuborish"))
        target = "android/app/src/main/res/values/strings.xml"
        self.assertEqual(generate(root, check=True), [target])
        self.assertEqual(generate(root, check=False), [target])
        self.assertEqual((root / target).read_bytes(), path.read_bytes())
        self.assertEqual(generate(root, check=True), [])

    def test_placeholder_loss_rejects_entire_batch_before_output(self):
        root = self.fixture()
        path = root / SOURCE / "direct/values-ru/strings.xml"
        original = path.read_text(encoding="utf-8")
        self.assertIn("%1$s", original)
        path.write_text(original.replace("%1$s", "", 1), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "placeholder parity"):
            generate(root, check=False)
        self.assertFalse((root / "android").exists())

    def test_missing_or_unregistered_source_is_rejected(self):
        root = self.fixture()
        path = root / SOURCE / "play/values-tg/strings.xml"
        path.unlink()
        with self.assertRaises(OSError):
            read_sources(root)
        path.write_text('<resources><string name="unexpected">x</string></resources>')
        with self.assertRaisesRegex(ValueError, "locale resource"):
            read_sources(root)

    def test_duplicate_resource_is_rejected(self):
        root = self.fixture()
        path = root / SOURCE / "play/values/strings.xml"
        text = path.read_text(encoding="utf-8")
        text = text.replace("</resources>", '<string name="limit_support">duplicate</string></resources>')
        path.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate Android"):
            read_sources(root)

    def test_manifest_path_escape_and_symlink_are_rejected(self):
        root = self.fixture()
        manifest = root / SOURCE / "manifest.json"
        obj = json.loads(manifest.read_text())
        obj["files"].append("../../escape.xml")
        manifest.write_text(json.dumps(obj))
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            read_sources(root)

    def test_generated_targets_cannot_redirect_writes(self):
        root = self.fixture()
        target = root / "android/app/src/main/res/values/strings.xml"
        target.parent.mkdir(parents=True)
        other = root / "unowned.txt"
        other.write_text("preserve")
        target.symlink_to(other)
        with self.assertRaisesRegex(ValueError, "symlink"):
            generate(root, check=False)
        self.assertEqual(other.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()

"""Public-site central authoring preserves all existing render/SEO contracts."""
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.i18n_build_public_site_catalog import ROOT, SOURCE, TARGET, generate


class PublicSiteCanonicalCopyTests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        source = root / SOURCE
        source.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / SOURCE, source)
        return root

    def test_generated_copy_is_exact(self):
        self.assertEqual(generate(check=True), [])
        self.assertEqual((ROOT / SOURCE).read_bytes(), (ROOT / TARGET).read_bytes())

    def test_editing_canonical_copy_changes_generated_module(self):
        root = self.fixture()
        self.assertEqual(generate(root, check=False), [TARGET])
        source = root / SOURCE
        source.write_bytes(source.read_bytes().replace(b'DOWNLOAD_PATH = "/download"',
                                                       b'DOWNLOAD_PATH = "/download-test"'))
        self.assertEqual(generate(root, check=True), [TARGET])
        generate(root, check=False)
        self.assertIn(b'"/download-test"', (root / TARGET).read_bytes())
        self.assertEqual(generate(root, check=True), [])

    def test_invalid_source_cannot_overwrite_existing_output(self):
        root = self.fixture()
        generate(root, check=False)
        original = (root / TARGET).read_bytes()
        (root / SOURCE).write_text("PAGES = {}\n")
        with self.assertRaisesRegex(ValueError, "exports"):
            generate(root, check=False)
        self.assertEqual((root / TARGET).read_bytes(), original)

    def test_generator_does_not_execute_source(self):
        root = self.fixture()
        with (root / SOURCE).open("a") as source:
            source.write('\nraise RuntimeError("must not execute while generating")\n')
        self.assertEqual(generate(root, check=False), [TARGET])


if __name__ == "__main__":
    unittest.main()

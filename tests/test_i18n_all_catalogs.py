"""One local build owns all generated UI bundles and validates before writes."""
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.i18n_build_all_catalogs import ROOT, generate, output_files


class AllLocalCatalogTests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        for directory in ("localization/ui", "localization/android", "localization/public_site"):
            shutil.copytree(ROOT / directory, root / directory)
        return root

    def test_all_52_bundled_artifacts_are_current(self):
        outputs = output_files()
        self.assertEqual(len(outputs), 52)
        self.assertEqual(generate(check=True), [])
        for path in outputs:
            self.assertTrue(path.startswith(("android/", "desktop/", "app/")))

    def test_all_sources_validate_before_any_writes(self):
        root = self.fixture()
        (root / "localization/public_site/content.py").write_text("not valid Python !!!")
        with self.assertRaises(SyntaxError):
            generate(root, check=False)
        self.assertFalse((root / "app").exists())
        self.assertFalse((root / "android").exists())
        self.assertFalse((root / "desktop").exists())

    def test_build_is_deterministic_and_reports_output_drift(self):
        root = self.fixture()
        self.assertEqual(len(generate(root, check=False)), 52)
        self.assertEqual(generate(root, check=True), [])
        target = root / "app/bot/generated/bot_i18n.py"
        target.write_text("stale")
        self.assertEqual(generate(root, check=True), [target.relative_to(root).as_posix()])
        generate(root, check=False)
        self.assertEqual(generate(root, check=True), [])


if __name__ == "__main__":
    unittest.main()

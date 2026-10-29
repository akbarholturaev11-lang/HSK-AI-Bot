"""Fixed system notification copy is generated locally without app imports."""
import ast
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.i18n_build_notification_catalogs import ROOT, generate, read_sources, TARGET


class NotificationCatalogTests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        for locale in ("uz", "ru", "tj"):
            relative = f"localization/ui/{locale}/notifications.json"
            target = root / relative
            target.parent.mkdir(parents=True)
            shutil.copyfile(ROOT / relative, target)
        return root

    def test_all_fixed_copy_matches_generated_artifact(self):
        catalogs = read_sources()
        self.assertEqual(len(catalogs["uz"]), 30)
        self.assertEqual(generate(check=True), [])
        tree = ast.parse((ROOT / TARGET).read_text(encoding="utf-8"))
        self.assertEqual(len(tree.body), 1)
        self.assertEqual(ast.literal_eval(tree.body[0].value), catalogs)

    def test_changed_canonical_value_updates_the_local_artifact(self):
        root = self.fixture()
        self.assertEqual(generate(root, check=False), [TARGET])
        path = root / "localization/ui/uz/notifications.json"
        obj = json.loads(path.read_text())
        obj["messages"]["course.title.lesson_time"] = "QA dars vaqti"
        path.write_text(json.dumps(obj))
        self.assertEqual(generate(root, check=True), [TARGET])
        generate(root, check=False)
        self.assertIn("QA dars vaqti", (root / TARGET).read_text())
        self.assertEqual(generate(root, check=True), [])

    def test_placeholder_and_markup_drift_are_rejected(self):
        for value in ("no lesson placeholder", "<script>{lesson}</script>", "<b>{lesson}"):
            with self.subTest(value=value):
                root = self.fixture()
                path = root / "localization/ui/ru/notifications.json"
                obj = json.loads(path.read_text())
                obj["messages"]["reminder.continueLessonNumber"] = value
                path.write_text(json.dumps(obj))
                with self.assertRaises(ValueError):
                    generate(root, check=False)
                self.assertFalse((root / TARGET).exists())

    def test_duplicate_keys_are_rejected(self):
        root = self.fixture()
        path = root / "localization/ui/tj/notifications.json"
        text = path.read_text().replace('"schema_version": 1,',
                                        '"schema_version": 1, "schema_version": 1,')
        path.write_text(text)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            read_sources(root)


if __name__ == "__main__":
    unittest.main()

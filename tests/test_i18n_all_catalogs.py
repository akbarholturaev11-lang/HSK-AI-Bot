"""One local build owns all generated UI bundles and validates before writes."""
from pathlib import Path
import json
import re
import shutil
import tempfile
import unittest

from scripts.i18n_build_all_catalogs import BROWSER_PAGES, ROOT, generate, output_files
from scripts.i18n_baseline_guard import git_blob_sha1


class AllLocalCatalogTests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        for directory in ("localization/ui", "localization/android", "localization/public_site"):
            shutil.copytree(ROOT / directory, root / directory)
        return root

    def test_all_56_bundled_artifacts_are_current(self):
        outputs = output_files()
        self.assertEqual(len(outputs), 56)
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
        self.assertEqual(len(generate(root, check=False)), 56)
        self.assertEqual(generate(root, check=True), [])
        target = root / "app/bot/generated/bot_i18n.py"
        target.write_text("stale")
        self.assertEqual(generate(root, check=True), [target.relative_to(root).as_posix()])
        generate(root, check=False)
        self.assertEqual(generate(root, check=True), [])

    def browser_fixture(self):
        root = self.fixture()
        for name in BROWSER_PAGES:
            target = root / "app/static" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / "app/static" / name, target)
        for relative in (
            "localization/baselines/reviewed_ui_changes.json",
            "app/static/course_v3_data/ads.js", "app/static/course_v3_data/memo.js",
            "app/static/course_v3_data/desktop-download.js",
            "app/static/course_v3_data/profile-carousel.js", "app/static/desktop-download-page.js",
        ):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        generate(root, check=False)
        return root

    def change_miniapp_text(self, root):
        path = root / "localization/ui/uz/miniapp.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        key = next(iter(data["messages"]))
        data["messages"][key] += " changed"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_build_refreshes_only_cache_tokens_and_reviewed_hashes(self):
        root = self.browser_fixture()
        before = {name: (root / "app/static" / name).read_bytes() for name in BROWSER_PAGES}
        self.change_miniapp_text(root)
        changed = generate(root, check=False)
        self.assertIn("app/static/course_v3_data/hsk-miniapp-i18n.js", changed)
        self.assertIn("localization/baselines/reviewed_ui_changes.json", changed)
        digest = git_blob_sha1((root / "app/static/course_v3_data/hsk-miniapp-i18n.js").read_bytes())[:12]
        review = json.loads((root / "localization/baselines/reviewed_ui_changes.json").read_text())
        for name in BROWSER_PAGES:
            path = root / "app/static" / name
            after = path.read_bytes()
            self.assertNotEqual(before[name], after)
            self.assertIn(("hsk-miniapp-i18n.js?v=20261021-" + digest).encode(), after)
            self.assertEqual(review["files"]["app/static/" + name]["reviewed_sha1"], git_blob_sha1(after))
        self.assertEqual(generate(root, check=True), [])

    def test_unreviewed_browser_change_blocks_all_writes(self):
        root = self.browser_fixture()
        target = root / "app/static/course_v3_data/hsk-miniapp-i18n.js"
        before = target.read_bytes()
        page = root / "app/static/course-v3.html"
        page.write_bytes(page.read_bytes() + b"<!-- unreviewed source change -->")
        self.change_miniapp_text(root)
        with self.assertRaisesRegex(ValueError, "Review browser source changes"):
            generate(root, check=False)
        self.assertEqual(target.read_bytes(), before)

    def test_cache_update_preserves_query_suffix_and_fragment(self):
        root = self.browser_fixture()
        page = root / "app/static/course-v3.html"
        text = page.read_text()
        text = re.sub(r'(hsk-miniapp-i18n.js\?v=[^"\x27]+)', r'\1&mode=local#bundle', text, count=1)
        page.write_text(text)
        review_path = root / "localization/baselines/reviewed_ui_changes.json"
        review = json.loads(review_path.read_text())
        review["files"]["app/static/course-v3.html"]["reviewed_sha1"] = git_blob_sha1(page.read_bytes())
        review_path.write_text(json.dumps(review))
        self.change_miniapp_text(root)
        generate(root, check=False)
        self.assertIn('&mode=local#bundle', page.read_text())
        self.assertEqual(generate(root, check=True), [])

    def test_invalid_output_paths_fail_before_any_writes(self):
        for relative, directory in (("app/public_site/content.py", True), ("app/public_site", False)):
            with self.subTest(path=relative):
                root = self.fixture()
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if directory:
                    target.mkdir()
                else:
                    target.write_text("file blocks parent directory")
                with self.assertRaisesRegex(ValueError, "not a (file|directory)"):
                    generate(root, check=False)
                self.assertFalse((root / "app/bot/generated/bot_i18n.py").exists())


if __name__ == "__main__":
    unittest.main()

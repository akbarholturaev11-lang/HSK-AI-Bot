"""Contract tests for the multilingual source inventory."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.i18n_inventory import inventory, scan_file, scan_json


class InventoryTests(unittest.TestCase):
    def test_detects_incomplete_nested_course_translations(self):
        data = {"title": "你好", "dialogues": [{"text": {"uz": "Salom", "ru": "Привет"}}]}
        count, missing, candidates = scan_json(data)
        self.assertEqual(count, 1)
        self.assertEqual(missing[0]["missing"], ["tj"])
        self.assertFalse(candidates)

    def test_finds_inline_ui_candidates_without_javascript_html_noise(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "app" / "static" / "page.html"
            path.parent.mkdir(parents=True)
            path.write_text(
                '<button>Boshlash</button><script>let text = "Xatolik";</script>'
                '<span>Profil</span>', encoding="utf-8"
            )
            result = scan_file(path, "miniapp", root)
            self.assertTrue(any(sample["sample"] == "Boshlash" for sample in result["samples"]))
            self.assertTrue(any(sample["sample"] == "Profil" for sample in result["samples"]))

    def test_includes_course_and_mobile_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            json_path = root / "app" / "static" / "course_data" / "hsk1.json"
            json_path.parent.mkdir(parents=True)
            json_path.write_text(json.dumps({"meaning": {"uz": "yaxshi",
                "ru": "хорошо", "tj": "хуб"}}), encoding="utf-8")
            ui_path = root / "android" / "app" / "src" / "main" / "java" / "Screen.kt"
            ui_path.parent.mkdir(parents=True)
            ui_path.write_text('Text("NEW")', encoding="utf-8")
            result = inventory(root)
            self.assertEqual(result["localized_maps"], 1)
            self.assertGreaterEqual(result["candidate_literals"], 1)
            self.assertEqual(result["parse_or_read_errors"], 0)


if __name__ == "__main__":
    unittest.main()

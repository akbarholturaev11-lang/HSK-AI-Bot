"""P0 inventory contracts: detection is read-only and reports review candidates."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_source_audit import (
    android_resource_parity, inventory, json_placeholder_drift,
    python_message_candidates, registry_coverage, scan_source, xml_names,
)


class SourceAuditTests(unittest.TestCase):
    def test_finds_multiline_bot_messages_and_keyboard_copy(self):
        source = '''
async def process(message, bot):
    await message.answer(
        "Delete this account? "
        "The request is permanent."
    )
    InlineKeyboardButton(text="Confirm deletion", callback_data="confirm")
    await bot.send_message(1, f"Waiting for {days} days")
'''
        found = python_message_candidates(source)
        labels = [row["sample"] for row in found]
        self.assertTrue(any("Delete this account?" in s for s in labels))
        self.assertIn("Confirm deletion", labels)
        self.assertTrue(any("Waiting for " in s for s in labels))

    def test_discovers_html_attributes_and_inline_js_catalog_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "app/static/deep/course.html"
            page.parent.mkdir(parents=True)
            page.write_text(
                '<input placeholder="Search words" aria-label="Find a word">'
                '<script>var I18N = {uz:{start:"Boshlash"},ru:{start:"Начать"}};</script>',
                encoding="utf-8",
            )
            report = scan_source(page, root, "miniapp_ui", all_hits=True)
            found = report["samples"]
            self.assertTrue(any(s["sample"] == "Search words" for s in found))
            self.assertTrue(any(s["sample"] == "Find a word" for s in found))
            self.assertTrue(any(s["sample"] == "Boshlash" for s in found))
            self.assertTrue(any(s["sample"] == "Начать" for s in found))

    def test_detects_placeholder_drift_without_changing_lesson_data(self):
        lesson = {
            "question": {"uz": "{count} ta savol", "ru": "{n} вопросов",
                         "tj": "{count} савол"},
            "answers": {"uz": ["a", "b"], "ru": ["c", "d"], "tj": ["e", "f"]},
        }
        actual = json_placeholder_drift(lesson)
        self.assertEqual(len(actual), 1)
        self.assertEqual(actual[0]["locale"], "ru")
        self.assertEqual(actual[0]["expected"], ["count"])
        self.assertEqual(actual[0]["actual"], ["n"])

    def test_android_strings_plurals_and_flavors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = root / "android/app/src/direct/res/values/strings.xml"
            base.parent.mkdir(parents=True)
            base.write_text(
                '<resources><string name="pro">Subscribe</string>'
                '<plurals name="lessons"><item quantity="one">1</item></plurals>'
                '<string name="technical" translatable="false">HSK</string>'
                '</resources>', encoding="utf-8")
            translated = base.parent.parent / "values-ru" / base.name
            translated.parent.mkdir(parents=True)
            translated.write_text(
                '<resources><string name="pro">Подписаться</string></resources>',
                encoding="utf-8")
            tajik = base.parent.parent / "values-tg" / base.name
            tajik.parent.mkdir(parents=True)
            tajik.write_text(
                '<resources><string name="pro">Обуна</string>'
                '<plurals name="lessons"><item quantity="one">1</item></plurals>'
                '</resources>', encoding="utf-8")
            self.assertNotIn("string:technical", xml_names(base.read_text()))
            audit = android_resource_parity(root)
            self.assertEqual(audit["missing_count"], 1)
            self.assertEqual(audit["compared_pairs"], 2)
            self.assertEqual(audit["pairs"][0]["missing"], ["plurals:lessons"])

    def test_registry_anchors_and_deep_directory_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reg = root / "localization/surface_registry.json"
            reg.parent.mkdir(parents=True)
            reg.write_text(json.dumps({"surfaces": [{"id": "miniapp",
                "anchors": ["app/static/deep/course.html", "lost.xml"]}]}),
                encoding="utf-8")
            page = root / "app/static/deep/course.html"
            page.parent.mkdir(parents=True)
            page.write_text('<button>Yangi dars</button>', encoding="utf-8")
            cov = registry_coverage(root)
            self.assertEqual(cov["missing_anchors"], ["lost.xml"])
            result = inventory(root)
            self.assertEqual(result["registry"]["surface_count"], 1)
            self.assertTrue(any(x["path"].endswith("deep/course.html")
                                for x in result["files"]))
            self.assertEqual(result["schema_version"], 2)
            self.assertEqual(result["parse_or_read_errors"], 0)

    def test_preserves_json_source_digest_and_flags_missing_tajik(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "app/static/course_v3_data/nhsk1/lesson_01.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({
                "title": {"uz": "Dars", "ru": "Урок"},
                "description": "Unreviewed sentence",
            }), encoding="utf-8")
            audit = scan_source(path, root, "lesson_content", all_hits=True)
            self.assertEqual(audit["missing_locale_maps"], 1)
            self.assertEqual(len(audit["sha256"]), 64)
            self.assertTrue(any(s.get("kind") == "missing_locale"
                                for s in audit["samples"]))


if __name__ == "__main__":
    unittest.main()

"""Authenticated native P3 grammar: bounded source changes and safe fallback."""
import json
from pathlib import Path
import unittest

from app.services.course_p3_grammar_localization import (
    _source_pinned_drafts, apply_native_grammar_locales,
)

ROOT = Path(__file__).resolve().parents[1]
LESSON16 = ROOT / "app/static/course_v3_data/nhsk2/lesson_16.json"
SERVICE = ROOT / "app/services/desktop_course_service.py"


class NativeGrammarLocalizationTests(unittest.TestCase):
    def test_real_lesson16_gets_exactly_six_main_six_mirrored_values(self):
        _source_pinned_drafts.cache_clear()
        before = LESSON16.read_bytes()
        original = json.loads(before)
        updated = apply_native_grammar_locales(
            original, level="nhsk2", lesson_order=16,
        )
        self.assertEqual(LESSON16.read_bytes(), before)
        self.assertEqual(original["grammar"][0]["examples"][0]["translation"],
                         {"uz": "", "ru": "", "tj": ""})
        self.assertEqual(len(updated["grammar"][0]["examples"]), 6)
        for source, translated in zip(
            original["grammar"][0]["examples"], updated["grammar"][0]["examples"],
        ):
            self.assertEqual(translated["zh"], source["zh"])
            self.assertEqual(translated["pinyin"], source["pinyin"])
            self.assertTrue(all(translated["translation"][lc] for lc in ("uz", "ru", "tj")))
        cards = [
            card for section in updated["sections"]
            for card in section.get("cards", [])
            if card.get("type") == "_grammar"
        ]
        self.assertTrue(cards)
        for e in cards[0]["g"]["examples"]:
            self.assertTrue(all(e["translation"][lc] for lc in ("uz", "ru", "tj")))
        self.assertNotEqual(updated, original)

    def test_sibling_tracks_and_no_gap_lesson_never_modified(self):
        lesson = {"level": "nhsk1", "lesson_id": 16, "sections": []}
        self.assertIs(apply_native_grammar_locales(
            lesson, level="nhsk1", lesson_order=16), lesson)
        self.assertIs(apply_native_grammar_locales(
            lesson, level="hsk1", lesson_order=16), lesson)
        self.assertIs(apply_native_grammar_locales(
            lesson, level="nhsk2", lesson_order=1), lesson)

    def test_wrong_revision_and_protected_field_fall_back_unchanged(self):
        old = json.loads(LESSON16.read_bytes())
        changed = json.loads(LESSON16.read_bytes())
        grammar_card = next(
            card for section in changed["sections"]
            for card in section.get("cards", [])
            if card.get("type") == "_grammar"
        )
        grammar_card["g"]["examples"][0]["zh"] = "CHANGED"
        self.assertIs(apply_native_grammar_locales(
            changed, level="nhsk2", lesson_order=16), changed)
        self.assertEqual(old["grammar"][0]["examples"][0]["translation"]["uz"], "")
        with __import__("tempfile").TemporaryDirectory() as tmp:
            self.assertIs(apply_native_grammar_locales(
                old, level="nhsk2", lesson_order=16, course_data_root=Path(tmp)), old)

    def test_no_unprotected_payload_or_http_added_to_common_native_service(self):
        source = SERVICE.read_text(encoding="utf-8")
        start = source.index("    async def lesson(")
        finish = source.index("    async def complete(", start)
        fragment = source[start:finish]
        self.assertIn("LessonAccessService", fragment)
        self.assertIn("apply_native_grammar_locales", fragment)
        self.assertLess(fragment.index("if not limit_status[\"allowed\"]"),
                        fragment.index("apply_native_grammar_locales"))
        for forbidden in ("requests.get(", "httpx.get(", "/api/v3/p3"):
            self.assertNotIn(forbidden, source)

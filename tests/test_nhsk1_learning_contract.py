"""Regression tests for HSK 3.0 N1 runtime content quality checks."""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "hsk30" / "verify_nhsk1_learning_contract.py"
spec = importlib.util.spec_from_file_location("nhsk1_contract", SCRIPT)
contract = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(contract)


def localized(value: str) -> dict[str, str]:
    return {lang: value for lang in ("uz", "ru", "tj")}


def fixture() -> dict:
    return {
        "schema_version": 2, "level": "nhsk1", "lesson_id": 1,
        "source_lesson": 1, "part_no": 1, "part_count": 1,
        "checkpoint": True, "title": "你好", "subtitle": localized("Salom"),
        "active_words": [{"zh": "你好", "pinyin": "nǐ hǎo", "meaning": localized("Salom")}],
        "grammar": [], "dialogues": [], "sections": [
            {"section_no": 1, "section_title": localized("So‘zlar"),
             "section_purpose": "intro", "cards": [
                 {"type": "active_word", "word": {"zh": "你好", "pinyin": "nǐ hǎo", "meaning": localized("Salom")}},
                 {"type": "meaning_guess", "options": [localized("Salom"), localized("Rahmat")],
                  "correct_index": 0, "explanation": localized("你好 — salom")},
             ]},
        ],
    }


class Nhsk1LearningContractTests(unittest.TestCase):
    def test_minimal_compatible_lesson_passes(self):
        errors, warnings = contract.validate_lesson(fixture(), number=1)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_invalid_choice_answer_fails(self):
        lesson = fixture()
        lesson["sections"][0]["cards"][1]["correct_index"] = 4
        errors, _ = contract.validate_lesson(lesson, number=1)
        self.assertTrue(any("correct_index out of range" in x for x in errors))

    def test_invalid_translation_fails(self):
        lesson = fixture()
        del lesson["active_words"][0]["meaning"]["tj"]
        errors, _ = contract.validate_lesson(lesson, number=1)
        self.assertTrue(any("active_words" in x for x in errors))

    def test_duplicate_answers_warn_without_blocking_migration(self):
        lesson = fixture()
        lesson["sections"][0]["cards"][1]["options"][1] = localized("Salom")
        errors, warnings = contract.validate_lesson(lesson, number=1)
        self.assertEqual(errors, [])
        self.assertTrue(any("duplicate" in x for x in warnings))

    def test_builder_rejects_answer_not_in_bank(self):
        errors, _ = contract.validate_card({
            "type": "sentence_builder", "tokens": ["你", "好"],
            "answer_tokens": ["你", "们"], "explanation": localized("你好"),
        }, "test")
        self.assertTrue(any("absent from bank" in x for x in errors))

    def test_n1_pilot_feedback_present_on_all_four_parts(self):
        from scripts.hsk30.apply_learning_overlays import (
            apply_nhsk1_pilot_feedback, validate_pilot_overlay,
        )
        self.assertEqual(validate_pilot_overlay(), 27)
        for part_no in range(1, 5):
            with self.subTest(part=part_no):
                path = Path("app/static/course_v3_data/nhsk1") / f"lesson_{part_no:02d}.json"
                original = json.loads(path.read_text(encoding="utf-8"))
                # Reapplying is idempotent, preserving all card positions and answers.
                enhanced = apply_nhsk1_pilot_feedback(original)
                self.assertEqual(original, enhanced)
                marked = [card for section in original["sections"]
                          for card in section["cards"]
                          if card.get("learning_feedback") == "n1_context_v1"]
                self.assertTrue(marked)
                for card in marked:
                    self.assertTrue(contract.localized(card["explanation"]))
                    self.assertFalse(re.search(
                        r"[А-Яа-яЁёҚқҒғҲҳҶҷӢӣӮӯЎў]", card["explanation"]["uz"],
                    ), "Uzbek teaching text must stay Latin-script")

    def test_n1_overlay_fails_on_reordered_cards(self):
        from scripts.hsk30.apply_learning_overlays import apply_nhsk1_pilot_feedback
        path = Path("app/static/course_v3_data/nhsk1/lesson_01.json")
        lesson = json.loads(path.read_text(encoding="utf-8"))
        # The existing material_ref is positional: changed card order must
        # never silently attach a teaching explanation to another answer.
        lesson["sections"][0]["cards"][2]["correct_index"] = 0
        with self.assertRaisesRegex(ValueError, "target changed"):
            apply_nhsk1_pilot_feedback(lesson)

    def test_n1_miniapp_renders_explanation_for_wrong_choice(self):
        html = Path("app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertIn('c.learning_feedback==="n1_context_v1"&&!Flow.challenge', html)
        self.assertIn('esc(rightText)+" · "+esc(why)', html)
        self.assertIn('c.learning_feedback==="n1_context_v1"?(esc(ans.join(" "))', html)
        self.assertIn("function skipN1PilotRechecks(index)", html)
        self.assertIn("Flow.pilotFailures[card.learning_objective]=!ok", html)

    def test_n1_exit_check_is_append_only_and_android_compatible(self):
        from scripts.hsk30.apply_learning_overlays import apply_nhsk1_pilot_exit_check
        src = json.loads(Path(
            "app/static/course_v3_data/nhsk1/lesson_04.json"
        ).read_text(encoding="utf-8"))
        enhanced = apply_nhsk1_pilot_exit_check(src)
        self.assertEqual(src, enhanced, "The overlay must be reproducible and idempotent")
        self.assertEqual([sec["section_no"] for sec in src["sections"]], [1, 2, 3, 4])
        self.assertEqual(src["sections"][2]["section_purpose"], "learning_exit_check")
        self.assertEqual(src["sections"][3]["section_purpose"], "learning_repair_bank")
        checks = src["sections"][2]["cards"]
        retries = src["sections"][3]["cards"]
        self.assertEqual(
            [card["type"] for card in checks],
            ["quick_quiz", "listening_choice", "sentence_builder"],
        )
        self.assertEqual(len({c["learning_objective"] for c in checks}), 3)
        self.assertTrue(all(c["learning_check"] == "n1_exit_check_v1" for c in checks))
        self.assertEqual(checks[1]["options"][checks[1]["correct_index"]], checks[1]["audio_text"])
        self.assertEqual(checks[2]["answer_tokens"], ["同学", "们", "再见"])
        self.assertEqual([x["learning_objective"] for x in retries], [x["learning_objective"] for x in checks])
        self.assertEqual([x["type"] for x in retries], [x["type"] for x in checks])
        self.assertEqual(retries[1]["audio_text"], "不客气！")
        # Existing Mini App and Android use these same three standard card
        # types. An appended section keeps every old material_ref unchanged.
        original = src.copy()
        original["sections"] = src["sections"][:2]
        self.assertEqual(original["sections"], enhanced["sections"][:2])

    def test_n1_exit_check_rejects_conflicting_section(self):
        from scripts.hsk30.apply_learning_overlays import apply_nhsk1_pilot_exit_check
        data = json.loads(Path(
            "app/static/course_v3_data/nhsk1/lesson_04.json"
        ).read_text(encoding="utf-8"))
        data["sections"][2]["cards"][0]["correct_index"] = 0
        with self.assertRaisesRegex(ValueError, "modified or collided"):
            apply_nhsk1_pilot_exit_check(data)

    def test_n1_exit_check_has_no_answer_leak_in_prompts(self):
        data = json.loads(Path(
            "app/static/course_v3_data/nhsk1/lesson_04.json"
        ).read_text(encoding="utf-8"))
        for card in data["sections"][2]["cards"]:
            for lang in ("uz", "ru", "tj"):
                prompt = card.get("prompt", card.get("sentence", {}))[lang]
                self.assertNotIn("老师，您好！", prompt)
                self.assertNotIn("谢谢！", prompt)
                self.assertNotIn("同学们，再见！", prompt)

    def test_runtime_rejects_map_part_mismatch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "nhsk1").mkdir()
            (root / "nhsk1" / "manifest.json").write_text(json.dumps({
                "level": "nhsk1", "lesson_count": 1, "source_lesson_count": 15,
            }), encoding="utf-8")
            (root / "nhsk1" / "lesson_01.json").write_text(json.dumps(fixture()), encoding="utf-8")
            (root / "nhsk1.json").write_text(json.dumps({
                "level": "nhsk1", "units": [{"no": n, "lessons": []} for n in range(1, 16)],
            }), encoding="utf-8")
            errors, _, _ = contract.validate_runtime(root)
            self.assertTrue(any("map/runtime part count mismatch" in x for x in errors))


if __name__ == "__main__":
    unittest.main()

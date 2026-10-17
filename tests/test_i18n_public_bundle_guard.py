"""P0 guard against accidentally embedding answer keys in future public i18n."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_public_bundle_guard import answer_key_paths, audit, normalize_key


class PublicLocalePackGuardTests(unittest.TestCase):
    def test_camel_case_and_snake_case_answer_keys(self):
        self.assertEqual(normalize_key("correctIndex"), "correct_index")
        self.assertEqual(answer_key_paths({
            "screens": [{"title": "Text", "quiz": {"correctIndex": 2}}],
            "legacy": {"answer_key": "SECRET"},
        }), ["$.screens[].quiz.correctIndex", "$.legacy.answer_key"])

    def test_word_order_solution_tokens_are_private_not_ui_copy(self):
        items = {
            "cards": [{"answer_tokens": ["SECRET_HANZI"],
                       "answerTokens": ["SECRET_ANSWER"],
                       "correctTokens": ["SECRET_ORDER"],
                       "solution_tokens": ["SECRET_PHRASE"],
                       "expected_tokens": ["SECRET_EXPECTED"]}],
        }
        found = answer_key_paths(items)
        self.assertEqual(found, [
            "$.cards[].answer_tokens", "$.cards[].answerTokens",
            "$.cards[].correctTokens", "$.cards[].solution_tokens",
            "$.cards[].expected_tokens",
        ])
        self.assertNotIn("SECRET", json.dumps(found))

    def test_safe_localized_labels_are_not_secret_answers(self):
        self.assertEqual(answer_key_paths({
            "answer": "Correct answer:",
            "correct": "Correct!",
            "solution": "Explanation",
            "subscription": "Subscribe",
            "card_id": "opaque_stable_card_reference",
        }), [])

    def test_nested_public_pack_triggers_block_without_leaking_values(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            pack = root / "app/static/i18n" / "course" / "ru.json"
            pack.parent.mkdir(parents=True)
            pack.write_text(json.dumps({
                "title": "Safe copy",
                "lesson": {"cards": [{"correct_index": 1, "answerKey": "SECRET"}]},
            }), encoding="utf-8")
            report = audit(root)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["checked_json_packs"], 1)
            self.assertEqual(len(report["findings"]), 2)
            self.assertNotIn("SECRET", json.dumps(report))
            self.assertEqual(report["findings"][0]["file"],
                             "app/static/i18n/course/ru.json")

    def test_invalid_json_blocks_publish(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            pack = root / "localization/generated/miniapp" / "uz.json"
            pack.parent.mkdir(parents=True)
            pack.write_text("{not-json", encoding="utf-8")
            report = audit(root)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["findings"][0]["issue"],
                             "unreadable_or_invalid_json")

    def test_absent_future_pack_roots_not_misreported_as_reviewed(self):
        with tempfile.TemporaryDirectory() as d:
            report = audit(Path(d))
            self.assertEqual(report["status"], "NO_PACKS_YET")
            self.assertEqual(report["checked_json_packs"], 0)
            self.assertEqual(report["findings"], [])


if __name__ == "__main__":
    unittest.main()

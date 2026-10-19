"""P3 translation-only preview invariant: block assessment, Pro and type drift."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.i18n_editor_preview_integrity import (
    _exact_same, attest_editor_preview, verify_approved_preview,
)
from scripts.i18n_editor_translation_draft import preview_editor_draft
from scripts.i18n_lesson_locale_gap_review_queue import _git_blob_sha1

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    original = {
        "schema_version": 2,
        "level": "nhsk2", "lesson_id": 1, "part_no": 1,
        "subtitle": {"uz": "Eski nom", "ru": "Старое название", "tj": "Номи кӯҳна"},
        "grammar": [{"examples": [
            {"zh": "秘密词汇", "pinyin": "mìmì", "translation": {"uz": "", "ru": "", "tj": ""}},
            {"zh": "另一词汇", "translation": {"uz": "", "ru": "", "tj": ""}},
        ]}],
        "sections": [{"cards": [{
            "type": "reverse_builder",
            "correct_index": 1,
            "options": ["SECRET_OPTION_A", "SECRET_OPTION_B"],
            "answer_tokens": ["SECRET_GRADE_TOKEN"],
            "grading": {"weight": 1, "is_correct": False},
            "access": {"requires_pro": True, "is_locked": True},
        }]}],
    }
    blob = json.dumps(original, ensure_ascii=False).encode("utf-8")
    draft = {
        "schema_version": 1, "kind": "p3_editor_translation_draft",
        "source_file": "app/static/course_v3_data/nhsk2/lesson_01.json",
        "source_git_blob_sha1": _git_blob_sha1(blob),
        "translations": [
            {"pointer": "/grammar/0/examples/0/translation",
             "values": {"uz": "Биринчи мисол", "ru": "Первый пример", "tj": "Намунаи аввал"}},
            {"pointer": "/grammar/0/examples/1/translation",
             "values": {"uz": "Иккинчи мисол", "ru": "Второй пример", "tj": "Намунаи дуюм"}},
        ],
    }
    return blob, draft


class EditorPreviewIntegrityTests(unittest.TestCase):
    def test_valid_display_only_preview_returns_only_counts(self):
        source, draft = fixture()
        before = bytes(source)
        result = attest_editor_preview(source, draft)
        self.assertEqual(result["verified_display_maps"], 2)
        self.assertEqual(result["verified_locale_values"], 6)
        self.assertTrue(result["all_nonapproved_source_fields_unchanged"])
        self.assertFalse(result["ready_to_ship"])
        self.assertTrue(result["human_language_approval_required"])
        self.assertEqual(source, before)
        safe = json.dumps(result, ensure_ascii=False)
        for forbidden in ("SECRET_", "秘密", "Биринчи", "Намунаи", "Первый"):
            self.assertNotIn(forbidden, safe)

    def test_grade_answer_and_pro_mutations_are_rejected(self):
        source, draft = fixture()
        good = preview_editor_draft(source, draft)
        card = good["sections"][0]["cards"][0]
        for label, change in (
            ("correct_index", lambda x: x.__setitem__("correct_index", 0)),
            ("option_order", lambda x: x["options"].reverse()),
            ("tokens", lambda x: x["answer_tokens"].append("INJECTED")),
            ("grade_weight", lambda x: x["grading"].__setitem__("weight", 2)),
            ("pro_access", lambda x: x["access"].__setitem__("requires_pro", False)),
            ("lock_flag", lambda x: x["access"].__setitem__("is_locked", False)),
            ("scoring_boolean_type", lambda x: x.__setitem__("correct_index", True)),
        ):
            with self.subTest(label=label):
                mutated = deepcopy(good)
                change(mutated["sections"][0]["cards"][0])
                with self.assertRaisesRegex(ValueError, "protected"):
                    verify_approved_preview(source, draft, mutated)
        self.assertEqual(card["correct_index"], 1)

    def test_chinese_pinyin_old_display_and_new_source_keys_rejected(self):
        source, draft = fixture()
        candidate = preview_editor_draft(source, draft)
        for label, mutate in (
            ("chinese", lambda x: x["grammar"][0]["examples"][0].__setitem__("zh", "REWRITTEN")),
            ("pinyin", lambda x: x["grammar"][0]["examples"][0].__setitem__("pinyin", "bad")),
            ("old_display", lambda x: x["subtitle"].__setitem__("ru", "CHANGED")),
            ("removed_section", lambda x: x["sections"].clear()),
            ("extra_root", lambda x: x.__setitem__("admin_override", True)),
            ("reordered_array", lambda x: x["grammar"][0]["examples"].reverse()),
        ):
            with self.subTest(label=label):
                tampered = deepcopy(candidate)
                mutate(tampered)
                with self.assertRaises(ValueError):
                    verify_approved_preview(source, draft, tampered)

    def test_draft_locale_values_and_structure_must_match_exactly(self):
        source, draft = fixture()
        valid = preview_editor_draft(source, draft)
        for label, mutate in (
            ("changed_translation", lambda x: x["grammar"][0]["examples"][0]["translation"].__setitem__("uz", "wrong")),
            ("missing_locale", lambda x: x["grammar"][0]["examples"][0]["translation"].pop("tj")),
            ("extra_locale", lambda x: x["grammar"][0]["examples"][0]["translation"].__setitem__("en", "unauthorized")),
            ("locale_type", lambda x: x["grammar"][0]["examples"][0]["translation"].__setitem__("ru", 12)),
        ):
            with self.subTest(label=label):
                tampered = deepcopy(valid)
                mutate(tampered)
                with self.assertRaises(ValueError):
                    verify_approved_preview(source, draft, tampered)

    def test_type_sensitive_json_equality(self):
        self.assertFalse(_exact_same(1, True))
        self.assertFalse(_exact_same(False, 0))
        self.assertFalse(_exact_same([1, 2], [2, 1]))
        self.assertFalse(_exact_same({"a": [1]}, {"a": [True]}))
        self.assertFalse(_exact_same({"a": None}, {"a": "None"}))
        self.assertTrue(_exact_same({"a": [1, {"x": False}]},
                                    {"a": [1, {"x": False}]}))

    def test_stale_sha_and_unsafe_pointer_rejected_before_diff(self):
        source, draft = fixture()
        bad = deepcopy(draft)
        bad["source_git_blob_sha1"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "revision"):
            attest_editor_preview(source, bad)
        bad = deepcopy(draft)
        bad["translations"][0]["pointer"] = "/sections/0/cards/0/correct_index"
        with self.assertRaises(ValueError):
            attest_editor_preview(source, bad)

    def test_no_source_write_public_pack_or_network_access(self):
        code = (ROOT / "scripts/i18n_editor_preview_integrity.py").read_text(
            encoding="utf-8"
        )
        for forbidden in (
            "write_text(", "write_bytes(", "open(", "requests.", "httpx.",
            "FastAPI(", "APIRouter(", "send_file(", "upload(", "json.dump(",
        ):
            self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()

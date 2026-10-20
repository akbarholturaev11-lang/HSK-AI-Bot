"""Editor draft P3 proof: fail-closed source SHA, fields, languages and immutable grades."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_editor_translation_draft import (
    _source_identity, _unique_json_keys, preview_editor_draft,
    validate_editor_draft,
)
from scripts.i18n_lesson_locale_gap_review_queue import (
    _git_blob_sha1, _missing_pointers,
)

ROOT = Path(__file__).resolve().parents[1]


def sample():
    source = {
        "schema_version": 2,
        "level": "nhsk2", "lesson_id": 1, "part_no": 1,
        "grammar": [{"examples": [{
            "hanzi": "秘密汉字",
            "translation": {"uz": "", "ru": "", "tj": ""},
        }]}],
        "sections": [{"cards": [
            {"type": "reverse_builder", "answer_tokens": ["SECRET_TOKEN"],
             "correct_index": 0, "options": ["SECRET_ANSWER"]},
        ]}],
    }
    raw = json.dumps(source, ensure_ascii=False).encode("utf-8")
    draft = {
        "schema_version": 1,
        "kind": "p3_editor_translation_draft",
        "source_file": "app/static/course_v3_data/nhsk2/lesson_01.json",
        "source_git_blob_sha1": _git_blob_sha1(raw),
        "translations": [{
            "pointer": "/grammar/0/examples/0/translation",
            "values": {"uz": "Машқ намунаси", "ru": "Пример упражнения",
                       "tj": "Намунаи машқ"},
        }],
    }
    return raw, draft


class EditorTranslationDraftTests(unittest.TestCase):
    def test_valid_synthetic_draft_reports_counts_without_text(self):
        original, draft = sample()
        report = validate_editor_draft(original, draft)
        self.assertEqual(report["validated_display_maps"], 1)
        self.assertEqual(report["validated_locale_values"], 3)
        self.assertFalse(report["ready_to_ship"])
        self.assertEqual(json.loads(original), json.loads(original))
        safe_json = json.dumps(report, ensure_ascii=False)
        for secret in ("SECRET_", "秘密", "Намунаи", "Машқ", "Пример"):
            self.assertNotIn(secret, safe_json)

    def test_preview_changes_only_reviewed_translation_maps(self):
        raw, draft = sample()
        original = json.loads(raw)
        modified = preview_editor_draft(raw, draft)
        expected = deepcopy(original)
        expected["grammar"][0]["examples"][0]["translation"] = dict(
            draft["translations"][0]["values"]
        )
        self.assertEqual(modified, expected)
        self.assertEqual(modified["sections"], original["sections"])
        self.assertEqual(modified["grammar"][0]["examples"][0]["hanzi"],
                         original["grammar"][0]["examples"][0]["hanzi"])
        self.assertEqual(json.loads(raw), original)

    def test_stale_blob_identity_and_traversal_fail_closed(self):
        raw, draft = sample()
        bad = deepcopy(draft)
        bad["source_git_blob_sha1"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "revision"):
            validate_editor_draft(raw, bad)
        bad = deepcopy(draft)
        bad["source_file"] = "app/static/course_v3_data/nhsk2/lesson_02.json"
        with self.assertRaisesRegex(ValueError, "identity"):
            validate_editor_draft(raw, bad)
        for path in (
            "../../etc/passwd",
            "app/static/course_v3_data/../lesson_01.json",
            "app/static/course_v3_data/nhsk2/lesson_001.json",
            "app/static/course_v3_data/nhsk4/lesson_01.json",
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                _source_identity(path)

    def test_answer_paths_duplicate_missing_extra_and_partial_locale_rejected(self):
        raw, draft = sample()
        for pointer in (
            "/sections/0/cards/0/correct_index",
            "/sections/0/cards/0/options/0",
            "/sections/0/cards/0/answer_tokens",
            "/grammar/0/examples/0/hanzi",
            "/grammar/999/examples/0/translation",
        ):
            bad = deepcopy(draft)
            bad["translations"][0]["pointer"] = pointer
            with self.subTest(pointer=pointer), self.assertRaises(ValueError):
                validate_editor_draft(raw, bad)
        bad = deepcopy(draft)
        bad["translations"].append(deepcopy(bad["translations"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_editor_draft(raw, bad)
        for values in (
            {"uz": "Тест", "ru": "Тест"},
            {"uz": "Тест", "ru": "Тест", "tj": "Тест", "en": "Test"},
            {"uz": "Тест", "ru": "Тест", "tj": ""},
            {"uz": "Тест", "ru": "Тест", "tj": "<script>x</script>"},
            {"uz": "Тест", "ru": "Тест", "tj": " \tbad "},
            {"uz": "Тест", "ru": "Тест", "tj": "ok\u0000bad"},
            {"uz": "Тест", "ru": "Тест", "tj": 5},
        ):
            bad = deepcopy(draft)
            bad["translations"][0]["values"] = values
            with self.subTest(values=list(values)), self.assertRaises(ValueError):
                validate_editor_draft(raw, bad)
        malformed = deepcopy(json.loads(raw))
        malformed["grammar"][0]["examples"][0]["translation"]["tj"] = "EXISTING"
        changed_raw = json.dumps(malformed).encode()
        bad = deepcopy(draft)
        bad["source_git_blob_sha1"] = _git_blob_sha1(changed_raw)
        with self.assertRaisesRegex(ValueError, "unapproved"):
            validate_editor_draft(changed_raw, bad)

    def test_real_lesson_16_pointers_and_sha_review_no_real_copy(self):
        file = ROOT / "app/static/course_v3_data/nhsk2/lesson_16.json"
        data = file.read_bytes()
        missing = _missing_pointers(json.loads(data))
        blank = [item for item in missing if item["issue"] == "all_locales_blank"]
        self.assertEqual(len(blank), 6)
        self.assertTrue(all(item["pointer"].startswith("/grammar/")
                            for item in blank))
        self.assertEqual(len(_git_blob_sha1(data)), 40)
        # No actual lesson translation is supplied by automated tests.

    def test_unique_json_key_parser_and_no_public_export_hooks(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            json.loads('{"uz":"x","uz":"y"}', object_pairs_hook=_unique_json_keys)
        code = (ROOT / "scripts/i18n_editor_translation_draft.py").read_text(
            encoding="utf-8"
        )
        for forbidden in (
            "requests.", "httpx.", "FastAPI(", "APIRouter(", "write_bytes(",
            "write_text(", "shutil.copy", "send_file(", "create_public_pack(",
        ):
            self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()

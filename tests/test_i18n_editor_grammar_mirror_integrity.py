"""P3 mirror integration proof: grammar/card parity, all grades and Pro untouched."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.i18n_editor_grammar_mirror_integrity import (
    _approved_mirrored_preview,
    attest_mirrored_grammar_preview,
    verify_mirrored_grammar_preview,
)
from scripts.i18n_lesson_locale_gap_review_queue import _git_blob_sha1

ROOT = Path(__file__).resolve().parents[1]


def source_and_draft(mirrors=True):
    group = {
        "no": 1, "title_zh": "过", "examples": [
            {"zh": "她去过中国。", "pinyin": "", "translation": {
                "uz": "", "ru": "", "tj": "",
            }},
        ],
    }
    original = {
        "schema_version": 2, "level": "nhsk2",
        "lesson_id": 1, "part_no": 1,
        "grammar": [deepcopy(group)],
        "sections": [
            {"cards": [{
                "type": "_grammar", "g": deepcopy(group),
            }] if mirrors else []},
            {"cards": [{
                "type": "reverse_builder",
                "correct_index": 1, "options": ["ANSWER_A", "ANSWER_B"],
                "answer_tokens": ["SECRET_TOKEN"],
                "grading": {"score": 5, "passed": False},
                "access": {"requires_pro": True, "is_locked": True},
            }]},
        ],
    }
    raw = json.dumps(original, ensure_ascii=False).encode("utf-8")
    draft = {
        "schema_version": 1, "kind": "p3_editor_translation_draft",
        "source_file": "app/static/course_v3_data/nhsk2/lesson_01.json",
        "source_git_blob_sha1": _git_blob_sha1(raw),
        "translations": [{
            "pointer": "/grammar/0/examples/0/translation",
            "values": {"uz": "Xitoyga borgan", "ru": "Была в Китае",
                       "tj": "Ба Чин рафтааст"},
        }],
    }
    return raw, draft


class GrammarMirrorIntegrityTests(unittest.TestCase):
    def test_real_nhsk2_lesson_16_source_main_and_six_mirror_copies(self):
        lesson = ROOT / "app/static/course_v3_data/nhsk2/lesson_16.json"
        raw = lesson.read_bytes()
        before = bytes(raw)
        doc = json.loads(raw)
        missing = doc["grammar"][0]["examples"]
        self.assertEqual(len(missing), 6)
        draft = {
            "schema_version": 1, "kind": "p3_editor_translation_draft",
            "source_file": "app/static/course_v3_data/nhsk2/lesson_16.json",
            "source_git_blob_sha1": _git_blob_sha1(raw),
            "translations": [{
                "pointer": f"/grammar/0/examples/{i}/translation",
                "values": {"uz": f"Uzbek sample {i}", "ru": f"Русский пример {i}",
                           "tj": f"Намунаи тоҷикӣ {i}"},
            } for i in range(6)],
        }
        attested = attest_mirrored_grammar_preview(raw, draft)
        self.assertEqual(attested["verified_original_display_maps"], 6)
        self.assertEqual(attested["verified_mirrored_card_maps"], 6)
        self.assertEqual(attested["verified_total_updated_display_maps"], 12)
        self.assertEqual(attested["human_authored_locale_values"], 18)
        self.assertFalse(attested["ready_to_ship"])
        _, proposed, _, _, _ = _approved_mirrored_preview(raw, draft)
        for i in range(6):
            self.assertEqual(
                proposed["grammar"][0]["examples"][i]["translation"],
                proposed["sections"][1]["cards"][0]["g"]["examples"][i]["translation"],
            )
        self.assertEqual(proposed["sections"][0], doc["sections"][0])
        self.assertEqual(raw, before)
        safe_output = json.dumps(attested, ensure_ascii=False)
        for s in ("Русский пример", "Намунаи тоҷикӣ", "correct_index", "answer_tokens"):
            self.assertNotIn(s, safe_output)

    def test_reviewed_original_and_mirror_in_memory_can_be_verified(self):
        raw, draft = source_and_draft()
        original = json.loads(raw)
        _, preview, _, bases, mirrors = _approved_mirrored_preview(raw, draft)
        self.assertEqual((bases, mirrors), (1, 1))
        self.assertEqual(
            preview["grammar"][0]["examples"][0]["translation"],
            preview["sections"][0]["cards"][0]["g"]["examples"][0]["translation"],
        )
        self.assertEqual(preview["sections"][1], original["sections"][1])
        self.assertEqual(
            verify_mirrored_grammar_preview(raw, draft, preview)["verified_total_updated_display_maps"],
            2,
        )

    def test_grade_answers_pro_lock_and_mirror_translation_tampering_rejected(self):
        raw, draft = source_and_draft()
        _, good, _, _, _ = _approved_mirrored_preview(raw, draft)
        mutate = {
            "correct_index": lambda x: x["sections"][1]["cards"][0].update(correct_index=0),
            "options": lambda x: x["sections"][1]["cards"][0]["options"].reverse(),
            "builder_tokens": lambda x: x["sections"][1]["cards"][0]["answer_tokens"].append("TRAP"),
            "grade": lambda x: x["sections"][1]["cards"][0]["grading"].update(score=10),
            "pro": lambda x: x["sections"][1]["cards"][0]["access"].update(requires_pro=False),
            "lock": lambda x: x["sections"][1]["cards"][0]["access"].update(is_locked=False),
            "chinese": lambda x: x["grammar"][0]["examples"][0].update(zh="CHANGED"),
            "pinyin": lambda x: x["grammar"][0]["examples"][0].update(pinyin="CHANGED"),
            "mirror_zh": lambda x: x["sections"][0]["cards"][0]["g"]["examples"][0].update(zh="WRONG"),
            "mirror_text": lambda x: x["sections"][0]["cards"][0]["g"]["examples"][0]["translation"].update(ru="WRONG"),
            "extra": lambda x: x.update(admin_override=True),
            "boolean_type": lambda x: x["sections"][1]["cards"][0].update(correct_index=True),
        }
        for key, action in mutate.items():
            with self.subTest(mutation=key):
                changed = deepcopy(good)
                action(changed)
                with self.assertRaisesRegex(ValueError, "protected"):
                    verify_mirrored_grammar_preview(raw, draft, changed)

    def test_divergent_mirror_and_ambiguous_double_mirror_rejected(self):
        raw, draft = source_and_draft()
        source = json.loads(raw)
        source["sections"][0]["cards"][0]["g"]["examples"][0]["zh"] = "DIFFERENT"
        diverged = json.dumps(source, ensure_ascii=False).encode("utf-8")
        draft["source_git_blob_sha1"] = _git_blob_sha1(diverged)
        with self.assertRaisesRegex(ValueError, "mirrored grammar source differs"):
            attest_mirrored_grammar_preview(diverged, draft)

        raw, draft = source_and_draft()
        source = json.loads(raw)
        source["grammar"].append(deepcopy(source["grammar"][0]))
        source["grammar"][1]["examples"][0]["translation"] = {"uz": "", "ru": "", "tj": ""}
        draft["source_git_blob_sha1"] = _git_blob_sha1(
            json.dumps(source, ensure_ascii=False).encode("utf-8")
        )
        draft["translations"].append({
            "pointer": "/grammar/1/examples/0/translation",
            "values": {"uz": "B", "ru": "Б", "tj": "Б"},
        })
        ambiguous = json.dumps(source, ensure_ascii=False).encode("utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate mirrored"):
            attest_mirrored_grammar_preview(ambiguous, draft)

    def test_non_grammar_source_pointer_and_stale_sha_rejected(self):
        raw, draft = source_and_draft()
        bad = deepcopy(draft)
        bad["source_git_blob_sha1"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "revision"):
            attest_mirrored_grammar_preview(raw, bad)
        source = json.loads(raw)
        source["subtitle"] = {"uz": "", "ru": "", "tj": ""}
        altered = json.dumps(source, ensure_ascii=False).encode("utf-8")
        bad = deepcopy(draft)
        bad["source_git_blob_sha1"] = _git_blob_sha1(altered)
        bad["translations"][0]["pointer"] = "/subtitle"
        with self.assertRaisesRegex(ValueError, "only grammar"):
            attest_mirrored_grammar_preview(altered, bad)

    def test_grammar_without_duplicate_card_needs_no_extra_translation(self):
        raw, draft = source_and_draft(mirrors=False)
        proof = attest_mirrored_grammar_preview(raw, draft)
        self.assertEqual(proof["verified_original_display_maps"], 1)
        self.assertEqual(proof["verified_mirrored_card_maps"], 0)
        self.assertEqual(proof["human_authored_locale_values"], 3)

    def test_helper_is_private_and_does_not_emit_source_or_write_public_packs(self):
        code = (ROOT / "scripts/i18n_editor_grammar_mirror_integrity.py").read_text(
            encoding="utf-8",
        )
        for marker in ("write_text(", "write_bytes(", "open(", "requests.", "httpx.",
                       "FastAPI(", "APIRouter(", "send_file(", "json.dump(", "pathlib.Path("):
            self.assertNotIn(marker, code)


if __name__ == "__main__":
    unittest.main()

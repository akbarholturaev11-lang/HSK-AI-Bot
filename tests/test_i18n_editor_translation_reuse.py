"""Source-pinned private translation reuse; real HSK source and tamper tests."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_editor_translation_reuse import prepare_translation_reuse
from scripts.i18n_editor_translation_draft import validate_editor_draft
from scripts.i18n_editor_grammar_mirror_integrity import attest_mirrored_grammar_preview
from scripts.i18n_lesson_locale_gap_review_queue import _git_blob_sha1

ROOT = Path(__file__).resolve().parents[1]


def _editor_draft(root, num):
    path = root / f"app/static/course_v3_data/nhsk2/lesson_{num:02d}.json"
    raw = path.read_bytes()
    data = json.loads(raw)
    fields = []
    for gi, group in enumerate(data["grammar"]):
        for ei, ex in enumerate(group["examples"]):
            if ex.get("translation") == {"uz": "", "ru": "", "tj": ""}:
                fields.append({
                    "pointer": f"/grammar/{gi}/examples/{ei}/translation",
                    "values": {
                        "uz": f"UZ example {num}-{gi}-{ei}",
                        "ru": f"Русский пример {num}-{gi}-{ei}",
                        "tj": f"Намунаи тоҷикӣ {num}-{gi}-{ei}",
                    },
                })
    return {
        "schema_version": 1, "kind": "p3_editor_translation_draft",
        "source_file": f"app/static/course_v3_data/nhsk2/lesson_{num:02d}.json",
        "source_git_blob_sha1": _git_blob_sha1(raw),
        "translations": fields,
    }


class EditorTranslationReuseTests(unittest.TestCase):
    def test_real_lessons_16_17_18_reuse_into_20_without_writing_course(self):
        before = {}
        for n in (16, 17, 18, 20):
            f = ROOT / f"app/static/course_v3_data/nhsk2/lesson_{n:02d}.json"
            before[n] = f.read_bytes()
        with tempfile.TemporaryDirectory() as t:
            private = Path(t)
            paths = []
            for num in (16, 17, 18):
                file = private / f"draft_{num}.json"
                file.write_text(json.dumps(_editor_draft(ROOT, num),
                                           ensure_ascii=False), encoding="utf-8")
                paths.append(file)
            proposal, proof = prepare_translation_reuse(
                paths, "nhsk2", 20, root=ROOT,
            )
        self.assertEqual(len(proposal["translations"]), 12)
        self.assertEqual(proof["target_display_maps_reused"], 12)
        self.assertEqual(proof["target_locale_values_reused"], 36)
        self.assertEqual(proof["target_mirrored_card_maps"], 0)
        self.assertEqual(proof["distinct_origin_source_lessons"], 3)
        self.assertFalse(proof["ready_to_ship"])
        self.assertTrue(proof["human_language_review_required"])
        self.assertEqual(
            validate_editor_draft(before[20], proposal)["validated_display_maps"], 12
        )
        safe_output = json.dumps(proof, ensure_ascii=False)
        for secret in ("UZ example", "Русский пример", "Намунаи тоҷикӣ",
                       '"correct_index"', '"answer_tokens"', '"options":'):
            self.assertNotIn(secret, safe_output)
        for n in before:
            self.assertEqual(
                (ROOT / f"app/static/course_v3_data/nhsk2/lesson_{n:02d}.json").read_bytes(),
                before[n],
            )

    def test_conflicting_suggestions_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            private = Path(folder)
            original = _editor_draft(ROOT, 16)
            file1, file2 = private / "one.json", private / "two.json"
            file1.write_text(json.dumps(original), encoding="utf-8")
            modified = deepcopy(original)
            modified["translations"][0]["values"]["ru"] = "DIFFERENT"
            file2.write_text(json.dumps(modified), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "conflicting"):
                prepare_translation_reuse([file1, file2], "nhsk2", 20)

    def test_stale_sha_rejected_and_target_incomplete_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            private = Path(folder)
            paths = []
            for n in (16, 17, 18):
                d = _editor_draft(ROOT, n)
                p = private / f"d{n}.json"
                p.write_text(json.dumps(d), encoding="utf-8")
                paths.append(p)
            with self.assertRaisesRegex(ValueError, "uncovered"):
                prepare_translation_reuse(paths[:1], "nhsk2", 20)
            stale = json.loads(paths[0].read_text())
            stale["source_git_blob_sha1"] = "0" * 40
            paths[0].write_text(json.dumps(stale))
            with self.assertRaisesRegex(ValueError, "revision"):
                prepare_translation_reuse(paths, "nhsk2", 20)

    def test_draft_input_inside_repo_and_illegal_lesson_rejected(self):
        path = ROOT / "localization/reviews/p3_nhsk2_locale_gaps_20261019.json"
        with self.assertRaisesRegex(ValueError, "private"):
            prepare_translation_reuse([path], "nhsk2", 20)
        with self.assertRaises(ValueError):
            prepare_translation_reuse([], "nhsk2", 20)
        with tempfile.TemporaryDirectory() as folder:
            draft = Path(folder) / "draft.json"
            draft.write_text(json.dumps(_editor_draft(ROOT, 16)), encoding="utf-8")
            with self.assertRaises(ValueError):
                prepare_translation_reuse([draft], "nhsk5", 20)

    def test_valid_source_but_different_chinese_is_not_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            private = Path(folder)
            file = private / "d16.json"
            file.write_text(json.dumps(_editor_draft(ROOT, 16)), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "uncovered"):
                prepare_translation_reuse([file], "nhsk2", 17)


    def test_partial_reuse_from_lesson16_into_20_still_needs_human_review(self):
        target_file = ROOT / "app/static/course_v3_data/nhsk2/lesson_20.json"
        original = target_file.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            source_file = Path(folder) / "lesson_16.json"
            source_file.write_text(json.dumps(_editor_draft(ROOT, 16)))
            with self.assertRaisesRegex(ValueError, "uncovered"):
                prepare_translation_reuse([source_file], "nhsk2", 20)
            partial, report = prepare_translation_reuse(
                [source_file], "nhsk2", 20, allow_partial=True,
            )
        self.assertEqual(report["reuse_scope"], "PARTIAL_PRIVATE_REVIEW")
        self.assertEqual(report["target_display_maps_total"], 12)
        self.assertEqual(report["target_display_maps_reused"], 6)
        self.assertEqual(report["target_display_maps_uncovered"], 6)
        self.assertEqual(report["target_locale_values_reused"], 18)
        self.assertEqual(report["target_locale_values_uncovered"], 18)
        self.assertEqual(len(partial["translations"]), 6)
        self.assertEqual(
            validate_editor_draft(original, partial)["validated_display_maps"], 6
        )
        self.assertTrue(
            attest_mirrored_grammar_preview(original, partial)["all_other_fields_unchanged"]
        )
        self.assertFalse(report["ready_to_ship"])
        self.assertEqual(target_file.read_bytes(), original)

    def test_partial_no_matching_context_and_invalid_mode_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "source.json"
            file.write_text(json.dumps(_editor_draft(ROOT, 16)))
            with self.assertRaisesRegex(ValueError, "no matching"):
                prepare_translation_reuse(
                    [file], "nhsk2", 17, allow_partial=True,
                )
            with self.assertRaisesRegex(ValueError, "invalid partial"):
                prepare_translation_reuse(
                    [file], "nhsk2", 20, allow_partial=1,
                )

    def test_partial_mirror_sync_and_nonmatched_examples_remain_untouched(self):
        # Synthetic lesson 1 provides source context; lesson 2 has two examples
        # with the first repeated, and a verified _grammar card mirror.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "checkout"
            source_dir = root / "app/static/course_v3_data/nhsk2"
            source_dir.mkdir(parents=True)
            def grammar(examples):
                return {
                    "no": 1,
                    "title": {"uz": "RULE", "ru": "RULE", "tj": "RULE"},
                    "title_zh": "规则",
                    "rule": {"uz": "RULE", "ru": "RULE", "tj": "RULE"},
                    "examples": [
                        {"zh": zh, "pinyin": pinyin,
                         "translation": {"uz": "", "ru": "", "tj": ""}}
                        for zh, pinyin in examples
                    ],
                }
            g1 = grammar([("来", "lái")])
            g2 = grammar([("来", "lái"), ("去", "qù")])
            def lesson(number, group, mirror):
                return {
                    "schema_version": 2, "level": "nhsk2",
                    "lesson_id": number, "part_no": 1,
                    "grammar": [group],
                    "sections": [{"cards": [
                        {"type": "_grammar", "g": deepcopy(group)},
                        {"type": "reverse_builder",
                         "answer_tokens": ["PROTECTED"], "correct_index": 0},
                    ]}] if mirror else [],
                }
            source_file = source_dir / "lesson_01.json"
            target_file = source_dir / "lesson_02.json"
            source_file.write_text(
                json.dumps(lesson(1, g1, False), ensure_ascii=False), encoding="utf-8"
            )
            target_file.write_text(
                json.dumps(lesson(2, g2, True), ensure_ascii=False), encoding="utf-8"
            )
            original_target = target_file.read_bytes()
            private_file = Path(folder) / "draft.json"
            draft = {
                "schema_version": 1, "kind": "p3_editor_translation_draft",
                "source_file": "app/static/course_v3_data/nhsk2/lesson_01.json",
                "source_git_blob_sha1": _git_blob_sha1(source_file.read_bytes()),
                "translations": [{
                    "pointer": "/grammar/0/examples/0/translation",
                    "values": {"uz": "Kelyapti", "ru": "Приходит", "tj": "Меояд"},
                }],
            }
            private_file.write_text(json.dumps(draft, ensure_ascii=False))
            subset, report = prepare_translation_reuse(
                [private_file], "nhsk2", 2, root=root, allow_partial=True
            )
            self.assertEqual(
                [x["pointer"] for x in subset["translations"]],
                ["/grammar/0/examples/0/translation"]
            )
            self.assertEqual(report["target_mirrored_card_maps"], 1)
            self.assertEqual(report["target_display_maps_uncovered"], 1)
            self.assertEqual(report["target_locale_values_uncovered"], 3)
            self.assertEqual(target_file.read_bytes(), original_target)
            self.assertNotIn("PROTECTED", json.dumps(report))

    def test_private_reuse_module_never_publishes_a_lesson_or_answers(self):
        source = (ROOT / "scripts/i18n_editor_translation_reuse.py").read_text(
            encoding="utf-8"
        )
        for forbidden in ("httpx.", "requests.", "FastAPI(", "APIRouter(",
                          "send_file(", "write_bytes(", "app.mount(",
                          "source_path.write_text("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

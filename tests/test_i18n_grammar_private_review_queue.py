"""P3 136-context PRIVATE human review queue and SHA-bound blank drafts."""
import json
from pathlib import Path
import stat
import tempfile
import unittest

from scripts.i18n_grammar_private_review_queue import (
    assemble_private_review_queue, prepare_private_context_review,
)
from scripts.i18n_editor_translation_draft import validate_editor_draft

ROOT = Path(__file__).resolve().parents[1]
TRACKS = ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")


def lesson(track, number, zh="秘密中文", title="规则"):
    group = {
        "no": 1,
        "title": {"uz": title, "ru": title, "tj": title},
        "title_zh": title,
        "rule": {"uz": "RULE", "ru": "RULE", "tj": "RULE"},
        "examples": [{
            "zh": zh, "pinyin": "pīnyīn",
            "translation": {"uz": "", "ru": "", "tj": ""},
            "options": ["SECRET_OPTION"], "correct_index": 0,
        }],
    }
    return {
        "schema_version": 2, "level": track,
        "lesson_id": number, "part_no": 1,
        "grammar": [group],
        "sections": [{"cards": [
            {"type": "reverse_builder", "answer_tokens": ["SECRET_TOKEN"],
             "requires_pro": True},
        ]}],
    }


def save(root, track, n, data):
    base = root / "app/static/course_v3_data" / track
    base.mkdir(parents=True, exist_ok=True)
    (base / f"lesson_{n:02d}.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8",
    )


class PrivateGrammarReviewQueueTests(unittest.TestCase):
    def test_real_complete_inventory_and_prior_lesson20_reuse(self):
        source = ROOT / "app/static/course_v3_data/nhsk2/lesson_16.json"
        original = source.read_bytes()
        queue, drafts = assemble_private_review_queue(ROOT)
        self.assertEqual(queue["source_lessons_scanned"], 746)
        self.assertEqual(queue["affected_lessons"], 48)
        self.assertEqual(queue["missing_original_maps"], 272)
        self.assertEqual(queue["unique_exact_contexts"], 136)
        self.assertEqual(queue["repeated_original_occurrences"], 136)
        self.assertEqual(queue["original_locale_cells"], 816)
        self.assertEqual(queue["independent_locale_cells_to_review"], 408)
        self.assertEqual(sum(len(d["translations"]) for d in drafts.values()), 136)
        self.assertFalse(queue["ready_to_ship"])
        lesson20 = [
            c for c in queue["contexts"]
            if any(loc["source_file"].endswith("/nhsk2/lesson_20.json")
                   for loc in c["occurrences"])
        ]
        self.assertEqual(len(lesson20), 12)
        for context in lesson20:
            self.assertTrue(any(
                loc["source_file"].endswith(
                    ("/nhsk2/lesson_16.json", "/nhsk2/lesson_17.json",
                     "/nhsk2/lesson_18.json"))
                for loc in context["occurrences"]
            ))
        self.assertEqual(source.read_bytes(), original)

    def test_private_files_permissions_and_blank_drafts_unapproved(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "review"
            status = prepare_private_context_review(folder, root=ROOT)
            self.assertEqual(status["unique_exact_contexts"], 136)
            self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE((folder / "drafts").stat().st_mode), 0o700)
            queue_file = folder / "review_queue.json"
            self.assertEqual(stat.S_IMODE(queue_file.stat().st_mode), 0o600)
            queue = json.loads(queue_file.read_text(encoding="utf-8"))
            self.assertEqual(len(queue["contexts"]), 136)
            paths = list((folder / "drafts").glob("*.json"))
            self.assertEqual(len(paths), status["private_draft_files"])
            for path in paths:
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
                draft = json.loads(path.read_text(encoding="utf-8"))
                raw = (ROOT / draft["source_file"]).read_bytes()
                with self.assertRaises(ValueError):
                    validate_editor_draft(raw, draft)
                self.assertTrue(all(
                    x["values"] == {"uz": "", "ru": "", "tj": ""}
                    for x in draft["translations"]
                ))
            with self.assertRaisesRegex(ValueError, "must not exist"):
                prepare_private_context_review(folder, root=ROOT)

    def test_exact_context_duplicates_and_protected_answers_not_copied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "checkout"
            root.mkdir()
            for track in TRACKS:
                save(root, track, 1, lesson(track, 1))
            queue, drafts = assemble_private_review_queue(root)
            self.assertEqual(queue["unique_exact_contexts"], 1)
            self.assertEqual(queue["missing_original_maps"], 7)
            self.assertEqual(queue["independent_locale_cells_to_review"], 3)
            self.assertEqual(len(drafts), 1)
            self.assertEqual(len(queue["contexts"][0]["occurrences"]), 7)
            private = json.dumps(queue, ensure_ascii=False)
            for prohibited in ("SECRET_OPTION", "SECRET_TOKEN",
                               "correct_index", "answer_tokens", "requires_pro"):
                self.assertNotIn(prohibited, private)
            self.assertIn("秘密中文", private)
            with self.assertRaisesRegex(ValueError, "outside"):
                prepare_private_context_review(root / "private", root=root)

    def test_different_chinese_or_grammar_rule_cannot_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "checkout"
            root.mkdir()
            for track in TRACKS:
                if track == "nhsk2":
                    save(root, track, 1, lesson(track, 1, "A"))
                    save(root, track, 2, lesson(track, 2, "B"))
                    save(root, track, 3, lesson(track, 3, "A", title="other"))
                else:
                    data = lesson(track, 1)
                    data["grammar"] = []
                    save(root, track, 1, data)
            queue, drafts = assemble_private_review_queue(root)
            self.assertEqual(queue["unique_exact_contexts"], 3)
            self.assertEqual(queue["repeated_original_occurrences"], 0)
            self.assertEqual(sum(len(d["translations"]) for d in drafts.values()), 3)

    def test_partial_locale_and_mismatched_mirror_fail_before_any_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "checkout"
            root.mkdir()
            for track in TRACKS:
                data = lesson(track, 1)
                if track != "nhsk2":
                    data["grammar"] = []
                else:
                    data["grammar"][0]["examples"][0]["translation"]["tj"] = "done"
                save(root, track, 1, data)
            target = Path(tmp) / "uncreated"
            with self.assertRaises(ValueError):
                prepare_private_context_review(target, root=root)
            self.assertFalse(target.exists())
            data = lesson("nhsk2", 1)
            mirror = json.loads(json.dumps(data["grammar"][0]))
            mirror["examples"][0]["zh"] = "DIVERGENT"
            data["sections"][0]["cards"].append({"type": "_grammar", "g": mirror})
            save(root, "nhsk2", 1, data)
            with self.assertRaises(ValueError):
                prepare_private_context_review(target, root=root)
            self.assertFalse(target.exists())

    def test_source_revision_pinned_and_no_public_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "checkout"
            root.mkdir()
            for track in TRACKS:
                save(root, track, 1, lesson(track, 1))
            dest = Path(tmp) / "private"
            prepare_private_context_review(dest, root=root)
            draft = json.loads(next((dest / "drafts").glob("*.json")).read_text())
            draft["translations"][0]["values"] = {
                "uz": "Tarjima", "ru": "Перевод", "tj": "Тарҷума",
            }
            original = (root / draft["source_file"]).read_bytes()
            self.assertEqual(validate_editor_draft(original, draft)["validated_display_maps"], 1)
            (root / draft["source_file"]).write_bytes(original + b" ")
            with self.assertRaisesRegex(ValueError, "revision"):
                validate_editor_draft((root / draft["source_file"]).read_bytes(), draft)
            source = (ROOT / "scripts/i18n_grammar_private_review_queue.py").read_text()
            for forbidden in ("requests.", "httpx.", "APIRouter(", "FastAPI(",
                              "send_file(", "write_bytes(", "translate_text("):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

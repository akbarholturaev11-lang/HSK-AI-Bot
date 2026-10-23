"""P3 private editor draft batch: coverage, stale SHA, no public/answer leaks."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_editor_translation_batch import audit_translation_draft_batch
from scripts.i18n_lesson_locale_gap_review_queue import _git_blob_sha1

ROOT = Path(__file__).resolve().parents[1]
TRACKS = ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")


def _fake_source(root, track):
    folder = root / "app/static/course_v3_data" / track
    folder.mkdir(parents=True)
    source_path = folder / "lesson_01.json"
    data = {
        "schema_version": 2, "level": track,
        "lesson_id": 1, "part_no": 1,
        "grammar": [{"examples": [{
            "zh": "SECRET_SOURCE_HANZI",
            "translation": {"uz": "", "ru": "", "tj": ""},
        }]}],
        "sections": [{"cards": [{
            "type": "reverse_builder",
            "answer_tokens": ["SECRET_ANSWER"],
            "correct_index": 0, "options": ["SECRET_OPTION"],
        }]}],
    }
    source_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return source_path


def _fake_draft(source_path, root):
    return {
        "schema_version": 1,
        "kind": "p3_editor_translation_draft",
        "source_file": source_path.relative_to(root).as_posix(),
        "source_git_blob_sha1": _git_blob_sha1(source_path.read_bytes()),
        "translations": [{
            "pointer": "/grammar/0/examples/0/translation",
            "values": {
                "uz": "Намунаи тоҷикӣ эмас", "ru": "Пример",
                "tj": "Намунаи тоҷикӣ",
            },
        }],
    }


class EditorTranslationBatchTests(unittest.TestCase):
    def test_real_repo_empty_draft_dir_records_all_816_missing_values(self):
        with tempfile.TemporaryDirectory() as private_dir:
            report = audit_translation_draft_batch(Path(private_dir), root=ROOT)
        self.assertEqual(report["source_lessons_scanned"], 746)
        self.assertEqual(report["affected_source_lessons"], 48)
        self.assertEqual(report["missing_display_maps_at_source"], 272)
        self.assertEqual(report["required_locale_values_at_source"], 816)
        self.assertEqual(report["remaining_locale_values"], 816)
        self.assertEqual(report["validated_editor_draft_files"], 0)
        self.assertFalse(report["ready_to_ship"])

    def test_partial_then_complete_coverage_does_not_change_sources(self):
        with tempfile.TemporaryDirectory() as scratch:
            base = Path(scratch)
            root = base / "checkout"
            draft_dir = base / "private_drafts"
            draft_dir.mkdir()
            sources = [_fake_source(root, track) for track in TRACKS]
            originals = {s: s.read_bytes() for s in sources}
            drafts = [_fake_draft(path, root) for path in sources]
            (draft_dir / "draft_01.json").write_text(
                json.dumps(drafts[0], ensure_ascii=False), encoding="utf-8"
            )
            partial = audit_translation_draft_batch(draft_dir, root=root)
            self.assertEqual(partial["validated_display_maps"], 1)
            self.assertEqual(partial["remaining_display_maps"], 6)
            self.assertEqual(partial["remaining_locale_values"], 18)
            with self.assertRaisesRegex(ValueError, "all current"):
                audit_translation_draft_batch(
                    draft_dir, root=root, require_complete=True,
                )
            for i, draft in enumerate(drafts[1:], 2):
                (draft_dir / f"draft_{i:02d}.json").write_text(
                    json.dumps(draft, ensure_ascii=False), encoding="utf-8"
                )
            full = audit_translation_draft_batch(
                draft_dir, root=root, require_complete=True,
            )
            self.assertEqual(full["validated_editor_draft_files"], 7)
            self.assertEqual(full["validated_locale_values"], 21)
            self.assertEqual(full["remaining_display_maps"], 0)
            self.assertEqual(
                full["status"],
                "STRUCTURALLY_COMPLETE_HUMAN_LANGUAGE_REVIEW_REQUIRED",
            )
            self.assertFalse(full["ready_to_ship"])
            self.assertEqual(full["source_lessons_mutated"], 0)
            for s in sources:
                self.assertEqual(s.read_bytes(), originals[s])
            encoded = json.dumps(full, ensure_ascii=False)
            for secret in ("SECRET", "Пример", "Намунаи", "SECRET_OPTION"):
                self.assertNotIn(secret, encoded)

    def test_stale_draft_duplicate_pointer_and_unknown_lesson_rejected(self):
        with tempfile.TemporaryDirectory() as scratch:
            base = Path(scratch)
            root = base / "checkout"
            folder = base / "private_drafts"
            folder.mkdir()
            for track in TRACKS:
                source = _fake_source(root, track)
            original = _fake_draft(
                root / "app/static/course_v3_data/nhsk2/lesson_01.json", root,
            )
            p1 = folder / "one.json"
            p1.write_text(json.dumps(original), encoding="utf-8")
            p2 = folder / "two.json"
            p2.write_text(json.dumps(original), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                audit_translation_draft_batch(folder, root=root)
            p2.unlink()
            stale = dict(original)
            stale["source_git_blob_sha1"] = "0" * 40
            p1.write_text(json.dumps(stale), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stale"):
                audit_translation_draft_batch(folder, root=root)
            unknown = dict(original)
            unknown["source_file"] = "app/static/course_v3_data/nhsk2/lesson_02.json"
            p1.write_text(json.dumps(unknown), encoding="utf-8")
            with self.assertRaises(ValueError):
                audit_translation_draft_batch(folder, root=root)

    def test_public_directory_symlink_and_unexpected_files_rejected(self):
        with tempfile.TemporaryDirectory() as scratch:
            base = Path(scratch)
            root = base / "checkout"
            folder = base / "private_drafts"
            folder.mkdir()
            for track in TRACKS:
                _fake_source(root, track)
            with self.assertRaisesRegex(ValueError, "inside repository"):
                audit_translation_draft_batch(root / "app/static/course_v3_data", root=root)
            (folder / "warning.txt").write_text("SECRET_TEXT", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unexpected"):
                audit_translation_draft_batch(folder, root=root)
            (folder / "warning.txt").unlink()
            symlink = folder / "hidden.json"
            symlink.symlink_to(
                root / "app/static/course_v3_data/nhsk2/lesson_01.json"
            )
            with self.assertRaisesRegex(ValueError, "unexpected"):
                audit_translation_draft_batch(folder, root=root)

    def test_batch_source_code_has_no_mutations_or_public_endpoints(self):
        source = (ROOT / "scripts/i18n_editor_translation_batch.py").read_text(
            encoding="utf-8",
        )
        for forbidden in (
            "write_text(", "write_bytes(", "requests.", "httpx.",
            "FastAPI(", "APIRouter(", "send_file(", "upload_file(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

"""Private P3 context counts, duplicate conflicts, and source invariants."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_editor_context_progress import audit_private_context_progress
from scripts.i18n_lesson_locale_gap_review_queue import _git_blob_sha1

ROOT = Path(__file__).resolve().parents[1]
TRACKS = ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")


def write_lesson(root, track, n=1, *, zh="完全一样", mirror=False):
    group = {
        "no": 1, "title": {"uz": "rule", "ru": "rule", "tj": "rule"},
        "title_zh": "规则",
        "rule": {"uz": "R", "ru": "R", "tj": "R"},
        "examples": [{"zh": zh, "pinyin": "wán quán",
                      "translation": {"uz": "", "ru": "", "tj": ""}}],
    }
    payload = {
        "schema_version": 2, "level": track, "lesson_id": n, "part_no": 1,
        "grammar": [group],
        "sections": [{"cards": [
            {"type": "reverse_builder", "answer_tokens": ["SECRET_TOKEN"],
             "requires_pro": True, "correct_index": 0},
        ]}],
    }
    if mirror:
        payload["sections"][0]["cards"].append({
            "type": "_grammar", "g": json.loads(json.dumps(group)),
        })
    folder = root / "app/static/course_v3_data" / track
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"lesson_{n:02d}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def candidate(root, path, uz="Candidate"):
    return {
        "schema_version": 1, "kind": "p3_editor_translation_draft",
        "source_file": path.relative_to(root).as_posix(),
        "source_git_blob_sha1": _git_blob_sha1(path.read_bytes()),
        "translations": [{
            "pointer": "/grammar/0/examples/0/translation",
            "values": {"uz": uz, "ru": "Перевод", "tj": "Тарҷума"},
        }],
    }


class PrivateContextProgressTests(unittest.TestCase):
    def fixture(self, top):
        root = top / "checkout"
        root.mkdir()
        return root, {t: write_lesson(root, t) for t in TRACKS}

    def test_real_746_sources_empty_drafts(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = audit_private_context_progress(Path(tmp), root=ROOT)
        self.assertEqual(report["source_lessons_scanned"], 746)
        self.assertEqual(report["total_unique_contexts"], 136)
        self.assertEqual(report["source_translation_maps"], 272)
        self.assertEqual(report["independent_locale_values_remaining"], 408)
        self.assertEqual(report["source_locale_values_outstanding"], 816)
        self.assertEqual(report["contexts_with_structural_candidate"], 0)
        self.assertFalse(report["human_language_approval_verified"])

    def test_same_context_two_drafts_one_candidate_and_five_reuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            top = Path(tmp)
            root, lessons = self.fixture(top)
            private = top / "drafts"
            private.mkdir()
            for i, track in enumerate(("hsk1", "hsk2")):
                (private / f"{i}.json").write_text(json.dumps(candidate(root, lessons[track])))
            report = audit_private_context_progress(private, root=root)
            self.assertEqual(report["total_unique_contexts"], 1)
            self.assertEqual(report["contexts_with_structural_candidate"], 1)
            self.assertEqual(report["source_maps_with_validated_draft"], 2)
            self.assertEqual(report["additional_exact_context_reuse_opportunities"], 5)
            self.assertEqual(report["validated_private_draft_files"], 2)
            s = json.dumps(report, ensure_ascii=False)
            for secret in ("SECRET_TOKEN", "完全一样", "Candidate", "correct_index"):
                self.assertNotIn(secret, s)

    def test_one_mirror_verified_not_independently_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            top = Path(tmp)
            root, lessons = self.fixture(top)
            lessons["hsk1"] = write_lesson(root, "hsk1", mirror=True)
            private = top / "drafts"
            private.mkdir()
            (private / "a.json").write_text(json.dumps(candidate(root, lessons["hsk1"])))
            report = audit_private_context_progress(private, root=root)
            self.assertEqual(report["verified_mirrored_card_maps"], 1)
            self.assertEqual(report["source_maps_with_validated_draft"], 1)
            self.assertEqual(report["additional_exact_context_reuse_opportunities"], 6)

    def test_identical_context_disagreeing_draft_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            top = Path(tmp)
            root, lessons = self.fixture(top)
            private = top / "drafts"
            private.mkdir()
            (private / "a.json").write_text(json.dumps(candidate(root, lessons["hsk1"])))
            (private / "b.json").write_text(json.dumps(candidate(
                root, lessons["hsk2"], "Different candidate"
            )))
            with self.assertRaisesRegex(ValueError, "conflicting"):
                audit_private_context_progress(private, root=root)

    def test_stale_sha_and_duplicate_pointer_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            top = Path(tmp)
            root, lessons = self.fixture(top)
            private = top / "drafts"
            private.mkdir()
            d = candidate(root, lessons["hsk1"])
            d["source_git_blob_sha1"] = "f" * 40
            a = private / "a.json"
            a.write_text(json.dumps(d))
            with self.assertRaises(ValueError):
                audit_private_context_progress(private, root=root)
            d = candidate(root, lessons["hsk1"])
            a.write_text(json.dumps(d))
            (private / "b.json").write_text(json.dumps(d))
            with self.assertRaises(ValueError):
                audit_private_context_progress(private, root=root)
            (private / "b.json").unlink()
            d["translations"][0]["values"]["tj"] = ""
            a.write_text(json.dumps(d))
            with self.assertRaises(ValueError):
                audit_private_context_progress(private, root=root)

    def test_checkout_or_symlink_and_unknown_draft_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            top = Path(tmp)
            root, lessons = self.fixture(top)
            within = root / "drafts"
            within.mkdir()
            with self.assertRaisesRegex(ValueError, "inside repository"):
                audit_private_context_progress(within, root=root)
            private = top / "drafts"
            private.mkdir()
            other = top / "candidate.json"
            other.write_text(json.dumps(candidate(root, lessons["hsk1"])))
            (private / "candidate.json").symlink_to(other)
            with self.assertRaises(ValueError):
                audit_private_context_progress(private, root=root)

    def test_different_chinese_contexts_and_source_byte_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            top = Path(tmp)
            root, lessons = self.fixture(top)
            lessons["hsk2"] = write_lesson(root, "hsk2", zh="完全不同")
            a, b = lessons["hsk1"], lessons["hsk2"]
            bytes_a, bytes_b = a.read_bytes(), b.read_bytes()
            private = top / "drafts"
            private.mkdir()
            (private / "a.json").write_text(json.dumps(candidate(root, a)))
            (private / "b.json").write_text(json.dumps(candidate(root, b)))
            result = audit_private_context_progress(private, root=root)
            self.assertEqual(result["total_unique_contexts"], 2)
            self.assertEqual(result["contexts_with_structural_candidate"], 2)
            self.assertEqual(result["source_maps_with_validated_draft"], 2)
            self.assertEqual(a.read_bytes(), bytes_a)
            self.assertEqual(b.read_bytes(), bytes_b)


if __name__ == "__main__":
    unittest.main()

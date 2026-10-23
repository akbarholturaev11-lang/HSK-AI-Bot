"""P3 private editor backlog: source SHA, independent contexts and privacy."""
from copy import deepcopy
import json
from pathlib import Path
import stat
import tempfile
import unittest

from scripts.i18n_editor_backlog import prepare_editor_backlog
from scripts.i18n_editor_translation_draft import validate_editor_draft
from scripts.i18n_lesson_locale_gap_review_queue import _git_blob_sha1

ROOT = Path(__file__).resolve().parents[1]
TRACKS = ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")


def real_candidate(root, number):
    path = root / f"app/static/course_v3_data/nhsk2/lesson_{number:02d}.json"
    data = json.loads(path.read_bytes())
    fields = []
    for gi, group in enumerate(data["grammar"]):
        for ei, example in enumerate(group["examples"]):
            if example.get("translation") == {"uz": "", "ru": "", "tj": ""}:
                fields.append({
                    "pointer": f"/grammar/{gi}/examples/{ei}/translation",
                    "values": {
                        "uz": f"private sample UZ {number}-{gi}-{ei}",
                        "ru": f"private sample RU {number}-{gi}-{ei}",
                        "tj": f"private sample TJ {number}-{gi}-{ei}",
                    },
                })
    return {
        "schema_version": 1, "kind": "p3_editor_translation_draft",
        "source_file": path.relative_to(root).as_posix(),
        "source_git_blob_sha1": _git_blob_sha1(path.read_bytes()),
        "translations": fields,
    }


def setup_three(temp):
    seed = temp / "private-candidates"
    seed.mkdir()
    for n in (16, 17, 18):
        (seed / f"seed_{n}.json").write_text(
            json.dumps(real_candidate(ROOT, n), ensure_ascii=False), encoding="utf-8"
        )
    return seed


class EditorBacklogTests(unittest.TestCase):
    def test_all_136_contexts_without_private_candidates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dest = root / "review"
            result = prepare_editor_backlog(dest, root=ROOT)
            self.assertEqual(result["total_unique_contexts"], 136)
            self.assertEqual(result["contexts_needing_candidate"], 136)
            self.assertEqual(result["independent_locale_values_to_author"], 408)
            self.assertEqual(result["contexts_with_candidate_unapproved"], 0)
            self.assertEqual(result["human_approved_contexts"], 0)
            self.assertEqual(stat.S_IMODE(dest.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE((dest / "drafts").stat().st_mode), 0o700)
            files = list((dest / "drafts").glob("*.json"))
            self.assertEqual(len(files), result["pending_blank_draft_files"])
            self.assertEqual(sum(len(json.loads(f.read_text())["translations"]) for f in files), 136)
            for f in files:
                self.assertEqual(stat.S_IMODE(f.stat().st_mode), 0o600)
                draft = json.loads(f.read_text())
                with self.assertRaises(ValueError):
                    validate_editor_draft((ROOT / draft["source_file"]).read_bytes(), draft)
            with self.assertRaisesRegex(ValueError, "must not exist"):
                prepare_editor_backlog(dest, root=ROOT)

    def test_real_12_existing_context_candidates_124_to_author(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed = setup_three(root)
            dest = root / "backlog"
            original_seed = [f.read_bytes() for f in sorted(seed.iterdir())]
            before_20 = (ROOT / "app/static/course_v3_data/nhsk2/lesson_20.json").read_bytes()
            counts = prepare_editor_backlog(dest, candidate_dir=seed, root=ROOT)
            self.assertEqual(counts["contexts_with_candidate_unapproved"], 12)
            self.assertEqual(counts["contexts_needing_candidate"], 124)
            self.assertEqual(counts["independent_locale_values_to_author"], 372)
            self.assertEqual(counts["candidate_locale_values_unapproved"], 36)
            self.assertEqual(counts["human_approved_contexts"], 0)
            review = json.loads((dest / "editor_backlog.json").read_text())
            self.assertEqual(len(review["existing_candidates_awaiting_human_review"]), 12)
            self.assertEqual(len(review["pending_candidate_authoring"]), 124)
            self.assertEqual(sum(len(json.loads(f.read_text())["translations"])
                                 for f in (dest / "drafts").iterdir()), 124)
            self.assertTrue(all(
                any(loc["source_file"].endswith(("lesson_16.json", "lesson_17.json", "lesson_18.json"))
                    for loc in c["private_candidate_origins"])
                for c in review["existing_candidates_awaiting_human_review"]
            ))
            serialized = (dest / "editor_backlog.json").read_text()
            for forbidden in ("private sample UZ", "private sample RU",
                              "private sample TJ", "correct_index", "answer_tokens"):
                self.assertNotIn(forbidden, serialized)
            self.assertEqual(stat.S_IMODE((dest / "editor_backlog.json").stat().st_mode), 0o600)
            self.assertEqual([f.read_bytes() for f in sorted(seed.iterdir())], original_seed)
            self.assertEqual(
                (ROOT / "app/static/course_v3_data/nhsk2/lesson_20.json").read_bytes(),
                before_20,
            )

    def test_conflicting_duplicate_context_rejected_before_mkdir(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed = setup_three(root)
            d = real_candidate(ROOT, 20)
            (seed / "lesson20_conflict.json").write_text(json.dumps(d))
            target = root / "out"
            with self.assertRaisesRegex(ValueError, "conflicting"):
                prepare_editor_backlog(target, candidate_dir=seed)
            self.assertFalse(target.exists())

    def test_stale_revision_or_incomplete_locale_rejected_before_mkdir(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed = setup_three(root)
            file = seed / "seed_16.json"
            draft = json.loads(file.read_text())
            draft["source_git_blob_sha1"] = "0" * 40
            file.write_text(json.dumps(draft))
            target = root / "out"
            with self.assertRaises(ValueError):
                prepare_editor_backlog(target, candidate_dir=seed)
            self.assertFalse(target.exists())
            draft = real_candidate(ROOT, 16)
            draft["translations"][0]["values"]["tj"] = ""
            file.write_text(json.dumps(draft))
            with self.assertRaises(ValueError):
                prepare_editor_backlog(target, candidate_dir=seed)
            self.assertFalse(target.exists())

    def test_private_checkout_symlinks_and_bad_destinations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed = setup_three(root)
            with self.assertRaises(ValueError):
                prepare_editor_backlog(ROOT / "localization" / "private-output",
                                       candidate_dir=seed)
            with self.assertRaisesRegex(ValueError, "inside candidate"):
                prepare_editor_backlog(seed / "inside", candidate_dir=seed)
            with self.assertRaisesRegex(ValueError, "must not exist"):
                prepare_editor_backlog(seed, candidate_dir=seed)
            (seed / "bad.json").symlink_to(seed / "seed_16.json")
            dest = root / "failed"
            with self.assertRaises(ValueError):
                prepare_editor_backlog(dest, candidate_dir=seed)
            self.assertFalse(dest.exists())

    def test_review_all_source_revisions_without_rewriting(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dest = root / "private"
            result = prepare_editor_backlog(dest, root=ROOT)
            queue = json.loads((dest / "editor_backlog.json").read_text())
            self.assertEqual(queue["original_source_maps"], 272)
            self.assertEqual(queue["original_locale_cells"], 816)
            self.assertFalse(queue["ready_to_ship"])
            self.assertFalse(result["ready_to_ship"])
            self.assertTrue(all(
                c["review_status"] == "NEEDS_TRANSLATION_CANDIDATE"
                and c["human_language_approval_verified"] is False
                for c in queue["pending_candidate_authoring"]
            ))

    def test_synthetic_same_context_one_representative_all_tracks(self):
        with tempfile.TemporaryDirectory() as temp:
            top = Path(temp)
            checkout = top / "checkout"
            checkout.mkdir()
            for track in TRACKS:
                folder = checkout / "app/static/course_v3_data" / track
                folder.mkdir(parents=True)
                group = {
                    "no": 1, "title": {"uz": "R", "ru": "R", "tj": "R"},
                    "title_zh": "规则",
                    "rule": {"uz": "R", "ru": "R", "tj": "R"},
                    "examples": [{"zh": "来", "pinyin": "lái",
                                  "translation": {"uz": "", "ru": "", "tj": ""}}],
                }
                data = {
                    "schema_version": 2, "level": track, "lesson_id": 1,
                    "part_no": 1, "grammar": [deepcopy(group)], "sections": [],
                }
                (folder / "lesson_01.json").write_text(
                    json.dumps(data, ensure_ascii=False), encoding="utf-8"
                )
            result = prepare_editor_backlog(top / "private", root=checkout)
            self.assertEqual(result["total_unique_contexts"], 1)
            self.assertEqual(result["contexts_needing_candidate"], 1)
            self.assertEqual(result["independent_locale_values_to_author"], 3)
            self.assertEqual(result["pending_blank_draft_files"], 1)
            queue = json.loads((top / "private" / "editor_backlog.json").read_text())
            self.assertEqual(len(queue["pending_candidate_authoring"][0]["occurrences"]), 7)


if __name__ == "__main__":
    unittest.main()

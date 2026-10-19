"""P3 private all-lesson reuse: real source, conflict and privacy regressions."""
import json
from pathlib import Path
import stat
import tempfile
import unittest

from scripts.i18n_editor_bulk_reuse import prepare_private_reuse_batch
from scripts.i18n_editor_translation_batch import audit_translation_draft_batch
from scripts.i18n_editor_translation_draft import validate_editor_draft
from scripts.i18n_editor_translation_reuse import prepare_translation_reuse
from scripts.i18n_lesson_locale_gap_review_queue import _git_blob_sha1

ROOT = Path(__file__).resolve().parents[1]


def sample(root, lesson):
    file = root / f"app/static/course_v3_data/nhsk2/lesson_{lesson:02d}.json"
    source = json.loads(file.read_text())
    fields = []
    for gi, grammar in enumerate(source["grammar"]):
        for ei, example in enumerate(grammar["examples"]):
            if example.get("translation") == {"uz": "", "ru": "", "tj": ""}:
                fields.append({
                    "pointer": f"/grammar/{gi}/examples/{ei}/translation",
                    "values": {
                        "uz": f"UZ sample {lesson}-{gi}-{ei}",
                        "ru": f"RU sample {lesson}-{gi}-{ei}",
                        "tj": f"TJ sample {lesson}-{gi}-{ei}",
                    },
                })
    return {
        "schema_version": 1, "kind": "p3_editor_translation_draft",
        "source_file": file.relative_to(root).as_posix(),
        "source_git_blob_sha1": _git_blob_sha1(file.read_bytes()),
        "translations": fields,
    }


def seeds(base, nums):
    folder = base / "seeds"
    folder.mkdir()
    paths = []
    for n in nums:
        path = folder / f"lesson_{n}.json"
        path.write_text(json.dumps(sample(ROOT, n)), encoding="utf-8")
        paths.append(path)
    return folder, paths


class PrivateBulkReuseTests(unittest.TestCase):
    def test_real_three_origins_generate_one_full_lesson20_draft(self):
        before = {
            n: (ROOT / f"app/static/course_v3_data/nhsk2/lesson_{n:02d}.json").read_bytes()
            for n in (16, 17, 18, 20)
        }
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source, original_files = seeds(base, (16, 17, 18))
            original_seed_bytes = [p.read_bytes() for p in original_files]
            destination = base / "output"
            result = prepare_private_reuse_batch(source, destination, root=ROOT)
            self.assertEqual(result["candidate_unique_contexts"], 12)
            self.assertEqual(result["additional_original_maps_reused"], 12)
            self.assertEqual(result["additional_locale_values_reused"], 36)
            self.assertEqual(result["new_private_draft_files"], 1)
            self.assertEqual(result["original_source_maps_still_missing"], 248)
            self.assertEqual(result["original_locale_values_still_missing"], 744)
            self.assertFalse(result["ready_to_ship"])
            self.assertFalse(result["human_language_approval_verified"])
            files = list(destination.iterdir())
            self.assertEqual(len(files), 1)
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(files[0].stat().st_mode), 0o600)
            candidate = json.loads(files[0].read_text())
            self.assertEqual(candidate["source_file"],
                             "app/static/course_v3_data/nhsk2/lesson_20.json")
            self.assertEqual(len(candidate["translations"]), 12)
            self.assertEqual(
                validate_editor_draft(before[20], candidate)["validated_display_maps"], 12
            )
            self.assertEqual(
                audit_translation_draft_batch(destination, root=ROOT)["validated_display_maps"],
                12,
            )
            self.assertEqual([p.read_bytes() for p in original_files], original_seed_bytes)
            display = json.dumps(result, ensure_ascii=False)
            for forbidden in ("UZ sample", "RU sample", "TJ sample", "correct_index",
                              "answer_tokens", "requires_pro"):
                self.assertNotIn(forbidden, display)
        for n, original in before.items():
            self.assertEqual(
                (ROOT / f"app/static/course_v3_data/nhsk2/lesson_{n:02d}.json").read_bytes(),
                original,
            )

    def test_real_single_origin_only_six_placements_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source, _ = seeds(base, (16,))
            output = base / "drafts"
            report = prepare_private_reuse_batch(source, output, root=ROOT)
            self.assertEqual(report["candidate_unique_contexts"], 6)
            self.assertEqual(report["additional_original_maps_reused"], 6)
            self.assertEqual(report["original_source_maps_still_missing"], 260)
            self.assertEqual(len(json.loads(next(output.iterdir()).read_text())
                                 ["translations"]), 6)

    def test_mismatching_suggestions_reject_before_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source, _ = seeds(base, (16, 20))
            dest = base / "output"
            with self.assertRaisesRegex(ValueError, "conflicting"):
                prepare_private_reuse_batch(source, dest, root=ROOT)
            self.assertFalse(dest.exists())

    def test_empty_stale_and_partial_candidates_do_not_create_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            empty = base / "empty"
            empty.mkdir()
            with self.assertRaisesRegex(ValueError, "no validated"):
                prepare_private_reuse_batch(empty, base / "out-empty", root=ROOT)
            self.assertFalse((base / "out-empty").exists())
            source, paths = seeds(base, (16,))
            draft = json.loads(paths[0].read_text())
            draft["source_git_blob_sha1"] = "f" * 40
            paths[0].write_text(json.dumps(draft))
            with self.assertRaises(ValueError):
                prepare_private_reuse_batch(source, base / "out-stale", root=ROOT)
            self.assertFalse((base / "out-stale").exists())
            draft = sample(ROOT, 16)
            draft["translations"][0]["values"]["tj"] = ""
            paths[0].write_text(json.dumps(draft))
            with self.assertRaises(ValueError):
                prepare_private_reuse_batch(source, base / "out-partial", root=ROOT)
            self.assertFalse((base / "out-partial").exists())

    def test_no_remaining_repeated_locations_is_safe_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source, files = seeds(base, (16, 17, 18))
            # Valid lesson20 reuse agrees with the three original suggestions,
            # unlike an independently invented lesson20 candidate.
            target, _ = prepare_translation_reuse(files, "nhsk2", 20, root=ROOT)
            (source / "lesson_20.json").write_text(json.dumps(target))
            dest = base / "finished"
            with self.assertRaisesRegex(ValueError, "no remaining"):
                prepare_private_reuse_batch(source, dest, root=ROOT)
            self.assertFalse(dest.exists())

    def test_output_boundaries_and_symlinked_input_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source, paths = seeds(base, (16,))
            with self.assertRaises(ValueError):
                prepare_private_reuse_batch(
                    source, ROOT / "localization" / "private-output", root=ROOT
                )
            with self.assertRaisesRegex(ValueError, "inside"):
                prepare_private_reuse_batch(source, source / "nested", root=ROOT)
            with self.assertRaisesRegex(ValueError, "must not exist"):
                prepare_private_reuse_batch(source, source, root=ROOT)
            other = base / "already"
            other.mkdir()
            with self.assertRaisesRegex(ValueError, "must not exist"):
                prepare_private_reuse_batch(source, other, root=ROOT)
            (source / "alias.json").symlink_to(paths[0])
            with self.assertRaises(ValueError):
                prepare_private_reuse_batch(source, base / "bad", root=ROOT)
            self.assertFalse((base / "bad").exists())

    def test_nonpublisher_static_guard(self):
        code = (ROOT / "scripts/i18n_editor_bulk_reuse.py").read_text()
        for forbidden in ("requests.", "httpx.", "FastAPI(", "APIRouter(", "send_file(",
                          "write_bytes(", "source_path.write_text(", "correct_index"):
            self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()

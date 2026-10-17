"""P0 blob baseline and stable lesson identity guard."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_baseline_guard import check_baseline, git_blob_sha1


def fixture(path: Path, payload: str, *, track: str = "hsk1") -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    contents = payload.encode("utf-8")
    path.write_bytes(contents)
    return {
        "schema_version": 1,
        "baseline_main_commit": "abcdef123",
        "source_count": 1,
        "track_counts": {k: int(k == track) for k in (
            "hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")},
        "sources": {
            "lessons": [{
                "path": "app/static/course_v3_data/" + track + "/lesson_01.json",
                "git_blob_sha1": git_blob_sha1(contents), "bytes": len(contents),
            }],
            "legacy_content": [],
            "ui_catalog_origins": [],
            "generators": [],
        },
    }


class BaselineGuardTests(unittest.TestCase):
    def test_git_blob_sha_matches_documented_git_empty_blob(self):
        self.assertEqual(git_blob_sha1(b""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")

    def test_untouched_source_and_lesson_identity_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "app/static/course_v3_data/hsk1/lesson_01.json"
            baseline = fixture(path, '{"level":"hsk1","lesson_id":1,"title":"你好"}')
            report = check_baseline(root, baseline)
            self.assertEqual(report["review_blockers"], 0)
            self.assertEqual(report["status"], "byte_baseline_intact")
            self.assertEqual(report["lesson_tracks"]["hsk1"], 1)

    def test_changed_bytes_rejected_even_when_json_still_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "app/static/course_v3_data/hsk1/lesson_01.json"
            baseline = fixture(path, '{"level":"hsk1","lesson_id":1}')
            path.write_text('{"level":"hsk1","lesson_id":1,"subtitle":"changed"}')
            findings = check_baseline(root, baseline)["findings"]
            self.assertEqual(findings[0]["issue"], "source_bytes_changed")

    def test_missing_file_is_review_blocker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "app/static/course_v3_data/hsk1/lesson_01.json"
            baseline = fixture(path, '{"level":"hsk1","lesson_id":1}')
            path.unlink()
            result = check_baseline(root, baseline)
            self.assertEqual(result["findings"][0]["issue"], "source_missing")

    def test_identity_mismatch_detected_without_hash_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "app/static/course_v3_data/hsk1/lesson_01.json"
            baseline = fixture(path, '{"level":"hsk1","lesson_id":2}')
            result = check_baseline(root, baseline)
            self.assertEqual(result["findings"][0]["issue"], "lesson_identity_mismatch")

    def test_unsafe_paths_and_duplicate_records_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "app/static/course_v3_data/hsk1/lesson_01.json"
            baseline = fixture(path, '{"level":"hsk1","lesson_id":1}')
            row = baseline["sources"]["lessons"][0]
            row["path"] = "../secret.env"
            with self.assertRaisesRegex(ValueError, "unsafe"):
                check_baseline(root, baseline)
            row["path"] = "app/static/course_v3_data/hsk1/lesson_01.json"
            baseline["sources"]["lessons"].append(dict(row))
            baseline["source_count"] = 2
            with self.assertRaisesRegex(ValueError, "duplicate"):
                check_baseline(root, baseline)


if __name__ == "__main__":
    unittest.main()

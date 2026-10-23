"""P0 blob baseline and stable lesson identity guard."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_baseline_guard import check_baseline, git_blob_sha1, VERIFIED_UPSTREAM_MAIN_COMMIT


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

    def test_only_exact_reviewed_ui_new_blob_can_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lesson = root / "app/static/course_v3_data/hsk1/lesson_01.json"
            baseline = fixture(lesson, '{"level":"hsk1","lesson_id":1}')
            ui = root / "desktop/ui/js/i18n.js"
            ui.parent.mkdir(parents=True)
            original = b"old catalog source"
            updated = b"new catalog source"
            ui.write_bytes(original)
            old_blob = git_blob_sha1(original)
            new_blob = git_blob_sha1(updated)
            baseline["sources"]["ui_catalog_origins"].append({
                "path": "desktop/ui/js/i18n.js",
                "git_blob_sha1": old_blob,
                "bytes": len(original),
            })
            baseline["source_count"] = 2
            reviewed = {
                "schema_version": 1,
                "baseline_main_commit": baseline["baseline_main_commit"],
                "files": {
                    "desktop/ui/js/i18n.js": {
                        "baseline_sha1": old_blob,
                        "reviewed_sha1": new_blob,
                        "reason": "Reviewed common-message migration",
                    },
                },
            }
            ui.write_bytes(updated)
            self.assertEqual(check_baseline(root, baseline)["review_blockers"], 1)
            report = check_baseline(root, baseline, reviewed)
            self.assertEqual(report["review_blockers"], 0)
            self.assertEqual(report["reviewed_ui_changes"], 1)
            self.assertEqual(report["status"],
                             "byte_baseline_intact_with_reviewed_ui")
            ui.write_bytes(b"unreviewed third edit")
            self.assertEqual(check_baseline(root, baseline, reviewed)["review_blockers"], 1)

    def test_reviewed_ui_manifest_cannot_hide_changed_lesson_blob(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lesson = root / "app/static/course_v3_data/hsk1/lesson_01.json"
            baseline = fixture(lesson, '{"level":"hsk1","lesson_id":1}')
            original = baseline["sources"]["lessons"][0]["git_blob_sha1"]
            new_bytes = b'{"level":"hsk1","lesson_id":2}'
            lesson.write_bytes(new_bytes)
            reviewed = {
                "schema_version": 1,
                "baseline_main_commit": baseline["baseline_main_commit"],
                "files": {
                    "app/static/course_v3_data/hsk1/lesson_01.json": {
                        "baseline_sha1": original,
                        "reviewed_sha1": git_blob_sha1(new_bytes),
                        "reason": "Attempt to waive lesson changes",
                    },
                },
            }
            with self.assertRaisesRegex(ValueError, "non-UI"):
                check_baseline(root, baseline, reviewed)

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


    def test_pinned_upstream_main_source_and_unapproved_content_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative = "app/static/course_v3_data/hsk1/lesson_01.json"
            path = root / relative
            before = '{"level":"hsk1","lesson_id":1,"score":1}'
            baseline = fixture(path, before)
            current = b'{"level":"hsk1","lesson_id":1,"score":2}'
            path.write_bytes(current)
            record = {
                "baseline_sha1": baseline["sources"]["lessons"][0]["git_blob_sha1"],
                "upstream_main_sha1": git_blob_sha1(current),
                "group": "lessons",
                "reason": "Verified exact main source, not approval for new edits",
            }
            manifest = {
                "schema_version": 1,
                "baseline_main_commit": baseline["baseline_main_commit"],
                "upstream_main_commit": VERIFIED_UPSTREAM_MAIN_COMMIT,
                "status": "VERIFIED_MAIN_BLOB_PROVENANCE_ONLY_NOT_ASSESSMENT_CERTIFICATION",
                "purpose": "Testing pinned main source",
                "files": {relative: record},
            }
            self.assertEqual(check_baseline(root, baseline)["review_blockers"], 1)
            report = check_baseline(root, baseline, upstream_main=manifest)
            self.assertEqual(report["review_blockers"], 0)
            self.assertEqual(report["verified_upstream_main_changes"], 1)
            self.assertEqual(report["status"], "verified_main_snapshot_with_reviewed_ui")
            path.write_bytes(current.replace(b'"score":2', b'"score":3'))
            self.assertEqual(check_baseline(root, baseline, upstream_main=manifest)["review_blockers"], 1)
            path.write_bytes(current)
            altered = json.loads(json.dumps(manifest))
            altered["upstream_main_commit"] = "0" * 40
            with self.assertRaisesRegex(ValueError, "invalid verified upstream"):
                check_baseline(root, baseline, upstream_main=altered)
            altered = json.loads(json.dumps(manifest))
            altered["files"][relative]["baseline_sha1"] = "0" * 40
            with self.assertRaisesRegex(ValueError, "wrong frozen original"):
                check_baseline(root, baseline, upstream_main=altered)
            altered = json.loads(json.dumps(manifest))
            altered["files"][relative]["group"] = "ui_catalog_origins"
            with self.assertRaisesRegex(ValueError, "wrong baseline source group"):
                check_baseline(root, baseline, upstream_main=altered)
            altered = json.loads(json.dumps(manifest))
            altered["files"]["untracked/new.json"] = altered["files"].pop(relative)
            with self.assertRaisesRegex(ValueError, "unknown frozen source"):
                check_baseline(root, baseline, upstream_main=altered)

if __name__ == "__main__":
    unittest.main()

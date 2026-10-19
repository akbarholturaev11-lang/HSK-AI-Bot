"""P3 human editor queue: exact display pointers, no private answer leakage."""
import json
from pathlib import Path
import re
import tempfile
import unittest

from scripts.i18n_lesson_locale_gap_review_queue import (
    _git_blob_sha1, _missing_pointers, create_review_queue,
    verify_existing_count_queue,
)
from scripts.i18n_lesson_display_overlay_contract import _allowed, LOCALES

ROOT = Path(__file__).resolve().parents[1]
COUNT_QUEUE = ROOT / "localization/reviews/p3_nhsk2_locale_gaps_20261019.json"


class LessonLocaleGapReviewQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = create_review_queue(ROOT)

    def test_every_existing_gap_is_locatable_and_pinned(self):
        result = self.review
        self.assertEqual(result["source_lessons_scanned"], 746)
        self.assertEqual(result["affected_lessons"], 48)
        self.assertEqual(result["affected_display_maps"], 272)
        self.assertEqual(result["locale_values_to_author"], 816)
        self.assertFalse(result["ready_to_ship"])
        self.assertEqual(result["status"], "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(set(record["track"] for record in result["lessons"]), {"nhsk2"})
        self.assertEqual(len(result["lessons"]), 48)
        for record in result["lessons"]:
            with self.subTest(lesson=record["lesson_number"]):
                self.assertRegex(record["source_git_blob_sha1"], r"^[0-9a-f]{40}$")
                self.assertEqual(
                    record["source_git_blob_sha1"],
                    _git_blob_sha1((ROOT / record["source_file"]).read_bytes()),
                )
                self.assertEqual(len(record["missing_display_fields"]),
                                 len(set(item["pointer"]
                                         for item in record["missing_display_fields"])))
                for field in record["missing_display_fields"]:
                    self.assertTrue(_allowed(tuple(field["pointer"].lstrip("/").split("/"))))
                    self.assertEqual(field["issue"], "all_locales_blank")
                    self.assertEqual(field["locales_to_review"], list(LOCALES))
        verify_existing_count_queue(result, COUNT_QUEUE)

    def test_earlier_review_snapshot_detects_stale_counts(self):
        with tempfile.TemporaryDirectory() as folder:
            snapshot = json.loads(COUNT_QUEUE.read_text(encoding="utf-8"))
            snapshot["lessons"][0]["all_empty_locale_maps"] += 1
            path = Path(folder) / "stale.json"
            path.write_text(json.dumps(snapshot), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "drift"):
                verify_existing_count_queue(self.review, path)

    def test_malformed_and_partial_display_fields_are_classified_only(self):
        sample = {
            "subtitle": {"uz": "PRIVATE_UZ", "ru": "", "tj": "PRIVATE_TJ"},
            "grammar": [{"examples": [
                {"translation": {"uz": "", "ru": "", "tj": ""}},
                {"translation": {"uz": "PRIVATE_ONLY"}},
            ]}],
            "sections": [{"cards": [{"options": [
                {"uz": "SECRET_ANSWER", "ru": "SECRET", "tj": "SECRET"}
            ]}]}],
        }
        issues = _missing_pointers(sample)
        self.assertEqual([i["issue"] for i in issues],
                         ["partially_blank", "all_locales_blank", "invalid_locale_map"])
        self.assertEqual([i["pointer"] for i in issues], [
            "/subtitle",
            "/grammar/0/examples/0/translation",
            "/grammar/0/examples/1/translation",
        ])
        self.assertNotIn("PRIVATE_", json.dumps(issues))
        self.assertNotIn("SECRET", json.dumps(issues))
        self.assertFalse(any("/options/" in issue["pointer"] for issue in issues))

    def test_synthetic_seven_track_queue_redacts_answers_and_content(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tracks = ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")
            for track in tracks:
                path = root / "app/static/course_v3_data" / track
                path.mkdir(parents=True)
                (path / "lesson_01.json").write_text(
                    json.dumps({
                        "schema_version": 2, "level": track,
                        "lesson_id": 1, "part_no": 1,
                        "grammar": [{"examples": [{
                            "zh": "SECRET_HANZI",
                            "translation": {"uz": "", "ru": "", "tj": ""}
                        }]}],
                        "sections": [{"cards": [{
                            "type": "reverse_builder",
                            "answer_tokens": ["SECRET_ANSWER"],
                            "correct_index": 1,
                            "options": ["SECRET_OPTION"],
                        }]}],
                    }, ensure_ascii=False),
                    encoding="utf-8",
                )
            result = create_review_queue(root)
            self.assertEqual(result["source_lessons_scanned"], 7)
            self.assertEqual(result["affected_lessons"], 7)
            self.assertEqual(result["affected_display_maps"], 7)
            self.assertEqual(result["locale_values_to_author"], 21)
            serialized = json.dumps(result)
            for secret in ("SECRET", '"correct_index"', '"answer_tokens"',
                           '"options"', "SECRET_HANZI"):
                self.assertNotIn(secret, serialized)

    def test_source_revision_update_changes_digest_and_no_source_writes(self):
        source = ROOT / "app/static/course_v3_data/nhsk2/lesson_16.json"
        old = source.read_bytes()
        self.assertEqual(self.review["lessons"][0]["source_git_blob_sha1"],
                         _git_blob_sha1(old))
        self.assertNotEqual(_git_blob_sha1(old), _git_blob_sha1(old + b" "))
        code = (ROOT / "scripts/i18n_lesson_locale_gap_review_queue.py").read_text(
            encoding="utf-8",
        )
        for forbidden in ("requests.", "httpx.", "FastAPI(", "APIRouter(",
                          "write_bytes(", "answer_tokens=", "pro_pack",
                          "correct_index=", "source.write_text("):
            self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()

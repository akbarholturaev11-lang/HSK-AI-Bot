"""Never serialize learner text or answer values in public lesson risk checks."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_legacy_lesson_content_risk_audit import (
    ROOT, TRACKS, _sensitive_field_counts, run_audit,
)


class LegacyLessonContentRiskTests(unittest.TestCase):
    def test_nested_grading_key_counts_have_no_values(self):
        data = {"sections": [{"cards": [
            {"correctIndex": 0, "answer_tokens": ["SECRET_HANZI"]},
            {"correct_index": 1, "answerTokens": ["SECRET_ORDER"],
             "explanation": "SECRET_EXPLANATION"},
        ]}]}
        counts = _sensitive_field_counts(data)
        self.assertEqual(counts["correct_index"], 2)
        self.assertEqual(counts["answer_tokens"], 2)
        self.assertNotIn("SECRET", json.dumps(counts))

    def test_seven_track_fixture_only_prints_field_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for track in TRACKS:
                d = root / "app/static/course_v3_data" / track
                d.mkdir(parents=True)
                for n in (1, 2):
                    (d / f"lesson_{n:02}.json").write_text(json.dumps({
                        "title": "HIDDEN_LESSON_TEXT",
                        "sections": [{"cards": [
                            {"answer_tokens": ["HIDDEN_ANSWER"]},
                            {"correct_index": 1},
                        ]}],
                    }), encoding="utf-8")
            report = run_audit(root)
            self.assertEqual(report["scanned_source_lesson_files"], 14)
            self.assertEqual(report["source_files_with_assessment_fields"], 14)
            self.assertEqual(len(report["first_last_samples"]), 14)
            self.assertEqual(report["sensitive_field_totals"]["answer_tokens"], 14)
            self.assertNotIn("HIDDEN_", json.dumps(report))

    def test_missing_or_nonconsecutive_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "app/static/course_v3_data" / TRACKS[0]
            folder.mkdir(parents=True)
            (folder / "lesson_01.json").write_text("{}", encoding="utf-8")
            (folder / "lesson_03.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "numbering_changed"):
                run_audit(root)

    def test_actual_746_source_lessons_and_first_last_samples(self):
        report = run_audit(ROOT)
        self.assertEqual(report["scanned_source_lesson_files"], 746)
        self.assertEqual(len(report["first_last_samples"]), 14)
        self.assertEqual(report["lesson_counts"],
                         dict(zip(TRACKS, [63, 72, 109, 181, 103, 73, 145])))
        self.assertGreater(report["sensitive_field_totals"]["correct_index"], 0)
        self.assertGreater(report["sensitive_field_totals"]["answer_tokens"], 0)
        self.assertNotIn('"options":', json.dumps(report))
        self.assertNotIn('"correct_answer":', json.dumps(report))


if __name__ == "__main__":
    unittest.main()

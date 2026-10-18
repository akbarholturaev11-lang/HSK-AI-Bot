"""All-746 P3 audit: structural review and safe reporting, no locale pack."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_lesson_overlay_full_audit import audit_all_lessons, _evaluate
from scripts.i18n_legacy_lesson_content_risk_audit import TRACKS

ROOT = Path(__file__).resolve().parents[1]
TRACK_COUNTS = (63, 72, 109, 181, 103, 73, 145)


class LessonOverlayFullAuditTests(unittest.TestCase):
    def test_all_746_real_lessons_in_all_seven_tracks(self):
        report = audit_all_lessons(ROOT)
        self.assertEqual(
            report["lesson_source_counts"], dict(zip(TRACKS, TRACK_COUNTS))
        )
        self.assertEqual(report["totals"]["source_lessons"], 746)
        self.assertEqual(sum(
            d["source_lessons"] for d in report["per_track"].values()
        ), 746)
        self.assertEqual(
            report["totals"]["ready_lessons"] + report["totals"]["blocked_lessons"], 746
        )
        self.assertEqual(
            report["totals"]["validated_locale_overlays"],
            report["totals"]["ready_lessons"] * 3
        )
        self.assertEqual(len(report["blocked_sources"]),
                         report["totals"]["blocked_lessons"])
        self.assertEqual(report["status"], "P3_FULL_SOURCE_GAPS_REQUIRE_REVIEW")
        self.assertGreater(report["totals"]["assessment_key_occurrences"], 0)
        self.assertGreater(report["totals"]["reverse_builder_cards_excluded"], 0)
        self.assertTrue(any(
            row["track"] == "nhsk2" and row["lesson_number"] == 73
            and row["all_empty_locale_maps"] == 9
            for row in report["blocked_sources"]
        ))

    def test_hard_fail_on_identity_and_partial_locale(self):
        valid = {
            "schema_version": 2, "level": "hsk1",
            "lesson_id": 1, "part_no": 1,
            "subtitle": {"uz": "Hello", "ru": "Привет", "tj": "Салом"},
            "sections": [{"cards": [{"type": "reverse_builder",
                "answer_tokens": ["SECRET_ANSWER"]}]}],
        }
        counts, issues = _evaluate(valid, "hsk1", 1)
        self.assertEqual(issues, [])
        self.assertEqual(counts["validated_locale_overlays"], 3)
        valid["lesson_id"] = 2
        self.assertIn("invalid_source_identity", _evaluate(valid, "hsk1", 1)[1])
        valid["lesson_id"] = 1
        valid["subtitle"]["tj"] = ""
        counts, issues = _evaluate(valid, "hsk1", 1)
        self.assertIn("incomplete_source_locales", issues)
        self.assertEqual(counts["validated_locale_overlays"], 0)

    def test_synthetic_sources_do_not_leak_content_or_answers(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for track in TRACKS:
                path = root / "app/static/course_v3_data" / track
                path.mkdir(parents=True)
                for number in (1, 2):
                    translations = {
                        "uz": "SECRET_UZ", "ru": "SECRET_RU", "tj": "SECRET_TJ",
                    }
                    if track == "nhsk2" and number == 2:
                        translations = dict.fromkeys(translations, "")
                    data = {
                        "schema_version": 2,
                        "level": track, "lesson_id": number, "part_no": 1,
                        "subtitle": translations,
                        "sections": [{"cards": [
                            {"type": "reverse_builder",
                             "answer_tokens": ["SECRET_ANSWER"]},
                            {"type": "meaning_guess",
                             "options": ["SECRET_OPTION"],
                             "correct_index": 0},
                        ]}],
                    }
                    (path / f"lesson_{number:02d}.json").write_text(
                        json.dumps(data, ensure_ascii=False), encoding="utf-8"
                    )
            result = audit_all_lessons(root)
            self.assertEqual(result["totals"]["source_lessons"], 14)
            self.assertEqual(result["totals"]["blocked_lessons"], 1)
            self.assertEqual(result["totals"]["ready_lessons"], 13)
            self.assertEqual(result["totals"]["validated_locale_overlays"], 39)
            self.assertEqual(len(result["blocked_sources"]), 1)
            encoded = json.dumps(result, ensure_ascii=False)
            for secret in ("SECRET_", "correct_index", "answer_tokens",
                           '"options":', '"subtitle":', "Привет", "Салом"):
                self.assertNotIn(secret, encoded)

    def test_invalid_json_counted_without_emitting_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for track in TRACKS:
                folder_path = root / "app/static/course_v3_data" / track
                folder_path.mkdir(parents=True)
                (folder_path / "lesson_01.json").write_text(
                    "PRIVATE_HANZI{INVALID", encoding="utf-8"
                )
            result = audit_all_lessons(root)
            self.assertEqual(result["totals"]["blocked_lessons"], 7)
            self.assertEqual(result["issue_counts"]["invalid_json_or_root"], 7)
            self.assertNotIn("PRIVATE_HANZI", json.dumps(result))

    def test_read_only_and_no_public_runtime_hook(self):
        source = (ROOT / "scripts/i18n_lesson_overlay_full_audit.py").read_text(
            encoding="utf-8"
        )
        for forbidden in ("httpx.", "requests.", "FastAPI(", "APIRouter(",
                          "send_file(", "write_bytes(", "public_pack",
                          "answers.json"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

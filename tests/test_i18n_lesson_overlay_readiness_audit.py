"""P3 source-only, fail-closed 7-track overlay review (not an entitlement test)."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_lesson_overlay_readiness_audit import (
    audit_sampled_lessons, _display_field_counts,
)
from scripts.i18n_legacy_lesson_content_risk_audit import TRACKS

ROOT = Path(__file__).resolve().parents[1]
COUNTS = (63, 72, 109, 181, 103, 73, 145)


class LessonOverlayReadinessAuditTests(unittest.TestCase):
    def test_all_seven_tracks_first_and_last_source_lessons(self):
        report = audit_sampled_lessons(ROOT)
        self.assertEqual(report["tracks"], list(TRACKS))
        self.assertEqual(report["lesson_source_counts"], dict(zip(TRACKS, COUNTS)))
        self.assertEqual(report["totals"]["sampled_source_lessons"], 14)
        self.assertEqual(len(report["samples"]), 14)
        self.assertEqual(report["reviewed_display_path_templates"], 13)
        self.assertEqual(report["totals"]["validated_locale_overlays"], 39)
        self.assertEqual(report["totals"]["blocked_samples"], 1)
        self.assertEqual(report["totals"]["all_empty_locale_maps"], 9)
        self.assertEqual(report["totals"]["partially_empty_locale_maps"], 0)
        self.assertEqual(report["totals"]["invalid_locale_maps"], 0)
        self.assertEqual(report["status"], "P3_SAMPLE_LOCALE_GAPS_REQUIRE_REVIEW")
        self.assertGreater(report["totals"]["reverse_builder_cards_excluded"], 0)
        self.assertGreater(report["totals"]["assessment_key_occurrences"], 0)
        for row in report["samples"]:
            self.assertEqual(
                row["validated_locale_overlays"],
                0 if row["status"].startswith("BLOCKED") else 3,
            )

    def test_known_nhsk2_final_lesson_empty_grammar_locales_are_blocked(self):
        report = audit_sampled_lessons(ROOT)
        blocked = [row for row in report["samples"]
                   if row["status"] == "BLOCKED_INCOMPLETE_SOURCE_LOCALES"]
        self.assertEqual(len(blocked), 1)
        self.assertEqual((blocked[0]["track"], blocked[0]["lesson_number"]),
                         ("nhsk2", 73))
        self.assertEqual(blocked[0]["all_empty_locale_maps"], 9)
        self.assertEqual(blocked[0]["validated_locale_overlays"], 0)

    def test_empty_text_distinguished_from_missing_or_partial_locale(self):
        self.assertEqual(_display_field_counts({
            "subtitle": {"uz": "", "ru": "", "tj": ""},
        })["all_empty_locale_maps"], 1)
        self.assertEqual(_display_field_counts({
            "subtitle": {"uz": "u", "ru": "r"},
        })["invalid_locale_maps"], 1)
        self.assertEqual(_display_field_counts({
            "subtitle": {"uz": "u", "ru": "", "tj": "t"},
        })["partially_empty_locale_maps"], 1)

    def test_safe_synthetic_source_never_leaks_translations_or_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for track in TRACKS:
                target = root / "app/static/course_v3_data" / track
                target.mkdir(parents=True)
                (target / "lesson_01.json").write_text(json.dumps({
                    "schema_version": 2, "level": track,
                    "lesson_id": 1, "part_no": 1,
                    "subtitle": {"uz": "PRIVATE_UZ_TEXT",
                                 "ru": "PRIVATE_RU_TEXT",
                                 "tj": "PRIVATE_TJ_TEXT"},
                    "sections": [{"cards": [
                        {"type": "reverse_builder",
                         "answer_tokens": ["PRIVATE_GRADE_SECRET"]},
                        {"type": "meaning_guess", "correct_index": 1,
                         "options": ["PRIVATE_OPTION_SECRET"]},
                    ]}],
                }), encoding="utf-8")
            report = audit_sampled_lessons(root)
            encoded = json.dumps(report)
            for secret in ("PRIVATE_", "correct_index", "answer_tokens",
                           '"options":', '"subtitle":'):
                self.assertNotIn(secret, encoded)
            self.assertEqual(report["totals"]["sampled_source_lessons"], 7)
            self.assertEqual(report["totals"]["validated_locale_overlays"], 21)
            self.assertEqual(report["totals"]["reverse_builder_cards_excluded"], 7)

    def test_source_input_unchanged_and_no_runtime_public_pack_writer(self):
        file = ROOT / "scripts/i18n_lesson_overlay_readiness_audit.py"
        source = file.read_text(encoding="utf-8")
        for forbidden in ("httpx.", "requests.", "fetch(", "app.mount(",
                          "FastAPI(", "APIRouter(", "write_bytes(",
                          "send_file(", "course_v3_data/hsk1/lesson_01.json"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

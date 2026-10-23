"""Seven-track grammar source/card mirror audit, no graded content exposure."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_grammar_mirror_source_audit import (
    audit_lesson_mirrors, audit_all_mirrors,
)

ROOT = Path(__file__).resolve().parents[1]
TRACKS = ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")


def fixture(mirror=True):
    group = {
        "no": 1,
        "title": {"uz": "Title", "ru": "Заглавие", "tj": "Сарлавҳа"},
        "rule": {"uz": "Rule", "ru": "Правило", "tj": "Қоида"},
        "examples": [{
            "zh": "SECRET_CHINESE",
            "pinyin": "SECRET_PINYIN",
            "translation": {"uz": "", "ru": "", "tj": ""},
        }],
    }
    return {
        "schema_version": 2, "level": "nhsk2",
        "lesson_id": 1, "part_no": 1,
        "grammar": [deepcopy(group)],
        "sections": [
            {"cards": [{
                "type": "_grammar", "g": deepcopy(group),
            }] if mirror else []},
            {"cards": [{
                "type": "reverse_builder",
                "correct_index": 0, "options": ["SECRET_ANSWER"],
                "answer_tokens": ["SECRET_TOKEN"],
                "access": {"requires_pro": True},
            }]},
        ],
    }


class GrammarMirrorSourceAuditTests(unittest.TestCase):
    def test_complete_matching_mirror_never_counts_two_distinct_translations(self):
        report = audit_lesson_mirrors(fixture(), "nhsk2", 1)
        self.assertEqual(report["issues"], {})
        self.assertEqual(report["counts"]["original_all_empty_display_maps"], 1)
        self.assertEqual(report["counts"]["matched_all_empty_mirror_maps"], 1)
        self.assertEqual(report["counts"]["matched_mirror_groups"], 1)
        self.assertNotIn("answer_tokens", json.dumps(report))
        self.assertNotIn("SECRET_", json.dumps(report))

    def test_mirrorless_source_is_not_automatically_invalid(self):
        report = audit_lesson_mirrors(fixture(mirror=False), "nhsk2", 1)
        self.assertEqual(report["issues"], {})
        self.assertEqual(report["counts"]["source_groups_without_mirror_card"], 1)

    def test_mismatched_text_and_translations_report_issue_codes_only(self):
        mutated = fixture()
        a = mutated["sections"][0]["cards"][0]["g"]["examples"][0]
        a["zh"] = "DIFFERENT_SECRET_HANZI"
        a["pinyin"] = "DIFFERENT_SECRET_PINYIN"
        a["translation"]["ru"] = "SECRET_RU"
        result = audit_lesson_mirrors(mutated, "nhsk2", 1)
        self.assertEqual(result["issues"]["mirror_chinese_mismatch"], 1)
        self.assertEqual(result["issues"]["mirror_pinyin_mismatch"], 1)
        self.assertEqual(result["issues"]["mirror_locale_map_mismatch"], 1)
        self.assertNotIn("DIFFERENT_", json.dumps(result))
        self.assertNotIn("SECRET_", json.dumps(result))

    def test_orphan_multiple_and_missing_examples_are_reported(self):
        original = fixture()
        copy = original["sections"][0]["cards"][0]
        copy["g"]["no"] = 999
        self.assertEqual(
            audit_lesson_mirrors(original, "nhsk2", 1)["issues"]["orphaned_mirror_group"],
            1,
        )
        original = fixture()
        copy = original["sections"][0]["cards"][0]
        original["sections"][0]["cards"].append(deepcopy(copy))
        self.assertEqual(
            audit_lesson_mirrors(original, "nhsk2", 1)["issues"]["multiple_mirrors_need_review"],
            1,
        )
        original = fixture()
        original["sections"][0]["cards"][0]["g"]["examples"] = []
        self.assertEqual(
            audit_lesson_mirrors(original, "nhsk2", 1)["issues"]["mirror_example_count_drift"],
            1,
        )

    def test_seven_real_tracks_are_scanned_and_grades_not_returned(self):
        result = audit_all_mirrors(ROOT)
        self.assertEqual(result["source_lesson_counts"], dict(zip(
            TRACKS, (63, 72, 109, 181, 103, 73, 145),
        )))
        self.assertEqual(result["totals"]["scanned_source_lessons"], 746)
        self.assertGreaterEqual(result["totals"]["matched_all_empty_mirror_maps"], 12)
        self.assertGreaterEqual(result["totals"]["matched_mirror_groups"], 3)
        self.assertFalse(result["ready_to_ship"])
        text = json.dumps(result, ensure_ascii=False)
        for forbidden in ("SECRET_CHINESE", "SECRET_TOKEN",
                          '"correct_index"', '"answer_tokens"', '"options":'):
            self.assertNotIn(forbidden, text)

    def test_synthetic_all_seven_tracks_are_safe_with_injected_quiz_answers(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for track in TRACKS:
                data = fixture()
                data["level"] = track
                dest = root / "app/static/course_v3_data" / track
                dest.mkdir(parents=True)
                (dest / "lesson_01.json").write_text(
                    json.dumps(data, ensure_ascii=False), encoding="utf-8"
                )
            report = audit_all_mirrors(root)
            self.assertEqual(report["totals"]["scanned_source_lessons"], 7)
            self.assertEqual(report["totals"]["matched_all_empty_mirror_maps"], 7)
            self.assertNotIn("SECRET_", json.dumps(report))
            self.assertEqual(report["review_locations"], [])

    def test_source_auditor_does_not_publish_or_modify_course(self):
        source = (ROOT / "scripts/i18n_grammar_mirror_source_audit.py").read_text(
            encoding="utf-8"
        )
        for forbidden in ("httpx.", "requests.", "FastAPI(", "APIRouter(",
                          "send_file(", "write_bytes(", "course_json.write_text("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

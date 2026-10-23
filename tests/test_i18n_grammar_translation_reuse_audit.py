"""P3 safe grammar translation reuse inventory; never output lesson contents."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_grammar_translation_reuse_audit import (
    _blank_original_grammar_maps, audit_repeated_grammar_translations,
)

ROOT = Path(__file__).resolve().parents[1]
TRACKS = ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")


def fake(number=1, track="nhsk2", *, context="STANDARD", chinese="秘密中文"):
    return {
        "schema_version": 2, "level": track, "lesson_id": number,
        "part_no": 1,
        "grammar": [{
            "no": 1,
            "title": {"uz": "TOPIC", "ru": "TOPIC", "tj": "TOPIC"},
            "title_zh": context,
            "rule": {"uz": "RULE", "ru": "RULE", "tj": "RULE"},
            "examples": [{
                "zh": chinese,
                "pinyin": "pīnyīn",
                "translation": {"uz": "", "ru": "", "tj": ""},
            }],
        }],
    }


class GrammarTranslationReuseTests(unittest.TestCase):
    def test_real_746_sources_and_lesson20_exact_repeated_examples(self):
        data = audit_repeated_grammar_translations(ROOT)
        self.assertEqual(data["total_scanned_lessons"], 746)
        self.assertEqual(data["source_lesson_counts"], dict(zip(
            TRACKS, (63, 72, 109, 181, 103, 73, 145),
        )))
        self.assertEqual(data["blank_source_grammar_maps"], 272)
        self.assertEqual(data["locale_values_before_reuse"], 816)
        self.assertLess(data["distinct_exact_grammar_contexts"], 272)
        self.assertFalse(data["ready_to_ship"])
        target_lesson20 = [
            (i, location)
            for i, group in enumerate(data["repeated_source_locations"])
            for location in group["locations"]
            if location["track"] == "nhsk2" and location["lesson_number"] == 20
        ]
        self.assertEqual(len(target_lesson20), 12)
        for i, location in target_lesson20:
            matched = data["repeated_source_locations"][i]["locations"]
            self.assertTrue(any(
                other["track"] == "nhsk2" and other["lesson_number"] in (16, 17, 18)
                for other in matched
            ))
        safe = json.dumps(data, ensure_ascii=False)
        for blocked in ('"zh":', '"pinyin":', '"correct_index":',
                        '"answer_tokens":', '"options":'):
            self.assertNotIn(blocked, safe)

    def test_identical_sources_deduplicate_across_seven_tracks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for track in TRACKS:
                p = root / "app/static/course_v3_data" / track
                p.mkdir(parents=True)
                (p / "lesson_01.json").write_text(
                    json.dumps(fake(track=track), ensure_ascii=False),
                    encoding="utf-8",
                )
            result = audit_repeated_grammar_translations(root)
            self.assertEqual(result["blank_source_grammar_maps"], 7)
            self.assertEqual(result["distinct_exact_grammar_contexts"], 1)
            self.assertEqual(result["duplicate_occurrences_after_first"], 6)
            self.assertEqual(len(result["repeated_source_locations"]), 1)
            self.assertEqual(len(result["repeated_source_locations"][0]["locations"]), 7)
            self.assertNotIn("秘密中文", json.dumps(result, ensure_ascii=False))

    def test_different_chinese_or_grammar_context_cannot_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for n, context, chinese in ((1, "GRAMMAR_A", "中文字"),
                                        (2, "GRAMMAR_B", "中文字"),
                                        (3, "GRAMMAR_A", "不同句")):
                p = root / "app/static/course_v3_data" / "nhsk2"
                p.mkdir(parents=True, exist_ok=True)
                (p / f"lesson_{n:02d}.json").write_text(
                    json.dumps(fake(n, context=context, chinese=chinese),
                               ensure_ascii=False), encoding="utf-8",
                )
            for track in TRACKS:
                if track == "nhsk2":
                    continue
                p = root / "app/static/course_v3_data" / track
                p.mkdir(parents=True)
                (p / "lesson_01.json").write_text(
                    json.dumps({
                        "schema_version": 2, "level": track,
                        "lesson_id": 1, "part_no": 1, "grammar": [],
                    }), encoding="utf-8",
                )
            result = audit_repeated_grammar_translations(root)
            self.assertEqual(result["distinct_exact_grammar_contexts"], 3)
            self.assertEqual(result["duplicate_occurrences_after_first"], 0)

    def test_incomplete_source_or_forged_lesson_id_fails_closed(self):
        data = fake()
        data["grammar"][0]["examples"][0]["translation"]["tj"] = "already present"
        with self.assertRaisesRegex(ValueError, "partial"):
            _blank_original_grammar_maps(data, "nhsk2", 1)
        data = fake()
        with self.assertRaisesRegex(ValueError, "identity"):
            _blank_original_grammar_maps(data, "nhsk2", 2)
        data = fake()
        data["grammar"][0]["examples"][0]["zh"] = ""
        with self.assertRaisesRegex(ValueError, "invalid original"):
            _blank_original_grammar_maps(data, "nhsk2", 1)

    def test_no_public_pack_answers_or_source_writes(self):
        s = (ROOT / "scripts/i18n_grammar_translation_reuse_audit.py").read_text(
            encoding="utf-8",
        )
        for forbidden in ("write_bytes(", "httpx.", "requests.", "FastAPI(",
                          "APIRouter(", "send_file(", "answer_tokens="):
            self.assertNotIn(forbidden, s)


if __name__ == "__main__":
    unittest.main()

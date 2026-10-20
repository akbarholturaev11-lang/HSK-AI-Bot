"""Fail-closed proof for private lesson display overlays, without runtime changes."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.i18n_lesson_display_overlay_contract import (
    DISPLAY_PATHS, LOCALES, apply_display_overlay, build_display_overlay,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = (
    ROOT / "app/static/course_v3_data/hsk1/lesson_01.json",
    ROOT / "app/static/course_v3_data/nhsk1/lesson_01.json",
)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class LessonDisplayOverlayContractTests(unittest.TestCase):
    def test_real_hsk20_and_hsk30_sources_preserve_answers_and_identity(self):
        for sample in SAMPLES:
            original = read(sample)
            for locale in LOCALES:
                with self.subTest(sample=sample.name, track=original["level"], locale=locale):
                    overlay = build_display_overlay(original, locale)
                    self.assertEqual(overlay["source"]["level"], original["level"])
                    self.assertEqual(overlay["source"]["lesson_id"], original["lesson_id"])
                    self.assertEqual(overlay["source"]["part_no"], original["part_no"])
                    self.assertGreater(len(overlay["texts"]), 10)
                    self.assertFalse(any(
                        forbidden in path
                        for path in overlay["texts"]
                        for forbidden in ("/options/", "/answer_tokens", "/correct_index",
                                          "/tokens", "/correct_answer", "/distractors")
                    ))
                    self.assertEqual(apply_display_overlay(original, overlay), original)
                    self.assertEqual(len(overlay["source"]["sha256"]), 64)

    def test_revision_bound_to_source_and_grading(self):
        original = read(SAMPLES[0])
        overlay = build_display_overlay(original, "uz")
        changed = deepcopy(original)
        target = next(
            card for section in changed["sections"] for card in section["cards"]
            if "correct_index" in card
        )
        target["correct_index"] = int(target["correct_index"]) + 1
        with self.assertRaisesRegex(ValueError, "revision"):
            apply_display_overlay(changed, overlay)

        changed = deepcopy(original)
        changed["subtitle"]["ru"] += " altered"
        with self.assertRaisesRegex(ValueError, "revision"):
            apply_display_overlay(changed, overlay)

    def test_unreviewed_or_missing_paths_and_wrong_locale_are_rejected(self):
        original = read(SAMPLES[0])
        good = build_display_overlay(original, "tj")
        for path in ("/sections/0/cards/0/correct_index",
                     "/sections/0/cards/2/options/0"):
            bad = deepcopy(good)
            bad["texts"][path] = "injected answer"
            with self.assertRaisesRegex(ValueError, "unreviewed"):
                apply_display_overlay(original, bad)
        bad = deepcopy(good)
        del bad["texts"][next(iter(bad["texts"]))]
        with self.assertRaisesRegex(ValueError, "missing"):
            apply_display_overlay(original, bad)
        with self.assertRaisesRegex(ValueError, "unsupported locale"):
            build_display_overlay(original, "en")

    def test_locale_completeness_and_identity_are_fail_closed(self):
        source = read(SAMPLES[0])
        del source["subtitle"]["tj"]
        with self.assertRaisesRegex(ValueError, "locale parity"):
            build_display_overlay(source, "uz")
        source = read(SAMPLES[0])
        source["part_no"] = None
        with self.assertRaisesRegex(ValueError, "part_no"):
            build_display_overlay(source, "ru")
        source = read(SAMPLES[0])
        source["schema_version"] = 3
        with self.assertRaisesRegex(ValueError, "schema"):
            build_display_overlay(source, "uz")

    def test_only_explicit_display_paths_and_no_public_emitter(self):
        self.assertGreaterEqual(len(DISPLAY_PATHS), 10)
        module = (ROOT / "scripts/i18n_lesson_display_overlay_contract.py").read_text(
            encoding="utf-8")
        for absent in ("write_text(", "open(", "requests.", "httpx.", "FastAPI",
                       "correct_index=", "api_router", "print("):
            self.assertNotIn(absent, module)


if __name__ == "__main__":
    unittest.main()

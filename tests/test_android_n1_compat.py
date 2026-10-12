"""Old Android APK compatibility for N1's conditional transfer bank."""

import json
import unittest
from pathlib import Path

from app.api.android_course import _legacy_n1_lesson_payload

COURSE = Path("app/static/course_v3_data/nhsk1")


class LegacyN1ProjectionTests(unittest.TestCase):
    def payload(self, lesson_order):
        data = json.loads((COURSE / f"lesson_{lesson_order:02d}.json").read_text(encoding="utf-8"))
        total = sum(len(s["cards"]) for s in data["sections"])
        return {"ok": True, "level": "nhsk1", "lesson_order": lesson_order,
                "lesson": data, "total_cards": total, "preview_half": False,
                "preview_card_limit": total, "completion_allowed": True}

    def test_old_apks_get_exit_but_not_conditional_retry(self):
        for order, total in [(4, 18), (9, 17), (15, 17), (103, 17)]:
            with self.subTest(lesson=order):
                original = self.payload(order)
                out = _legacy_n1_lesson_payload(original, supports_transfer=False)
                self.assertEqual(original["total_cards"], total)
                self.assertEqual(out["total_cards"], total - (3 if order == 4 else 2))
                self.assertEqual(out["preview_card_limit"], out["total_cards"])
                self.assertEqual(
                    [s["section_purpose"] for s in out["lesson"]["sections"]][-1],
                    "learning_exit_check",
                )
                self.assertEqual(original["lesson"]["sections"][-1]["section_purpose"], "learning_repair_bank")
                # No position/identity drift for either client.
                self.assertEqual(out["lesson"]["sections"][:2], original["lesson"]["sections"][:2])

    def test_updated_apk_receives_entire_bank(self):
        original = self.payload(9)
        actual = _legacy_n1_lesson_payload(original, supports_transfer=True)
        self.assertIs(actual, original)
        self.assertEqual(actual["total_cards"], 17)

    def test_other_tracks_unmodified(self):
        original = self.payload(9)
        original["level"] = "hsk1"
        self.assertIs(_legacy_n1_lesson_payload(original, supports_transfer=False), original)

    def test_preview_envelope_is_recalculated_not_bypassed(self):
        original = self.payload(4)
        original["preview_half"] = True
        original["completion_allowed"] = False
        original["preview_card_limit"] = 9
        out = _legacy_n1_lesson_payload(original, supports_transfer=False)
        self.assertEqual(out["total_cards"], 15)
        self.assertEqual(out["preview_card_limit"], 7)
        self.assertFalse(out["completion_allowed"])


if __name__ == "__main__":
    unittest.main()

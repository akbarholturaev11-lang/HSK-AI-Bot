import json
import unittest
from pathlib import Path


BASE = Path("app/static/course_v3_data")
LEVELS = ("hsk1", "hsk2", "hsk3", "hsk4")


def lesson_number(path: Path) -> int:
    return int(path.stem.rsplit("_", 1)[-1])


class CourseRetentionReviewTests(unittest.TestCase):
    def test_every_regular_part_ends_with_previous_and_current_word_review(self):
        known_words: set[str] = set()
        regular_parts = 0

        for level in LEVELS:
            paths = sorted((BASE / level).glob("lesson_*.json"), key=lesson_number)
            for path in paths:
                data = json.loads(path.read_text(encoding="utf-8"))
                where = f"{level}/{path.name}"
                sections = data.get("sections", [])
                self.assertTrue(sections, where)

                if data.get("checkpoint"):
                    self.assertNotEqual(
                        sections[-1].get("section_purpose"),
                        "retention_review",
                        where,
                    )
                    continue

                regular_parts += 1
                cards = [card for section in sections for card in section.get("cards", [])]
                self.assertLessEqual(len(cards), 18, where)

                current_words = {
                    word.get("zh")
                    for word in data.get("active_words", [])
                    if word.get("zh")
                }
                review = sections[-1]
                self.assertEqual(review.get("section_purpose"), "retention_review", where)
                self.assertEqual(len(review.get("cards", [])), 2, where)

                origins = [card.get("review_origin") for card in review["cards"]]
                expected = ["previous", "current"] if known_words else ["current", "current"]
                self.assertEqual(origins, expected, where)

                for card in review["cards"]:
                    self.assertTrue(card.get("review_mix"), where)
                    word = card.get("review_word") or {}
                    self.assertTrue(word.get("zh"), where)
                    self.assertTrue(word.get("pinyin"), where)
                    for lang in ("uz", "ru", "tj"):
                        self.assertTrue((word.get("meaning") or {}).get(lang), f"{where}:{lang}")

                    if card["review_origin"] == "previous":
                        self.assertIn(word["zh"], known_words, where)
                    else:
                        self.assertIn(word["zh"], current_words, where)

                    options = card.get("options") or []
                    correct_index = card.get("correct_index")
                    self.assertTrue(options, where)
                    self.assertIsInstance(correct_index, int, where)
                    self.assertTrue(0 <= correct_index < len(options), where)

                known_words.update(current_words)

        self.assertEqual(regular_parts, 355)

    def test_review_ui_keeps_learning_context_and_analytics_markers(self):
        html = Path("app/static/course-v3.html").read_text(encoding="utf-8")

        self.assertIn("c.review_word||{}", html)
        self.assertIn("rw.pinyin", html)
        self.assertIn("rw.meaning", html)
        self.assertIn("review_mix:!!c.review_mix", html)
        self.assertIn("review_origin:c.review_origin||", html)
        self.assertIn("section_purpose:c._sPurpose||", html)


if __name__ == "__main__":
    unittest.main()

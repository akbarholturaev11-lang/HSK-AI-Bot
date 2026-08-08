"""Guards the lesson-card shapes the native clients parse.

The Android renderer hand-parses `app/static/course_v3_data/**/lesson_*.json`
because several fields reuse a name with a different shape depending on the
card type. That is fine as long as the shapes stay stable, so this test pins
them across all checked-in lessons.

If `scripts/gen_course_v3_from_seed.py` ever changes one of these shapes, this
test fails here rather than the Android client failing silently on a phone.
"""

import json
import unittest
from collections import Counter
from pathlib import Path


COURSE_DATA_ROOT = Path("app/static/course_v3_data")
LANGUAGES = {"uz", "ru", "tj"}

# Every card type the Android LessonParser knows about. A new type is not a
# failure by itself — unknown cards degrade to a visible "unsupported" state —
# but it must be a deliberate decision, so the list is pinned.
KNOWN_CARD_TYPES = {
    "_grammar",
    "active_word",
    "dialog_cloze",
    "gap_fill",
    "hanzi_choice",
    "listening_choice",
    "match_pairs",
    "meaning_guess",
    "pinyin_choice",
    "pronunciation",
    "quick_quiz",
    "reverse_builder",
    "sentence_builder",
    "translation_choice",
}

# Choice cards whose `options` are plain strings.
STRING_OPTION_TYPES = {
    "dialog_cloze",
    "gap_fill",
    "hanzi_choice",
    "listening_choice",
    "pinyin_choice",
    "quick_quiz",
    "translation_choice",
}

# The one choice card whose `options` are localized objects.
LOCALIZED_OPTION_TYPES = {"meaning_guess"}

CHOICE_TYPES = STRING_OPTION_TYPES | LOCALIZED_OPTION_TYPES


def _lesson_files() -> list[Path]:
    return sorted(COURSE_DATA_ROOT.glob("hsk*/lesson_*.json"))


def _is_localized(value) -> bool:
    return isinstance(value, dict) and LANGUAGES.issubset(value.keys())


class CourseCardContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = _lesson_files()
        if not cls.files:
            raise unittest.SkipTest("Course v3 lesson data is not checked out")
        cls.lessons = [(p, json.loads(p.read_text(encoding="utf-8"))) for p in cls.files]

    def test_all_425_mini_lessons_are_present(self):
        self.assertEqual(425, len(self.files))

    def test_sections_expose_section_no_and_purpose_but_no_type(self):
        for path, data in self.lessons:
            for section in data.get("sections") or []:
                with self.subTest(path=path.name):
                    self.assertIn("section_no", section)
                    self.assertIsInstance(section["section_no"], int)
                    self.assertIn("section_purpose", section)
                    self.assertIsInstance(section.get("cards"), list)
                    # The renderer keys off section_purpose; a `type` field
                    # appearing here would mean the schema changed.
                    self.assertNotIn("type", section)

    def test_card_types_are_the_known_set(self):
        seen = Counter()
        for _path, data in self.lessons:
            for section in data.get("sections") or []:
                for card in section.get("cards") or []:
                    seen[card.get("type")] += 1
        self.assertEqual(KNOWN_CARD_TYPES, set(seen))

    def test_choice_cards_have_a_valid_answer_index(self):
        for path, data in self.lessons:
            for section in data.get("sections") or []:
                for position, card in enumerate(section.get("cards") or [], 1):
                    card_type = card.get("type")
                    if card_type not in CHOICE_TYPES:
                        continue
                    with self.subTest(path=path.name, card=position):
                        options = card.get("options")
                        self.assertIsInstance(options, list)
                        self.assertGreaterEqual(len(options), 2)
                        index = card.get("correct_index")
                        self.assertIsInstance(index, int)
                        self.assertTrue(0 <= index < len(options))
                        self.assertTrue(_is_localized(card.get("explanation")))

    def test_option_shape_is_stable_per_card_type(self):
        for path, data in self.lessons:
            for section in data.get("sections") or []:
                for card in section.get("cards") or []:
                    card_type = card.get("type")
                    if card_type not in CHOICE_TYPES:
                        continue
                    with self.subTest(path=path.name, type=card_type):
                        for option in card["options"]:
                            if card_type in LOCALIZED_OPTION_TYPES:
                                self.assertTrue(_is_localized(option))
                            else:
                                self.assertIsInstance(option, str)

    def test_sentence_is_a_string_on_gap_fill_and_localized_on_builder(self):
        for path, data in self.lessons:
            for section in data.get("sections") or []:
                for card in section.get("cards") or []:
                    card_type = card.get("type")
                    if card_type == "gap_fill":
                        with self.subTest(path=path.name, type=card_type):
                            self.assertIsInstance(card.get("sentence"), str)
                    elif card_type == "sentence_builder":
                        with self.subTest(path=path.name, type=card_type):
                            self.assertTrue(_is_localized(card.get("sentence")))

    def test_token_shape_differs_between_the_two_builders(self):
        for path, data in self.lessons:
            for section in data.get("sections") or []:
                for card in section.get("cards") or []:
                    card_type = card.get("type")
                    if card_type == "sentence_builder":
                        with self.subTest(path=path.name, type=card_type):
                            for key in ("tokens", "answer_tokens"):
                                value = card.get(key)
                                self.assertIsInstance(value, list)
                                self.assertTrue(all(isinstance(t, str) for t in value))
                            self.assertTrue(
                                set(card["answer_tokens"]).issubset(set(card["tokens"]))
                            )
                    elif card_type == "reverse_builder":
                        with self.subTest(path=path.name, type=card_type):
                            for key in ("tokens", "answer_tokens"):
                                value = card.get(key)
                                self.assertIsInstance(value, dict)
                                self.assertTrue(LANGUAGES.issubset(value.keys()))
                                for language in LANGUAGES:
                                    self.assertTrue(
                                        all(
                                            isinstance(t, str)
                                            for t in value[language]
                                        )
                                    )

    def test_match_pairs_are_hanzi_plus_localized_meaning_tuples(self):
        for path, data in self.lessons:
            for section in data.get("sections") or []:
                for card in section.get("cards") or []:
                    if card.get("type") != "match_pairs":
                        continue
                    with self.subTest(path=path.name):
                        pairs = card.get("pairs")
                        self.assertIsInstance(pairs, list)
                        self.assertGreaterEqual(len(pairs), 2)
                        for pair in pairs:
                            self.assertIsInstance(pair, list)
                            self.assertEqual(2, len(pair))
                            self.assertIsInstance(pair[0], str)
                            self.assertTrue(_is_localized(pair[1]))

    def test_nested_objects_keep_their_fields(self):
        for path, data in self.lessons:
            for section in data.get("sections") or []:
                for card in section.get("cards") or []:
                    card_type = card.get("type")
                    if card_type == "active_word":
                        with self.subTest(path=path.name, type=card_type):
                            word = card.get("word")
                            self.assertIsInstance(word, dict)
                            for key in ("zh", "pinyin"):
                                self.assertIsInstance(word.get(key), str)
                            self.assertTrue(_is_localized(word.get("meaning")))
                    elif card_type == "_grammar":
                        with self.subTest(path=path.name, type=card_type):
                            grammar = card.get("g")
                            self.assertIsInstance(grammar, dict)
                            self.assertTrue(_is_localized(grammar.get("title")))
                            self.assertTrue(_is_localized(grammar.get("rule")))
                            for example in grammar.get("examples") or []:
                                self.assertIsInstance(example.get("zh"), str)
                                self.assertTrue(
                                    _is_localized(example.get("translation"))
                                )
                    elif card_type == "pronunciation":
                        with self.subTest(path=path.name, type=card_type):
                            self.assertIsInstance(card.get("phrase"), str)
                            self.assertIsInstance(card.get("pinyin"), str)
                            self.assertTrue(_is_localized(card.get("translation")))

    def test_dialog_cloze_marks_exactly_the_blank_lines(self):
        for path, data in self.lessons:
            for section in data.get("sections") or []:
                for card in section.get("cards") or []:
                    if card.get("type") != "dialog_cloze":
                        continue
                    with self.subTest(path=path.name):
                        lines = card.get("lines")
                        self.assertIsInstance(lines, list)
                        blanks = [line for line in lines if line.get("blank")]
                        self.assertEqual(1, len(blanks))
                        for line in lines:
                            self.assertIsInstance(line.get("speaker"), str)
                            self.assertIsInstance(line.get("zh"), str)

    def test_listening_cards_carry_audio_text(self):
        for path, data in self.lessons:
            for section in data.get("sections") or []:
                for card in section.get("cards") or []:
                    if card.get("type") != "listening_choice":
                        continue
                    with self.subTest(path=path.name):
                        self.assertIsInstance(card.get("audio_text"), str)
                        self.assertTrue(card["audio_text"].strip())

    def test_review_cards_declare_where_they_came_from(self):
        origins = set()
        for _path, data in self.lessons:
            for section in data.get("sections") or []:
                for card in section.get("cards") or []:
                    if card.get("review_mix"):
                        origins.add(card.get("review_origin"))
        # The end-of-lesson retention deck pairs one previous-part card with
        # one from the current part.
        self.assertTrue(origins)
        self.assertTrue(origins.issubset({"previous", "current"}))


if __name__ == "__main__":
    unittest.main()

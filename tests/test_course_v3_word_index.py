"""So'z indeksi: qaysi so'z qaysi qismda ochiladi.

Indeks ataylab `lesson_gate.js` dan quriladi — klient ham shuni ishlatadi.
Dars fayllaridagi `active_words` dan qurilsa hsk4 da 30 ta so'zda farq
chiqardi va server klient ochgan so'zni "hali yopiq" deb hisoblardi.
"""

import json
import re
import unittest
from pathlib import Path

from app.services.course_v3_parts import total_parts
from app.services.course_v3_word_index import (
    index_size,
    level_number,
    normalize_level,
    taught_words,
    word_position,
)
from app.services.course_v3_vocab import words_for_level


LEVELS = ("hsk1", "hsk2", "hsk3", "hsk4")


def client_dictionary() -> set[str]:
    """`hsk-words.js` dagi `WORDS` — klient nima ko'ra oladi."""
    source = Path("app/static/hsk-words.js").read_text(encoding="utf-8")
    match = re.search(r"const WORDS=(\[.*?\]);", source, re.S)
    return {item["h"] for item in json.loads(match.group(1))}


class IndexTests(unittest.TestCase):
    def test_index_matches_the_course_vocabulary(self):
        vocabulary = set()
        for level in LEVELS:
            vocabulary |= {word["zh"] for word in words_for_level(level)}
        self.assertEqual(index_size(), len(vocabulary))

    def test_every_indexed_word_exists_in_the_client_dictionary(self):
        # Server taklif qilgan so'zni klient chiza olishi shart.
        dictionary = client_dictionary()
        for level in LEVELS:
            for zh, _ in taught_words(level, 999):
                self.assertIn(zh, dictionary, zh)

    def test_proper_names_are_excluded(self):
        # 李月 / 王方 — dialog personajlari; "bu so'z nima degani?" ma'nosiz.
        for name in ("李月", "王方", "安娜"):
            self.assertIsNone(word_position(name), name)

    def test_a_known_word_reports_its_band_and_part(self):
        self.assertEqual(word_position("你"), (1, 1))

    def test_unknown_input_is_safe(self):
        for value in ("", "   ", "ZZZ", "🙂"):
            self.assertIsNone(word_position(value))


class LevelNormalisationTests(unittest.TestCase):
    def test_course_bands_map_the_same_way_as_the_rest_of_the_course(self):
        self.assertEqual(normalize_level("beginner"), "hsk1")
        self.assertEqual(normalize_level("az0"), "hsk1")
        self.assertEqual(normalize_level("hsk4a"), "hsk4")
        self.assertEqual(normalize_level("hsk4b"), "hsk4")
        self.assertEqual(normalize_level(None), "hsk1")
        self.assertEqual(normalize_level("nonsense"), "hsk1")

    def test_level_number_follows_the_band(self):
        self.assertEqual(level_number("hsk1"), 1)
        self.assertEqual(level_number("hsk4b"), 4)
        self.assertEqual(level_number("beginner"), 1)


class ColdStartTests(unittest.TestCase):
    def test_a_brand_new_learner_has_only_three_taught_words(self):
        # Bu o'lchangan haqiqat va butun kengaytirish qoidasining sababi.
        words = taught_words("hsk1", 1)
        self.assertEqual([zh for zh, _ in words], ["你", "好", "您"])

    def test_widening_fills_the_pool_for_a_beginner(self):
        self.assertEqual(len(taught_words("hsk1", 1, min_pool=10)), 10)
        self.assertEqual(len(taught_words("hsk1", 1, single_char=True, min_pool=8)), 8)

    def test_widening_never_runs_past_the_band(self):
        # Chegara bandning haqiqiy qism soni; klientdagi o'lik 40 emas.
        huge = taught_words("hsk1", 1, min_pool=10_000)
        every = taught_words("hsk1", total_parts("hsk1"))
        self.assertEqual(len(huge), len(every))

    def test_widening_is_not_applied_when_not_asked_for(self):
        self.assertEqual(len(taught_words("hsk1", 1, min_pool=0)), 3)


class ScopeTests(unittest.TestCase):
    def test_lower_bands_are_fully_unlocked(self):
        # hsk2 o'quvchisi 1-qismda ham butun hsk1 lug'atini ko'radi.
        hsk1_total = len(taught_words("hsk1", total_parts("hsk1")))
        hsk2_start = taught_words("hsk2", 1)
        self.assertGreaterEqual(len(hsk2_start), hsk1_total)

    def test_the_learner_never_sees_words_from_a_later_part(self):
        limit = 12
        for zh, part in taught_words("hsk1", limit):
            position = word_position(zh)
            if position[0] == 1:
                self.assertLessEqual(part, limit, zh)

    def test_single_char_filter_keeps_only_single_characters(self):
        for zh, _ in taught_words("hsk3", 999, single_char=True):
            self.assertEqual(len(zh), 1, zh)

    def test_the_gate_wins_over_the_lesson_files(self):
        # 流利 gate'da 92-qismda ochiladi; dars fayllarida 100-qismda.
        # Server gate'ni o'qishi shu bilan qotiriladi.
        self.assertEqual(word_position("流利"), (4, 92))
        self.assertIn("流利", {zh for zh, _ in taught_words("hsk4", 92)})


class OrderingTests(unittest.TestCase):
    def test_newest_taught_words_come_first(self):
        words = taught_words("hsk2", 30)
        own = [part for zh, part in words if word_position(zh)[0] == 2]
        self.assertEqual(own, sorted(own, reverse=True))

    def test_ordering_is_stable_across_calls(self):
        first = taught_words("hsk3", 40, min_pool=10)
        second = taught_words("hsk3", 40, min_pool=10)
        self.assertEqual(first, second)

    def test_same_part_words_are_ordered_deterministically(self):
        words = taught_words("hsk1", 10)
        grouped: dict[int, list[str]] = {}
        for zh, part in words:
            grouped.setdefault(part, []).append(zh)
        for part, items in grouped.items():
            self.assertEqual(items, sorted(items), part)


if __name__ == "__main__":
    unittest.main()

"""Xatolarim v3: savol yasovchi va universal tekshirgich.

Asosiy kafolat: lug'atdagi HAR so'z va gap havzasidagi HAR gap, har mashq
turi va har tilda yasalgan savol tekshirgichdan o'tadi, javobni ochib
qo'ymaydi va har nishon kamida 3 xil mashqqa ega.
"""

import json
import unittest
from collections import Counter

from app.services import mistake_drill_bank as bank
from app.services import mistake_drill_factory as drills
from app.services.mistake_target_resolver import _sentence_target, _word_target


def word(zh, category="word", target_id=1):
    target = _word_target(bank.lookup_word(zh))
    target.update(id=target_id, category=category)
    return target


def sentence(zh, category="grammar", target_id=1, **kwargs):
    target = _sentence_target(zh, level="hsk1", language="uz", **kwargs)
    target.update(id=target_id, category=category)
    return target


class LexiconWideTests(unittest.TestCase):
    """Lug'at bo'ylab xususiyat testi."""

    def test_every_word_has_three_valid_drills_in_every_category_and_language(self):
        weak = []
        for index, zh in enumerate(bank.lexicon()):
            for category in ("word", "character", "pronunciation"):
                target = word(zh, category, index + 1)
                for language in bank.LANGUAGES:
                    questions = drills.available_questions(
                        target, language=language, seed="lexicon", client_formats=drills.ALL_FORMATS
                    )
                    if len({question["format"] for question in questions}) < 3:
                        weak.append((zh, category, language))
                    for question in questions:
                        self.assertIsNone(drills.validate_question(question), (zh, question))
        self.assertEqual(weak, [])

    def test_word_drills_never_reveal_the_answer(self):
        for index, zh in enumerate(list(bank.lexicon())[:400]):
            target = word(zh, "word", index + 1)
            for question in drills.available_questions(
                target, language="uz", seed="leak", client_formats=drills.ALL_FORMATS
            ):
                correct = question["options"][question["answer_index"]]
                visible = question["prompt"] + question["sentence"] + question["pinyin"]
                if bank.has_cjk(correct):
                    self.assertNotIn(bank.normalize_zh(correct), bank.normalize_zh(visible), question)
                if question["format"] in drills.LISTEN_FORMATS:
                    self.assertEqual((question["sentence"], question["pinyin"]), ("", ""))
                    self.assertEqual(question["audio_text"], zh)
                if question["format"] in {"pinyin_choice", "listening_pinyin"}:
                    self.assertEqual(question["pinyin"], "")

    def test_listening_distractors_never_sound_like_the_answer(self):
        for index, zh in enumerate(bank.lexicon()):
            target = word(zh, "pronunciation", index + 1)
            question = drills.build_question(target, "listening_choice", language="ru", seed="homophone")
            if not question:
                continue
            plain = bank.pinyin_plain(target["payload"]["pinyin"])
            for option_index, option in enumerate(question["options"]):
                if option_index == question["answer_index"]:
                    continue
                other = bank.lookup_word(option)
                self.assertNotEqual(bank.pinyin_plain(other["pinyin"]), plain, (zh, option))

    def test_meaning_distractors_are_not_synonyms_of_the_answer(self):
        for index, zh in enumerate(list(bank.lexicon())[:500]):
            target = word(zh, "word", index + 1)
            question = drills.build_question(target, "meaning_choice", language="uz", seed="synonym")
            if not question:
                continue
            correct = question["options"][question["answer_index"]]
            for option in question["options"]:
                if option != correct:
                    self.assertFalse(drills._meaning_related(option, correct), (zh, option, correct))

    def test_every_pool_sentence_has_three_valid_drills(self):
        weak = []
        for level in bank.LEVELS:
            for index, entry in enumerate(bank.sentence_pool(level)):
                target = _sentence_target(entry["zh"], level=level, language="uz")
                if target["kind"] != "sentence":
                    continue
                target.update(id=index + 1, category="grammar")
                for language in bank.LANGUAGES:
                    questions = drills.available_questions(
                        target, language=language, seed="pool", client_formats=drills.ALL_FORMATS
                    )
                    if len(questions) < 3:
                        weak.append((level, entry["zh"], language))
                    for question in questions:
                        self.assertIsNone(drills.validate_question(question), question)
        self.assertEqual(weak, [])


class DrillFormatTests(unittest.TestCase):
    def test_each_word_session_uses_three_distinct_formats(self):
        questions, required = drills.plan_target(
            word("你"), language="uz", seed="s", client_formats=drills.ALL_FORMATS, passed=set()
        )
        self.assertEqual(required, 3)
        self.assertEqual(len({question["format"] for question in questions}), 3)

    def test_unpassed_formats_come_first(self):
        target = word("你")
        first, _ = drills.plan_target(
            target, language="uz", seed="s", client_formats=drills.ALL_FORMATS, passed=set()
        )
        passed = {first[0]["format"], first[1]["format"]}
        second, _ = drills.plan_target(
            target, language="uz", seed="s", client_formats=drills.ALL_FORMATS, passed=passed
        )
        self.assertNotIn(second[0]["format"], passed)

    def test_legacy_client_never_receives_builder(self):
        target = sentence("我是学生。", wrong="我是学生吗")
        questions = drills.available_questions(
            target, language="uz", seed="s", client_formats=drills.LEGACY_CLIENT_FORMATS
        )
        self.assertTrue(questions)
        for question in questions:
            self.assertNotIn(question["format"], drills.BUILDER_FORMATS)
            self.assertGreaterEqual(len(question["options"]), 2)

    def test_voice_sentence_offers_correct_choice_with_own_wrong_sentence(self):
        target = sentence("我是学生。", wrong="我是学生吗")
        question = drills.build_question(target, "correct_choice", language="uz", seed="s")
        self.assertEqual(sorted(question["options"]), sorted(["我是学生。", "我是学生吗"]))
        self.assertEqual(question["options"][question["answer_index"]], "我是学生。")
        self.assertEqual(question["prompt"], "Qaysi gap to'g'ri?")

    def test_builder_is_shuffled_and_graded_by_answer_tokens(self):
        target = sentence("我是学生。")
        question = drills.build_question(target, "sentence_builder", language="ru", seed="s")
        self.assertEqual(question["answer_tokens"], ["我", "是", "学生"])
        self.assertNotEqual(question["tokens"], question["answer_tokens"])
        self.assertEqual(sorted(question["tokens"]), sorted(question["answer_tokens"]))
        self.assertNotIn("我是学生", bank.normalize_zh(question["prompt"]))

    def test_long_sentence_builder_is_chunked(self):
        tokens = ["我", "已经", "学", "过", "一", "年", "的", "汉", "语", "了"]
        self.assertLessEqual(len(drills.builder_tokens(tokens)), drills.MAX_BUILDER_TOKENS)
        self.assertEqual("".join(drills.builder_tokens(tokens)), "".join(tokens))

    def test_authored_gap_fill_keeps_the_lesson_options(self):
        target = sentence(
            "你好！",
            gap={"sentence": "____好！", "options": ["你", "们", "关", "不"], "answer_index": 0},
        )
        question = drills.build_question(target, "gap_fill", language="uz", seed="s")
        self.assertEqual(sorted(question["options"]), sorted(["你", "们", "关", "不"]))
        self.assertEqual(question["options"][question["answer_index"]], "你")
        self.assertEqual(question["sentence"], "____好！")

    def test_public_question_hides_grading_fields(self):
        question = drills.build_question(word("你"), "listening_choice", language="uz", seed="s")
        public = drills.public_question(question)
        for field in ("answer_index", "answer_tokens", "correct_answer", "explanation", "target_id"):
            self.assertNotIn(field, public)
        self.assertTrue(public["autoplay"])

    def test_instructions_exist_in_all_three_languages(self):
        for key, texts in drills.INSTRUCTIONS.items():
            self.assertEqual(set(texts), {"uz", "ru", "tj"}, key)
            self.assertTrue(all(text.strip() for text in texts.values()), key)


class ValidatorTests(unittest.TestCase):
    def base(self, **overrides):
        question = {
            "id": "t:1:hanzi_choice",
            "format": "hanzi_choice",
            "prompt": "«sen» — qaysi ieroglif?",
            "sentence": "",
            "pinyin": "",
            "audio_text": "",
            "options": ["你", "好", "您"],
            "answer_index": 0,
        }
        question.update(overrides)
        return question

    def test_valid_question_passes(self):
        self.assertIsNone(drills.validate_question(self.base()))

    def test_prompt_equal_to_an_option_is_rejected(self):
        self.assertEqual(
            drills.validate_question(self.base(prompt="好", options=["你", "好"], answer_index=0)),
            "prompt_equals_option",
        )

    def test_visible_answer_is_rejected(self):
        self.assertEqual(
            drills.validate_question(self.base(format="listening_choice", audio_text="你", sentence="你")),
            "listening_text_visible",
        )
        self.assertEqual(
            drills.validate_question(self.base(prompt="你 — qaysi ieroglif?")),
            "answer_visible",
        )

    def test_listening_without_audio_is_rejected(self):
        self.assertEqual(
            drills.validate_question(self.base(format="listening_choice")),
            "listening_without_audio",
        )

    def test_duplicate_options_are_rejected(self):
        self.assertEqual(
            drills.validate_question(self.base(options=["你", "你！", "好"])),
            "duplicate_options",
        )

    def test_builder_rules(self):
        builder = {
            "id": "t:1:sentence_builder",
            "format": "sentence_builder",
            "prompt": "Gapni tuzing",
            "tokens": ["是", "我", "学生"],
            "answer_tokens": ["我", "是", "学生"],
            "correct_answer": "我是学生。",
        }
        self.assertIsNone(drills.validate_question(builder))
        self.assertEqual(
            drills.validate_question({**builder, "tokens": ["我", "是", "学生"]}),
            "builder_already_ordered",
        )
        self.assertEqual(
            drills.validate_question({**builder, "sentence": "我是学生"}),
            "builder_answer_visible",
        )


class DrillBankTests(unittest.TestCase):
    def test_tone_variants_change_only_the_tone(self):
        self.assertEqual(bank.tone_variants("nǐ"), ["nī", "ní", "nì"])
        self.assertEqual(bank.pinyin_plain("Nǐ hǎo"), "nihao")

    def test_segment_uses_longest_lexicon_words(self):
        self.assertEqual(bank.segment("我是学生。"), ["我", "是", "学生"])

    def test_pool_sentences_have_distinct_keys(self):
        for level in bank.LEVELS:
            keys = Counter(entry["key"] for entry in bank.sentence_pool(level))
            self.assertEqual([key for key, count in keys.items() if count > 1], [])

    def test_snapshot_payload_stays_small(self):
        questions, _ = drills.plan_target(
            sentence("我已经学过汉语。"), language="tj", seed="s", client_formats=drills.ALL_FORMATS, passed=set()
        )
        self.assertLess(len(json.dumps(questions, ensure_ascii=False)), 2400)


if __name__ == "__main__":
    unittest.main()

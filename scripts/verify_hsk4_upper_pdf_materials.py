import importlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


EXPECTED = {
    1: {
        "vocab_count": 32,
        "must_have": {"亮", "幽默", "脾气"},
        "must_not_have": {"照"},
        "grammar": ["不仅……也/还/而且……", "从来", "刚", "即使……也……", "（在）……上"],
    },
    2: {
        "vocab_count": 30,
        "must_have": {"丰富", "无聊", "讨厌", "却", "周围", "交流", "理解", "镜子", "而", "当", "困难", "及时", "陪"},
        "must_not_have": {"了解", "弄", "帮"},
        "grammar": ["正好", "差不多", "尽管", "却", "而"],
    },
    3: {
        "vocab_count": 31,
        "must_have": {"律师", "专业", "首先", "正式", "改变", "不管", "约会"},
        "must_not_have": {"越"},
        "grammar": ["挺", "本来", "另外", "首先", "不管……都……"],
    },
    4: {
        "vocab_count": 31,
        "must_have": {"按照", "工资", "不得不", "责任", "奖金", "调查", "甚至"},
        "must_not_have": {"起初"},
        "grammar": ["以为", "原来", "并", "按照", "甚至"],
    },
    5: {
        "vocab_count": 31,
        "must_have": {"制冷", "实际", "考虑", "标准", "购物", "受到", "寄"},
        "must_not_have": {"冷冻", "的确", "实际上"},
        "grammar": ["肯定", "再说", "实际", "对……来说", "尤其"],
    },
    6: {
        "vocab_count": 31,
        "must_have": {"售货员", "袜子", "打扰", "轻", "方面", "支持", "会员卡", "降低"},
        "must_not_have": {"产品", "品牌", "进口", "国产", "消费", "经济"},
        "grammar": ["竟然", "倍", "值得", "其中", "（在）……下"],
    },
}


def _parse(value):
    return json.loads(value) if isinstance(value, str) else value


def verify_lesson(lesson_no):
    module = importlib.import_module(f"scripts.seed_hsk4_lesson_{lesson_no:02d}")
    lesson = module.LESSON
    vocab = _parse(lesson["vocabulary_json"])
    grammar = _parse(lesson["grammar_json"])
    blocks = _parse(lesson["dialogue_json"])
    intro = _parse(lesson["intro_text"])
    exercises = _parse(lesson["exercise_json"])
    homework = _parse(lesson["homework_json"])
    expected = EXPECTED[lesson_no]

    hanzis = {word.get("zh") for word in vocab}
    titles = [item.get("title_zh") for item in grammar]

    assert isinstance(intro, dict), (lesson_no, "intro_not_i18n")
    for lang in ("uz", "ru", "tj"):
        assert intro.get(lang), (lesson_no, "missing_intro_lang", lang)
        assert "PDF" not in intro[lang] and "pdf" not in intro[lang], (lesson_no, "student_intro_mentions_pdf", lang)

    assert len(vocab) == expected["vocab_count"], (lesson_no, "vocab_count", len(vocab))
    assert len(blocks) == 5, (lesson_no, "dialogue_blocks", len(blocks))
    assert expected["must_have"] <= hanzis, (lesson_no, "missing_words", expected["must_have"] - hanzis)
    assert not (expected["must_not_have"] & hanzis), (lesson_no, "unexpected_words", expected["must_not_have"] & hanzis)
    assert titles == expected["grammar"], (lesson_no, "grammar_titles", titles)
    for word in vocab:
        for lang in ("uz", "ru", "tj"):
            assert word.get(lang), (lesson_no, "missing_word_translation", word.get("zh"), lang)

    for item in grammar:
        for field in ("title_uz", "title_ru", "title_tj", "rule_uz", "rule_ru", "rule_tj"):
            assert item.get(field), (lesson_no, "missing_grammar_i18n", item.get("title_zh"), field)
        for example in item.get("examples") or []:
            assert example.get("pinyin"), (lesson_no, "missing_grammar_example_pinyin", item.get("title_zh"))
            for lang in ("uz", "ru", "tj"):
                assert example.get(lang), (lesson_no, "missing_grammar_example_translation", item.get("title_zh"), lang)

    seen_grammar = []
    for index, block in enumerate(blocks, 1):
        assert int(block.get("block_no") or 0) == index, (lesson_no, "block_no", index)
        assert block.get("scene_uz") and block.get("scene_ru") and block.get("scene_tj"), (lesson_no, "missing_scene_i18n", index)
        assert block.get("word_nos"), (lesson_no, "missing_word_nos", index)
        assert block.get("grammar_nos"), (lesson_no, "missing_grammar_nos", index)
        assert block.get("dialogue"), (lesson_no, "missing_dialogue", index)
        assert block.get("mini_quiz"), (lesson_no, "missing_mini_quiz", index)
        assert block.get("mini_homework"), (lesson_no, "missing_mini_homework", index)
        assert block["mini_homework"].get("instruction_uz"), (lesson_no, "missing_mini_homework_uz", index)
        assert block["mini_homework"].get("instruction_ru"), (lesson_no, "missing_mini_homework_ru", index)
        assert block["mini_homework"].get("instruction_tj"), (lesson_no, "missing_mini_homework_tj", index)
        for line in block.get("dialogue") or []:
            assert line.get("pinyin"), (lesson_no, "missing_dialogue_pinyin", index, line.get("zh"))
            for lang in ("uz", "ru", "tj"):
                assert line.get(lang), (lesson_no, "missing_dialogue_translation", index, line.get("zh"), lang)
        for question in block.get("mini_quiz") or []:
            for field in ("prompt_uz", "prompt_ru", "prompt_tj"):
                assert question.get(field), (lesson_no, "missing_mini_quiz_prompt", index, field)
        seen_grammar.extend(block.get("grammar_nos") or [])

    assert seen_grammar == [1, 2, 3, 4, 5], (lesson_no, "duplicate_or_missing_block_grammar", seen_grammar)
    for exercise in exercises:
        for field in ("instruction_uz", "instruction_ru", "instruction_tj"):
            assert exercise.get(field), (lesson_no, "missing_exercise_instruction", field)
    for task in homework:
        for field in ("instruction_uz", "instruction_ru", "instruction_tj"):
            assert task.get(field), (lesson_no, "missing_homework_instruction", field)


def main():
    for lesson_no in EXPECTED:
        verify_lesson(lesson_no)
    print("ok: HSK4 上 lessons 1-6 PDF materials verified")


if __name__ == "__main__":
    main()

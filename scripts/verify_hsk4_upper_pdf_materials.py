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
}


def _parse(value):
    return json.loads(value) if isinstance(value, str) else value


def verify_lesson(lesson_no):
    module = importlib.import_module(f"scripts.seed_hsk4_lesson_{lesson_no:02d}")
    lesson = module.LESSON
    vocab = _parse(lesson["vocabulary_json"])
    grammar = _parse(lesson["grammar_json"])
    blocks = _parse(lesson["dialogue_json"])
    expected = EXPECTED[lesson_no]

    hanzis = {word.get("zh") for word in vocab}
    titles = [item.get("title_zh") for item in grammar]

    assert len(vocab) == expected["vocab_count"], (lesson_no, "vocab_count", len(vocab))
    assert len(blocks) == 5, (lesson_no, "dialogue_blocks", len(blocks))
    assert expected["must_have"] <= hanzis, (lesson_no, "missing_words", expected["must_have"] - hanzis)
    assert not (expected["must_not_have"] & hanzis), (lesson_no, "unexpected_words", expected["must_not_have"] & hanzis)
    assert titles == expected["grammar"], (lesson_no, "grammar_titles", titles)

    seen_grammar = []
    for index, block in enumerate(blocks, 1):
        assert int(block.get("block_no") or 0) == index, (lesson_no, "block_no", index)
        assert block.get("word_nos"), (lesson_no, "missing_word_nos", index)
        assert block.get("grammar_nos"), (lesson_no, "missing_grammar_nos", index)
        assert block.get("dialogue"), (lesson_no, "missing_dialogue", index)
        assert block.get("mini_quiz"), (lesson_no, "missing_mini_quiz", index)
        assert block.get("mini_homework"), (lesson_no, "missing_mini_homework", index)
        seen_grammar.extend(block.get("grammar_nos") or [])

    assert seen_grammar == [1, 2, 3, 4, 5], (lesson_no, "duplicate_or_missing_block_grammar", seen_grammar)


def main():
    for lesson_no in EXPECTED:
        verify_lesson(lesson_no)
    print("ok: HSK4 上 lessons 1-3 PDF materials verified")


if __name__ == "__main__":
    main()

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

EXPECTED = {
    1: {"vocab": 14, "dialogues": 4, "lines": 19, "grammar": 3},
    2: {"vocab": 16, "dialogues": 4, "lines": 19, "grammar": 3},
    3: {"vocab": 15, "dialogues": 4, "lines": 17, "grammar": 3},
}


def load_seed(order: int):
    path = ROOT / f"seed_nhsk2_lesson_{order:02d}.py"
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verify(order: int) -> dict[str, int]:
    mod = load_seed(order)
    lesson = mod.LESSON
    exp = EXPECTED[order]

    assert lesson["level"] == "nhsk2"
    assert lesson["lesson_order"] == order
    assert lesson["lesson_code"] == f"NHSK2-L{order:02d}"

    vocab = json.loads(lesson["vocabulary_json"])
    dialogues = json.loads(lesson["dialogue_json"])
    grammar = json.loads(lesson["grammar_json"])

    assert len(vocab) == exp["vocab"], (order, "vocab", len(vocab))
    assert len(dialogues) == exp["dialogues"], (order, "dialogues", len(dialogues))
    assert len(grammar) == exp["grammar"], (order, "grammar", len(grammar))

    for word in vocab:
        assert word["zh"] and word["pinyin"] and word["pos"]
        for lang in ("uz", "ru", "tj"):
            assert word.get(lang), f"lesson {order}: missing {lang} for {word['zh']}"

    lines = 0
    for block in dialogues:
        assert block["scene_zh"]
        for lang in ("uz", "ru", "tj"):
            assert block.get(f"scene_{lang}")
        for row in block["dialogue"]:
            lines += 1
            assert row["speaker"] and row["zh"] and row["pinyin"]
            for lang in ("uz", "ru", "tj"):
                assert row.get(lang), f"lesson {order}: missing {lang} for {row['zh']}"
    assert lines == exp["lines"], (order, "lines", lines)

    for point in grammar:
        assert point["title_zh"] and point["rule_zh"] and point["examples"]
        for lang in ("uz", "ru", "tj"):
            assert point.get(f"title_{lang}") and point.get(f"rule_{lang}")

    return {
        "vocab": len(vocab),
        "dialogues": len(dialogues),
        "lines": lines,
        "grammar": len(grammar),
    }


def main() -> None:
    for order in sorted(EXPECTED):
        stats = verify(order)
        print(f"OK lesson {order:02d}: " + " ".join(f"{k}={v}" for k, v in stats.items()))


if __name__ == "__main__":
    main()

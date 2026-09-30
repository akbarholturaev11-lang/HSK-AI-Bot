from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEED = ROOT / "seed_nhsk1_lesson_01.py"


def load_seed():
    spec = importlib.util.spec_from_file_location("seed_nhsk1_lesson_01", SEED)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load seed")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    mod = load_seed()
    lesson = mod.LESSON
    assert lesson["level"] == "nhsk1"
    assert lesson["lesson_order"] == 1
    assert lesson["lesson_code"] == "NHSK1-L01"

    vocab = json.loads(lesson["vocabulary_json"])
    dialogues = json.loads(lesson["dialogue_json"])
    grammar = json.loads(lesson["grammar_json"])

    assert len(vocab) == 12, f"expected 12 core vocabulary items, got {len(vocab)}"
    assert len({w["zh"] for w in vocab}) == len(vocab), "duplicate vocabulary"
    assert grammar == [], "lesson 1 should not invent grammar items"

    required_langs = ("uz", "ru", "tj")
    for word in vocab:
        assert word["zh"] and word["pinyin"] and word["pos"]
        for lang in required_langs:
            assert word.get(lang), f"missing {lang} for {word['zh']}"

    assert len(dialogues) == 3, f"expected 3 dialogue blocks, got {len(dialogues)}"
    line_count = 0
    for block in dialogues:
        assert block.get("scene_zh")
        for lang in required_langs:
            assert block.get(f"scene_{lang}")
        for line in block["dialogue"]:
            line_count += 1
            assert line["speaker"] and line["zh"] and line["pinyin"]
            for lang in required_langs:
                assert line.get(lang), f"missing {lang} dialogue translation for {line['zh']}"
    assert line_count == 10, f"expected 10 dialogue lines, got {line_count}"

    print("OK: nhsk1 lesson 01 source")
    print(f"vocabulary={len(vocab)} dialogues={len(dialogues)} lines={line_count} grammar={len(grammar)}")


if __name__ == "__main__":
    main()

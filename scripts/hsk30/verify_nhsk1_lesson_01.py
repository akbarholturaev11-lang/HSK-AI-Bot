from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

EXPECTED = {
    1: {"vocab": 12, "dialogues": 3, "lines": 10, "grammar": 0},
    2: {"vocab": 15, "dialogues": 3, "lines": 10, "grammar": 1},
    3: {"vocab": 18, "dialogues": 3, "lines": 12, "grammar": 3},
    4: {"vocab": 21, "dialogues": 3, "lines": 14, "grammar": 4},
    5: {"vocab": 22, "dialogues": 3, "lines": 14, "grammar": 3},
    6: {"vocab": 22, "dialogues": 3, "lines": 14, "grammar": 3},
    7: {"vocab": 27, "dialogues": 3, "lines": 14, "grammar": 4},
    8: {"vocab": 23, "dialogues": 3, "lines": 14, "grammar": 3},
    9: {"vocab": 23, "dialogues": 3, "lines": 14, "grammar": 3},
    10: {"vocab": 23, "dialogues": 3, "lines": 16, "grammar": 3},
    11: {"vocab": 25, "dialogues": 3, "lines": 14, "grammar": 3},
    12: {"vocab": 24, "dialogues": 3, "lines": 14, "grammar": 3},
}


def load_seed(order: int):
    path = ROOT / f"seed_nhsk1_lesson_{order:02d}.py"
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

    assert lesson["level"] == "nhsk1"
    assert lesson["lesson_order"] == order
    assert lesson["lesson_code"] == f"NHSK1-L{order:02d}"

    vocab = json.loads(lesson["vocabulary_json"])
    dialogues = json.loads(lesson["dialogue_json"])
    grammar = json.loads(lesson["grammar_json"])

    assert len(vocab) == exp["vocab"], (order, "vocab", len(vocab))
    assert len({(w["zh"], w["pinyin"], w["pos"]) for w in vocab}) == len(vocab), f"lesson {order}: duplicate vocab entry"
    assert len(dialogues) == exp["dialogues"], (order, "dialogues", len(dialogues))
    assert len(grammar) == exp["grammar"], (order, "grammar", len(grammar))

    required_langs = ("uz", "ru", "tj")
    for word in vocab:
        assert word["zh"] and word["pinyin"] and word["pos"]
        for lang in required_langs:
            assert word.get(lang), f"lesson {order}: missing {lang} for {word['zh']}"

    line_count = 0
    for block in dialogues:
        assert block.get("scene_zh")
        for lang in required_langs:
            assert block.get(f"scene_{lang}")
        for line in block["dialogue"]:
            line_count += 1
            assert line["speaker"] and line["zh"] and line["pinyin"]
            for lang in required_langs:
                assert line.get(lang), f"lesson {order}: missing {lang} for {line['zh']}"
    assert line_count == exp["lines"], (order, "lines", line_count)

    for g in grammar:
        assert g["title_zh"]
        for lang in required_langs:
            assert g.get(f"title_{lang}") and g.get(f"rule_{lang}")
        assert g.get("examples")
        for ex in g["examples"]:
            assert ex["zh"] and ex["pinyin"]
            for lang in required_langs:
                assert ex.get(lang)

    return {"vocab": len(vocab), "dialogues": len(dialogues), "lines": line_count, "grammar": len(grammar)}


def main() -> None:
    for order in sorted(EXPECTED):
        stats = verify(order)
        print(f"OK lesson {order:02d}: " + " ".join(f"{k}={v}" for k, v in stats.items()))


if __name__ == "__main__":
    main()

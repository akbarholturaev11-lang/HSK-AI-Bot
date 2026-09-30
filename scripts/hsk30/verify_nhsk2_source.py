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


def verify_index() -> dict[str, int]:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    source_rows = index["common_index_rows"]
    source_words = {row["zh"] for row in source_rows}
    beyond = set(index["beyond_syllabus"])
    proper = {row["zh"] for row in index["proper_nouns"]}

    actual_occurrences: dict[str, set[int]] = {}
    proper_seen: set[str] = set()

    for order in range(1, 16):
        lesson = load_seed(order).LESSON
        for item in json.loads(lesson["vocabulary_json"]):
            actual_occurrences.setdefault(item["zh"], set()).add(order)
        for item in json.loads(lesson.get("proper_nouns_json", "[]")):
            proper_seen.add(item["zh"])

    actual_words = set(actual_occurrences)
    assert actual_words == source_words, (
        f"index coverage mismatch missing={sorted(source_words-actual_words)} "
        f"extras={sorted(actual_words-source_words)}"
    )
    assert proper <= proper_seen, f"missing proper nouns: {sorted(proper-proper_seen)}"

    for row in source_rows:
        if row["zh"] == "过":
            continue
        assert sorted(actual_occurrences[row["zh"]]) == row["lessons"], (
            row["zh"], sorted(actual_occurrences[row["zh"]]), row["lessons"]
        )

    counts = index["source_counts"]
    assert len(source_rows) == counts["common_index_rows"] == 207
    assert len(source_words) == counts["unique_common_spellings"] == 206
    assert len(beyond) == counts["common_rows_marked_beyond_syllabus"] == 10
    assert sum(not row["beyond_syllabus"] for row in source_rows) == 197
    assert len(index["proper_nouns"]) == 3
    assert 197 + 3 == counts["syllabus_rows_including_proper_nouns"] == 200

    guo_rows = [row for row in source_rows if row["zh"] == "过"]
    assert [(row["pinyin"], row["lessons"]) for row in guo_rows] == [
        ("guò", [6]),
        ("guo", [4]),
    ]

    return {
        "lesson_vocab_rows": sum(EXPECTED[i]["vocab"] for i in EXPECTED),
        "index_rows": len(source_rows),
        "unique_spellings": len(source_words),
        "beyond_syllabus": len(beyond),
        "proper_nouns": len(index["proper_nouns"]),
        "syllabus_rows": counts["syllabus_rows_including_proper_nouns"],
    }


def main() -> None:
    for order in sorted(EXPECTED):
        stats = verify(order)
        print(f"OK lesson {order:02d}: " + " ".join(f"{k}={v}" for k, v in stats.items()))
    audit = verify_index()
    print("OK N2 index: " + " ".join(f"{k}={v}" for k, v in audit.items()))


if __name__ == "__main__":
    main()

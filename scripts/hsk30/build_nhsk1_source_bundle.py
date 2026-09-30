from __future__ import annotations

import importlib.util
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated" / "nhsk1"
INDEX = ROOT / "nhsk1_vocab_index.json"


def load_seed(order: int):
    path = ROOT / f"seed_nhsk1_lesson_{order:02d}.py"
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.LESSON


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    source_words = set(index["common_words"])
    source_proper = set(index["proper_nouns"])
    beyond = set(index["beyond_syllabus"])

    vocab_occurrences: dict[str, list[dict]] = defaultdict(list)
    proper_occurrences: dict[str, list[dict]] = defaultdict(list)
    grammar_points: list[dict] = []
    dialogue_lessons: list[dict] = []

    total_vocab_rows = 0
    total_dialogue_blocks = 0
    total_dialogue_lines = 0

    for order in range(1, 16):
        lesson = load_seed(order)

        vocab = json.loads(lesson["vocabulary_json"])
        total_vocab_rows += len(vocab)
        for item in vocab:
            row = dict(item)
            row["lesson_order"] = order
            vocab_occurrences[item["zh"]].append(row)

        proper = json.loads(lesson.get("proper_nouns_json", "[]"))
        for item in proper:
            row = dict(item)
            row["lesson_order"] = order
            proper_occurrences[item["zh"]].append(row)

        grammar = json.loads(lesson["grammar_json"])
        for item in grammar:
            row = dict(item)
            row["lesson_order"] = order
            row["lesson_code"] = lesson["lesson_code"]
            grammar_points.append(row)

        dialogues = json.loads(lesson["dialogue_json"])
        total_dialogue_blocks += len(dialogues)
        total_dialogue_lines += sum(len(block["dialogue"]) for block in dialogues)
        dialogue_lessons.append(
            {
                "lesson_order": order,
                "lesson_code": lesson["lesson_code"],
                "title": lesson["title"],
                "title_pinyin": lesson["title_pinyin"],
                "goal": json.loads(lesson["goal"]),
                "intro_text": json.loads(lesson["intro_text"]),
                "source": getattr(
                    __import__(f"seed_nhsk1_lesson_{order:02d}"),
                    "SOURCE",
                    {},
                )
                if False
                else {},
                "blocks": dialogues,
            }
        )

    actual_words = set(vocab_occurrences)
    missing = sorted(source_words - actual_words)
    extras = sorted(actual_words - source_words)
    if missing or extras:
        raise AssertionError(
            f"vocabulary index mismatch: missing={missing}, extras={extras}"
        )

    wordlist = []
    for zh in index["common_words"]:
        occurrences = vocab_occurrences[zh]

        grouped: dict[tuple[str, str], dict] = {}
        for row in occurrences:
            key = (row["pinyin"], row["pos"])
            if key not in grouped:
                grouped[key] = {
                    "pinyin": row["pinyin"],
                    "pos": row["pos"],
                    "uz": row["uz"],
                    "ru": row["ru"],
                    "tj": row["tj"],
                    "lesson_orders": [],
                }
            grouped[key]["lesson_orders"].append(row["lesson_order"])

        senses = []
        for _, sense in sorted(grouped.items()):
            sense["lesson_orders"] = sorted(set(sense["lesson_orders"]))
            senses.append(sense)

        wordlist.append(
            {
                "zh": zh,
                "lesson_orders": sorted(
                    {row["lesson_order"] for row in occurrences}
                ),
                "beyond_syllabus": zh in beyond,
                "senses": senses,
            }
        )

    proper_nouns = []
    all_proper_names = sorted(
        set(index["proper_nouns"]) | set(index["allowed_character_name_extras"])
    )
    for zh in all_proper_names:
        occurrences = proper_occurrences.get(zh, [])
        proper_nouns.append(
            {
                "zh": zh,
                "source_index": zh in source_proper,
                "character_name_extra": zh
                in set(index["allowed_character_name_extras"]),
                "lesson_orders": sorted(
                    {row["lesson_order"] for row in occurrences}
                ),
                "forms": [
                    {
                        key: row[key]
                        for key in ("pinyin", "en", "uz", "ru", "tj")
                        if key in row
                    }
                    for row in occurrences
                ],
            }
        )

    manifest = {
        "schema_version": 1,
        "track": "hsk30",
        "level": "nhsk1",
        "source_book": index["source_book"],
        "source_pdf_path": index["source_pdf_path"],
        "lesson_count": 15,
        "common_index_words": len(source_words),
        "common_index_beyond_syllabus": len(beyond),
        "proper_nouns_in_source_index": len(source_proper),
        "character_name_extras": len(index["allowed_character_name_extras"]),
        "vocabulary_rows_across_lessons": total_vocab_rows,
        "grammar_points": len(grammar_points),
        "dialogue_blocks": total_dialogue_blocks,
        "dialogue_lines": total_dialogue_lines,
        "publisher_claim_aligned_words": index["source_counts"][
            "publisher_claim_aligned_words"
        ],
        "counting_note": index["counting_note"],
    }

    assert manifest["common_index_words"] == 307
    assert manifest["common_index_beyond_syllabus"] == 8
    assert manifest["proper_nouns_in_source_index"] == 12
    assert manifest["vocabulary_rows_across_lessons"] == 333
    assert manifest["grammar_points"] == 40
    assert manifest["dialogue_blocks"] == 45
    assert manifest["dialogue_lines"] == 203

    dump(OUT / "manifest.json", manifest)
    dump(OUT / "wordlist.json", wordlist)
    dump(OUT / "grammar.json", grammar_points)
    dump(OUT / "dialogues.json", dialogue_lessons)
    dump(OUT / "proper_nouns.json", proper_nouns)

    print("OK: generated nhsk1 source bundle")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

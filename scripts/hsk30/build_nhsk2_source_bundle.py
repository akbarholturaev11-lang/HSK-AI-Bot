from __future__ import annotations

import importlib.util
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated" / "nhsk2"
INDEX = ROOT / "nhsk2_vocab_index.json"


def load_seed(order: int):
    path = ROOT / f"seed_nhsk2_lesson_{order:02d}.py"
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
    beyond = set(index["beyond_syllabus"])
    vocab_occurrences = defaultdict(list)
    proper_occurrences = defaultdict(list)
    grammar_points = []
    dialogue_lessons = []
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

        for item in json.loads(lesson.get("proper_nouns_json", "[]")):
            row = dict(item)
            row["lesson_order"] = order
            proper_occurrences[item["zh"]].append(row)

        for item in json.loads(lesson["grammar_json"]):
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
                "blocks": dialogues,
            }
        )

    source_words = {row["zh"] for row in index["common_index_rows"]}
    actual_words = set(vocab_occurrences)
    assert actual_words == source_words, (
        f"missing={sorted(source_words-actual_words)} "
        f"extras={sorted(actual_words-source_words)}"
    )

    first_index_row = {}
    source_rows_by_word = defaultdict(list)
    for row in index["common_index_rows"]:
        source_rows_by_word[row["zh"]].append(row["row"])
        first_index_row.setdefault(row["zh"], row["row"])

    wordlist = []
    for zh in sorted(source_words, key=lambda x: first_index_row[x]):
        senses = {}
        for row in vocab_occurrences[zh]:
            key = (row["pinyin"], row["pos"])
            if key not in senses:
                senses[key] = {
                    "pinyin": row["pinyin"],
                    "pos": row["pos"],
                    "uz": row["uz"],
                    "ru": row["ru"],
                    "tj": row["tj"],
                    "lesson_orders": [],
                }
            senses[key]["lesson_orders"].append(row["lesson_order"])

        wordlist.append(
            {
                "zh": zh,
                "level": "N2",
                "beyond_syllabus": zh in beyond,
                "lesson_orders": sorted(
                    {row["lesson_order"] for row in vocab_occurrences[zh]}
                ),
                "source_index_rows": source_rows_by_word[zh],
                "senses": [
                    {
                        **sense,
                        "lesson_orders": sorted(set(sense["lesson_orders"])),
                    }
                    for sense in senses.values()
                ],
            }
        )

    proper_nouns = []
    for source in index["proper_nouns"]:
        forms = proper_occurrences.get(source["zh"], [])
        proper_nouns.append(
            {
                "zh": source["zh"],
                "pinyin": source["pinyin"],
                "lesson_orders": source["lessons"],
                "source_index": True,
                "forms": [
                    {
                        key: row[key]
                        for key in ("pinyin", "en", "uz", "ru", "tj")
                        if key in row
                    }
                    for row in forms
                ],
            }
        )

    hanzi = set()
    for row in index["common_index_rows"]:
        if row["beyond_syllabus"]:
            continue
        hanzi.update(ch for ch in row["zh"] if "\u4e00" <= ch <= "\u9fff")
    for row in index["proper_nouns"]:
        hanzi.update(ch for ch in row["zh"] if "\u4e00" <= ch <= "\u9fff")

    manifest = {
        "schema_version": 1,
        "track": "hsk30",
        "level": "nhsk2",
        "source_book": index["source_book"],
        "source_pdf_path": index["source_pdf_path"],
        "source_lfs_oid_sha256": index["source_lfs_oid_sha256"],
        "lesson_count": 15,
        "lesson_vocabulary_rows": total_vocab_rows,
        "common_index_rows": index["source_counts"]["common_index_rows"],
        "unique_common_spellings": index["source_counts"]["unique_common_spellings"],
        "beyond_syllabus_rows": index["source_counts"]["common_rows_marked_beyond_syllabus"],
        "in_syllabus_common_rows": index["source_counts"]["common_rows_in_syllabus"],
        "proper_noun_rows": index["source_counts"]["proper_noun_rows"],
        "syllabus_rows": index["source_counts"]["syllabus_rows_including_proper_nouns"],
        "grammar_points": len(grammar_points),
        "dialogue_blocks": total_dialogue_blocks,
        "dialogue_lines": total_dialogue_lines,
        "derived_hanzi_count": len(hanzi),
        "counting_note": index["counting_note"],
    }

    assert manifest["lesson_vocabulary_rows"] == 211
    assert manifest["common_index_rows"] == 207
    assert manifest["unique_common_spellings"] == 206
    assert manifest["beyond_syllabus_rows"] == 10
    assert manifest["in_syllabus_common_rows"] == 197
    assert manifest["proper_noun_rows"] == 3
    assert manifest["syllabus_rows"] == 200
    assert manifest["grammar_points"] == 45
    assert manifest["dialogue_blocks"] == 60
    assert manifest["dialogue_lines"] == 308

    dump(OUT / "manifest.json", manifest)
    dump(OUT / "wordlist.json", wordlist)
    dump(OUT / "grammar.json", grammar_points)
    dump(OUT / "dialogues.json", dialogue_lessons)
    dump(OUT / "proper_nouns.json", proper_nouns)
    dump(
        OUT / "hanzi.json",
        {
            "schema_version": 1,
            "track": "hsk30",
            "level": "N2",
            "status": "derived_from_textbook_syllabus_rows_not_official_hanzi_list",
            "source_pdf_path": index["source_pdf_path"],
            "derived_from": "197 non-star common index rows plus 3 proper-noun syllabus rows",
            "count": len(hanzi),
            "expected_official_increment_from_plan": 125,
            "validation_status": "pending_official_hanzi_source",
            "note": (
                "This is a derived character set from textbook vocabulary/proper-noun "
                "rows, not the official HSK 3.0 hanzi list."
            ),
            "characters": sorted(hanzi),
        },
    )

    print("OK: generated nhsk2 source bundle")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

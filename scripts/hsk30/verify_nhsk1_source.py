from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "nhsk1_vocab_index.json"


def load_seed(order: int):
    path = ROOT / f"seed_nhsk1_lesson_{order:02d}.py"
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    source_words = set(index["common_words"])
    source_proper = set(index["proper_nouns"])
    beyond = set(index["beyond_syllabus"])
    allowed_name_extras = set(index["allowed_character_name_extras"])

    vocab_rows = []
    proper_rows = []
    dialogue_blocks = 0
    dialogue_lines = 0
    grammar_points = 0

    for order in range(1, 16):
        lesson = load_seed(order).LESSON
        assert lesson["level"] == "nhsk1"
        assert lesson["lesson_order"] == order
        assert lesson["lesson_code"] == f"NHSK1-L{order:02d}"

        vocab = json.loads(lesson["vocabulary_json"])
        vocab_rows.extend((order, x["zh"], x["pinyin"], x["pos"]) for x in vocab)

        if "proper_nouns_json" in lesson:
            proper = json.loads(lesson["proper_nouns_json"])
            proper_rows.extend((order, x["zh"], x["pinyin"]) for x in proper)

        dialogues = json.loads(lesson["dialogue_json"])
        dialogue_blocks += len(dialogues)
        dialogue_lines += sum(len(x["dialogue"]) for x in dialogues)

        grammar = json.loads(lesson["grammar_json"])
        grammar_points += len(grammar)

    vocab_words = {x[1] for x in vocab_rows}
    proper_words = {x[1] for x in proper_rows}

    missing_vocab = sorted(source_words - vocab_words)
    extra_vocab = sorted(vocab_words - source_words)
    assert not missing_vocab, f"missing vocabulary-index words: {missing_vocab}"
    assert not extra_vocab, f"unexpected vocabulary words: {extra_vocab}"

    missing_proper = sorted(source_proper - proper_words)
    extra_proper = sorted(proper_words - source_proper)
    assert not missing_proper, f"missing proper nouns: {missing_proper}"
    assert set(extra_proper) == allowed_name_extras, (
        "unexpected proper-name extras: "
        f"actual={extra_proper}, expected={sorted(allowed_name_extras)}"
    )

    assert beyond <= vocab_words
    assert len(source_words) == 307
    assert len(source_proper) == 12
    assert len(beyond) == 8
    assert len(vocab_words) == 307
    assert len(vocab_rows) == 333
    assert dialogue_blocks == 45
    assert dialogue_lines == 203
    assert grammar_points == 40

    print("OK: nhsk1 source audit")
    print(
        "lessons=15 "
        f"vocab_rows={len(vocab_rows)} "
        f"unique_vocab={len(vocab_words)} "
        f"source_proper={len(source_proper)} "
        f"character_name_extras={len(extra_proper)} "
        f"beyond_syllabus={len(beyond)} "
        f"dialogue_blocks={dialogue_blocks} "
        f"dialogue_lines={dialogue_lines} "
        f"grammar_points={grammar_points}"
    )


if __name__ == "__main__":
    main()

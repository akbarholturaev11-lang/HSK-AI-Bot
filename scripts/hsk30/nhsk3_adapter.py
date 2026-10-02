from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE_DIR = HERE / "normalized" / "nhsk3"
TRANSLATION_DIR = HERE / "translations" / "nhsk3"


class Nhsk3TranslationError(RuntimeError):
    pass


def _load_json(path: Path) -> dict:
    if not path.is_file():
        raise Nhsk3TranslationError(f"missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _need_text(value, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise Nhsk3TranslationError(f"missing translation: {label}")
    return text


def _validate_langs(row: dict, label: str) -> None:
    for lang in ("uz", "ru", "tj"):
        _need_text(row.get(lang), f"{label}.{lang}")


def load_seed_lesson(order: int) -> dict:
    order = int(order)
    source_path = SOURCE_DIR / f"lesson_{order:02d}.json"
    translation_path = TRANSLATION_DIR / f"lesson_{order:02d}.json"

    source = _load_json(source_path)
    tr = _load_json(translation_path)

    if source.get("level") != "nhsk3" or source.get("lesson") != order:
        raise Nhsk3TranslationError(f"invalid N3 source identity: {source_path}")
    if tr.get("lesson") != order:
        raise Nhsk3TranslationError(f"translation lesson mismatch: {translation_path}")

    source_title = source["title"]["hanzi"]
    if tr.get("source_title_hanzi") != source_title:
        raise Nhsk3TranslationError(
            f"translation source title mismatch for lesson {order}: "
            f"{tr.get('source_title_hanzi')!r} != {source_title!r}"
        )

    goal = tr.get("goal") or {}
    intro = tr.get("intro_text") or {}
    _validate_langs(goal, "goal")
    _validate_langs(intro, "intro_text")

    source_vocab = source.get("vocabulary") or []
    tr_vocab = tr.get("vocabulary") or []
    if len(source_vocab) != len(tr_vocab):
        raise Nhsk3TranslationError(
            f"lesson {order}: vocabulary count mismatch "
            f"{len(source_vocab)} != {len(tr_vocab)}"
        )
    vocabulary = []
    for idx, (src, lang) in enumerate(zip(source_vocab, tr_vocab), start=1):
        if (src.get("hanzi"), src.get("pinyin")) != (
            lang.get("hanzi"),
            lang.get("pinyin"),
        ):
            raise Nhsk3TranslationError(
                f"lesson {order}: vocabulary alignment mismatch at {idx}"
            )
        _validate_langs(lang, f"vocabulary[{idx}]")
        vocabulary.append(
            {
                "no": idx,
                "zh": src["hanzi"],
                "pinyin": src["pinyin"],
                "pos": src.get("part_of_speech") or "",
                "uz": lang["uz"],
                "ru": lang["ru"],
                "tj": lang["tj"],
                "source_page": src.get("source_page"),
            }
        )

    source_grammar = source.get("grammar") or []
    tr_grammar = tr.get("grammar") or []
    if len(source_grammar) != len(tr_grammar):
        raise Nhsk3TranslationError(
            f"lesson {order}: grammar count mismatch "
            f"{len(source_grammar)} != {len(tr_grammar)}"
        )
    grammar = []
    for idx, (src, lang) in enumerate(zip(source_grammar, tr_grammar), start=1):
        if src.get("label") != lang.get("label"):
            raise Nhsk3TranslationError(
                f"lesson {order}: grammar alignment mismatch at {idx}"
            )
        for key in (
            "title_uz",
            "title_ru",
            "title_tj",
            "rule_uz",
            "rule_ru",
            "rule_tj",
        ):
            _need_text(lang.get(key), f"grammar[{idx}].{key}")
        src_examples = src.get("examples") or []
        tr_examples = lang.get("examples") or []
        if len(src_examples) != len(tr_examples):
            raise Nhsk3TranslationError(
                f"lesson {order}: grammar example count mismatch at {idx}"
            )
        examples = []
        for ex_idx, (src_ex, tr_ex) in enumerate(
            zip(src_examples, tr_examples), start=1
        ):
            if src_ex.get("hanzi") != tr_ex.get("hanzi"):
                raise Nhsk3TranslationError(
                    f"lesson {order}: grammar example alignment mismatch "
                    f"{idx}.{ex_idx}"
                )
            _validate_langs(tr_ex, f"grammar[{idx}].examples[{ex_idx}]")
            examples.append(
                {
                    "zh": src_ex["hanzi"],
                    "pinyin": src_ex.get("pinyin") or "",
                    "uz": tr_ex["uz"],
                    "ru": tr_ex["ru"],
                    "tj": tr_ex["tj"],
                }
            )
        grammar.append(
            {
                "no": idx,
                "title_zh": src["label"],
                "title_uz": lang["title_uz"],
                "title_ru": lang["title_ru"],
                "title_tj": lang["title_tj"],
                "rule_uz": lang["rule_uz"],
                "rule_ru": lang["rule_ru"],
                "rule_tj": lang["rule_tj"],
                "examples": examples,
                "source_page": src.get("source_page"),
                "rule_origin": "assistant_authored_from_source_grammar_label",
            }
        )

    source_dialogues = source.get("dialogues") or []
    tr_dialogues = tr.get("dialogues") or []
    if len(source_dialogues) != len(tr_dialogues):
        raise Nhsk3TranslationError(
            f"lesson {order}: dialogue block count mismatch "
            f"{len(source_dialogues)} != {len(tr_dialogues)}"
        )
    dialogues = []
    for block_idx, (src, lang) in enumerate(
        zip(source_dialogues, tr_dialogues), start=1
    ):
        if src.get("scene") != lang.get("scene_zh"):
            raise Nhsk3TranslationError(
                f"lesson {order}: dialogue scene mismatch at block {block_idx}"
            )
        for key in ("scene_uz", "scene_ru", "scene_tj"):
            _need_text(lang.get(key), f"dialogues[{block_idx}].{key}")
        src_turns = src.get("turns") or []
        tr_turns = lang.get("turns") or []
        if len(src_turns) != len(tr_turns):
            raise Nhsk3TranslationError(
                f"lesson {order}: dialogue turn count mismatch at block {block_idx}"
            )
        turns = []
        for turn_idx, (src_turn, tr_turn) in enumerate(
            zip(src_turns, tr_turns), start=1
        ):
            if src_turn.get("hanzi") != tr_turn.get("hanzi"):
                raise Nhsk3TranslationError(
                    f"lesson {order}: dialogue alignment mismatch "
                    f"{block_idx}.{turn_idx}"
                )
            _validate_langs(
                tr_turn,
                f"dialogues[{block_idx}].turns[{turn_idx}]",
            )
            turns.append(
                {
                    "speaker": src_turn["speaker"],
                    "zh": src_turn["hanzi"],
                    "pinyin": src_turn.get("pinyin") or "",
                    "uz": tr_turn["uz"],
                    "ru": tr_turn["ru"],
                    "tj": tr_turn["tj"],
                }
            )
        dialogues.append(
            {
                "block_no": block_idx,
                "section_label": f"课文 {block_idx}",
                "scene_zh": src["scene"],
                "scene_uz": lang["scene_uz"],
                "scene_ru": lang["scene_ru"],
                "scene_tj": lang["scene_tj"],
                "source_page": src.get("source_page"),
                "dialogue": turns,
            }
        )

    return {
        "level": "nhsk3",
        "lesson_order": order,
        "lesson_code": f"NHSK3-L{order:02d}",
        "title": source_title,
        "title_pinyin": source["title"]["pinyin"],
        "goal": json.dumps(goal, ensure_ascii=False),
        "intro_text": json.dumps(intro, ensure_ascii=False),
        "vocabulary_json": json.dumps(vocabulary, ensure_ascii=False),
        "grammar_json": json.dumps(grammar, ensure_ascii=False),
        "dialogue_json": json.dumps(dialogues, ensure_ascii=False),
        "source_provenance": source.get("source"),
        "translation_origin": "assistant_authored_from_source_verified_chinese",
    }

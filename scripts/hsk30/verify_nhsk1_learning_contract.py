"""Read-only HSK 3.0 N1 Course V3 material quality gate (stdlib only).

This validates the current, shipped schema without regenerating lessons or
changing answer keys, access rules, or existing position-based material refs.
Pedagogical issues are reported separately from hard compatibility errors.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "app" / "static" / "course_v3_data"
LANGUAGES = ("uz", "ru", "tj")
CHOICE_TYPES = {
    "meaning_guess", "pinyin_choice", "hanzi_choice", "translation_choice",
    "listening_choice", "gap_fill", "quick_quiz", "dialog_cloze", "dialog_context",
    "character_recognition",
}
BUILDER_TYPES = {"sentence_builder", "word_order", "reverse_builder"}
CARD_TYPES = CHOICE_TYPES | BUILDER_TYPES | {
    "active_word", "pronunciation", "match_pairs", "_grammar", "_dialogue",
    "_basics", "_word_flash", "_word_listen", "_word_pick_meaning",
    "_word_pick_hanzi",
}


def localized(value: object) -> bool:
    return isinstance(value, dict) and all(
        isinstance(value.get(lang), str) and bool(value[lang].strip())
        for lang in LANGUAGES
    )


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_card(card: object, where: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(card, dict):
        return [f"{where}: card must be an object"], warnings
    kind = card.get("type")
    if kind not in CARD_TYPES:
        return [f"{where}: unsupported card type {kind!r}"], warnings

    if kind == "active_word":
        word = card.get("word")
        if not isinstance(word, dict) or not nonempty(word.get("zh")) or not nonempty(word.get("pinyin")):
            errors.append(f"{where}: active_word needs zh and pinyin")
        elif not localized(word.get("meaning")):
            errors.append(f"{where}: active_word meaning must have uz/ru/tj")
    elif kind == "pronunciation":
        if not nonempty(card.get("phrase")) or not nonempty(card.get("pinyin")):
            errors.append(f"{where}: pronunciation needs phrase and pinyin")
    elif kind == "_grammar":
        g = card.get("g")
        if not isinstance(g, dict):
            errors.append(f"{where}: _grammar needs a g object")
    elif kind in CHOICE_TYPES:
        options = card.get("options")
        answer = card.get("correct_index")
        if not isinstance(options, list) or len(options) < 2:
            errors.append(f"{where}: at least two options required")
        elif type(answer) is not int or not (0 <= answer < len(options)):
            errors.append(f"{where}: correct_index out of range")
        else:
            raw = [json.dumps(x, ensure_ascii=False, sort_keys=True) for x in options]
            if len(set(raw)) != len(raw):
                warnings.append(f"{where}: duplicate answer option (ambiguous question)")
            if any(x is None or x == "" or x == {} for x in options):
                errors.append(f"{where}: empty answer option")
        if kind == "listening_choice" and not nonempty(card.get("audio_text")):
            errors.append(f"{where}: listening card missing audio_text")
        if kind == "gap_fill" and "____" not in str(card.get("sentence") or ""):
            errors.append(f"{where}: gap_fill missing ____ placeholder")
        if kind == "dialog_cloze":
            lines = card.get("lines")
            if not isinstance(lines, list) or sum(
                bool(line.get("blank")) for line in lines if isinstance(line, dict)
            ) != 1:
                errors.append(f"{where}: dialog_cloze requires exactly one blank line")
        if not localized(card.get("explanation")):
            warnings.append(f"{where}: localized pedagogical explanation missing")
    elif kind in BUILDER_TYPES:
        tokens, answer = card.get("tokens"), card.get("answer_tokens")
        for lang in LANGUAGES if kind == "reverse_builder" else (None,):
            source = tokens.get(lang) if lang and isinstance(tokens, dict) else tokens
            target = answer.get(lang) if lang and isinstance(answer, dict) else answer
            if not isinstance(source, list) or not isinstance(target, list) or not target:
                errors.append(f"{where}: builder tokens missing for {lang or 'zh'}")
            elif any(not nonempty(t) for t in source + target):
                errors.append(f"{where}: builder tokens must be nonempty text")
            elif Counter(target) - Counter(source):
                errors.append(f"{where}: answer tokens absent from bank ({lang or 'zh'})")
        if not localized(card.get("explanation")):
            warnings.append(f"{where}: localized pedagogical explanation missing")
    elif kind == "match_pairs":
        pairs = card.get("pairs")
        if not isinstance(pairs, list) or len(pairs) < 2:
            errors.append(f"{where}: at least two pairs required")
        else:
            for i, pair in enumerate(pairs, 1):
                if not isinstance(pair, list) or len(pair) != 2 or not nonempty(pair[0]) or not localized(pair[1]):
                    errors.append(f"{where}: pair {i} needs zh and localized meaning")
            left = [p[0] for p in pairs if isinstance(p, list) and len(p) == 2]
            if len(left) != len(set(left)):
                warnings.append(f"{where}: repeated match-pair hanzi")
    return errors, warnings


def validate_lesson(lesson: object, *, number: int) -> tuple[list[str], list[str]]:
    where = f"nhsk1/lesson_{number:02d}"
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(lesson, dict):
        return [f"{where}: lesson must be an object"], []
    if lesson.get("schema_version") != 2 or lesson.get("level") != "nhsk1" or lesson.get("lesson_id") != number:
        errors.append(f"{where}: schema_version/level/lesson_id mismatch")
    if not localized(lesson.get("subtitle")) or not nonempty(lesson.get("title")):
        errors.append(f"{where}: title/subtitle missing")
    if type(lesson.get("source_lesson")) is not int or not (1 <= lesson["source_lesson"] <= 15):
        errors.append(f"{where}: source_lesson must be 1..15")
    part, total = lesson.get("part_no"), lesson.get("part_count")
    if type(part) is not int or type(total) is not int or not (1 <= part <= total):
        errors.append(f"{where}: part_no/part_count invalid")
    if not isinstance(lesson.get("checkpoint"), bool):
        errors.append(f"{where}: checkpoint must be boolean")
    words = lesson.get("active_words")
    if not isinstance(words, list):
        errors.append(f"{where}: active_words must be a list")
    else:
        for index, word in enumerate(words, 1):
            if not isinstance(word, dict) or not nonempty(word.get("zh")) or not nonempty(word.get("pinyin")) or not localized(word.get("meaning")):
                errors.append(f"{where}: active_words[{index}] lacks zh/pinyin/translation")
    sections = lesson.get("sections")
    if not isinstance(sections, list) or not sections:
        errors.append(f"{where}: sections must be a nonempty list")
    else:
        seen: set[int] = set()
        for pos, section in enumerate(sections, 1):
            sw = f"{where}/section_{pos}"
            if not isinstance(section, dict):
                errors.append(f"{sw}: invalid section")
                continue
            no = section.get("section_no")
            if type(no) is not int or no <= 0 or no in seen:
                errors.append(f"{sw}: section number must be unique positive int")
            else:
                seen.add(no)
            if not nonempty(section.get("section_purpose")) or not localized(section.get("section_title")):
                errors.append(f"{sw}: section purpose/title missing")
            cards = section.get("cards")
            if section.get("section_purpose") == "learning_exit_check":
                if number != 4 or not lesson.get("checkpoint"):
                    errors.append(f"{sw}: independent exit check only allowed on first source checkpoint")
                if not isinstance(cards, list) or len(cards) != 3:
                    errors.append(f"{sw}: independent exit check must have three cards")
                else:
                    objectives = [str(c.get("learning_objective") or "") for c in cards if isinstance(c, dict)]
                    if len(objectives) != 3 or not all(objectives) or len(set(objectives)) != 3:
                        errors.append(f"{sw}: all exit objectives must be unique")
                    if any(not isinstance(c, dict) or c.get("learning_check") != "n1_exit_check_v1" for c in cards):
                        errors.append(f"{sw}: invalid exit check content edition")
            if not isinstance(cards, list) or not cards:
                errors.append(f"{sw}: no cards")
                continue
            for index, card in enumerate(cards, 1):
                e, w = validate_card(card, f"{sw}/card_{index}")
                errors.extend(e)
                warnings.extend(w)
    return errors, warnings


def validate_runtime(data_root: Path) -> tuple[list[str], list[str], dict[str, int]]:
    errors: list[str] = []
    warnings: list[str] = []
    folder = data_root / "nhsk1"
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    mapping = json.loads((data_root / "nhsk1.json").read_text(encoding="utf-8"))
    expected = manifest.get("lesson_count")
    if type(expected) is not int or expected <= 0:
        return ["nhsk1/manifest.json: invalid lesson_count"], [], {}
    if manifest.get("level") != "nhsk1" or manifest.get("source_lesson_count") != 15:
        errors.append("nhsk1/manifest.json: level/source count invalid")
    units = mapping.get("units")
    if mapping.get("level") != "nhsk1" or not isinstance(units, list) or len(units) != 15:
        errors.append("nhsk1.json: expected 15 source-lesson units")
        units = []
    by_order: dict[int, dict] = {}
    counts: Counter[int] = Counter()
    for no in range(1, expected + 1):
        path = folder / f"lesson_{no:02d}.json"
        try:
            lesson = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"{path.name}: not loadable ({exc})")
            continue
        e, w = validate_lesson(lesson, number=no)
        errors.extend(e)
        warnings.extend(w)
        by_order[no] = lesson
        source = lesson.get("source_lesson")
        if type(source) is int:
            counts[source] += 1
    actual_files = list(folder.glob("lesson_*.json"))
    if len(actual_files) != expected:
        errors.append(f"nhsk1: manifest {expected} parts, found {len(actual_files)} files")
    flat_orders: list[int] = []
    for src, unit in enumerate(units, 1):
        if unit.get("no") != src or not isinstance(unit.get("lessons"), list):
            errors.append(f"nhsk1.json: invalid unit {src}")
            continue
        parts = unit["lessons"]
        if len(parts) != counts[src]:
            errors.append(f"nhsk1 unit {src}: map/runtime part count mismatch")
        for part_index, item in enumerate(parts, 1):
            order = item.get("n")
            if type(order) is not int:
                errors.append(f"nhsk1 unit {src}: non-numeric map lesson")
                continue
            flat_orders.append(order)
            data = by_order.get(order)
            if data and (data.get("source_lesson") != src or data.get("part_no") != part_index or data.get("part_count") != len(parts)):
                errors.append(f"nhsk1 lesson {order}: map/source part metadata disagreement")
            if data and (data.get("checkpoint") != (part_index == len(parts)) or bool(item.get("checkpoint")) != (part_index == len(parts))):
                errors.append(f"nhsk1 lesson {order}: checkpoint not final part")
    if flat_orders != list(range(1, expected + 1)):
        errors.append("nhsk1.json: map does not list every part in canonical order")
    return errors, warnings, {"parts": len(by_order), "units": len(units), "warnings": len(warnings)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DATA_ROOT)
    args = parser.parse_args()
    try:
        errors, warnings, stats = validate_runtime(args.data_root)
    except (OSError, ValueError, TypeError) as exc:
        print(f"FAIL: cannot read nhsk1 runtime: {exc}")
        return 1
    print("HSK 3.0 N1 learning contract:", json.dumps(stats, ensure_ascii=False))
    for message in errors[:40]:
        print("ERROR:", message)
    for message in warnings[:15]:
        print("QUALITY WARNING:", message)
    if len(errors) > 40:
        print(f"... {len(errors) - 40} further errors")
    if len(warnings) > 15:
        print(f"... {len(warnings) - 15} further quality warnings")
    if errors:
        print(f"FAIL: {len(errors)} structural contract violations")
        return 1
    print("PASS: structure compatible; quality warnings require editorial review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Apply authored, guarded pedagogical feedback to HSK 3.0 Course V3 data.

Runtime JSON is generated from textbook seeds. Keep editorial feedback in a
separate, reproducible layer so rerunning the generator cannot erase it.

Only explanations are modified: never mutate prompts, answers, card order,
section IDs or the position-based material_ref contract.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PILOT_PATH = HERE / "learning_overlays" / "nhsk1_lesson_01.json"
LANGUAGES = ("uz", "ru", "tj")


def _answer(card: dict) -> str:
    if card.get("type") == "reverse_builder":
        return str(card.get("zh") or "")
    if card.get("type") in {"sentence_builder", "word_order"}:
        return " ".join(card.get("answer_tokens") or [])
    options = card.get("options")
    index = card.get("correct_index")
    if isinstance(options, list) and type(index) is int and 0 <= index < len(options):
        value = options[index]
        return str(value.get("uz") or "") if isinstance(value, dict) else str(value)
    raise ValueError("overlay cannot establish a stable answer")


def apply_nhsk1_pilot_feedback(payload: dict, path: Path = PILOT_PATH) -> dict:
    """Return a copy with a validated set of localized explanations applied.

    Strict match protects against silently attaching an old hint to a new
    exercise after generated card order changes. No other content changes.
    """
    if payload.get("level") != "nhsk1" or payload.get("source_lesson") != 1:
        return payload
    overlay = json.loads(path.read_text(encoding="utf-8"))
    if (
        overlay.get("schema_version") != 1
        or overlay.get("level") != "nhsk1"
        or overlay.get("source_lesson") != 1
        or overlay.get("feedback_version") != "n1_context_v1"
    ):
        raise ValueError("N1 learning overlay metadata is invalid")
    part = payload.get("part_no")
    sections = {
        s.get("section_no"): s.get("cards")
        for s in payload.get("sections", [])
        if isinstance(s, dict)
    }
    result = deepcopy(payload)
    output_sections = {
        s.get("section_no"): s.get("cards")
        for s in result.get("sections", [])
        if isinstance(s, dict)
    }
    seen: set[tuple[int, int, int]] = set()
    applied = 0
    for item in overlay.get("cards", []):
        key = (item["part_no"], item["section_no"], item["card_no"])
        if key in seen:
            raise ValueError(f"duplicate N1 feedback overlay reference: {key}")
        seen.add(key)
        if item["part_no"] != part:
            continue
        sn, cn = item["section_no"], item["card_no"]
        cards = sections.get(sn)
        if not isinstance(cards, list) or type(cn) is not int or not (1 <= cn <= len(cards)):
            raise ValueError(f"N1 feedback overlay card position changed: {key}")
        card = cards[cn - 1]
        if card.get("type") != item["type"] or _answer(card) != item["expected_answer"]:
            raise ValueError(
                f"N1 feedback overlay target changed: {key} "
                f"expected {item['type']}/{item['expected_answer']!r}; "
                f"found {card.get('type')}/{_answer(card)!r}"
            )
        translations = item.get("explanation")
        if not isinstance(translations, dict) or any(
            not isinstance(translations.get(lang), str) or not translations[lang].strip()
            for lang in LANGUAGES
        ):
            raise ValueError(f"N1 feedback overlay translation missing: {key}")
        updated = output_sections[sn][cn - 1]
        updated["explanation"] = dict(translations)
        updated["learning_feedback"] = overlay["feedback_version"]
        applied += 1
    if part in (1, 2, 3, 4) and not applied:
        raise ValueError(f"N1 feedback missing for pilot part {part}")
    return result


def validate_pilot_overlay(path: Path = PILOT_PATH) -> int:
    """Static checks used by CI; no runtime files are changed."""
    data = json.loads(path.read_text(encoding="utf-8"))
    cards = data["cards"]
    if not cards or len({(r["part_no"], r["section_no"], r["card_no"]) for r in cards}) != len(cards):
        raise ValueError("duplicate or empty pilot feedback entries")
    if set(r["part_no"] for r in cards) != {1, 2, 3, 4}:
        raise ValueError("pilot feedback must cover all four parts")
    if any(not isinstance(r.get("expected_answer"), str) or not r["expected_answer"] for r in cards):
        raise ValueError("pilot answer guard missing")
    return len(cards)


if __name__ == "__main__":
    print(f"Validated {validate_pilot_overlay()} N1 pedagogical feedback entries")

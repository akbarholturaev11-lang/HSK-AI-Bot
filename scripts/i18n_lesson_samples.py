#!/usr/bin/env python3
"""Freeze three-language learner-text samples from the seven course tracks.

The byte-level baseline already covers all 746 lessons. This complementary
guard checks representative *source JSON selections* for the three existing
locales as well as stable lesson IDs, Chinese and pinyin. It does not run the
Mini App/Android/Desktop renderer, check entitlement, or approve a translation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "localization/baselines/lesson_locale_samples.json"
TRACKS = ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")
LANGUAGES = ("uz", "ru", "tj")


def _require_localized(value: object, *, at: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError(f"{at}: expected locale map")
    result = {}
    for language in LANGUAGES:
        text = value.get(language)
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{at}: missing {language} learner copy")
        result[language] = text
    return result


def source_sample(path: Path, expected_level: str) -> dict:
    """Use *exact* authored values; never fake fallback translations."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{expected_level}: lesson is not an object")
    if data.get("level") != expected_level or data.get("lesson_id") != 1:
        raise ValueError(f"{expected_level}: lesson identity changed")
    for attr in ("source_lesson", "part_no", "part_count"):
        if not isinstance(data.get(attr), int):
            raise ValueError(f"{expected_level}: invalid {attr}")

    words = data.get("active_words")
    sections = data.get("sections")
    if not isinstance(words, list) or not words or not isinstance(words[0], dict):
        raise ValueError(f"{expected_level}: no active word")
    if not isinstance(sections, list) or not sections or not isinstance(sections[0], dict):
        raise ValueError(f"{expected_level}: no sections")
    cards = sections[0].get("cards")
    if not isinstance(cards, list) or not cards or not isinstance(cards[0], dict):
        raise ValueError(f"{expected_level}: no first card")
    word = words[0]
    subtitle = _require_localized(data.get("subtitle"), at="subtitle")
    meanings = _require_localized(word.get("meaning"), at="active_words[0].meaning")
    for key, value in (
        ("title_zh", data.get("title")),
        ("first_word_zh", word.get("zh")),
        ("first_word_pinyin", word.get("pinyin")),
        ("first_card_type", cards[0].get("type")),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{expected_level}: missing {key}")

    return {
        "level": expected_level,
        "lesson_id": data["lesson_id"],
        "source_lesson": data["source_lesson"],
        "part_no": data["part_no"],
        "part_count": data["part_count"],
        "title_zh": data["title"],
        "first_word_zh": word["zh"],
        "first_word_pinyin": word["pinyin"],
        "section_count": len(sections),
        "first_section_card_count": len(cards),
        "first_card_type": cards[0]["type"],
        "locales": {
            language: {
                "subtitle": subtitle[language],
                "first_word_meaning": meanings[language],
            }
            for language in LANGUAGES
        },
    }


def check_samples(root: Path, baseline: dict) -> dict:
    """Compare selected learner texts without mutating source or leaking copy."""
    if baseline.get("schema_version") != 1:
        raise ValueError("unsupported locale-sample baseline")
    previous = baseline.get("lessons")
    if not isinstance(previous, list) or len(previous) != len(TRACKS):
        raise ValueError("locale-sample baseline requires all 7 track samples")
    indexed = {}
    for row in previous:
        if not isinstance(row, dict) or row.get("level") not in TRACKS:
            raise ValueError("unknown locale-sample track")
        if row["level"] in indexed:
            raise ValueError("duplicate locale-sample track")
        indexed[row["level"]] = row
    if set(indexed) != set(TRACKS):
        raise ValueError("locale-sample tracks incomplete")

    issues = []
    for track in TRACKS:
        path = root / "app/static/course_v3_data" / track / "lesson_01.json"
        try:
            actual = source_sample(path, track)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            issues.append({"track": track, "field": "file_or_shape", "reason": str(error)[:160]})
            continue
        expected = indexed[track]
        for key in ("lesson_id", "source_lesson", "part_no", "part_count",
                    "title_zh", "first_word_zh", "first_word_pinyin",
                    "section_count", "first_section_card_count", "first_card_type"):
            if actual[key] != expected.get(key):
                issues.append({"track": track, "field": key})
        for language in LANGUAGES:
            old = expected.get("locales", {}).get(language, {})
            for key in ("subtitle", "first_word_meaning"):
                if actual["locales"][language][key] != old.get(key):
                    issues.append({"track": track, "locale": language, "field": key})
    return {
        "schema_version": 1, "tracks_checked": len(TRACKS),
        "languages_checked": list(LANGUAGES),
        "fields_per_locale": 2,
        "issues_count": len(issues),
        "status": "source_samples_match" if not issues else "review_required",
        "issues": issues,
        "scope": "source JSON learner-text selections, not runtime-rendered UI",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        report = check_samples(args.root, baseline)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        print("Invalid locale-sample baseline:", error, file=sys.stderr)
        return 1
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print("Lesson JSON source samples:", report["tracks_checked"], "tracks x",
          len(report["languages_checked"]), "languages; issues:", report["issues_count"])
    return 1 if report["issues_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""P3 reviewer-only content reuse audit across all seven original HSK tracks.

Conservatively group originally blank UZ/RU/TJ grammar example fields by
exact source Chinese + pinyin + grammar no/title/title_zh/rule. Such groups
MAY reuse one human-reviewed translation; no Chinese, translated strings,
answers, hash fingerprints, or paywall data appear in the report.

No source writes, no public locale packs and no client/backend code changes.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any

if __package__:
    from scripts.i18n_legacy_lesson_content_risk_audit import (
        ROOT, TRACKS, _lesson_files,
    )
else:
    from i18n_legacy_lesson_content_risk_audit import (
        ROOT, TRACKS, _lesson_files,
    )

LANGUAGES = ("uz", "ru", "tj")


def _source_context(group: dict[str, Any], ex: dict[str, Any]) -> str:
    """Canonical in-memory comparison key; NEVER serialize in reports."""
    if (
        type(group.get("no")) not in (int, str)
        or type(ex.get("zh")) is not str
        or not ex["zh"].strip()
        or type(ex.get("pinyin", "")) is not str
    ):
        raise ValueError("invalid original grammar source context")
    return json.dumps({
        "no": group["no"],
        "title": group.get("title"),
        "title_zh": group.get("title_zh"),
        "rule": group.get("rule"),
        "zh": ex["zh"],
        "pinyin": ex.get("pinyin", ""),
    }, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _blank_original_grammar_maps(
    lesson: dict[str, Any], track: str, number: int,
) -> list[tuple[str, str]]:
    """Return only private context keys and public-safe display pointers."""
    if (
        type(lesson) is not dict
        or lesson.get("schema_version") != 2
        or lesson.get("level") != track
        or type(lesson.get("lesson_id")) is not int
        or lesson["lesson_id"] != number
    ):
        raise ValueError("source identity mismatch")
    groups = lesson.get("grammar", [])
    if type(groups) is not list:
        raise ValueError("malformed grammar groups")
    result = []
    for gi, group in enumerate(groups):
        if type(group) is not dict:
            raise ValueError("malformed grammar source")
        examples = group.get("examples", [])
        if type(examples) is not list:
            raise ValueError("malformed grammar examples")
        for ei, ex in enumerate(examples):
            if type(ex) is not dict:
                raise ValueError("malformed grammar example")
            values = ex.get("translation")
            if type(values) is not dict:
                continue
            if set(values) != set(LANGUAGES):
                raise ValueError("unreviewed source locale map")
            blank = [type(values[x]) is str and not values[x].strip()
                     for x in LANGUAGES]
            if all(blank):
                result.append((
                    _source_context(group, ex),
                    f"/grammar/{gi}/examples/{ei}/translation",
                ))
            elif any(blank):
                raise ValueError("partial source locale map requires separate review")
    return result


def audit_repeated_grammar_translations(root: Path = ROOT) -> dict[str, Any]:
    """Safe summary of blank fields eligible for conservative deduplication."""
    source_counts = {}
    by_track = Counter()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for track in TRACKS:
        files = _lesson_files(root, track)
        source_counts[track] = len(files)
        for num, file in enumerate(files, 1):
            try:
                lesson = json.loads(file.read_text(encoding="utf-8"))
            except (UnicodeError, json.JSONDecodeError):
                raise ValueError("invalid lesson source JSON") from None
            for key, pointer in _blank_original_grammar_maps(lesson, track, num):
                by_track[track] += 1
                grouped.setdefault(key, []).append({
                    "track": track,
                    "lesson_number": num,
                    "pointer": pointer,
                })

    occurrences = sum(len(x) for x in grouped.values())
    unique = len(grouped)
    repeats = [
        {
            "occurrence_count": len(members),
            "locations": members,
        }
        for members in grouped.values() if len(members) > 1
    ]
    repeats.sort(key=lambda x: (
        x["locations"][0]["track"],
        x["locations"][0]["lesson_number"],
        x["locations"][0]["pointer"],
    ))
    return {
        "schema_version": 1,
        "kind": "p3_reviewed_grammar_translation_reuse_inventory",
        "status": "SOURCE_REUSE_CANDIDATES_HUMAN_REVIEW_REQUIRED",
        "source_lesson_counts": source_counts,
        "total_scanned_lessons": sum(source_counts.values()),
        "blank_source_grammar_maps": occurrences,
        "locale_values_before_reuse": occurrences * len(LANGUAGES),
        "distinct_exact_grammar_contexts": unique,
        "locale_values_for_unique_contexts": unique * len(LANGUAGES),
        "duplicate_occurrences_after_first": occurrences - unique,
        "duplicate_context_groups": len(repeats),
        "blank_maps_by_track": dict(sorted(by_track.items())),
        "repeated_source_locations": repeats,
        "ready_to_ship": False,
        "limitations": [
            "Identical Chinese, pinyin, grammar identity/title/rule; NOT automatic language approval.",
            "Source contexts are compared in-memory but not emitted as Chinese or hashes.",
            "Only original grammar display fields, not answer options or Pro lesson packs.",
            "Some original blank display maps may exist outside grammar examples.",
            "Human editors must approve translations and revalidate SHA-bound target lessons.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        data = audit_repeated_grammar_translations(ROOT)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(data, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, KeyError, TypeError):
        print("P3 grammar reuse audit failed (source contents withheld)",
              file=sys.stderr)
        return 1
    print(
        "P3 grammar reuse:",
        data["blank_source_grammar_maps"], "blank source maps,",
        data["distinct_exact_grammar_contexts"], "distinct contexts,",
        data["duplicate_occurrences_after_first"], "repeat occurrences",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

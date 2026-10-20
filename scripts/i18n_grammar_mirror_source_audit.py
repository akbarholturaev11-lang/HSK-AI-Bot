#!/usr/bin/env python3
"""P3 read-only seven-track grammar/card mirror audit; report counts, never text.

A lesson's top-level grammar entries may be repeated in "_grammar" cards.
Translation updates must not modify a copy without checking the original.
The report contains only source-relative filenames, issue codes and counts.
No Chinese, pinyin, locale values, quiz answers, graded tokens or Pro content.
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
    from i18n_legacy_lesson_content_risk_audit import ROOT, TRACKS, _lesson_files


def audit_lesson_mirrors(data: Any, track: str, lesson_number: int) -> dict[str, Any]:
    """Count source-aligned mirrors; any ambiguity becomes a named blocker."""
    counts = Counter()
    issues = Counter()

    if (
        type(data) is not dict
        or data.get("schema_version") != 2
        or data.get("level") != track
        or type(data.get("lesson_id")) is not int
        or data["lesson_id"] != lesson_number
    ):
        raise ValueError("invalid source identity")
    grammar = data.get("grammar", [])
    sections = data.get("sections", [])
    if type(grammar) is not list or type(sections) is not list:
        issues["malformed_grammar_or_section"] += 1
        return {"counts": dict(counts), "issues": dict(issues)}

    source_groups = {}
    for g in grammar:
        counts["original_grammar_groups"] += 1
        if type(g) is not dict:
            issues["malformed_original_group"] += 1
            continue
        no = g.get("no")
        if type(no) not in (int, str) or no in source_groups:
            issues["duplicate_or_unidentified_original_group"] += 1
            continue
        source_groups[no] = g
        examples = g.get("examples")
        if type(examples) is not list:
            issues["malformed_original_examples"] += 1
            continue
        counts["original_examples"] += len(examples)
        for ex in examples:
            if type(ex) is not dict:
                issues["malformed_original_example"] += 1
                continue
            values = ex.get("translation")
            if type(values) is dict and set(values) == {"uz", "ru", "tj"}:
                if all(type(values[k]) is str and not values[k].strip()
                       for k in ("uz", "ru", "tj")):
                    counts["original_all_empty_display_maps"] += 1

    mirror_groups_seen = Counter()
    for section in sections:
        if type(section) is not dict or type(section.get("cards", [])) is not list:
            issues["malformed_section_cards"] += 1
            continue
        for card in section.get("cards", []):
            if type(card) is not dict or card.get("type") != "_grammar":
                continue
            counts["mirror_grammar_cards"] += 1
            copy = card.get("g")
            if type(copy) is not dict:
                issues["malformed_mirror_group"] += 1
                continue
            no = copy.get("no")
            if no not in source_groups:
                issues["orphaned_mirror_group"] += 1
                continue
            mirror_groups_seen[no] += 1
            original = source_groups[no]
            counts["matched_mirror_groups"] += 1
            for field in ("title", "rule", "title_zh"):
                if field in original and copy.get(field) != original[field]:
                    issues["mirror_" + field + "_drift"] += 1
            first, second = original.get("examples"), copy.get("examples")
            if type(first) is not list or type(second) is not list:
                issues["malformed_mirror_examples"] += 1
                continue
            if len(first) != len(second):
                issues["mirror_example_count_drift"] += 1
            for a, b in zip(first, second):
                counts["matched_mirror_example_positions"] += 1
                if type(a) is not dict or type(b) is not dict:
                    issues["malformed_mirror_example"] += 1
                    continue
                if a.get("zh") != b.get("zh"):
                    issues["mirror_chinese_mismatch"] += 1
                if a.get("pinyin") != b.get("pinyin"):
                    issues["mirror_pinyin_mismatch"] += 1
                if a.get("translation") != b.get("translation"):
                    issues["mirror_locale_map_mismatch"] += 1
                else:
                    values = a.get("translation")
                    if type(values) is dict and set(values) == {"uz", "ru", "tj"}:
                        if all(type(values[k]) is str and not values[k].strip()
                               for k in ("uz", "ru", "tj")):
                            counts["matched_all_empty_mirror_maps"] += 1

    for no in source_groups:
        if mirror_groups_seen[no] == 0:
            counts["source_groups_without_mirror_card"] += 1
        elif mirror_groups_seen[no] > 1:
            counts["source_groups_with_multiple_mirror_cards"] += 1
            # Separate matched mirrors are not necessarily errors, but they
            # must be reviewed before content integration.
            issues["multiple_mirrors_need_review"] += 1

    return {
        "counts": dict(sorted(counts.items())),
        "issues": dict(sorted(issues.items())),
    }


def audit_all_mirrors(root: Path = ROOT) -> dict[str, Any]:
    by_track = {}
    source_counts = {}
    totals = Counter()
    issues = Counter()
    blocked = []

    for track in TRACKS:
        files = _lesson_files(root, track)
        source_counts[track] = len(files)
        track_counts = Counter()
        track_issues = Counter()
        for ordinal, path in enumerate(files, 1):
            try:
                lesson = json.loads(path.read_text(encoding="utf-8"))
            except (UnicodeError, json.JSONDecodeError):
                raise ValueError("unparseable source JSON") from None
            result = audit_lesson_mirrors(lesson, track, ordinal)
            counts = result["counts"]
            problems = result["issues"]
            track_counts.update(counts)
            track_issues.update(problems)
            totals.update(counts)
            issues.update(problems)
            totals["scanned_source_lessons"] += 1
            track_counts["scanned_source_lessons"] += 1
            if problems:
                totals["lessons_with_mirror_issues"] += 1
                track_counts["lessons_with_mirror_issues"] += 1
                blocked.append({
                    "track": track,
                    "lesson_number": ordinal,
                    "source_file": path.relative_to(root).as_posix(),
                    "issue_counts": problems,
                })
        by_track[track] = {
            "counts": dict(sorted(track_counts.items())),
            "issue_counts": dict(sorted(track_issues.items())),
        }

    return {
        "schema_version": 1,
        "kind": "p3_source_grammar_mirror_inventory",
        "status": ("HUMAN_REVIEW_MIRROR_GAPS" if blocked
                   else "NO_MIRROR_DIVERGENCE_DETECTED"),
        "source_lesson_counts": source_counts,
        "totals": dict(sorted(totals.items())),
        "issue_counts": dict(sorted(issues.items())),
        "by_track": by_track,
        "review_locations": blocked,
        "ready_to_ship": False,
        "limitations": [
            "Structural source comparison, not proof of translation correctness.",
            "Counts only; all source Chinese, answers and Pro fields are excluded.",
            "Source JSON may contain graded/gated material: never publish previews.",
            "Client rendering, subscription, auth and device QA remain separate.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit_all_mirrors(ROOT)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
    except (ValueError, TypeError, OSError, KeyError):
        print("P3 grammar mirror source audit failed (content withheld)",
              file=sys.stderr)
        return 1
    print(
        "P3 grammar mirror inventory:",
        report["totals"]["scanned_source_lessons"], "lessons,",
        report["totals"].get("matched_all_empty_mirror_maps", 0),
        "duplicated blank display maps,",
        report["totals"].get("lessons_with_mirror_issues", 0),
        "lessons need mirror review",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

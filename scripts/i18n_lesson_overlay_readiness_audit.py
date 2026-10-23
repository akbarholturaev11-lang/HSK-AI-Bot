#!/usr/bin/env python3
"""Read-only P3 lesson overlay readiness audit. Never serialize lesson text.

Scans only the first/last lesson of each existing HSK 2.0/3.0 track.
The report contains structural counts and issue types, not Chinese, pinyin,
translations, option values, answers, account data, or paid lesson packs.
No runtime access, HTTP requests, or lesson JSON writes occur.
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
        ROOT, TRACKS, _lesson_files, _sensitive_field_counts,
    )
    from scripts.i18n_lesson_display_overlay_contract import (
        DISPLAY_PATHS, LOCALES, _allowed, apply_display_overlay,
        build_display_overlay,
    )
else:
    from i18n_legacy_lesson_content_risk_audit import (
        ROOT, TRACKS, _lesson_files, _sensitive_field_counts,
    )
    from i18n_lesson_display_overlay_contract import (
        DISPLAY_PATHS, LOCALES, _allowed, apply_display_overlay,
        build_display_overlay,
    )


def _display_field_counts(source: dict[str, Any]) -> dict[str, int]:
    result = Counter()

    def walk(node: Any, path: tuple[str, ...]) -> None:
        if isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, (*path, str(i)))
        elif isinstance(node, dict):
            if _allowed(path):
                if set(node) != set(LOCALES) or any(
                    not isinstance(node.get(locale), str) for locale in LOCALES
                ):
                    result["invalid_locale_maps"] += 1
                elif all(not node[locale].strip() for locale in LOCALES):
                    result["all_empty_locale_maps"] += 1
                elif any(not node[locale].strip() for locale in LOCALES):
                    result["partially_empty_locale_maps"] += 1
                else:
                    result["complete_display_maps"] += 1
                return
            for key, value in node.items():
                walk(value, (*path, str(key)))

    walk(source, ())
    return {
        key: result[key] for key in (
            "complete_display_maps", "all_empty_locale_maps",
            "partially_empty_locale_maps", "invalid_locale_maps",
        )
    }


def _reverse_builder_count(source: dict[str, Any]) -> int:
    return sum(
        1
        for section in source.get("sections", [])
        for card in section.get("cards", [])
        if isinstance(card, dict) and card.get("type") == "reverse_builder"
    )


def audit_sampled_lessons(root: Path = ROOT) -> dict[str, Any]:
    """Inspect 14 source samples, recording failures rather than emitting packs.

    Fail structural issues closed; no blanket claims for 746 full lessons.
    A blocked sample is deliberately kept in the report for human review.
    """
    samples: list[dict[str, Any]] = []
    lesson_counts: dict[str, int] = {}
    totals = Counter()
    for track in TRACKS:
        lesson_files = _lesson_files(root, track)
        lesson_counts[track] = len(lesson_files)
        for index in sorted({0, len(lesson_files) - 1}):
            path = lesson_files[index]
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("lesson_root_not_object: " + track)
            if (data.get("schema_version") != 2 or data.get("level") != track
                    or type(data.get("lesson_id")) is not int
                    or data["lesson_id"] != index + 1):
                raise ValueError("source_lesson_identity_changed: " + track)
            fields = _display_field_counts(data)
            assessment = _sensitive_field_counts(data)
            sample = {
                "track": track,
                "lesson_number": index + 1,
                "source_file": path.relative_to(root).as_posix(),
                **fields,
                "assessment_key_occurrences": sum(assessment.values()),
                "reverse_builder_cards_excluded": _reverse_builder_count(data),
                "validated_locale_overlays": 0,
                "status": "NOT_EVALUATED",
            }
            issues = (fields["all_empty_locale_maps"]
                      + fields["partially_empty_locale_maps"]
                      + fields["invalid_locale_maps"])
            if issues:
                sample["status"] = "BLOCKED_INCOMPLETE_SOURCE_LOCALES"
            else:
                for locale in LOCALES:
                    overlay = build_display_overlay(data, locale)
                    if len(overlay["texts"]) != fields["complete_display_maps"]:
                        raise ValueError("overlay_display_map_count_changed: " + track)
                    if apply_display_overlay(data, overlay) != data:
                        raise ValueError("overlay_source_identity_changed: " + track)
                    sample["validated_locale_overlays"] += 1
                sample["status"] = "SOURCE_BOUND_CONTRACT_OK"
            totals.update({
                "sampled_source_lessons": 1,
                "complete_display_maps": fields["complete_display_maps"],
                "all_empty_locale_maps": fields["all_empty_locale_maps"],
                "partially_empty_locale_maps": fields["partially_empty_locale_maps"],
                "invalid_locale_maps": fields["invalid_locale_maps"],
                "validated_locale_overlays": sample["validated_locale_overlays"],
                "assessment_key_occurrences": sample["assessment_key_occurrences"],
                "reverse_builder_cards_excluded": sample["reverse_builder_cards_excluded"],
                "blocked_samples": int(issues > 0),
            })
            samples.append(sample)
    return {
        "schema_version": 1,
        "status": ("P3_SAMPLE_LOCALE_GAPS_REQUIRE_REVIEW"
                   if totals["blocked_samples"] else
                   "P3_SAMPLES_REVIEWED_RUNTIME_NOT_ENABLED"),
        "tracks": list(TRACKS),
        "lesson_source_counts": lesson_counts,
        "reviewed_display_path_templates": len(DISPLAY_PATHS),
        "totals": dict(sorted(totals.items())),
        "samples": samples,
        "limitations": [
            "Only first/last source lessons per track, NOT all lessons reviewed.",
            "Not a public pack, route, Pro eligibility, grade verification or runtime migration.",
            "Counts reflect source fields, not translated-content correctness.",
            "Keep paid/locked material private; independent route/access audit is required.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit_sampled_lessons(ROOT)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print("P3 sampled-overlay audit failed: " + str(exc), file=sys.stderr)
        return 1
    print(
        "P3 sample overlay audit:", report["totals"]["sampled_source_lessons"],
        "sources,", report["totals"]["blocked_samples"],
        "blocked samples,", report["totals"]["validated_locale_overlays"],
        "validated locale overlays (read-only)",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

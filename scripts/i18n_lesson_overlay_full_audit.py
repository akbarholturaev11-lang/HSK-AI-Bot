#!/usr/bin/env python3
"""Read-only P3 structure check for ALL seven-track source lessons.

Produces a count-only and safe-source-path report. It does NOT export any
locale strings, lesson answer values, Chinese source content, public bundles,
paid lessons, user information, or grading solutions. No runtime integration.
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
    from scripts.i18n_lesson_overlay_readiness_audit import (
        _display_field_counts, _reverse_builder_count,
    )
    from scripts.i18n_lesson_display_overlay_contract import (
        LOCALES, apply_display_overlay, build_display_overlay,
    )
else:
    from i18n_legacy_lesson_content_risk_audit import (
        ROOT, TRACKS, _lesson_files, _sensitive_field_counts,
    )
    from i18n_lesson_overlay_readiness_audit import (
        _display_field_counts, _reverse_builder_count,
    )
    from i18n_lesson_display_overlay_contract import (
        LOCALES, apply_display_overlay, build_display_overlay,
    )

FIELD_KEYS = (
    "complete_display_maps",
    "all_empty_locale_maps",
    "partially_empty_locale_maps",
    "invalid_locale_maps",
)
ISSUE_KEYS = (
    "invalid_json_or_root",
    "invalid_source_identity",
    "incomplete_source_locales",
    "overlay_contract_rejected",
)


def _evaluate(data: Any, track: str, lesson_number: int) -> tuple[dict, list[str]]:
    """Return structural statistics and fixed issue codes, never source values."""
    counts = {key: 0 for key in FIELD_KEYS}
    counts.update({
        "assessment_key_occurrences": 0,
        "reverse_builder_cards_excluded": 0,
        "validated_locale_overlays": 0,
    })
    issues: list[str] = []
    if not isinstance(data, dict):
        return counts, ["invalid_json_or_root"]

    identity_ok = (
        data.get("schema_version") == 2
        and data.get("level") == track
        and type(data.get("lesson_id")) is int
        and data["lesson_id"] == lesson_number
        and type(data.get("part_no")) is int
        and data["part_no"] >= 1
    )
    if not identity_ok:
        issues.append("invalid_source_identity")

    counts.update(_display_field_counts(data))
    counts["assessment_key_occurrences"] = sum(
        _sensitive_field_counts(data).values()
    )
    try:
        counts["reverse_builder_cards_excluded"] = _reverse_builder_count(data)
    except (TypeError, AttributeError, KeyError):
        # A structurally malformed source is never treated as overlay-ready.
        if "invalid_source_identity" not in issues:
            issues.append("invalid_source_identity")

    if any(counts[k] for k in FIELD_KEYS if k != "complete_display_maps") or not counts["complete_display_maps"]:
        issues.append("incomplete_source_locales")
    if not issues:
        try:
            for locale in LOCALES:
                overlay = build_display_overlay(data, locale)
                if len(overlay["texts"]) != counts["complete_display_maps"]:
                    raise ValueError("display count mismatch")
                if apply_display_overlay(data, overlay) != data:
                    raise ValueError("source identity mismatch")
                counts["validated_locale_overlays"] += 1
        except (ValueError, TypeError, KeyError, IndexError):
            counts["validated_locale_overlays"] = 0
            issues.append("overlay_contract_rejected")
    return counts, issues


def audit_all_lessons(root: Path = ROOT) -> dict[str, Any]:
    """Review every numbered lesson, report blockers instead of dropping files."""
    totals = Counter()
    per_track: dict[str, dict[str, int]] = {}
    blocked: list[dict[str, Any]] = []
    reasons = Counter()
    source_counts = {}

    for track in TRACKS:
        paths = _lesson_files(root, track)
        source_counts[track] = len(paths)
        track_totals = Counter()
        for ordinal, file in enumerate(paths, 1):
            try:
                source = json.loads(file.read_text(encoding="utf-8"))
            except (UnicodeError, json.JSONDecodeError):
                source = None
            counts, issues = _evaluate(source, track, ordinal)
            common = {
                "source_lessons": 1,
                **counts,
                "blocked_lessons": int(bool(issues)),
                "ready_lessons": int(not issues),
            }
            totals.update(common)
            track_totals.update(common)
            for issue in issues:
                reasons[issue] += 1
            if issues:
                blocked.append({
                    "track": track,
                    "lesson_number": ordinal,
                    "source_file": file.relative_to(root).as_posix(),
                    "issues": issues,
                    **{key: counts[key] for key in FIELD_KEYS},
                })
        per_track[track] = dict(sorted(track_totals.items()))

    return {
        "schema_version": 1,
        "status": ("P3_FULL_SOURCE_GAPS_REQUIRE_REVIEW"
                   if totals["blocked_lessons"] else
                   "P3_FULL_SOURCE_STRUCTURE_OK_RUNTIME_NOT_ENABLED"),
        "scope": "all_existing_seven_track_source_lessons",
        "lesson_source_counts": source_counts,
        "totals": dict(sorted(totals.items())),
        "issue_counts": dict(sorted(reasons.items())),
        "per_track": per_track,
        "blocked_sources": blocked,
        "limitations": [
            "Source checks are structural only, not semantic translation review.",
            "No lesson content, answers, answer options, source-language strings or user data are emitted.",
            "Existing public route and paid-content exposure risks remain unresolved.",
            "This is NOT a public or deployable overlay pack, authenticated runtime or entitlement verification.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit_all_lessons(ROOT)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )
    except (ValueError, TypeError, OSError) as exc:
        # No lesson values should ever be included in command output.
        print("P3 full lesson audit blocked by invalid source structure", file=sys.stderr)
        return 1
    print(
        "P3 full lesson audit:", report["totals"]["source_lessons"],
        "sources,", report["totals"]["blocked_lessons"], "blocked,",
        report["totals"]["validated_locale_overlays"], "valid locale overlays",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
    from scripts.i18n_canonical_grammar_catalog import audit_canonical_grammar
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
    from i18n_canonical_grammar_catalog import audit_canonical_grammar

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
    """Review source completeness and whether canonical overlays cover its gaps."""
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

    canonical_catalog = None
    covered_sources: set[str] = set()
    try:
        drafts, canonical_counts = audit_canonical_grammar(root)
        covered_sources = set(drafts)
        canonical_catalog = {
            "status": "SOURCE_SHA_AND_CONTEXT_VALID",
            "unique_contexts": canonical_counts["contexts"],
            "independent_locale_values": canonical_counts["independent_values"],
            "source_lessons": canonical_counts["source_lessons"],
            "original_maps": canonical_counts["original_maps"],
            "mirror_maps": canonical_counts["mirror_maps"],
        }
    except (OSError, ValueError, TypeError, KeyError, IndexError, UnicodeError):
        # Source-only synthetic fixtures intentionally have no private P3 catalog.
        canonical_catalog = {"status": "NOT_VALIDATED"}

    covered_gap_count = 0
    for item in blocked:
        item["canonical_catalog_covers_source_gap"] = (
            canonical_catalog.get("status") == "SOURCE_SHA_AND_CONTEXT_VALID"
            and item["source_file"] in covered_sources
            and item["issues"] == ["incomplete_source_locales"]
        )
        covered_gap_count += int(item["canonical_catalog_covers_source_gap"])
    source_gap_count = len(blocked)
    uncovered_gap_count = source_gap_count - covered_gap_count
    if source_gap_count and uncovered_gap_count == 0:
        status = "P3_CANONICAL_DISPLAY_OVERLAYS_VALIDATED_RUNTIME_SECURITY_QA_REQUIRED"
    elif source_gap_count:
        status = "P3_FULL_SOURCE_GAPS_REQUIRE_REVIEW"
    else:
        status = "P3_FULL_SOURCE_STRUCTURE_OK_RUNTIME_NOT_ENABLED"

    return {
        "schema_version": 1,
        "status": status,
        "scope": "all_existing_seven_track_source_lessons",
        "lesson_source_counts": source_counts,
        "totals": dict(sorted(totals.items())),
        "source_gap_lessons": source_gap_count,
        "canonical_catalog_covered_gap_lessons": covered_gap_count,
        "uncovered_source_gap_lessons": uncovered_gap_count,
        "canonical_catalog": canonical_catalog,
        "issue_counts": dict(sorted(reasons.items())),
        "per_track": per_track,
        "blocked_sources": blocked,
        "limitations": [
            "Source checks are structural only, not semantic translation review.",
            "No lesson content, answers, answer options, source-language strings or user data are emitted.",
            "Existing public route and paid-content exposure risks remain unresolved.",
            "This audit does not execute the authenticated runtime or entitlement boundary; reservation/API and device QA remain separate.",
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
        "sources,", report["source_gap_lessons"], "source gaps,",
        report["canonical_catalog_covered_gap_lessons"], "catalog-covered,",
        report["uncovered_source_gap_lessons"], "uncovered,",
        report["totals"]["validated_locale_overlays"], "valid locale overlays",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

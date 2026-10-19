#!/usr/bin/env python3
"""P0 guard: classify Mini App lesson source GET intents before URL migration.

This is source review, not an auth/entitlement implementation. No JS executes
and no live requests are made. Does not serialize lesson/quiz content.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PAGE = "app/static/course-v3.html"
REGISTRY = "localization/review/miniapp_lesson_fetch_calls.json"
CALL = re.compile(r"\bloadLessonData\s*\(")
KNOWN_INTENTS = {
    "paywall_preview_prime", "audio_preload_before_continue",
    "background_nearby_prefetch", "skip_test_question_generation",
    "starter_foundation_content", "interactive_lesson_after_reservation",
}


def extract_calls(source: str) -> list[dict]:
    """Record source locations for direct calls; exclude the declaration."""
    items = []
    for match in CALL.finditer(source):
        if re.search(r"\bfunction\s+$", source[max(0, match.start() - 32):match.start()]):
            continue
        line = source.count("\n", 0, match.start()) + 1
        items.append({
            "ordinal": len(items) + 1,
            "line": line,
            "source_line": source.splitlines()[line - 1],
        })
    return items


def _function_return_line(source: str, name: str) -> str:
    match = re.search(r"\bfunction\s+" + re.escape(name)
                      + r"\s*\([^)]*\)\s*\{([^\n]*)", source)
    return match.group(1) if match else ""


def audit_source(source: str, registry: dict) -> dict:
    actual = extract_calls(source)
    expected = registry.get("read_calls")
    failures = []
    if not isinstance(expected, list):
        raise ValueError("Mini App fetch intent registry is malformed")
    if len(actual) != len(expected):
        failures.append({"issue": "unreviewed_or_missing_direct_read", "found": len(actual),
                         "registered": len(expected)})
    for index, (found, recorded) in enumerate(zip(actual, expected), start=1):
        if (not isinstance(recorded, dict) or
                recorded.get("ordinal") != index or
                recorded.get("line") != found["line"] or
                recorded.get("anchor") not in found["source_line"] or
                recorded.get("intent") not in KNOWN_INTENTS):
            failures.append({"issue": "stale_or_unclassified_read", "ordinal": index})
    if not re.search(
        r"reserveLessonStart\(l\)\.then\(function\(\)\{return loadLessonData\(lv,l\.n\)\}",
        source,
    ):
        failures.append({"issue": "interactive_lesson_reservation_order_changed"})
    if not re.search(
        r"fetch\(lessonDataUrl\(lv,n\),normalizeLevel\(lv\)===.nhsk1.",
        source,
    ):
        failures.append({"issue": "legacy_source_fetch_contract_changed"})
    if not re.search(
        r"function lessonDataKey\([^)]*\)\{return normalizeLevel\(lv\)\+",
        source,
    ):
        failures.append({"issue": "page_lesson_data_cache_key_changed"})
    if not re.search(
        r"function lessonResumeKey\([^)]*\)\{return.hsk_v3_lesson_resume:v2:",
        source,
    ):
        failures.append({"issue": "lesson_resume_cache_key_changed"})
    if not re.search(
        r"function lessonMasteryKey\([^)]*\)\{return.hsk_v3_mastery:v",
        source,
    ):
        failures.append({"issue": "lesson_mastery_cache_key_changed"})

    lesson_cache_return = _function_return_line(source, "lessonDataKey")
    resume_return = _function_return_line(source, "lessonResumeKey")
    mastery_return = _function_return_line(source, "lessonMasteryKey")
    return {
        "schema_version": 1,
        "status": "SOURCE_CALLS_CLASSIFIED_REVIEW_REQUIRED" if not failures else "SOURCE_CONTRACT_REGRESSION",
        "source": PAGE,
        "classified_direct_calls": len(actual),
        "calls": [
            {
                "ordinal": row.get("ordinal"),
                "line": row.get("line"),
                "owner": row.get("owner"),
                "intent": row.get("intent"),
                "expected_future_policy": row.get("expected_future_policy"),
                "cost_sensitive": row.get("cost_sensitive"),
            }
            for row in expected if isinstance(row, dict)
        ],
        "cache_scope": {
            "memory_lesson_key_contains_identity": "localUserScope()" in lesson_cache_return,
            "resume_key_contains_identity": "localUserScope()" in resume_return,
            "mastery_key_contains_identity": "localUserScope()" in mastery_return,
        },
        "review_findings": [
            {"issue": "background_or_preview_reads_must_not_consume_lesson_quota",
             "status": "P0_manual_migration_blocker"},
            {"issue": "shared_page_lesson_cache_and_resume_identity_scope_requires_QA",
             "status": "P0_manual_account_switch_review"},
            {"issue": "skip_test_and_foundation_need_distinct_content_policy",
             "status": "P0_manual_access_review"},
        ],
        "regression_failures": failures,
        "limitations": [
            "Source syntax and existing six callsites only; not complete function call graph or deployed behavior.",
            "The existing Mini App direct JSON URL is public from code-level inspection, not a production HTTP test.",
            "No future content, token, correct answer, translation text or user state is included in the report.",
            "Cached lessons, score/resume and account switching require device QA and approved privacy decisions.",
        ],
    }


def audit(root: Path = ROOT) -> dict:
    registry = json.loads((root / REGISTRY).read_text(encoding="utf-8"))
    if registry.get("source") != PAGE:
        raise ValueError("Mini App registered source path changed")
    return audit_source((root / PAGE).read_text(encoding="utf-8"), registry)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(args.root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, UnicodeError) as exc:
        print("Mini App fetch safety audit failed:", exc, file=sys.stderr)
        return 1
    print("Mini App fetch intent contract:", report["status"],
          "calls:", report["classified_direct_calls"],
          "regressions:", len(report["regression_failures"]))
    return int(bool(report["regression_failures"]))


if __name__ == "__main__":
    raise SystemExit(main())

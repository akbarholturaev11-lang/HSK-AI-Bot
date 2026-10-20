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
    "audio_preload_before_continue", "background_nearby_prefetch",
    "interactive_lesson_after_reservation",
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
    if not re.search(r'var url="/api/v3/lesson/content/"\+level\+"/"', source):
        failures.append({"issue": "lesson_content_no_longer_uses_authenticated_api"})
    if not re.search(
        r'fetch\(lessonDataUrl\(lv,n\),\{headers:\{"X-Telegram-Init-Data":INIT_DATA\},cache:"no-store"\}\)',
        source,
    ):
        failures.append({"issue": "lesson_content_missing_signed_no_store_request"})
    if not re.search(r'fetch\("/api/v3/lesson/sales-preview"', source):
        failures.append({"issue": "sales_preview_projection_endpoint_missing"})
    if not re.search(r'fetch\("/api/v3/lesson/foundation"', source):
        failures.append({"issue": "foundation_projection_endpoint_missing"})
    if not re.search(r'_apiPost\("/api/v3/lesson/skip-test"', source):
        failures.append({"issue": "skip_test_projection_endpoint_missing"})
    if not re.search(r"Array\.isArray\(d&&d\.questions\).*slice\(0,6\)", source):
        failures.append({"issue": "skip_test_must_consume_bounded_server_questions"})
    if not re.search(r"if\(!q\.length\)\{toast\(skipI18n\(\)\.notReady", source):
        failures.append({"issue": "empty_skip_test_must_fail_closed"})
    if not re.search(
        r"function lessonDataKey\([^)]*\)\{return localUserScope\(\)\+",
        source,
    ):
        failures.append({"issue": "lesson_data_cache_identity_scope_missing"})
    if not re.search(
        r"function lessonResumeKey\([^)]*\)\{var scope=localUserScope\(\).*hsk_v3_lesson_resume:v3:",
        source,
    ):
        failures.append({"issue": "lesson_resume_account_scope_missing"})
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
        "status": "PURPOSE_SPECIFIC_API_CALLS_CLASSIFIED_REVIEW_REQUIRED" if not failures else "SOURCE_CONTRACT_REGRESSION",
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
            {"issue": "identity_scoped_lesson_cache_requires_runtime_QA",
             "status": "P0_manual_account_switch_review"},
            {"issue": "authenticated_lesson_content_requires_staging_HTTP_and_old_client_QA",
             "status": "P0_release_verification_open"},
        ],
        "regression_failures": failures,
        "limitations": [
            "Source syntax and existing six callsites only; not complete function call graph or deployed behavior.",
            "Mini App requests now target authenticated APIs in source; this scanner does not execute their server authorization.",
            "No future content, token, correct answer, translation text or user state is included in the report.",
            "Lesson JSON delivery, account switching and cached older Mini App clients still require staging/device QA.",
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

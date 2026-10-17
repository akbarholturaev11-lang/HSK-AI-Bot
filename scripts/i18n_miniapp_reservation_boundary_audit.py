#!/usr/bin/env python3
"""Read-only source contract for Mini App reserved starts versus public JSON GET.

No FastAPI imports, secrets, DB, HTTP or course answer values are accessed.
Source checks do not certify live entitlement; legacy JSON remains a P0
manual-review blocker even when the authenticated start gate passes.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
API = "app/api/miniapp_entitlements.py"
MINIAPP = "app/static/course-v3.html"


def _calls(node: ast.AST, name: str) -> list[ast.Call]:
    return [
        x for x in ast.walk(node)
        if isinstance(x, ast.Call)
        and (getattr(x.func, "attr", None) == name
             or isinstance(x.func, ast.Name) and x.func.id == name)
    ]


def _guarded_unauthorized(node: ast.AST) -> bool:
    for part in ast.walk(node):
        if not isinstance(part, ast.If):
            continue
        if not (isinstance(part.test, ast.UnaryOp)
                and isinstance(part.test.op, ast.Not)
                and isinstance(part.test.operand, ast.Name)
                and part.test.operand.id == "telegram_id"):
            continue
        if any(
            isinstance(call, ast.Call) and
            any(kw.arg == "status_code" and isinstance(kw.value, ast.Constant)
                and kw.value.value == 401 for kw in call.keywords)
            for stmt in part.body for call in ast.walk(stmt)
        ):
            return True
    return False


def _server_checks(source: str) -> dict[str, bool]:
    tree = ast.parse(source)
    nodes = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "v3_course_lesson_start"
    ]
    if len(nodes) != 1:
        raise ValueError("Mini App lesson start handler identity changed")
    fn = nodes[0]
    pretty = ast.unparse(fn)
    calls = _calls(fn, "status")
    consumed = any(
        "LessonAccessService(" in ast.unparse(call.func)
        and any(kw.arg == "consume" and isinstance(kw.value, ast.Constant)
                and kw.value.value is True for kw in call.keywords)
        for call in calls
    )
    return {
        "verifies_telegram_init_data": bool(_calls(fn, "extract_verified_webapp_user_id")),
        "rejects_missing_identity_401": _guarded_unauthorized(fn),
        "uses_verified_account_lookup": bool(_calls(fn, "get_by_telegram_id")),
        "rejects_out_of_sequence_lesson": (
            "order > completed + 1" in pretty
            and "course_lesson_not_unlocked" in pretty
        ),
        "enforces_numbered_lesson_bounds": (
            "order < 1" in pretty
            and "order > total_parts(level)" in pretty
        ),
        "uses_lesson_access_consume_true": consumed,
        "commits_entitlement_result": bool(_calls(fn, "commit")),
    }


def _client_checks(source: str) -> dict[str, bool]:
    return {
        "calls_authenticated_start_api_for_current_lesson": bool(re.search(
            r'return\s+_apiPost\("/api/v3/lesson/start",',
            source,
        )),
        "reserves_before_interactive_json_read": bool(re.search(
            r"reserveLessonStart\(l\)\.then\(function\(\)\{return loadLessonData\(lv,l\.n\)\}",
            source,
        )),
        "uses_direct_legacy_static_json_fetch": bool(re.search(
            r"fetch\(lessonDataUrl\(lv,n\),", source,
        )),
        "permits_skip_of_reservation_without_init_data": bool(re.search(
            r"if\(!INIT_DATA\|\|!l\|\|l\.status!==[\"']current[\"']\)"
            r"return Promise\.resolve\(\{ok:true,allowed:true\}\)",
            source,
        )),
    }


def audit_source(api: str, client: str) -> dict:
    server = _server_checks(api)
    frontend = _client_checks(client)
    required = {
        **{f"server.{k}": v for k, v in server.items()},
        **{f"miniapp.{k}": v for k, v in frontend.items()},
    }
    missing = [
        {"issue": "source_contract_changed", "check": key}
        for key, ok in required.items() if not ok
    ]
    return {
        "schema_version": 1,
        "status": "SOURCE_REGRESSION" if missing else "SOURCE_AUTH_GATE_PRESENT_LEGACY_GET_REVIEW",
        "server": server,
        "miniapp": frontend,
        "regressions": missing,
        "review_findings": [
            {
                "issue": "static_lesson_json_not_tied_to_user_reservation",
                "severity": "P0_manual_migration_blocker",
            },
            {
                "issue": "client_skips_reservation_without_telegram_initdata",
                "severity": "P0_compatibility_review",
            },
        ],
        "limits": [
            "This checks source AST and Mini App call expressions only; no requests or account tests.",
            "The start API authenticates/reserves, but the legacy JSON GET does not carry this access decision.",
            "A successful entitlement reservation does not itself make the separate static JSON URL private.",
            "Do not replace speculative preview/background calls with a consume=True API.",
            "Does not prove a paid-billing bypass, grade data exposure or production deployment behavior.",
        ],
    }


def audit(root: Path = ROOT) -> dict:
    return audit_source(
        (root / API).read_text(encoding="utf-8"),
        (root / MINIAPP).read_text(encoding="utf-8"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, SyntaxError, UnicodeError) as exc:
        print("Mini App lesson reservation source audit failed:", exc, file=sys.stderr)
        return 1
    print("Lesson reservation source:", report["status"],
          "regressions:", len(report["regressions"]))
    return int(bool(report["regressions"]))


if __name__ == "__main__":
    raise SystemExit(main())

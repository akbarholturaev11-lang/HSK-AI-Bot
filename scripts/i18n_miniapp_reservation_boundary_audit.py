#!/usr/bin/env python3
"""Read-only source contract for Mini App lesson start and content access.

No FastAPI imports, secrets, DB, HTTP or course answer values are accessed.
Source checks do not certify live entitlement or deployed route behavior.
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


def _shared_entitlement(node: ast.AST, *, consume: bool) -> bool:
    return any(
        "LessonAccessService(" in ast.unparse(call.func)
        and any(kw.arg == "consume" and isinstance(kw.value, ast.Constant)
                and kw.value.value is consume for kw in call.keywords)
        for call in _calls(node, "status")
    )


def _server_checks(source: str) -> dict[str, bool]:
    tree = ast.parse(source)
    start_nodes = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "v3_course_lesson_start"
    ]
    content_nodes = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "v3_course_lesson_content"
    ]
    skip_nodes = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "v3_course_lesson_skip_test"
    ]
    if len(start_nodes) != 1:
        raise ValueError("Mini App lesson start handler identity changed")
    if len(content_nodes) != 1:
        raise ValueError("Mini App lesson content handler identity changed")
    if len(skip_nodes) != 1:
        raise ValueError("Mini App lesson skip-test handler identity changed")
    fn = start_nodes[0]
    content_fn = content_nodes[0]
    skip_fn = skip_nodes[0]
    pretty = ast.unparse(fn)
    content_pretty = ast.unparse(content_fn)
    skip_pretty = ast.unparse(skip_fn)
    question_nodes = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "_skip_test_questions"
    ]
    if len(question_nodes) != 1:
        raise ValueError("Mini App skip-test projection identity changed")
    question_pretty = ast.unparse(question_nodes[0])
    skip_reads = _calls(skip_fn, "_read_course_lesson")
    skip_gates = _calls(skip_fn, "status")
    skip_denials = [
        n for n in ast.walk(skip_fn) if isinstance(n, ast.If)
        and ast.unparse(n.test) == "not access.get('allowed')"
        and any("status_code=403" in ast.unparse(stmt) for stmt in n.body)
    ]
    skip_success_projection = any(
        isinstance(call.args[0], ast.Dict)
        and {key.value for key in call.args[0].keys if isinstance(key, ast.Constant)}
            == {"ok", "level", "lesson_order", "questions"}
        and any(isinstance(key, ast.Constant) and key.value == "questions"
                and isinstance(value, ast.Name) and value.id == "questions"
                for key, value in zip(call.args[0].keys, call.args[0].values))
        for call in _calls(skip_fn, "_private_content_response") if call.args
    )
    private_responses = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "_private_content_response"
    ]
    private_headers = [
        n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "PRIVATE_CONTENT_HEADERS"
                for target in n.targets)
    ]
    locked_accounts = [
        call for call in _calls(fn, "get_by_telegram_id_for_update")
        if ast.unparse(call.func) == "UserRepository(session).get_by_telegram_id_for_update"
        and len(call.args) == 1
        and isinstance(call.args[0], ast.Name) and call.args[0].id == "telegram_id"
    ]
    progress_and_quota = _calls(fn, "get_by_user_id") + _calls(fn, "status")
    return {
        "verifies_telegram_init_data": bool(_calls(fn, "extract_verified_webapp_user_id")),
        "rejects_missing_identity_401": _guarded_unauthorized(fn),
        "uses_verified_account_lookup": bool(locked_accounts),
        "locks_account_before_progress_and_quota": (
            len(locked_accounts) == 1 and bool(progress_and_quota)
            and all(locked_accounts[0].lineno < call.lineno for call in progress_and_quota)
        ),
        "rejects_out_of_sequence_lesson": (
            "order > completed + 1" in pretty
            and "course_lesson_not_unlocked" in pretty
        ),
        "enforces_numbered_lesson_bounds": (
            "order < 1" in pretty
            and "order > total_parts(level)" in pretty
        ),
        "uses_lesson_access_consume_true": _shared_entitlement(fn, consume=True),
        "commits_entitlement_result": bool(_calls(fn, "commit")),
        "content_uses_authenticated_identity_helper": bool(_calls(content_fn, "_authenticated")),
        "content_rejects_missing_identity_401": _guarded_unauthorized(content_fn),
        "content_uses_verified_account_lookup": bool(_calls(content_fn, "get_by_telegram_id")),
        "content_rejects_out_of_sequence_lesson": (
            "lesson_order > completed + 1" in content_pretty
            and "course_lesson_not_unlocked" in content_pretty
        ),
        "content_enforces_numbered_lesson_bounds": (
            "lesson_order < 1" in content_pretty
            and "lesson_order > total" in content_pretty
        ),
        "content_checks_non_consuming_entitlement": _shared_entitlement(content_fn, consume=False),
        "content_uses_no_store_response": bool(_calls(content_fn, "_private_content_response")),
        "skip_test_uses_authenticated_identity_helper": bool(_calls(skip_fn, "_authenticated")),
        "skip_test_rejects_missing_identity_401": _guarded_unauthorized(skip_fn),
        "skip_test_uses_verified_account_lookup": bool(_calls(skip_fn, "get_by_telegram_id")),
        "skip_test_checks_selected_level": (
            "level != user_level" in skip_pretty
            and "user_level = content_level(getattr(user, 'level', None))" in skip_pretty
            and "course_level_not_allowed" in skip_pretty
        ),
        "skip_test_enforces_numbered_lesson_bounds": (
            any(isinstance(node, ast.If)
                and ast.unparse(node.test) == "level not in COURSE_LEVELS or lesson_order < 1"
                for node in ast.walk(skip_fn))
            and "total = total_parts(level)" in skip_pretty
            and any(isinstance(node, ast.If)
                    and ast.unparse(node.test) == "not total or lesson_order > total"
                    for node in ast.walk(skip_fn))
        ),
        "skip_test_checks_required_foundation": (
            bool(_calls(skip_fn, "_foundation_is_blocked"))
            and "android_foundation_required" in skip_pretty
        ),
        "skip_test_allows_locked_lesson_projection": not any(
            {"lesson_order", "completed"} <= {
                x.id for x in ast.walk(n.test) if isinstance(x, ast.Name)
            }
            for n in ast.walk(skip_fn) if isinstance(n, ast.If)
        ),
        "skip_test_checks_non_consuming_entitlement": _shared_entitlement(skip_fn, consume=False),
        "skip_test_access_denial_precedes_source_read": (
            len(skip_reads) == 1 and len(skip_gates) == 1 and len(skip_denials) == 1
            and skip_gates[0].lineno < skip_denials[0].lineno < skip_reads[0].lineno
        ),
        "skip_test_returns_bounded_projection_only": (
            bool(_calls(skip_fn, "_skip_test_questions")) and skip_success_projection
            and "secrets.SystemRandom().sample(candidates, min(6, len(candidates)))" in question_pretty
            and not any(isinstance(call.args[0], ast.Name) and call.args[0].id == "lesson"
                        for call in _calls(skip_fn, "_private_content_response") if call.args)
        ),
        "skip_test_uses_no_store_response": (
            len(private_responses) == 1 and len(private_headers) == 1
            and "'Cache-Control': 'no-store'" in ast.unparse(private_headers[0])
            and "headers=PRIVATE_CONTENT_HEADERS" in ast.unparse(private_responses[0])
            and all(isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "_private_content_response"
                    for node in ast.walk(skip_fn) if isinstance(node, ast.Return))
        ),
        "skip_test_does_not_commit_or_unlock_progress": not any(
            _calls(skip_fn, name) for name in ("commit", "unlock_lesson", "set_current_lesson_and_step")
        ) and not any(
            isinstance(target, ast.Attribute) for node in ast.walk(skip_fn)
            if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign))
            for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        ),
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
        "status": "SOURCE_REGRESSION" if missing else "SOURCE_AUTHENTICATED_CONTENT_GATE_PRESENT",
        "server": server,
        "miniapp": frontend,
        "regressions": missing,
        "review_findings": [],
        "limits": [
            "This checks source AST and Mini App call expressions only; no requests or deployed account tests.",
            "The lesson content API revalidates signed identity, sequence, foundation and entitlement without consuming quota.",
            "Locked-lesson skip tests return at most six questions after signed identity, selected-level, foundation and non-consuming entitlement checks; they do not unlock lessons.",
            "Do not replace speculative preview/background calls with a consume=True API.",
            "Does not certify paid billing, grade exposure or production deployment behavior.",
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

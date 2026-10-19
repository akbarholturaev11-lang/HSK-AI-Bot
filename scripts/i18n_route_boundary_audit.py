#!/usr/bin/env python3
"""P0 source-only audit: public HSK lesson JSON vs private exam boundary.

Reports route policy evidence, NOT live HTTP availability or entitlement.
Reads AST only; never imports FastAPI, starts a server or exposes answer values.
Expected legacy lesson exposure is a recorded BLOCKER, not retroactively fixed.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
LESSON_ROUTE = "/course_v3_data/{level}/{filename}"
EXAM_ROUTE = "/course_v3_data/exams/{filename}"
MAP_ROUTE = "/course_v3_data/{filename}"
GUARD_PREFIX = "/api/"


def routes(source: str) -> dict[str, ast.AsyncFunctionDef | ast.FunctionDef]:
    result = {}
    for node in ast.parse(source).body:
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not decorator.args:
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue
            if decorator.func.attr != "get":
                continue
            name = decorator.args[0]
            if isinstance(name, ast.Constant) and isinstance(name.value, str):
                path = name.value
                if path in {LESSON_ROUTE, EXAM_ROUTE, MAP_ROUTE}:
                    if path in result:
                        raise ValueError("Duplicate course data route: " + path)
                    result[path] = node
    if set(result) != {LESSON_ROUTE, EXAM_ROUTE, MAP_ROUTE}:
        raise ValueError("Course route contract changed; manual review required")
    return result


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _has_dependency(route: ast.AST) -> bool:
    exprs = list(route.args.defaults) + [
        x for x in route.args.kw_defaults if x is not None
    ] + list(route.decorator_list)
    return any(_call_name(child.func) in {"Depends", "Security"}
               for expr in exprs for child in ast.walk(expr)
               if isinstance(child, ast.Call))


def _uses_file_serve(route: ast.AST) -> bool:
    return any(isinstance(n, ast.Call) and
               _call_name(n.func) in {"static_json_response", "FileResponse"}
               for n in ast.walk(route))


def _returns_explicit_exam_404(route: ast.AST) -> bool:
    returns = [n for n in ast.walk(route) if isinstance(n, ast.Return)]
    if not returns:
        return False
    for ret in returns:
        value = ret.value
        if not isinstance(value, ast.Call) or _call_name(value.func) != "JSONResponse":
            return False
        status = next((kw.value for kw in value.keywords
                       if kw.arg == "status_code"), None)
        if not isinstance(status, ast.Constant) or status.value != 404:
            return False
    return True


def _lesson_filename_validation(route: ast.AST) -> bool:
    patterns = []
    for node in ast.walk(route):
        if not isinstance(node, ast.Call) or _call_name(node.func) != "fullmatch":
            continue
        if len(node.args) >= 2 and isinstance(node.args[0], ast.Constant):
            patterns.append((node.args[0].value,
                             node.args[1].id if isinstance(node.args[1], ast.Name) else None))
    return (("(?:hsk[1-4]|nhsk[1-3])", "level") in patterns
            and ("lesson_\\d+\\.json", "filename") in patterns)


def middleware_boundary(guard_source: str) -> dict:
    tree = ast.parse(guard_source)
    prefixes = [
        (target.id, node.value.value)
        for node in tree.body if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
        for target in node.targets if isinstance(target, ast.Name)
    ]
    value = dict(prefixes).get("GUARDED_PATH_PREFIX")
    if value is None:
        raise ValueError("Middleware public path-prefix contract changed")
    return {
        "guarded_prefix": value,
        "guard_applies_to_course_json": LESSON_ROUTE.startswith(value),
        "guard_applies_to_exam_route": EXAM_ROUTE.startswith(value),
        "scope_note": "prefix-only source analysis, not complete middleware or proxy audit",
    }


def audit(main_source: str, guard_source: str) -> dict:
    path_nodes = routes(main_source)
    lesson = path_nodes[LESSON_ROUTE]
    exam = path_nodes[EXAM_ROUTE]
    overview = path_nodes[MAP_ROUTE]
    middleware = middleware_boundary(guard_source)
    findings = []
    if not _returns_explicit_exam_404(exam) or _uses_file_serve(exam):
        findings.append({
            "route": EXAM_ROUTE,
            "issue": "private_exam_route_no_longer_returns_explicit_404",
            "severity": "stop_the_release",
        })
    if not _lesson_filename_validation(lesson):
        findings.append({
            "route": LESSON_ROUTE,
            "issue": "lesson_level_or_filename_validation_changed",
            "severity": "stop_the_release",
        })
    file_serve = _uses_file_serve(lesson)
    auth_dependency = _has_dependency(lesson)
    if file_serve and not auth_dependency and not middleware["guard_applies_to_course_json"]:
        findings.append({
            "route": LESSON_ROUTE,
            "issue": "source_level_public_lesson_file_exposure",
            "severity": "manual_entitlement_review_blocker",
        })
    if _uses_file_serve(overview) and not _has_dependency(overview):
        findings.append({
            "route": MAP_ROUTE,
            "issue": "source_level_public_curriculum_map",
            "severity": "classify_map_payload_before_public_locale_pack",
        })
    return {
        "schema_version": 1,
        "status": "SOURCE_REVIEW_REQUIRED" if findings else "SOURCE_CHECK_NO_FINDINGS",
        "lesson": {
            "route": LESSON_ROUTE, "handler": lesson.name,
            "serves_file": file_serve,
            "handler_dependency": auth_dependency,
            "has_level_and_filename_pattern_validation": _lesson_filename_validation(lesson),
        },
        "exam": {
            "route": EXAM_ROUTE, "handler": exam.name,
            "explicit_404_return": _returns_explicit_exam_404(exam),
            "serves_file": _uses_file_serve(exam),
        },
        "map": {
            "route": MAP_ROUTE, "handler": overview.name,
            "serves_file": _uses_file_serve(overview),
            "handler_dependency": _has_dependency(overview),
        },
        "middleware": middleware,
        "findings": findings,
        "limitations": [
            "Does not make HTTP requests, authenticate users, inspect deployed reverse-proxy config or evaluate global dependencies.",
            "Source-level route findings do not certify a production vulnerability or actual billing bypass.",
            "Does not inspect learner answers, private exam JSON, payment policies, trial or progress state.",
            "The existing lesson URL may be required by older Android, Desktop and Mini App clients.",
        ],
    }



MAP_TRACKS = ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")
PRIVATE_ASSESSMENT_KEYS = frozenset({
    "answer_id", "answer_key", "correct_answer", "correct_index",
    "correct_option", "correct_option_id", "correct_option_index",
    "expected_answer", "grading_key", "is_correct", "right_answer",
})


def _normalize_map_field(value: str) -> str:
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"[-\s]+", "_", name).lower()


def _assessment_key_paths(node: object, at: str = "$") -> list[str]:
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            here = at + "." + str(key)
            if _normalize_map_field(str(key)) in PRIVATE_ASSESSMENT_KEYS:
                found.append(here)
            found.extend(_assessment_key_paths(value, here))
    elif isinstance(node, list):
        for item in node:
            found.extend(_assessment_key_paths(item, at + "[]"))
    return found


def curriculum_map_shapes(root: Path = ROOT) -> dict:
    """Inspect seven top-level curriculum maps; never serialize their contents."""
    maps = []
    for level in MAP_TRACKS:
        rel = f"app/static/course_v3_data/{level}.json"
        data = json.loads((root / rel).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("units"), list):
            raise ValueError(f"Invalid course map structure: {rel}")
        units = data["units"]
        if not units or any(not isinstance(u, dict) or
                            not isinstance(u.get("lessons"), list) for u in units):
            raise ValueError(f"Malformed course units: {rel}")
        lesson_items = [lesson for unit in units for lesson in unit["lessons"]]
        if not lesson_items or not all(isinstance(item, dict) for item in lesson_items):
            raise ValueError(f"Invalid course lesson navigation entries: {rel}")
        keys = _assessment_key_paths(data)
        maps.append({
            "level": level, "source_path": rel, "unit_count": len(units),
            "lesson_navigation_entries": len(lesson_items),
            "top_level_field_names": sorted(data.keys()),
            "lesson_entry_field_names": sorted(set().union(
                *(set(item.keys()) for item in lesson_items)
            )),
            "private_assessment_key_paths": keys,
        })
    return {
        "maps_checked": len(maps),
        "lesson_navigation_entries": sum(m["lesson_navigation_entries"] for m in maps),
        "private_assessment_key_occurrences": sum(
            len(m["private_assessment_key_paths"]) for m in maps
        ),
        "maps": maps,
        "limits": "Structural keys only: public lesson metadata still requires content and entitlement review",
    }



def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        report = audit(
            (args.root / "app/main.py").read_text(encoding="utf-8"),
            (args.root / "app/services/blocked_user_guard.py").read_text(encoding="utf-8"),
        )
        report["curriculum_maps"] = curriculum_map_shapes(args.root)
        for nav_map in report["curriculum_maps"]["maps"]:
            for key_path in nav_map["private_assessment_key_paths"]:
                report["findings"].append({
                    "route": MAP_ROUTE, "file": nav_map["source_path"],
                    "path": key_path,
                    "issue": "public_curriculum_map_contains_private_assessment_key",
                    "severity": "stop_the_release",
                })
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except (OSError, UnicodeError, ValueError, SyntaxError) as exc:
        print("P0 route boundary audit failed:", exc, file=sys.stderr)
        return 1
    issues = report["findings"]
    print("Course route boundary:", report["status"], len(issues), "review findings")
    return int(any(row["severity"] == "stop_the_release" for row in issues))


if __name__ == "__main__":
    raise SystemExit(main())

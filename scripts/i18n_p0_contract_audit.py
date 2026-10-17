#!/usr/bin/env python3
"""Read-only P0 locale compatibility and public lesson-JSON exposure audit.

This guard reports structural candidates only. It does not certify entitlement,
exam secrecy, translation quality, or client runtime behavior. It never dumps
actual questions, answers, learner text, or user records.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TRACKS = ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")
LOCALE_TAGS = {"uz": "uz", "ru": "ru", "tj": "tg"}
LESSON_FILE = re.compile(r"lesson_\d+\.json\Z")
ANSWER_FIELD = re.compile(
    r"(?:correct(?:_\w+)?|(?:expected|right)_answer(?:_\w+)?|"
    r"answer(?:_key|_index|_id|_option)?|is_correct|solution(?:_\w+)?)\Z",
    re.I,
)
PUBLIC_ROUTE = "/course_v3_data/{level}/{filename}"


def locale_contract(manifest: dict, registry: dict) -> dict:
    """Check P0 locale declarations; never rewrite persisted 'tj' values."""
    if manifest.get("schema_version") != 1 or registry.get("schema_version") != 1:
        raise ValueError("unsupported localization schema")
    if manifest.get("status") != "preparation_only_no_runtime_switch":
        raise ValueError("P0 must not enable runtime localization")
    if registry.get("runtime_changes_authorized") is not False:
        raise ValueError("P0 registry must forbid runtime changes")
    languages = manifest.get("locales")
    if not isinstance(languages, list) or any(not isinstance(x, dict) for x in languages):
        raise ValueError("invalid locales array")
    pairs = [(x.get("id"), x.get("tag")) for x in languages]
    if len(pairs) != len(LOCALE_TAGS) or dict(pairs) != LOCALE_TAGS:
        raise ValueError("unexpected uz/ru/tj and Android tg locale mapping")
    if len({item[0] for item in pairs}) != len(pairs):
        raise ValueError("duplicate locale ID")
    if manifest.get("default_locale") not in LOCALE_TAGS:
        raise ValueError("unsupported default locale")
    aliases = manifest.get("backend_compatibility_aliases")
    if not isinstance(aliases, dict) or any(
        aliases.get(key) != "tj" for key in ("tg", "tg-TJ")
    ):
        raise ValueError("missing Tajik compatibility aliases")
    if any(value not in LOCALE_TAGS for value in aliases.values()):
        raise ValueError("alias maps to unsupported backend locale")
    existing = registry.get("existing_languages")
    if not isinstance(existing, list) or (
        len(existing) != len(LOCALE_TAGS) or set(existing) != set(LOCALE_TAGS)
    ):
        raise ValueError("registry/manifest languages disagree")
    return {
        "backend_codes": sorted(LOCALE_TAGS),
        "display_tags": LOCALE_TAGS,
        "default_locale": manifest["default_locale"],
        "compatibility_aliases": sorted(aliases),
        "runtime_changes_authorized": False,
    }


def lesson_route_contract(source: str) -> dict:
    """Inspect the exact route decorator, not global auth/middleware behavior."""
    tree = ast.parse(source)
    matches = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not decorator.args:
                continue
            if not isinstance(decorator.func, ast.Attribute) or decorator.func.attr != "get":
                continue
            if not isinstance(decorator.args[0], ast.Constant):
                continue
            if decorator.args[0].value != PUBLIC_ROUTE:
                continue
            defaults = list(node.args.defaults) + list(node.args.kw_defaults)
            defaults.extend(kw.value for kw in decorator.keywords)
            has_dependency = any(
                isinstance(child, ast.Call) and (
                    (isinstance(child.func, ast.Name) and child.func.id in ("Depends", "Security"))
                    or (isinstance(child.func, ast.Attribute) and child.func.attr in ("Depends", "Security"))
                )
                for expr in defaults if expr is not None
                for child in ast.walk(expr)
            )
            matches.append({
                "path": PUBLIC_ROUTE, "handler": node.name,
                "explicit_dependency_in_handler_or_decorator": has_dependency,
                "global_middleware_and_upstream_auth": "not_evaluated",
            })
    if len(matches) != 1:
        raise ValueError("lesson route missing or duplicated; manual review required")
    return matches[0]


def structural_answer_fields(value: object, prefix: str = "$") -> Counter:
    """Record structural key paths, never any field values."""
    paths = Counter()
    if isinstance(value, dict):
        for key, child in value.items():
            at = prefix + "." + str(key)
            if ANSWER_FIELD.fullmatch(str(key)):
                paths[at] += 1
            paths.update(structural_answer_fields(child, at))
    elif isinstance(value, list):
        for child in value:
            paths.update(structural_answer_fields(child, prefix + "[]"))
    return paths


def run_audit(root: Path) -> dict:
    manifest = json.loads((root / "localization/manifest.json").read_text(encoding="utf-8"))
    registry = json.loads((root / "localization/surface_registry.json").read_text(encoding="utf-8"))
    locale = locale_contract(manifest, registry)
    route = lesson_route_contract((root / "app/main.py").read_text(encoding="utf-8"))
    by_track = {}
    candidate_paths = Counter()
    for track in TRACKS:
        directory = root / "app/static/course_v3_data" / track
        if not directory.is_dir():
            raise ValueError("missing course source directory " + track)
        paths = sorted(p for p in directory.iterdir() if p.is_file() and LESSON_FILE.fullmatch(p.name))
        if not paths:
            raise ValueError("empty course source directory " + track)
        by_track[track] = len(paths)
        for file in paths:
            data = json.loads(file.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("invalid lesson root object " + str(file))
            candidate_paths.update(structural_answer_fields(data))
    return {
        "schema_version": 1,
        "status": "P0_manual_security_review_required",
        "locale_contract": locale,
        "lesson_route": route,
        "scanned_lesson_files": sum(by_track.values()),
        "lesson_files_by_track": by_track,
        "answer_like_field_occurrences": sum(candidate_paths.values()),
        "answer_like_structural_paths": dict(sorted(candidate_paths.items())),
        "limitations": [
            "A route decorator is not an evaluation of middleware, authentication or authorization.",
            "An answer-like field name is a review candidate, not proof of a private exam key.",
            "Old static lessons may already be visible; do not publish additional locked content or answer keys.",
            "This report does not contain lesson text, answer values, user information or runtime HTTP responses.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run_audit(args.root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, SyntaxError, TypeError, json.JSONDecodeError) as exc:
        print("P0 contract audit failed:", exc, file=sys.stderr)
        return 1
    print("P0 locale/route guard:", report["scanned_lesson_files"],
          "lessons inspected; security review still required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

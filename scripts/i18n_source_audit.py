#!/usr/bin/env python3
"""P0 review-oriented inventory for HSK AI local-first localization.

Extends the existing candidate scanner without changing runtime copy, lesson
content, auth or paid access. Findings are *candidates*, not verified defects.
Usage: python scripts/i18n_source_audit.py --output /tmp/hsk-i18n-p0.json
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

try:
    from scripts.i18n_inventory import scan_file, scan_json
except ModuleNotFoundError:
    from i18n_inventory import scan_file, scan_json


ROOT = Path(__file__).resolve().parents[1]
LOCALES = frozenset({"uz", "ru", "tj"})
SCAN_GLOBS = {
    "lesson_content": (
        "app/static/course_v3_data/**/*.json",
        "app/static/course_data/**/*.json",
        "app/static/course_content/**/*.json",
        "scripts/hsk30/translations/**/*.json",
        "scripts/hsk30/generated/**/*.json",
    ),
    "bundled_content": (
        "android/app/src/main/assets/**/*.json",
        "app/static/hsk-*.js",
        "app/static/course_v3_data/hsk30-*.js",
    ),
    "miniapp_ui": ("app/static/**/*.html", "app/static/**/*.js"),
    "android_ui": ("android/app/src/**/*.kt", "android/app/src/**/res/values*/*.xml"),
    "desktop_ui": ("desktop/ui/**/*.html", "desktop/ui/**/*.js"),
    "bot_backend": (
        "app/bot/**/*.py", "app/api/**/*.py", "app/services/**/*.py",
        "app/repositories/**/*.py", "app/public_site/**/*.py", "app/main.py",
    ),
    "generators": (
        "scripts/gen_course_v3_from_seed.py", "scripts/hsk30/**/*.py",
        "scripts/seed_hsk*_lesson_*.py",
    ),
}
HTML_ATTR = re.compile(
    r"\b(placeholder|aria-label|aria-description|alt|title)\s*=\s*"
    r"(?P<quote>['\"])(?P<value>[^'\"<>\n]{2,200})(?P=quote)", re.I
)
HTML_STYLE_SCRIPT = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.I | re.S)
JS_CATALOG = re.compile(
    r"(?:^|[,{\n])\s*[A-Za-z_$][\w$]*\s*:\s*"
    r"(?P<quote>['\"])(?P<value>[^\n]{2,200}?)(?P=quote)", re.M,
)
VARIABLE = re.compile(r"(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})")
RESOURCE_ELEMENT = re.compile(r"<(string|plurals|string-array)\b([^>]*)>", re.I | re.S)
RESOURCE_NAME = re.compile(r"\bname\s*=\s*(['\"])(.*?)\1", re.I)
NO_TRANSLATE = re.compile(r"\btranslatable\s*=\s*(['\"])false\1", re.I)
MESSAGE_METHODS = frozenset({
    "answer", "reply", "edit_text", "send_message", "send_photo",
    "send_video", "send_document", "answer_text", "answer_photo",
    "answer_video", "send_animation",
})
BUTTON_CLASSES = frozenset({"InlineKeyboardButton", "KeyboardButton", "MenuButtonWebApp"})


def _markers(value: str) -> list[str]:
    return sorted(set(VARIABLE.findall(value)))


def json_placeholder_drift(data: object) -> list[dict]:
    """Review locale maps with non-equivalent named placeholders."""
    found = []

    def walk(value: object, where: str) -> None:
        if isinstance(value, dict):
            languages = value.keys() & LOCALES
            if "uz" in languages and isinstance(value["uz"], str):
                expected = _markers(value["uz"])
                for language in sorted(languages - {"uz"}):
                    if not isinstance(value[language], str):
                        continue
                    actual = _markers(value[language])
                    if expected != actual:
                        found.append({
                            "at": where, "locale": language,
                            "expected": expected, "actual": actual,
                        })
            for key, child in value.items():
                walk(child, where + "." + str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, where + "[" + str(index) + "]")

    walk(data, "$")
    return found


def python_message_candidates(source: str) -> list[dict]:
    """Use Python's parser so multiline concatenation and f-strings are visible."""
    tree = ast.parse(source)
    found = []

    def literal(node: ast.AST | None) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            parts = [part.value for part in node.values
                     if isinstance(part, ast.Constant) and isinstance(part.value, str)]
            return "…".join(parts) if parts else None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = literal(node.left), literal(node.right)
            return left + right if left is not None and right is not None else None
        return None

    for call in ast.walk(tree):
        if not isinstance(call, ast.Call):
            continue
        method = call.func.attr if isinstance(call.func, ast.Attribute) else (
            call.func.id if isinstance(call.func, ast.Name) else ""
        )
        value_node = None
        if method in MESSAGE_METHODS:
            arg = 1 if method.startswith("send_") else 0
            if len(call.args) > arg:
                value_node = call.args[arg]
            if value_node is None:
                value_node = next((p.value for p in call.keywords
                                   if p.arg in ("text", "caption")), None)
        elif method in BUTTON_CLASSES:
            value_node = next((p.value for p in call.keywords if p.arg == "text"), None)
        text = literal(value_node)
        if text and len(text.strip()) >= 2:
            found.append({"kind": "python_message", "line": call.lineno,
                          "sample": text.strip()[:140]})
    return found


def xml_names(source: str) -> set[str]:
    """Android string, plural and string-array names; skip non-translatable."""
    names = set()
    for m in RESOURCE_ELEMENT.finditer(source):
        if NO_TRANSLATE.search(m.group(2)):
            continue
        name = RESOURCE_NAME.search(m.group(2))
        if name:
            names.add(m.group(1).lower() + ":" + name.group(2))
    return names


def android_resource_parity(root: Path) -> dict:
    """Track Android flavor-specific missing and orphan translations."""
    rows = []
    for base in sorted((root / "android/app/src").glob("*/res/values/*.xml")):
        if not base.is_file():
            continue
        source_set = base.relative_to(root / "android/app/src").parts[0]
        try:
            expected = xml_names(base.read_text(encoding="utf-8"))
            if not expected:
                continue
            for folder in ("values-ru", "values-tg"):
                path = base.parent.parent / folder / base.name
                actual = (xml_names(path.read_text(encoding="utf-8"))
                          if path.is_file() else set())
                rows.append({
                    "source_set": source_set, "file": base.name, "locale": folder,
                    "expected": len(expected), "actual": len(actual),
                    "missing": sorted(expected - actual),
                    "orphan": sorted(actual - expected),
                })
        except (OSError, UnicodeError) as error:
            rows.append({"source_set": source_set, "file": base.name,
                         "read_error": str(error)})
    return {
        "compared_pairs": len(rows),
        "missing_count": sum(len(p.get("missing", [])) for p in rows),
        "orphan_count": sum(len(p.get("orphan", [])) for p in rows),
        "pairs": rows,
    }


def registry_coverage(root: Path) -> dict:
    path = root / "localization/surface_registry.json"
    if not path.is_file():
        return {"present": False, "surface_count": 0, "missing_anchors": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    surfaces = data.get("surfaces", [])
    if not isinstance(surfaces, list):
        raise ValueError("localization surface registry has no surfaces list")
    missing = sorted({
        file
        for surface in surfaces if isinstance(surface, dict)
        for file in surface.get("anchors", [])
        if not (root / file).is_file()
    })
    return {"present": True, "surface_count": len(surfaces),
            "missing_anchors": missing}


def scan_source(path: Path, root: Path, group: str, all_hits: bool = False) -> dict:
    """Augment original inventory with language and source-producer evidence."""
    report = scan_file(path, group, root, all_hits=all_hits)
    source = path.read_text(encoding="utf-8")
    report["sha256"] = hashlib.sha256(source.encode("utf-8")).hexdigest()
    additions = []
    if path.suffix == ".json" and not report.get("parse_error"):
        tree = json.loads(source)
        drift = json_placeholder_drift(tree)
        report["placeholder_mismatches"] = len(drift)
        additions += [{"kind": "placeholder_mismatch", **x} for x in drift]
    if path.suffix == ".py":
        try:
            additions += python_message_candidates(source)
        except SyntaxError as error:
            report["parse_error"] = str(error)
    if path.suffix == ".html":
        stripped = HTML_STYLE_SCRIPT.sub(lambda m: "\n" * m.group(0).count("\n"), source)
        for hit in HTML_ATTR.finditer(stripped):
            if hit.group("value").strip().startswith(("{", "$", "http")):
                continue
            additions.append({
                "kind": "html_attribute", "attribute": hit.group(1).lower(),
                "line": stripped.count("\n", 0, hit.start()) + 1,
                "sample": hit.group("value")[:140],
            })
    if path.suffix in (".html", ".js") and group in ("miniapp_ui", "desktop_ui"):
        if re.search(r"\b(I18N|LANG|messages|TEXTS)\b", source):
            for hit in JS_CATALOG.finditer(source):
                value = hit.group("value").strip()
                if value and not value.startswith(("http://", "https://")):
                    additions.append({
                        "kind": "js_catalog_candidate",
                        "line": source.count("\n", 0, hit.start()) + 1,
                        "sample": value[:140],
                    })
    legacy_count = report.get("candidate_literals", 0)
    report["candidate_literals"] = legacy_count + sum(
        hit["kind"] != "placeholder_mismatch" for hit in additions
    )
    kinds = Counter(
        hit.get("kind", "unknown") for hit in additions
        if hit.get("kind") != "placeholder_mismatch"
    )
    # Explicitly account for inherited scanner candidates. Review counts
    # and per-kind totals must not contradict each other.
    if legacy_count:
        kinds["legacy_scan_candidate"] += legacy_count
    report["candidate_kinds"] = dict(sorted(kinds.items()))
    if all_hits:
        report.setdefault("samples", []).extend(additions)
    else:
        # Avoid hiding all new detectors when the inherited scanner has
        # already filled its default twelve review samples.
        report["samples"] = (report.get("samples", [])[:6] + additions[:6])[:12]
    return report


def inventory(root: Path = ROOT, all_hits: bool = False) -> dict:
    files, seen = [], set()
    for group, patterns in SCAN_GLOBS.items():
        for pattern in patterns:
            for path in sorted(root.glob(pattern)):
                if not path.is_file() or path in seen:
                    continue
                seen.add(path)
                try:
                    files.append(scan_source(path, root, group, all_hits))
                except (OSError, UnicodeError, ValueError) as error:
                    files.append({
                        "path": path.relative_to(root).as_posix(), "group": group,
                        "read_error": str(error),
                    })
    by_group = Counter(x["group"] for x in files)
    kinds = Counter()
    for row in files:
        kinds.update(row.get("candidate_kinds", {}))
    coverage = android_resource_parity(root)
    try:
        registry = registry_coverage(root)
    except (OSError, UnicodeError, ValueError) as error:
        registry = {"present": True, "error": str(error),
                    "surface_count": 0, "missing_anchors": []}
    errors = sum(bool(x.get("parse_error") or x.get("read_error")) for x in files)
    errors += sum(bool(x.get("read_error")) for x in coverage["pairs"])
    errors += int(bool(registry.get("error")))
    return {
        "schema_version": 2,
        "status": "review_required",
        "scope": "heuristic coverage, not proof of complete translation or live defect",
        "locales": sorted(LOCALES),
        "files_scanned": len(files),
        "groups": dict(sorted(by_group.items())),
        "candidate_kinds": dict(sorted(kinds.items())),
        "localized_maps": sum(x.get("localized_maps", 0) for x in files),
        "missing_locale_maps": sum(x.get("missing_locale_maps", 0) for x in files),
        "placeholder_mismatches": sum(x.get("placeholder_mismatches", 0) for x in files),
        "candidate_literals": sum(x.get("candidate_literals", 0) for x in files),
        "parse_or_read_errors": errors,
        "registry": registry,
        "android_resource_parity": coverage,
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="save a reviewable JSON report")
    parser.add_argument("--all-hits", action="store_true", help="include all candidate samples")
    args = parser.parse_args()
    report = inventory(all_hits=args.all_hits)
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        print("Audit written:", args.output)
        print("Files:", report["files_scanned"],
              "locale maps:", report["localized_maps"],
              "candidates:", report["candidate_literals"],
              "parse/read errors:", report["parse_or_read_errors"])
    else:
        sys.stdout.write(output)
    return 1 if report["parse_or_read_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

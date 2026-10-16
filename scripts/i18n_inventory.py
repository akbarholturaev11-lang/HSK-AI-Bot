#!/usr/bin/env python3
"""Inventory possible user-visible copy across HSK AI without changing runtime.

This is a discovery tool, not an exhaustive proof that every string is localized.
Run: python scripts/i18n_inventory.py --output /tmp/hsk-i18n-audit.json
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = frozenset(("uz", "ru", "tj"))
GLOBS = {
    "miniapp": ("app/static/*.html", "app/static/*.js"),
    "bot_backend": ("app/bot/**/*.py", "app/api/*.py", "app/services/*.py",
                    "app/public_site/*.py"),
    "android": ("android/app/src/**/*.kt", "android/app/src/**/res/values*/*.xml"),
    "desktop": ("desktop/ui/*.html", "desktop/ui/js/*.js"),
    "lessons": ("app/static/course_v3_data/**/*.json",
                "app/static/course_data/*.json",
                "app/static/course_content/**/*.json",
                "scripts/hsk30/translations/**/*.json"),
    "bundled_data": ("android/app/src/main/assets/*.json",),
}
HTML_COPY = re.compile(
    r"<(?:button|h[1-6]|title|label|small|p|span|option|a)\b[^>]*>"
    r"\s*([^<>{}\n]{2,200}?)\s*</", re.I
)
CODE_COPY = re.compile(
    r"(?:\bText\s*\(\s*|\btext\s*=\s*|\bplaceholder\s*=\s*|"
    r"\bcontentDescription\s*=\s*|\btitle\s*=\s*|"
    r"\.answer\s*\(\s*)([\"'])([^\"'\n]{2,200})\1"
)
XML_STRING = re.compile(r"<string\s+[^>]*name=[\"']([^\"']+)", re.I)
TRANSLATABLE_HINTS = frozenset((
    "title", "subtitle", "meaning", "translation", "description",
    "explanation", "prompt", "text", "intro", "hint", "scene",
    "instructions", "label", "definition", "feedback",
))
SCRIPT_AND_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.I | re.S)


def scan_json(value: object, prefix: str = "$") -> tuple[int, list[dict], list[dict]]:
    localized = 0
    incomplete: list[dict] = []
    ambiguous: list[dict] = []

    def walk(node: object, at: str) -> None:
        nonlocal localized
        if isinstance(node, dict):
            locale_keys = set(node) & LOCALES
            if locale_keys:
                localized += 1
                missing = sorted(LOCALES - locale_keys)
                if missing:
                    incomplete.append({"at": at, "missing": missing})
                # Values of locale dictionaries are already classified.
                for key, child in node.items():
                    if key not in LOCALES:
                        walk(child, at + "." + str(key))
                return
            for key, child in node.items():
                path = at + "." + str(key)
                if (key in TRANSLATABLE_HINTS and isinstance(child, str)
                        and len(child.strip()) > 3 and not re.fullmatch(
                            r"[\u3400-\u9fff\s\d\W]+", child
                        )):
                    ambiguous.append({"at": path, "sample": child[:140]})
                else:
                    walk(child, path)
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, at + "[" + str(index) + "]")

    walk(value, prefix)
    return localized, incomplete, ambiguous


def scan_file(path: Path, group: str, root: Path = ROOT, all_hits: bool = False) -> dict:
    text = path.read_text(encoding="utf-8")
    relative = path.relative_to(root).as_posix()
    result: dict = {"path": relative, "group": group, "localized_maps": 0,
                    "missing_locale_maps": 0, "candidate_literals": 0,
                    "samples": [], "parse_error": None}
    if path.suffix == ".json":
        try:
            tree = json.loads(text)
        except json.JSONDecodeError as exc:
            result["parse_error"] = str(exc)
            return result
        found, missing, ambiguous = scan_json(tree)
        result["localized_maps"] = found
        result["missing_locale_maps"] = len(missing)
        examples = [{"kind": "missing_locale", **item} for item in missing]
        examples += [{"kind": "possibly_neutral_copy", **item} for item in ambiguous]
        result["candidate_literals"] = len(ambiguous)
        result["samples"] = examples if all_hits else examples[:12]
        return result

    if path.suffix == ".xml":
        result["resource_keys"] = len(XML_STRING.findall(text))
        return result

    patterns: list[tuple[str, re.Pattern, str]] = [("inline_code", CODE_COPY, text)]
    if path.suffix == ".html":
        stripped = SCRIPT_AND_STYLE.sub(
            lambda match: "\n" * match.group(0).count("\n"), text
        )
        patterns.append(("inline_html", HTML_COPY, stripped))

    found: list[dict] = []
    for kind, pattern, content in patterns:
        for match in pattern.finditer(content):
            value = (match.group(2) if kind == "inline_code" else match.group(1)).strip()
            if not value or value.startswith(("$", "{", "http", "R.string.")):
                continue
            found.append({"kind": kind,
                          "line": content.count("\n", 0, match.start()) + 1,
                          "sample": value[:140]})
    result["candidate_literals"] = len(found)
    result["samples"] = found if all_hits else found[:12]
    return result


def inventory(root: Path = ROOT, all_hits: bool = False) -> dict:
    output: list[dict] = []
    seen: set[Path] = set()
    for group, patterns in GLOBS.items():
        for glob in patterns:
            for path in sorted(root.glob(glob)):
                if not path.is_file() or path in seen:
                    continue
                seen.add(path)
                try:
                    output.append(scan_file(path, group, root, all_hits))
                except (OSError, UnicodeError) as exc:
                    output.append({"path": path.relative_to(root).as_posix(),
                                   "group": group, "read_error": str(exc)})
    by_group = Counter(row["group"] for row in output)
    return {
        "schema_version": 1,
        "scope": "heuristic source inventory; not proof of exhaustive coverage",
        "locales": sorted(LOCALES),
        "files_scanned": len(output),
        "groups": dict(sorted(by_group.items())),
        "localized_maps": sum(x.get("localized_maps", 0) for x in output),
        "missing_locale_maps": sum(x.get("missing_locale_maps", 0) for x in output),
        "candidate_literals": sum(x.get("candidate_literals", 0) for x in output),
        "parse_or_read_errors": sum(bool(x.get("parse_error") or x.get("read_error")) for x in output),
        "files": output,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write JSON audit outside the source tree")
    parser.add_argument("--all-hits", action="store_true", help="include all candidates")
    args = parser.parse_args()
    report = inventory(all_hits=args.all_hits)
    formatted = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(formatted + "\n", encoding="utf-8")
        print("Audit written:", args.output)
    else:
        print(formatted)
    return 1 if report["parse_or_read_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

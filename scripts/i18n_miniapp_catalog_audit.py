#!/usr/bin/env python3
"""P0 read-only Mini App nested source-literal locale audit.

Never imports or executes JS; translated strings, questions and answers are
never put in the report. Only selected verified existing dictionaries are
included. Dynamic expressions are review candidates, not translations.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ("uz", "ru", "tj")
TARGETS = (
    ("app/static/course-v3.html", "I18N"),
    ("app/static/course-v3.html", "TRACK_UI"),
    ("app/static/course-v3.html", "HSK30_BOOK_COPY"),
    ("app/static/subscription.html", "I18N"),
    ("app/static/course_v3_test.html", "L"),
    ("app/static/course_v3_test.html", "EM"),
    ("app/static/course_v3_test.html", "HSK30_SOON"),
    ("app/static/course_v3_test.html", "PT"),
    ("app/static/course_v3_mistakes.html", "L"),
    ("app/static/course_v3_pronunciation.html", "L"),
    ("app/static/course_v3_recognition.html", "L"),
    ("app/static/course_v3_onboarding.html", "ONBOARDING_LEGACY"),
    ("app/static/course_v3_voice.html", "L"),
    ("app/static/hsk-lugat.html", "UI"),
    ("app/static/hsk-lugat.html", "practiceLabels"),
    ("app/static/hsk-lugat.html", "memoLabels"),
    ("app/static/hsk-lugat.html", "messages"),
    ("app/static/hsk-gaplar.html", "UI"),
)
NAME = re.compile(r"^\s*([A-Za-z_$][\w$]*)\s*:\s*", re.S)
VARIABLE = re.compile(r"(?<![$\{])\{([A-Za-z_]\w*)\}(?!\})")
TAG = re.compile(r"</?([A-Za-z][A-Za-z0-9-]*)\b")


def split_top(src: str) -> list[str]:
    """Split at commas outside JS strings, arrays, objects and comments."""
    if not src or src[0] not in "[{" or src[-1] not in "]}":
        raise ValueError("JS object/array literal boundaries required")
    inside = src[1:-1]
    starts, stack, i, items = 0, [], 0, []
    close = {"]": "[", "}": "{", ")": "("}
    while i < len(inside):
        ch = inside[i]
        if inside.startswith("//", i):
            end = inside.find("\n", i + 2)
            i = len(inside) if end < 0 else end
            continue
        if inside.startswith("/*", i):
            end = inside.find("*/", i + 2)
            if end < 0:
                raise ValueError("Unclosed JS comment")
            i = end + 2
            continue
        if ch in ("'", '"', chr(96)):
            quote = ch
            i += 1
            while i < len(inside):
                if inside[i] == "\\":
                    i += 2
                elif inside[i] == quote:
                    i += 1
                    break
                else:
                    i += 1
            else:
                raise ValueError("Unclosed JS string")
            continue
        if ch in ("{", "[", "("):
            stack.append(ch)
        elif ch in ("}", "]", ")"):
            if not stack or stack.pop() != close[ch]:
                raise ValueError("Mismatched JS delimiters")
        elif ch == "," and not stack:
            if inside[starts:i].strip():
                items.append(inside[starts:i].strip())
            starts = i + 1
        i += 1
    if stack:
        raise ValueError("Unclosed JS nesting")
    if inside[starts:].strip():
        items.append(inside[starts:].strip())
    return items


def key_value(fragment: str) -> tuple[str, str]:
    m = NAME.match(fragment)
    if m:
        return m.group(1), fragment[m.end():].strip()
    f = fragment.lstrip()
    if not f or f[0] not in ("'", '"'):
        raise ValueError("Unsupported object property")
    mark = f[0]
    i = 1
    while i < len(f):
        if f[i] == "\\":
            i += 2
        elif f[i] == mark:
            remain = f[i + 1:].lstrip()
            if remain.startswith(":"):
                return f[1:i], remain[1:].strip()
            break
        else:
            i += 1
    raise ValueError("Unsupported quoted object key")


def flatten(value: str, path: str, leaves: dict, issues: list, depth: int = 0) -> None:
    if depth > 16:
        issues.append({"path": path, "issue": "excessive_nesting"})
        return
    value = value.strip()
    if value.startswith("{") and value.endswith("}"):
        seen = set()
        for field in split_top(value):
            try:
                key, child = key_value(field)
            except ValueError:
                issues.append({"path": path, "issue": "unsupported_property"})
                continue
            child_path = (path + "." if path else "") + key
            if key in seen:
                issues.append({"path": child_path, "issue": "duplicate_property"})
            seen.add(key)
            flatten(child, child_path, leaves, issues, depth + 1)
    elif value.startswith("[") and value.endswith("]"):
        for pos, child in enumerate(split_top(value)):
            flatten(child, path + f"[{pos}]", leaves, issues, depth + 1)
    elif len(value) >= 2 and value[0] in ('"', "'", chr(96)) and value[-1] == value[0]:
        if value[0] == chr(96) and (("$" + "{") in value):
            issues.append({"path": path, "issue": "dynamic_template"})
        leaves[path] = {
            "type": "literal",
            "variables": sorted(Counter(VARIABLE.findall(value)).items()),
            "tags": sorted(Counter(TAG.findall(value)).items()),
        }
    else:
        legacy = re.match(r"^function\s*\(([^)]*)\)\s*\{", value)
        if legacy:
            params = [x.strip() for x in legacy.group(1).split(",") if x.strip()]
            if not all(re.fullmatch(r"[A-Za-z_$][\w$]*", x) for x in params):
                issues.append({"path": path, "issue": "unsupported_function_parameter"})
            leaves[path] = {"type": "legacy_callable", "parameters": params}
            issues.append({"path": path, "issue": "legacy_function_copy",
                           "parameters": params})
        else:
            leaves[path] = {"type": "expression"}
            issues.append({"path": path, "issue": "dynamic_value"})


def compare_literal(source: str) -> dict:
    locale_src = {}
    for field in split_top(source):
        key, value = key_value(field)
        if key in locale_src:
            raise ValueError("Duplicate top-level locale")
        locale_src[key] = value
    if set(locale_src) != set(LOCALES):
        raise ValueError("Expected exactly uz/ru/tj locale mappings")
    leaves, issues = {}, []
    for locale in LOCALES:
        leaves[locale] = {}
        flatten(locale_src[locale], "", leaves[locale], issues)
    all_keys = sorted(set().union(*(set(leaves[locale]) for locale in LOCALES)))
    missing, mismatch, markup, types, callables = [], [], [], [], []
    for key in all_keys:
        present = [loc for loc in LOCALES if key in leaves[loc]]
        absent = [loc for loc in LOCALES if loc not in present]
        if absent:
            missing.append({"path": key, "missing": absent})
        first = leaves[present[0]][key]
        for loc in present[1:]:
            current = leaves[loc][key]
            if current["type"] != first["type"]:
                types.append({"path": key, "locale": loc})
            if current["type"] == "legacy_callable" and first["type"] == "legacy_callable":
                if current["parameters"] != first["parameters"]:
                    callables.append({"path": key, "locale": loc,
                                      "reference_params": first["parameters"],
                                      "locale_params": current["parameters"]})
            if current["type"] != "literal" or first["type"] != "literal":
                continue
            if current["variables"] != first["variables"]:
                mismatch.append({"path": key, "locale": loc,
                    "reference_signature": first["variables"],
                    "locale_signature": current["variables"]})
            if current["tags"] != first["tags"]:
                markup.append({"path": key, "locale": loc})
    return {
        "leaf_counts": {loc: len(leaves[loc]) for loc in LOCALES},
        "leaf_union": len(all_keys), "missing_leaves": missing,
        "placeholder_drift": mismatch, "html_tag_count_drift": markup,
        "value_type_drift": types, "legacy_function_parameter_drift": callables,
        "parse_review": issues,
    }


def extract_literal(text: str, name: str) -> tuple[str, int]:
    rx = r"\b(?:const|let|var)\s+" + re.escape(name) + r"\s*=\s*(?=\{)"
    matches = list(re.finditer(rx, text))
    if len(matches) != 1:
        raise ValueError(f"Expected one static {name} declaration; found {len(matches)}")
    start = matches[0].end()
    quote, level, i = None, 0, start
    while i < len(text):
        ch = text[i]
        if text.startswith("//", i):
            end = text.find("\n", i + 2)
            i = len(text) if end < 0 else end
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                raise ValueError("Unterminated comment")
            i = end + 2
            continue
        if ch in ("'", '"', chr(96)):
            mark = ch
            i += 1
            while i < len(text):
                if text[i] == "\\":
                    i += 2
                elif text[i] == mark:
                    i += 1
                    break
                else:
                    i += 1
            else:
                raise ValueError("Unterminated JS string")
            continue
        if ch == "{":
            level += 1
        if ch == "}":
            level -= 1
            if level == 0:
                return text[start:i + 1], text.count("\n", 0, start) + 1
            if level < 0:
                raise ValueError("Bad JS braces")
        i += 1
    raise ValueError("JS catalog object not closed")


HOTSPOT_PAGES = (
    "course-v3.html", "subscription.html", "course_v3_test.html",
    "course_v3_memorize.html", "course_v3_mistakes.html",
    "course_v3_pronunciation.html", "course_v3_recognition.html",
    "course_v3_onboarding.html", "course_v3_voice.html",
    "hsk-lugat.html", "hsk-gaplar.html",
)
HOTSPOT_PATTERNS = {
    "inline_locale_call": re.compile(r"\b(?:tr|t)\s*\(\s*\{\s*(?:uz|ru|tj)\s*:"),
    "language_branch": re.compile(r"\bLANG\s*===?\s*['\"](?:uz|ru|tj)['\"]"),
    "locale_object_declaration": re.compile(
        r"\b(?:var|let|const)\s+\w+\s*=\s*\{\s*(?:uz|ru|tj)\s*:\s*\{"
    ),
    "markup_attribute_candidate": re.compile(
        r"\b(?:aria-label|placeholder|title|alt)\s*=\s*['\"][^'\"<>]{2,200}['\"]",
        re.I,
    ),
}


def source_hotspots(root: Path, pages: tuple[str, ...] = HOTSPOT_PAGES) -> dict:
    """Candidates, not confirmed defects; includes already audited catalogs."""
    out = {}
    for file in pages:
        text = (root / "app/static" / file).read_text(encoding="utf-8")
        row = {}
        for name, pattern in HOTSPOT_PATTERNS.items():
            matches = list(pattern.finditer(text))
            row[name] = {
                "candidate_count": len(matches),
                "first_lines": [text.count("\n", 0, m.start()) + 1 for m in matches[:30]],
            }
        out[file] = row
    return out


def inventory(root: Path = ROOT) -> dict:
    reports = []
    for rel, name in TARGETS:
        source = (root / rel).read_text(encoding="utf-8")
        literal, line = extract_literal(source, name)
        reports.append({"file": rel, "catalog": name, "source_line": line,
                        **compare_literal(literal)})
    return {"schema_version": 1, "status": "manual_review_required",
            "scope": "Selected current Mini App static locale catalogs; not exhaustive UI",
            "catalogs": reports,
            "source_hotspots": source_hotspots(root),
            "limitations": [
                "Hotspot counts include already audited catalogs; they are not remaining error counts.",
                "Other per-page ad hoc locale strings and runtime DOM remain to be audited.",
                "The scanner does not execute JS, render WebView or attest translation quality.",
                "Dynamic JS expressions are review items; no private lesson/answer content emitted.",
            ]}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--output", type=Path, required=True)
    opts = p.parse_args()
    try:
        result = inventory(opts.root)
        opts.output.parent.mkdir(parents=True, exist_ok=True)
        opts.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        print("Mini App catalog P0 audit failed:", exc, file=sys.stderr)
        return 1
    for r in result["catalogs"]:
        print(r["file"], r["catalog"], r["leaf_counts"],
              "missing:", len(r["missing_leaves"]),
              "placeholders:", len(r["placeholder_drift"]),
              "parser review:", len(r["parse_review"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

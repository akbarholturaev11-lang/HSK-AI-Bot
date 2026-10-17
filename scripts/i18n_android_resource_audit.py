#!/usr/bin/env python3
"""Read-only P0 Android localized XML structural and placeholder audit.

Android resources are owned by source sets (main/direct/play). Only compares
same-name files and resource entries for existing ru/tg locales. Findings are
review candidates, not proof of malformed UI or a bad translation. No values
of learner-visible strings are emitted to JSON reports.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("android/app/src")
LOCALES = ("values-ru", "values-tg")
RESOURCE_TAGS = frozenset(("string", "plurals", "string-array"))
FORMAT_TOKEN = re.compile(r"%(?:(?P<position>\d+)\$)?[-+ #0,(]*\d*(?:\.\d+)?(?P<type>[a-zA-Z%])")
NAMED_TOKEN = re.compile(r"(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})")


def _local_tag(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def _text(element: ET.Element) -> str:
    return "".join(element.itertext())


def placeholder_signature(value: str) -> dict:
    """Compare token counts/types, without exposing the translated text."""
    printf = Counter()
    for match in FORMAT_TOKEN.finditer(value):
        if match.group("type") == "%":
            continue
        printf[(match.group("position") or "implicit") + ":" + match.group("type")] += 1
    named = Counter(NAMED_TOKEN.findall(value))
    return {
        "printf": sorted((token, n) for token, n in printf.items()),
        "named": sorted((token, n) for token, n in named.items()),
    }


def parse_resources(source: str) -> dict[str, dict]:
    root = ET.fromstring(source)
    if _local_tag(root.tag) != "resources":
        raise ValueError("Android XML must use a resources root")
    catalog = {}
    for item in root:
        kind = _local_tag(item.tag)
        if kind not in RESOURCE_TAGS or item.attrib.get("translatable") == "false":
            continue
        name = item.attrib.get("name")
        if not name:
            continue
        key = kind + ":" + name
        if key in catalog:
            raise ValueError("duplicate Android resource: " + key)
        if kind == "string":
            values = {"text": _text(item)}
        elif kind == "plurals":
            values = {}
            for child in item:
                if _local_tag(child.tag) == "item":
                    quantity = child.attrib.get("quantity")
                    if quantity in values:
                        raise ValueError("duplicate plural quantity in " + key)
                    if quantity:
                        values[quantity] = _text(child)
        else:
            values = [_text(child) for child in item if _local_tag(child.tag) == "item"]
        catalog[key] = {"kind": kind, "values": values,
                        "formatted": item.attrib.get("formatted") != "false"}
    return catalog


def compare_resources(base: dict[str, dict], translated: dict[str, dict]) -> list[dict]:
    """Find potential contract drift, keeping every finding content-free."""
    findings = []
    for key in sorted(set(base) - set(translated)):
        findings.append({"key": key, "issue": "missing_resource"})
    for key in sorted(set(translated) - set(base)):
        findings.append({"key": key, "issue": "orphan_resource"})
    for key in sorted(set(base) & set(translated)):
        left, right = base[key], translated[key]
        if left["formatted"] != right["formatted"]:
            findings.append({"key": key, "issue": "formatted_flag_drift"})
        if left["kind"] == "string-array":
            a, b = left["values"], right["values"]
            if len(a) != len(b):
                findings.append({"key": key, "issue": "array_length_drift",
                                 "source_length": len(a), "locale_length": len(b)})
            indexed = ((f"[{i}]", a[i], b[i]) for i in range(min(len(a), len(b))))
        else:
            a, b = left["values"], right["values"]
            if left["kind"] == "plurals":
                if set(a) != set(b):
                    findings.append({"key": key, "issue": "plural_quantity_drift",
                                     "missing": sorted(set(a) - set(b)),
                                     "orphan": sorted(set(b) - set(a))})
            indexed = ((q, a[q], b[q]) for q in sorted(set(a) & set(b)))
        if not left["formatted"] or not right["formatted"]:
            # formatted=false strings may intentionally contain literal '%' signs.
            continue
        for slot, source_text, locale_text in indexed:
            if placeholder_signature(source_text) != placeholder_signature(locale_text):
                findings.append({"key": key, "issue": "placeholder_drift",
                                 "slot": slot,
                                 "source_signature": placeholder_signature(source_text),
                                 "locale_signature": placeholder_signature(locale_text)})
    return findings


def audit(root: Path = ROOT) -> dict:
    results = []
    counts = Counter()
    for base in sorted((root / BASE).glob("*/res/values/*.xml")):
        if not base.is_file():
            continue
        source_set = base.relative_to(root / BASE).parts[0]
        try:
            original = parse_resources(base.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError, ET.ParseError) as err:
            results.append({"source_set": source_set, "file": base.name,
                            "issue": "invalid_source_xml", "error_type": type(err).__name__})
            counts["invalid_source_xml"] += 1
            continue
        if not original:
            continue
        for loc in LOCALES:
            file = base.parent.parent / loc / base.name
            if not file.is_file():
                results.append({"source_set": source_set, "file": base.name,
                                "locale": loc, "issue": "missing_locale_file"})
                counts["missing_locale_file"] += 1
                continue
            try:
                target = parse_resources(file.read_text(encoding="utf-8"))
                findings = compare_resources(original, target)
            except (OSError, UnicodeError, ValueError, ET.ParseError) as err:
                findings = [{"issue": "invalid_locale_xml",
                             "error_type": type(err).__name__}]
            counts["compared_pairs"] += 1
            for finding in findings:
                issue = finding["issue"]
                counts[issue] += 1
                results.append({"source_set": source_set, "file": base.name,
                                "locale": loc, **finding})
    return {
        "schema_version": 1,
        "status": "manual_review_required",
        "scope": "Android XML structural checks only; not Android compilation or UI translation quality",
        "compared_pairs": counts["compared_pairs"],
        "issues_by_type": {key: counts[key] for key in sorted(counts) if key != "compared_pairs"},
        "findings": results,
        "notes": [
            "String values are intentionally excluded from the report.",
            "Plural quantity differences and placeholder drift need review, not automatic translation.",
            "Source-set overlays may legitimately omit keys supplied by main; review effective Android merge semantics.",
        ],
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = audit(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Android XML P0:", result["compared_pairs"], "pairs,",
          len(result["findings"]), "review findings,",
          result["issues_by_type"])
    return 1 if any(
        row["issue"] in ("invalid_source_xml", "invalid_locale_xml")
        for row in result["findings"]
    ) else 0


if __name__ == "__main__":
    raise SystemExit(main())

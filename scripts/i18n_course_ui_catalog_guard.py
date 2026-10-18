#!/usr/bin/env python3
"""Validate local-first Mini App course UI catalogs; no app imports or network.

Only approved static UI messages; no lesson JSON, graded answers, user data,
runtime HTTP, payments or production resources are touched.
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
SOURCE = "localization/ui"
EXPECTED_COUNT = 124
KEY_NAME = re.compile(r"[a-z][a-zA-Z0-9]*(?:\.[a-z][a-zA-Z0-9]*)*")
PLACEHOLDER = re.compile(r"\{([A-Za-z][A-Za-z0-9_]*)\}")
GRADING_KEYS = {
    "answer", "answer_key", "answer_tokens", "correct_index",
    "correct_answer", "correct_option_id", "correct_tokens",
    "grading_key", "is_correct", "options", "solution_tokens",
}
REQUIRED_METADATA = {"schema_version", "namespace", "locale", "messages"}


def no_duplicate_keys(pairs):
    output = {}
    for key, value in pairs:
        if key in output:
            raise ValueError("Duplicate source JSON key (values never logged): " + str(key))
        output[key] = value
    return output


def signature(value: str) -> tuple[tuple[str, int], ...]:
    placeholders = PLACEHOLDER.findall(value)
    remainder = PLACEHOLDER.sub("", value)
    if "{" in remainder or "}" in remainder:
        raise ValueError("Invalid named UI placeholder syntax")
    return tuple(sorted(Counter(placeholders).items()))


def review_sources(root: Path = ROOT) -> dict:
    catalogs = {}
    for locale in LOCALES:
        relative = f"{SOURCE}/{locale}/course.json"
        parsed = json.loads((root / relative).read_text(encoding="utf-8"),
                            object_pairs_hook=no_duplicate_keys)
        if (not isinstance(parsed, dict)
                or set(parsed) != REQUIRED_METADATA
                or parsed["schema_version"] != 1
                or parsed["locale"] != locale
                or parsed["namespace"] != "course"
                or not isinstance(parsed["messages"], dict)):
            raise ValueError("Invalid course UI source schema: " + locale)
        current = parsed["messages"]
        if len(current) != EXPECTED_COUNT:
            raise ValueError(f"Course UI key set changed for {locale}; re-review required")
        for key, val in current.items():
            if (not isinstance(key, str) or not KEY_NAME.fullmatch(key)
                    or key.lower().replace(".", "_") in GRADING_KEYS
                    or not isinstance(val, str) or not val.strip()
                    or "<" in val or ">" in val):
                raise ValueError("Invalid/non-UI course catalog entry: " + locale + "/" + str(key))
            try:
                signature(val)
            except ValueError as exc:
                raise ValueError("Invalid placeholder: " + locale + "/" + key) from exc
        catalogs[locale] = current

    reference = set(catalogs["uz"])
    for locale in LOCALES[1:]:
        if set(catalogs[locale]) != reference:
            raise ValueError("Course UI locale key mismatch: " + locale)
    for key in sorted(reference):
        expected = signature(catalogs["uz"][key])
        if any(signature(catalogs[locale][key]) != expected for locale in LOCALES[1:]):
            raise ValueError("Course UI placeholder mismatch: " + key)
    return {
        "schema_version": 1,
        "status": "SOURCE_CONTRACT_VALID_RUNTIME_NOT_TESTED",
        "namespace": "course",
        "locales": list(LOCALES),
        "message_keys": len(reference),
        "placeholder_keys": sum(bool(signature(catalogs["uz"][key])) for key in reference),
        "sources": [f"{SOURCE}/{locale}/course.json" for locale in LOCALES],
        "limitations": [
            "No live Mini App rendering, Android/desktop language switch or RTL/layout screenshots.",
            "The source keys reflect current UI copy; semantic translation quality needs human review.",
            "This validates no entitlement, quiz, exam, offline cache or Pro payment behavior.",
            "Never use these static UI catalogs to publish raw lesson JSON or grading answers.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = review_sources(args.root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, UnicodeError) as exc:
        print("Course UI source validation failed:", exc, file=sys.stderr)
        return 1
    print("Course UI catalog contract:", report["message_keys"],
          "keys across", len(report["locales"]), "locales")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

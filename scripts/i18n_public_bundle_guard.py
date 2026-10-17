#!/usr/bin/env python3
"""Fail closed on accidental answer-key leakage in *new* public locale packs.

P0 preparation safety rule, not a claim that existing public lessons are safe:
the legacy /course_v3_data/<track>/lesson_*.json route is OUT OF SCOPE.
No files are changed or imported; only JSON key paths, never values, are emitted.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
# These are proposed destinations, not published bundles. Keep additions
# explicit: reviewing a new output path is mandatory before enabling it.
LOCALE_PACK_ROOTS = (
    "app/static/i18n",
    "app/static/locales",
    "app/static/course_v3_data/locales",
    "localization/generated/web",
    "localization/generated/miniapp",
)
# Excludes generic UI labels such as "answer", "correct", "solution" and
# "subscription" that can legitimately be localized strings.
FORBIDDEN_KEYS = frozenset({
    "answer_id", "answer_key", "correct_answer", "correct_index",
    "correct_option", "correct_option_id", "correct_option_index",
    "expected_answer", "grading_key", "is_correct", "right_answer",
})


def normalize_key(key: str) -> str:
    key = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
    return re.sub(r"[-\s]+", "_", key).lower()


def answer_key_paths(node: object, path: str = "$") -> list[str]:
    paths = []
    if isinstance(node, dict):
        for raw, value in node.items():
            key = str(raw)
            here = path + "." + key
            if normalize_key(key) in FORBIDDEN_KEYS:
                paths.append(here)
            paths.extend(answer_key_paths(value, here))
    elif isinstance(node, list):
        for value in node:
            paths.extend(answer_key_paths(value, path + "[]"))
    return paths


def audit(root: Path = ROOT, pack_roots: tuple[str, ...] = LOCALE_PACK_ROOTS) -> dict:
    examined, alerts = 0, []
    for rel in pack_roots:
        folder = root / rel
        if not folder.exists():
            continue
        if not folder.is_dir():
            alerts.append({"file": rel, "issue": "pack_root_not_directory"})
            continue
        for file in sorted(folder.rglob("*.json")):
            relative = file.relative_to(root).as_posix()
            examined += 1
            try:
                parsed = json.loads(file.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, ValueError):
                alerts.append({"file": relative, "issue": "unreadable_or_invalid_json"})
                continue
            for key_path in answer_key_paths(parsed):
                alerts.append({
                    "file": relative, "issue": "private_assessment_key",
                    "path": key_path,
                })
    return {
        "schema_version": 1,
        "status": "BLOCKED" if alerts else ("PASS" if examined else "NO_PACKS_YET"),
        "checked_json_packs": examined,
        "findings": alerts,
        "limitations": [
            "Only explicitly listed prospective locale-pack JSON roots are scanned.",
            "Does not inspect JS, external artifacts, source lessons or deployed HTTP responses.",
            "Legacy public lesson files and course entitlements require separate security review.",
            "Presence of a generic translated word 'answer' is not an answer-key leak.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print("New public locale pack guard:", report["status"],
          "scanned files:", report["checked_json_packs"],
          "findings:", len(report["findings"]))
    return int(bool(report["findings"]))


if __name__ == "__main__":
    raise SystemExit(main())

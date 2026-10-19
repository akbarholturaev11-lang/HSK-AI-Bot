#!/usr/bin/env python3
"""P0 source-side content risk summary for publicly reachable lesson paths.

Only emits known grading field NAMES, counts and stable source filenames.
Never emits JSON values, answers, Hanzi/pinyin, lesson translations or users.
The HTTP exposure observation comes from a separate staging-only status probe.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

if __package__:
    from scripts.i18n_public_bundle_guard import FORBIDDEN_KEYS, normalize_key
else:
    # CLI runs as python scripts/this_file.py (scripts/ is sys.path[0]).
    from i18n_public_bundle_guard import FORBIDDEN_KEYS, normalize_key

ROOT = Path(__file__).resolve().parents[1]
TRACKS = ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")
FILE_NAME = re.compile(r"lesson_(\d+)\.json\Z")


def _sensitive_field_counts(node: object) -> Counter:
    """Count only known assessment/solution field names; never values."""
    result = Counter()
    if isinstance(node, dict):
        for raw_key, child in node.items():
            key = normalize_key(str(raw_key))
            if key in FORBIDDEN_KEYS:
                result[key] += 1
            result.update(_sensitive_field_counts(child))
    elif isinstance(node, list):
        for item in node:
            result.update(_sensitive_field_counts(item))
    return result


def _lesson_files(root: Path, track: str) -> list[Path]:
    folder = root / "app/static/course_v3_data" / track
    if not folder.is_dir():
        raise ValueError("missing_lesson_track_dir: " + track)
    pairs = []
    for f in folder.iterdir():
        if f.is_file():
            match = FILE_NAME.fullmatch(f.name)
            if match:
                pairs.append((int(match.group(1)), f))
    if not pairs:
        raise ValueError("empty_lesson_track: " + track)
    pairs.sort()
    numbers = [x[0] for x in pairs]
    if numbers != list(range(1, len(numbers) + 1)):
        raise ValueError("lesson_numbering_changed: " + track)
    return [x[1] for x in pairs]


def run_audit(root: Path = ROOT) -> dict:
    summary = []
    total = Counter()
    by_track = {}
    private_files = 0
    sampled = []
    for track in TRACKS:
        paths = _lesson_files(root, track)
        by_track[track] = len(paths)
        first_last = {0, len(paths) - 1}
        for ordinal, filename in enumerate(paths):
            data = json.loads(filename.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("lesson_root_not_object: " + track)
            counts = _sensitive_field_counts(data)
            total.update(counts)
            if counts:
                private_files += 1
            if ordinal in first_last:
                sampled.append({
                    "track": track,
                    "lesson_number": ordinal + 1,
                    "source_file": filename.relative_to(root).as_posix(),
                    "sensitive_field_counts": dict(sorted(counts.items())),
                    "has_assessment_material": bool(counts),
                })
    return {
        "schema_version": 1,
        "status": "P0_REVIEW_PUBLIC_LESSON_ASSESSMENT_MATERIAL",
        "scanned_source_lesson_files": sum(by_track.values()),
        "lesson_counts": by_track,
        "source_files_with_assessment_fields": private_files,
        "sensitive_field_totals": dict(sorted(total.items())),
        "first_last_samples": sampled,
        "limitations": [
            "A sensitive key is assessment metadata, not proof of a private final exam or paid content classification.",
            "Source files are not remote HTTP response bodies. Staging Range GET statuses establish partial HTTP access separately.",
            "Does not classify subscriptions, quota bypass, production hosting, account entitlement, cache, or translation correctness.",
            "No lesson strings, secret answer values, tokens, or user data appear in the report.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    try:
        report = run_audit(args.root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        print("P0 lesson content risk scan FAILED: " + str(exc), file=sys.stderr)
        return 1
    print("P0 lesson content risk:",
          report["scanned_source_lesson_files"],
          "sources, with assessment keys:",
          report["source_files_with_assessment_fields"],
          "sampled first/last:", len(report["first_last_samples"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Turn heuristic P0 source findings into a bounded *manual* localization queue.

Path/feature-level classification is preliminary. This is not an AI
translation, not a runtime change, and not a declaration of confirmed bugs.
Run after i18n_source_audit.py:
  python scripts/i18n_review_queue.py --source /tmp/hsk-i18n-source-audit.json \
      --output /tmp/hsk-i18n-review-queue.json
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
AUDIT_GROUPS = {
    "miniapp_ui", "android_ui", "desktop_ui", "bot_backend",
    "lesson_content", "bundled_content", "generators",
}
AREAS = {
    "learner_frontend": ("P0", "UI controls, labels and errors need per-screen language review"),
    "learner_messaging": ("P0", "Messages and callbacks can reach learners without localization"),
    "course_content": ("P1", "Course translations and answer-identity safety require content QA"),
    "content_producer": ("P1", "Build-time locale loops and asset generation require review"),
    "admin_or_operator": ("P2", "Operator copy is not automatically learner-facing"),
    "backend_unknown": ("P2", "Separate learner responses from logs and internal API strings"),
    "bundled_data": ("P2", "Inspect existing static dictionary and phrase locale maps"),
    "no_known_surface": ("P3", "Unclassified source path; inspect manually"),
}


def provisional_area(path: str, group: str) -> str:
    """Classify by ownership, not by guessing the language of a string."""
    lowered = path.lower()
    if group == "lesson_content":
        return "course_content"
    if group == "generators":
        return "content_producer"
    if group == "bundled_content":
        return "bundled_data"
    if group in ("miniapp_ui", "android_ui", "desktop_ui"):
        if "admin" in Path(path).name.lower():
            return "admin_or_operator"
        return "learner_frontend"
    if group == "bot_backend":
        # Admin-named modules require manual validation: some of their output
        # is learner-facing, and none is *approved* by this tentative label.
        if "/admin/" in lowered or Path(path).stem.startswith("admin_") or (
            Path(path).stem == "admin"
        ):
            return "admin_or_operator"
        if path.startswith("app/bot/") or path.startswith(
            "app/services/notification_"
        ) or path.startswith("app/services/course_notification_"):
            return "learner_messaging"
        return "backend_unknown"
    return "no_known_surface"


def build_review_queue(report: dict, *, max_files: int = 75) -> dict:
    if report.get("schema_version") != 2 or not isinstance(report.get("files"), list):
        raise ValueError("requires schema_version=2 P0 source audit")
    if not isinstance(max_files, int) or max_files < 1:
        raise ValueError("max_files must be >= 1")
    totals = defaultdict(lambda: {"files": 0, "candidate_literals": 0,
                                  "missing_locale_maps": 0,
                                  "placeholder_mismatches": 0})
    ranked = []
    seen = set()
    for item in report["files"]:
        if not isinstance(item, dict):
            raise ValueError("invalid source audit file item")
        path = item.get("path")
        group = item.get("group")
        if not isinstance(path, str) or not isinstance(group, str):
            raise ValueError("invalid source audit file identity")
        if path in seen:
            raise ValueError("duplicate source audit file " + path)
        seen.add(path)
        area = provisional_area(path, group)
        priority, reason = AREAS[area]
        counts = {
            "candidate_literals": int(item.get("candidate_literals", 0)),
            "missing_locale_maps": int(item.get("missing_locale_maps", 0)),
            "placeholder_mismatches": int(item.get("placeholder_mismatches", 0)),
        }
        if any(n < 0 for n in counts.values()):
            raise ValueError("negative candidate counts")
        totals[area]["files"] += 1
        for key, amount in counts.items():
            totals[area][key] += amount
        if not any(counts.values()) and not item.get("read_error") and not item.get("parse_error"):
            continue
        ranked.append({
            "path": path,
            "group": group,
            "area": area,
            "priority": priority,
            "reason": reason,
            "manual_review": "unreviewed",
            **counts,
            "read_or_parse_error": bool(item.get("read_error") or item.get("parse_error")),
            "samples": item.get("samples", [])[:4],
        })
    ranked.sort(key=lambda x: (
        PRIORITY_RANK[x["priority"]], -int(x["read_or_parse_error"]),
        -x["missing_locale_maps"], -x["placeholder_mismatches"],
        -x["candidate_literals"], x["path"],
    ))
    return {
        "schema_version": 1,
        "status": "manual_classification_required",
        "source_scope": report.get("scope", ""),
        "scanned_files": len(seen),
        "candidate_literals": sum(t["candidate_literals"] for t in totals.values()),
        "ranked_source_files": len(ranked),
        "displayed_files": min(len(ranked), max_files),
        "areas": dict(sorted(totals.items())),
        "queue": ranked[:max_files],
        "warnings": [
            "Category is inferred from file ownership, NOT user-visible proof.",
            "A candidate is not a translation defect; some strings are admin-only, code identifiers or authored Chinese.",
            "Queue is a bounded view; review raw P0 audit for all sources.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-files", type=int, default=75)
    args = parser.parse_args()
    try:
        report = json.loads(args.source.read_text(encoding="utf-8"))
        queue = build_review_queue(report, max_files=args.max_files)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError, TypeError) as error:
        print("Review queue failed:", error, file=sys.stderr)
        return 1
    print("Candidate queue:", queue["candidate_literals"], "candidates across",
          queue["ranked_source_files"], "source files; showing",
          queue["displayed_files"], "highest-priority files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

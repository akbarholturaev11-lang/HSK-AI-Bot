#!/usr/bin/env python3
"""P3 reviewer JSON-pointer queue from existing source lessons (read-only).

Only exposes approved display-field POINTERS and source Git blob digests.
Never emits Chinese, translations, answer choices, correct answers, tokens,
paid lesson payloads, learner/account data, or arbitrary source values.
This is not a language pack or a public lesson-content endpoint.
"""
from __future__ import annotations

import argparse
from hashlib import sha1
import json
from pathlib import Path
import sys
from typing import Any

if __package__:
    from scripts.i18n_legacy_lesson_content_risk_audit import ROOT, TRACKS, _lesson_files
    from scripts.i18n_lesson_display_overlay_contract import LOCALES, _allowed
else:
    from i18n_legacy_lesson_content_risk_audit import ROOT, TRACKS, _lesson_files
    from i18n_lesson_display_overlay_contract import LOCALES, _allowed

ISSUES = ("all_locales_blank", "partially_blank", "invalid_locale_map")


def _missing_pointers(source: dict[str, Any]) -> list[dict[str, Any]]:
    """Only paths recognized by the P3 display whitelist can be serialized."""
    result: list[dict[str, Any]] = []

    def walk(node: Any, path: tuple[str, ...]) -> None:
        if isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, (*path, str(index)))
        elif isinstance(node, dict):
            if _allowed(path):
                keys_ok = set(node) == set(LOCALES)
                empty = [
                    locale for locale in LOCALES
                    if not isinstance(node.get(locale), str) or not node[locale].strip()
                ]
                if not keys_ok:
                    issue = "invalid_locale_map"
                elif len(empty) == len(LOCALES):
                    issue = "all_locales_blank"
                elif empty:
                    issue = "partially_blank"
                else:
                    return
                if issue not in ISSUES:
                    raise ValueError("unrecognized review issue")
                result.append({
                    "pointer": "/" + "/".join(path),
                    "issue": issue,
                    "locales_to_review": list(LOCALES) if not keys_ok else empty,
                })
                return
            for key, item in node.items():
                walk(item, (*path, str(key)))

    walk(source, ())
    return result


def _git_blob_sha1(raw: bytes) -> str:
    header = b"blob " + str(len(raw)).encode("ascii") + b"\0"
    return sha1(header + raw).hexdigest()


def create_review_queue(root: Path = ROOT) -> dict[str, Any]:
    """Report all 7 tracks, with no content or language text in output."""
    source_counts: dict[str, int] = {}
    reviewed_sources = []
    gap_count = 0
    locale_gaps = 0

    for track in TRACKS:
        paths = _lesson_files(root, track)
        source_counts[track] = len(paths)
        for number, file in enumerate(paths, 1):
            raw = file.read_bytes()
            try:
                source = json.loads(raw.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise ValueError("invalid lesson JSON structure") from None
            if (
                not isinstance(source, dict)
                or source.get("schema_version") != 2
                or source.get("level") != track
                or type(source.get("lesson_id")) is not int
                or source["lesson_id"] != number
                or type(source.get("part_no")) is not int
                or source["part_no"] < 1
            ):
                raise ValueError("unexpected lesson identity")
            pointers = _missing_pointers(source)
            if not pointers:
                continue
            for field in pointers:
                # Fail closed if a path is outside the explicit display whitelist.
                parts = tuple(field["pointer"].lstrip("/").split("/"))
                if not _allowed(parts) or field["issue"] not in ISSUES:
                    raise ValueError("unsafe review location")
                gap_count += 1
                locale_gaps += len(field["locales_to_review"])
            reviewed_sources.append({
                "track": track,
                "lesson_number": number,
                "source_file": file.relative_to(root).as_posix(),
                "source_git_blob_sha1": _git_blob_sha1(raw),
                "missing_display_fields": pointers,
            })

    return {
        "schema_version": 1,
        "kind": "p3_source_locale_gap_pointer_queue",
        "status": "HUMAN_REVIEW_REQUIRED" if gap_count else "NO_REVIEWED_LOCALE_GAPS",
        "source_tracks": list(TRACKS),
        "source_lessons_scanned": sum(source_counts.values()),
        "lesson_counts": source_counts,
        "affected_lessons": len(reviewed_sources),
        "affected_display_maps": gap_count,
        "locale_values_to_author": locale_gaps,
        "lessons": reviewed_sources,
        "editor_policy": [
            "Review these JSON pointers in the original approved content source.",
            "Three original translations require authored and reviewed copy; never guess from another locale.",
            "The source_git_blob_sha1 must still match before editing or applying changes.",
            "Do not change question options, correct_index, reverse_builder, Chinese, pinyin, payment, or entitlement.",
            "This report contains pointers and hashes only: never publish lesson answers as locale packs.",
        ],
        "ready_to_ship": False,
    }


def verify_existing_count_queue(queue: dict[str, Any], path: Path) -> None:
    """Prevent the earlier verified 48-lesson summary from silently drifting."""
    summary = json.loads(path.read_text(encoding="utf-8"))
    actual = [
        (record["lesson_number"], len(record["missing_display_fields"]))
        for record in queue["lessons"] if record["track"] == "nhsk2"
    ]
    expected = [
        (record["lesson_number"], record["all_empty_locale_maps"])
        for record in summary["lessons"]
    ]
    if (
        queue["affected_lessons"] != summary["affected_lessons"]
        or queue["affected_display_maps"] != summary["all_empty_three_locale_display_maps"]
        or len(actual) != queue["affected_lessons"]
        or actual != expected
        or any(field["issue"] != "all_locales_blank"
               for record in queue["lessons"]
               for field in record["missing_display_fields"])
    ):
        raise ValueError("source queue drift: reviewer summary must be updated")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--verify-count-queue", type=Path)
    args = p.parse_args()
    try:
        report = create_review_queue(ROOT)
        if args.verify_count_queue:
            verify_existing_count_queue(report, args.verify_count_queue)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, TypeError, KeyError):
        print("P3 reviewer pointer queue failed validation", file=sys.stderr)
        return 1
    print(
        "P3 reviewer pointers:", report["affected_lessons"], "lessons,",
        report["affected_display_maps"], "display maps,",
        report["locale_values_to_author"], "locale values",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

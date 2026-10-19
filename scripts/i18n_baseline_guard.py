#!/usr/bin/env python3
"""Guard the frozen P0 source baseline before changing localized HSK assets.

The baseline records Git blob IDs from an audited main snapshot. The guard
does not rewrite source files, compile locale packs, or make network requests.
A byte change is a REVIEW BLOCKER for this P0 phase, not proof of a bug.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BASELINE_FILE = ROOT / "localization/baselines/source_git_blobs.json"
REVIEWED_UI_FILE = ROOT / "localization/baselines/reviewed_ui_changes.json"
LESSON_FILE = re.compile(
    r"^app/static/course_v3_data/(hsk[1-4]|nhsk[1-3])/lesson_(\d+)\.json$"
)
EXPECTED_TRACKS = frozenset(("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3"))
SOURCE_GROUPS = frozenset((
    "lessons", "legacy_content", "ui_catalog_origins", "generators"
))


def git_blob_sha1(raw: bytes) -> str:
    """Compute Git's blob ID without Git or an external dependency."""
    header = b"blob " + str(len(raw)).encode("ascii") + b"\x00"
    return hashlib.sha1(header + raw).hexdigest()


def _safe_relative_path(path: object) -> bool:
    if not isinstance(path, str) or not path:
        return False
    posix = PurePosixPath(path)
    return not posix.is_absolute() and ".." not in posix.parts and "\\" not in path


def check_baseline(root: Path, baseline: dict, reviewed_ui: dict | None = None) -> dict:
    """Compare recorded source *bytes* and basic lesson identity, read-only."""
    if baseline.get("schema_version") != 1:
        raise ValueError("unsupported source baseline schema version")
    if not baseline.get("baseline_main_commit"):
        raise ValueError("baseline has no source commit")
    groups = baseline.get("sources")
    if not isinstance(groups, dict) or set(groups) != SOURCE_GROUPS:
        raise ValueError("baseline source groups missing or unexpected")
    rows = []
    approved_count = 0
    preexisting_target_count = 0
    approved = {}
    target_snapshot = baseline.get("preexisting_target_branch")
    target_changes = {}
    if target_snapshot is not None:
        if (not isinstance(target_snapshot, dict)
                or not isinstance(target_snapshot.get("branch"), str)
                or not target_snapshot["branch"].strip()
                or not re.fullmatch(r"[0-9a-f]{40}",
                                    str(target_snapshot.get("commit", "")))
                or not isinstance(target_snapshot.get("changes"), dict)):
            raise ValueError("invalid preexisting target branch snapshot")
        target_changes = target_snapshot["changes"]
        for rel, note in target_changes.items():
            if (not _safe_relative_path(rel) or not isinstance(note, dict)
                    or not re.fullmatch(r"[0-9a-f]{40}", str(note.get("baseline_sha1", "")))
                    or not re.fullmatch(r"[0-9a-f]{40}", str(note.get("target_sha1", "")))
                    or not isinstance(note.get("target_bytes"), int)
                    or note["target_bytes"] < 0
                    or not str(note.get("reason", "")).strip()):
                raise ValueError("malformed preexisting target branch snapshot row")
    if reviewed_ui is not None:
        if (reviewed_ui.get("schema_version") != 1
                or reviewed_ui.get("baseline_main_commit") != baseline["baseline_main_commit"]
                or not isinstance(reviewed_ui.get("files"), dict)):
            raise ValueError("invalid reviewed UI migration manifest")
        approved = reviewed_ui["files"]
        for rel, note in approved.items():
            if (not _safe_relative_path(rel) or not isinstance(note, dict)
                    or not re.fullmatch(r"[0-9a-f]{40}", str(note.get("baseline_sha1", "")))
                    or not re.fullmatch(r"[0-9a-f]{40}", str(note.get("reviewed_sha1", "")))
                    or not str(note.get("reason", "")).strip()):
                raise ValueError("malformed reviewed UI migration entry")
    if set(target_changes) & set(approved):
        raise ValueError("source path cannot use both target and reviewed UI snapshots")
    seen = set()
    group_counts = Counter()
    lesson_tracks = Counter()
    for group, entries in groups.items():
        if not isinstance(entries, list):
            raise ValueError("baseline entries must be arrays")
        for item in entries:
            if not isinstance(item, dict):
                raise ValueError("baseline row must be object")
            relative = item.get("path")
            if not _safe_relative_path(relative):
                raise ValueError("unsafe source baseline path")
            if relative in seen:
                raise ValueError("duplicate source baseline path: " + relative)
            seen.add(relative)
            target_row = target_changes.get(relative)
            group_counts[group] += 1
            expected = item.get("git_blob_sha1")
            if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{40}", expected):
                raise ValueError("invalid baseline Git blob for " + relative)
            if target_row and target_row["baseline_sha1"] != expected:
                raise ValueError("target snapshot baseline disagrees for " + relative)
            if not isinstance(item.get("bytes"), int) or item["bytes"] < 0:
                raise ValueError("invalid baseline file size for " + relative)
            lesson_match = LESSON_FILE.match(relative)
            # Track counts describe the *recorded baseline*, not only files
            # still present on disk. A missing file must remain a review
            # finding rather than turning into a misleading schema error.
            if lesson_match:
                lesson_tracks[lesson_match.group(1)] += 1
            path = root / relative
            issue = None
            if not path.is_file():
                issue = "source_missing"
            else:
                try:
                    raw = path.read_bytes()
                    current_blob = git_blob_sha1(raw)
                    is_target_snapshot = bool(
                        target_row
                        and current_blob == target_row["target_sha1"]
                        and len(raw) == target_row["target_bytes"]
                    )
                    if is_target_snapshot and current_blob != expected:
                        preexisting_target_count += 1
                    elif len(raw) != item["bytes"]:
                        issue = "byte_size_changed"
                    if current_blob != expected and not is_target_snapshot:
                        waiver = approved.get(relative)
                        if (waiver and group == "ui_catalog_origins"
                                and waiver["baseline_sha1"] == expected
                                and waiver["reviewed_sha1"] == current_blob):
                            approved_count += 1
                            issue = None
                        else:
                            issue = "source_bytes_changed"
                    if lesson_match:
                        try:
                            lesson = json.loads(raw.decode("utf-8"))
                        except (UnicodeError, json.JSONDecodeError):
                            if issue is None:
                                issue = "invalid_lesson_json"
                        else:
                            if not isinstance(lesson, dict):
                                if issue is None:
                                    issue = "invalid_lesson_shape"
                            elif (lesson.get("level") != lesson_match.group(1)
                                  or lesson.get("lesson_id") != int(lesson_match.group(2))):
                                if issue is None:
                                    issue = "lesson_identity_mismatch"
                except OSError:
                    issue = "source_unreadable"
            if issue:
                rows.append({"path": relative, "group": group, "issue": issue})

    if set(approved) - seen:
        raise ValueError("reviewed UI migration contains unknown frozen source")
    if set(target_changes) - seen:
        raise ValueError("target snapshot contains unknown frozen source")
    if any(
        row["path"] in approved and row["group"] != "ui_catalog_origins"
        for row in rows
    ):
        raise ValueError("reviewed UI migration attempts to waive non-UI source")
    source_count = baseline.get("source_count")
    if not isinstance(source_count, int) or source_count != len(seen):
        raise ValueError("baseline source count disagrees with entries")
    declared_tracks = baseline.get("track_counts")
    if not isinstance(declared_tracks, dict) or set(declared_tracks) != EXPECTED_TRACKS:
        raise ValueError("baseline track counts incomplete")
    # Counter omits keys with zero observations; the manifest lists all
    # seven tracks explicitly, including empty tracks in minimal test data.
    if {track: lesson_tracks[track] for track in EXPECTED_TRACKS} != declared_tracks:
        raise ValueError("baseline lesson file counts disagree with track counts")
    return {
        "schema_version": 1,
        "baseline_main_commit": baseline["baseline_main_commit"],
        "source_files_checked": len(seen),
        "groups": dict(sorted(group_counts.items())),
        "lesson_tracks": dict(sorted(lesson_tracks.items())),
        "review_blockers": len(rows),
        "reviewed_ui_changes": approved_count,
        "preexisting_target_changes": preexisting_target_count,
        "status": ("review_required" if rows else
                   "byte_baseline_intact_with_target_snapshot_and_reviewed_ui"
                   if preexisting_target_count and approved_count else
                   "byte_baseline_intact_with_target_snapshot"
                   if preexisting_target_count else
                   "byte_baseline_intact_with_reviewed_ui" if approved_count else
                   "byte_baseline_intact"),
        "findings": rows,
        "note": "Byte equality proves neither translation quality nor live lesson access security.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=BASELINE_FILE)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--reviewed-ui", type=Path, default=REVIEWED_UI_FILE)
    parser.add_argument("--output", type=Path, help="optional JSON report path")
    args = parser.parse_args()
    try:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        reviewed = (json.loads(args.reviewed_ui.read_text(encoding="utf-8"))
                    if args.reviewed_ui.exists() else None)
        report = check_baseline(args.root, baseline, reviewed_ui=reviewed)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print("Invalid or unreadable baseline:", exc, file=sys.stderr)
        return 1
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print("Frozen sources:", report["source_files_checked"],
          "| Lessons:", report["groups"].get("lessons", 0),
          "| Preexisting target changes:", report["preexisting_target_changes"],
          "| Review blockers:", report["review_blockers"])
    for row in report["findings"][:20]:
        print("REVIEW:", row["issue"], row["path"])
    return 1 if report["review_blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

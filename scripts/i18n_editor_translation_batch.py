#!/usr/bin/env python3
"""Private P3 multi-draft progress audit (read-only, never a publisher).

Scans existing source JSONs and local editor-supplied translation drafts.
Reports ONLY structural counts. It never serializes translation texts,
Chinese, answer values, private lesson payloads, or account data.
A completed structural audit is NOT language approval or Pro entitlement.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any

if __package__:
    from scripts.i18n_legacy_lesson_content_risk_audit import ROOT
    from scripts.i18n_lesson_locale_gap_review_queue import create_review_queue
    from scripts.i18n_editor_translation_draft import (
        MAX_DRAFT_BYTES, _source_identity, _unique_json_keys,
        validate_editor_draft,
    )
else:
    from i18n_legacy_lesson_content_risk_audit import ROOT
    from i18n_lesson_locale_gap_review_queue import create_review_queue
    from i18n_editor_translation_draft import (
        MAX_DRAFT_BYTES, _source_identity, _unique_json_keys,
        validate_editor_draft,
    )

MAX_BATCH_DRAFTS = 1500


def _private_draft_directory(root: Path, draft_dir: Path) -> Path:
    """Editor drafts must be outside the checked-out repository."""
    root = root.resolve(strict=True)
    directory = draft_dir.resolve(strict=True)
    if directory == root or directory.is_relative_to(root):
        raise ValueError("drafts inside repository are not permitted")
    if not directory.is_dir():
        raise ValueError("draft directory is missing")
    return directory


def audit_translation_draft_batch(
    draft_dir: Path,
    *,
    root: Path = ROOT,
    require_complete: bool = False,
) -> dict[str, Any]:
    """Validate any reviewed subset, always against CURRENT original sources.

    Any failed/stale/duplicate draft aborts the whole audit. There is no
    partial-success export, silent skip or target source mutation.
    """
    directory = _private_draft_directory(root, draft_dir)
    queue = create_review_queue(root)
    targets = {
        entry["source_file"]: entry
        for entry in queue["lessons"]
    }
    if len(targets) != len(queue["lessons"]):
        raise ValueError("duplicate source entry in reviewed pointer queue")
    pending = {
        source: {item["pointer"] for item in entry["missing_display_fields"]}
        for source, entry in targets.items()
    }
    expected_total = sum(len(x) for x in pending.values())
    if expected_total != queue["affected_display_maps"]:
        raise ValueError("inconsistent current source review inventory")

    files = sorted(directory.iterdir())
    if len(files) > MAX_BATCH_DRAFTS:
        raise ValueError("too many editor drafts")
    reviewed = set()
    file_count = 0
    by_track = Counter()

    for path in files:
        if path.is_symlink() or not path.is_file() or path.suffix != ".json":
            raise ValueError("unexpected draft-directory entry")
        if path.stat().st_size > MAX_DRAFT_BYTES:
            raise ValueError("oversized translation draft")
        try:
            draft = json.loads(
                path.read_text(encoding="utf-8"),
                object_pairs_hook=_unique_json_keys,
            )
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise ValueError("invalid private editor draft JSON") from None
        if not isinstance(draft, dict):
            raise ValueError("invalid private editor draft")
        source = draft.get("source_file")
        _source_identity(source)
        if source not in targets:
            raise ValueError("editor draft source is not in current gap inventory")
        if draft.get("source_git_blob_sha1") != targets[source]["source_git_blob_sha1"]:
            raise ValueError("editor draft references stale source revision")
        source_path = root / source
        result = validate_editor_draft(source_path.read_bytes(), draft)
        if result["validated_display_maps"] != len(draft["translations"]):
            raise ValueError("translation draft count mismatch")
        for item in draft["translations"]:
            key = (source, item["pointer"])
            if item["pointer"] not in pending[source] or key in reviewed:
                raise ValueError("duplicate or previously unreviewed draft pointer")
            reviewed.add(key)
            by_track[_source_identity(source)[0]] += 1
        file_count += 1

    done = len(reviewed)
    remaining = expected_total - done
    if remaining < 0:
        raise ValueError("editor draft coverage exceeds original gaps")
    if require_complete and remaining:
        raise ValueError("all current missing display fields must be reviewed")

    return {
        "schema_version": 1,
        "status": (
            "STRUCTURALLY_COMPLETE_HUMAN_LANGUAGE_REVIEW_REQUIRED"
            if remaining == 0 else "INCOMPLETE_EDITOR_TRANSLATION_DRAFTS"
        ),
        "source_lessons_scanned": queue["source_lessons_scanned"],
        "affected_source_lessons": queue["affected_lessons"],
        "missing_display_maps_at_source": expected_total,
        "required_locale_values_at_source": queue["locale_values_to_author"],
        "validated_editor_draft_files": file_count,
        "validated_display_maps": done,
        "validated_locale_values": done * 3,
        "remaining_display_maps": remaining,
        "remaining_locale_values": remaining * 3,
        "validated_maps_by_track": dict(sorted(by_track.items())),
        "ready_to_ship": False,
        "source_lessons_mutated": 0,
        "limitations": [
            "Only complete UZ/RU/TJ drafts with pinned Git blob SHA are counted.",
            "Text quality and linguistic accuracy require separate human approval.",
            "Original source lessons, scoring, auth and Pro flows are not altered.",
            "Do not publish editor drafts or report contents to public course assets.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft-dir", type=Path, required=True)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    try:
        report = audit_translation_draft_batch(
            args.draft_dir, require_complete=args.require_complete,
        )
    except (OSError, ValueError, KeyError, TypeError):
        # Do not surface editor-authored strings through exception messages.
        print("P3 draft batch REJECTED (source/draft contents withheld)", file=sys.stderr)
        return 1
    print(
        "P3 editor draft coverage:",
        report["validated_display_maps"], "/", report["missing_display_maps_at_source"],
        "maps;", report["remaining_locale_values"],
        "locale values outstanding; NOT SHIPPABLE",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

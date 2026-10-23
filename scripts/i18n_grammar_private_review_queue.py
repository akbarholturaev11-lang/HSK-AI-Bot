#!/usr/bin/env python3
"""Build a PRIVATE 136-context grammar translation review queue.

No source lessons, public artifacts, runtime code, answers or Pro data are
written. Reviewer-visible Chinese and existing grammar context are written
ONLY to a new private directory outside this checkout.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

if __package__:
    from scripts.i18n_legacy_lesson_content_risk_audit import ROOT, TRACKS, _lesson_files
    from scripts.i18n_grammar_translation_reuse_audit import (
        _blank_original_grammar_maps,
    )
    from scripts.i18n_grammar_editor_workspace import (
        _approved_context, _mirrored_grammar_pointers,
        _private_new_directory, _write_private_json,
    )
    from scripts.i18n_editor_translation_reuse import _grammar_key
    from scripts.i18n_lesson_locale_gap_review_queue import (
        _git_blob_sha1, _missing_pointers,
    )
else:
    from i18n_legacy_lesson_content_risk_audit import ROOT, TRACKS, _lesson_files
    from i18n_grammar_translation_reuse_audit import _blank_original_grammar_maps
    from i18n_grammar_editor_workspace import (
        _approved_context, _mirrored_grammar_pointers,
        _private_new_directory, _write_private_json,
    )
    from i18n_editor_translation_reuse import _grammar_key
    from i18n_lesson_locale_gap_review_queue import _git_blob_sha1, _missing_pointers


def assemble_private_review_queue(
    root: Path = ROOT,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Build in memory first, fail closed on any unsupported source gap.

    One task per exact Chinese/pinyin/grammar context. All source occurrences
    carry their own original Git blob SHA so later reuse can be revalidated.
    Blank per-lesson representative drafts are deliberately NOT valid until
    a qualified human translator supplies all three reviewed locale strings.
    """
    groups: dict[str, dict[str, Any]] = {}
    drafts: dict[str, dict[str, Any]] = {}
    scanned = 0
    affected_lessons = 0
    mirrors = 0
    occurrences = 0
    for track in TRACKS:
        for number, file in enumerate(_lesson_files(root, track), 1):
            scanned += 1
            raw = file.read_bytes()
            try:
                source = json.loads(raw.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError):
                raise ValueError("invalid original lesson JSON") from None
            original = _blank_original_grammar_maps(source, track, number)
            missing = _missing_pointers(source)
            if (len(original) != len(missing)
                    or {pointer for _, pointer in original}
                    != {item["pointer"] for item in missing}
                    or any(item["issue"] != "all_locales_blank"
                           or item["locales_to_review"] != ["uz", "ru", "tj"]
                           for item in missing)):
                raise ValueError("unclassified or partial display translation gaps")
            if not original:
                continue
            if type(source.get("part_no")) is not int or source["part_no"] < 1:
                raise ValueError("invalid original lesson part number")
            affected_lessons += 1
            relative = file.relative_to(root).as_posix()
            sha = _git_blob_sha1(raw)
            draft_name = f"{track}_lesson_{number:02d}_representatives.json"
            for _, pointer in original:
                key = _grammar_key(source, pointer)
                context = _approved_context(source, pointer)
                mirror_paths = _mirrored_grammar_pointers(source, pointer)
                grammar_number = int(pointer.split("/")[2])
                grammar = source["grammar"][grammar_number]
                occurrence = {
                    "source_file": relative,
                    "source_git_blob_sha1": sha,
                    "pointer": pointer,
                    "mirrored_paths": mirror_paths,
                }
                mirrors += len(mirror_paths)
                occurrences += 1
                if key not in groups:
                    identifier = f"G{len(groups) + 1:03d}"
                    groups[key] = {
                        "review_id": identifier,
                        "review_status": "HUMAN_REVIEW_REQUIRED",
                        "grammar": {
                            "no": grammar.get("no"),
                            "title": grammar.get("title"),
                            "title_zh": grammar.get("title_zh"),
                            "rule": grammar.get("rule"),
                        },
                        "chinese_example": context["chinese_example"],
                        "pinyin": context["pinyin"],
                        "representative_draft_file": f"drafts/{draft_name}",
                        "occurrences": [],
                    }
                    if draft_name not in drafts:
                        drafts[draft_name] = {
                            "schema_version": 1,
                            "kind": "p3_editor_translation_draft",
                            "source_file": relative,
                            "source_git_blob_sha1": sha,
                            "translations": [],
                        }
                    drafts[draft_name]["translations"].append({
                        "pointer": pointer,
                        "values": {"uz": "", "ru": "", "tj": ""},
                    })
                groups[key]["occurrences"].append(occurrence)

    queue = {
        "schema_version": 1,
        "kind": "p3_private_grammar_context_review_queue",
        "status": "HUMAN_REVIEW_REQUIRED",
        "source_lessons_scanned": scanned,
        "affected_lessons": affected_lessons,
        "missing_original_maps": occurrences,
        "unique_exact_contexts": len(groups),
        "repeated_original_occurrences": occurrences - len(groups),
        "representative_draft_files": len(drafts),
        "original_locale_cells": occurrences * 3,
        "independent_locale_cells_to_review": len(groups) * 3,
        "mirrored_card_locations": mirrors,
        "ready_to_ship": False,
        "contexts": list(groups.values()),
        "instructions": [
            "PRIVATE qualified editorial review only; contents can include gated examples.",
            "Fill only UZ/RU/TJ values in representative draft files after checking Chinese, pinyin and grammar rule.",
            "Original translation maps, assessment fields, answer options, grading and Pro access must not change.",
            "Blank drafts deliberately fail the source-SHA editor validator.",
            "For each repeated context use the existing private exact-context reuse tool after human review.",
            "No linguistic approval, publication, cache update or client runtime change is implied.",
        ],
    }
    return queue, drafts


def prepare_private_context_review(
    destination: Path, *, root: Path = ROOT,
) -> dict[str, Any]:
    folder = _private_new_directory(root, destination)
    queue, drafts = assemble_private_review_queue(root)
    if not queue["unique_exact_contexts"]:
        raise ValueError("nothing eligible for private grammar review")
    oldmask = os.umask(0o077)
    try:
        folder.mkdir(mode=0o700)
        draft_dir = folder / "drafts"
        draft_dir.mkdir(mode=0o700)
        _write_private_json(folder, "review_queue.json", queue)
        for name, draft in drafts.items():
            _write_private_json(draft_dir, name, draft)
    finally:
        os.umask(oldmask)
    return {
        "source_lessons_scanned": queue["source_lessons_scanned"],
        "affected_lessons": queue["affected_lessons"],
        "missing_original_maps": queue["missing_original_maps"],
        "unique_exact_contexts": queue["unique_exact_contexts"],
        "independent_locale_cells_to_review": queue["independent_locale_cells_to_review"],
        "private_draft_files": len(drafts),
        "ready_to_ship": False,
        "original_sources_unchanged": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        status = prepare_private_context_review(args.private_dir)
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        print("P3 private grammar review queue REJECTED (content withheld)",
              file=sys.stderr)
        return 1
    print(
        "Private P3 grammar review:", status["unique_exact_contexts"],
        "unique contexts /", status["independent_locale_cells_to_review"],
        "UZ-RU-TJ texts to author or review; NOT APPROVED",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Prepare a PRIVATE 136-context editorial backlog using existing candidate drafts.

Distinct from source-map coverage: structurally valid candidate strings are
NOT human-approved. Emit no source answers, public assets, runtime resources
or candidate values in logs. All artifacts remain outside Git checkout.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

if __package__:
    from scripts.i18n_legacy_lesson_content_risk_audit import ROOT
    from scripts.i18n_editor_context_progress import audit_private_context_progress
    from scripts.i18n_editor_translation_batch import _private_draft_directory
    from scripts.i18n_editor_translation_draft import (
        _source_identity, _unique_json_keys, _validate,
    )
    from scripts.i18n_grammar_private_review_queue import assemble_private_review_queue
    from scripts.i18n_grammar_editor_workspace import (
        _private_new_directory, _write_private_json,
    )
else:
    from i18n_legacy_lesson_content_risk_audit import ROOT
    from i18n_editor_context_progress import audit_private_context_progress
    from i18n_editor_translation_batch import _private_draft_directory
    from i18n_editor_translation_draft import _source_identity, _unique_json_keys, _validate
    from i18n_grammar_private_review_queue import assemble_private_review_queue
    from i18n_grammar_editor_workspace import _private_new_directory, _write_private_json


def prepare_editor_backlog(
    destination: Path, *, candidate_dir: Path | None = None, root: Path = ROOT,
) -> dict[str, Any]:
    """Create a candidate-aware private reviewer queue, NEVER an approval log.

    Only independent contexts with NO structurally valid translation candidate
    get a new blank representative draft. Contexts with candidate texts still
    go into the separate HUMAN_REVIEW_REQUIRED queue with private origin
    filenames/pointers, but with no candidate values copied into the queue.
    """
    target = _private_new_directory(root, destination)
    if candidate_dir is not None:
        folder = _private_draft_directory(root, candidate_dir)
        if target == folder or target.is_relative_to(folder):
            raise ValueError("review output must not be inside candidate input")
        progress = audit_private_context_progress(folder, root=root)
    else:
        folder = None
        progress = None

    queue, _ = assemble_private_review_queue(root)
    index: dict[tuple[str, str], tuple[str, str]] = {}
    for context in queue["contexts"]:
        for loc in context["occurrences"]:
            key = (loc["source_file"], loc["pointer"])
            if key in index:
                raise ValueError("duplicate original context in editor queue")
            index[key] = (context["review_id"], loc["source_git_blob_sha1"])
    if len(index) != queue["missing_original_maps"]:
        raise ValueError("incomplete original review queue")

    origins: dict[str, list[dict[str, str]]] = {}
    if folder is not None:
        for candidate_file in sorted(folder.iterdir()):
            # The full strict batch/unique-context validator already checked
            # every entry. Recheck the source SHA to prevent stale candidate
            # provenance in the private human-editor queue.
            draft = json.loads(
                candidate_file.read_text(encoding="utf-8"),
                object_pairs_hook=_unique_json_keys,
            )
            source_file = draft["source_file"]
            _source_identity(source_file)
            _, fields, actual_sha = _validate((root / source_file).read_bytes(), draft)
            for pointer, _values in fields:
                identity = index.get((source_file, pointer))
                if identity is None or identity[1] != actual_sha:
                    raise ValueError("candidate source no longer matches review context")
                origins.setdefault(identity[0], []).append({
                    "candidate_draft_file": candidate_file.name,
                    "source_file": source_file,
                    "pointer": pointer,
                })
        if len(origins) != progress["contexts_with_structural_candidate"]:
            raise ValueError("candidate context count changed during review setup")

    pending: list[dict[str, Any]] = []
    awaiting: list[dict[str, Any]] = []
    blanks: dict[str, dict[str, Any]] = {}
    for context in queue["contexts"]:
        identifier = context["review_id"]
        if identifier in origins:
            awaiting.append({
                "review_id": identifier,
                "review_status": "CANDIDATE_PENDING_HUMAN_REVIEW",
                "grammar": context["grammar"],
                "chinese_example": context["chinese_example"],
                "pinyin": context["pinyin"],
                "occurrences": context["occurrences"],
                "private_candidate_origins": origins[identifier],
                "human_language_approval_verified": False,
            })
            continue

        first = context["occurrences"][0]
        source = first["source_file"]
        track, number = _source_identity(source)
        draft_name = f"{track}_lesson_{number:02d}_pending.json"
        if draft_name not in blanks:
            blanks[draft_name] = {
                "schema_version": 1,
                "kind": "p3_editor_translation_draft",
                "source_file": source,
                "source_git_blob_sha1": first["source_git_blob_sha1"],
                "translations": [],
            }
        else:
            if (blanks[draft_name]["source_file"] != source
                    or blanks[draft_name]["source_git_blob_sha1"]
                    != first["source_git_blob_sha1"]):
                raise ValueError("inconsistent representative draft source revision")
        blanks[draft_name]["translations"].append({
            "pointer": first["pointer"],
            "values": {"uz": "", "ru": "", "tj": ""},
        })
        pending.append({
            "review_id": identifier,
            "review_status": "NEEDS_TRANSLATION_CANDIDATE",
            "grammar": context["grammar"],
            "chinese_example": context["chinese_example"],
            "pinyin": context["pinyin"],
            "occurrences": context["occurrences"],
            "private_blank_draft_file": f"drafts/{draft_name}",
            "human_language_approval_verified": False,
        })

    if len(pending) + len(awaiting) != queue["unique_exact_contexts"]:
        raise ValueError("original review contexts not completely assigned")
    if sum(len(x["translations"]) for x in blanks.values()) != len(pending):
        raise ValueError("blank representative draft count mismatch")
    if progress is not None and (
        len(awaiting) != progress["contexts_with_structural_candidate"]
        or len(pending) != progress["contexts_needing_candidate"]
    ):
        raise ValueError("review backlog disagrees with validated candidate coverage")

    backlog = {
        "schema_version": 1,
        "kind": "p3_private_candidate_aware_editor_backlog",
        "source_lessons_scanned": queue["source_lessons_scanned"],
        "original_source_maps": queue["missing_original_maps"],
        "original_locale_cells": queue["original_locale_cells"],
        "total_unique_contexts": queue["unique_exact_contexts"],
        "independent_locale_values_to_review": queue["independent_locale_cells_to_review"],
        "contexts_with_candidate_unapproved": len(awaiting),
        "contexts_needing_candidate": len(pending),
        "candidate_locale_values_unapproved": len(awaiting) * 3,
        "independent_locale_values_to_author": len(pending) * 3,
        "human_approved_contexts": 0,
        "pending_blank_draft_files": len(blanks),
        "status": "PRIVATE_HUMAN_LANGUAGE_REVIEW_REQUIRED",
        "ready_to_ship": False,
        "pending_candidate_authoring": pending,
        "existing_candidates_awaiting_human_review": awaiting,
        "instructions": [
            "Private editorial information only; grammar examples may be gated content.",
            "Candidate texts in original private files are NOT human-approved.",
            "Review Chinese, pinyin, grammar, then UZ, RU, TJ against each source.",
            "Never treat blank templates as structurally valid editor drafts.",
            "Only exact SHA-pinned context reuse may create other target drafts.",
            "Do not publish or write lesson sources, quizzes, Pro, auth or runtime packs.",
        ],
    }

    # Prepare every context and validate candidate provenance before mkdir.
    mask = os.umask(0o077)
    try:
        target.mkdir(mode=0o700)
        _write_private_json(target, "editor_backlog.json", backlog)
        if blanks:
            draft_folder = target / "drafts"
            draft_folder.mkdir(mode=0o700)
            for name, draft in sorted(blanks.items()):
                _write_private_json(draft_folder, name, draft)
    finally:
        os.umask(mask)

    return {
        "schema_version": 1,
        "total_unique_contexts": len(pending) + len(awaiting),
        "contexts_with_candidate_unapproved": len(awaiting),
        "contexts_needing_candidate": len(pending),
        "independent_locale_values_to_author": len(pending) * 3,
        "candidate_locale_values_unapproved": len(awaiting) * 3,
        "pending_blank_draft_files": len(blanks),
        "human_approved_contexts": 0,
        "original_sources_mutated": 0,
        "ready_to_ship": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--draft-dir", type=Path)
    args = parser.parse_args()
    try:
        report = prepare_editor_backlog(
            args.private_dir, candidate_dir=args.draft_dir,
        )
    except (OSError, ValueError, KeyError, TypeError, IndexError, UnicodeError):
        print("P3 private editorial backlog REJECTED (content withheld)", file=sys.stderr)
        return 1
    print(
        "Private P3 editor backlog:",
        report["contexts_with_candidate_unapproved"], "candidate contexts,",
        report["contexts_needing_candidate"], "contexts need authoring,",
        report["human_approved_contexts"], "human-approved; NOT SHIPPABLE",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

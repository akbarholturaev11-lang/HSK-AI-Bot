#!/usr/bin/env python3
"""Audit PRIVATE grammar-draft coverage by unique original context, not only lesson.

Reject conflicting repeated-context suggestions and stale or tampered drafts.
No text, answer, Pro metadata, private content or approved status is emitted.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

if __package__:
    from scripts.i18n_legacy_lesson_content_risk_audit import ROOT
    from scripts.i18n_editor_translation_batch import (
        MAX_BATCH_DRAFTS, _private_draft_directory, audit_translation_draft_batch,
    )
    from scripts.i18n_editor_translation_draft import (
        MAX_DRAFT_BYTES, _source_identity, _unique_json_keys, _validate,
    )
    from scripts.i18n_editor_grammar_mirror_integrity import attest_mirrored_grammar_preview
    from scripts.i18n_grammar_private_review_queue import assemble_private_review_queue
else:
    from i18n_legacy_lesson_content_risk_audit import ROOT
    from i18n_editor_translation_batch import (
        MAX_BATCH_DRAFTS, _private_draft_directory, audit_translation_draft_batch,
    )
    from i18n_editor_translation_draft import (
        MAX_DRAFT_BYTES, _source_identity, _unique_json_keys, _validate,
    )
    from i18n_editor_grammar_mirror_integrity import attest_mirrored_grammar_preview
    from i18n_grammar_private_review_queue import assemble_private_review_queue


def audit_private_context_progress(
    draft_dir: Path, *, root: Path = ROOT,
) -> dict[str, Any]:
    """Full-source and exact-context cross-check of private candidate drafts."""
    directory = _private_draft_directory(root, draft_dir)
    batch = audit_translation_draft_batch(directory, root=root)
    queue, _ = assemble_private_review_queue(root)

    # Only the trusted original-source inventory assigns a review context.
    index: dict[tuple[str, str], tuple[str, str]] = {}
    source_sha: dict[str, str] = {}
    for context in queue["contexts"]:
        for loc in context["occurrences"]:
            file, pointer, sha = (
                loc["source_file"], loc["pointer"], loc["source_git_blob_sha1"],
            )
            key = (file, pointer)
            if key in index or (file in source_sha and source_sha[file] != sha):
                raise ValueError("ambiguous source context identity")
            index[key] = (context["review_id"], sha)
            source_sha[file] = sha
    if len(index) != queue["missing_original_maps"]:
        raise ValueError("source grammar context inventory is incomplete")

    candidates: dict[str, dict[str, str]] = {}
    covered: set[tuple[str, str]] = set()
    mirror_maps = 0
    files = sorted(directory.iterdir())
    if len(files) > MAX_BATCH_DRAFTS:
        raise ValueError("excessive private drafts")
    for file in files:
        if (file.is_symlink() or not file.is_file()
                or file.suffix != ".json" or file.stat().st_size > MAX_DRAFT_BYTES):
            raise ValueError("unsupported private draft entry")
        try:
            draft = json.loads(
                file.read_text(encoding="utf-8"),
                object_pairs_hook=_unique_json_keys,
            )
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise ValueError("invalid private draft JSON") from None
        if type(draft) is not dict:
            raise ValueError("invalid private draft structure")
        path = draft.get("source_file")
        _source_identity(path)
        if path not in source_sha:
            raise ValueError("original lesson absent from review queue")
        source_bytes = (root / path).read_bytes()
        _, fields, actual_sha = _validate(source_bytes, draft)
        if actual_sha != source_sha[path]:
            raise ValueError("source SHA no longer matches original review queue")
        proof = attest_mirrored_grammar_preview(source_bytes, draft)
        if not proof["all_other_fields_unchanged"]:
            raise ValueError("source integrity violation")
        mirror_maps += proof["verified_mirrored_card_maps"]
        for pointer, values in fields:
            key = (path, pointer)
            if key not in index or key in covered:
                raise ValueError("unknown or repeated source grammar pointer")
            context_id, expected_sha = index[key]
            if expected_sha != actual_sha:
                raise ValueError("wrong source revision for context")
            if context_id in candidates and candidates[context_id] != values:
                raise ValueError("conflicting translations for identical grammar context")
            candidates[context_id] = dict(values)
            covered.add(key)

    if (len(covered) != batch["validated_display_maps"]
            or len(files) != batch["validated_editor_draft_files"]):
        raise ValueError("source map and independent context coverage disagree")
    uncovered = set(index) - covered
    ready_to_reuse = sum(1 for key in uncovered if index[key][0] in candidates)
    contexts_done = len(candidates)
    contexts_total = queue["unique_exact_contexts"]
    if contexts_done > contexts_total:
        raise ValueError("invalid context count")
    return {
        "schema_version": 1,
        "kind": "p3_private_grammar_context_draft_progress",
        "status": "STRUCTURAL_CANDIDATES_HUMAN_REVIEW_REQUIRED",
        "source_lessons_scanned": queue["source_lessons_scanned"],
        "total_unique_contexts": contexts_total,
        "contexts_with_structural_candidate": contexts_done,
        "contexts_needing_candidate": contexts_total - contexts_done,
        "independent_locale_values_with_candidates": contexts_done * 3,
        "independent_locale_values_remaining": (contexts_total - contexts_done) * 3,
        "source_translation_maps": len(index),
        "source_maps_with_validated_draft": len(covered),
        "source_maps_outstanding": len(uncovered),
        "source_locale_values_outstanding": len(uncovered) * 3,
        "additional_exact_context_reuse_opportunities": ready_to_reuse,
        "validated_private_draft_files": len(files),
        "verified_mirrored_card_maps": mirror_maps,
        "source_lessons_mutated": 0,
        "human_language_approval_verified": False,
        "ready_to_ship": False,
        "limitations": [
            "Context and source map coverage are different metrics.",
            "Structural and mirror verification cannot approve language quality.",
            "Conflict, stale SHA, duplicate and unknown source pointers abort the audit.",
            "Reuse requires a separately validated private target-SHA draft.",
            "No original lessons, scoring, Pro, auth, clients or public packs changed.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = audit_private_context_progress(args.draft_dir)
    except (ValueError, TypeError, KeyError, OSError, IndexError, UnicodeError):
        print("P3 context audit REJECTED (private text withheld)", file=sys.stderr)
        return 1
    print(
        "Private grammar contexts:",
        report["contexts_with_structural_candidate"], "/",
        report["total_unique_contexts"], "candidate-covered;",
        report["source_maps_with_validated_draft"], "/",
        report["source_translation_maps"], "source maps;",
        report["additional_exact_context_reuse_opportunities"],
        "reuse opportunities; HUMAN REVIEW REQUIRED",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

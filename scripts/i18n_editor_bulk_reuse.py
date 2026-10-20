#!/usr/bin/env python3
"""PRIVATE bulk draft reuse for repeated grammar contexts; never a publisher."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

if __package__:
    from scripts.i18n_legacy_lesson_content_risk_audit import ROOT
    from scripts.i18n_editor_translation_batch import _private_draft_directory
    from scripts.i18n_editor_translation_draft import (
        _source_identity, _unique_json_keys, _validate, validate_editor_draft,
    )
    from scripts.i18n_editor_context_progress import audit_private_context_progress
    from scripts.i18n_editor_grammar_mirror_integrity import attest_mirrored_grammar_preview
    from scripts.i18n_grammar_private_review_queue import assemble_private_review_queue
    from scripts.i18n_grammar_editor_workspace import _private_new_directory, _write_private_json
else:
    from i18n_legacy_lesson_content_risk_audit import ROOT
    from i18n_editor_translation_batch import _private_draft_directory
    from i18n_editor_translation_draft import (
        _source_identity, _unique_json_keys, _validate, validate_editor_draft,
    )
    from i18n_editor_context_progress import audit_private_context_progress
    from i18n_editor_grammar_mirror_integrity import attest_mirrored_grammar_preview
    from i18n_grammar_private_review_queue import assemble_private_review_queue
    from i18n_grammar_editor_workspace import _private_new_directory, _write_private_json


def prepare_private_reuse_batch(
    source_draft_dir: Path, destination: Path, *, root: Path = ROOT,
) -> dict[str, Any]:
    """Validate all candidate and target data BEFORE writing any new private files.

    Source SHA, duplicate originals, repeated-context conflicts, mirrors,
    and each planned draft are fail-closed. Already covered original pointers
    must never be emitted again, even across lesson-level draft boundaries.
    """
    inputs = _private_draft_directory(root, source_draft_dir)
    target = _private_new_directory(root, destination)
    if target == inputs or target.is_relative_to(inputs):
        raise ValueError("private output must not be inside the input draft directory")
    progress = audit_private_context_progress(inputs, root=root)
    if not progress["contexts_with_structural_candidate"]:
        raise ValueError("no validated private candidates available")
    queue, _ = assemble_private_review_queue(root)

    # Do not retain stable Chinese/content keys outside this in-memory process.
    pointer_context: dict[tuple[str, str], str] = {}
    revisions: dict[str, str] = {}
    for context in queue["contexts"]:
        for entry in context["occurrences"]:
            rel, ptr, sha = (
                entry["source_file"], entry["pointer"], entry["source_git_blob_sha1"]
            )
            if (rel, ptr) in pointer_context:
                raise ValueError("duplicated source context occurrence")
            if rel in revisions and revisions[rel] != sha:
                raise ValueError("inconsistent original Git blob SHA")
            pointer_context[(rel, ptr)] = context["review_id"]
            revisions[rel] = sha

    proposals: dict[str, dict[str, str]] = {}
    original_locations: set[tuple[str, str]] = set()
    for file in sorted(inputs.iterdir()):
        # This directory was already validated by the existing strict batch
        # auditor; repeat the source SHA check to guard concurrent edits.
        draft = json.loads(
            file.read_text(encoding="utf-8"), object_pairs_hook=_unique_json_keys
        )
        relative = draft["source_file"]
        _source_identity(relative)
        _, fields, sha = _validate((root / relative).read_bytes(), draft)
        if sha != revisions[relative]:
            raise ValueError("source revision changed during batch preparation")
        for ptr, values in fields:
            key = (relative, ptr)
            if key not in pointer_context or key in original_locations:
                raise ValueError("unknown or duplicate source context")
            context_id = pointer_context[key]
            if context_id in proposals and proposals[context_id] != values:
                raise ValueError("conflicting candidate translations")
            proposals[context_id] = dict(values)
            original_locations.add(key)
    if (len(proposals) != progress["contexts_with_structural_candidate"]
            or len(original_locations) != progress["source_maps_with_validated_draft"]):
        raise ValueError("private candidate batch changed during validation")

    by_lesson: dict[str, list[dict[str, Any]]] = {}
    for context in queue["contexts"]:
        values = proposals.get(context["review_id"])
        if values is None:
            continue
        for occurrence in context["occurrences"]:
            rel, ptr = occurrence["source_file"], occurrence["pointer"]
            if (rel, ptr) not in original_locations:
                by_lesson.setdefault(rel, []).append({
                    "pointer": ptr, "values": dict(values),
                })
    if not by_lesson:
        raise ValueError("no remaining matching grammar contexts to reuse")

    output: dict[str, dict[str, Any]] = {}
    mirror_count = 0
    created_maps = 0
    for relative, fields in sorted(by_lesson.items()):
        track, number = _source_identity(relative)
        draft = {
            "schema_version": 1,
            "kind": "p3_editor_translation_draft",
            "source_file": relative,
            "source_git_blob_sha1": revisions[relative],
            "translations": sorted(fields, key=lambda row: row["pointer"]),
        }
        raw = (root / relative).read_bytes()
        validation = validate_editor_draft(raw, draft)
        proof = attest_mirrored_grammar_preview(raw, draft)
        if (validation["validated_display_maps"] != len(fields)
                or proof["verified_original_display_maps"] != len(fields)
                or not proof["all_other_fields_unchanged"]):
            raise ValueError("mirrored grammar integrity failure")
        mirror_count += proof["verified_mirrored_card_maps"]
        created_maps += len(fields)
        name = f"{track}_lesson_{number:02d}_reused.json"
        if name in output:
            raise ValueError("duplicate output target name")
        output[name] = draft
    if created_maps != progress["additional_exact_context_reuse_opportunities"]:
        raise ValueError("reuse plan does not match independently audited count")

    # Output folder contains draft JSONs ONLY; existing private batch checker
    # can validate it without any modified format or embedded status reports.
    mask = os.umask(0o077)
    try:
        target.mkdir(mode=0o700)
        for name, draft in sorted(output.items()):
            _write_private_json(target, name, draft)
    finally:
        os.umask(mask)
    remaining = progress["source_maps_outstanding"] - created_maps
    return {
        "schema_version": 1,
        "kind": "p3_private_bulk_exact_context_reuse",
        "status": "STRUCTURAL_CANDIDATES_HUMAN_REVIEW_REQUIRED",
        "source_lessons_scanned": progress["source_lessons_scanned"],
        "candidate_unique_contexts": len(proposals),
        "unique_contexts_still_needing_candidates": progress["contexts_needing_candidate"],
        "initial_candidate_source_maps": len(original_locations),
        "new_private_draft_files": len(output),
        "additional_original_maps_reused": created_maps,
        "additional_locale_values_reused": created_maps * 3,
        "additional_mirrored_card_maps_verified": mirror_count,
        "original_source_maps_still_missing": remaining,
        "original_locale_values_still_missing": remaining * 3,
        "original_sources_mutated": 0,
        "input_drafts_mutated": 0,
        "human_language_approval_verified": False,
        "ready_to_ship": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft-dir", type=Path, required=True)
    parser.add_argument("--private-output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare_private_reuse_batch(args.draft_dir, args.private_output_dir)
    except (ValueError, TypeError, KeyError, IndexError, OSError, UnicodeError):
        print("P3 bulk private reuse REJECTED (content withheld)", file=sys.stderr)
        return 1
    print(
        "Private P3 exact-context reuse:",
        result["additional_original_maps_reused"], "extra maps,",
        result["new_private_draft_files"], "private lesson drafts;",
        result["original_locale_values_still_missing"],
        "locale values still missing; HUMAN REVIEW REQUIRED",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

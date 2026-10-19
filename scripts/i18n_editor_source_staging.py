#!/usr/bin/env python3
"""Stage SHA-verified private P3 grammar lesson-source previews outside Git.

All source drafts are verified and every lesson preview is constructed in
memory BEFORE any private output is written. Never publish these full lesson
payloads: they can include gated lessons and assessed answer fields.
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
    from scripts.i18n_editor_translation_batch import _private_draft_directory
    from scripts.i18n_editor_context_progress import audit_private_context_progress
    from scripts.i18n_editor_translation_draft import (
        _source_identity, _unique_json_keys, _validate,
    )
    from scripts.i18n_editor_grammar_mirror_integrity import (
        _approved_mirrored_preview, verify_mirrored_grammar_preview,
    )
    from scripts.i18n_grammar_editor_workspace import (
        _private_new_directory, _write_private_json,
    )
else:
    from i18n_legacy_lesson_content_risk_audit import ROOT
    from i18n_editor_translation_batch import _private_draft_directory
    from i18n_editor_context_progress import audit_private_context_progress
    from i18n_editor_translation_draft import _source_identity, _unique_json_keys, _validate
    from i18n_editor_grammar_mirror_integrity import (
        _approved_mirrored_preview, verify_mirrored_grammar_preview,
    )
    from i18n_grammar_editor_workspace import _private_new_directory, _write_private_json


def stage_private_grammar_lessons(
    draft_dir: Path, private_output: Path, *,
    root: Path = ROOT, require_complete: bool = True,
) -> dict[str, Any]:
    """Preview the ONLY allowed grammar+verified _grammar mirror mutations.

    A complete source batch is the default. --allow-partial is exclusively
    for small editorial pilots: no source lesson JSON is modified in either
    mode. The returned summary contains counts only, never lesson content.
    """
    if type(require_complete) is not bool:
        raise ValueError("invalid completeness policy")
    folder = _private_draft_directory(root, draft_dir)
    dest = _private_new_directory(root, private_output)
    if dest == folder or dest.is_relative_to(folder):
        raise ValueError("private output must not be nested inside drafts")
    progress = audit_private_context_progress(folder, root=root)
    if not progress["source_maps_with_validated_draft"]:
        raise ValueError("no valid lesson grammar candidates")
    if require_complete and (
        progress["contexts_needing_candidate"] != 0
        or progress["source_maps_outstanding"] != 0
    ):
        raise ValueError("full lesson candidate coverage is required")

    by_source: dict[str, dict[str, Any]] = {}
    for path in sorted(folder.iterdir()):
        data = json.loads(path.read_text(encoding="utf-8"),
                          object_pairs_hook=_unique_json_keys)
        source_file = data["source_file"]
        _source_identity(source_file)
        raw = (root / source_file).read_bytes()
        _, translated, sha = _validate(raw, data)
        if source_file not in by_source:
            by_source[source_file] = {
                "sha": sha, "translations": [], "seen": set(),
            }
        slot = by_source[source_file]
        if sha != slot["sha"]:
            raise ValueError("same source lesson references different revisions")
        for pointer, values in translated:
            if pointer in slot["seen"]:
                raise ValueError("duplicate original grammar pointer")
            slot["seen"].add(pointer)
            slot["translations"].append({
                "pointer": pointer, "values": dict(values),
            })

    planned: dict[str, dict[str, Any]] = {}
    mirrored = 0
    original_maps = 0
    for relative, slot in sorted(by_source.items()):
        source_bytes = (root / relative).read_bytes()
        combined_draft = {
            "schema_version": 1,
            "kind": "p3_editor_translation_draft",
            "source_file": relative,
            "source_git_blob_sha1": slot["sha"],
            "translations": sorted(slot["translations"], key=lambda x: x["pointer"]),
        }
        _, preview, _, main_count, mirror_count = (
            _approved_mirrored_preview(source_bytes, combined_draft)
        )
        proof = verify_mirrored_grammar_preview(
            source_bytes, combined_draft, preview,
        )
        if (
            not proof["all_other_fields_unchanged"]
            or proof["verified_original_display_maps"] != main_count
            or proof["verified_mirrored_card_maps"] != mirror_count
        ):
            raise ValueError("protected source field or grammar mirror integrity failure")
        planned[relative] = preview
        original_maps += main_count
        mirrored += mirror_count

    if original_maps != progress["source_maps_with_validated_draft"]:
        raise ValueError("planned map count does not match source-wide draft audit")
    if mirrored != progress["verified_mirrored_card_maps"]:
        raise ValueError("mirrored map count does not match source-wide draft audit")

    # All validation passes BEFORE private output creation. This is not a
    # content publisher, and does not modify the working tree or server.
    mask = os.umask(0o077)
    try:
        dest.mkdir(mode=0o700)
        for relative, preview in sorted(planned.items()):
            track, _ = _source_identity(relative)
            filename = Path(relative).name
            private_track = dest / track
            if not private_track.exists():
                private_track.mkdir(mode=0o700)
            _write_private_json(private_track, filename, preview)
    finally:
        os.umask(mask)

    return {
        "schema_version": 1,
        "status": "PRIVATE_SOURCE_PREVIEW_ONLY",
        "source_lessons_scanned": progress["source_lessons_scanned"],
        "original_lessons_staged": len(planned),
        "original_grammar_display_maps_staged": original_maps,
        "mirrored_grammar_display_maps_staged": mirrored,
        "locale_values_staged": (original_maps + mirrored) * 3,
        "remaining_original_grammar_maps": progress["source_maps_outstanding"],
        "original_source_files_mutated": 0,
        "graded_or_pro_fields_changed": False,
        "human_language_approval_verified": False,
        "ready_to_ship": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft-dir", type=Path, required=True)
    parser.add_argument("--private-output-dir", type=Path, required=True)
    parser.add_argument("--allow-partial", action="store_true",
                        help="Private editorial pilot only; default requires all gaps")
    args = parser.parse_args()
    try:
        report = stage_private_grammar_lessons(
            args.draft_dir, args.private_output_dir,
            require_complete=not args.allow_partial,
        )
    except (OSError, ValueError, TypeError, KeyError, IndexError, UnicodeError):
        print("P3 source integration preview REJECTED (content withheld)",
              file=sys.stderr)
        return 1
    print(
        "PRIVATE P3 lesson previews:",
        report["original_lessons_staged"], "lessons,",
        report["original_grammar_display_maps_staged"], "grammar maps,",
        report["mirrored_grammar_display_maps_staged"],
        "verified mirror maps; originals untouched; NOT SHIPPABLE",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

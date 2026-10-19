#!/usr/bin/env python3
"""Privately reuse SHA-validated, human-review-pending grammar translations.

Only exact original Chinese/pinyin + grammar no/title/title_zh/rule matches
are accepted. Input drafts MUST reside outside the checkout. Output is a new
PRIVATE source-revision-bound editor draft, never a deployable language pack.
No original lesson JSON is written, no HTTP and no Pro/grade fields are edited.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

if __package__:
    from scripts.i18n_legacy_lesson_content_risk_audit import ROOT
    from scripts.i18n_grammar_translation_reuse_audit import (
        _blank_original_grammar_maps, _source_context,
    )
    from scripts.i18n_editor_translation_draft import (
        MAX_DRAFT_BYTES, _source_identity, _unique_json_keys,
        _validate, validate_editor_draft,
    )
    from scripts.i18n_editor_grammar_mirror_integrity import (
        attest_mirrored_grammar_preview,
    )
    from scripts.i18n_grammar_editor_workspace import (
        GRAMMAR_POINTER, _git_blob_sha1, _private_new_directory,
        _write_private_json,
    )
    from scripts.i18n_lesson_locale_gap_review_queue import _missing_pointers
else:
    from i18n_legacy_lesson_content_risk_audit import ROOT
    from i18n_grammar_translation_reuse_audit import (
        _blank_original_grammar_maps, _source_context,
    )
    from i18n_editor_translation_draft import (
        MAX_DRAFT_BYTES, _source_identity, _unique_json_keys,
        _validate, validate_editor_draft,
    )
    from i18n_editor_grammar_mirror_integrity import (
        attest_mirrored_grammar_preview,
    )
    from i18n_grammar_editor_workspace import (
        GRAMMAR_POINTER, _git_blob_sha1, _private_new_directory,
        _write_private_json,
    )
    from i18n_lesson_locale_gap_review_queue import _missing_pointers


def _source_path(root: Path, track: str, number: int) -> str:
    if type(number) is not int or not (1 <= number <= 999):
        raise ValueError("invalid source lesson number")
    path = f"app/static/course_v3_data/{track}/lesson_{number:02d}.json"
    _source_identity(path)
    return path


def _grammar_key(lesson: dict[str, Any], pointer: str) -> str:
    match = GRAMMAR_POINTER.fullmatch(pointer)
    if not match:
        raise ValueError("only originally blank grammar examples may be reused")
    gi, ei = map(int, match.groups())
    try:
        group = lesson["grammar"][gi]
        example = group["examples"][ei]
        return _source_context(group, example)
    except (KeyError, TypeError, IndexError):
        raise ValueError("source grammar location no longer valid") from None


def _safe_private_input(root: Path, file: Path) -> None:
    checkout = root.resolve(strict=True)
    path = file.resolve(strict=True)
    if (path == checkout or path.is_relative_to(checkout)
            or file.is_symlink() or not file.is_file()
            or file.suffix != ".json"):
        raise ValueError("input editor drafts must be private JSON outside checkout")
    if file.stat().st_size > MAX_DRAFT_BYTES:
        raise ValueError("editor draft too large")


def prepare_translation_reuse(
    source_drafts: list[Path], track: str, lesson_number: int,
    *, root: Path = ROOT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return source-pinned private draft+metadata. Caller MUST keep them private."""
    if not isinstance(source_drafts, list) or not (1 <= len(source_drafts) <= 100):
        raise ValueError("invalid original draft count")
    target_rel = _source_path(root, track, lesson_number)
    original_target = (root / target_rel).read_bytes()
    try:
        target = json.loads(original_target.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("target lesson is not JSON") from None
    needed = _blank_original_grammar_maps(target, track, lesson_number)
    all_missing = _missing_pointers(target)
    if not needed or len(needed) != len(all_missing):
        raise ValueError("target has unsupported or no original blank locale maps")

    proposals: dict[str, dict[str, str]] = {}
    provenance: dict[str, list[dict[str, Any]]] = {}
    origins: set[str] = set()
    for file in source_drafts:
        _safe_private_input(root, file)
        try:
            original_draft = json.loads(
                file.read_text(encoding="utf-8"),
                object_pairs_hook=_unique_json_keys,
            )
        except (UnicodeError, json.JSONDecodeError):
            raise ValueError("invalid original editor draft JSON") from None
        if type(original_draft) is not dict:
            raise ValueError("invalid editor draft format")
        origin = original_draft.get("source_file")
        origin_track, origin_number = _source_identity(origin)
        origin_bytes = (root / _source_path(root, origin_track, origin_number)).read_bytes()
        source, validated, origin_sha = _validate(origin_bytes, original_draft)
        for pointer, values in validated:
            key = _grammar_key(source, pointer)
            if key in proposals and proposals[key] != values:
                raise ValueError("conflicting suggestions for identical source context")
            proposals[key] = dict(values)
            entry = {
                "source_file": origin,
                "source_git_blob_sha1": origin_sha,
                "pointer": pointer,
            }
            provenance.setdefault(key, [])
            if entry not in provenance[key]:
                provenance[key].append(entry)
        origins.add(origin)

    output_fields = []
    safe_locations = []
    for key, pointer in needed:
        if key not in proposals:
            raise ValueError("uncovered grammar context; human authoring required")
        output_fields.append({
            "pointer": pointer,
            "values": dict(proposals[key]),
        })
        safe_locations.append({
            "target_pointer": pointer,
            "origin_locations": provenance[key],
        })

    draft = {
        "schema_version": 1,
        "kind": "p3_editor_translation_draft",
        "source_file": target_rel,
        "source_git_blob_sha1": _git_blob_sha1(original_target),
        "translations": output_fields,
    }
    validation = validate_editor_draft(original_target, draft)
    proof = attest_mirrored_grammar_preview(original_target, draft)
    if (
        validation["validated_display_maps"] != len(needed)
        or proof["verified_original_display_maps"] != len(needed)
        or not proof["all_other_fields_unchanged"]
    ):
        raise ValueError("target preview integrity proof did not match")

    report = {
        "schema_version": 1,
        "kind": "p3_private_editor_translation_reuse_review",
        "source_file": target_rel,
        "source_git_blob_sha1": draft["source_git_blob_sha1"],
        "origin_draft_files_validated": len(source_drafts),
        "distinct_origin_source_lessons": len(origins),
        "target_display_maps_reused": len(needed),
        "target_locale_values_reused": len(needed) * 3,
        "target_mirrored_card_maps": proof["verified_mirrored_card_maps"],
        "original_source_unchanged": True,
        "ready_to_ship": False,
        "human_language_review_required": True,
        "source_reuse_locations": safe_locations,
        "limitations": [
            "Draft content remains UNAPPROVED even after structural checks.",
            "Source bytes, grading, answer choices, Pro and authentication are never modified.",
            "The full lesson preview is in-memory only and must never be published.",
        ],
    }
    return draft, report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-draft", type=Path, action="append", required=True)
    ap.add_argument("--target-track", type=str, required=True)
    ap.add_argument("--target-lesson", type=int, required=True)
    ap.add_argument("--private-output-dir", type=Path, required=True)
    args = ap.parse_args()
    try:
        folder = _private_new_directory(ROOT, args.private_output_dir)
        draft, report = prepare_translation_reuse(
            args.source_draft, args.target_track, args.target_lesson, root=ROOT,
        )
        oldmask = os.umask(0o077)
        try:
            folder.mkdir(mode=0o700)
            _write_private_json(folder, "editor_draft.json", draft)
            _write_private_json(folder, "reuse_provenance.json", report)
        finally:
            os.umask(oldmask)
    except (ValueError, KeyError, TypeError, OSError, IndexError):
        print("P3 private translation reuse REJECTED (all content withheld)",
              file=sys.stderr)
        return 1
    print(
        "P3 source-pinned draft created privately:",
        report["target_display_maps_reused"], "source fields,",
        report["target_locale_values_reused"], "UZ-RU-TJ values; NOT APPROVED",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

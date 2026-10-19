#!/usr/bin/env python3
"""Private local-first grammar-only overlays; no lesson source or answer writes."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

from scripts.i18n_legacy_lesson_content_risk_audit import ROOT
from scripts.i18n_editor_translation_batch import _private_draft_directory
from scripts.i18n_editor_translation_draft import _source_identity, _unique_json_keys, _validate
from scripts.i18n_editor_semantic_guard import audit_private_translation_semantics
from scripts.i18n_editor_grammar_mirror_integrity import attest_mirrored_grammar_preview
from scripts.i18n_grammar_editor_workspace import (
    _private_new_directory, _write_private_json, _mirrored_grammar_pointers,
)

LANGUAGES = ("uz", "ru", "tj")


def build_local_grammar_previews(draft_dir: Path, output_dir: Path, *,
                                 root: Path = ROOT, require_complete: bool = True):
    """Build detached locale display maps only AFTER structural/semantic guards."""
    source_dir = _private_draft_directory(root, draft_dir)
    destination = _private_new_directory(root, output_dir)
    if destination == source_dir or destination.is_relative_to(source_dir):
        raise ValueError("output cannot be nested under source drafts")
    coverage = audit_private_translation_semantics(
        source_dir, root=root, require_complete=require_complete,
    )
    grouped = {}
    for file in sorted(source_dir.iterdir()):
        draft = json.loads(file.read_text(encoding="utf-8"),
                           object_pairs_hook=_unique_json_keys)
        relative = draft["source_file"]
        track, number = _source_identity(relative)
        raw = (root / relative).read_bytes()
        original, fields, sha = _validate(raw, draft)
        proof = attest_mirrored_grammar_preview(raw, draft)
        if not proof["all_other_fields_unchanged"]:
            raise ValueError("source proof rejected")
        unit = grouped.setdefault(relative, {
            "track": track, "number": number, "sha": sha,
            "main": set(), "mirror": set(),
            "translations": {lc: {} for lc in LANGUAGES},
        })
        if unit["sha"] != sha:
            raise ValueError("source revision inconsistent")
        for pointer, values in fields:
            if pointer in unit["main"]:
                raise ValueError("duplicate grammar pointer")
            unit["main"].add(pointer)
            mirrors = _mirrored_grammar_pointers(original, pointer)
            for place in (pointer, *mirrors):
                for lc in LANGUAGES:
                    if place in unit["translations"][lc]:
                        raise ValueError("overlapping grammar mirror")
                    unit["translations"][lc][place] = values[lc]
            unit["mirror"].update(mirrors)

    main_count = sum(len(x["main"]) for x in grouped.values())
    mirror_count = sum(len(x["mirror"]) for x in grouped.values())
    if main_count != coverage["candidate_source_maps_checked"]:
        raise ValueError("source coverage changed during overlay build")
    if not main_count:
        raise ValueError("no translation candidates")
    plans = {}
    for relative, unit in grouped.items():
        for lc in LANGUAGES:
            name = lc + "/" + unit["track"] + "_lesson_" + str(unit["number"]).zfill(2) + ".json"
            plans[name] = {
                "schema_version": 1, "kind": "p3_private_local_grammar_display",
                "source_file": relative, "source_git_blob_sha1": unit["sha"],
                "locale": lc, "texts": dict(sorted(unit["translations"][lc].items())),
            }
    mask = os.umask(0o077)
    try:
        destination.mkdir(mode=0o700)
        for lc in LANGUAGES:
            (destination / lc).mkdir(mode=0o700)
        for name, obj in sorted(plans.items()):
            lc, basename = name.split("/")
            _write_private_json(destination / lc, basename, obj)
    finally:
        os.umask(mask)

    return {
        "lesson_count": len(grouped), "private_locale_packs": len(plans),
        "main_display_maps": main_count, "mirrored_display_maps": mirror_count,
        "locale_values": (main_count + mirror_count) * 3,
        "original_source_files_changed": 0, "human_review_required": False,
        "client_runtime_integrated": False, "ready_to_ship": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--draft-dir", type=Path, required=True)
    p.add_argument("--private-output-dir", type=Path, required=True)
    p.add_argument("--allow-partial", action="store_true")
    args = p.parse_args()
    try:
        result = build_local_grammar_previews(
            args.draft_dir, args.private_output_dir,
            require_complete=not args.allow_partial,
        )
    except (OSError, ValueError, TypeError, KeyError, IndexError, UnicodeError):
        print("Private P3 locale previews REJECTED (translation text withheld)", file=sys.stderr)
        return 1
    print("Private locale previews:", result["private_locale_packs"],
          "files;", result["locale_values"], "localized display values;",
          "not yet released")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

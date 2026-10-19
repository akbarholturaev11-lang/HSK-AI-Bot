#!/usr/bin/env python3
"""Create a PRIVATE local worksheet for human-authored P3 grammar translations.

The worksheet exposes only the Chinese grammar example corresponding to a
verified originally blank UZ/RU/TJ display map. This is local editorial
context, not a deployable pack or course API. Never publish these files.
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
    from scripts.i18n_legacy_lesson_content_risk_audit import ROOT, TRACKS
    from scripts.i18n_editor_translation_draft import _source_identity
    from scripts.i18n_lesson_locale_gap_review_queue import (
        _git_blob_sha1, _missing_pointers,
    )
else:
    from i18n_legacy_lesson_content_risk_audit import ROOT, TRACKS
    from i18n_editor_translation_draft import _source_identity
    from i18n_lesson_locale_gap_review_queue import (
        _git_blob_sha1, _missing_pointers,
    )

GRAMMAR_POINTER = re.compile(r"/grammar/(\d+)/examples/(\d+)/translation\Z")
MAX_EXAMPLES = 300


def _approved_context(source: dict[str, Any], pointer: str) -> dict[str, str]:
    match = GRAMMAR_POINTER.fullmatch(pointer)
    if not match:
        raise ValueError("editor worksheet is restricted to grammar-example translations")
    g, e = map(int, match.groups())
    try:
        example = source["grammar"][g]["examples"][e]
    except (KeyError, IndexError, TypeError):
        raise ValueError("missing grammar example") from None
    if type(example) is not dict:
        raise ValueError("invalid grammar example")
    zh, pinyin = example.get("zh"), example.get("pinyin", "")
    if type(zh) is not str or not zh.strip():
        raise ValueError("missing original Chinese example")
    if type(pinyin) is not str:
        raise ValueError("non-text original pinyin")
    # Explicitly exclude answer, correct_index, options, prompts, bank and Pro.
    return {"pointer": pointer, "chinese_example": zh, "pinyin": pinyin}


def _private_new_directory(root: Path, path: Path) -> Path:
    checkout = root.resolve(strict=True)
    candidate = path.resolve(strict=False)
    if candidate == checkout or candidate.is_relative_to(checkout):
        raise ValueError("private worksheet output must be outside the repository")
    if candidate.exists() or path.is_symlink():
        raise ValueError("private worksheet output folder must not exist")
    if not candidate.parent.is_dir():
        raise ValueError("private worksheet parent directory does not exist")
    return candidate


def _write_private_json(folder: Path, name: str, data: dict[str, Any]) -> None:
    # No overwrites, even under an accidental concurrent invocation.
    file = folder / name
    fd = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def prepare_grammar_editor_workspace(
    track: str, lesson_number: int, destination: Path, *, root: Path = ROOT,
) -> dict[str, Any]:
    """Write two *private* local files, leave the original source untouched.

    editor_draft.json is deliberately INVALID (empty locale strings) until a
    human writes all 3 translations. worksheet.json is only for an authorized
    content editor to inspect in their private checkout/workstation.
    """
    if track not in TRACKS or type(lesson_number) is not int or lesson_number < 1:
        raise ValueError("unsupported HSK track or lesson number")
    relative = f"app/static/course_v3_data/{track}/lesson_{lesson_number:02d}.json"
    _source_identity(relative)
    source_path = root / relative
    source_bytes = source_path.read_bytes()
    try:
        source = json.loads(source_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("malformed original lesson JSON") from None
    if (
        type(source) is not dict
        or source.get("schema_version") != 2
        or source.get("level") != track
        or type(source.get("lesson_id")) is not int
        or source["lesson_id"] != lesson_number
        or type(source.get("part_no")) is not int
        or source["part_no"] < 1
    ):
        raise ValueError("lesson identity does not match the original source")
    missing = _missing_pointers(source)
    if not (1 <= len(missing) <= MAX_EXAMPLES):
        raise ValueError("no approved incomplete display fields or excessive number")
    if any(
        item["issue"] != "all_locales_blank"
        or item["locales_to_review"] != ["uz", "ru", "tj"]
        for item in missing
    ):
        raise ValueError("partial or invalid locale maps need separate human resolution")
    contexts = [_approved_context(source, item["pointer"]) for item in missing]
    if len({item["pointer"] for item in contexts}) != len(contexts):
        raise ValueError("repeated source pointer")
    blob_sha = _git_blob_sha1(source_bytes)
    draft = {
        "schema_version": 1,
        "kind": "p3_editor_translation_draft",
        "source_file": relative,
        "source_git_blob_sha1": blob_sha,
        "translations": [
            {"pointer": item["pointer"], "values": {"uz": "", "ru": "", "tj": ""}}
            for item in contexts
        ],
    }
    worksheet = {
        "schema_version": 1,
        "kind": "p3_private_grammar_editor_worksheet",
        "source_file": relative,
        "source_git_blob_sha1": blob_sha,
        "review_status": "HUMAN_TRANSLATIONS_PENDING",
        "publishable": False,
        "examples": contexts,
        "instructions": [
            "Authorized editors only: source examples can contain gated course material.",
            "Read the Chinese example, then author and review UZ, RU and TJ separately.",
            "Fill the matching values in editor_draft.json; do not alter its source SHA or pointers.",
            "Validate privately with scripts/i18n_editor_translation_draft.py.",
            "A passing validator is not a human language approval or publish permission.",
        ],
    }
    folder = _private_new_directory(root, destination)
    previous_umask = os.umask(0o077)
    try:
        folder.mkdir(mode=0o700)
        _write_private_json(folder, "worksheet.json", worksheet)
        _write_private_json(folder, "editor_draft.json", draft)
    finally:
        os.umask(previous_umask)
    return {
        "source_file": relative,
        "source_git_blob_sha1": blob_sha,
        "pending_display_maps": len(contexts),
        "pending_locale_values": len(contexts) * 3,
        "private_files_created": 2,
        "ready_to_ship": False,
        "original_lesson_unchanged": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", required=True, choices=TRACKS)
    parser.add_argument("--lesson", required=True, type=int)
    parser.add_argument("--private-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        status = prepare_grammar_editor_workspace(
            args.track, args.lesson, args.private_dir
        )
    except (ValueError, KeyError, OSError, TypeError, IndexError):
        print("P3 private grammar worksheet REJECTED (source content withheld)",
              file=sys.stderr)
        return 1
    print(
        "Private P3 worksheet created:", status["pending_display_maps"],
        "display maps /", status["pending_locale_values"],
        "UZ-RU-TJ values awaiting human translation; NOT SHIPPABLE",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

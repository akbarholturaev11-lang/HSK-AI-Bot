#!/usr/bin/env python3
"""Private P3 translation-draft validation; no lesson writes or public packs.

Validates editor-supplied UZ/RU/TJ text for a single approved, currently blank
display pointer against the exact original Git blob SHA. Structural acceptance
is NOT translation approval, publishing permission or Pro entitlement.

CLI reads an external editor draft but prints COUNTS ONLY; original lessons
and translations are never written or serialized to CI/public artifacts.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
import unicodedata
from typing import Any

if __package__:
    from scripts.i18n_legacy_lesson_content_risk_audit import ROOT, TRACKS
    from scripts.i18n_lesson_display_overlay_contract import LOCALES, _allowed
    from scripts.i18n_lesson_locale_gap_review_queue import (
        _git_blob_sha1, _missing_pointers,
    )
else:
    from i18n_legacy_lesson_content_risk_audit import ROOT, TRACKS
    from i18n_lesson_display_overlay_contract import LOCALES, _allowed
    from i18n_lesson_locale_gap_review_queue import (
        _git_blob_sha1, _missing_pointers,
    )

DRAFT_SCHEMA = 1
MAX_VALUE_CHARS = 2000
MAX_FIELDS_PER_DRAFT = 300
MAX_DRAFT_BYTES = 2_000_000
LESSON_PATH = re.compile(
    r"app/static/course_v3_data/(hsk[1-4]|nhsk[1-3])/lesson_(\d{2,3})\.json\Z"
)
BLOB_SHA = re.compile(r"[0-9a-f]{40}\Z")


def _source_identity(path: str) -> tuple[str, int]:
    """Accept only canonical files inside the seven known, public-source dirs."""
    if not isinstance(path, str):
        raise ValueError("invalid source file path")
    match = LESSON_PATH.fullmatch(path)
    if not match or match.group(1) not in TRACKS:
        raise ValueError("invalid source file path")
    track, raw_number = match.groups()
    number = int(raw_number)
    if number < 1 or raw_number != f"{number:02d}":
        raise ValueError("noncanonical lesson number")
    return track, number


def _safe_value(value: Any) -> None:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError("empty or padded translation value")
    if len(value) > MAX_VALUE_CHARS:
        raise ValueError("translation value too long")
    if unicodedata.normalize("NFC", value) != value:
        raise ValueError("translation not NFC normalized")
    if "<" in value or ">" in value:
        raise ValueError("unsafe markup in display translation")
    if any(
        (ord(ch) < 32 and ch != "\n")
        or ord(ch) == 127
        or ch in ("\u2028", "\u2029")
        for ch in value
    ):
        raise ValueError("unsafe control character in display translation")


def _source_and_fields(
    source_bytes: bytes, source_file: str, supplied_sha: Any,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], str]:
    track, number = _source_identity(source_file)
    if not isinstance(source_bytes, bytes):
        raise ValueError("source must be original raw bytes")
    sha = _git_blob_sha1(source_bytes)
    if not isinstance(supplied_sha, str) or not BLOB_SHA.fullmatch(supplied_sha):
        raise ValueError("invalid source SHA format")
    if supplied_sha != sha:
        raise ValueError("source revision changed")
    try:
        source = json.loads(source_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("invalid source JSON") from None
    if (
        not isinstance(source, dict)
        or source.get("schema_version") != 2
        or source.get("level") != track
        or type(source.get("lesson_id")) is not int
        or source["lesson_id"] != number
        or type(source.get("part_no")) is not int
        or source["part_no"] < 1
    ):
        raise ValueError("lesson identity mismatch")
    missing = _missing_pointers(source)
    approved = {
        item["pointer"]: item
        for item in missing
        if item["issue"] == "all_locales_blank"
    }
    if len(approved) != len([x for x in missing if x["issue"] == "all_locales_blank"]):
        raise ValueError("duplicate source display pointer")
    return source, approved, sha


def _validate(
    source_bytes: bytes, draft: dict[str, Any],
) -> tuple[dict[str, Any], list[tuple[str, dict[str, str]]], str]:
    if not isinstance(draft, dict) or set(draft) != {
        "schema_version", "kind", "source_file",
        "source_git_blob_sha1", "translations",
    }:
        raise ValueError("invalid editor draft schema")
    if type(draft["schema_version"]) is not int or draft["schema_version"] != DRAFT_SCHEMA:
        raise ValueError("unsupported editor draft schema")
    if draft["kind"] != "p3_editor_translation_draft":
        raise ValueError("unsupported draft kind")
    source, available, sha = _source_and_fields(
        source_bytes, draft["source_file"], draft["source_git_blob_sha1"],
    )
    items = draft["translations"]
    if not isinstance(items, list) or not (1 <= len(items) <= MAX_FIELDS_PER_DRAFT):
        raise ValueError("invalid draft field count")
    seen = set()
    validated: list[tuple[str, dict[str, str]]] = []
    for item in items:
        if not isinstance(item, dict) or set(item) != {"pointer", "values"}:
            raise ValueError("invalid draft entry schema")
        pointer = item["pointer"]
        if type(pointer) is not str or pointer in seen or pointer not in available:
            raise ValueError("duplicate or unapproved display pointer")
        parts = tuple(pointer.lstrip("/").split("/"))
        if not pointer.startswith("/") or not _allowed(parts):
            raise ValueError("non-display path rejected")
        seen.add(pointer)
        if available[pointer]["locales_to_review"] != list(LOCALES):
            raise ValueError("nonblank source locale may not be changed")
        translations = item["values"]
        if not isinstance(translations, dict) or set(translations) != set(LOCALES):
            raise ValueError("all three original locale values are required")
        for value in translations.values():
            _safe_value(value)
        validated.append((pointer, dict(translations)))
    return source, validated, sha


def validate_editor_draft(source_bytes: bytes, draft: dict[str, Any]) -> dict[str, Any]:
    """Return metadata-only report; never echo approved *text* or source content."""
    _, validated, sha = _validate(source_bytes, draft)
    return {
        "schema_version": 1,
        "status": "STRUCTURE_VALID_HUMAN_LANGUAGE_REVIEW_REQUIRED",
        "source_file": draft["source_file"],
        "source_git_blob_sha1": sha,
        "validated_display_maps": len(validated),
        "validated_locale_values": len(validated) * len(LOCALES),
        "original_source_unchanged": True,
        "ready_to_ship": False,
    }


def preview_editor_draft(source_bytes: bytes, draft: dict[str, Any]) -> dict[str, Any]:
    """Optional IN-MEMORY preview of a copy; no write, upload or public exposure.

    Never publish/serve the returned source object: it still contains all
    original source assessment/answer fields. Only an approved editor should
    inspect this local preview.
    """
    source, fields, _ = _validate(source_bytes, draft)
    preview = deepcopy(source)
    for pointer, translations in fields:
        target: Any = preview
        for segment in pointer.lstrip("/").split("/"):
            target = target[int(segment)] if isinstance(target, list) else target[segment]
        if not isinstance(target, dict) or set(target) != set(LOCALES):
            raise ValueError("unexpected display target")
        target.update(translations)
    return preview


def _unique_json_keys(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate editor JSON key")
        result[key] = value
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--draft", type=Path, required=True,
                   help="Local editor-authored JSON draft, never checked in as course content")
    args = p.parse_args()
    try:
        if args.draft.stat().st_size > MAX_DRAFT_BYTES:
            raise ValueError("oversized draft")
        draft = json.loads(
            args.draft.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_keys,
        )
        if not isinstance(draft, dict):
            raise ValueError("invalid editor draft")
        # Source path is matched to the seven canonical track dirs, no traversal.
        _source_identity(draft.get("source_file"))
        original_path = ROOT / draft["source_file"]
        report = validate_editor_draft(original_path.read_bytes(), draft)
    except (ValueError, TypeError, KeyError, OSError, UnicodeError):
        # Suppress parser/source exceptions: they could contain editor text.
        print("P3 editor draft REJECTED (source and draft text withheld)", file=sys.stderr)
        return 1
    print(
        "P3 editor draft structurally valid:", report["validated_display_maps"],
        "display maps,", report["validated_locale_values"],
        "locale values; HUMAN language review required; NOT SHIPPABLE",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

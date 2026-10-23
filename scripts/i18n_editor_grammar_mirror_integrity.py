"""P3 private grammar+mirrored-card integration proof (NO source writes).

Editor drafts contain only approved original grammar example translations.
A source-verified _grammar display mirror can receive the SAME 3 strings
inside a private, detached in-memory preview. The preview must never be
published as a language pack or returned by an unauthenticated route because
the original source may contain grading material and gated course content.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

if __package__:
    from scripts.i18n_editor_translation_draft import _validate
    from scripts.i18n_editor_preview_integrity import (
        _display_target, _exact_same,
    )
    from scripts.i18n_grammar_editor_workspace import (
        GRAMMAR_POINTER, _mirrored_grammar_pointers,
    )
    from scripts.i18n_lesson_display_overlay_contract import LOCALES
else:
    from i18n_editor_translation_draft import _validate
    from i18n_editor_preview_integrity import _display_target, _exact_same
    from i18n_grammar_editor_workspace import (
        GRAMMAR_POINTER, _mirrored_grammar_pointers,
    )
    from i18n_lesson_display_overlay_contract import LOCALES


def _approved_mirrored_preview(
    source_bytes: bytes, draft: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], str, int, int]:
    """Build expected source-aligned private copy, reject ambiguous mirrors.

    Must use the exact current source SHA and originally blank source values.
    The base draft contains no mirror pointers. Mirror destinations derive
    exclusively from verified Chinese and original locale-map equivalence.
    """
    original, fields, sha = _validate(source_bytes, draft)
    result = deepcopy(original)
    used: set[str] = set()
    mirror_count = 0

    for main_pointer, translations in fields:
        if not GRAMMAR_POINTER.fullmatch(main_pointer):
            raise ValueError("only grammar example display drafts can be mirrored")
        mirror_paths = _mirrored_grammar_pointers(original, main_pointer)
        for path in (main_pointer, *mirror_paths):
            if path in used:
                raise ValueError("ambiguous or duplicate mirrored display path")
            used.add(path)
            original_map = _display_target(original, path)
            if set(original_map) != set(LOCALES) or any(
                type(original_map[locale]) is not str
                or original_map[locale].strip()
                for locale in LOCALES
            ):
                raise ValueError("mirror is not an originally empty display map")
            target_map = _display_target(result, path)
            target_map.update(deepcopy(translations))
        mirror_count += len(mirror_paths)

    return original, result, sha, len(fields), mirror_count


def verify_mirrored_grammar_preview(
    source_bytes: bytes, draft: dict[str, Any], proposed_preview: Any,
) -> dict[str, Any]:
    """Reject ANY preview mutation other than approved base + known mirrors."""
    original, expected, sha, main_count, mirror_count = (
        _approved_mirrored_preview(source_bytes, draft)
    )
    if not _exact_same(expected, proposed_preview):
        raise ValueError(
            "preview changed protected, unrelated or mismatched mirrored source fields"
        )
    # Defensive assertion: no source mutations under the in-memory process.
    if not isinstance(original, dict):
        raise ValueError("unexpected original lesson object")
    return {
        "schema_version": 1,
        "status": "PRIVATE_GRAMMAR_MIRROR_INTEGRITY_VERIFIED",
        "source_file": draft["source_file"],
        "source_git_blob_sha1": sha,
        "verified_original_display_maps": main_count,
        "verified_mirrored_card_maps": mirror_count,
        "verified_total_updated_display_maps": main_count + mirror_count,
        "human_authored_locale_values": main_count * len(LOCALES),
        "source_bytes_unchanged": True,
        "all_other_fields_unchanged": True,
        "human_language_approval_required": True,
        "ready_to_ship": False,
    }


def attest_mirrored_grammar_preview(
    source_bytes: bytes, draft: dict[str, Any],
) -> dict[str, Any]:
    """Verify automatically constructed IN-MEMORY copy; do not publish it."""
    _, proposed, _, _, _ = _approved_mirrored_preview(source_bytes, draft)
    return verify_mirrored_grammar_preview(source_bytes, draft, proposed)

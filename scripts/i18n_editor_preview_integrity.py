"""Private P3 editor preview integrity proof; NEVER publish the preview.

The only permitted changes are the three human-authored translations at each
source-SHA-pinned, originally blank, explicitly whitelisted display pointer.
Every other JSON field must be unchanged, including answer choices, their
order, grading, Chinese/pinyin, lessons and any embedded access flags.

This module accepts IN-MEMORY objects only. It never reads or writes files,
talks to a server, builds a client pack, or grants editorial approval.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

if __package__:
    from scripts.i18n_editor_translation_draft import (
        _validate, preview_editor_draft,
    )
    from scripts.i18n_lesson_display_overlay_contract import LOCALES
else:
    from i18n_editor_translation_draft import _validate, preview_editor_draft
    from i18n_lesson_display_overlay_contract import LOCALES


def _exact_same(first: Any, second: Any) -> bool:
    """Compare JSON trees including types (bool != int), array order and keys."""
    if type(first) is not type(second):
        return False
    if type(first) is dict:
        return (
            first.keys() == second.keys()
            and all(_exact_same(value, second[key])
                    for key, value in first.items())
        )
    if type(first) is list:
        return (
            len(first) == len(second)
            and all(_exact_same(x, y) for x, y in zip(first, second))
        )
    return first == second


def _display_target(tree: dict[str, Any], pointer: str) -> dict[str, str]:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("invalid approved display pointer")
    node: Any = tree
    for part in pointer[1:].split("/"):
        if type(node) is list:
            if not part.isascii() or not part.isdecimal() or (
                len(part) > 1 and part.startswith("0")
            ):
                raise ValueError("noncanonical display array index")
            pos = int(part)
            if pos >= len(node):
                raise ValueError("display array index out of bounds")
            node = node[pos]
        elif type(node) is dict:
            if part not in node:
                raise ValueError("missing display pointer")
            node = node[part]
        else:
            raise ValueError("invalid display object nesting")
    if type(node) is not dict or set(node) != set(LOCALES):
        raise ValueError("unexpected display locale map")
    return node


def verify_approved_preview(
    source_bytes: bytes,
    editor_draft: dict[str, Any],
    proposed_preview: Any,
) -> dict[str, Any]:
    """Fail closed on ANY other change, including answers, grading and Pro data.

    The supplied preview is never serialized or persisted. The output is
    count-only metadata; no translations or source assessment values escape.
    """
    original, approved, blob_sha = _validate(source_bytes, editor_draft)
    if type(proposed_preview) is not dict:
        raise ValueError("preview must be a source object")
    restored = deepcopy(proposed_preview)

    for pointer, required_translations in approved:
        actual_map = _display_target(restored, pointer)
        if not _exact_same(actual_map, required_translations):
            raise ValueError("preview has unapproved translation values")
        # Restore the entire original display map, without touching anything
        # else. A full-tree comparison below proves every non-display field.
        original_map = _display_target(original, pointer)
        actual_map.clear()
        actual_map.update(deepcopy(original_map))

    if not _exact_same(original, restored):
        raise ValueError("preview modified protected or unreviewed lesson data")

    return {
        "schema_version": 1,
        "status": "IN_MEMORY_DISPLAY_ONLY_INTEGRITY_VERIFIED",
        "source_file": editor_draft["source_file"],
        "source_git_blob_sha1": blob_sha,
        "verified_display_maps": len(approved),
        "verified_locale_values": len(approved) * len(LOCALES),
        "all_nonapproved_source_fields_unchanged": True,
        "source_bytes_unchanged": True,
        "ready_to_ship": False,
        "human_language_approval_required": True,
    }


def attest_editor_preview(
    source_bytes: bytes, editor_draft: dict[str, Any],
) -> dict[str, Any]:
    """Verify the local in-memory preview produced by the existing editor API."""
    proposed = preview_editor_draft(source_bytes, editor_draft)
    return verify_approved_preview(source_bytes, editor_draft, proposed)

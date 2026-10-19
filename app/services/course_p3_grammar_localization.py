"""Read-only P3 grammar translation integration for authenticated native lessons.

The canonical UZ/RU/TJ source is validated once per process. No new HTTP
endpoint, no public bundle, no per-string network fetch and no changes to
grades, Pro, auth or the original lesson files.
"""
from __future__ import annotations

from functools import lru_cache
import json
import logging
from pathlib import Path
from typing import Any

from scripts.i18n_canonical_grammar_catalog import audit_canonical_grammar
from scripts.i18n_editor_grammar_mirror_integrity import (
    _approved_mirrored_preview, verify_mirrored_grammar_preview,
)

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def _source_pinned_drafts() -> dict[str, dict[str, Any]]:
    """Resolve all 136 context hashes and 48 original source SHAs once.

    In a broken deployment, this raises and no translated content is used.
    Subsequent requests reuse validated immutable source-draft definitions.
    """
    drafts, counts = audit_canonical_grammar(ROOT)
    if (counts["contexts"], counts["original_maps"], counts["mirror_maps"]) != (
        136, 272, 136,
    ):
        raise ValueError("invalid canonical grammar source coverage")
    return drafts


def apply_native_grammar_locales(
    lesson: dict[str, Any], *, level: str, lesson_order: int,
    course_data_root: Path | None = None,
) -> dict[str, Any]:
    """Return checked translated copy, or the unchanged legacy lesson.

    Only call AFTER the existing native lesson entitlement/unlock checks.
    Only an exact original source-SHA-bound content match may be modified.
    This fallback is intentional: never break prior learners or silently
    apply stale translations to a new lesson revision.
    """
    if level != "nhsk2" or type(lesson_order) is not int or not 1 <= lesson_order <= 73:
        return lesson
    if not isinstance(lesson, dict):
        return lesson
    filename = f"lesson_{lesson_order:02d}.json"
    relative = f"app/static/course_v3_data/nhsk2/{filename}"
    try:
        draft = _source_pinned_drafts().get(relative)
        if draft is None:
            return lesson  # No original localization gap for this lesson.
        path = (course_data_root or (ROOT / "app/static/course_v3_data")) / "nhsk2" / filename
        original_bytes = path.read_bytes()
        original, preview, _, original_count, mirrors = (
            _approved_mirrored_preview(original_bytes, draft)
        )
        if lesson != original:
            raise ValueError("loaded lesson is not the original source revision")
        proof = verify_mirrored_grammar_preview(original_bytes, draft, preview)
        if (not proof["all_other_fields_unchanged"]
                or proof["verified_original_display_maps"] != original_count
                or proof["verified_mirrored_card_maps"] != mirrors):
            raise ValueError("protected source equality failed")
        return preview
    except (OSError, ValueError, TypeError, KeyError, IndexError, UnicodeError):
        # Fail to the PRE-EXISTING response rather than break study flow.
        # Never log protected Chinese text or graded answer data.
        logger.error("P3 native grammar fallback: invalid source/catalog for %s/%02d",
                     level, lesson_order)
        return lesson

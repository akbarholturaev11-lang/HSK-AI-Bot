"""Private, in-memory P3 lesson display-overlay contract (NOT a public pack builder).

This module deliberately has no file-output, HTTP, entitlement or grading API.
It prepares a narrow, source-revision-bound learner-display overlay for review.
Answer choices/tokens, scoring data and other unreviewed lesson fields stay in
the original lesson payload. Never serve this preview as a static asset.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any

LOCALES = ("uz", "ru", "tj")
OVERLAY_SCHEMA = 1

# Path segments are deliberately explicit. A "*" matches an array position.
# In particular, options, builder tokens, distractors, correct_index, answers,
# and source-language Chinese/pinyin are not eligible for display overlays.
DISPLAY_PATHS = (
    ("subtitle",),
    ("active_words", "*", "meaning"),
    ("grammar", "*", "title"),
    ("grammar", "*", "rule"),
    ("grammar", "*", "examples", "*", "translation"),
    ("dialogues", "*", "scene"),
    ("dialogues", "*", "dialogue", "*", "text"),
    ("sections", "*", "section_title"),
    ("sections", "*", "cards", "*", "prompt"),
    ("sections", "*", "cards", "*", "title"),
    ("sections", "*", "cards", "*", "explanation"),
    ("sections", "*", "cards", "*", "translation"),
    ("sections", "*", "cards", "*", "word", "meaning"),
)


def _allowed(segments: tuple[str, ...]) -> bool:
    return any(
        len(segments) == len(pattern)
        and all(expected == actual or (expected == "*" and actual.isdigit())
                for expected, actual in zip(pattern, segments))
        for pattern in DISPLAY_PATHS
    )


def _revision(source: dict[str, Any]) -> str:
    canonical = json.dumps(
        source, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def _identity(source: dict[str, Any]) -> dict[str, Any]:
    identity = {key: source.get(key) for key in ("level", "lesson_id", "part_no")}
    if not isinstance(identity["level"], str) or not identity["level"]:
        raise ValueError("invalid source level")
    for key in ("lesson_id", "part_no"):
        if type(identity[key]) is not int or identity[key] < 1:
            raise ValueError(f"invalid source {key}")
    return identity


def _display_maps(source: dict[str, Any]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}

    def walk(value: Any, path: tuple[str, ...]) -> None:
        if isinstance(value, list):
            for i, item in enumerate(value):
                walk(item, (*path, str(i)))
        elif isinstance(value, dict):
            if _allowed(path):
                if set(value) != set(LOCALES):
                    raise ValueError("display locale parity: " + "/".join(path))
                if any(not isinstance(value[locale], str) or not value[locale].strip()
                       for locale in LOCALES):
                    raise ValueError("empty or non-text locale: " + "/".join(path))
                result["/" + "/".join(path)] = value
                return
            for name, item in value.items():
                if "/" in name or "~" in name:
                    # No ambiguous path encoding for this proof of contract.
                    continue
                walk(item, (*path, name))

    walk(source, ())
    return result


def build_display_overlay(source: dict[str, Any], locale: str) -> dict[str, Any]:
    """Create a detached in-memory preview; do not publish or cache it."""
    if locale not in LOCALES:
        raise ValueError("unsupported locale; never silently fall back")
    if not isinstance(source, dict) or source.get("schema_version") != 2:
        raise ValueError("unsupported source lesson schema")
    identity = _identity(source)
    maps = _display_maps(source)
    if not maps:
        raise ValueError("no reviewed display fields")
    return {
        "overlay_schema": OVERLAY_SCHEMA,
        "source": {**identity, "sha256": _revision(source)},
        "locale": locale,
        "texts": {path: values[locale] for path, values in sorted(maps.items())},
    }


def apply_display_overlay(source: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with reviewed display strings only; reject all stale packs."""
    if not isinstance(overlay, dict) or set(overlay) != {
        "overlay_schema", "source", "locale", "texts",
    } or overlay["overlay_schema"] != OVERLAY_SCHEMA:
        raise ValueError("unsupported overlay contract")
    locale = overlay["locale"]
    if locale not in LOCALES:
        raise ValueError("unsupported locale")
    if overlay["source"] != {**_identity(source), "sha256": _revision(source)}:
        raise ValueError("source revision or lesson identity mismatch")
    expected = _display_maps(source)
    texts = overlay["texts"]
    if not isinstance(texts, dict) or set(texts) != set(expected):
        raise ValueError("missing or unreviewed display path")
    result = deepcopy(source)
    for path, value in texts.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError("invalid replacement display text")
        parts = path.lstrip("/").split("/")
        target: Any = result
        for part in parts:
            target = target[int(part)] if isinstance(target, list) else target[part]
        target[locale] = value
    return result

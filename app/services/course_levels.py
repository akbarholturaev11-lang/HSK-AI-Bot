from __future__ import annotations

from dataclasses import dataclass


TRACK_HSK20 = "hsk20"
TRACK_HSK30 = "hsk30"


@dataclass(frozen=True)
class CourseLevelSpec:
    key: str
    track: str
    band: int
    content_level: str
    selectable: bool = True
    entry_alias: bool = False


_LEVEL_SPECS = (
    CourseLevelSpec(
        key="beginner",
        track=TRACK_HSK20,
        band=1,
        content_level="hsk1",
        entry_alias=True,
    ),
    CourseLevelSpec(key="hsk1", track=TRACK_HSK20, band=1, content_level="hsk1"),
    CourseLevelSpec(key="hsk2", track=TRACK_HSK20, band=2, content_level="hsk2"),
    CourseLevelSpec(key="hsk3", track=TRACK_HSK20, band=3, content_level="hsk3"),
    CourseLevelSpec(key="hsk4", track=TRACK_HSK20, band=4, content_level="hsk4"),
    CourseLevelSpec(
        key="nbeginner",
        track=TRACK_HSK30,
        band=1,
        content_level="nhsk1",
        entry_alias=True,
    ),
    CourseLevelSpec(key="nhsk1", track=TRACK_HSK30, band=1, content_level="nhsk1"),
    CourseLevelSpec(key="nhsk2", track=TRACK_HSK30, band=2, content_level="nhsk2"),
    CourseLevelSpec(key="nhsk3", track=TRACK_HSK30, band=3, content_level="nhsk3"),
    CourseLevelSpec(key="nhsk4", track=TRACK_HSK30, band=4, content_level="nhsk4"),
)

COURSE_LEVEL_SPECS = {spec.key: spec for spec in _LEVEL_SPECS}

# Legacy renderer aliases are intentionally not standalone course bands.
_RENDER_ALIASES = {
    "az0": "hsk1",
    "hsk4a": "hsk4",
    "hsk4b": "hsk4",
}


def level_spec(value: str | None) -> CourseLevelSpec | None:
    key = str(value or "").strip().lower()
    return COURSE_LEVEL_SPECS.get(key)


def is_hsk30_level(value: str | None) -> bool:
    spec = level_spec(value)
    return bool(spec and spec.track == TRACK_HSK30)


def content_level(value: str | None, *, default: str = "hsk1") -> str:
    raw = str(value or "").strip().lower()
    spec = COURSE_LEVEL_SPECS.get(raw)
    if spec:
        return spec.content_level
    alias = _RENDER_ALIASES.get(raw)
    if alias:
        return alias
    return default


def legacy_content_levels() -> tuple[str, ...]:
    return tuple(
        spec.content_level
        for spec in _LEVEL_SPECS
        if spec.track == TRACK_HSK20 and not spec.entry_alias
    )


def hsk30_content_levels() -> tuple[str, ...]:
    return tuple(
        spec.content_level
        for spec in _LEVEL_SPECS
        if spec.track == TRACK_HSK30 and not spec.entry_alias
    )


def onboarding_levels(*, hsk30_enabled: bool = False) -> frozenset[str]:
    keys = {
        spec.key
        for spec in _LEVEL_SPECS
        if spec.selectable and spec.track == TRACK_HSK20
    }
    if hsk30_enabled:
        keys.update(
            spec.key
            for spec in _LEVEL_SPECS
            if spec.selectable and spec.track == TRACK_HSK30
        )
    return frozenset(keys)


def normalize_legacy_content_level(value: str | None, *, default: str = "hsk1") -> str:
    normalized = content_level(value, default=default)
    return normalized if normalized in legacy_content_levels() else default


def render_level(value: str | None, lesson_order: int | None = None) -> str:
    normalized = content_level(value)
    if normalized == "hsk4":
        return "hsk4b" if int(lesson_order or 0) > 10 else "hsk4a"
    return normalized


def next_level(value: str | None) -> str | None:
    spec = level_spec(value)
    if not spec or spec.entry_alias or spec.band >= 4:
        return None
    prefix = "nhsk" if spec.track == TRACK_HSK30 else "hsk"
    return f"{prefix}{spec.band + 1}"

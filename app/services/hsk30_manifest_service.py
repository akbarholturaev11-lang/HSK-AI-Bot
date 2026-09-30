from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


_DATA_ROOT = Path("app/static/course_v3_data")


@dataclass(frozen=True)
class Hsk30CourseManifest:
    level: str
    lesson_count: int
    first_lesson_order: int
    version: int


class Hsk30ManifestService:
    @staticmethod
    def load(level: str) -> Hsk30CourseManifest | None:
        normalized = str(level or "").strip().lower()
        if not normalized.startswith("nhsk"):
            return None
        path = _DATA_ROOT / normalized / "manifest.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        try:
            lesson_count = int(payload.get("lesson_count") or 0)
            first_lesson_order = int(payload.get("first_lesson_order") or 1)
            version = int(payload.get("version") or 1)
        except (TypeError, ValueError):
            return None
        if (
            str(payload.get("level") or "").strip().lower() != normalized
            or lesson_count <= 0
            or first_lesson_order <= 0
        ):
            return None
        return Hsk30CourseManifest(
            level=normalized,
            lesson_count=lesson_count,
            first_lesson_order=first_lesson_order,
            version=version,
        )

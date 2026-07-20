"""parts_manifest.json o'quvchisi — Course v3 darslari mini-qismlarga bo'lingan.

Har HSK darsligi darsi bir nechta qisqa mini-darsga (qismga) bo'lingan; qismlar
darajada TEKIS raqamlanadi (completed_lessons_count endi qismlarni sanaydi).
Manba: scripts/gen_course_v3_from_seed.py yozadigan
app/static/course_v3_data/parts_manifest.json. Fayl faqat deploy bilan
o'zgaradi, shuning uchun bir marta o'qib keshda saqlaymiz.
"""

from __future__ import annotations

import json
from pathlib import Path

_MANIFEST_PATH = Path("app/static/course_v3_data/parts_manifest.json")
_cache: dict | None = None


def _manifest() -> dict:
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — manifest yo'q bo'lsa chegara o'chadi
            _cache = {}
    return _cache


def _level_data(level: str) -> dict:
    return _manifest().get(str(level or "").strip().lower()) or {}


def total_parts(level: str) -> int:
    """Darajadagi jami mini-darslar (qismlar) soni; manifest bo'lmasa 0."""
    return int(_level_data(level).get("total_parts") or 0)


def source_lesson_for_part(level: str, part_n: int) -> int:
    """Flat qism raqami -> asl HSK darsligi darsi raqami (1-based).

    Legacy tizimlar (challenge/practice savol banki) hali darslik darsi
    tartibida ishlaydi — qism raqamini shunga aylantirish uchun.
    Manifest bo'lmasa 0 qaytadi (chaqiruvchi eski xatti-harakatga qaytsin)."""
    part_n = int(part_n or 0)
    lessons = _level_data(level).get("lessons") or []
    for les in lessons:
        parts = les.get("parts") or []
        if parts and part_n <= int(parts[-1]):
            return int(les.get("src") or 0)
    if lessons and part_n > 0:
        return int(lessons[-1].get("src") or 0)
    return 0

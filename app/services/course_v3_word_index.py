"""So'z -> qaysi bandda va qaysi qismda O'RGATILGAN degan indeks.

Legacy HSK 2.0 va HSK 3.0 uchun gate artefaktlari alohida:
- lesson_gate.js -> window.HSK_WORD_GATE
- lesson_gate_hsk30.js -> window.HSK30_WORD_GATE

Server va klient bir xil gate'ni ishlatishi shart. Shunda recognition /
pronunciation mashqlarida klient ochgan so'zni server "hali yopiq" demaydi.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from app.services.course_levels import content_level, legacy_content_levels
from app.services.course_v3_parts import total_parts
from app.services.course_v3_vocab import words_for_level


logger = logging.getLogger(__name__)

_DATA_DIR = Path("app/static/course_v3_data")
_LEGACY_LEVELS = legacy_content_levels()
_HSK30_LEVELS = ("nhsk1", "nhsk2", "nhsk3")
_GATE_SPECS = {
    "hsk20": (
        _DATA_DIR / "lesson_gate.js",
        re.compile(r"window\.HSK_WORD_GATE\s*=\s*(\{.*?\})\s*;", re.S),
        _LEGACY_LEVELS,
    ),
    "hsk30": (
        _DATA_DIR / "lesson_gate_hsk30.js",
        re.compile(r"window\.HSK30_WORD_GATE\s*=\s*(\{.*?\})\s*;", re.S),
        _HSK30_LEVELS,
    ),
}

# track -> {zh: (band_number, first_flat_part)}
_cache: dict[str, dict[str, tuple[int, int]]] = {}


def normalize_level(value: str | None) -> str:
    normalized = content_level(value, default="hsk1")
    if normalized in _LEGACY_LEVELS or normalized in _HSK30_LEVELS:
        return normalized
    return "hsk1"


def _track(level: str | None) -> str:
    return "hsk30" if normalize_level(level).startswith("nhsk") else "hsk20"


def level_number(level: str | None) -> int:
    normalized = normalize_level(level)
    match = re.search(r"(\d+)$", normalized)
    return int(match.group(1)) if match else 1


def _vocabulary(levels: tuple[str, ...]) -> set[str]:
    words: set[str] = set()
    for level in levels:
        words |= {str(item.get("zh") or "") for item in words_for_level(level)}
    words.discard("")
    return words


def _index(level: str | None = None) -> dict[str, tuple[int, int]]:
    track = _track(level)
    if track in _cache:
        return _cache[track]

    gate_path, gate_pattern, levels = _GATE_SPECS[track]
    index: dict[str, tuple[int, int]] = {}
    try:
        raw = gate_path.read_text(encoding="utf-8")
        match = gate_pattern.search(raw)
        gate = json.loads(match.group(1)) if match else {}
    except Exception:  # noqa: BLE001
        logger.exception("%s could not be read", gate_path.name)
        gate = {}

    vocabulary = _vocabulary(levels)
    for zh, position in gate.items():
        if zh not in vocabulary:
            continue
        if not isinstance(position, (list, tuple)) or len(position) < 2:
            continue
        try:
            level_no, part_no = int(position[0]), int(position[1])
        except (TypeError, ValueError):
            continue
        if level_no < 1 or part_no < 1:
            continue
        index[str(zh)] = (level_no, part_no)

    _cache[track] = index
    return index


def index_size(level: str | None = None) -> int:
    """Diagnostika uchun: berilgan track indeksidagi so'zlar soni."""
    return len(_index(level))


def word_position(zh: str, level: str | None = None) -> tuple[int, int] | None:
    """So'z qaysi band/qismda o'rgatilgan. Level track'ni tanlaydi."""
    return _index(level).get(str(zh or "").strip())


def taught_words(
    level: str | None,
    current_part: int,
    *,
    single_char: bool = False,
    min_pool: int = 0,
) -> list[tuple[str, int]]:
    """O'quvchi ko'rgan so'zlar: (zh, flat_part), yangisi birinchi.

    Joriy banddagi part <= current_part so'zlar, keyin shu track'dagi quyi
    bandlarning hammasi qo'shiladi. min_pool yetmasa ayni band ichida
    oldinga qarab kengayadi; boshqa track'ga o'tmaydi.
    """
    normalized = normalize_level(level)
    level_no = level_number(normalized)
    try:
        current_part = max(1, int(current_part or 1))
    except (TypeError, ValueError):
        current_part = 1

    index = _index(normalized)
    candidates = (
        {
            zh: position
            for zh, position in index.items()
            if len(zh) == 1
        }
        if single_char
        else index
    )

    base = sorted(
        ((zh, part) for zh, (lv, part) in candidates.items() if lv < level_no),
        key=lambda item: (-item[1], item[0]),
    )

    def own_words(limit_part: int) -> list[tuple[str, int]]:
        return sorted(
            (
                (zh, part)
                for zh, (lv, part) in candidates.items()
                if lv == level_no and part <= limit_part
            ),
            key=lambda item: (-item[1], item[0]),
        )

    own = own_words(current_part)
    if min_pool > 0:
        ceiling = total_parts(normalized) or current_part
        limit_part = current_part
        while len(own) + len(base) < min_pool and limit_part < ceiling:
            limit_part += 1
            own = own_words(limit_part)

    return own + base

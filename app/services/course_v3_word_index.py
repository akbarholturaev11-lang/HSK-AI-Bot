"""So'z -> qaysi bandda va qaysi qismda O'RGATILGAN degan indeks.

Manba ataylab `lesson_gate.js` — dars fayllaridagi `active_words` EMAS.
Ikkalasi bir xil ko'rinsa ham, hsk4 da **30 ta so'zda farq qiladi**: gate
ularni ancha erta ochadi (masalan 使 gate'da 65-qism, dars faylida 157-qism).
Sabab: generator gate'ni `plan[...]["parts"][*]["chunk"]` bo'yicha yozadi,
`active_words` esa boshqa ro'yxat. Klient (`course_v3_recognition.html`,
`course_v3_pronunciation.html`) aynan shu gate bilan ishlaydi, shuning uchun
server ham shu artefaktni o'qiydi — shunda ikkalasi qurilishi bo'yicha doim
mos keladi va o'quvchi klient ochgan so'zni server "hali yopiq" demaydi.

Gate'da 1247 yozuv bor, `course_v3_vocab` da 1227 so'z. Farq — 20 ta atoqli
ot (安娜, 李月, 王方 ...), ularni `course_v3_vocab` allaqachon filtrlagan.
Shu sababli indeks vocab bilan kesishtiriladi.

Fayl faqat deploy bilan o'zgaradi, shuning uchun bir marta o'qib keshda
saqlanadi — `course_v3_parts.py` va `course_v3_vocab.py` kabi.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from app.services.course_v3_parts import total_parts
from app.services.course_v3_vocab import words_for_level


logger = logging.getLogger(__name__)

_GATE_PATH = Path("app/static/course_v3_data/lesson_gate.js")
_GATE_PATTERN = re.compile(r"window\.HSK_WORD_GATE\s*=\s*(\{.*?\})\s*;", re.S)
_LEVELS = ("hsk1", "hsk2", "hsk3", "hsk4")

# Kurs oqimidagi bilan bir xil normallashtirish.
_LEVEL_FALLBACK = {
    "beginner": "hsk1",
    "az0": "hsk1",
    "hsk1": "hsk1",
    "hsk2": "hsk2",
    "hsk3": "hsk3",
    "hsk4": "hsk4",
    "hsk4a": "hsk4",
    "hsk4b": "hsk4",
}

# {zh: (hsk_level, first_part)}
_cache: dict[str, tuple[int, int]] | None = None


def normalize_level(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    return _LEVEL_FALLBACK.get(normalized, "hsk1")


def level_number(level: str | None) -> int:
    normalized = normalize_level(level)
    try:
        return int(normalized[3:]) or 1
    except (TypeError, ValueError):
        return 1


def _vocabulary() -> set[str]:
    words: set[str] = set()
    for level in _LEVELS:
        words |= {str(item.get("zh") or "") for item in words_for_level(level)}
    words.discard("")
    return words


def _index() -> dict[str, tuple[int, int]]:
    global _cache
    if _cache is not None:
        return _cache

    index: dict[str, tuple[int, int]] = {}
    try:
        raw = _GATE_PATH.read_text(encoding="utf-8")
        match = _GATE_PATTERN.search(raw)
        gate = json.loads(match.group(1)) if match else {}
    except Exception:  # noqa: BLE001 — indeks yo'q bo'lsa mashq eski yo'ldan ketadi
        logger.exception("lesson_gate.js could not be read")
        gate = {}

    vocabulary = _vocabulary()
    for zh, position in gate.items():
        if zh not in vocabulary:
            # Atoqli ot yoki kurs lug'atidan tashqaridagi yozuv.
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

    _cache = index
    return _cache


def index_size() -> int:
    """Diagnostika uchun: indeksdagi so'zlar soni."""
    return len(_index())


def word_position(zh: str) -> tuple[int, int] | None:
    """So'z qaysi bandda va qaysi qismda o'rgatilgan. Topilmasa None."""
    return _index().get(str(zh or "").strip())


def taught_words(
    level: str | None,
    current_part: int,
    *,
    single_char: bool = False,
    min_pool: int = 0,
) -> list[tuple[str, int]]:
    """O'quvchi KO'RGAN so'zlar: `(zh, part)`, yangisi birinchi.

    Joriy banddagi `part <= current_part` so'zlar, so'ng quyi bandlarning
    hammasi (ular to'liq ochiq — klient gate'i ham shunday ishlaydi).

    `min_pool` — kengaytirish chegarasi. Bu MAJBURIY: o'lchandi, HSK1 ning
    1-qismida atigi **3 ta** so'z bor va 10 savollik mashq qurib bo'lmaydi.
    Klient ham xuddi shunday oldinga qarab kengaytiradi; server undan
    torroq bo'lsa mashq bo'sh chiqadi. Chegara — bandning haqiqiy qism soni
    (62/71/108/180), klientdagi o'lik `40` emas.
    """
    normalized = normalize_level(level)
    level_no = level_number(normalized)
    try:
        current_part = max(1, int(current_part or 1))
    except (TypeError, ValueError):
        current_part = 1

    index = _index()
    if single_char:
        candidates = {
            zh: position
            for zh, position in index.items()
            if len(zh) == 1
        }
    else:
        candidates = index

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

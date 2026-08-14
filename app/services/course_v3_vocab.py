"""Course v3 dars fayllaridagi `active_words` o'quvchisi.

`app/static/course_v3_data/<level>/lesson_*.json` ichida har bir dars uchun
`active_words` ro'yxati bor: xitoycha yozuv, pinyin va uch tilda ma'no.
Bu tayyor lug'at QA rejimining kirish savoli uchun manba bo'ladi — ilgari
qattiq yozilgan 3 ta so'z ishlatilardi va savollar tez takrorlanardi.

Fayllar faqat deploy bilan o'zgaradi, shuning uchun `course_v3_parts.py`
kabi bir marta o'qib keshda saqlaymiz.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


_DATA_DIR = Path("app/static/course_v3_data")
_LEVELS = ("hsk1", "hsk2", "hsk3", "hsk4")

# Dialoglardagi personaj ismlari ham `active_words` ichida keladi
# (王方 "Wang Fang", 花花 "Huahua"). "Bu so'z nima degani?" degan savol
# ular uchun ma'nosiz, shuning uchun chiqarib tashlanadi.
_PROPER_POS = {"proper noun", "proper n.", "name", "place"}
# `pn.` aralash: 中国 "Xitoy" ham, 李月 "Li Yue (ism)" ham shu belgida.
# Faqat qavs ichida ism deb izohlanganlarini filtrlaymiz.
_NAME_HINT = re.compile(r"\(\s*(ism|имя|ном)|familiya|фамилия|насаб", re.IGNORECASE)

# Kurs oqimidagi bilan bir xil: `beginner` uchun alohida dars fayli yo'q,
# hsk1 dan boshlanadi.
_LEVEL_FALLBACK = {
    "beginner": "hsk1",
    "az0": "hsk1",
    "hsk1": "hsk1",
    "hsk2": "hsk2",
    "hsk3": "hsk3",
    "hsk4": "hsk4",
}

_cache: dict[str, list[dict]] | None = None


def _is_proper_name(item: dict) -> bool:
    pos = (item.get("pos") or "").strip().lower()
    if pos in _PROPER_POS:
        return True
    if pos == "pn.":
        meaning = item.get("meaning") or {}
        text = " ".join(str(meaning.get(k, "")) for k in ("uz", "ru", "tj"))
        return bool(_NAME_HINT.search(text))
    return False


def _normalize_level(level: str | None) -> str:
    raw = str(level or "").strip().lower().replace(" ", "").replace("_", "")
    return _LEVEL_FALLBACK.get(raw, "hsk1")


def _load() -> dict[str, list[dict]]:
    """level -> [{"zh", "pinyin", "meaning": {"uz","ru","tj"}}]"""
    global _cache
    if _cache is not None:
        return _cache

    data: dict[str, list[dict]] = {}
    for level in _LEVELS:
        words: list[dict] = []
        seen: set[str] = set()
        try:
            files = sorted((_DATA_DIR / level).glob("lesson_*.json"))
        except Exception:  # noqa: BLE001 — papka yo'q bo'lsa bo'sh qoladi
            files = []
        for path in files:
            try:
                lesson = json.loads(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001 — buzuq fayl butun bazani yiqitmasin
                continue
            for item in lesson.get("active_words") or []:
                zh = (item.get("zh") or "").strip()
                pinyin = (item.get("pinyin") or "").strip()
                meaning = item.get("meaning") or {}
                if not zh or not pinyin or not isinstance(meaning, dict):
                    continue
                if not all(meaning.get(k) for k in ("uz", "ru", "tj")):
                    continue
                if _is_proper_name(item):
                    continue
                if zh in seen:
                    continue
                seen.add(zh)
                words.append({"zh": zh, "pinyin": pinyin, "meaning": meaning})
        data[level] = words

    _cache = data
    return _cache


def words_for_level(level: str | None) -> list[dict]:
    """Darajaga mos so'zlar. Fayl topilmasa quyi darajaga tushadi."""
    normalized = _normalize_level(level)
    data = _load()

    words = data.get(normalized) or []
    if words:
        return words

    # Fayllar yetishmasa pastdagi darajalarni sinaymiz, oxirida bo'sh ro'yxat.
    order = list(_LEVELS)
    if normalized in order:
        for fallback in reversed(order[: order.index(normalized)]):
            if data.get(fallback):
                return data[fallback]
    return []


def level_word_counts() -> dict[str, int]:
    """Diagnostika uchun: daraja bo'yicha so'zlar soni."""
    return {level: len(words) for level, words in _load().items()}

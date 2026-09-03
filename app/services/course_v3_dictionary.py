"""Ieroglif lug'ati manbasi.

Mini App lug'ati (`hsk-lugat.html`) `app/static/hsk-words.js` ichidagi `WORDS`
ro'yxatini o'qiydi. Native klientlar ham AYNAN shu ro'yxatni ko'rsatishi kerak,
aks holda bir xil mahsulotda ikki xil lug'at paydo bo'ladi.

Fayl JavaScript bo'lgani uchun uni nusxalash o'rniga shu yerda o'qiymiz:
`const WORDS=[...]` prefiksi olib tashlanadi, qolgani JSON. Fayl faqat deploy
bilan o'zgaradi, shuning uchun `course_v3_vocab.py` kabi bir marta keshlanadi.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


_SOURCE = Path("app/static/hsk-words.js")

# `const WORDS=[ ... ];` — massivning o'zi to'g'ri JSON.
_ARRAY = re.compile(r"const\s+WORDS\s*=\s*(\[.*\])\s*;?\s*\Z", re.S)

_LANGUAGES = ("uz", "ru", "tj")
_DEFAULT_LANGUAGE = "ru"

_cache: dict | None = None


def _normalize_language(language: str | None) -> str:
    value = str(language or "").strip().lower()
    return value if value in _LANGUAGES else _DEFAULT_LANGUAGE


def _load() -> dict:
    """{"version": str, "words": [{"h","p","m":{...},"lv"}]}"""

    global _cache
    if _cache is not None:
        return _cache

    words: list[dict] = []
    version = ""
    try:
        raw = _SOURCE.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001 — fayl yo'q bo'lsa lug'at bo'sh qoladi
        raw = ""

    if raw:
        # Manba o'zgarganini bitta qisqa qiymat bilan bildiramiz; klient shu
        # bo'yicha keshini yangilaydi va har safar 90 KB yuklab olmaydi.
        version = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        match = _ARRAY.search(raw)
        if match:
            try:
                parsed = json.loads(match.group(1))
            except Exception:  # noqa: BLE001 — buzuq fayl serverni yiqitmasin
                parsed = []
            for item in parsed if isinstance(parsed, list) else []:
                if not isinstance(item, dict):
                    continue
                hanzi = str(item.get("h") or "").strip()
                pinyin = str(item.get("p") or "").strip()
                meaning = item.get("m")
                level = str(item.get("lv") or "").strip()
                if not hanzi or not pinyin or not isinstance(meaning, dict):
                    continue
                # Uch tilning bittasi ham yetishmasa, o'sha tildagi o'quvchi
                # bo'sh qator ko'rardi — bunday yozuv umuman berilmaydi.
                if not all(str(meaning.get(key) or "").strip() for key in _LANGUAGES):
                    continue
                words.append(
                    {
                        "h": hanzi,
                        "p": pinyin,
                        "m": {key: str(meaning[key]).strip() for key in _LANGUAGES},
                        "lv": level,
                    }
                )

    _cache = {"version": version, "words": words}
    return _cache


def dictionary_version() -> str:
    """Manba faylining qisqa barmoq izi. Bo'sh lug'atda bo'sh satr."""

    return _load()["version"]


def dictionary_for_language(language: str | None) -> list[dict]:
    """Bitta tildagi lug'at: [{"h","p","m","lv"}]. `m` — endi satr."""

    key = _normalize_language(language)
    return [
        {"h": item["h"], "p": item["p"], "m": item["m"][key], "lv": item["lv"]}
        for item in _load()["words"]
    ]


def dictionary_size() -> int:
    return len(_load()["words"])

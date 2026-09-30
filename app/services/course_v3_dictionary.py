"""HSK AI lug'ati manbasi.

Mini App lug'ati legacy HSK 2.0 so'zlarini hsk-words.js dan, HSK 3.0
so'zlarini esa generated course_v3_data/hsk30-words.js dan o'qiydi.
Native klientlar ham aynan shu ikki manbani ko'rishi kerak.

JS wrapper olib tashlanadi, massivlar JSON sifatida parse qilinadi. Ikkala
fayl faqat deploy bilan o'zgaradi, shuning uchun natija bir marta keshlanadi.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


_SOURCES = (
    (
        Path("app/static/hsk-words.js"),
        re.compile(r"const\s+WORDS\s*=\s*(\[.*\])\s*;?\s*\Z", re.S),
    ),
    (
        Path("app/static/course_v3_data/hsk30-words.js"),
        re.compile(r"window\.HSK30_WORDS\s*=\s*(\[.*\])\s*;?\s*\Z", re.S),
    ),
)

_LANGUAGES = ("uz", "ru", "tj")
_DEFAULT_LANGUAGE = "ru"

_cache: dict | None = None


def _normalize_language(language: str | None) -> str:
    value = str(language or "").strip().lower()
    return value if value in _LANGUAGES else _DEFAULT_LANGUAGE


def _load() -> dict:
    """Return version and normalized words from both course versions."""

    global _cache
    if _cache is not None:
        return _cache

    words: list[dict] = []
    version_hasher = hashlib.sha256()
    any_source = False

    for source, array_pattern in _SOURCES:
        try:
            raw = source.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            raw = ""
        if not raw:
            continue

        any_source = True
        version_hasher.update(str(source).encode("utf-8"))
        version_hasher.update(b"\0")
        version_hasher.update(raw.encode("utf-8"))
        match = array_pattern.search(raw)
        if not match:
            continue
        try:
            parsed = json.loads(match.group(1))
        except Exception:  # noqa: BLE001
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

    _cache = {
        "version": version_hasher.hexdigest()[:16] if any_source else "",
        "words": words,
    }
    return _cache


def dictionary_version() -> str:
    """Ikkala dictionary assetning umumiy qisqa barmoq izi."""
    return _load()["version"]


def dictionary_for_language(language: str | None) -> list[dict]:
    """Bitta tildagi lug'at; m qiymati bitta tarjima satri."""
    key = _normalize_language(language)
    return [
        {"h": item["h"], "p": item["p"], "m": item["m"][key], "lv": item["lv"]}
        for item in _load()["words"]
    ]


def dictionary_size() -> int:
    return len(_load()["words"])

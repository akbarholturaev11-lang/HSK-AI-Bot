"""Xatolarim takrori uchun kanonik material: lug'at va gap havzasi.

Takror eski savolni qayta o'ynatmaydi — nishondan (so'z yoki gap) yangi
savol yasaydi. Buning uchun ikkita manba kerak:

- lug'at: `course_v3_vocab` (har daraja uchun ieroglif, pinyin, 3 tilda ma'no);
- gap havzasi: dars JSON'laridagi gap tuzish, bo'sh joy va dialog kartalari
  (distraktor gaplar va tarjimalar shu yerdan olinadi).

Fayllar faqat deploy bilan o'zgaradi, shuning uchun bir marta o'qib keshlanadi.
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from app.services.course_v3_vocab import words_for_level


LEVELS = ("hsk1", "hsk2", "hsk3", "hsk4")
LANGUAGES = ("uz", "ru", "tj")
_DATA_DIR = Path(__file__).resolve().parents[1] / "static" / "course_v3_data"

CJK_RE = re.compile(r"[㐀-䶿一-鿿]")
CJK_RUN_RE = re.compile(r"[㐀-䶿一-鿿][㐀-䶿一-鿿，。！？、；：“”‘’（）《》…·\s,.!?]*")
GAP_RE = re.compile(r"_{2,}")
_ZH_PUNCT_RE = re.compile(r"[\s，。！？、；：“”‘’（）《》…·,.!?;:'\"()\[\]\-—–~]+")
_MAX_WORD_LEN = 4
# Pinyin ohangi: bitta unli belgisi -> (asos, ohang). Tone variantlari
# (`nǐ` -> `nī`/`ní`/`nì`) pinyin/tinglash distraktorlari uchun.
_TONE_TABLE = {
    "a": "āáǎà", "e": "ēéěè", "i": "īíǐì", "o": "ōóǒò", "u": "ūúǔù", "ü": "ǖǘǚǜ",
}
_TONED_TO_BASE = {
    toned: (base, index + 1)
    for base, toned_chars in _TONE_TABLE.items()
    for index, toned in enumerate(toned_chars)
}
# Gap tuzish kartasidagi izoh: "To'g'ri: 你 — 你好！ (Salom!)" — oxiridagi
# qavs gapning tarjimasi. "北京 (Běijīng) — Pekin" shaklida esa bu so'z izohi.
_EXPLANATION_TRANSLATION_RE = re.compile(r"—\s*[^()—]*[一-鿿][^()—]*\(([^()]+)\)\s*$")


def has_cjk(value) -> bool:
    return bool(CJK_RE.search(str(value or "")))


def normalize_zh(value) -> str:
    """Ikki xitoycha matn KO'RINISHDA bir xilmi (tinish/bo'shliqsiz)."""
    text = unicodedata.normalize("NFKC", str(value or ""))
    return _ZH_PUNCT_RE.sub("", text)


def only_cjk_text(value) -> bool:
    """Matnda xitoycha belgi bor va lotin/kirill harfi yo'q."""
    text = str(value or "")
    if not has_cjk(text):
        return False
    return not re.search(r"[A-Za-zА-Яа-яЁёӢӣӮӯҚқҲҳҶҷҒғ]", text)


def pinyin_key(value) -> str:
    """Ohang belgilari SAQLANGAN, registr/bo'shliq/apostrofsiz pinyin."""
    text = unicodedata.normalize("NFC", str(value or "")).casefold()
    return re.sub(r"[\s'’·\-]+", "", text)


def pinyin_plain(value) -> str:
    """Ohangsiz pinyin (omofonlarni solishtirish uchun)."""
    out = []
    for char in pinyin_key(value):
        base = _TONED_TO_BASE.get(char)
        out.append(base[0] if base else char)
    return "".join(out).replace("v", "ü")


def tone_variants(pinyin: str) -> list[str]:
    """Birinchi ohangli unlining boshqa ohanglari (tartib barqaror)."""
    text = unicodedata.normalize("NFC", str(pinyin or ""))
    for index, char in enumerate(text):
        info = _TONED_TO_BASE.get(char)
        if not info:
            continue
        base, tone = info
        variants = []
        for other in range(1, 5):
            if other == tone:
                continue
            variants.append(text[:index] + _TONE_TABLE[base][other - 1] + text[index + 1:])
        return variants
    return []


def extract_cjk_sentence(value) -> str:
    """Aralash matndan (AI tuzatishi) birinchi xitoycha gapni ajratadi."""
    for match in CJK_RUN_RE.finditer(str(value or "")):
        candidate = match.group(0).strip(" ,.")
        if len(normalize_zh(candidate)) >= 1:
            return candidate.strip()
    return ""


def normalize_level(value) -> str:
    level = str(value or "").strip().lower().replace(" ", "")
    if level in {"hsk4a", "hsk4b"}:
        level = "hsk4"
    return level if level in LEVELS else "hsk1"


@lru_cache(maxsize=1)
def lexicon() -> dict[str, dict]:
    """zh -> {"zh", "pinyin", "meaning": {uz,ru,tj}, "level"} (pastki daraja ustun)."""
    index: dict[str, dict] = {}
    for level in LEVELS:
        for word in words_for_level(level):
            zh = str(word.get("zh") or "").strip()
            pinyin = str(word.get("pinyin") or "").strip()
            meaning = word.get("meaning") if isinstance(word.get("meaning"), dict) else {}
            if not zh or zh in index or not pinyin or "→" in pinyin:
                continue
            if not all(str(meaning.get(lang) or "").strip() for lang in LANGUAGES):
                continue
            index[zh] = {
                "zh": zh,
                "pinyin": pinyin,
                "meaning": {lang: str(meaning[lang]).strip() for lang in LANGUAGES},
                "level": level,
            }
    return index


def lookup_word(zh) -> dict | None:
    return lexicon().get(str(zh or "").strip())


@lru_cache(maxsize=8)
def level_words(level: str) -> tuple[dict, ...]:
    """Distraktor havzasi: shu daraja so'zlari, yetmasa quyi darajalar ham."""
    level = normalize_level(level)
    words = [word for word in lexicon().values() if word["level"] == level]
    if len(words) < 12:
        order = list(LEVELS)
        for fallback in reversed(order[: order.index(level) + 1]):
            for word in lexicon().values():
                if word["level"] == fallback and word not in words:
                    words.append(word)
    return tuple(words)


def segment(zh: str) -> list[str]:
    """Lug'at bo'yicha eng uzun moslik bilan bo'laklash (tinish belgisiz)."""
    text = normalize_zh(zh)
    words = lexicon()
    tokens: list[str] = []
    index = 0
    while index < len(text):
        for size in range(min(_MAX_WORD_LEN, len(text) - index), 0, -1):
            piece = text[index:index + size]
            if size == 1 or piece in words:
                tokens.append(piece)
                index += size
                break
    return tokens


def sentence_pinyin(tokens: list[str]) -> str:
    """Hamma bo'lak lug'atda bo'lsa — gap pinyini, aks holda bo'sh."""
    parts = []
    for token in tokens:
        word = lookup_word(token)
        if not word:
            return ""
        parts.append(word["pinyin"])
    return " ".join(parts)


def _localized(value, lang: str) -> str:
    if isinstance(value, dict):
        value = value.get(lang)
    return re.sub(r"\s+", " ", str(value or "")).strip()


def explanation_translation(explanation) -> dict[str, str]:
    """Gap tuzish kartasi izohidagi tarjima (uchala tilda bo'lsagina)."""
    if not isinstance(explanation, dict):
        return {}
    result = {}
    for lang in LANGUAGES:
        match = _EXPLANATION_TRANSLATION_RE.search(_localized(explanation, lang))
        if not match:
            return {}
        result[lang] = match.group(1).strip()
    return result


def _pool_add(pool: dict[str, dict], zh: str, *, tokens=None, translation=None) -> None:
    key = normalize_zh(zh)
    if len(key) < 2 or not only_cjk_text(zh):
        return
    entry = pool.get(key)
    if entry is None:
        entry = {"zh": str(zh).strip(), "key": key, "tokens": [], "translation": {}}
        pool[key] = entry
    if tokens and not entry["tokens"]:
        entry["tokens"] = [str(token) for token in tokens]
    if translation and not entry["translation"]:
        if all(str(translation.get(lang) or "").strip() for lang in LANGUAGES):
            entry["translation"] = {lang: str(translation[lang]).strip() for lang in LANGUAGES}


@lru_cache(maxsize=8)
def sentence_pool(level: str) -> tuple[dict, ...]:
    """Darajadagi dars gaplari: {"zh", "key", "tokens", "translation", "pinyin"}."""
    level = normalize_level(level)
    pool: dict[str, dict] = {}
    for path in sorted((_DATA_DIR / level).glob("lesson_*.json")):
        try:
            lesson = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for section in lesson.get("sections") or []:
            if not isinstance(section, dict):
                continue
            for card in section.get("cards") or []:
                if not isinstance(card, dict):
                    continue
                card_type = str(card.get("type") or "")
                if card_type == "sentence_builder":
                    answer = card.get("answer_tokens")
                    if isinstance(answer, list) and all(has_cjk(token) for token in answer):
                        _pool_add(
                            pool,
                            "".join(str(token) for token in answer),
                            tokens=answer,
                            translation=card.get("sentence") if isinstance(card.get("sentence"), dict) else None,
                        )
                elif card_type == "reverse_builder":
                    _pool_add(
                        pool,
                        str(card.get("zh") or ""),
                        translation=card.get("translation") if isinstance(card.get("translation"), dict) else None,
                    )
                elif card_type == "gap_fill":
                    full = _filled_gap(card)
                    if full:
                        _pool_add(pool, full, translation=explanation_translation(card.get("explanation")))
                elif card_type == "dialog_cloze":
                    for line in card.get("lines") or []:
                        if isinstance(line, dict) and line.get("zh"):
                            _pool_add(pool, str(line["zh"]))
    result = []
    for entry in pool.values():
        tokens = entry["tokens"] or segment(entry["zh"])
        if normalize_zh("".join(tokens)) != entry["key"]:
            tokens = segment(entry["zh"])
        result.append({**entry, "tokens": tokens, "pinyin": sentence_pinyin(tokens)})
    return tuple(result)


def _filled_gap(card: dict) -> str:
    sentence = str(card.get("sentence") or "")
    options = card.get("options")
    try:
        answer_index = int(card.get("correct_index"))
    except (TypeError, ValueError):
        return ""
    if (
        len(GAP_RE.findall(sentence)) != 1
        or not isinstance(options, list)
        or not 0 <= answer_index < len(options)
    ):
        return ""
    return GAP_RE.sub(str(options[answer_index]), sentence)


def find_pool_sentence(zh: str, level: str | None = None) -> dict | None:
    key = normalize_zh(zh)
    if not key:
        return None
    levels = [normalize_level(level)] if level else []
    levels += [item for item in LEVELS if item not in levels]
    for item in levels:
        for entry in sentence_pool(item):
            if entry["key"] == key:
                return entry
    return None

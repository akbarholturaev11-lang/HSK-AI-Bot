"""Xatodan "nishon"ni ajratish: o'quvchi aynan nimani bilmadi.

Bitta xato 6 xil manbadan (dars, imtihon, mashq, bellashuv, drill, AI Voice)
har xil shaklda keladi. Bu modul hammasini ikki turga keltiradi:

- `word`: lug'at so'zi (你) — ma'no/ieroglif/pinyin/tinglash xatolari;
- `sentence`: to'g'ri xitoycha gap — bo'sh joy, dialog, gap tuzish, AI Voice.

Nishon topilmasa `None` qaytadi va chaqiruvchi eski savolni (`question`)
bitta format sifatida saqlab qoladi.
"""

from __future__ import annotations

import hashlib
import re

from app.services import mistake_drill_bank as bank


_BUILDER_FORMATS = {"sentence_builder", "sentence_reorder", "word_order", "reorder"}
_LISTEN_FORMATS = {"listening_choice", "audio_choice", "listen_and_fill"}
_DIALOG_FORMATS = {"dialog_cloze", "dialog_context"}
# "好 = yaxshi, ajoyib (hǎo)" / "骂 — mà" / "你 — sen (birlik) (nǐ)"
_EXPLANATION_WORD_RE = re.compile(
    r"^\s*(?:[^:：]*[:：]\s*)?([一-鿿]{1,4})\s*[=—–-]\s*(.*?)\s*$"
)
_TRAILING_PINYIN_RE = re.compile(r"\(([^()]*)\)\s*$")
_PINYIN_CHARS_RE = re.compile(r"^[a-zA-Zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü\s'’·]+$")


def target_key(kind: str, value: str) -> str:
    return hashlib.sha256(f"{kind}|{value}".encode("utf-8")).hexdigest()


def _text(value, limit: int = 2000) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _answer_key(value) -> str:
    text = _text(value).casefold()
    text = re.sub(r"[.,;:!?()\[\]{}«»\"'’`\-—–/\\]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _looks_like_pinyin(value) -> bool:
    text = _text(value, 200)
    return bool(text) and bool(_PINYIN_CHARS_RE.match(text)) and not bank.has_cjk(text)


def _word_target(word: dict) -> dict:
    return {
        "kind": "word",
        "zh": word["zh"],
        "key": target_key("word", word["zh"]),
        "level": word["level"],
        "payload": {"pinyin": word["pinyin"], "meaning": dict(word["meaning"])},
    }


def _adhoc_word(zh: str, *, pinyin: str, meaning: str, language: str, level: str) -> dict | None:
    """Lug'atda yo'q qisqa so'z (masalan ton mashqidagi 骂). Pinyinsiz — yo'q."""
    zh = bank.normalize_zh(zh)
    if not zh or len(zh) > 4 or not _looks_like_pinyin(pinyin):
        return None
    payload = {"pinyin": _text(pinyin, 120), "meaning": {}}
    if meaning and language in bank.LANGUAGES and not bank.has_cjk(meaning):
        payload["meaning"][language] = _text(meaning, 300)
    return {
        "kind": "word",
        "zh": zh,
        "key": target_key("word", zh),
        "level": bank.normalize_level(level),
        "payload": payload,
    }


def _explanation_parts(explanation: str) -> tuple[str, str, str]:
    """(zh, ma'no, pinyin) — izohdan, bo'lmasa bo'sh."""
    match = _EXPLANATION_WORD_RE.match(_text(explanation, 400))
    if not match:
        return "", "", ""
    zh, rest = match.group(1), match.group(2)
    pinyin = ""
    trailing = _TRAILING_PINYIN_RE.search(rest)
    if trailing and _looks_like_pinyin(trailing.group(1)):
        pinyin = trailing.group(1).strip()
        rest = rest[: trailing.start()].strip()
    elif _looks_like_pinyin(rest):
        pinyin, rest = rest, ""
    return zh, rest.strip(" —-"), pinyin


def _word_or_adhoc(zh: str, *, material: dict, explanation: str, language: str, level: str) -> dict | None:
    word = bank.lookup_word(bank.normalize_zh(zh)) or bank.lookup_word(zh)
    if word:
        return _word_target(word)
    exp_zh, exp_meaning, exp_pinyin = _explanation_parts(explanation)
    pinyin = _text(material.get("pinyin"), 120)
    if exp_zh and bank.normalize_zh(exp_zh) == bank.normalize_zh(zh):
        pinyin = exp_pinyin or pinyin
    else:
        exp_meaning = ""
    return _adhoc_word(zh, pinyin=pinyin, meaning=exp_meaning, language=language, level=level)


def _sentence_target(
    zh: str,
    *,
    level: str,
    language: str,
    tokens: list[str] | None = None,
    translation: str | dict | None = None,
    wrong: str = "",
    gap: dict | None = None,
    dialog: dict | None = None,
    pinyin: str = "",
) -> dict | None:
    zh = _text(zh, 300)
    key = bank.normalize_zh(zh)
    if len(key) < 2 or not bank.only_cjk_text(zh):
        return None
    word = bank.lookup_word(key)
    if word and not gap and not dialog and not wrong:
        # Bitta lug'at so'zi — gap emas, so'z mashqlari mosroq.
        return _word_target(word)
    pool_entry = bank.find_pool_sentence(zh, level)
    clean_tokens = [bank.normalize_zh(token) for token in (tokens or []) if bank.normalize_zh(token)]
    if not clean_tokens or "".join(clean_tokens) != key:
        clean_tokens = list(pool_entry["tokens"]) if pool_entry else bank.segment(zh)
    translations: dict[str, str] = {}
    if pool_entry and pool_entry.get("translation"):
        translations = dict(pool_entry["translation"])
    elif isinstance(translation, dict):
        translations = {
            lang: _text(value, 400)
            for lang, value in translation.items()
            if lang in bank.LANGUAGES and _text(value) and not bank.has_cjk(value)
        }
    elif translation and language in bank.LANGUAGES and not bank.has_cjk(translation):
        translations = {language: _text(translation, 400)}
    payload: dict = {
        "tokens": clean_tokens,
        "translation": translations,
        "pinyin": _text(pinyin, 400) or (pool_entry or {}).get("pinyin") or bank.sentence_pinyin(clean_tokens),
        "wrong": [],
    }
    wrong_text = _text(wrong, 300)
    if wrong_text and bank.only_cjk_text(wrong_text) and bank.normalize_zh(wrong_text) != key:
        payload["wrong"] = [wrong_text]
    if gap:
        payload["gap"] = gap
    if dialog:
        payload["dialog"] = dialog
    return {
        "kind": "sentence",
        "zh": zh,
        "key": target_key("sentence", key),
        "level": bank.normalize_level(level),
        "payload": payload,
    }


def _voice_correct_sentence(correction: str, wrong: str) -> str:
    """AI tuzatishidan to'g'ri gapni ajratadi.

    Tuzatish erkin matn: "我是学生。", "应该说：我是学生。", "Use 很: 他很高。".
    Nomzodlar — xitoycha qismlar (ikki nuqtadan keyingi qism alohida).
    O'quvchining xato gapiga eng o'xshashi olinadi: tuzatish o'sha gapning
    to'g'rilangan ko'rinishi. Xato gap yo'q bo'lsa — eng uzuni.
    """
    candidates: list[str] = []
    for match in bank.CJK_RUN_RE.finditer(str(correction or "")):
        run = match.group(0).strip(" ,.")
        for part in [run, *re.split(r"[：:]", run)[1:]]:
            part = part.strip(" ,.")
            if len(bank.normalize_zh(part)) >= 2 and part not in candidates:
                candidates.append(part)
    wrong_key = bank.normalize_zh(wrong)
    candidates = [value for value in candidates if bank.normalize_zh(value) != wrong_key]
    if not candidates:
        return ""
    if not wrong_key:
        return max(candidates, key=lambda value: len(bank.normalize_zh(value)))

    def similarity(value: str) -> tuple[float, int]:
        key = bank.normalize_zh(value)
        common = sum(min(key.count(char), wrong_key.count(char)) for char in set(key))
        return (2 * common / (len(key) + len(wrong_key)), -abs(len(key) - len(wrong_key)))

    return max(candidates, key=similarity)


def _choice_block(material: dict, correct_answer: str) -> dict | None:
    """Muallif variantlari (bo'sh joy/dialog uchun): gap, variantlar, javob."""
    options = [_text(value, 300) for value in (material.get("options") or []) if _text(value, 300)]
    if correct_answer not in options or len(options) < 2:
        return None
    return {"options": options[:6], "answer_index": options.index(correct_answer)}


def _word_from_texts(texts: list[str], correct_answer: str, language: str) -> dict | None:
    """To'g'ri javob ma'no yoki pinyin bo'lsa: matnlardagi so'zlardan mosini topadi."""
    answer = _answer_key(correct_answer)
    if not answer:
        return None
    matches: dict[str, dict] = {}
    for text in texts:
        for token in bank.segment(text):
            word = bank.lookup_word(token)
            if not word:
                continue
            meaning = _answer_key(word["meaning"].get(language, ""))
            if meaning == answer or bank.pinyin_key(word["pinyin"]) == bank.pinyin_key(correct_answer):
                matches[word["zh"]] = word
    if len(matches) == 1:
        return _word_target(next(iter(matches.values())))
    if matches:
        return None
    # Ma'no matni lug'atdagidan biroz farq qilishi mumkin ("birga" /
    # "birga, birgalikda"). Savoldagi xitoycha qism AYNAN bitta lug'at so'zi
    # bo'lsa — nishon o'sha (ma'no lug'atdan olinadi).
    runs = {bank.normalize_zh(match.group(0)) for text in texts for match in bank.CJK_RUN_RE.finditer(text)}
    runs.discard("")
    if len(runs) == 1:
        word = bank.lookup_word(next(iter(runs)))
        if word:
            return _word_target(word)
    return None


def resolve_target(
    *,
    category: str,
    source: str,
    material: dict,
    prompt: str,
    correct_answer: str,
    user_answer: str | None,
    explanation: str | None,
    level: str | None,
    language: str | None,
) -> dict | None:
    material = material if isinstance(material, dict) else {}
    language = _text(language or material.get("language"), 8).lower()
    level = bank.normalize_level(level or (material.get("source") or {}).get("level"))
    fmt = _text(material.get("format"), 64).lower()
    correct = _text(material.get("correct_answer") or correct_answer, 700)
    prompt = _text(material.get("prompt") or prompt, 700)
    sentence = _text(material.get("sentence"), 700)
    audio_text = _text(material.get("audio_text"), 300)
    explanation = _text(material.get("explanation") or explanation, 700)
    wrong = _text(user_answer, 300)
    source = _text(source, 32).lower()

    # 1) Gap tuzish: to'g'ri gap — javob bo'laklari (xitoycha bo'lsa).
    if fmt in _BUILDER_FORMATS or fmt == "reverse_builder":
        answer_tokens = [_text(value, 200) for value in (material.get("answer_tokens") or [])]
        if answer_tokens and all(bank.has_cjk(token) for token in answer_tokens):
            return _sentence_target(
                "".join(answer_tokens),
                level=level,
                language=language,
                tokens=answer_tokens,
                translation=material.get("translation") or prompt,
            )
        if bank.has_cjk(sentence):
            return _sentence_target(
                sentence,
                level=level,
                language=language,
                translation=material.get("translation") or prompt,
            )
        return None

    # 2) Juftlik: "你 → sen (birlik)" — chap tomon so'z.
    if fmt in {"match_pairs", "pair_match", "matching"} and "→" in correct:
        left = correct.split("→", 1)[0].strip()
        word = bank.lookup_word(left)
        return _word_target(word) if word else None

    # 3) Bo'sh joy (dars `gap_fill`, imtihon `text_choice` "我___学过汉语。").
    if bank.GAP_RE.search(sentence) and bank.has_cjk(correct) and len(bank.GAP_RE.findall(sentence)) == 1:
        block = _choice_block(material, correct)
        full = bank.GAP_RE.sub(correct, sentence)
        if fmt in _DIALOG_FORMATS or "\n" in sentence or re.search(r"(^|\s)[AB]:", sentence):
            return _sentence_target(
                correct,
                level=level,
                language=language,
                dialog={"sentence": sentence, **block} if block else None,
            )
        target = _sentence_target(
            full,
            level=level,
            language=language,
            translation=material.get("translation"),
            gap={"sentence": sentence, **block} if block else None,
        )
        if target:
            return target

    # 4) Tinglash: eshitilgan matn — nishon (javob ieroglif yoki tarjima bo'lishi mumkin).
    if audio_text and bank.has_cjk(audio_text) and (fmt in _LISTEN_FORMATS or fmt == "audio_truefalse"):
        word = bank.lookup_word(bank.normalize_zh(audio_text))
        if word:
            return _word_target(word)
        translation = correct if (fmt == "audio_choice" and not bank.has_cjk(correct)) else None
        target = _sentence_target(audio_text, level=level, language=language, translation=translation)
        if target:
            return target
        return _word_or_adhoc(audio_text, material=material, explanation=explanation, language=language, level=level)

    # 5) AI Voice tuzatishi: to'g'ri gap + o'quvchining o'z xato gapi.
    if source == "voice":
        wrong_zh = bank.extract_cjk_sentence(wrong)
        correct_zh = _voice_correct_sentence(correct, wrong_zh)
        if correct_zh:
            target = _sentence_target(correct_zh, level=level, language=language, wrong=wrong_zh)
            if target:
                return target
            return _word_or_adhoc(correct_zh, material=material, explanation="", language=language, level=level)
        return None

    # 6) To'g'ri javob xitoycha: so'z yoki gap.
    if bank.has_cjk(correct) and bank.only_cjk_text(correct):
        key = bank.normalize_zh(correct)
        word = bank.lookup_word(key)
        if word:
            return _word_target(word)
        if len(key) >= 3 or re.search(r"[，。！？,.!?]", correct):
            dialog = None
            if fmt in _DIALOG_FORMATS and sentence:
                block = _choice_block(material, correct)
                dialog = {"sentence": sentence, **block} if block and bank.GAP_RE.search(sentence) else None
            target = _sentence_target(
                correct,
                level=level,
                language=language,
                translation=material.get("translation"),
                wrong=wrong if source in {"voice", "pronunciation"} else "",
                dialog=dialog,
            )
            if target:
                return target
        return _word_or_adhoc(correct, material=material, explanation=explanation, language=language, level=level)

    # 7) To'g'ri javob ma'no/pinyin: savol matnidagi so'zdan mosini topamiz.
    texts = [prompt, sentence if not bank.GAP_RE.search(sentence) else "", explanation, audio_text]
    word = _word_from_texts([text for text in texts if bank.has_cjk(text)], correct, language)
    if word:
        return word
    if _looks_like_pinyin(correct):
        for text in (prompt, sentence, explanation):
            run = bank.extract_cjk_sentence(text)
            key = bank.normalize_zh(run)
            if key and len(key) <= 4:
                exp_zh, exp_meaning, _ = _explanation_parts(explanation)
                meaning = exp_meaning if bank.normalize_zh(exp_zh) == key else ""
                return _adhoc_word(key, pinyin=correct, meaning=meaning, language=language, level=level)
    if sentence and bank.only_cjk_text(sentence) and not bank.GAP_RE.search(sentence):
        translation = correct if not bank.has_cjk(correct) and not _looks_like_pinyin(correct) else None
        if translation and fmt not in {"audio_truefalse"}:
            return _sentence_target(sentence, level=level, language=language, translation=translation)
    return None

"""Nishondan takror savollarini yasash va har birini tekshirish.

Bitta xato kamida 3 xil mashqda qaytadi. Mashq turi kategoriyaga bog'liq
(`WORD_LADDERS` / `SENTENCE_LADDERS`). Har savol klientga ketishidan oldin
`validate_question` dan o'tadi: javobni ochib qo'ygan, ovozsiz tinglash yoki
takroriy variantli savol hech qachon chiqmaydi — yasalmagan hisoblanadi.

Savol shakli eski review bilan bir xil (prompt, sentence, pinyin,
audio_text, options/answer_index yoki tokens/answer_tokens), shuning uchun
eski klientlar ham variantli turlarni ko'rsata oladi.
"""

from __future__ import annotations

import hashlib
import re

from app.services import mistake_drill_bank as bank


DRILL_MATERIAL_VERSION = 3
REQUIRED_FORMATS = 3

CHOICE_FORMATS = frozenset(
    {
        "meaning_choice",
        "hanzi_choice",
        "hanzi_from_pinyin",
        "pinyin_choice",
        "listening_choice",
        "listening_pinyin",
        "sentence_listening",
        "sentence_meaning",
        "gap_fill",
        "dialog_choice",
        "correct_choice",
    }
)
BUILDER_FORMATS = frozenset({"sentence_builder", "listen_builder"})
ALL_FORMATS = CHOICE_FORMATS | BUILDER_FORMATS
# `formats` yubormaydigan (eski) klient faqat variantli savolni ko'rsata oladi.
LEGACY_CLIENT_FORMATS = CHOICE_FORMATS
LISTEN_FORMATS = frozenset(
    {"listening_choice", "listening_pinyin", "sentence_listening", "listen_builder"}
)
_HANZI_OPTION_FORMATS = frozenset(
    {"hanzi_choice", "hanzi_from_pinyin", "listening_choice", "sentence_listening", "correct_choice"}
)
_PINYIN_OPTION_FORMATS = frozenset({"pinyin_choice", "listening_pinyin"})
_MEANING_OPTION_FORMATS = frozenset({"meaning_choice", "sentence_meaning"})
_GAP_FORMATS = frozenset({"gap_fill", "dialog_choice"})
# Eski savol (`question` nishoni) klientning eski builder rendereri bilan chiqadi.
LEGACY_BUILDER_FORMATS = frozenset({"sentence_builder", "sentence_reorder", "word_order", "reorder"})

WORD_LADDERS = {
    "word": ("meaning_choice", "hanzi_choice", "listening_choice", "pinyin_choice", "hanzi_from_pinyin"),
    "character": ("hanzi_from_pinyin", "pinyin_choice", "hanzi_choice", "listening_choice", "meaning_choice"),
    "pronunciation": ("listening_choice", "listening_pinyin", "pinyin_choice", "meaning_choice", "hanzi_from_pinyin"),
    "grammar": ("meaning_choice", "hanzi_choice", "listening_choice", "pinyin_choice", "hanzi_from_pinyin"),
}
SENTENCE_LADDERS = {
    "default": (
        "gap_fill",
        "dialog_choice",
        "correct_choice",
        "sentence_builder",
        "sentence_meaning",
        "sentence_listening",
        "listen_builder",
    ),
    "pronunciation": (
        "sentence_listening",
        "listen_builder",
        "sentence_meaning",
        "sentence_builder",
        "correct_choice",
        "gap_fill",
        "dialog_choice",
    ),
}

MAX_BUILDER_TOKENS = 7
MAX_OPTIONS = 4

INSTRUCTIONS = {
    "meaning_choice": {
        "uz": "Ma'nosini tanlang",
        "ru": "Выберите значение",
        "tj": "Маъноашро интихоб кунед",
    },
    "hanzi_choice": {
        "uz": "«{meaning}» — qaysi ieroglif?",
        "ru": "«{meaning}» — какой иероглиф?",
        "tj": "«{meaning}» — кадом иероглиф?",
    },
    "hanzi_from_pinyin": {
        "uz": "Qaysi ieroglif shunday o'qiladi?",
        "ru": "Какой иероглиф так читается?",
        "tj": "Кадом иероглиф ҳамин тавр хонда мешавад?",
    },
    "pinyin_choice": {
        "uz": "Qanday o'qiladi?",
        "ru": "Как читается?",
        "tj": "Чӣ тавр хонда мешавад?",
    },
    "listening_choice": {
        "uz": "Tinglang va eshitganingizni tanlang",
        "ru": "Послушайте и выберите, что услышали",
        "tj": "Гӯш кунед ва шунидаатонро интихоб кунед",
    },
    "listening_pinyin": {
        "uz": "Tinglang: qanday o'qildi?",
        "ru": "Послушайте: как это прочитано?",
        "tj": "Гӯш кунед: чӣ тавр хонда шуд?",
    },
    "sentence_listening": {
        "uz": "Tinglang va eshitgan gapingizni tanlang",
        "ru": "Послушайте и выберите услышанную фразу",
        "tj": "Гӯш кунед ва ҷумлаи шунидаатонро интихоб кунед",
    },
    "sentence_meaning": {
        "uz": "Bu gap nimani anglatadi?",
        "ru": "Что означает эта фраза?",
        "tj": "Ин ҷумла чӣ маъно дорад?",
    },
    "sentence_builder": {
        "uz": "Gapni to'g'ri tartibda tuzing",
        "ru": "Составьте фразу в правильном порядке",
        "tj": "Ҷумларо бо тартиби дуруст созед",
    },
    "sentence_builder_hint": {
        "uz": "Gapni tuzing: «{translation}»",
        "ru": "Составьте фразу: «{translation}»",
        "tj": "Ҷумларо созед: «{translation}»",
    },
    "listen_builder": {
        "uz": "Tinglang va eshitgan gapni tuzing",
        "ru": "Послушайте и составьте услышанную фразу",
        "tj": "Гӯш кунед ва ҷумлаи шунидаро созед",
    },
    "gap_fill": {
        "uz": "Bo'sh joyga mosini tanlang",
        "ru": "Выберите, что подходит в пропуск",
        "tj": "Барои ҷойи холӣ мувофиқашро интихоб кунед",
    },
    "gap_fill_hint": {
        "uz": "Bo'sh joyga mosini tanlang: «{translation}»",
        "ru": "Выберите, что подходит в пропуск: «{translation}»",
        "tj": "Барои ҷойи холӣ мувофиқашро интихоб кунед: «{translation}»",
    },
    "dialog_choice": {
        "uz": "Dialogni to'ldiring",
        "ru": "Дополните диалог",
        "tj": "Гуфтугӯро пурра кунед",
    },
    # Xato variant o'quvchining O'Z gapi, u ba'zan boshqa ma'noda to'g'ri
    # xitoycha ham bo'lishi mumkin (我是学生吗 — "talabamanmi?"). Shuning
    # uchun savol "qaysi gap to'g'ri" emas, "aytgan gapingizning to'g'ri shakli".
    "correct_choice": {
        "uz": "Aytgan gapingizning to'g'ri shaklini tanlang",
        "ru": "Выберите правильный вариант фразы, которую вы сказали",
        "tj": "Шакли дурусти ҷумлаи гуфтаатонро интихоб кунед",
    },
    "correct_choice_hint": {
        "uz": "Aytmoqchi bo'lgan gapingiz: «{translation}». To'g'ri shaklini tanlang",
        "ru": "Вы хотели сказать: «{translation}». Выберите правильный вариант",
        "tj": "Шумо гуфтан мехостед: «{translation}». Шакли дурустро интихоб кунед",
    },
}


def _text(value, limit: int = 700) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def answer_key(value) -> str:
    text = _text(value).casefold()
    text = re.sub(r"[.,;:!?()\[\]{}«»\"'’`\-—–/\\，。！？、；：“”‘’（）…]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _meaning_related(first: str, second: str) -> bool:
    """Ikki ma'no bir xil yoki biri ikkinchisini o'z ichiga oladi."""
    a, b = answer_key(first), answer_key(second)
    if not a or not b:
        return True
    if a == b:
        return True
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    return len(shorter) >= 3 and shorter in longer


def _rank(seed: str, value: str) -> bytes:
    return hashlib.sha256(f"{seed}|{value}".encode("utf-8")).digest()


def _instruction(key: str, language: str, **values) -> str:
    template = INSTRUCTIONS[key].get(language) or INSTRUCTIONS[key]["ru"]
    return template.format(**values) if values else template


def _shuffle(values: list[str], seed: str) -> list[str]:
    return sorted(values, key=lambda value: _rank(seed, value))


def _choice(
    target: dict,
    fmt: str,
    *,
    language: str,
    seed: str,
    prompt: str,
    correct: str,
    distractors: list[str],
    sentence: str = "",
    pinyin: str = "",
    audio_text: str = "",
    explanation: str = "",
) -> dict | None:
    options = [correct]
    seen = {answer_key(correct)}
    for value in distractors:
        key = answer_key(value)
        if not key or key in seen:
            continue
        seen.add(key)
        options.append(value)
        if len(options) >= MAX_OPTIONS:
            break
    if len(options) < 2:
        return None
    options = _shuffle(options, f"{seed}|options")
    return _question(
        target,
        fmt,
        language=language,
        prompt=prompt,
        sentence=sentence,
        pinyin=pinyin,
        audio_text=audio_text,
        explanation=explanation,
        options=options,
        answer_index=options.index(correct),
    )


def _question(target: dict, fmt: str, *, language: str, prompt: str, explanation: str, **fields) -> dict:
    question = {
        "id": f"t:{int(target['id'])}:{fmt}",
        "target_id": int(target["id"]),
        "category": target["category"],
        "format": fmt,
        "language": language,
        "prompt": _text(prompt),
        "sentence": _text(fields.pop("sentence", "")),
        "pinyin": _text(fields.pop("pinyin", ""), 300),
        "audio_text": _text(fields.pop("audio_text", ""), 240),
        "explanation": _text(explanation),
        "material_version": DRILL_MATERIAL_VERSION,
    }
    question.update(fields)
    return question


# ---------------------------------------------------------------- word ---

def _word_meaning(target: dict, language: str) -> str:
    meaning = (target["payload"].get("meaning") or {}).get(language)
    return _text(meaning, 300)


def _word_explanation(target: dict, language: str) -> str:
    pinyin = _text(target["payload"].get("pinyin"), 120)
    meaning = _word_meaning(target, language)
    text = target["zh"] + (f" ({pinyin})" if pinyin else "")
    return f"{text} — {meaning}" if meaning else text


_POOL_CANDIDATES = 40


def _word_pool(target: dict, seed: str) -> list[dict]:
    """Distraktor nomzodlari: urug' bo'yicha tanlangan joydan siklik 40 ta so'z.

    Lug'at dars tartibida turadi, shuning uchun qo'shni so'zlar odatda bir
    mavzudan — distraktor shunchaki tasodifiy emas, o'xshash bo'ladi.
    """
    words = bank.level_words(target.get("level") or "hsk1")
    if not words:
        return []
    start = int.from_bytes(_rank(seed, "pool-start")[:4], "big") % len(words)
    picked = []
    for offset in range(len(words)):
        candidate = words[(start + offset) % len(words)]
        if candidate["zh"] != target["zh"]:
            picked.append(candidate)
        if len(picked) >= _POOL_CANDIDATES:
            break
    # Uzunligi yaqin so'zlar oldinda — tanlash taxminga aylanib qolmasin.
    length = len(target["zh"])
    return sorted(picked, key=lambda word: abs(len(word["zh"]) - length) > 1)


def _meaning_choice(target, language, seed):
    meaning = _word_meaning(target, language)
    if not meaning:
        return None
    distractors = [
        word["meaning"][language]
        for word in _word_pool(target, seed)
        if not _meaning_related(word["meaning"][language], meaning)
    ]
    return _choice(
        target, "meaning_choice", language=language, seed=seed,
        prompt=_instruction("meaning_choice", language),
        correct=meaning,
        distractors=distractors,
        sentence=target["zh"],
        pinyin=target["payload"].get("pinyin") or "",
        explanation=_word_explanation(target, language),
    )


def _hanzi_choice(target, language, seed):
    meaning = _word_meaning(target, language)
    if not meaning:
        return None
    distractors = [
        word["zh"]
        for word in _word_pool(target, seed)
        if not _meaning_related(word["meaning"][language], meaning)
    ]
    return _choice(
        target, "hanzi_choice", language=language, seed=seed,
        prompt=_instruction("hanzi_choice", language, meaning=meaning),
        correct=target["zh"],
        distractors=distractors,
        explanation=_word_explanation(target, language),
    )


def _hanzi_from_pinyin(target, language, seed):
    pinyin = _text(target["payload"].get("pinyin"), 120)
    if not pinyin:
        return None
    key = bank.pinyin_key(pinyin)
    distractors = [word["zh"] for word in _word_pool(target, seed) if bank.pinyin_key(word["pinyin"]) != key]
    return _choice(
        target, "hanzi_from_pinyin", language=language, seed=seed,
        prompt=_instruction("hanzi_from_pinyin", language),
        correct=target["zh"],
        distractors=distractors,
        pinyin=pinyin,
        explanation=_word_explanation(target, language),
    )


def _pinyin_distractors(target: dict, pinyin: str, seed: str) -> list[str]:
    key = bank.pinyin_key(pinyin)
    tones = [value for value in _shuffle(bank.tone_variants(pinyin), f"{seed}|tones")][:2]
    syllables = len(pinyin.split())
    others = [
        word["pinyin"]
        for word in _word_pool(target, seed)
        if bank.pinyin_key(word["pinyin"]) != key and len(word["pinyin"].split()) == syllables
    ]
    return tones + others


def _pinyin_choice(target, language, seed):
    pinyin = _text(target["payload"].get("pinyin"), 120)
    if not pinyin:
        return None
    return _choice(
        target, "pinyin_choice", language=language, seed=seed,
        prompt=_instruction("pinyin_choice", language),
        correct=pinyin,
        distractors=_pinyin_distractors(target, pinyin, seed),
        sentence=target["zh"],
        explanation=_word_explanation(target, language),
    )


def _listening_choice(target, language, seed):
    pinyin = _text(target["payload"].get("pinyin"), 120)
    if not pinyin:
        # Omofonni chiqarib tashlash uchun o'qilishi kerak.
        return None
    plain = bank.pinyin_plain(pinyin)
    distractors = [word["zh"] for word in _word_pool(target, seed) if bank.pinyin_plain(word["pinyin"]) != plain]
    return _choice(
        target, "listening_choice", language=language, seed=seed,
        prompt=_instruction("listening_choice", language),
        correct=target["zh"],
        distractors=distractors,
        audio_text=target["zh"],
        explanation=_word_explanation(target, language),
    )


def _listening_pinyin(target, language, seed):
    pinyin = _text(target["payload"].get("pinyin"), 120)
    if not pinyin:
        return None
    return _choice(
        target, "listening_pinyin", language=language, seed=seed,
        prompt=_instruction("listening_pinyin", language),
        correct=pinyin,
        distractors=_pinyin_distractors(target, pinyin, seed),
        audio_text=target["zh"],
        explanation=_word_explanation(target, language),
    )


# ------------------------------------------------------------ sentence ---

def _translation(target: dict, language: str) -> str:
    return _text((target["payload"].get("translation") or {}).get(language), 400)


def _sentence_explanation(target: dict, language: str) -> str:
    pinyin = _text(target["payload"].get("pinyin"), 300)
    translation = _translation(target, language)
    text = target["zh"] + (f" ({pinyin})" if pinyin else "")
    return f"{text} — {translation}" if translation else text


def _sentence_pool(target: dict, seed: str) -> list[dict]:
    key = bank.normalize_zh(target["zh"])
    entries = []
    for level in (target.get("level") or "hsk1", *bank.LEVELS):
        for entry in bank.sentence_pool(level):
            other = entry["key"]
            if other == key or other in key or key in other:
                continue
            if entry not in entries:
                entries.append(entry)
        if len(entries) >= 12:
            break
    length = len(key)
    return sorted(entries, key=lambda entry: (abs(len(entry["key"]) - length) > 3, _rank(seed, entry["key"])))


def _sentence_listening(target, language, seed):
    distractors = [entry["zh"] for entry in _sentence_pool(target, seed)]
    return _choice(
        target, "sentence_listening", language=language, seed=seed,
        prompt=_instruction("sentence_listening", language),
        correct=target["zh"],
        distractors=distractors,
        audio_text=target["zh"],
        explanation=_sentence_explanation(target, language),
    )


def _sentence_meaning(target, language, seed):
    translation = _translation(target, language)
    if not translation:
        return None
    distractors = [
        entry["translation"][language]
        for entry in _sentence_pool(target, seed)
        if entry.get("translation") and not _meaning_related(entry["translation"][language], translation)
    ]
    return _choice(
        target, "sentence_meaning", language=language, seed=seed,
        prompt=_instruction("sentence_meaning", language),
        correct=translation,
        distractors=distractors,
        sentence=target["zh"],
        pinyin=target["payload"].get("pinyin") or "",
        explanation=_sentence_explanation(target, language),
    )


def builder_tokens(tokens: list[str], limit: int = MAX_BUILDER_TOKENS) -> list[str]:
    """Juda ko'p bo'lakni qo'shni eng qisqa juftlarni birlashtirib kamaytiradi."""
    pieces = [str(token) for token in tokens if str(token)]
    while len(pieces) > limit:
        best = min(range(len(pieces) - 1), key=lambda index: (len(pieces[index]) + len(pieces[index + 1]), index))
        pieces[best:best + 2] = [pieces[best] + pieces[best + 1]]
    return pieces


def _builder(target, fmt, language, seed, *, prompt: str, audio_text: str = ""):
    answer = builder_tokens(target["payload"].get("tokens") or [])
    if len(answer) < 2 or len(set(answer)) < 2:
        return None
    shuffled = _shuffle(list(answer), f"{seed}|tokens")
    if shuffled == answer:
        shuffled = shuffled[1:] + shuffled[:1]
    return _question(
        target, fmt, language=language,
        prompt=prompt,
        explanation=_sentence_explanation(target, language),
        audio_text=audio_text,
        options=[],
        tokens=shuffled,
        answer_tokens=answer,
        correct_answer=target["zh"],
    )


def _sentence_builder(target, language, seed):
    translation = _translation(target, language)
    prompt = (
        _instruction("sentence_builder_hint", language, translation=translation)
        if translation
        else _instruction("sentence_builder", language)
    )
    return _builder(target, "sentence_builder", language, seed, prompt=prompt)


def _listen_builder(target, language, seed):
    return _builder(
        target, "listen_builder", language, seed,
        prompt=_instruction("listen_builder", language),
        audio_text=target["zh"],
    )


def _authored_gap(target, fmt, block_key, language, seed):
    block = target["payload"].get(block_key)
    if not isinstance(block, dict):
        return None
    options = [_text(value, 300) for value in (block.get("options") or []) if _text(value, 300)]
    try:
        answer_index = int(block.get("answer_index"))
    except (TypeError, ValueError):
        return None
    if not 0 <= answer_index < len(options):
        return None
    correct = options[answer_index]
    translation = _translation(target, language) if fmt == "gap_fill" else ""
    prompt = (
        _instruction("gap_fill_hint", language, translation=translation)
        if translation
        else _instruction(fmt, language)
    )
    return _choice(
        target, fmt, language=language, seed=seed,
        prompt=prompt,
        correct=correct,
        distractors=[value for index, value in enumerate(options) if index != answer_index],
        sentence=_text(block.get("sentence"), 600),
        explanation=_sentence_explanation(target, language),
    )


def _gap_fill(target, language, seed):
    return _authored_gap(target, "gap_fill", "gap", language, seed)


def _dialog_choice(target, language, seed):
    return _authored_gap(target, "dialog_choice", "dialog", language, seed)


def _correct_choice(target, language, seed):
    wrong = [value for value in (target["payload"].get("wrong") or []) if bank.only_cjk_text(value)]
    if not wrong:
        return None
    translation = _translation(target, language)
    prompt = (
        _instruction("correct_choice_hint", language, translation=translation)
        if translation
        else _instruction("correct_choice", language)
    )
    return _choice(
        target, "correct_choice", language=language, seed=seed,
        prompt=prompt,
        correct=target["zh"],
        distractors=wrong[:2],
        explanation=_sentence_explanation(target, language),
    )


# ------------------------------------------------------------ question ---

def _replay(target, language, seed):
    """Nishon ajratib bo'lmagan eski savol — o'zi, faqat tekshiruvdan o'tsa."""
    stored = target["payload"].get("question")
    if not isinstance(stored, dict):
        return None
    fmt = _text(stored.get("format"), 64) or "word_choice"
    fields = {
        "sentence": stored.get("sentence") or "",
        "pinyin": stored.get("pinyin") or "",
        "audio_text": stored.get("audio_text") or "",
        "replay_format": fmt,
    }
    if fmt in LEGACY_BUILDER_FORMATS:
        tokens = [_text(value, 200) for value in (stored.get("tokens") or []) if _text(value, 200)]
        answer = [_text(value, 200) for value in (stored.get("answer_tokens") or []) if _text(value, 200)]
        question = _question(
            target, "replay", language=language,
            prompt=stored.get("prompt") or "",
            explanation=stored.get("explanation") or "",
            options=[], tokens=tokens, answer_tokens=answer,
            correct_answer=_text(stored.get("correct_answer")) or "".join(answer),
            **fields,
        )
        question["format"] = fmt
        return question
    options = [_text(value) for value in (stored.get("options") or []) if _text(value)]
    try:
        answer_index = int(stored.get("answer_index"))
    except (TypeError, ValueError):
        return None
    if not 0 <= answer_index < len(options):
        return None
    question = _question(
        target, "replay", language=language,
        prompt=stored.get("prompt") or "",
        explanation=stored.get("explanation") or "",
        options=options, answer_index=answer_index,
        **fields,
    )
    question["format"] = "replay"
    return question


BUILDERS = {
    "meaning_choice": _meaning_choice,
    "hanzi_choice": _hanzi_choice,
    "hanzi_from_pinyin": _hanzi_from_pinyin,
    "pinyin_choice": _pinyin_choice,
    "listening_choice": _listening_choice,
    "listening_pinyin": _listening_pinyin,
    "sentence_listening": _sentence_listening,
    "sentence_meaning": _sentence_meaning,
    "sentence_builder": _sentence_builder,
    "listen_builder": _listen_builder,
    "gap_fill": _gap_fill,
    "dialog_choice": _dialog_choice,
    "correct_choice": _correct_choice,
}


def ladder(target: dict) -> tuple[str, ...]:
    kind = target.get("kind")
    category = target.get("category") or "word"
    if kind == "word":
        return WORD_LADDERS.get(category, WORD_LADDERS["word"])
    if kind == "sentence":
        return SENTENCE_LADDERS.get(category, SENTENCE_LADDERS["default"])
    if kind == "question":
        return ("replay",)
    return ()


def client_supports(question: dict, client_formats: frozenset) -> bool:
    fmt = question.get("format")
    if fmt == "replay":
        return True
    if fmt in LEGACY_BUILDER_FORMATS:
        return "sentence_builder" in client_formats
    return fmt in client_formats


def build_question(target: dict, fmt: str, *, language: str, seed: str) -> dict | None:
    """Tekshiruvdan o'tgan savol yoki `None`."""
    language = language if language in bank.LANGUAGES else "ru"
    builder = _replay if fmt == "replay" else BUILDERS.get(fmt)
    if builder is None:
        return None
    try:
        question = builder(target, language, f"{seed}|{target.get('id')}|{fmt}")
    except (KeyError, TypeError, ValueError):
        return None
    if not question or validate_question(question):
        return None
    return question


def available_questions(
    target: dict,
    *,
    language: str,
    seed: str,
    client_formats: frozenset,
) -> list[dict]:
    """Nishon uchun shu klient ko'rsata oladigan barcha yaroqli savollar (zinapoya tartibida)."""
    result = []
    for fmt in ladder(target):
        question = build_question(target, fmt, language=language, seed=seed)
        if question and client_supports(question, client_formats):
            result.append(question)
    return result


def plan_target(
    target: dict,
    *,
    language: str,
    seed: str,
    client_formats: frozenset,
    passed: set[str],
    limit: int = REQUIRED_FORMATS,
) -> tuple[list[dict], int]:
    """Sessiyaga (savollar, yopish uchun kerakli format soni).

    Hali o'tilmagan turlar oldin olinadi, keyin o'tilganlari (mustahkamlash).
    """
    questions = available_questions(target, language=language, seed=seed, client_formats=client_formats)
    fresh = [question for question in questions if question["format"] not in passed]
    repeat = [question for question in questions if question["format"] in passed]
    chosen = (fresh + repeat)[:limit]
    required = min(REQUIRED_FORMATS, len(questions))
    return chosen, required


# ---------------------------------------------------------- validation ---

def _visible(question: dict) -> str:
    return " ".join(
        str(question.get(field) or "") for field in ("prompt", "sentence", "pinyin")
    )


def validate_question(question: dict) -> str | None:
    """Savol yaroqsiz bo'lsa sababini qaytaradi, yaroqli bo'lsa `None`."""
    if not isinstance(question, dict):
        return "not_a_question"
    fmt = question.get("format")
    if not question.get("id") or not _text(question.get("prompt")):
        return "missing_prompt"
    audio_text = _text(question.get("audio_text"))
    sentence = _text(question.get("sentence"))
    pinyin = _text(question.get("pinyin"))
    if audio_text and not bank.has_cjk(audio_text):
        return "audio_not_chinese"
    if fmt in LISTEN_FORMATS:
        if not audio_text:
            return "listening_without_audio"
        if sentence or pinyin:
            return "listening_text_visible"
    if fmt in _PINYIN_OPTION_FORMATS and pinyin:
        return "pinyin_visible"

    tokens = question.get("tokens")
    if isinstance(tokens, list) and tokens:
        answer = question.get("answer_tokens")
        if not isinstance(answer, list) or len(tokens) < 2 or len(tokens) > 8:
            return "builder_size"
        if sorted(tokens) != sorted(answer) or any(not _text(token) for token in tokens):
            return "builder_tokens_mismatch"
        if list(tokens) == list(answer):
            return "builder_already_ordered"
        if not _text(question.get("correct_answer")):
            return "builder_missing_answer"
        joined = bank.normalize_zh("".join(answer))
        visible = bank.normalize_zh(_visible(question))
        if joined and joined in visible:
            return "builder_answer_visible"
        return None

    options = question.get("options")
    if not isinstance(options, list) or not 2 <= len(options) <= 6:
        return "option_count"
    if any(not _text(option) for option in options):
        return "empty_option"
    keys = [answer_key(option) for option in options]
    if len(set(keys)) != len(keys):
        return "duplicate_options"
    zh_keys = [bank.normalize_zh(option) for option in options if bank.has_cjk(option)]
    if len(set(zh_keys)) != len(zh_keys):
        return "duplicate_options"
    answer_index = question.get("answer_index")
    if not isinstance(answer_index, int) or isinstance(answer_index, bool):
        return "answer_index"
    if not 0 <= answer_index < len(options):
        return "answer_index"
    prompt_key = answer_key(question.get("prompt"))
    if prompt_key in keys:
        return "prompt_equals_option"
    if sentence and answer_key(sentence) in keys and fmt not in _GAP_FORMATS:
        return "sentence_equals_option"
    correct = _text(options[answer_index])
    if bank.has_cjk(correct):
        correct_zh = bank.normalize_zh(correct)
        visible_zh = bank.normalize_zh(_visible(question))
        if correct_zh and correct_zh in visible_zh:
            return "answer_visible"
    else:
        correct_key = answer_key(correct)
        if fmt in _PINYIN_OPTION_FORMATS:
            if bank.pinyin_key(correct) in {bank.pinyin_key(pinyin), bank.pinyin_key(sentence)}:
                return "answer_visible"
        elif len(correct_key) >= 3 and correct_key in answer_key(_visible(question)):
            return "answer_visible"
    if fmt in _HANZI_OPTION_FORMATS and not all(bank.only_cjk_text(option) for option in options):
        return "option_not_hanzi"
    if fmt in _MEANING_OPTION_FORMATS and any(bank.has_cjk(option) for option in options):
        return "option_not_meaning"
    if fmt in _PINYIN_OPTION_FORMATS and any(bank.has_cjk(option) for option in options):
        return "option_not_pinyin"
    if fmt in _GAP_FORMATS and len(bank.GAP_RE.findall(sentence)) != 1:
        return "gap_marker"
    return None


def public_question(question: dict) -> dict:
    """Klientga: baholash maydonlarisiz."""
    hidden = {"answer_index", "answer_tokens", "correct_answer", "explanation", "target_id", "replay_format"}
    public = {key: value for key, value in question.items() if key not in hidden}
    public["autoplay"] = bool(question.get("audio_text")) and (
        question.get("format") in LISTEN_FORMATS
    )
    return public

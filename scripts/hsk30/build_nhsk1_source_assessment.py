"""N1 source-backed checkpoint/transfer question builder.

No generated Chinese or free-form translations: answer keys and language
strings are selected from *the lesson's already validated* vocabulary and
grammar examples. A retry tests a different word/sentence than its exit check.
Original checkpoint cards and server mistake refs are not touched.
"""
from __future__ import annotations

from copy import deepcopy

LANGS = ("uz", "ru", "tj")
VERSION = "n1_exit_check_v1"
FEEDBACK = "n1_context_v1"


def _valid_locales(value: object) -> bool:
    return isinstance(value, dict) and all(
        isinstance(value.get(lang), str) and bool(value[lang].strip())
        for lang in LANGS
    )


def _words(payload: dict) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    for word in payload.get("active_words", []):
        if not isinstance(word, dict):
            continue
        zh = word.get("zh")
        if not isinstance(zh, str) or not zh.strip() or zh in seen:
            continue
        if not word.get("pinyin") or not _valid_locales(word.get("meaning")):
            continue
        seen.add(zh)
        result.append(word)
    return result


def _examples(payload: dict) -> list[tuple[dict, dict]]:
    result = []
    seen: set[tuple[str, str, str]] = set()
    for grammar in payload.get("grammar", []):
        if not isinstance(grammar, dict):
            continue
        for example in grammar.get("examples", []):
            if not isinstance(example, dict) or not example.get("zh"):
                continue
            if not _valid_locales(example.get("translation")):
                continue
            key = tuple(example["translation"][lang] for lang in LANGS)
            if key in seen:
                continue
            seen.add(key)
            result.append((example, grammar))
    return result


def _audio_check(choices: list[dict], target: int, *, src: int, retry: bool) -> dict:
    word = choices[target]
    zh = word["zh"]
    py = word["pinyin"]
    meaning = word["meaning"]
    return {
        "type": "listening_choice",
        "learning_objective": f"n1_source_{src:02d}_listen",
        "learning_feedback": FEEDBACK,
        "learning_retry" if retry else "learning_check": VERSION,
        "title": {
            "uz": "Boshqa so'zni tinglang" if retry else "Tinglab taniy olasizmi?",
            "ru": "Послушайте другое слово" if retry else "Узнайте слово на слух",
            "tj": "Калимаи дигарро гӯш кунед" if retry else "Калимаро аз шунидан шиносед",
        },
        "prompt": {
            "uz": "Eshitilgan xitoycha so'zni tanlang.",
            "ru": "Выберите услышанное китайское слово.",
            "tj": "Калимаи чинии шунидашударо интихоб кунед.",
        },
        "audio_text": zh,
        "audio_pinyin": py,
        "options": [w["zh"] for w in choices],
        "correct_index": target,
        "explanation": {
            "uz": f"{zh} ({py}) — {meaning['uz']}. Talaffuzni qayta tinglab, so'zni farqlang.",
            "ru": f"{zh} ({py}) — {meaning['ru']}. Сравните звучание с другими словами.",
            "tj": f"{zh} ({py}) — {meaning['tj']}. Овозро боз шунида, калимаро фарқ кунед.",
        },
    }


def _meaning_check(options: list[tuple[dict, dict]], target: int, *, src: int, retry: bool) -> dict:
    example, grammar = options[target]
    zh, py = example["zh"], example.get("pinyin") or ""
    translation = example["translation"]
    rules = grammar.get("rule") or {}
    return {
        "type": "meaning_guess",
        "learning_objective": f"n1_source_{src:02d}_sentence",
        "learning_feedback": FEEDBACK,
        "learning_retry" if retry else "learning_check": VERSION,
        "title": {
            "uz": "Yangi jumlani tushuning" if retry else "Jumlani tushundingizmi?",
            "ru": "Поймите другое предложение" if retry else "Проверьте понимание",
            "tj": "Ҷумлаи дигарро фаҳмед" if retry else "Ҷумларо фаҳмидед?",
        },
        "prompt": {
            "uz": f"“{zh}” jumlasining ma'nosini tanlang.",
            "ru": f"Выберите перевод фразы «{zh}».",
            "tj": f"Тарҷумаи ҷумлаи «{zh}»-ро интихоб кунед.",
        },
        "options": [deepcopy(x["translation"]) for x, _ in options],
        "correct_index": target,
        "explanation": {
            lang: f"{zh}" + (f" ({py})" if py else "") +
            f" — {translation[lang]}. " +
            (rules.get(lang, "") if isinstance(rules, dict) else "")
            for lang in LANGS
        },
    }


def apply_nhsk1_source_checks(payload: dict) -> dict:
    """Append source-derived tests for N1 textbook units 2..15, if checkpoint.

    Tests are deterministic and idempotent. Old sections [1,2] retain all
    card offsets. Unit 1 uses the manually authored pilot assessment instead.
    """
    if payload.get("level") != "nhsk1" or not payload.get("checkpoint"):
        return payload
    src = payload.get("source_lesson")
    if type(src) is not int or not 2 <= src <= 15:
        return payload
    words = _words(payload)
    examples = _examples(payload)
    if len(words) < 6 or len(examples) < 3:
        raise ValueError(f"N1 source {src}: insufficient verified vocabulary/grammar examples")

    # Deterministic choices: only words taught in THIS textbook unit.
    # Two distinct correct answers and two distinct source examples.
    widx = [0, 2, 4, 5]
    selected_words = [words[i] for i in widx]
    first_audio = src % 4
    second_audio = (first_audio + 1) % 4

    source_examples = examples[:3]
    first_sentence = src % 3
    second_sentence = (first_sentence + 1) % 3
    exams = [
        _audio_check(selected_words, first_audio, src=src, retry=False),
        _meaning_check(source_examples, first_sentence, src=src, retry=False),
    ]
    retries = [
        _audio_check(selected_words, second_audio, src=src, retry=True),
        _meaning_check(source_examples, second_sentence, src=src, retry=True),
    ]
    sections = [
        {
            "section_no": 3,
            "section_title": {"uz": "Mustaqil bilim tekshiruvi", "ru": "Проверка знаний",
                              "tj": "Санҷиши мустақили дониш"},
            "section_purpose": "learning_exit_check",
            "cards": exams,
        },
        {
            "section_no": 4,
            "section_title": {"uz": "Boshqa misolda qayta sinash", "ru": "Другой пример",
                              "tj": "Мисоли дигар барои санҷиш"},
            "section_purpose": "learning_repair_bank",
            "cards": retries,
        },
    ]
    existing = payload.get("sections")
    if not isinstance(existing, list):
        raise ValueError("N1 checkpoint has no sections")
    ids = [s.get("section_no") for s in existing if isinstance(s, dict)]
    if ids == [1, 2, 3, 4]:
        if existing[2:] != sections:
            raise ValueError(f"N1 source {src}: generated checkpoint drifted")
        return payload
    if ids != [1, 2]:
        raise ValueError(f"N1 source {src}: original checkpoint section IDs changed")

    result = deepcopy(payload)
    result["sections"].extend(sections)
    return result

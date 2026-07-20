"""Generate course_v3_data lesson detail files from the REAL seeded HSK content.

Why: the existing app/static/course_v3_data/<level>/lesson_NN.json files were
produced by a generic template (fake "主题词语" grammar, fake "这个词怎么读"
dialogue, and exercises that show words / characters the learner has not met
yet). That breaks three project rules at once: illogical questions, mixed /
weak Tajik, and content above the learner's level.

The bot already ships expert, HSK-textbook-ordered content with correct
Uzbek / Russian / Tajik for every lesson (the scripts/seed_hsk*_lesson_*.py
files, and scripts/hsk4_lower_seed_data.build_lesson for HSK4 lessons 11-20).
This generator restructures that vetted content into the v3 schema. It does
NOT author any new translation — every uz/ru/tj string is copied verbatim
from the seed data.

Strict level gating:
  * Section order is intro (all new words) -> practice -> dialog, so every
    example only appears after its words have been introduced.
  * Auto-generated practice distractors are drawn ONLY from the cumulative
    "known" vocabulary (this lesson + all earlier lessons of the same and
    lower HSK levels). A later-lesson or higher-level character can never
    appear as an option.
  * Grammar examples and dialogue lines are kept verbatim from the graded
    HSK textbook content (by construction they only use learned vocabulary).

SPLIT (2026-07): har HSK darsligi darsi bir nechta QISQA mini-darsga bo'linadi
(3-4 yangi so'z + mustahkamlash; oxirida checkpoint qismi — dialog + takror).
Qismlar darajada tekis raqamlanadi: lesson_01.json .. lesson_NN.json. HSK dars
-> qismlar xaritasi parts_manifest.json da.

Run:  venv_311/bin/python3.11 scripts/gen_course_v3_from_seed.py [--level hsk4] [--lesson 1]
"""

from __future__ import annotations

import argparse
import importlib
import json
import random
from pathlib import Path

BASE = Path("app/static/course_v3_data")
LEVELS = [("hsk1", 15), ("hsk2", 15), ("hsk3", 20), ("hsk4", 20)]

# Har bir HSK darsligi darsi bir nechta QISQA mini-darsga (qismga) bo'linadi:
# har qismda ko'pi bilan PART_MAX_WORDS yangi so'z o'rgatiladi va shu qism
# ichida mustahkamlanadi (Duolingo uslubi). Dars oxirida alohida "checkpoint"
# qismi bo'ladi: yangi so'z yo'q — dialog + butun dars so'zlarini aralash
# takrorlash. Qismlar darajada TEKIS (flat) raqamlanadi (lesson_01.json,
# lesson_02.json, ...), shuning uchun backend (completed_lessons_count,
# max_lesson, unlock) semantikasi o'zgarmaydi.
PART_MAX_WORDS = 4

# Bitta mini-dars karta byudjeti (charchatmaydigan ~5-7 daqiqa).
PART_CARD_BUDGET = 18

# Deterministic shuffling so re-runs produce identical files.
RNG = random.Random(20240629)


# --------------------------------------------------------------------------
# Seed content loading
# --------------------------------------------------------------------------
def load_seed_lesson(level: str, order: int) -> dict:
    """Return the canonical (post-materials) lesson dict for a level/order."""
    if level == "hsk4" and order >= 11:
        mod = importlib.import_module("scripts.hsk4_lower_seed_data")
        return mod.build_lesson(order)
    mod = importlib.import_module(f"scripts.seed_{level}_lesson_{order:02d}")
    return dict(mod.LESSON)


def loadjson(value, default):
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    return json.loads(value)


def l3(d: dict, base: str) -> dict:
    """Build a {uz,ru,tj} dict from base_uz / base_ru / base_tj keys."""
    uz = d.get(f"{base}_uz", "")
    return {
        "uz": uz,
        "ru": d.get(f"{base}_ru") or uz,
        "tj": d.get(f"{base}_tj") or uz,
    }


def t3(d: dict) -> dict:
    """Build {uz,ru,tj} from direct uz/ru/tj keys (grammar examples, dialogue lines)."""
    uz = d.get("uz", "")
    return {"uz": uz, "ru": d.get("ru") or uz, "tj": d.get("tj") or uz}


def word_meaning(w: dict) -> dict:
    uz = w.get("uz", "")
    return {"uz": uz, "ru": w.get("ru") or uz, "tj": w.get("tj") or uz}


def parse_title(seed: dict):
    """Some lessons (HSK3) store `title` as a JSON object string holding the
    Chinese title plus uz/ru/tj. Return (zh_title, translation|None)."""
    raw = seed.get("title", "")
    if isinstance(raw, str) and raw.strip().startswith("{"):
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict) and obj.get("zh"):
                return obj["zh"], t3(obj)
        except (ValueError, TypeError):
            pass
    if isinstance(raw, dict) and raw.get("zh"):
        return raw["zh"], t3(raw)
    return raw, None


# --------------------------------------------------------------------------
# Schema sub-builders
# --------------------------------------------------------------------------
def build_active_words(vocab: list[dict]) -> list[dict]:
    out = []
    for i, w in enumerate(vocab, 1):
        out.append(
            {
                "no": i,
                "zh": w["zh"],
                "pinyin": w.get("pinyin", ""),
                "pos": w.get("pos", ""),
                "meaning": word_meaning(w),
            }
        )
    return out


def build_grammar(grammar: list[dict]) -> list[dict]:
    out = []
    for g in grammar:
        examples = []
        for ex in g.get("examples", []):
            examples.append(
                {
                    "zh": ex.get("zh", ""),
                    "pinyin": ex.get("pinyin", ""),
                    "translation": t3(ex),  # ex has uz/ru/tj directly
                }
            )
        out.append(
            {
                "no": g.get("no"),
                "title": l3(g, "title"),
                "title_zh": g.get("title_zh", ""),
                "rule": l3(g, "rule"),
                "examples": examples,
            }
        )
    return out


def build_dialogues(blocks: list[dict]) -> list[dict]:
    out = []
    for b in blocks:
        lines = []
        for ln in b.get("dialogue", []):
            lines.append(
                {
                    "speaker": ln.get("speaker", ""),
                    "zh": ln.get("zh", ""),
                    "pinyin": ln.get("pinyin", ""),
                    "text": t3(ln),  # ln has uz/ru/tj directly
                }
            )
        out.append({"scene": l3(b, "scene"), "dialogue": lines})
    return out


# --------------------------------------------------------------------------
# Practice cards (level-gated)
# --------------------------------------------------------------------------
def _distinct_pad(options, pool, key, need=4):
    """Pad `options` up to `need` distinct entries using `pool` (gated)."""
    seen = {key(o) for o in options}
    for cand in pool:
        if len(options) >= need:
            break
        if key(cand) in seen:
            continue
        options.append(cand)
        seen.add(key(cand))
    return options


# --------------------------------------------------------------------------
# Interactive (Duolingo-style) builders: sentence_builder, listening_choice,
# dialog_cloze. Every token / option stays strictly level-gated.
# --------------------------------------------------------------------------
_PUNCT = set("，。！？、：；,.!?…·～~\"'“”‘’（）()《》〈〉<>「」『』 　　")


def segment_zh(sentence: str, known_words: set[str]) -> list[str] | None:
    """Greedy longest-match a Chinese sentence into known vocabulary words.

    Punctuation / latin / digits are dropped. Returns the ordered word tokens,
    or None if any Han character cannot be covered by already-learned vocabulary
    (so we never build a gap/builder exercise above the learner's level)."""
    toks: list[str] = []
    i, n = 0, len(sentence)
    while i < n:
        ch = sentence[i]
        if ch in _PUNCT or ch.isspace():
            i += 1
            continue
        if not ("一" <= ch <= "鿿"):
            i += 1  # skip non-Han (latin, digits) without failing the whole sentence
            continue
        matched = None
        for j in range(min(n, i + 5), i, -1):  # try longest known word first
            seg = sentence[i:j]
            if seg in known_words:
                matched = seg
                break
        if matched:
            toks.append(matched)
            i += len(matched)
        else:
            return None  # an un-learned character -> not gated, skip this sentence
    return toks or None


def make_builder_card(zh, pinyin, translation, known_words, pool) -> dict | None:
    """sentence_builder: rebuild a real sentence from shuffled word tiles."""
    ans = segment_zh(zh, known_words)
    if not ans or not (2 <= len(ans) <= 8):
        return None
    # 1-2 gated distractor tiles (real learned words not used in the answer).
    distract: list[str] = []
    for x in pool:
        w = x.get("zh", "")
        if w and w not in ans and w not in distract and 1 <= len(w) <= 3:
            distract.append(w)
        if len(distract) >= 2:
            break
    order = ans + distract
    RNG.shuffle(order)
    return {
        "type": "sentence_builder",
        "sentence": translation,  # {uz,ru,tj} prompt (what to say)
        "tokens": order,
        "answer_tokens": ans,
        "explanation": {
            "uz": f"{zh} — {pinyin}".strip(" —"),
            "ru": f"{zh} — {pinyin}".strip(" —"),
            "tj": f"{zh} — {pinyin}".strip(" —"),
        },
    }


_STRIP_PUNCT = ",.!?…—–:;()«»\"„“”¡¿"


def _split_words(s: str) -> list[str]:
    out = []
    for t in str(s or "").split():
        t = t.strip(_STRIP_PUNCT)
        if t:
            out.append(t)
    return out


def make_reverse_builder_card(zh, pinyin, translation, other_translations, lr) -> dict | None:
    """Duolingo yadro mashqi (teskari builder): ustoz xitoy gapni aytadi,
    o'quvchi TARJIMASINI ona tili so'z-plitkalaridan yig'adi. Har uch til uchun
    alohida plitka to'plami; chalg'ituvchi so'zlar shu darsning boshqa real
    tarjimalaridan olinadi."""
    if not zh:
        return None
    toks: dict[str, list[str]] = {}
    for lang in ("uz", "ru", "tj"):
        t = _split_words(translation.get(lang, ""))
        if not (2 <= len(t) <= 9):
            return None
        toks[lang] = t
    bank: dict[str, list[str]] = {}
    for lang in ("uz", "ru", "tj"):
        distract: list[str] = []
        for otr in other_translations:
            for w in _split_words(otr.get(lang, "")):
                if w and w not in toks[lang] and w not in distract:
                    distract.append(w)
                if len(distract) >= 2:
                    break
            if len(distract) >= 2:
                break
        order = toks[lang] + distract
        lr.shuffle(order)
        bank[lang] = order
    return {
        "type": "reverse_builder",
        "zh": zh,
        "pinyin": pinyin,
        "translation": translation,
        "tokens": bank,
        "answer_tokens": toks,
        "explanation": {
            "uz": f"{zh} — {translation['uz']}",
            "ru": f"{zh} — {translation['ru']}",
            "tj": f"{zh} — {translation['tj']}",
        },
    }


def make_listen_card(target, line_pool) -> dict | None:
    """listening_choice: hear a sentence, pick which one you heard."""
    zh = target.get("zh", "")
    if not zh:
        return None
    opts = [zh]
    for ln in line_pool:
        if len(opts) >= 4:
            break
        z = ln.get("zh", "")
        if z and z not in opts:
            opts.append(z)
    if len(opts) < 3:
        return None
    RNG.shuffle(opts)
    ci = opts.index(zh)
    tr = t3(target)
    return {
        "type": "listening_choice",
        "title": {
            "uz": "Eshitganingizni tanlang",
            "ru": "Выберите, что вы услышали",
            "tj": "Он чи шунидед, интихоб кунед",
        },
        "audio_text": zh,
        "pinyin": target.get("pinyin", ""),
        "options": opts,
        "correct_index": ci,
        "explanation": {
            "uz": f"{zh} — {tr['uz']}",
            "ru": f"{zh} — {tr['ru']}",
            "tj": f"{zh} — {tr['tj']}",
        },
    }


def make_cloze_card(block, distractor_lines) -> dict | None:
    """dialog_cloze: one reply in a real dialogue is hidden, pick the right line."""
    lines = [ln for ln in block.get("dialogue", []) if ln.get("zh")]
    if len(lines) < 2:
        return None
    bi = len(lines) - 1  # blank the final reply
    correct = lines[bi]["zh"]
    opts = [correct]
    for z in distractor_lines:
        if len(opts) >= 4:
            break
        if z and z not in opts:
            opts.append(z)
    if len(opts) < 3:
        return None
    RNG.shuffle(opts)
    ci = opts.index(correct)
    disp = [
        {
            "speaker": ln.get("speaker", ""),
            "zh": "" if k == bi else ln.get("zh", ""),
            "blank": k == bi,
        }
        for k, ln in enumerate(lines)
    ]
    return {
        "type": "dialog_cloze",
        "title": {
            "uz": "Dialogni to'ldiring",
            "ru": "Дополните диалог",
            "tj": "Гуфтугӯро пурра кунед",
        },
        "lines": disp,
        "options": opts,
        "correct_index": ci,
        "explanation": {
            "uz": f"To'g'ri javob: {correct}",
            "ru": f"Правильный ответ: {correct}",
            "tj": f"Ҷавоби дуруст: {correct}",
        },
    }


def make_char_gap_card(line, known_chars) -> dict | None:
    """Hide ONE character of a real dialogue line; pick the right hanzi.
    Distractor characters are drawn only from already-learned vocabulary."""
    zh = line.get("zh", "")
    han = [ch for ch in zh if "一" <= ch <= "鿿"]
    if len(han) < 2:
        return None
    # prefer a character that occurs exactly once (unambiguous blank)
    once = [ch for ch in han if zh.count(ch) == 1]
    target = (once or han)[0]
    opts = [target]
    for ch in known_chars:
        if len(opts) >= 4:
            break
        if ch != target and ch not in opts:
            opts.append(ch)
    if len(opts) < 3:
        return None
    RNG.shuffle(opts)
    tr = t3(line)
    return {
        "type": "gap_fill",
        "sentence": zh.replace(target, "____", 1),
        "prompt": {
            "uz": "Bo'sh joyga mos ieroglifni tanlang:",
            "ru": "Выберите подходящий иероглиф:",
            "tj": "Иероглифи мувофиқро интихоб кунед:",
        },
        "options": opts,
        "correct_index": opts.index(target),
        "explanation": {
            "uz": f"To'g'ri: {target} — {zh} ({tr['uz']})",
            "ru": f"Верно: {target} — {zh} ({tr['ru']})",
            "tj": f"Дуруст: {target} — {zh} ({tr['tj']})",
        },
    }


# --------------------------------------------------------------------------
# Shared multiple-choice builders. Used by BOTH the intro section (teach a word
# then immediately check it — Duolingo interleaving) and the practice section,
# so the same gated logic produces every check. Distractors are padded only
# from `pool` (current lesson + earlier lessons), never future / higher words.
# --------------------------------------------------------------------------
def mc_meaning(w, pool):
    correct = word_meaning(w)
    opts = [correct]
    _distinct_pad(opts, [word_meaning(x) for x in pool], key=lambda m: m["uz"])
    order = opts[:]
    RNG.shuffle(order)
    return {
        "type": "meaning_guess",
        "prompt": {
            "uz": f"{w['zh']} so'zining ma'nosini tanlang:",
            "ru": f"Выберите значение слова {w['zh']}:",
            "tj": f"Маънои калимаи {w['zh']}-ро интихоб кунед:",
        },
        "title": {"uz": "Ma'nosi nima?", "ru": "Что означает?", "tj": "Маъно чист?"},
        "options": order,
        "correct_index": order.index(correct),
        "explanation": {
            "uz": f"{w['zh']} = {correct['uz']} ({w.get('pinyin','')})",
            "ru": f"{w['zh']} = {correct['ru']} ({w.get('pinyin','')})",
            "tj": f"{w['zh']} = {correct['tj']} ({w.get('pinyin','')})",
        },
    }


def mc_pinyin(w, pool):
    right = w.get("pinyin", "")
    opts = [right]
    _distinct_pad(opts, [x.get("pinyin", "") for x in pool], key=lambda s: s)
    order = opts[:]
    RNG.shuffle(order)
    return {
        "type": "pinyin_choice",
        "prompt": {
            "uz": f"{w['zh']} talaffuzini tanlang:",
            "ru": f"Выберите произношение {w['zh']}:",
            "tj": f"Талаффузи {w['zh']}-ро интихоб кунед:",
        },
        "title": {"uz": "Qanday o'qiladi?", "ru": "Как читается?", "tj": "Чӣ хел хонда мешавад?"},
        "options": order,
        "correct_index": order.index(right),
        "explanation": {
            "uz": f"{w['zh']} — {right}",
            "ru": f"{w['zh']} — {right}",
            "tj": f"{w['zh']} — {right}",
        },
    }


def mc_translation(w, pool):
    m = word_meaning(w)
    opts = [w["zh"]]
    _distinct_pad(opts, [x["zh"] for x in pool], key=lambda s: s)
    order = opts[:]
    RNG.shuffle(order)
    return {
        "type": "translation_choice",
        "prompt": {
            "uz": f"'{m['uz']}' xitoycha qaysi?",
            "ru": f"'{m['ru']}' по-китайски?",
            "tj": f"'{m['tj']}' ба хитоӣ кадом аст?",
        },
        "title": {"uz": "Xitoycha qanday?", "ru": "Как по-китайски?", "tj": "Ба хитоӣ чӣ тавр?"},
        "options": order,
        "correct_index": order.index(w["zh"]),
        "explanation": {
            "uz": f"{m['uz']} = {w['zh']} ({w.get('pinyin','')})",
            "ru": f"{m['ru']} = {w['zh']} ({w.get('pinyin','')})",
            "tj": f"{m['tj']} = {w['zh']} ({w.get('pinyin','')})",
        },
    }


def mc_hanzi(w, pool):
    opts = [w["zh"]]
    _distinct_pad(opts, [x["zh"] for x in pool], key=lambda s: s)
    order = opts[:]
    RNG.shuffle(order)
    return {
        "type": "hanzi_choice",
        "prompt": {
            "uz": f"{w.get('pinyin','')} qaysi ieroglif?",
            "ru": f"Какой иероглиф читается {w.get('pinyin','')}?",
            "tj": f"{w.get('pinyin','')} кадом иероглиф аст?",
        },
        "title": {"uz": "Ieroglifni tanlang", "ru": "Выберите иероглиф", "tj": "Иероглифро интихоб кунед"},
        "options": order,
        "correct_index": order.index(w["zh"]),
        "explanation": {
            "uz": f"{w['zh']} = {word_meaning(w)['uz']} ({w.get('pinyin','')})",
            "ru": f"{w['zh']} = {word_meaning(w)['ru']} ({w.get('pinyin','')})",
            "tj": f"{w['zh']} = {word_meaning(w)['tj']} ({w.get('pinyin','')})",
        },
    }


def mc_match(words):
    return {
        "type": "match_pairs",
        "pairs": [[w["zh"], word_meaning(w)] for w in words],
        "explanation": {
            "uz": "Juftliklar darsdagi yangi so'zlardan olindi.",
            "ru": "Пары взяты из новых слов урока.",
            "tj": "Ҷуфтҳо аз калимаҳои нави дарс гирифта шудаанд.",
        },
    }


def pron_card(w):
    return {
        "type": "pronunciation",
        "phrase": w["zh"],
        "pinyin": w.get("pinyin", ""),
        "translation": word_meaning(w),
    }


def pron_sentence_card(line) -> dict | None:
    """Pronunciation drill on a REAL dialogue line (sentence-level speaking).
    Kept short (<=10 Han chars) because the mic recording auto-stops at ~4s."""
    zh = line.get("zh", "")
    han = [ch for ch in zh if "一" <= ch <= "鿿"]
    if not (2 <= len(han) <= 10):
        return None
    return {
        "type": "pronunciation",
        "phrase": zh,
        "pinyin": line.get("pinyin", ""),
        "translation": t3(line),
    }


def make_word_listen_card(w, pool) -> dict | None:
    """listening_choice on a single WORD: hear it, pick the right hanzi.
    Distractors come only from the gated pool (this + earlier lessons)."""
    zh = w.get("zh", "")
    if not zh:
        return None
    opts = [zh]
    for x in pool:
        if len(opts) >= 4:
            break
        z = x.get("zh", "")
        if z and z not in opts:
            opts.append(z)
    if len(opts) < 3:
        return None
    RNG.shuffle(opts)
    m = word_meaning(w)
    py = w.get("pinyin", "")
    return {
        "type": "listening_choice",
        "title": {
            "uz": "Tinglang — qaysi so'z?",
            "ru": "Послушайте — какое слово?",
            "tj": "Гӯш кунед — кадом калима?",
        },
        "audio_text": zh,
        "pinyin": py,
        "options": opts,
        "correct_index": opts.index(zh),
        "explanation": {
            "uz": f"{zh} — {m['uz']} ({py})",
            "ru": f"{zh} — {m['ru']} ({py})",
            "tj": f"{zh} — {m['tj']} ({py})",
        },
    }


# Har qism o'z "arxetipi"da o'tadi — bir xil shablon zerikishini yo'qotish uchun.
# listen: tinglash ko'proq; build: gap yig'ish ko'proq; speak: talaffuz ko'proq;
# mix: juftlash ko'proq. Level + flat qism raqami bo'yicha deterministik aylanadi
# (ketma-ket qismlar har doim boshqa arxetip oladi).
ARCHETYPES = ("listen", "build", "speak", "mix")


def make_grammar_meaning_card(grammar_raw, known_words) -> dict | None:
    """A sentence-level comprehension check: show a translation, pick the real
    Chinese sentence that matches it among OTHER real grammar example sentences.
    Everything is authentic textbook content, so it stays level-gated."""
    sents = []  # (zh, pinyin, {uz,ru,tj})
    for g in grammar_raw:
        for ex in g.get("examples", []):
            zh = ex.get("zh", "")
            if zh and all(z[0] != zh for z in sents):
                sents.append((zh, ex.get("pinyin", ""), t3(ex)))
    if len(sents) < 3:
        return None
    RNG.shuffle(sents)
    target = sents[0]
    opts = [target[0]] + [s[0] for s in sents[1:4]]
    RNG.shuffle(opts)
    tr = target[2]
    return {
        "type": "quick_quiz",
        "prompt": {
            "uz": f"«{tr['uz']}» — xitoychada qaysi biri?",
            "ru": f"«{tr['ru']}» — какое предложение по-китайски?",
            "tj": f"«{tr['tj']}» — кадом ҷумла ба хитоӣ аст?",
        },
        "title": {"uz": "To'g'ri gapni tanlang", "ru": "Выберите верное предложение", "tj": "Ҷумлаи дурустро интихоб кунед"},
        "options": opts,
        "correct_index": opts.index(target[0]),
        "explanation": {
            "uz": f"{target[0]} — {target[1]}",
            "ru": f"{target[0]} — {target[1]}",
            "tj": f"{target[0]} — {target[1]}",
        },
    }


def build_part_intro(chunk, chunk_active, taught, known_prior, flat_n, lr,
                     lean: bool = False) -> list[dict]:
    """Qism introsi (Duolingo interleaving): 3-4 yangi so'zning HAR BIRI uchun
    flash-karta -> DARHOL tekshiruv (format so'zma-so'z aylanadi), bitta tez
    talaffuz, oxirida match_pairs rekap. Shu bilan har yangi so'z o'z qismida
    kamida 3-4 marta uchraydi; qism mashqi va checkpoint yana qo'shadi.

    NOTE: the flash card uses the BUILT active_word shape (`meaning` sub-dict),
    while the check builders (mc_*) need the RAW vocab shape (top-level uz/ru/tj),
    so both lists are taken and kept index-aligned.

    Distraktorlar FAQAT shu paytgacha o'rgatilgan so'zlardan (`taught` — shu
    darsning 1..k chunklari + `known_prior`) — o'quvchi hali ko'rmagan ieroglif
    variant sifatida ham chiqmaydi."""
    cards: list[dict] = []
    if not chunk:
        return cards
    pool = list(taught) + list(known_prior)
    # 5 rotating check formats (incl. audio) so consecutive parts open with a
    # different drill sequence — kills the "same template every part" feel.
    check_cycle = [mc_meaning, mc_hanzi, mc_pinyin, mc_translation, make_word_listen_card]
    ci = (flat_n - 1) % len(check_cycle)
    pron_at = (flat_n - 1) % len(chunk)
    for i, w in enumerate(chunk):
        cards.append({"type": "active_word", "word": chunk_active[i]})
        if i == pron_at:
            cards.append(pron_card(w))
        card = check_cycle[ci % len(check_cycle)](w, pool)
        ci += 1
        if card:
            cards.append(card)
    # Birinchi so'zga IKKINCHI formatdagi qo'shimcha tekshiruv (eng eski so'z
    # unutilmasin — mini spaced repetition qism ichida). `lean` rejimda (qismda
    # katta grammatika bo'lsa) tashlab ketiladi — byudjet oshib ketmasin.
    if len(chunk) >= 2 and not lean:
        card = check_cycle[ci % len(check_cycle)](chunk[0], pool)
        if card:
            cards.append(card)
    if len(chunk) >= 3:
        cards.append(mc_match(chunk))
    return cards


def build_grammar_section(grammar_raw, vocab, known_prior, order=1, lr=None) -> list[dict]:
    """Interactive grammar, Duolingo-style: for each rule, TEACH it (the panda
    "Li ustoz" card) then IMMEDIATELY drill it (build the example from tiles or a
    gap-fill), instead of dumping every rule first and every drill after. A final
    sentence-comprehension check adds variety. Everything stays level-gated."""
    lr = lr or random.Random(order)
    cards: list[dict] = []
    if not grammar_raw or not vocab:
        return cards
    pool = vocab + known_prior
    known_words = {x.get("zh", "") for x in pool if x.get("zh")}
    grammar_shaped = build_grammar(grammar_raw)  # {uz,ru,tj} teacher-card shape

    for gi, g in enumerate(grammar_raw):
        # 1) Teach this rule (rendered by cardGrammar via the "_grammar" type).
        cards.append({"type": "_grammar", "g": grammar_shaped[gi]})
        # 2) Immediately drill THIS rule: prefer rebuilding its example, else a
        #    gap-fill of a current-lesson word inside one of its examples.
        drill = None
        for ex in g.get("examples", []):
            drill = make_builder_card(ex.get("zh", ""), ex.get("pinyin", ""), t3(ex), known_words, pool)
            if drill:
                break
        if not drill:
            drill = _grammar_gap_fill(g, vocab, pool)
        if drill:
            cards.append(drill)

    # 3) One sentence-level comprehension check across the rules (variety).
    gm = make_grammar_meaning_card(grammar_raw, known_words)
    if gm:
        cards.append(gm)
    return cards


def _grammar_gap_fill(g, vocab, pool) -> dict | None:
    """Blank a current-lesson word inside one real example of grammar rule g."""
    for w in vocab:
        if not (w.get("zh") and len(w["zh"]) >= 2):
            continue
        for ex in g.get("examples", []):
            zh = ex.get("zh", "")
            if w["zh"] in zh:
                opts = [w["zh"]]
                _distinct_pad(opts, [x["zh"] for x in pool], key=lambda s: s)
                RNG.shuffle(opts)
                return {
                    "type": "gap_fill",
                    "sentence": zh.replace(w["zh"], "____", 1),
                    "prompt": {
                        "uz": "Bo'sh joyga mos so'zni tanlang:",
                        "ru": "Выберите слово для пропуска:",
                        "tj": "Калимаи мувофиқро барои ҷойи холӣ интихоб кунед:",
                    },
                    "options": opts,
                    "correct_index": opts.index(w["zh"]),
                    "explanation": {
                        "uz": f"To'g'ri: {w['zh']} ({w.get('pinyin','')}) — {word_meaning(w)['uz']}",
                        "ru": f"Верно: {w['zh']} ({w.get('pinyin','')}) — {word_meaning(w)['ru']}",
                        "tj": f"Дуруст: {w['zh']} ({w.get('pinyin','')}) — {word_meaning(w)['tj']}",
                    },
                }
    return None



def build_part_practice(chunk, taught, known_prior, grammar_all, dialogue_raw,
                        flat_n, lr, archetype: str, budget: int) -> list[dict]:
    """Qism mini-mashqi: yangi so'zlar endi GAP ICHIDA ishlatiladi ("qayerda va
    qanday" konteksti) — dialog satri / grammatika misolidan builder, tinglash
    va teskari builder; ustiga bitta spaced-review (oldingi qism yoki dars
    so'zi). Distraktorlar faqat o'rganilgan so'zlardan. Talaffuz doim oxirida.

    `budget` — qismning umumiy karta byudjetidan mashqqa qolgan joy; ortiqcha
    kartalar tashlab yuboriladi (qism 12-18 kartadan oshmasin)."""
    cards: list[dict] = []
    if not chunk:
        return cards
    pool = list(taught) + list(known_prior)
    known_words = {x.get("zh", "") for x in pool if x.get("zh")}
    chunk_zh = {w.get("zh", "") for w in chunk if w.get("zh")}
    dialogue_raw = dialogue_raw or []
    all_lines = [ln for b in dialogue_raw for ln in b.get("dialogue", []) if ln.get("zh")]

    # Kontekst nomzodlari: shu qism so'zi QATNASHGAN va o'rganilgan so'zlar
    # bilan to'liq segmentlanadigan real gaplar (dialog satrlari + grammatika
    # misollari). Aynan shular so'zni "ishlatishni" o'rgatadi.
    ctx: list[dict] = []
    ctx_dialog: list[dict] = []  # faqat dialog satrlari (tinglash uchun)
    gram_examples = [ex for g in (grammar_all or []) for ex in g.get("examples", []) if ex.get("zh")]
    for ln in all_lines + gram_examples:
        toks = segment_zh(ln.get("zh", ""), known_words)
        if toks and any(t in chunk_zh for t in toks):
            ctx.append(ln)
            if ln in all_lines:
                ctx_dialog.append(ln)

    varied: list[dict] = []

    # 1) Gap yig'ish: kontekst gapini plitkalardan qurish.
    if ctx:
        ln = ctx[(flat_n - 1) % len(ctx)]
        bc = make_builder_card(ln.get("zh", ""), ln.get("pinyin", ""), t3(ln), known_words, pool)
        if bc:
            varied.append(bc)

    # 2) Tinglash: kontekstdagi dialog satri (variantlar ham dialog satrlari —
    #    gate saqlanadi); bo'lmasa — qism so'zining o'zi.
    lc = None
    if ctx_dialog:
        lc = make_listen_card(ctx_dialog[flat_n % len(ctx_dialog)], all_lines)
    if not lc:
        lc = make_word_listen_card(chunk[(flat_n - 1) % len(chunk)], pool)
    if lc:
        varied.append(lc)

    # 3) Teskari builder: xitoy gap eshitiladi — tarjimasi ona tili
    #    plitkalaridan yig'iladi (Duolingo yadro mashqi).
    if ctx:
        trs = [t3(x) for x in ctx]
        st = (flat_n - 1) % len(ctx)
        for k in range(len(ctx)):
            ri = (st + k) % len(ctx)
            rb = make_reverse_builder_card(
                ctx[ri].get("zh", ""), ctx[ri].get("pinyin", ""), trs[ri],
                trs[:ri] + trs[ri + 1:], lr
            )
            if rb:
                varied.append(rb)
                break

    # 4) Spaced review: oldingi qism/dars so'zidan bitta tekshiruv.
    review_pool = [w for w in taught if w.get("zh") not in chunk_zh] or list(known_prior)
    if review_pool:
        mc_builders = [mc_meaning, mc_pinyin, mc_translation, mc_hanzi]
        w = review_pool[(flat_n - 1) % len(review_pool)]
        varied.append(mc_builders[flat_n % len(mc_builders)](w, pool))

    # 5) Arxetip qo'shimchasi — qismlar bir-biridan farq qilsin.
    if archetype == "listen":
        wl = make_word_listen_card(chunk[flat_n % len(chunk)], pool)
        if wl:
            varied.append(wl)
    elif archetype == "build" and len(ctx) >= 2:
        ln = ctx[(flat_n + 1) % len(ctx)]
        bc = make_builder_card(ln.get("zh", ""), ln.get("pinyin", ""), t3(ln), known_words, pool)
        if bc:
            varied.append(bc)
    elif archetype == "speak":
        varied.append(pron_card(chunk[flat_n % len(chunk)]))
    elif len(chunk) >= 3:  # "mix"
        varied.append(mc_match(chunk))

    # Tartib har qismda boshqacha; byudjetga sig'dirib, talaffuz doim oxirida.
    lr.shuffle(varied)
    cards = [c for c in varied if c][: max(2, budget - 1)]
    cards.append(pron_card(chunk[(flat_n - 1) % len(chunk)]))
    return cards


def build_dialog_quizzes(blocks: list[dict]) -> list[dict]:
    """quick_quiz cards whose options are the REAL lines of the first dialogue
    block (authentic + automatically level-gated)."""
    cards: list[dict] = []
    if not blocks:
        return cards
    lines = [ln for ln in blocks[0].get("dialogue", []) if ln.get("zh")]
    # Distractor pool: every distinct line from all dialogue blocks of this
    # lesson (authentic + automatically level-gated).
    distractor_pool = []
    for b in blocks:
        for ln in b.get("dialogue", []):
            if ln.get("zh") and ln["zh"] not in distractor_pool:
                distractor_pool.append(ln["zh"])
    if len(lines) < 1 or len(distractor_pool) < 2:
        return cards

    def quiz(target_idx, prompt):
        correct = lines[target_idx]["zh"]
        opts = [correct]
        for zh in distractor_pool:
            if len(opts) >= 4:
                break
            if zh not in opts:
                opts.append(zh)
        order = opts[:]
        RNG.shuffle(order)
        ci = order.index(correct)
        return {
            "type": "quick_quiz",
            "prompt": prompt,
            "title": {"uz": "Dialogdan savol:", "ru": "Вопрос по диалогу:", "tj": "Савол аз гуфтугӯ:"},
            "options": order,
            "correct_index": ci,
            "explanation": {
                "uz": f"To'g'ri javob: {correct}",
                "ru": f"Правильный ответ: {correct}",
                "tj": f"Ҷавоби дуруст: {correct}",
            },
        }

    first = lines[0]
    cards.append(
        quiz(
            0,
            {
                "uz": f"Dialogda {first['speaker']} avval nima deydi?",
                "ru": f"Что {first['speaker']} говорит в начале диалога?",
                "tj": f"Дар гуфтугӯ {first['speaker']} аввал чӣ мегӯяд?",
            },
        )
    )
    last = lines[-1]
    if last["zh"] != first["zh"]:
        cards.append(
            quiz(
                len(lines) - 1,
                {
                    "uz": f"Dialog oxirida {last['speaker']} nima deydi?",
                    "ru": f"Что {last['speaker']} говорит в конце диалога?",
                    "tj": f"Дар охири гуфтугӯ {last['speaker']} чӣ мегӯяд?",
                },
            )
        )
    return cards


def build_dialog_section(blocks: list[dict], pool: list[dict], lr=None) -> list[dict]:
    """Fully interactive dialogue section (no passive text dump): hear a line
    and pick what was said, fill a missing character, complete the dialogue,
    then a comprehension question. Everything stays level-gated.

    The audio "listen — what did they say?" card opens the section, but the
    middle exercises (character gap, cloze, comprehension) are shuffled per
    lesson (`lr`) so the dialogue stage isn't the same sequence every time."""
    lr = lr or random.Random(1)
    cards: list[dict] = []
    if not blocks:
        return cards
    line_objs = [ln for b in blocks for ln in b.get("dialogue", []) if ln.get("zh")]
    line_pool = []
    for ln in line_objs:
        if ln["zh"] not in line_pool:
            line_pool.append(ln["zh"])

    # 1) Audio first: "listen — what did they say?"
    if line_objs:
        lc = make_listen_card(line_objs[0], line_objs)
        if lc:
            lc["title"] = {
                "uz": "Tinglang — nima dedi?",
                "ru": "Послушайте — что сказали?",
                "tj": "Гӯш кунед — чӣ гуфт?",
            }
            cards.append(lc)

    # Middle + comprehension exercises, shuffled per lesson for variety.
    rest: list[dict] = []

    # Fill the missing character in a real dialogue line.
    known_chars = {ch for w in pool for ch in w.get("zh", "") if "一" <= ch <= "鿿"}
    for ln in line_objs:
        cg = make_char_gap_card(ln, known_chars)
        if cg:
            rest.append(cg)
            break

    # Complete the dialogue (pick the missing reply).
    cloze = make_cloze_card(blocks[0], line_pool)
    if cloze:
        rest.append(cloze)

    # Comprehension question(s).
    rest.extend(build_dialog_quizzes(blocks))

    lr.shuffle(rest)
    cards.extend(rest)

    # Speaking finale: repeat one short REAL dialogue line aloud ("endi o'zingiz
    # ayting"). The chosen line rotates per lesson so it isn't always the first.
    sayable = [ln for ln in line_objs if pron_sentence_card(ln)]
    if sayable:
        card = pron_sentence_card(lr.choice(sayable))
        if card:
            cards.append(card)
    return cards


def build_checkpoint_sections(vocab, known_prior, grammar_raw, dialogue_raw,
                              flat_n, lr) -> list[dict]:
    """HSK darsining YAKUNIY mustahkamlash qismi: yangi so'z YO'Q — butun dars
    so'zlari aralash takrorlanadi (match, aylanuvchi MC, teskari builder,
    grammatika-tushunish), so'ng to'liq interaktiv dialog bo'limi. Bu qism
    tugaganda dars (bo'lim) yopiladi — frontendda katta bayram."""
    pool = list(vocab) + list(known_prior)
    known_words = {x.get("zh", "") for x in pool if x.get("zh")}
    review: list[dict] = []
    if len(vocab) >= 3:
        review.append(mc_match(vocab[: min(4, len(vocab))]))
    if len(vocab) >= 8:
        review.append(mc_match(vocab[4:8]))

    # Aylanuvchi formatdagi tekshiruvlar — dars so'zlari bo'ylab sakrab yuradi.
    if vocab:
        mc_builders = [mc_meaning, mc_pinyin, mc_translation, mc_hanzi, make_word_listen_card]
        st = (flat_n - 1) % len(vocab)
        for k in range(min(3, len(vocab))):
            w = vocab[(st + 2 * k) % len(vocab)]
            c = mc_builders[(flat_n + k) % len(mc_builders)](w, pool)
            if c:
                review.append(c)

    gm = make_grammar_meaning_card(grammar_raw or [], known_words)
    if gm:
        review.append(gm)

    # Teskari builder: dars gaplaridan biri (dialog satri / grammatika misoli).
    rb_cand = [ln for b in (dialogue_raw or []) for ln in b.get("dialogue", []) if ln.get("zh")]
    rb_cand += [ex for g in (grammar_raw or []) for ex in g.get("examples", []) if ex.get("zh")]
    if rb_cand:
        trs = [t3(x) for x in rb_cand]
        st = (flat_n - 1) % len(rb_cand)
        for k in range(len(rb_cand)):
            ri = (st + k) % len(rb_cand)
            rb = make_reverse_builder_card(
                rb_cand[ri].get("zh", ""), rb_cand[ri].get("pinyin", ""), trs[ri],
                trs[:ri] + trs[ri + 1:], lr
            )
            if rb:
                review.append(rb)
                break

    lr.shuffle(review)
    review = review[:7]

    dialog_cards = build_dialog_section(dialogue_raw or [], pool, lr)

    sections = [{
        "section_no": 1,
        "section_title": {"uz": "Takrorlash", "ru": "Повторение", "tj": "Такрор"},
        "section_purpose": "practice",
        "cards": review,
    }]
    if dialog_cards:
        sections.append({
            "section_no": 2,
            "section_title": {"uz": "Dialog", "ru": "Диалог", "tj": "Гуфтугӯ"},
            "section_purpose": "dialog",
            "cards": dialog_cards,
        })
    return sections


# --------------------------------------------------------------------------
# Darsni qismlarga bo'lish (split plan) va qism quruvchisi
# --------------------------------------------------------------------------
def chunk_words(vocab: list[dict]) -> list[list[dict]]:
    """Dars lug'atini 3-4 talik qismlarga bo'lish. Bo'laklar imkon qadar teng:
    11 so'z -> 4+4+3, 9 -> 3+3+3. Faqat juda kichik qoldiqda (masalan 5 -> 3+2)
    2 talik chunk chiqishi mumkin."""
    n = len(vocab)
    if n == 0:
        return []
    if n <= PART_MAX_WORDS:
        return [list(vocab)]
    k = -(-n // PART_MAX_WORDS)  # ceil
    base, rem = divmod(n, k)
    sizes = [base + 1] * rem + [base] * (k - rem)
    chunks, i = [], 0
    for s in sizes:
        chunks.append(list(vocab[i:i + s]))
        i += s
    return chunks


def assign_grammar(grammar_raw: list[dict], chunks: list[list[dict]],
                   known_prior_words: set[str]) -> list[list[int]]:
    """Grammatika qoidalarini so'z-qismlarga taqsimlash. Qoida ENG ERTA shu
    qismga tushadi: misollaridan biri o'sha paytgacha o'rganilgan so'zlar bilan
    segmentlanadigan bo'lsa (qoida darsligi misoli tushunarli bo'lishi uchun).
    Hech bir misol segmentlanmasa — qismlar bo'ylab tekis taqsim. Qoidalar
    qismlarga sig'sa — har qismga bittadan (yoyish), sig'masa 2 tagacha."""
    P = len(chunks)
    assign: list[list[int]] = [[] for _ in range(P)]
    if not grammar_raw or P == 0:
        return assign
    cap = 1 if len(grammar_raw) <= P else 2
    cum_known: list[set[str]] = []
    known = set(known_prior_words)
    for ch in chunks:
        known = known | {w["zh"] for w in ch if w.get("zh")}
        cum_known.append(set(known))
    for gi, g in enumerate(grammar_raw):
        pref = None
        for k in range(P):
            if any(segment_zh(ex.get("zh", ""), cum_known[k])
                   for ex in g.get("examples", [])):
                pref = k
                break
        if pref is None:
            pref = min(gi * P // max(1, len(grammar_raw)), P - 1)
        placed = False
        for k in list(range(pref, P)) + list(range(pref - 1, -1, -1)):
            if len(assign[k]) < cap:
                assign[k].append(gi)
                placed = True
                break
        if not placed:
            assign[P - 1].append(gi)
    return assign


def build_split_plan() -> dict:
    """Yagona haqiqat manbai: har daraja uchun HSK darsi -> qismlar xaritasi.
    Generatsiya, sync_maps, lesson_gate va parts_manifest hammasi shundan
    o'qiydi (raqamlash hech qayerda ikki xil hisoblanmaydi)."""
    plan: dict[str, dict] = {}
    for level, count in LEVELS:
        flat = 0
        lessons = []
        for src in range(1, count + 1):
            seed = load_seed_lesson(level, src)
            vocab = loadjson(seed.get("vocabulary_json"), [])
            chunks = chunk_words(vocab)
            parts = []
            for pi, chunk in enumerate(chunks):
                flat += 1
                parts.append({"flat": flat, "part_idx": pi, "chunk": chunk,
                              "checkpoint": False})
            flat += 1
            parts.append({"flat": flat, "part_idx": len(chunks), "chunk": [],
                          "checkpoint": True})
            lessons.append({"src": src, "seed": seed, "vocab": vocab,
                            "chunks": chunks, "parts": parts})
        plan[level] = {"lessons": lessons, "total": flat}
    return plan


def build_v3_part(level: str, flat_n: int, src: int, lesson: dict,
                  part: dict, grammar_assign: list[list[int]],
                  known_prior: list[dict]) -> dict:
    """Bitta mini-dars (qism) JSONi. So'z-qism: intro (3-4 so'z) + [grammatika]
    + mini-mashq. Checkpoint: takror + dialog. Sxema eski dars sxemasi bilan
    bir xil (schema_version 2 + qism maydonlari) — frontend Flow o'zgarishsiz
    o'ynaydi."""
    seed = lesson["seed"]
    vocab = lesson["vocab"]
    chunks = lesson["chunks"]
    grammar_raw = loadjson(seed.get("grammar_json"), [])
    dialogue_raw = loadjson(seed.get("dialogue_json"), [])
    goal = loadjson(seed.get("goal"), {})
    if not isinstance(goal, dict):
        goal = {}

    lvl = int(level.replace("hsk", "") or 0)
    pi = part["part_idx"]
    checkpoint = part["checkpoint"]
    part_count = len(lesson["parts"])
    # Per-part deterministic RNG: qayta ishga tushirishda bayt-bay bir xil.
    lr = random.Random(lvl * 100000 + src * 100 + pi + 1)
    archetype = ARCHETYPES[(lvl + flat_n) % len(ARCHETYPES)]

    if checkpoint:
        taught = list(vocab)
        sections = build_checkpoint_sections(vocab, known_prior, grammar_raw,
                                             dialogue_raw, flat_n, lr)
        active = build_active_words(vocab)
        grammar_shaped = build_grammar(grammar_raw)
    else:
        chunk = part["chunk"]
        # Shu paytgacha o'rgatilgan dars so'zlari (1..pi chunklari) — gating.
        taught = [w for ch in chunks[: pi + 1] for w in ch]
        active_all = build_active_words(chunk)
        part_grammar = [grammar_raw[i] for i in grammar_assign[pi]] if pi < len(grammar_assign) else []

        grammar_cards = build_grammar_section(part_grammar, taught, known_prior, flat_n, lr)
        # Grammatikasi katta qismda intro ixchamlashadi (byudjet 18 dan oshmasin).
        intro_cards = build_part_intro(chunk, active_all, taught, known_prior, flat_n, lr,
                                       lean=len(grammar_cards) >= 4)
        budget = PART_CARD_BUDGET - len(intro_cards) - len(grammar_cards)
        practice_cards = build_part_practice(chunk, taught, known_prior, grammar_raw,
                                             dialogue_raw, flat_n, lr, archetype, budget)

        # Qamrov kafolati: qismning HAR yangi so'zi kamida 4 kartada uchrashi
        # kerak (flash + tekshiruv + match + mashq). Yetmay qolgan so'zga
        # talaffuzdan oldin bitta aylanuvchi tekshiruv qo'shiladi.
        pool = taught + list(known_prior)

        def _hits(zh: str, cards_: list[dict]) -> int:
            return sum(1 for c in cards_ if zh and zh in json.dumps(c, ensure_ascii=False))

        all_cards = intro_cards + grammar_cards + practice_cards
        fill_cycle = [mc_translation, mc_hanzi, mc_meaning, make_word_listen_card]
        fills = 0
        for w in chunk:
            if _hits(w.get("zh", ""), all_cards) < 4:
                card = fill_cycle[(flat_n + fills) % len(fill_cycle)](w, pool)
                if card:
                    practice_cards.insert(max(0, len(practice_cards) - 1), card)
                    fills += 1

        # Byudjetdan oshgan bo'lsa — qamrovni BUZMAYDIGAN mashq kartalarini
        # (oxirgi talaffuzdan tashqari) olib tashlaymiz.
        total = len(intro_cards) + len(grammar_cards) + len(practice_cards)
        i = len(practice_cards) - 2
        while total > PART_CARD_BUDGET and i >= 0:
            cand = practice_cards[:i] + practice_cards[i + 1:]
            rest = intro_cards + grammar_cards + cand
            if all(_hits(w.get("zh", ""), rest) >= 4 for w in chunk):
                practice_cards = cand
                total -= 1
            i -= 1

        sections = [{
            "section_no": 1,
            "section_title": {"uz": "Yangi so'zlar", "ru": "Новые слова", "tj": "Калимаҳои нав"},
            "section_purpose": "intro",
            "cards": intro_cards,
        }]
        next_no = 2
        if grammar_cards:
            sections.append({
                "section_no": next_no,
                "section_title": {"uz": "Grammatika", "ru": "Грамматика", "tj": "Грамматика"},
                "section_purpose": "grammar",
                "cards": grammar_cards,
            })
            next_no += 1
        sections.append({
            "section_no": next_no,
            "section_title": {"uz": "Mashq", "ru": "Упражнение", "tj": "Машқ"},
            "section_purpose": "practice",
            "cards": practice_cards,
        })
        active = active_all
        grammar_shaped = build_grammar(part_grammar)

    subtitle = {
        "uz": goal.get("uz", ""),
        "ru": goal.get("ru", goal.get("uz", "")),
        "tj": goal.get("tj", goal.get("uz", "")),
    }
    zh_title, _ = parse_title(seed)
    return {
        "schema_version": 2,
        "level": level,
        "lesson_id": flat_n,
        # Qism metadatasi — frontend yorliqlar ("X-dars · Y-qism") va checkpoint
        # bayrami uchun ishlatadi.
        "source_lesson": src,
        "part_no": pi + 1,
        "part_count": part_count,
        "checkpoint": checkpoint,
        "title": zh_title,
        "subtitle": subtitle,
        # Markers: the intro/grammar sections are already interleaved (teach +
        # check) by the generator, so the client must NOT re-apply its old
        # transform.
        "intro_prebuilt": True,
        "grammar_prebuilt": True,
        "active_words": active,
        "grammar": grammar_shaped,
        # Dialoglar har qism JSONida to'liq turadi (frontend ma'lumotnoma uchun
        # ishlatishi mumkin); dialog KARTALARI faqat checkpoint qismida.
        "dialogues": build_dialogues(dialogue_raw),
        "sections": sections,
    }


def build_word_pinyin_index() -> dict:
    """word -> pinyin from every lesson's vocabulary (HSK-authoritative)."""
    idx: dict[str, str] = {}
    for level, count in LEVELS:
        for order in range(1, count + 1):
            seed = load_seed_lesson(level, order)
            for w in loadjson(seed.get("vocabulary_json"), []):
                zh, py = w.get("zh"), w.get("pinyin")
                if zh and py and zh not in idx:
                    idx[zh] = py
    return idx


def title_pinyin(zh: str, idx: dict) -> str:
    """Pinyin for a title: greedy longest-match against the HSK vocab index,
    falling back to pypinyin for anything not found."""
    try:
        from pypinyin import Style, pinyin as _pyp
    except Exception:  # pragma: no cover
        _pyp = None

    out: list[str] = []
    i, n = 0, len(zh)
    while i < n:
        ch = zh[i]
        if not ("一" <= ch <= "鿿"):
            i += 1  # skip punctuation / quotes etc.
            continue
        matched = None
        for j in range(min(n, i + 6), i, -1):  # try longest vocab word first
            seg = zh[i:j]
            if seg in idx:
                matched = (seg, idx[seg])
                break
        if matched:
            out.append(matched[1])
            i += len(matched[0])
        elif _pyp:
            out.append("".join(s[0] for s in _pyp(ch, style=Style.TONE)))
            i += 1
        else:
            i += 1
    return " ".join(p for p in out if p).strip()


def sync_maps(plan: dict | None = None, dry: bool = False):
    """<level>.json xaritasini split plandan TO'LIQ qayta qurish: bitta unit =
    bitta HSK darsligi darsi (sarlavha + qism tugunlari + checkpoint tuguni).
    Fayl darajasidagi maydonlar (schema_version, label, progress, ...)
    o'zgarishsiz qoladi."""
    plan = plan or build_split_plan()
    idx = build_word_pinyin_index()
    for level, count in LEVELS:
        path = BASE / f"{level}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        units = []
        for les in plan[level]["lessons"]:
            src = les["src"]
            zh_title, _ = parse_title(les["seed"])
            part_count = len(les["parts"])
            unit = {
                "no": src,
                "title": {
                    "uz": f"{src}-dars · {zh_title}",
                    "ru": f"Урок {src} · {zh_title}",
                    "tj": f"Дарси {src} · {zh_title}",
                },
                "lessons": [],
            }
            for part in les["parts"]:
                n = part["flat"]
                entry = {
                    "n": n,
                    "src": src,
                    "part": part["part_idx"] + 1,
                    "part_count": part_count,
                    "checkpoint": part["checkpoint"],
                    "status": "locked",
                    "content": f"lesson_{n:02d}",
                }
                if part["checkpoint"]:
                    entry["zh"] = zh_title
                    entry["py"] = title_pinyin(zh_title, idx)
                    entry["tr"] = {
                        "uz": "Mustahkamlash — dialog va takror",
                        "ru": "Закрепление — диалог и повторение",
                        "tj": "Мустаҳкамкунӣ — гуфтугӯ ва такрор",
                    }
                else:
                    chunk = part["chunk"]
                    entry["zh"] = " · ".join(w.get("zh", "") for w in chunk)
                    entry["py"] = " · ".join(w.get("pinyin", "") for w in chunk)
                    p = part["part_idx"] + 1
                    entry["tr"] = {
                        "uz": f"{p}-qism — yangi so'zlar",
                        "ru": f"Часть {p} — новые слова",
                        "tj": f"Қисми {p} — калимаҳои нав",
                    }
                unit["lessons"].append(entry)
            # Boss/chest kadansi eski holatda qoladi: har 5-darsdan keyin.
            if src % 5 == 0:
                unit["milestone"] = {
                    "title": {
                        "uz": f"{src - 4}–{src}-darslar takrori",
                        "ru": f"Повторение уроков {src - 4}–{src}",
                        "tj": f"Такрори дарсҳои {src - 4}–{src}",
                    },
                    "status": "locked",
                }
            units.append(unit)
        # Statik (autentifikatsiyasiz) holat: birinchi tugun current, 3-dan
        # keyingilar premium-qulf. Server /api/v3/map da jonli qiymat qo'yadi.
        if units and units[0]["lessons"]:
            units[0]["lessons"][0]["status"] = "current"
        for u in units:
            for e in u["lessons"]:
                if e["n"] > 3:
                    e["locked_premium"] = True
        data["units"] = units
        text = json.dumps(data, ensure_ascii=False, indent=2)
        if dry:
            print(f"[dry] {path}: would rebuild {len(units)} units / {plan[level]['total']} parts")
        else:
            path.write_text(text + "\n", encoding="utf-8")
            print(f"rebuilt map {path}: {len(units)} units / {plan[level]['total']} parts")


def write_parts_manifest(plan: dict | None = None, dry: bool = False):
    """parts_manifest.json — HSK dars -> qismlar xaritasi (flat raqamlar).
    Progress migratsiyasi va tekshiruv skriptlari uchun yagona manba."""
    plan = plan or build_split_plan()
    out: dict[str, dict] = {}
    for level, count in LEVELS:
        lessons = []
        for les in plan[level]["lessons"]:
            zh_title, _ = parse_title(les["seed"])
            lessons.append({
                "src": les["src"],
                "zh": zh_title,
                "words": len(les["vocab"]),
                "parts": [p["flat"] for p in les["parts"]],
                "checkpoint": les["parts"][-1]["flat"],
            })
        out[level] = {"total_parts": plan[level]["total"], "lessons": lessons}
    path = BASE / "parts_manifest.json"
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if dry:
        print(f"[dry] {path}: {sum(v['total_parts'] for v in out.values())} parts")
    else:
        path.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {path}: " + ", ".join(f"{lv}={v['total_parts']}" for lv, v in out.items()))


def write_lesson_gate(plan: dict | None = None, dry: bool = False):
    """so'z/belgi -> [HSK daraja, qism raqami] (birinchi O'RGATILGAN joyi —
    endi flat mini-dars raqami).

    Mashq sahifalari (ieroglif tanish / talaffuz / yodlash) kontentni userning
    O'RGANILGAN qismlari bilan cheklaydi: user 4-qismda bo'lsa, o'z darajasining
    7-qism so'zlari mashqqa chiqmaydi (quyi darajalar to'liq ochiq)."""
    plan = plan or build_split_plan()
    words: dict[str, list[int]] = {}
    chars: dict[str, list[int]] = {}
    for level, count in LEVELS:
        lvl = int(level.replace("hsk", "") or 1)
        for les in plan[level]["lessons"]:
            for part in les["parts"]:
                for w in part["chunk"]:
                    zh = str(w.get("zh") or "")
                    if not zh:
                        continue
                    if zh not in words:
                        words[zh] = [lvl, part["flat"]]
                    for ch in zh:
                        if "一" <= ch <= "鿿" and ch not in chars:
                            chars[ch] = [lvl, part["flat"]]
    text = (
        "/* GENERATED by scripts/gen_course_v3_from_seed.py — so'z/belgi -> [HSK daraja, qism]\n"
        "   (birinchi o'rgatilgan joyi; flat mini-dars raqami). Qo'lda tahrirlamang. */\n"
        "window.HSK_WORD_GATE=" + json.dumps(words, ensure_ascii=False, separators=(",", ":")) + ";\n"
        "window.HSK_CHAR_GATE=" + json.dumps(chars, ensure_ascii=False, separators=(",", ":")) + ";\n"
    )
    out = BASE / "lesson_gate.js"
    if dry:
        print(f"[dry] {out}: words={len(words)} chars={len(chars)}")
    else:
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out}: words={len(words)} chars={len(chars)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", help="only this level (hsk1..hsk4)")
    ap.add_argument("--lesson", type=int, help="only this SOURCE lesson (uning hamma qismlari)")
    ap.add_argument("--dry", action="store_true", help="print, do not write")
    ap.add_argument("--maps-only", action="store_true", help="only sync <level>.json maps")
    ap.add_argument("--no-maps", action="store_true", help="skip map sync")
    args = ap.parse_args()

    plan = build_split_plan()

    if args.maps_only:
        sync_maps(plan, dry=args.dry)
        write_lesson_gate(plan, dry=args.dry)
        write_parts_manifest(plan, dry=args.dry)
        return

    known_prior: list[dict] = []  # cumulative vocab across all earlier lessons
    written = 0
    for level, count in LEVELS:
        # To'liq (filtrsiz) regeneratsiyada darajaning eski lesson fayllari
        # o'chiriladi — raqamlash o'zgarganda quyruq fayllar qolib ketmasin.
        if not args.dry and not args.lesson and (not args.level or args.level == level):
            for old in sorted((BASE / level).glob("lesson_*.json")):
                old.unlink()
        for les in plan[level]["lessons"]:
            want = (not args.level or args.level == level) and (
                not args.lesson or args.lesson == les["src"]
            )
            if want:
                known_words = {w.get("zh", "") for w in known_prior if w.get("zh")}
                grammar_raw = loadjson(les["seed"].get("grammar_json"), [])
                gassign = assign_grammar(grammar_raw, les["chunks"], known_words)
                for part in les["parts"]:
                    lesson = build_v3_part(level, part["flat"], les["src"], les,
                                           part, gassign, known_prior)
                    out_path = BASE / level / f"lesson_{part['flat']:02d}.json"
                    text = json.dumps(lesson, ensure_ascii=False, indent=2)
                    if args.dry:
                        print(f"--- {out_path} ---")
                        print(text[:2000])
                    else:
                        out_path.write_text(text + "\n", encoding="utf-8")
                        written += 1
                        total_cards = sum(len(s["cards"]) for s in lesson["sections"])
                        kind = "checkpoint" if part["checkpoint"] else f"words={len(part['chunk'])}"
                        print(f"wrote {out_path}  (src={les['src']} "
                              f"part={lesson['part_no']}/{lesson['part_count']} "
                              f"{kind} cards={total_cards})")

            # Grow the cumulative known pool AFTER this lesson is processed so a
            # lesson never uses its own future siblings as distractors source
            # beyond its own vocab.
            known_prior = les["vocab"] + known_prior

    if not args.dry:
        print(f"\nTotal written: {written}")

    if not args.no_maps and not args.level and not args.lesson:
        sync_maps(plan, dry=args.dry)
        write_lesson_gate(plan, dry=args.dry)
        write_parts_manifest(plan, dry=args.dry)


if __name__ == "__main__":
    main()

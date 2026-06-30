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
            "tj": "Муколамаро пурра кунед",
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


def build_grammar_section(grammar_raw, vocab, known_prior) -> list[dict]:
    """Interactive grammar practice: build a real example sentence from tiles,
    plus one gap-fill of a current-lesson word inside a grammar example."""
    cards: list[dict] = []
    if not grammar_raw or not vocab:
        return cards
    pool = vocab + known_prior
    known_words = {x.get("zh", "") for x in pool if x.get("zh")}

    # sentence_builder from the first usable grammar example (rule applied).
    for g in grammar_raw:
        made = False
        for ex in g.get("examples", []):
            card = make_builder_card(ex.get("zh", ""), ex.get("pinyin", ""), t3(ex), known_words, pool)
            if card:
                cards.append(card)
                made = True
                break
        if made:
            break

    # one gap-fill: blank a current-lesson word inside a real grammar example.
    for w in vocab:
        if not (w.get("zh") and len(w["zh"]) >= 2):
            continue
        for g in grammar_raw:
            for ex in g.get("examples", []):
                zh = ex.get("zh", "")
                if w["zh"] in zh:
                    opts = [w["zh"]]
                    _distinct_pad(opts, [x["zh"] for x in pool], key=lambda s: s)
                    RNG.shuffle(opts)
                    cards.append({
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
                    })
                    return cards  # one gap-fill is enough
    return cards


def build_practice(vocab: list[dict], known_prior: list[dict], grammar: list[dict],
                   dialogue_raw: list[dict] | None = None, order: int = 1) -> list[dict]:
    """Build practice cards. Distractors come from `vocab` (current lesson) and,
    if needed, `known_prior` (earlier lessons). Never from future / higher words.

    Old multiple-choice drills are kept but REDUCED and mixed with the new
    interactive cards (sentence_builder, listening_choice) for variety."""
    cards: list[dict] = []
    if not vocab:
        return cards

    # Pool used to pad distractors: current lesson first, then earlier lessons.
    pool = vocab + known_prior
    known_words = {x.get("zh", "") for x in pool if x.get("zh")}
    dialogue_raw = dialogue_raw or []
    all_lines = [ln for b in dialogue_raw for ln in b.get("dialogue", []) if ln.get("zh")]

    def meaning_card(w):
        correct = word_meaning(w)
        opts = [correct]
        _distinct_pad(opts, [word_meaning(x) for x in pool], key=lambda m: m["uz"])
        order = opts[:]
        RNG.shuffle(order)
        ci = order.index(correct)
        return {
            "type": "meaning_guess",
            "prompt": {
                "uz": f"{w['zh']} so'zining ma'nosini tanlang:",
                "ru": f"Выберите значение слова {w['zh']}:",
                "tj": f"Маънои калимаи {w['zh']}-ро интихоб кунед:",
            },
            "title": {"uz": "Ma'nosi nima?", "ru": "Что означает?", "tj": "Маъно чист?"},
            "options": order,
            "correct_index": ci,
            "explanation": {
                "uz": f"{w['zh']} = {correct['uz']} ({w.get('pinyin','')})",
                "ru": f"{w['zh']} = {correct['ru']} ({w.get('pinyin','')})",
                "tj": f"{w['zh']} = {correct['tj']} ({w.get('pinyin','')})",
            },
        }

    def pinyin_card(w):
        opts = [w.get("pinyin", "")]
        _distinct_pad(opts, [x.get("pinyin", "") for x in pool], key=lambda s: s)
        order = opts[:]
        RNG.shuffle(order)
        ci = order.index(w.get("pinyin", ""))
        return {
            "type": "pinyin_choice",
            "prompt": {
                "uz": f"{w['zh']} talaffuzini tanlang:",
                "ru": f"Выберите произношение {w['zh']}:",
                "tj": f"Талаффузи {w['zh']}-ро интихоб кунед:",
            },
            "title": {"uz": "Qanday o'qiladi?", "ru": "Как читается?", "tj": "Чӣ хел хонда мешавад?"},
            "options": order,
            "correct_index": ci,
            "explanation": {
                "uz": f"{w['zh']} — {w.get('pinyin','')}",
                "ru": f"{w['zh']} — {w.get('pinyin','')}",
                "tj": f"{w['zh']} — {w.get('pinyin','')}",
            },
        }

    def translation_card(w):
        m = word_meaning(w)
        opts = [w["zh"]]
        _distinct_pad(opts, [x["zh"] for x in pool], key=lambda s: s)
        order = opts[:]
        RNG.shuffle(order)
        ci = order.index(w["zh"])
        return {
            "type": "translation_choice",
            "prompt": {
                "uz": f"'{m['uz']}' xitoycha qaysi?",
                "ru": f"'{m['ru']}' по-китайски?",
                "tj": f"'{m['tj']}' ба хитоӣ кадом аст?",
            },
            "title": {"uz": "Xitoycha qanday?", "ru": "Как по-китайски?", "tj": "Ба хитоӣ чӣ тавр?"},
            "options": order,
            "correct_index": ci,
            "explanation": {
                "uz": f"{m['uz']} = {w['zh']} ({w.get('pinyin','')})",
                "ru": f"{m['ru']} = {w['zh']} ({w.get('pinyin','')})",
                "tj": f"{m['tj']} = {w['zh']} ({w.get('pinyin','')})",
            },
        }

    def hanzi_card(w):
        opts = [w["zh"]]
        _distinct_pad(opts, [x["zh"] for x in pool], key=lambda s: s)
        order = opts[:]
        RNG.shuffle(order)
        ci = order.index(w["zh"])
        return {
            "type": "hanzi_choice",
            "prompt": {
                "uz": f"{w.get('pinyin','')} qaysi ieroglif?",
                "ru": f"Какой иероглиф читается {w.get('pinyin','')}?",
                "tj": f"{w.get('pinyin','')} кадом иероглиф аст?",
            },
            "title": {"uz": "Ieroglifni tanlang", "ru": "Выберите иероглиф", "tj": "Иероглифро интихоб кунед"},
            "options": order,
            "correct_index": ci,
            "explanation": {
                "uz": f"{w['zh']} = {word_meaning(w)['uz']} ({w.get('pinyin','')})",
                "ru": f"{w['zh']} = {word_meaning(w)['ru']} ({w.get('pinyin','')})",
                "tj": f"{w['zh']} = {word_meaning(w)['tj']} ({w.get('pinyin','')})",
            },
        }

    def match_card(words):
        pairs = [[w["zh"], word_meaning(w)] for w in words]
        return {
            "type": "match_pairs",
            "pairs": pairs,
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

    # Assemble a varied, gated practice set. Old MC drills are REDUCED to two
    # per lesson and the starting type rotates by lesson order so consecutive
    # lessons don't feel identical. They are mixed with the new interactive
    # cards (sentence_builder, listening_choice), match, and pronunciation.
    v = vocab
    mc_builders = [meaning_card, pinyin_card, translation_card, hanzi_card]
    start = (order - 1) % len(mc_builders)
    for k in range(2):  # only 2 multiple-choice drills now (was 4)
        b = mc_builders[(start + k) % len(mc_builders)]
        w = v[(start + k) % len(v)]
        cards.append(b(w))

    # Interactive: rebuild a real dialogue line from word tiles (gated).
    for ln in all_lines:
        bc = make_builder_card(ln.get("zh", ""), ln.get("pinyin", ""), t3(ln), known_words, pool)
        if bc:
            cards.append(bc)
            break

    # Interactive: "tap what you heard" from the dialogue lines.
    if all_lines:
        lc = make_listen_card(all_lines[0], all_lines)
        if lc:
            cards.append(lc)

    cards.append(match_card(v[: min(4, len(v))]))
    cards.append(pron_card(v[0]))
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
            "title": {"uz": "Dialogdan savol:", "ru": "Вопрос по диалогу:", "tj": "Савол аз муколама:"},
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
                "tj": f"Дар муколама {first['speaker']} аввал чӣ мегӯяд?",
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
                    "tj": f"Дар охири муколама {last['speaker']} чӣ мегӯяд?",
                },
            )
        )
    return cards


def build_dialog_section(blocks: list[dict], pool: list[dict]) -> list[dict]:
    """Fully interactive dialogue section (no passive text dump): hear a line
    and pick what was said, fill a missing character, complete the dialogue,
    then a comprehension question. Everything stays level-gated."""
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

    # 2) Fill the missing character in a real dialogue line.
    known_chars = {ch for w in pool for ch in w.get("zh", "") if "一" <= ch <= "鿿"}
    for ln in line_objs:
        cg = make_char_gap_card(ln, known_chars)
        if cg:
            cards.append(cg)
            break

    # 3) Complete the dialogue (pick the missing reply).
    cloze = make_cloze_card(blocks[0], line_pool)
    if cloze:
        cards.append(cloze)

    # 4) Comprehension question(s).
    cards.extend(build_dialog_quizzes(blocks))
    return cards


# --------------------------------------------------------------------------
# Top-level lesson builder
# --------------------------------------------------------------------------
def build_v3_lesson(level: str, order: int, seed: dict, known_prior: list[dict]) -> dict:
    vocab = loadjson(seed.get("vocabulary_json"), [])
    grammar_raw = loadjson(seed.get("grammar_json"), [])
    dialogue_raw = loadjson(seed.get("dialogue_json"), [])
    goal = loadjson(seed.get("goal"), {})
    if not isinstance(goal, dict):
        goal = {}

    active_words = build_active_words(vocab)
    grammar = build_grammar(grammar_raw)
    dialogues = build_dialogues(dialogue_raw)

    intro_cards = [{"type": "active_word", "word": w} for w in active_words]
    grammar_cards = build_grammar_section(grammar_raw, vocab, known_prior)
    practice_cards = build_practice(vocab, known_prior, grammar_raw, dialogue_raw, order)
    dialog_cards = build_dialog_section(dialogue_raw, vocab + known_prior)

    sections = [
        {
            "section_no": 1,
            "section_title": {"uz": "Yangi so'zlar", "ru": "Новые слова", "tj": "Калимаҳои нав"},
            "section_purpose": "intro",
            "cards": intro_cards,
        },
    ]
    # Grammar becomes its own interactive section (only when grammar exists).
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
    next_no += 1
    sections.append({
        "section_no": next_no,
        "section_title": {"uz": "Dialog", "ru": "Диалог", "tj": "Муколама"},
        "section_purpose": "dialog",
        "cards": dialog_cards,
    })

    subtitle = {
        "uz": goal.get("uz", ""),
        "ru": goal.get("ru", goal.get("uz", "")),
        "tj": goal.get("tj", goal.get("uz", "")),
    }

    zh_title, _ = parse_title(seed)
    return {
        "schema_version": 2,
        "level": level,
        "lesson_id": order,
        "title": zh_title,
        "subtitle": subtitle,
        "active_words": active_words,
        "grammar": grammar,
        "dialogues": dialogues,
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


def sync_maps(dry: bool = False):
    """Rewrite each <level>.json lesson entry (zh/py/tr) to match the real
    seeded lesson, keeping n/status/locked_premium/content untouched."""
    idx = build_word_pinyin_index()
    for level, count in LEVELS:
        path = BASE / f"{level}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        seeds = {o: load_seed_lesson(level, o) for o in range(1, count + 1)}
        changed = 0
        for unit in data.get("units", []):
            # Neutral unit headers: the old themed titles no longer match the
            # real lessons grouped under them. No invented topic / translation.
            uno = unit.get("no", 0)
            unit["title"] = {
                "uz": f"{uno}-bo'lim",
                "ru": f"Раздел {uno}",
                "tj": f"Боби {uno}",
            }
            for entry in unit.get("lessons", []):
                seed = seeds.get(entry.get("n"))
                if not seed:
                    continue
                zh, title_tr = parse_title(seed)
                goal = loadjson(seed.get("goal"), {})
                if not isinstance(goal, dict):
                    goal = {}
                tr = title_tr or {
                    "uz": goal.get("uz", ""),
                    "ru": goal.get("ru", goal.get("uz", "")),
                    "tj": goal.get("tj", goal.get("uz", "")),
                }
                entry["zh"] = zh
                entry["py"] = title_pinyin(zh, idx)
                entry["tr"] = tr
                changed += 1
        text = json.dumps(data, ensure_ascii=False, indent=2)
        if dry:
            print(f"[dry] {path}: would update {changed} lessons")
        else:
            path.write_text(text + "\n", encoding="utf-8")
            print(f"updated map {path}: {changed} lessons")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", help="only this level (hsk1..hsk4)")
    ap.add_argument("--lesson", type=int, help="only this lesson order")
    ap.add_argument("--dry", action="store_true", help="print, do not write")
    ap.add_argument("--maps-only", action="store_true", help="only sync <level>.json maps")
    ap.add_argument("--no-maps", action="store_true", help="skip map sync")
    args = ap.parse_args()

    if args.maps_only:
        sync_maps(dry=args.dry)
        return

    known_prior: list[dict] = []  # cumulative vocab across all earlier lessons
    written = 0
    for level, count in LEVELS:
        for order in range(1, count + 1):
            seed = load_seed_lesson(level, order)
            vocab = loadjson(seed.get("vocabulary_json"), [])

            want = (not args.level or args.level == level) and (
                not args.lesson or args.lesson == order
            )
            if want:
                lesson = build_v3_lesson(level, order, seed, known_prior)
                out_path = BASE / level / f"lesson_{order:02d}.json"
                text = json.dumps(lesson, ensure_ascii=False, indent=2)
                if args.dry:
                    print(f"--- {out_path} ---")
                    print(text[:2000])
                else:
                    out_path.write_text(text + "\n", encoding="utf-8")
                    written += 1
                    sec_counts = {s["section_purpose"]: len(s["cards"]) for s in lesson["sections"]}
                    print(f"wrote {out_path}  (vocab={len(vocab)}, "
                          f"grammar_cards={sec_counts.get('grammar', 0)}, "
                          f"practice={sec_counts.get('practice', 0)}, "
                          f"dialog={sec_counts.get('dialog', 0)})")

            # Grow the cumulative known pool AFTER this lesson is processed so a
            # lesson never uses its own future siblings as distractors source
            # beyond its own vocab.
            known_prior = vocab + known_prior

    if not args.dry:
        print(f"\nTotal written: {written}")

    if not args.no_maps and not args.level and not args.lesson:
        sync_maps(dry=args.dry)


if __name__ == "__main__":
    main()

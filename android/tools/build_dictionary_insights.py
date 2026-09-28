#!/usr/bin/env python3
"""Bundle the dictionary entry's examples and character breakdowns.

A dictionary entry shows two things beyond the word itself, and both ship
inside the APK so the entry is complete with no connection:

  assets/hsk-examples.json   real sentences that use the word
  assets/hanzi-parts.json    what each character is built from, and a line
                             that makes it easier to remember

**Examples** come from the course first: every dialogue line and grammar
example already has pinyin and a translation in all three languages, and a
learner may meet the same sentence in a lesson. Words the course never uses
in a sentence take theirs from `dictionary_insights/examples*.json`.

**Breakdowns** are written by hand, in `dictionary_insights/parts/*.json`,
one character per line:

    "好": {"parts": [["女", "nǚ", "ayol", "женщина", "зан"], ...],
           "hint": ["uz", "ru", "tj"]}

A pictograph has no parts, only the hint describing the picture.

Run it after changing either source or the course data:

    python3 android/tools/build_dictionary_insights.py

`check_dictionary_assets.py` fails the build when the assets are stale.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
STATIC = ROOT / "app" / "static"
COURSE = STATIC / "course_v3_data"
ASSETS = ROOT / "android" / "app" / "src" / "main" / "assets"
SOURCES = Path(__file__).resolve().parent / "dictionary_insights"
EXAMPLES_ASSET = ASSETS / "hsk-examples.json"
PARTS_ASSET = ASSETS / "hanzi-parts.json"

LANGUAGES = ("uz", "ru", "tj")
MAX_EXAMPLES = 3
MAX_PARTS = 3
# Long enough to show the word in use, short enough to read at a glance.
MIN_HANZI, MAX_HANZI = 3, 22
SENTENCE_END = tuple("。？！?!…")
HANZI = re.compile(r"[一-鿿]")


def js_literal(path: Path, name: str) -> object:
    text = path.read_text(encoding="utf-8")
    marker = f"const {name}="
    value, _ = json.JSONDecoder().raw_decode(text, text.index(marker) + len(marker))
    return value


def word_level(label: str) -> int:
    match = re.search(r"HSK\s*(\d)", label or "")
    return int(match.group(1)) if match else 9


def dictionary_words() -> list[dict]:
    return js_literal(ASSETS / "hsk-words.js", "WORDS")


def translations(value: object) -> list[str] | None:
    if not isinstance(value, dict):
        return None
    texts = [str(value.get(lang) or "").strip() for lang in LANGUAGES]
    return texts if all(texts) else None


def course_sentences() -> dict[str, tuple[str, list[str], int]]:
    """Every usable sentence in the course: zh -> (pinyin, translations, level)."""
    found: dict[str, tuple[str, list[str], int]] = {}

    def add(zh: object, pinyin: object, translated: object, level: int) -> None:
        if not isinstance(zh, str) or not isinstance(pinyin, str):
            return
        zh, pinyin = zh.strip(), pinyin.strip()
        texts = translations(translated)
        count = len(HANZI.findall(zh))
        if not pinyin or texts is None or not MIN_HANZI <= count <= MAX_HANZI:
            return
        if not zh.endswith(SENTENCE_END):
            return
        # The same sentence appears in several lessons; the easiest one wins.
        if zh not in found or found[zh][2] > level:
            found[zh] = (pinyin, texts, level)

    for path in sorted(COURSE.glob("hsk*/*.json")):
        level = int(path.parent.name.removeprefix("hsk"))
        data = json.loads(path.read_text(encoding="utf-8"))
        for dialogue in data.get("dialogues") or []:
            for line in dialogue.get("dialogue") or []:
                add(line.get("zh"), line.get("pinyin"), line.get("text"), level)
        for grammar in data.get("grammar") or []:
            for example in grammar.get("examples") or []:
                add(example.get("zh"), example.get("pinyin"), example.get("translation"), level)
        for section in data.get("sections") or []:
            for card in section.get("cards") or []:
                for example in (card.get("g") or {}).get("examples") or []:
                    add(example.get("zh"), example.get("pinyin"), example.get("translation"), level)
    return found


def authored_examples() -> dict[str, list[list[str]]]:
    """Hand-written sentences, from every `dictionary_insights/examples*.json`."""
    merged: dict[str, list[list[str]]] = {}
    for path in sorted(SOURCES.glob("examples*.json")):
        for word, rows in json.loads(path.read_text(encoding="utf-8")).items():
            merged.setdefault(word, []).extend(list(row) for row in rows)
    return merged


def example_problems(words: list[dict]) -> list[str]:
    """A hand-written sentence the builder would silently drop is a mistake."""
    known = {str(w.get("h") or "").strip() for w in words}
    problems: list[str] = []
    for word, rows in authored_examples().items():
        if word not in known:
            problems.append(f"examples: {word} is not in the dictionary")
        for row in rows:
            if len(row) != 2 + len(LANGUAGES) or not all(str(v).strip() for v in row):
                problems.append(f"examples: {word}: {row!r} needs [zh, pinyin, uz, ru, tj]")
                continue
            if not uses_word(row[0], word):
                problems.append(f"examples: {word}: {row[0]} does not use the word")
            if CYRILLIC.search(row[2]):
                problems.append(f"examples: {word}: Uzbek text has Cyrillic letters: {row[2]!r}")
            for text in row[1:]:
                if typo := mixed_script(text):
                    problems.append(f"examples: {word}: {typo!r} mixes Latin and Cyrillic letters")
    return problems


BRACKETS = re.compile(r"[(（]([^)）]*)[)）]")


def uses_word(sentence: str, word: str) -> bool:
    """Whether a sentence uses a dictionary entry as the entry is written.

    Most entries are plain words. A few carry an optional part — 春(天),
    极（了）— or are frames — 不但……而且……. The optional part is read in
    first; left out only when what remains is still a word of its own, so
    极（了）does not match the 极 inside 积极.
    """
    for part in (p for p in word.split("…") if p):
        whole = BRACKETS.sub(r"\1", part)
        short = BRACKETS.sub("", part)
        if whole in sentence or (len(short) >= 2 and short in sentence):
            continue
        return False
    return True


def build_examples(words: list[dict]) -> dict:
    sentences = course_sentences()
    authored = authored_examples()
    table: list[list[str]] = []
    index: dict[str, int] = {}
    by_word: dict[str, list[int]] = {}

    def slot(row: list[str]) -> int:
        if row[0] not in index:
            index[row[0]] = len(table)
            table.append(row)
        return index[row[0]]

    for word in words:
        hanzi = str(word.get("h") or "").strip()
        if not hanzi or hanzi in by_word:
            continue
        level = word_level(str(word.get("lv") or ""))
        candidates = sorted(
            (zh for zh in sentences if uses_word(zh, hanzi)),
            # A sentence from the word's own level or below reads easiest;
            # among those, the shortest shows the word most plainly.
            key=lambda zh: (max(0, sentences[zh][2] - level), len(HANZI.findall(zh)), zh),
        )
        chosen: list[int] = []
        for zh in candidates:
            if len(chosen) == MAX_EXAMPLES:
                break
            # "我很好。" and "我很好！" are the same example twice.
            if any(zh[:-1] in table[i][0] or table[i][0][:-1] in zh for i in chosen):
                continue
            pinyin, texts, _ = sentences[zh]
            chosen.append(slot([zh, pinyin, *texts]))
        for row in authored.get(hanzi, []):
            if len(chosen) == MAX_EXAMPLES:
                break
            if len(row) == 2 + len(LANGUAGES) and all(row) and uses_word(row[0], hanzi):
                chosen.append(slot([str(v).strip() for v in row]))
        if chosen:
            by_word[hanzi] = chosen

    return {"v": 1, "languages": list(LANGUAGES), "sentences": table, "words": by_word}


def authored_parts() -> tuple[dict[str, dict], list[str]]:
    merged: dict[str, dict] = {}
    problems: list[str] = []
    for path in sorted((SOURCES / "parts").glob("*.json")):
        pairs = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=lambda items: items,
        )
        for char, entry in pairs:
            where = f"{path.name}: {char}"
            if char in merged:
                problems.append(f"{where} is defined twice")
                continue
            entry = dict(entry)
            parts = entry.get("parts") or []
            hint = entry.get("hint") or []
            if len(char) != 1 or not HANZI.match(char):
                problems.append(f"{where} is not one character")
            if len(hint) != len(LANGUAGES) or not all(str(h).strip() for h in hint):
                problems.append(f"{where} needs a hint in {'/'.join(LANGUAGES)}")
            if len(parts) > MAX_PARTS:
                problems.append(f"{where} has {len(parts)} parts; at most {MAX_PARTS} fit a row")
            for part in parts:
                if len(part) != 2 + len(LANGUAGES) or not all(str(v).strip() for v in part):
                    problems.append(f"{where} part {part!r} needs [char, pinyin, uz, ru, tj]")
            for text in [str(h) for h in hint] + [str(part[0]) for part in parts if part]:
                if rare := RARE_HANZI.findall(text):
                    problems.append(f"{where}: {''.join(rare)} may not render on a phone")
            texts = [str(h) for h in hint] + [str(v) for part in parts for v in part[2:]]
            for text in texts:
                if typo := mixed_script(text):
                    problems.append(f"{where}: {typo!r} mixes Latin and Cyrillic letters")
            for text in [str(hint[0]) if hint else ""] + [str(part[2]) for part in parts if len(part) > 2]:
                if CYRILLIC.search(text):
                    problems.append(f"{where}: Uzbek text has Cyrillic letters: {text!r}")
            merged[char] = {
                "parts": [[str(v).strip() for v in part] for part in parts],
                "hint": [str(h).strip() for h in hint],
            }
    return merged, problems


# CJK Extension A and beyond: many phone fonts draw these as empty boxes.
RARE_HANZI = re.compile(r"[㐀-䶿\U00020000-\U0003FFFF]")
CYRILLIC = re.compile(r"[Ѐ-ӿ]")
LATIN = re.compile(r"[A-Za-z]")
WORD = re.compile(r"[^\W\d_]+")


def mixed_script(text: str) -> str | None:
    """A word typed half in one alphabet: the typo a reader cannot see."""
    for word in WORD.findall(text):
        if CYRILLIC.search(word) and LATIN.search(word):
            return word
    return None


def build_parts(words: list[dict]) -> tuple[dict, list[str]]:
    parts, problems = authored_parts()
    needed = {ch for word in words for ch in str(word.get("h") or "") if HANZI.match(ch)}
    for char in sorted(set(parts) - needed):
        problems.append(f"{char} is not in the dictionary")
    return {"v": 1, "languages": list(LANGUAGES), "chars": dict(sorted(parts.items()))}, problems


def serialise(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"


def build() -> tuple[str, str, list[str]]:
    words = dictionary_words()
    examples = build_examples(words)
    parts, problems = build_parts(words)
    return serialise(examples), serialise(parts), problems + example_problems(words)


def main() -> int:
    examples, parts, problems = build()
    if problems:
        for problem in problems:
            print(problem if problem.startswith("examples:") else f"parts: {problem}")
        return 1
    EXAMPLES_ASSET.write_text(examples, encoding="utf-8")
    PARTS_ASSET.write_text(parts, encoding="utf-8")
    ex, pa = json.loads(examples), json.loads(parts)
    print(
        f"hsk-examples.json: {len(ex['words'])} words, {len(ex['sentences'])} sentences, "
        f"{len(examples.encode()) // 1024} KB"
    )
    print(f"hanzi-parts.json: {len(pa['chars'])} characters, {len(parts.encode()) // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())

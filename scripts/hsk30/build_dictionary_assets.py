#!/usr/bin/env python3
"""Build offline HSK 3.0 dictionary examples from translated course content.

The HSK 3.0 word list is generated separately. This builder pairs words that
are new to HSK 3.0 with short, translated course sentences and a small authored
fallback list for words that do not occur in the course material.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
WORDS_JS = STATIC / "course_v3_data" / "hsk30-words.js"
LEGACY_WORDS_JS = STATIC / "hsk-words.js"
LEGACY_EXAMPLES_JS = STATIC / "hsk-extra.js"
COURSE_DIR = STATIC / "course_v3_data"
MANUAL_EXAMPLES = Path(__file__).with_name("dictionary_examples_manual.json")
OUTPUT = COURSE_DIR / "hsk30-dictionary-examples.js"
LANGUAGES = ("uz", "ru", "tj")
HANZI = re.compile(r"[\u3400-\u9fff]")
BRACKETS = re.compile(r"[(（]([^)）]*)[)）]")
SENTENCE_END = tuple("。？！?!…")
MIN_HANZI = 3
MAX_HANZI = 22


def js_json(path: Path, marker: str) -> object:
    source = path.read_text(encoding="utf-8")
    start = source.index(marker) + len(marker)
    value, _ = json.JSONDecoder().raw_decode(source, start)
    return value


def dictionary_words() -> tuple[list[dict], set[str]]:
    current = js_json(WORDS_JS, "window.HSK30_WORDS=")
    hsk30_words = {
        str(row.get("h") or "").strip()
        for row in current
        if str(row.get("h") or "").strip()
    }
    return current, hsk30_words


def uses_word(sentence: str, word: str) -> bool:
    """Match plain words plus the dictionary's optional parenthetical forms."""
    for part in (part for part in word.split("…") if part):
        whole = BRACKETS.sub(r"\1", part)
        short = BRACKETS.sub("", part)
        if whole in sentence or (len(short) >= 2 and short in sentence):
            continue
        return False
    return True


def valid_example(word: str, example: dict) -> bool:
    zh = str(example.get("zh") or "").strip()
    pinyin = str(example.get("p") or "").strip()
    meanings = example.get("m")
    count = len(HANZI.findall(zh))
    return (
        bool(pinyin)
        and MIN_HANZI <= count <= MAX_HANZI
        and zh.endswith(SENTENCE_END)
        and uses_word(zh, word)
        and isinstance(meanings, dict)
        and all(str(meanings.get(language) or "").strip() for language in LANGUAGES)
    )


def _collect_sentence(out: list[tuple[str, str, dict]], row: object, translation_key: str) -> None:
    if not isinstance(row, dict):
        return
    zh = str(row.get("zh") or "").strip()
    pinyin = str(row.get("pinyin") or "").strip()
    meanings = row.get(translation_key)
    if (
        not zh
        or not pinyin
        or not isinstance(meanings, dict)
        or not all(str(meanings.get(language) or "").strip() for language in LANGUAGES)
    ):
        return
    out.append((zh, pinyin, {language: str(meanings[language]).strip() for language in LANGUAGES}))


def course_sentences() -> list[tuple[str, str, dict]]:
    found: list[tuple[str, str, dict]] = []
    paths = set(COURSE_DIR.glob("hsk*/*.json")) | set(COURSE_DIR.glob("nhsk*/*.json"))
    for path in sorted(paths):
        data = json.loads(path.read_text(encoding="utf-8"))
        for dialogue in data.get("dialogues") or []:
            for line in dialogue.get("dialogue") or []:
                _collect_sentence(found, line, "text")
        for grammar in data.get("grammar") or []:
            for example in grammar.get("examples") or []:
                _collect_sentence(found, example, "translation")
        for section in data.get("sections") or []:
            for card in section.get("cards") or []:
                grammar = card.get("g") or {}
                for example in grammar.get("examples") or []:
                    _collect_sentence(found, example, "translation")
    return found


def build_examples() -> dict[str, dict]:
    _, hsk30_words = dictionary_words()
    legacy_examples = js_json(LEGACY_EXAMPLES_JS, "const EXAMPLES=")
    manual_rows = json.loads(MANUAL_EXAMPLES.read_text(encoding="utf-8"))
    manual = {str(row["word"]): row for row in manual_rows}
    unexpected = sorted(set(manual) - hsk30_words)
    if unexpected:
        raise ValueError(f"manual examples contain words outside the HSK 3.0 list: {unexpected}")
    missing_legacy = {
        word
        for word in hsk30_words
        if not (isinstance(legacy_examples.get(word), dict) and legacy_examples[word].get("zh"))
    }
    preferred_manual = {
        word for word, row in manual.items() if row.get("prefer") is True
    }
    targets = missing_legacy | preferred_manual

    candidates: dict[str, list[tuple[int, int, str, str, dict]]] = {}
    for zh, pinyin, meanings in course_sentences():
        hanzi_count = len(HANZI.findall(zh))
        if not MIN_HANZI <= hanzi_count <= MAX_HANZI or not zh.endswith(SENTENCE_END):
            continue
        for word in targets:
            if uses_word(zh, word):
                candidates.setdefault(word, []).append(
                    (hanzi_count, len(zh), zh, pinyin, meanings)
                )

    result: dict[str, dict] = {}
    course_count = 0
    for word in sorted(targets):
        choices = candidates.get(word) or []
        authored = manual.get(word)
        if authored is not None and authored.get("prefer") is True:
            example = {
                "zh": str(authored.get("zh") or "").strip(),
                "p": str(authored.get("p") or "").strip(),
                "m": {
                    language: str((authored.get("m") or {}).get(language) or "").strip()
                    for language in LANGUAGES
                },
                "source": "authored",
            }
        elif choices:
            _, _, zh, pinyin, meanings = min(
                choices, key=lambda row: (row[0], row[1], row[2], row[3])
            )
            example = {"zh": zh, "p": pinyin, "m": meanings, "source": "course"}
            course_count += 1
        else:
            if authored is None:
                continue
            example = {
                "zh": str(authored.get("zh") or "").strip(),
                "p": str(authored.get("p") or "").strip(),
                "m": {
                    language: str((authored.get("m") or {}).get(language) or "").strip()
                    for language in LANGUAGES
                },
                "source": "authored",
            }
        if not valid_example(word, example):
            raise ValueError(f"invalid dictionary example for {word}: {example}")
        result[word] = example

    missing = sorted(targets - set(result))
    if missing:
        raise ValueError(f"add short translated examples for HSK 3.0 dictionary words: {missing}")
    return result


def render_asset(examples: dict[str, dict]) -> str:
    payload = json.dumps(examples, ensure_ascii=False, separators=(",", ":"))
    return (
        "/* GENERATED by scripts/hsk30/build_dictionary_assets.py. */\n"
        f"window.HSK30_DICTIONARY_EXAMPLES={payload};\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when the generated asset is stale")
    args = parser.parse_args()
    try:
        examples = build_examples()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(error, file=sys.stderr)
        return 1

    rendered = render_asset(examples)
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print(f"{OUTPUT.relative_to(ROOT)} is missing or stale; run this script without --check")
            return 1
    else:
        OUTPUT.write_text(rendered, encoding="utf-8")

    _, hsk30_words = dictionary_words()
    legacy_examples = js_json(LEGACY_EXAMPLES_JS, "const EXAMPLES=")
    covered_words = {
        word
        for word in hsk30_words
        if (isinstance(legacy_examples.get(word), dict) and legacy_examples[word].get("zh"))
        or word in examples
    }
    authored_count = sum(row["source"] == "authored" for row in examples.values())
    print(
        f"HSK 3.0 dictionary examples ready: {len(covered_words)}/{len(hsk30_words)} "
        f"words covered; {len(examples)} examples ({len(examples) - authored_count} course, "
        f"{authored_count} authored)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

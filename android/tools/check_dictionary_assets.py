#!/usr/bin/env python3
"""The dictionary bundled in the APK must match the one the Mini App ships.

Android carries its own copy of the word list and the stroke data so the
dictionary opens with no connection. Two copies of the same thing drift: the
Mini App's list gets a word, nobody re-runs the generator, and the phone shows
a dictionary one release behind — silently, because a missing word looks
exactly like a word that was never there.

So the copy is compared with its source here rather than trusted.

Usage:  python3 tools/check_dictionary_assets.py
Exit code 1 when the bundle no longer matches `app/static/`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
STATIC = ROOT / "app" / "static"
ASSETS = ROOT / "android" / "app" / "src" / "main" / "assets"
REBUILD = "python3 android/tools/build_dictionary_assets.py"


def _js_literal(path: Path, name: str) -> object:
    text = path.read_text(encoding="utf-8")
    marker = f"const {name}="
    value, _ = json.JSONDecoder().raw_decode(text, text.index(marker) + len(marker))
    return value


def main() -> int:
    words_asset = ASSETS / "dictionary.json"
    strokes_dir = ASSETS / "strokes"
    if not words_asset.is_file() or not strokes_dir.is_dir():
        print(f"the bundled dictionary is missing — run: {REBUILD}")
        return 1

    source_words = _js_literal(STATIC / "hsk-words.js", "WORDS")
    bundled_words = json.loads(words_asset.read_text(encoding="utf-8"))
    problems: list[str] = []

    if len(source_words) != len(bundled_words):
        problems.append(
            f"word count {len(bundled_words)} != {len(source_words)} in hsk-words.js"
        )
    elif source_words != bundled_words:
        differing = next(
            (
                a.get("h")
                for a, b in zip(source_words, bundled_words)
                if a != b
            ),
            "?",
        )
        problems.append(f"word entries differ, first at {differing}")

    source_strokes = _js_literal(STATIC / "hsk-extra.js", "STROKES")
    bundled = {path.stem for path in strokes_dir.glob("*.json")}
    expected = {
        str(ord(char))
        for char, data in source_strokes.items()
        if len(char) == 1 and isinstance(data, dict) and data.get("strokes")
    }
    if missing := sorted(expected - bundled):
        problems.append(f"{len(missing)} stroke file(s) missing, e.g. {missing[:5]}")
    if extra := sorted(bundled - expected):
        problems.append(f"{len(extra)} stroke file(s) no longer in the source, e.g. {extra[:5]}")

    # The point of the bundle: a character the dictionary can open must be
    # drawable without a connection.
    needed = {
        ch
        for word in bundled_words
        for ch in str(word.get("h", ""))
        if "一" <= ch <= "鿿"
    }
    if undrawable := sorted(ch for ch in needed if str(ord(ch)) not in bundled):
        problems.append(
            f"{len(undrawable)} dictionary character(s) have no stroke file: "
            f"{''.join(undrawable[:10])}"
        )

    if problems:
        for problem in problems:
            print(f"bundled dictionary: {problem}")
        print(f"rebuild it with: {REBUILD}")
        return 1

    print(
        f"the bundled dictionary matches the Mini App "
        f"({len(bundled_words)} words, {len(bundled)} characters)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

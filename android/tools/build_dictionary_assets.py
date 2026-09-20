#!/usr/bin/env python3
"""Bundle the dictionary into the APK so it works with no connection at all.

The Android dictionary used to download its word list on first open and fetch
every character's stroke data one request at a time, with no cache. A learner
who installed the app on mobile data and then opened it on a train saw an
empty dictionary; one who had used it before still saw no writing order,
because strokes were never stored.

Both sets already live in this repository — the Mini App's dictionary page
ships them (`hsk-words.js`, `hsk-extra.js`). This copies them into Android
assets rather than inventing a second source that could drift from the first.

Layout written under `android/app/src/main/assets/`:

  dictionary.json          the word list, all three languages
  strokes/<codepoint>.json one file per character, named as the server names
                           its own cache, so both sides agree

Run it whenever the Mini App's dictionary data changes:

    python3 android/tools/build_dictionary_assets.py
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
STATIC = ROOT / "app" / "static"
ASSETS = ROOT / "android" / "app" / "src" / "main" / "assets"


def _js_literal(path: Path, name: str) -> object:
    """Read `const <name>= <json>;` out of one of the Mini App's data files."""
    text = path.read_text(encoding="utf-8")
    marker = f"const {name}="
    start = text.index(marker) + len(marker)
    decoder = json.JSONDecoder()
    value, _ = decoder.raw_decode(text, start)
    return value


def main() -> int:
    words = _js_literal(STATIC / "hsk-words.js", "WORDS")
    strokes = _js_literal(STATIC / "hsk-extra.js", "STROKES")

    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "dictionary.json").write_text(
        json.dumps(words, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    stroke_dir = ASSETS / "strokes"
    if stroke_dir.exists():
        shutil.rmtree(stroke_dir)
    stroke_dir.mkdir(parents=True)

    written = 0
    for char, data in strokes.items():
        if len(char) != 1 or not isinstance(data, dict):
            continue
        if not data.get("strokes"):
            continue
        payload = {
            "strokes": data["strokes"],
            # Without these the character can only appear whole; they are what
            # the writing animation follows.
            "medians": data.get("medians", []),
        }
        (stroke_dir / f"{ord(char)}.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        written += 1

    # Every character the word list uses must have a stroke file, or the
    # dictionary would open a character it cannot draw offline.
    needed = {
        ch
        for word in words
        for ch in str(word.get("h", ""))
        if "一" <= ch <= "鿿"
    }
    missing = sorted(ch for ch in needed if not (stroke_dir / f"{ord(ch)}.json").is_file())

    print(f"dictionary.json: {len(words)} words")
    print(f"strokes/: {written} characters")
    if missing:
        print(f"WARNING: {len(missing)} characters have no stroke data: {''.join(missing[:20])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

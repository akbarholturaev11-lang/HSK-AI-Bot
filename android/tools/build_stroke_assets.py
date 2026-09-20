#!/usr/bin/env python3
"""Bundle the writing order into the APK so the dictionary draws offline.

The word list already travels with the app (`assets/hsk-words.js`, read by
`AssetBundledDictionarySource`). The strokes did not: every character was
fetched one request at a time with no cache, so a learner with no connection
saw the words and an empty writing box.

The data already lives in this repository — the Mini App's dictionary page
ships it in `hsk-extra.js`. This copies it into Android assets rather than
inventing a second source that could drift from the first.

  assets/strokes/<codepoint>.json   one file per character, named as the
                                    server names its own cache

Run it whenever the Mini App's stroke data changes:

    python3 android/tools/build_stroke_assets.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
STATIC = ROOT / "app" / "static"
STROKES_DIR = ROOT / "android" / "app" / "src" / "main" / "assets" / "strokes"


def js_literal(path: Path, name: str) -> object:
    """Read `const <name>= <json>;` out of one of the Mini App's data files."""
    text = path.read_text(encoding="utf-8")
    marker = f"const {name}="
    value, _ = json.JSONDecoder().raw_decode(text, text.index(marker) + len(marker))
    return value


def main() -> int:
    strokes = js_literal(STATIC / "hsk-extra.js", "STROKES")
    words = js_literal(STATIC / "hsk-words.js", "WORDS")

    if STROKES_DIR.exists():
        shutil.rmtree(STROKES_DIR)
    STROKES_DIR.mkdir(parents=True)

    written = 0
    for char, data in strokes.items():
        if len(char) != 1 or not isinstance(data, dict) or not data.get("strokes"):
            continue
        (STROKES_DIR / f"{ord(char)}.json").write_text(
            json.dumps(
                {
                    "strokes": data["strokes"],
                    # Without these the character can only appear whole; they
                    # are the line the writing animation follows.
                    "medians": data.get("medians", []),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        written += 1

    needed = {
        ch
        for word in words
        for ch in str(word.get("h", ""))
        if "一" <= ch <= "鿿"
    }
    missing = sorted(ch for ch in needed if not (STROKES_DIR / f"{ord(ch)}.json").is_file())

    print(f"strokes/: {written} characters")
    if missing:
        print(f"WARNING: {len(missing)} dictionary characters have none: {''.join(missing[:20])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

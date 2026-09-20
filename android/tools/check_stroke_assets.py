#!/usr/bin/env python3
"""The stroke data bundled in the APK must match the Mini App's.

Android carries its own copy so the dictionary draws with no connection. Two
copies of the same thing drift: the Mini App's data changes, nobody re-runs
the generator, and the phone shows a character it cannot write — silently,
because a missing stroke file looks exactly like a character that never had
one.

It also checks the thing the bundle exists for: every character the bundled
word list can open must be drawable without a connection.

Usage:  python3 tools/check_stroke_assets.py
Exit code 1 when the bundle no longer matches `app/static/`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
STATIC = ROOT / "app" / "static"
ANDROID_ASSETS = ROOT / "android" / "app" / "src" / "main" / "assets"
STROKES_DIR = ANDROID_ASSETS / "strokes"
REBUILD = "python3 android/tools/build_stroke_assets.py"


def js_literal(path: Path, name: str) -> object:
    text = path.read_text(encoding="utf-8")
    marker = f"const {name}="
    value, _ = json.JSONDecoder().raw_decode(text, text.index(marker) + len(marker))
    return value


def main() -> int:
    if not STROKES_DIR.is_dir():
        print(f"the bundled stroke data is missing — run: {REBUILD}")
        return 1

    source = js_literal(STATIC / "hsk-extra.js", "STROKES")
    bundled = {path.stem for path in STROKES_DIR.glob("*.json")}
    expected = {
        str(ord(char))
        for char, data in source.items()
        if len(char) == 1 and isinstance(data, dict) and data.get("strokes")
    }

    problems: list[str] = []
    if missing := sorted(expected - bundled):
        problems.append(f"{len(missing)} file(s) missing, e.g. {missing[:5]}")
    if extra := sorted(bundled - expected):
        problems.append(f"{len(extra)} file(s) no longer in the source, e.g. {extra[:5]}")

    # The point of the bundle: a character the dictionary can open must be
    # drawable without a connection. The word list Android ships is the same
    # file the Mini App reads, so it is the one checked against.
    words = js_literal(ANDROID_ASSETS / "hsk-words.js", "WORDS")
    needed = {
        ch
        for word in words
        for ch in str(word.get("h", ""))
        if "一" <= ch <= "鿿"
    }
    if undrawable := sorted(ch for ch in needed if str(ord(ch)) not in bundled):
        problems.append(
            f"{len(undrawable)} bundled dictionary character(s) have no stroke file: "
            f"{''.join(undrawable[:10])}"
        )

    if problems:
        for problem in problems:
            print(f"bundled strokes: {problem}")
        print(f"rebuild them with: {REBUILD}")
        return 1

    print(f"the bundled stroke data matches the Mini App ({len(bundled)} characters)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

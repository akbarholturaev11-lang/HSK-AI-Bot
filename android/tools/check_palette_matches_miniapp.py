#!/usr/bin/env python3
"""The Android palette must be the Mini App's palette, value for value.

The two clients are one product. When a token drifts by a shade the apps stop
looking like the same thing, and nobody notices from a screenshot — the
difference is one or two units per channel. So the comparison is done here,
against the Mini App's own stylesheet, rather than by eye.

Usage:  python3 tools/check_palette_matches_miniapp.py
Exit code 1 when a mapped colour no longer matches its Mini App token.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
MINI_APP = ROOT / "app" / "static" / "course-v3.html"
COLORS = ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "pomp" / "hskai" / "core" / "design" / "Color.kt"

# Android name -> Mini App CSS custom property it must equal.
# Anything not listed here is Android-only and is not checked (a disabled
# control colour, for instance, has no Mini App counterpart).
MAPPING = {
    "Paper": "paper",
    "PaperRaised": "card",
    "Ink": "ink",
    "InkSecondary": "ink2",
    "InkDisabled": "ink3",
    "Cinnabar": "cin",
    "CinnabarDark": "cin2",
    "CinnabarSoft": "cinbg",
    "Jade": "jade",
    "JadeSoft": "jadebg",
    "Gold": "gold",
    "GoldSoft": "goldbg",
    "Flame": "flame",
    "FlameSoft": "flamebg",
    "Blue": "blue",
    "BlueSoft": "bluebg",
    "Overlay": "overlay",
    "Shadow": "shadow",
    "Divider": "line",
}

TOKEN = re.compile(r"--([a-z0-9-]+)\s*:\s*#([0-9A-Fa-f]{6})\b")
KOTLIN = re.compile(r"\bval\s+([A-Za-z][A-Za-z0-9_]*)\s*=\s*Color\(0x(?:FF)?([0-9A-Fa-f]{6})\)")


def main() -> int:
    if not MINI_APP.is_file():
        print(f"cannot read the Mini App stylesheet at {MINI_APP}")
        return 1
    if not COLORS.is_file():
        print(f"cannot read the Android palette at {COLORS}")
        return 1

    tokens = {name: value.upper() for name, value in TOKEN.findall(MINI_APP.read_text(encoding="utf-8"))}
    android = {name: value.upper() for name, value in KOTLIN.findall(COLORS.read_text(encoding="utf-8"))}

    problems = 0
    for kotlin_name, token in sorted(MAPPING.items()):
        expected = tokens.get(token)
        actual = android.get(kotlin_name)
        if expected is None:
            print(f"--{token} is no longer defined in the Mini App; the mapping is stale")
            problems += 1
        elif actual is None:
            print(f"{kotlin_name} is missing from the Android palette (--{token} is #{expected})")
            problems += 1
        elif actual != expected:
            print(f"{kotlin_name} is #{actual} but --{token} is #{expected}")
            problems += 1

    if problems:
        print(f"\n{problems} colour(s) no longer match the Mini App")
        return 1
    print(f"the palette matches the Mini App ({len(MAPPING)} colours checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

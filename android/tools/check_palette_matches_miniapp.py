#!/usr/bin/env python3
"""The Android light palette must be the Mini App's palette, value for value.

The two clients are one product. When a token drifts by a shade the apps stop
looking like the same thing, and nobody notices from a screenshot — the
difference is one or two units per channel. So the comparison is done here,
against the Mini App's own stylesheet, rather than by eye.

Dark mode is intentionally Android-only and is not compared with the Mini App.
Usage:  python3 tools/check_palette_matches_miniapp.py
Exit code 1 when a mapped colour no longer matches its Mini App token.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
MINI_APP = ROOT / "app" / "static" / "course-v3.html"
MINI_APP_TOKENS = ROOT / "app" / "static" / "course_v3_data" / "design-tokens.css"
COLORS = ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "pomp" / "hskai" / "core" / "design" / "Color.kt"

# Android light name -> Mini App CSS custom property it must equal.
# Anything not listed here is Android-only and is not checked (a disabled
# control colour, for instance, has no Mini App counterpart).
MAPPING = {
    "LightPaper": "hsk-paper",
    "LightPaperRaised": "hsk-paper-raised",
    "LightInk": "hsk-ink",
    "LightInkSecondary": "hsk-ink-secondary",
    "LightInkDisabled": "hsk-ink-disabled",
    "LightCinnabar": "hsk-cinnabar",
    "LightCinnabarDark": "hsk-cinnabar-ink",
    "LightCinnabarSoft": "hsk-cinnabar-soft",
    "LightJade": "hsk-jade",
    "LightJadeSoft": "hsk-jade-soft",
    "LightGold": "hsk-gold",
    "LightGoldSoft": "hsk-gold-soft",
    "LightFlame": "hsk-flame",
    "LightFlameSoft": "hsk-flame-soft",
    "LightBlue": "hsk-blue",
    "LightBlueSoft": "hsk-blue-soft",
    "LightOverlay": "overlay",
    "LightShadow": "shadow",
    "LightDivider": "hsk-divider",
}

TOKEN = re.compile(r"--([a-z0-9-]+)\s*:\s*#([0-9A-Fa-f]{6})\b")
KOTLIN = re.compile(r"\bval\s+([A-Za-z][A-Za-z0-9_]*)\s*=\s*Color\(0x(?:FF)?([0-9A-Fa-f]{6})\)")


def main() -> int:
    if not MINI_APP.is_file() or not MINI_APP_TOKENS.is_file():
        missing = [str(path) for path in (MINI_APP, MINI_APP_TOKENS) if not path.is_file()]
        print(f"cannot read the Mini App stylesheet/token file: {', '.join(missing)}")
        return 1
    if not COLORS.is_file():
        print(f"cannot read the Android palette at {COLORS}")
        return 1

    # The design token file declares the light palette first and the dark
    # palette later. Keep the first definition for each token; the screen's
    # own stylesheet supplies screen-local tokens such as overlay and shadow.
    tokens: dict[str, str] = {}
    for source in (MINI_APP_TOKENS, MINI_APP):
        for name, value in TOKEN.findall(source.read_text(encoding="utf-8")):
            tokens.setdefault(name, value.upper())
    android = {name: value.upper() for name, value in KOTLIN.findall(COLORS.read_text(encoding="utf-8"))}

    problems = 0
    for kotlin_name, token in sorted(MAPPING.items()):
        expected = tokens.get(token)
        actual = android.get(kotlin_name)
        if expected is None:
            print(f"--{token} is no longer defined in the Mini App; the mapping is stale")
            problems += 1
        elif actual is None:
            print(f"{kotlin_name} is missing from the Android light palette (--{token} is #{expected})")
            problems += 1
        elif actual != expected:
            print(f"{kotlin_name} is #{actual} but --{token} is #{expected}")
            problems += 1

    if problems:
        print(f"\n{problems} colour(s) no longer match the Mini App")
        return 1
    print(f"the Android light palette matches the Mini App ({len(MAPPING)} colours checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Every visible string must exist in all three languages.

The project supports Uzbek (the default locale), Russian and Tajik, and a
string added to only one of them ships a screen that falls back to Uzbek for
Russian and Tajik learners. Android Lint catches this too, but only once a
full Gradle run reaches the lint task — this is the same answer in a second,
and it covers every source set including the distribution flavours.

Usage:  python3 tools/check_strings_translated.py
Exit code 1 when a string is missing a translation, or a translation has a
string the default locale does not.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "app" / "src"
STRING_ELEMENT = re.compile(r'<string\s+([^>]*?)>', re.S)
STRING_NAME = re.compile(r'name="([^"]+)"')
# A brand name or a language shown in its own language is the same in every
# locale; Android marks those `translatable="false"` and so do we.
NOT_TRANSLATABLE = re.compile(r'translatable\s*=\s*"false"')
# Uzbek is the default locale, so it lives in the unqualified values/.
TRANSLATIONS = ("values-ru", "values-tg")


def names_in(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    names = set()
    for attributes in STRING_ELEMENT.findall(path.read_text(encoding="utf-8")):
        if NOT_TRANSLATABLE.search(attributes):
            continue
        found = STRING_NAME.search(attributes)
        if found:
            names.add(found.group(1))
    return names


def main() -> int:
    defaults = sorted(SRC.glob("*/res/values/strings.xml"))
    if not defaults:
        print("no string resources found; nothing to check")
        return 0

    problems = 0
    checked = 0
    for default in defaults:
        source_set = default.relative_to(SRC).parts[0]
        base = names_in(default)
        checked += len(base)
        for locale in TRANSLATIONS:
            path = default.parent.parent / locale / "strings.xml"
            translated = names_in(path)
            for name in sorted(base - translated):
                print(f"{source_set}/{locale}: missing translation for `{name}`")
                problems += 1
            # A translated string with no default is an Android Lint error and
            # means the default locale silently lost a line.
            for name in sorted(translated - base):
                print(f"{source_set}/{locale}: `{name}` has no default (Uzbek) string")
                problems += 1

    if problems:
        print(f"\n{problems} string(s) are not available in all three languages")
        return 1
    print(f"all strings exist in uz, ru and tg ({checked} string(s) across {len(defaults)} source set(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())

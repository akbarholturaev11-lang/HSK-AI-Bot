#!/usr/bin/env python3
"""Catch test fakes that fell behind an interface they implement.

Adding a method to a Retrofit API interface compiles the main sources fine and
then breaks `compileDebugUnitTestKotlin`, because every hand-written fake in
the test sources must implement the new member. On a machine without the
Android SDK the Kotlin compiler cannot be run, so this stands in for it.

It is deliberately narrow: it only looks at interfaces whose members are all
`suspend fun` declarations (the Retrofit APIs), and only at classes that name
such an interface as a supertype. Anything it cannot parse confidently is
skipped rather than guessed at.

Usage:  python3 tools/check_interface_fakes.py
Exit code 1 when a fake is missing a member.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "app" / "src"
MAIN = ROOT / "main"
TEST = ROOT / "test"


def _balanced_block(text: str, open_at: int) -> str:
    """Returns the {...} block starting at open_at, braces balanced."""
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_at : i + 1]
    return ""


def interface_members(sources: list[Path]) -> dict[str, set[str]]:
    """Maps interface name -> the suspend fun names it declares."""
    found: dict[str, set[str]] = {}
    for path in sources:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\binterface\s+([A-Z][A-Za-z0-9_]*)\s*\{", text):
            body = _balanced_block(text, match.end() - 1)
            if not body:
                continue
            members = set(re.findall(r"\bsuspend\s+fun\s+([A-Za-z_][A-Za-z0-9_]*)", body))
            # Only the Retrofit-style, all-suspend interfaces are checked.
            if members and not re.search(r"\bval\s|\bvar\s", body):
                found[match.group(1)] = members
    return found


def main() -> int:
    main_files = sorted(MAIN.rglob("*.kt"))
    test_files = sorted(TEST.rglob("*.kt"))
    interfaces = interface_members(main_files)
    if not interfaces:
        print("no all-suspend interfaces found; nothing to check")
        return 0

    problems = 0
    for path in test_files:
        text = path.read_text(encoding="utf-8")
        for name, required in interfaces.items():
            # `class Foo : Bar {` and `object : Bar {` both count. A subclass of
            # another fake inherits the members, so only direct implementors of
            # the interface itself are checked.
            for match in re.finditer(
                r"(?:class\s+[A-Za-z0-9_]*\s*(?:\([^)]*\)\s*)?|object\s*)"
                r":\s*" + re.escape(name) + r"\s*\{",
                text,
            ):
                body = _balanced_block(text, match.end() - 1)
                if not body:
                    continue
                implemented = set(
                    re.findall(r"\boverride\s+suspend\s+fun\s+([A-Za-z_][A-Za-z0-9_]*)", body)
                )
                missing = sorted(required - implemented)
                if missing:
                    line = text[: match.start()].count("\n") + 1
                    rel = path.relative_to(ROOT.parent.parent)
                    print(f"{rel}:{line}: fake of {name} is missing: {', '.join(missing)}")
                    problems += 1

    if problems:
        print(f"\n{problems} fake(s) behind their interface — unit tests will not compile")
        return 1
    print(f"interface fakes are complete ({len(interfaces)} interface(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

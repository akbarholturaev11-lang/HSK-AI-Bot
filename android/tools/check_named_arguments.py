#!/usr/bin/env python3
"""Catch call sites that pass a named argument the function does not declare.

Compose code is almost entirely named arguments, so renaming or removing a
parameter breaks every call site — and `No parameter with name 'x' found` is
exactly the error that has cost CI rounds here. On a machine without the
Android SDK the Kotlin compiler cannot be run, so this stands in for it.

It is deliberately conservative: a call is only checked when its callee name
is declared in this project's own sources. Calls into Compose, Retrofit or the
standard library are skipped, because their parameter lists are not visible
here and guessing would produce noise.

Usage:  python3 tools/check_named_arguments.py
Exit code 1 when a call passes a name no declaration has.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "app" / "src"

# `fun name(`, `class Name(`, `object Name` — the declarations we can see.
DECL = re.compile(
    r"\b(?:fun|class|data\s+class|value\s+class)\s+"
    r"(?:<[^>]*>\s*)?"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*\(",
)
CALL = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
# A named argument: `name = ` but not `name ==`, and not inside a string.
NAMED_ARG = re.compile(r"(?:^|[(,])\s*([a-z_][A-Za-z0-9_]*)\s*=(?!=)")
# A parameter: optional modifiers, then `name:`.
PARAM = re.compile(
    r"(?:^|[(,])\s*"
    r"(?:@[A-Za-z_][\w.]*\s*(?:\"\"\s*)?)*"
    r"(?:(?:private|internal|public|override|vararg|crossinline|noinline)\s+)*"
    r"(?:v(?:al|ar)\s+)?([a-z_][A-Za-z0-9_]*)\s*:"
)

KEYWORDS = {"if", "while", "for", "when", "catch", "return", "fun", "class"}


def strip_comments(text: str) -> str:
    """Blanks out comments, keeping every byte offset and line intact.

    A KDoc block reads exactly like code to a regex — it is full of colons,
    parentheses and the word `fun` — so leaving comments in produced a page of
    false reports. Offsets are preserved so reported line numbers stay true.
    """
    out = list(text)
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            if text.startswith('"""', i):
                end = text.find('"""', i + 3)
                i = n if end == -1 else end + 3
            else:
                i += 1
                while i < n and text[i] != '"':
                    i += 2 if text[i] == "\\" else 1
                i += 1
            continue
        if text.startswith("//", i):
            while i < n and text[i] != "\n":
                out[i] = " "
                i += 1
            continue
        if text.startswith("/*", i):
            depth = 0
            while i < n:
                if text.startswith("/*", i):
                    depth += 1
                    out[i] = out[i + 1] = " "
                    i += 2
                    continue
                if text.startswith("*/", i):
                    depth -= 1
                    out[i] = out[i + 1] = " "
                    i += 2
                    if depth == 0:
                        break
                    continue
                if text[i] != "\n":
                    out[i] = " "
                i += 1
            continue
        i += 1
    return "".join(out)


def balanced_parens(text: str, open_at: int) -> str:
    """The (...) starting at open_at, parens balanced, strings skipped."""
    depth = 0
    i = open_at
    while i < len(text):
        ch = text[i]
        if ch == '"':
            # Skip the whole string literal, escapes and all.
            if text.startswith('"""', i):
                end = text.find('"""', i + 3)
                i = len(text) if end == -1 else end + 3
                continue
            i += 1
            while i < len(text) and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
            i += 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[open_at : i + 1]
        i += 1
    return ""


def top_level_pieces(block: str) -> str:
    """The argument list with every nested (...) , [...] and {...} removed.

    Nested calls carry their own named arguments; only this call's own names
    belong to this check.
    """
    out = []
    depth = 0
    i = 0
    while i < len(block):
        ch = block[i]
        if ch == '"':
            if block.startswith('"""', i):
                end = block.find('"""', i + 3)
                i = len(block) if end == -1 else end + 3
            else:
                i += 1
                while i < len(block) and block[i] != '"':
                    i += 2 if block[i] == "\\" else 1
                i += 1
            out.append('""')
            continue
        if ch in "([{":
            depth += 1
            if depth == 1:
                out.append("(")
            i += 1
            continue
        if ch in ")]}":
            depth -= 1
            if depth == 0:
                out.append(")")
            i += 1
            continue
        if depth <= 1:
            out.append(ch)
        i += 1
    return "".join(out)


def is_test_source(path: Path) -> bool:
    """True for any test source set: `test`, `testPlay`, `androidTest`, ..."""
    source_set = path.relative_to(ROOT).parts[0]
    return source_set.startswith(("test", "androidTest"))


def declarations(files: list[Path]) -> dict[str, set[str]]:
    """Maps each declared callable name to every parameter name it accepts."""
    found: dict[str, set[str]] = {}
    for path in files:
        text = strip_comments(path.read_text(encoding="utf-8"))
        for match in DECL.finditer(text):
            name = match.group(1)
            if name in KEYWORDS:
                continue
            block = balanced_parens(text, match.end() - 1)
            if not block:
                continue
            params = set(PARAM.findall(top_level_pieces(block)))
            found.setdefault(name, set()).update(params)
    return found


def main() -> int:
    files = sorted(ROOT.rglob("*.kt"))
    if not files:
        print("no Kotlin sources found; nothing to check")
        return 0
    # Test helpers are scoped to the tests. One of them is named `viewModel`,
    # which is also Compose's own function: without this split every
    # `viewModel(factory = ...)` in the app would be checked against the test
    # helper's parameters and reported. Tests may call app code, not the
    # other way round.
    main_files = [f for f in files if not is_test_source(f)]
    test_files = [f for f in files if is_test_source(f)]
    app_declared = declarations(main_files)
    test_declared = declarations(test_files)
    for name, params in app_declared.items():
        test_declared.setdefault(name, set()).update(params)

    problems = 0
    for path in files:
        declared = test_declared if is_test_source(path) else app_declared
        text = strip_comments(path.read_text(encoding="utf-8"))
        for match in CALL.finditer(text):
            name = match.group(1)
            if name in KEYWORDS or name not in declared:
                continue
            # Skip the declaration itself.
            head = text.rfind("\n", 0, match.start())
            line_start = text[head + 1 : match.start()]
            if re.search(r"\b(?:fun|class)\s+(?:<[^>]*>\s*)?$", line_start):
                continue
            block = balanced_parens(text, match.end() - 1)
            if not block:
                continue
            passed = set(NAMED_ARG.findall(top_level_pieces(block)))
            unknown = sorted(passed - declared[name])
            if unknown:
                line = text[: match.start()].count("\n") + 1
                rel = path.relative_to(ROOT.parent.parent)
                print(f"{rel}:{line}: {name}(...) has no parameter: {', '.join(unknown)}")
                problems += 1

    if problems:
        print(f"\n{problems} call site(s) pass a name their function does not declare")
        return 1
    print(f"named arguments match their declarations ({len(test_declared)} callables)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

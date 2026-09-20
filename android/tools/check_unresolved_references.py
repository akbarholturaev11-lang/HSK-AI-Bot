#!/usr/bin/env python3
"""Catch calls to a name the file never imported.

`Unresolved reference` is the compile error the other static checks could not
see, and it has cost CI rounds here: a composable moved between files and kept
its old call site, or a `Modifier.background(...)` was written without
`import androidx.compose.foundation.background`. On a machine without the
Android SDK the Kotlin compiler cannot be run, so this stands in for it.

Two rules, both narrow enough to be trusted:

* Every link in a `Modifier` chain is a top-level extension function, so it
  must be imported where it is used — the one exception being the handful of
  members a layout scope supplies, which are listed below.
* A capitalised call with nothing in front of it — a composable or a
  constructor — must be declared in the file's own package or imported into
  the file. Kotlin has no implicit import beyond the standard library, so
  anything else names something that is not there.

Everything else — a member call, a bare lowercase call, a fully qualified
one — is out of a regex's reach and is skipped rather than guessed at.

Usage:  python3 tools/check_unresolved_references.py
Exit code 1 when a call names something the file cannot see.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "app" / "src"

IMPORT = re.compile(r"^import\s+([\w.]+\*?)(?:\s+as\s+(\w+))?", re.MULTILINE)
PACKAGE = re.compile(r"^package\s+([\w.]+)", re.MULTILINE)
# A top-level declaration is visible to its whole package without an import.
# The optional dotted group is an extension receiver: `fun Modifier.glass()`.
DECL = re.compile(
    r"\b(?:fun|class|object|interface|typealias|val|var)\s+"
    r"(?:<[^>]*>\s*)?"
    r"(?:[\w.]+\.)?"
    r"([A-Za-z_][A-Za-z0-9_]*)",
)
# Only a declaration at the left margin is visible to the rest of the package.
# A `val background =` inside a composable is a local, and counting it as a
# package member hid a genuinely missing
# `import androidx.compose.foundation.background` in another file. Within its
# own file every declaration counts, nested or not, so a private helper stays
# callable where it was written.
TOP_LEVEL = re.compile(
    r"(?:(?:private|internal|public|abstract|open|sealed|data|value|enum"
    r"|annotation|inline|external|lateinit|const|expect|actual|suspend)\s+)*$"
)
CALL = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")

# Capitalised callables that need no import at all.
IMPLICIT = {
    "Any", "Array", "Boolean", "BooleanArray", "Byte", "ByteArray", "Char",
    "CharArray", "CharSequence", "Comparator", "Double", "DoubleArray",
    "Error", "Exception", "Float", "FloatArray", "IllegalArgumentException",
    "IllegalStateException", "Int", "IntArray", "Iterable", "Lazy", "List",
    "Long", "LongArray", "Map", "MutableList", "MutableMap", "MutableSet",
    "NotImplementedError", "Number", "NumberFormatException", "Pair",
    "Regex", "RuntimeException",
    "Set", "Short", "ShortArray", "String", "StringBuilder", "Thread",
    "Throwable", "Triple", "Unit", "UnsupportedOperationException",
}

# Members a layout or animation scope puts on Modifier without an import.
SCOPE_MEMBERS = {
    "align", "alignBy", "alignByBaseline", "animateEnterExit", "animateItem",
    "animateItemPlacement", "matchParentSize", "then", "weight",
}


def strip_comments_and_strings(text: str) -> str:
    """Blanks out comments and string bodies, keeping every byte and line.

    A KDoc block and a string literal both read like code to a regex — they
    are full of parentheses and capitalised words — so leaving them in
    produced a page of false reports. Offsets are preserved so reported line
    numbers stay true.
    """
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        two = text[i : i + 2]
        if two == "//":
            while i < n and text[i] != "\n":
                out[i] = " "
                i += 1
        elif two == "/*":
            while i < n and text[i : i + 2] != "*/":
                if text[i] != "\n":
                    out[i] = " "
                i += 1
            for j in range(i, min(i + 2, n)):
                out[j] = " "
            i += 2
        elif text[i : i + 3] == '"""':
            for j in range(i, min(i + 3, n)):
                out[j] = " "
            i += 3
            while i < n and text[i : i + 3] != '"""':
                if text[i] != "\n":
                    out[i] = " "
                i += 1
            for j in range(i, min(i + 3, n)):
                out[j] = " "
            i += 3
        elif text[i] == '"':
            out[i] = " "
            i += 1
            while i < n and text[i] != '"':
                if text[i] == "\\":
                    out[i] = " "
                    i += 1
                if i < n and text[i] != "\n":
                    out[i] = " "
                i += 1
            if i < n:
                out[i] = " "
            i += 1
        else:
            i += 1
    return "".join(out)


def _skip_back(body: str, i: int) -> int:
    while i >= 0 and body[i] in " \t\n\r":
        i -= 1
    return i


def chain_root(body: str, dot: int) -> str | None:
    """The token a dotted call hangs off: `Modifier` in `Modifier.a().b()`.

    Walks backwards over balanced groups and identifiers, so a chain broken
    across lines and carrying trailing lambdas still resolves to its root.
    Returns None when the chain starts with something that is not a plain
    name, such as a literal or a closing brace it cannot pair.
    """
    i = dot - 1
    for _ in range(64):  # a chain longer than this is not worth resolving
        i = _skip_back(body, i)
        if i < 0:
            return None
        while i >= 0 and body[i] in ")]}":
            close = body[i]
            opening = {")": "(", "]": "[", "}": "{"}[close]
            depth = 0
            while i >= 0:
                if body[i] == close:
                    depth += 1
                elif body[i] == opening:
                    depth -= 1
                    if depth == 0:
                        break
                i -= 1
            if i < 0:
                return None
            i = _skip_back(body, i - 1)
        end = i + 1
        while i >= 0 and (body[i].isalnum() or body[i] == "_"):
            i -= 1
        token = body[i + 1 : end]
        if not token:
            return None
        previous = _skip_back(body, i)
        if previous >= 0 and body[previous] == "." and not (previous > 0 and body[previous - 1] == "."):
            i = previous - 1
            continue
        return token
    return None


def main() -> int:
    files = sorted(ROOT.rglob("*.kt"))
    bodies = {p: strip_comments_and_strings(p.read_text(encoding="utf-8")) for p in files}

    imports: dict[Path, dict[str, str]] = {}
    package_of: dict[Path, str] = {}
    declared: dict[str, set[str]] = {}
    in_file: dict[Path, set[str]] = {}
    canonical: dict[str, set[str]] = {}

    for path, body in bodies.items():
        names: dict[str, str] = {}
        for match in IMPORT.finditer(body):
            full, alias = match.group(1), match.group(2)
            if full.endswith("*"):
                names["*"] = "*"
                continue
            simple = alias or full.rsplit(".", 1)[-1]
            names[simple] = full
            canonical.setdefault(simple, set()).add(full)
        imports[path] = names
        package = PACKAGE.search(body)
        package_of[path] = package.group(1) if package else ""
        here = in_file.setdefault(path, set())
        for match in DECL.finditer(body):
            here.add(match.group(1))
            margin = body.rfind("\n", 0, match.start()) + 1
            if TOP_LEVEL.fullmatch(body[margin : match.start()]):
                declared.setdefault(package_of[path], set()).add(match.group(1))

    problems = 0
    for path, body in bodies.items():
        visible = imports[path]
        if "*" in visible:
            continue
        own = declared.get(package_of[path], set()) | in_file[path]
        rel = path.relative_to(ROOT.parent.parent)
        for match in CALL.finditer(body):
            name = match.group(1)
            if name in visible or name in own or name in IMPLICIT:
                continue
            before = _skip_back(body, match.start() - 1)
            if before >= 0 and body[before] == "@":
                continue  # an annotation, not a call
            dotted = before >= 0 and body[before] == "."
            if dotted:
                if name in SCOPE_MEMBERS or chain_root(body, before) != "Modifier":
                    continue
            elif not name[0].isupper() or name.isupper():
                # Bare lowercase is a local function or the standard library;
                # ALL CAPS is an enum entry declaring itself. Out of reach.
                continue
            line = body[: match.start()].count("\n") + 1
            want = canonical.get(name)
            hint = f" (expected {next(iter(want))})" if want and len(want) == 1 else ""
            print(f"{rel}:{line}: '{name}' is called but not imported{hint}")
            problems += 1

    if problems:
        print(f"\n{problems} unresolved reference(s) — the Kotlin compiler will reject this")
        return 1
    print(f"every called name resolves ({len(files)} file(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

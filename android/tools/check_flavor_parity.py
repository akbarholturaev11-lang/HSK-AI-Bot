#!/usr/bin/env python3
"""The two distribution flavours must stay interchangeable, and stay apart.

`src/play` and `src/direct` each provide their own version of the same few
declarations (the limit gate and the limit block), and the app's shared
sources call them without knowing which build they are in. If one flavour
gains a parameter the other does not, the app still compiles for one flavour
and fails for the other — and the one that breaks is usually the one nobody
built locally.

Usage:  python3 tools/check_flavor_parity.py
Exit code 1 when the flavours have drifted apart.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_named_arguments import DECL, PARAM, balanced_parens, strip_comments, top_level_pieces

SRC = Path(__file__).resolve().parent.parent / "app" / "src"
FLAVOURS = ("play", "direct")
STRING_NAME = re.compile(r'<string\s+name="([^"]+)"')


def flavour_declarations(flavour: str) -> dict[str, set[str]]:
    """Maps each declaration in a flavour's sources to its parameter names."""
    root = SRC / flavour
    found: dict[str, set[str]] = {}
    for path in sorted(root.rglob("*.kt")):
        text = strip_comments(path.read_text(encoding="utf-8"))
        for match in DECL.finditer(text):
            block = balanced_parens(text, match.end() - 1)
            if not block:
                continue
            found[match.group(1)] = set(PARAM.findall(top_level_pieces(block)))
    return found


def names_used_by_shared_sources() -> set[str]:
    """Every identifier the flavour-independent sources mention.

    A flavour is free to have declarations of its own — the subscription
    handoff exists only in `direct` and that is the whole point. Parity is
    required only where the shared sources reach into a flavour, because those
    are the names that must resolve in both builds.
    """
    used: set[str] = set()
    for path in sorted((SRC / "main").rglob("*.kt")):
        text = strip_comments(path.read_text(encoding="utf-8"))
        used.update(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", text))
    return used


def strings_of(source_set: str) -> set[str]:
    """Every string resource name a source set defines, any locale."""
    names: set[str] = set()
    for path in sorted((SRC / source_set).rglob("res/values*/strings.xml")):
        names.update(STRING_NAME.findall(path.read_text(encoding="utf-8")))
    return names


def channel_wording_stays_in_its_channel() -> int:
    """The Play build must not CONTAIN the other channel's wording.

    A string defined only in `src/direct/res` does not exist in the Play
    build, so referencing it from shared or Play sources is a build failure —
    and, worse, it means someone tried to show a checkout where there is none.
    """
    direct_only = strings_of("direct") - strings_of("main") - strings_of("play")
    if not direct_only:
        return 0
    problems = 0
    for source_set in ("main", "play"):
        for path in sorted((SRC / source_set).rglob("*.kt")):
            text = strip_comments(path.read_text(encoding="utf-8"))
            for name in sorted(direct_only):
                if re.search(r"\bR\.string\.%s\b" % re.escape(name), text):
                    rel = path.relative_to(SRC.parent.parent)
                    print(f"{rel}: uses R.string.{name}, which only the direct channel has")
                    problems += 1
    return problems


def main() -> int:
    missing_root = [f for f in FLAVOURS if not (SRC / f).is_dir()]
    if missing_root:
        print(f"no sources for flavour(s): {', '.join(missing_root)}")
        return 1

    declared = {f: flavour_declarations(f) for f in FLAVOURS}
    play, direct = declared["play"], declared["direct"]
    # A name the shared sources also DECLARE is their own — `Factory`,
    # `create` and the like exist all over the app. Only names the shared
    # sources use but do not declare have to come from a flavour.
    from check_named_arguments import declarations

    own = set(declarations(sorted((SRC / "main").rglob("*.kt"))))
    shared = ((set(play) | set(direct)) & names_used_by_shared_sources()) - own

    problems = 0
    for name in sorted(shared):
        if name not in play:
            print(f"`{name}` exists in direct but not in play — the Play build will not compile")
            problems += 1
            continue
        if name not in direct:
            print(f"`{name}` exists in play but not in direct — the direct build will not compile")
            problems += 1
            continue
        if play[name] != direct[name]:
            only_play = sorted(play[name] - direct[name])
            only_direct = sorted(direct[name] - play[name])
            detail = []
            if only_play:
                detail.append(f"play only: {', '.join(only_play)}")
            if only_direct:
                detail.append(f"direct only: {', '.join(only_direct)}")
            print(f"`{name}` takes different parameters per flavour — {'; '.join(detail)}")
            problems += 1

    if problems:
        print(f"\n{problems} declaration(s) have drifted between the flavours")
        return 1

    leaked = channel_wording_stays_in_its_channel()
    if leaked:
        print(f"\n{leaked} reference(s) to wording the Play build does not have")
        return 1

    print(f"the flavours are interchangeable ({len(shared)} shared declaration(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())

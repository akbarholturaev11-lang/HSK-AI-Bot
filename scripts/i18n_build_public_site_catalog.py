#!/usr/bin/env python3
"""Bundle the existing public-site copy from its canonical localization source.

Keep Python's existing structured content/tuple contracts and SEO route assembly
byte-identical. The generator parses source but never executes it or uses a DB.
"""
from __future__ import annotations

import argparse
import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "localization/public_site/content.py"
TARGET = "app/public_site/content.py"


def read_source(root: Path = ROOT) -> bytes:
    path = root / SOURCE
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Public-site canonical source must not be a symlink")
    raw = path.read_bytes()
    tree = ast.parse(raw.decode("utf-8"))
    names = {target.id for node in tree.body if isinstance(node, ast.Assign)
             for target in node.targets if isinstance(target, ast.Name)}
    required = {"DOWNLOAD_PATH", "GOOGLE_SIGNIN_PRIVACY_PAGES", "PAGES",
                "PAGE_TRANSLATIONS", "NAV_LABELS", "RELATED_LINKS", "HOME_PATHS",
                "CTA", "DOWNLOAD_CTA"}
    if not required <= names:
        raise ValueError("Public-site content exports are missing")
    return raw


def generate(root: Path = ROOT, *, check: bool) -> list[str]:
    raw = read_source(root)
    path = root / TARGET
    if any((root / p).is_symlink() for p in (Path(TARGET), *Path(TARGET).parents)):
        raise ValueError("Public-site generated target must not be a symlink")
    changed = not path.is_file() or path.read_bytes() != raw
    if changed and not check:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return [TARGET] if changed else []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        changed = generate(args.root, check=args.check)
    except (OSError, ValueError, SyntaxError, UnicodeError) as exc:
        print("Public-site catalog generation failed:", exc, file=sys.stderr)
        return 1
    if args.check and changed:
        print("Stale public-site copy:", ", ".join(changed), file=sys.stderr)
        return 1
    print("Canonical public-site copy:", len(changed), "stale" if args.check else "written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

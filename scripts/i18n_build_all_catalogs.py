#!/usr/bin/env python3
"""Validate/build every centrally authored local UI resource in one command.

Validation completes for all namespaces before any output is written. Generated
artifacts remain committed and bundled; no runtime translation API is needed.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    i18n_build_android_catalogs as android,
    i18n_build_bot_catalogs as bot,
    i18n_build_course_catalogs as course,
    i18n_build_desktop_catalogs as desktop,
    i18n_build_local_catalogs as common,
    i18n_build_notification_catalogs as notifications,
    i18n_build_public_site_catalog as public_site,
)

ROOT = Path(__file__).resolve().parents[1]


def output_files(root: Path = ROOT) -> dict[str, bytes]:
    sources = [
        common.output_files(common.read_sources(root)),
        course.output_files(course.read_sources(root)),
        bot.output_files(bot.read_sources(root)),
        desktop.output_files(desktop.read_sources(root)),
        notifications.output_files(notifications.read_sources(root)),
        android.read_sources(root),
        {public_site.TARGET: public_site.read_source(root)},
    ]
    result = {}
    for outputs in sources:
        for path, value in outputs.items():
            if path in result:
                raise ValueError("Multiple canonical owners for generated artifact: " + path)
            result[path] = value.encode("utf-8") if isinstance(value, str) else value
    return result


def generate(root: Path = ROOT, *, check: bool) -> list[str]:
    outputs = output_files(root)
    changed = []
    for relative, raw in outputs.items():
        target = root / relative
        if any((root / p).is_symlink() for p in (Path(relative), *Path(relative).parents)):
            raise ValueError("Generated artifact target is a symlink: " + relative)
        if not target.is_file() or target.read_bytes() != raw:
            changed.append(relative)
    if not check:
        for relative in changed:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(outputs[relative])
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        changed = generate(args.root, check=args.check)
    except (OSError, ValueError, TypeError, KeyError, SyntaxError) as exc:
        print("Local catalog build failed:", exc, file=sys.stderr)
        return 1
    if args.check and changed:
        print("Stale local catalogs:", ", ".join(changed), file=sys.stderr)
        return 1
    print("All local UI catalogs:", len(output_files(args.root)), "artifacts;",
          len(changed), "stale" if args.check else "written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

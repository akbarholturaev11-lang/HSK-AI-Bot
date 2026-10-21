#!/usr/bin/env python3
"""Validate/build every centrally authored local UI resource in one command.

Validation completes for all namespaces before any output is written. Generated
artifacts remain committed and bundled; no runtime translation API is needed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    i18n_build_android_catalogs as android,
    i18n_build_bot_catalogs as bot,
    i18n_build_course_catalogs as course,
    i18n_build_desktop_catalogs as desktop,
    i18n_build_local_catalogs as common,
    i18n_build_miniapp_catalogs as miniapp,
    i18n_build_notification_catalogs as notifications,
    i18n_build_public_site_catalog as public_site,
)
from scripts.i18n_baseline_guard import git_blob_sha1

ROOT = Path(__file__).resolve().parents[1]
BROWSER_PAGES = (
    "course-v3.html", "course_v3_memorize.html", "course_v3_mistakes.html",
    "course_v3_onboarding.html", "course_v3_pronunciation.html", "course_v3_recognition.html",
    "course_v3_test.html", "course_v3_voice.html", "desktop-download.html",
    "hsk-gaplar.html", "hsk-lugat.html", "subscription.html",
)


def output_files(root: Path = ROOT) -> dict[str, bytes]:
    sources = [
        common.output_files(common.read_sources(root)),
        course.output_files(course.read_sources(root)),
        bot.output_files(bot.read_sources(root)),
        desktop.output_files(desktop.read_sources(root)),
        notifications.output_files(notifications.read_sources(root)),
        miniapp.output_files(miniapp.read_sources(root)),
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


def browser_version_updates(root: Path, outputs: dict[str, bytes]) -> dict[str, bytes]:
    """Only update cache tokens on previously reviewed HTML, never approve code drift."""
    pages = [root / "app/static" / name for name in BROWSER_PAGES]
    if not any(path.exists() for path in pages):
        return {}  # A source-only generator fixture has no browser consumers.
    if not all(path.is_file() for path in pages):
        raise ValueError("Missing registered browser catalog consumer")
    review_path = root / "localization/baselines/reviewed_ui_changes.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))
    assets = dict(outputs)
    for relative in (
        "app/static/course_v3_data/ads.js", "app/static/course_v3_data/memo.js",
        "app/static/course_v3_data/desktop-download.js", "app/static/course_v3_data/profile-carousel.js",
        "app/static/desktop-download-page.js",
    ):
        assets[relative] = (root / relative).read_bytes()
    fingerprints = {relative.removeprefix("app/static/"): git_blob_sha1(raw)[:12]
                    for relative, raw in assets.items() if relative.startswith("app/static/")}
    changed = {}
    for path in pages:
        if path.is_symlink():
            raise ValueError("Browser consumer is a symlink")
        original = path.read_bytes()
        text = original.decode("utf-8")
        for url, digest in fingerprints.items():
            pattern = re.compile(r'(?P<prefix>\bsrc=["\x27]/?' + re.escape(url)
                                 + r'\?v=)(?P<version>[^"\x27&#]+)(?P<suffix>[^"\x27]*)(?=["\x27])')
            def replace(match):
                date = re.match(r"\d{8}", match.group("version"))
                if not date:
                    raise ValueError("Unknown browser cache version format: " + url)
                return match.group("prefix") + date.group(0) + "-" + digest + match.group("suffix")
            text = pattern.sub(replace, text)
            if re.search(r'\bsrc=["\x27]/?' + re.escape(url) + r'["\x27]', text):
                raise ValueError("Browser UI asset lacks a cache version: " + url)
        updated = text.encode("utf-8")
        if updated == original:
            continue
        relative = path.relative_to(root).as_posix()
        note = review["files"].get(relative)
        if not isinstance(note, dict) or note.get("reviewed_sha1") != git_blob_sha1(original):
            raise ValueError("Review browser source changes before refreshing cache tokens: " + relative)
        note["reviewed_sha1"] = git_blob_sha1(updated)
        changed[relative] = updated
    if changed:
        changed[review_path.relative_to(root).as_posix()] = (
            json.dumps(review, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8")
    return changed


def generate(root: Path = ROOT, *, check: bool) -> list[str]:
    outputs = output_files(root)
    outputs.update(browser_version_updates(root, outputs))
    changed = []
    for relative, raw in outputs.items():
        target = root / relative
        if any((root / p).is_symlink() for p in (Path(relative), *Path(relative).parents)):
            raise ValueError("Generated artifact target is a symlink: " + relative)
        if target.exists() and not target.is_file():
            raise ValueError("Generated artifact target is not a file: " + relative)
        if any((root / p).exists() and not (root / p).is_dir() for p in Path(relative).parents):
            raise ValueError("Generated artifact ancestor is not a directory: " + relative)
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

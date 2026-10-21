#!/usr/bin/env python3
"""Build the Bot's local Python catalog from localization/ui/*/bot.json.

Fixed Bot copy is authored once here. Existing common/course copy is referenced
by key, not copied into this namespace. No server, AI, database or network call
is used to generate or read this artifact.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from string import Formatter
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ("uz", "ru", "tj")
OUTPUT = "app/bot/generated/bot_i18n.py"
KEY = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)*")


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs)


def _signature(text: str):
    return Counter((field, spec, conversion) for _, field, spec, conversion
                   in Formatter().parse(text) if field is not None)


def read_sources(root: Path = ROOT):
    catalogs = {}
    for locale in LOCALES:
        data = _read(root / f"localization/ui/{locale}/bot.json")
        if (set(data) != {"schema_version", "namespace", "locale", "messages",
                          "references", "tables"}
                or data["schema_version"] != 1 or data["namespace"] != "bot"
                or data["locale"] != locale):
            raise ValueError(f"Bot catalog metadata mismatch: {locale}")
        messages, refs, tables = data["messages"], data["references"], data["tables"]
        if not isinstance(messages, dict) or not messages or not isinstance(refs, dict):
            raise ValueError(f"Invalid Bot messages/references: {locale}")
        if set(messages) & set(refs):
            raise ValueError(f"Bot messages/reference collision: {locale}")
        for key, value in messages.items():
            if not KEY.fullmatch(key) or not isinstance(value, str) or not value.strip():
                raise ValueError(f"Invalid Bot message: {locale}/{key}")
            try:
                _signature(value)
            except ValueError as exc:
                raise ValueError(f"Invalid Bot placeholder: {locale}/{key}") from exc
        shared = {ns: _read(root / f"localization/ui/{locale}/{ns}.json")["messages"]
                  for ns in ("common", "course")}
        for key, reference in refs.items():
            if (not KEY.fullmatch(key) or not isinstance(reference, dict)
                    or set(reference) != {"namespace", "key"}
                    or reference["namespace"] not in shared
                    or reference["key"] not in shared[reference["namespace"]]):
                raise ValueError(f"Invalid Bot reference: {locale}/{key}")
        if not isinstance(tables, dict) or set(tables) != {"TEXTS", "COURSE_I18N"}:
            raise ValueError(f"Invalid Bot compatibility tables: {locale}")
        for name, entries in tables.items():
            if not isinstance(entries, dict) or not entries:
                raise ValueError(f"Invalid Bot compatibility table: {locale}/{name}")
            for old, key in entries.items():
                if not KEY.fullmatch(old) or key not in messages.keys() | refs.keys():
                    raise ValueError(f"Unknown Bot compatibility message: {locale}/{name}/{old}")
        catalogs[locale] = data
    first = catalogs["uz"]
    for locale, data in catalogs.items():
        if (set(data["messages"]) != set(first["messages"])
                or data["references"] != first["references"]
                or data["tables"] != first["tables"]):
            raise ValueError(f"Bot locale key/reference/table drift: {locale}")
        for key, text in data["messages"].items():
            if _signature(text) != _signature(first["messages"][key]):
                raise ValueError(f"Bot placeholder parity mismatch: {locale}/{key}")
    return catalogs


def materialize_tables(catalogs, root: Path = ROOT):
    """Return compatibility tables without importing the application."""
    result = {name: {} for name in ("TEXTS", "COURSE_I18N")}
    for locale, data in catalogs.items():
        shared = {ns: _read(root / f"localization/ui/{locale}/{ns}.json")["messages"]
                  for ns in ("common", "course")}
        resolved = dict(data["messages"])
        for key, ref in data["references"].items():
            resolved[key] = shared[ref["namespace"]][ref["key"]]
        for name, entries in data["tables"].items():
            result[name][locale] = {old: resolved[key] for old, key in entries.items()}
    return result


def _json(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
            .replace("\u2028", r"\u2028").replace("\u2029", r"\u2029"))


def output_files(catalogs):
    first = catalogs["uz"]
    body = (
        "# Generated by scripts/i18n_build_bot_catalogs.py; do not edit.\n"
        "from app.bot.generated.common_i18n import COMMON_MESSAGES\n"
        "from app.bot.generated.course_i18n import COURSE_MESSAGES\n\n"
        "BOT_MESSAGES = " + _json({c: d["messages"] for c, d in catalogs.items()}) + "\n\n"
        "BOT_REFERENCES = " + _json(first["references"]) + "\n\n"
        "BOT_TABLE_KEYS = " + _json(first["tables"]) + "\n\n"
        "def bot_message(key, locale):\n"
        "    reference = BOT_REFERENCES.get(key)\n"
        "    if reference is not None:\n"
        "        source = COMMON_MESSAGES if reference['namespace'] == 'common' else COURSE_MESSAGES\n"
        "        return source.get(locale, {}).get(reference['key'])\n"
        "    return BOT_MESSAGES.get(locale, {}).get(key)\n\n"
        "TEXTS = {locale: {old: bot_message(key, locale)\n"
        "                   for old, key in BOT_TABLE_KEYS['TEXTS'].items()}\n"
        "         for locale in BOT_MESSAGES}\n"
        "COURSE_I18N = {locale: {old: bot_message(key, locale)\n"
        "                         for old, key in BOT_TABLE_KEYS['COURSE_I18N'].items()}\n"
        "               for locale in BOT_MESSAGES}\n"
    )
    return {OUTPUT: body}


def generate(root: Path = ROOT, *, check: bool):
    changed = []
    for relative, content in output_files(read_sources(root)).items():
        path = root / relative
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            changed.append(relative)
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        changed = generate(args.root, check=args.check)
        if args.check and changed:
            raise ValueError("Generated Bot catalog is stale: " + ", ".join(changed))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print("Bot catalog generation failed:", exc, file=sys.stderr)
        return 1
    print(f"Bot catalogs: {len(LOCALES)} locales, {len(output_files(read_sources(args.root)))} "
          f"local artifact, {len(changed)} files {'stale' if args.check else 'written'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

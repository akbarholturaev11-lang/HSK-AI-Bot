#!/usr/bin/env python3
"""Validate the shared phrasebook source and publish its static app copies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "scripts" / "ready_phrases" / "phrases.json"
OUTPUTS = (
    ROOT / "app" / "static" / "course_v3_data" / "ready-phrases-v1.json",
    ROOT / "android" / "app" / "src" / "main" / "assets" / "ready-phrases-v1.json",
)
LANGUAGES = ("uz", "ru", "tj")
HANZI = re.compile(r"[一-鿿]")


def validate(catalog: dict) -> None:
    if catalog.get("version") != 1:
        raise ValueError("catalog version must be 1")

    categories = catalog.get("categories")
    phrases = catalog.get("phrases")
    if not isinstance(categories, list) or len(categories) != 12:
        raise ValueError("catalog must have the 12 reviewed categories")
    if not isinstance(phrases, list) or len(phrases) != 300:
        raise ValueError("catalog must have exactly 300 phrases")

    category_ids: set[str] = set()
    for position, category in enumerate(categories, start=1):
        category_id = category.get("id")
        labels = category.get("labels")
        if not isinstance(category_id, str) or not category_id or category_id in category_ids:
            raise ValueError(f"category {position} has a missing or duplicate id")
        if category.get("sort_order") != position:
            raise ValueError(f"category {category_id} has unstable sort order")
        if not isinstance(labels, dict) or any(not str(labels.get(lang, "")).strip() for lang in LANGUAGES):
            raise ValueError(f"category {category_id} is missing a translated label")
        category_ids.add(category_id)

    ids: set[str] = set()
    phrases_by_category: dict[str, list[dict]] = {category_id: [] for category_id in category_ids}
    hanzi: set[str] = set()
    for position, phrase in enumerate(phrases, start=1):
        phrase_id = phrase.get("id")
        category_id = phrase.get("category_id")
        text = str(phrase.get("zh", "")).strip()
        translations = phrase.get("translations")
        if not isinstance(phrase_id, str) or not phrase_id or phrase_id in ids:
            raise ValueError(f"phrase {position} has a missing or duplicate id")
        if category_id not in category_ids:
            raise ValueError(f"phrase {phrase_id} references an unknown category")
        if not HANZI.search(text) or not str(phrase.get("pinyin", "")).strip():
            raise ValueError(f"phrase {phrase_id} needs Chinese text and pinyin")
        if text in hanzi:
            raise ValueError(f"phrase text is duplicated: {text}")
        if not isinstance(translations, dict) or any(
            not str(translations.get(lang, "")).strip() for lang in LANGUAGES
        ):
            raise ValueError(f"phrase {phrase_id} is missing a translation")
        ids.add(phrase_id)
        hanzi.add(text)
        phrases_by_category[category_id].append(phrase)

    for category_id, category_phrases in phrases_by_category.items():
        sort_orders = [phrase.get("sort_order") for phrase in category_phrases]
        if not sort_orders or sort_orders != list(range(1, len(category_phrases) + 1)):
            raise ValueError(f"category {category_id} has an empty or unstable phrase order")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the generated Android and Mini App copies match the source",
    )
    args = parser.parse_args()

    try:
        source_bytes = SOURCE.read_bytes()
        catalog = json.loads(source_bytes)
        validate(catalog)
        for output in OUTPUTS:
            if args.check:
                if not output.is_file() or output.read_bytes() != source_bytes:
                    raise ValueError(f"{output.relative_to(ROOT)} is missing or out of date")
            else:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(source_bytes)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Ready phrase assets: {exc}", file=sys.stderr)
        return 1

    action = "match" if args.check else "generated"
    print(f"Ready phrase assets {action}: 300 phrases, 12 categories, uz/ru/tj")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Check central UZ/RU/TJ grammar translations against all original HSK sources."""
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.i18n_legacy_lesson_content_risk_audit import ROOT
from scripts.i18n_grammar_private_review_queue import assemble_private_review_queue
from scripts.i18n_editor_translation_draft import _validate
from scripts.i18n_editor_grammar_mirror_integrity import attest_mirrored_grammar_preview
from scripts.i18n_editor_semantic_guard import (
    AMBIGUOUS_PRECIPITATION_EXAMPLE, SPECIFIC_WEATHER, SNOW_REQUIRED,
    RUSSIAN_GENDER_PLACEHOLDER,
)

CATALOG = "localization/lessons/nhsk2_grammar_uz_ru_tj.tsv"
LANGS = ("uz", "ru", "tj")


def context_source_sha256(context):
    """Pin a locale row to the complete source context and every occurrence."""
    identity = {
        "review_id": context["review_id"],
        "grammar": context["grammar"],
        "chinese_example": context["chinese_example"],
        "pinyin": context["pinyin"],
        "occurrences": sorted(
            ({
                "source_file": item["source_file"],
                "source_git_blob_sha1": item["source_git_blob_sha1"],
                "pointer": item["pointer"],
                "mirrored_paths": sorted(item["mirrored_paths"]),
            } for item in context["occurrences"]),
            key=lambda item: (item["source_file"], item["pointer"]),
        ),
    }
    raw = json.dumps(identity, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def read_canonical_catalog(path):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames != ["review_id", "context_sha256", *LANGS]:
            raise ValueError("canonical catalog schema invalid")
        rows = list(reader)
    if any(None in item for item in rows):
        raise ValueError("canonical catalog row has extra columns")
    if len(rows) != 136:
        raise ValueError("136 unique contexts required")
    reviewed = {}
    for i, item in enumerate(rows, 1):
        key = f"G{i:03d}"
        if item.get("review_id") != key:
            raise ValueError("missing, reordered or duplicate context")
        digest = item.get("context_sha256", "")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("invalid context source SHA-256")
        values = {}
        for locale in LANGS:
            value = item.get(locale)
            if (not isinstance(value, str) or not value.strip()
                    or value != value.strip() or "\n" in value or "\r" in value
                    or "\t" in value):
                raise ValueError("empty/invalid translation")
            if unicodedata.normalize("NFC", value) != value:
                raise ValueError("non-NFC translation")
            values[locale] = value
        reviewed[key] = {"context_sha256": digest, "translations": values}
    return reviewed


def audit_canonical_grammar(root=ROOT):
    reviewed = read_canonical_catalog(root / CATALOG)
    queue, _ = assemble_private_review_queue(root)
    if queue["unique_exact_contexts"] != 136 or queue["missing_original_maps"] != 272:
        raise ValueError("original source review inventory changed")
    drafts = {}
    for ctx in queue["contexts"]:
        key = ctx["review_id"]
        entry = reviewed.get(key)
        if entry is None:
            raise ValueError("unmatched Chinese grammar context")
        if entry["context_sha256"] != context_source_sha256(ctx):
            raise ValueError("source context SHA-256 changed")
        values = entry["translations"]
        zh = ctx["chinese_example"]
        if RUSSIAN_GENDER_PLACEHOLDER.search(values["ru"]):
            raise ValueError("Russian placeholder regression")
        for lc in LANGS:
            if zh == AMBIGUOUS_PRECIPITATION_EXAMPLE and SPECIFIC_WEATHER[lc].search(values[lc]):
                raise ValueError("weather meaning invented")
            if ("下雪" in zh or "下着雪" in zh) and not SNOW_REQUIRED[lc].search(values[lc]):
                raise ValueError("snow meaning lost")
        for ref in ctx["occurrences"]:
            file = ref["source_file"]
            draft = drafts.setdefault(file, {
                "schema_version": 1, "kind": "p3_editor_translation_draft",
                "source_file": file, "source_git_blob_sha1": ref["source_git_blob_sha1"],
                "translations": [],
            })
            if draft["source_git_blob_sha1"] != ref["source_git_blob_sha1"]:
                raise ValueError("source SHA collision")
            draft["translations"].append({"pointer": ref["pointer"], "values": values.copy()})
    original_count = mirror_count = 0
    for file, draft in drafts.items():
        draft["translations"].sort(key=lambda item: item["pointer"])
        raw = (root / file).read_bytes()
        _, fields, _ = _validate(raw, draft)
        proof = attest_mirrored_grammar_preview(raw, draft)
        if not proof["all_other_fields_unchanged"]:
            raise ValueError("protected course content changed")
        original_count += len(fields)
        mirror_count += proof["verified_mirrored_card_maps"]
    if len(drafts) != 48 or original_count != 272 or mirror_count != 136:
        raise ValueError("lesson/mirror count drift")
    return drafts, {"contexts": 136, "independent_values": 408,
                    "source_lessons": 48, "original_maps": original_count,
                    "mirror_maps": mirror_count, "source_files_written": 0}


def main():
    try:
        _, status = audit_canonical_grammar()
    except (OSError, ValueError, TypeError, KeyError, IndexError, UnicodeError):
        print("Canonical grammar catalog REJECTED (content withheld)", file=sys.stderr)
        return 1
    print("Canonical UZ/RU/TJ grammar verified:", status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

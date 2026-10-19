#!/usr/bin/env python3
"""Agent-owned P3 semantic regression guard for PRIVATE grammar candidate drafts.

Narrow deterministic checks for known translation failures; NOT a claim that
all three languages were semantically audited. Do not print protected content.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

if __package__:
    from scripts.i18n_legacy_lesson_content_risk_audit import ROOT
    from scripts.i18n_editor_context_progress import audit_private_context_progress
    from scripts.i18n_editor_translation_batch import _private_draft_directory
    from scripts.i18n_editor_translation_draft import (
        _source_identity, _unique_json_keys, _validate,
    )
    from scripts.i18n_grammar_private_review_queue import assemble_private_review_queue
else:
    from i18n_legacy_lesson_content_risk_audit import ROOT
    from i18n_editor_context_progress import audit_private_context_progress
    from i18n_editor_translation_batch import _private_draft_directory
    from i18n_editor_translation_draft import _source_identity, _unique_json_keys, _validate
    from i18n_grammar_private_review_queue import assemble_private_review_queue

# Translate precipitation without a supplied rain/snow subject; do not turn
# the ambiguous source into rain or snow by assumption.
AMBIGUOUS_PRECIPITATION_EXAMPLE = "昨天比今天下得大。"
SPECIFIC_WEATHER = {
    "uz": re.compile(r"\b(?:qor|yomg[‘'ʻ]?ir|yomg)\b", re.I),
    "ru": re.compile(r"\b(?:снег|дожд[ьяеиуом]*)\b", re.I),
    "tj": re.compile(r"\b(?:барф|борон)\b", re.I),
}
SNOW_REQUIRED = {
    "uz": re.compile(r"\bqor\b", re.I),
    "ru": re.compile(r"\bснег\b|снеж", re.I),
    "tj": re.compile(r"\bбарф\b", re.I),
}
# Phrases like "не возвращался(ась)" and "читал(а)" are draft-editor
# placeholders, not polished Russian learner-facing translation.
RUSSIAN_GENDER_PLACEHOLDER = re.compile(
    r"\b[А-Яа-яЁё]+\((?:а|ась|ся|ый|ая|ё?л|ла)\)\b?"
)


def audit_private_translation_semantics(
    draft_dir: Path, *, root: Path = ROOT, require_complete: bool = True,
) -> dict[str, Any]:
    if type(require_complete) is not bool:
        raise ValueError("invalid semantic audit policy")
    folder = _private_draft_directory(root, draft_dir)
    coverage = audit_private_context_progress(folder, root=root)
    if require_complete and (
        coverage["source_maps_outstanding"] or coverage["contexts_needing_candidate"]
    ):
        raise ValueError("complete candidate coverage required")

    queue, _ = assemble_private_review_queue(root)
    context_by_location: dict[tuple[str, str], dict[str, Any]] = {}
    for ctx in queue["contexts"]:
        for occurrence in ctx["occurrences"]:
            identity = (occurrence["source_file"], occurrence["pointer"])
            if identity in context_by_location:
                raise ValueError("duplicate source grammar context")
            context_by_location[identity] = ctx

    review_checked: set[str] = set()
    issues: dict[str, set[str]] = {}
    for path in sorted(folder.iterdir()):
        draft = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_unique_json_keys,
        )
        relative = draft["source_file"]
        _source_identity(relative)
        _, fields, _ = _validate((root / relative).read_bytes(), draft)
        for pointer, values in fields:
            ctx = context_by_location.get((relative, pointer))
            if ctx is None:
                raise ValueError("translation no longer matches source context")
            rid = ctx["review_id"]
            chinese = ctx["chinese_example"]
            review_checked.add(rid)
            found = issues.setdefault(rid, set())
            ru = values["ru"]
            if RUSSIAN_GENDER_PLACEHOLDER.search(ru):
                found.add("russian_gender_placeholder")
            for lang in ("uz", "ru", "tj"):
                if (chinese == AMBIGUOUS_PRECIPITATION_EXAMPLE
                        and SPECIFIC_WEATHER[lang].search(values[lang])):
                    found.add("source_weather_type_invented_" + lang)
                if (("下雪" in chinese or "下着雪" in chinese)
                        and not SNOW_REQUIRED[lang].search(values[lang])):
                    found.add("explicit_snow_meaning_missing_" + lang)

    problems = {rid: sorted(errors) for rid, errors in issues.items() if errors}
    if problems:
        # Never print example, translations, personal details, or answer data.
        details = "; ".join(f"{rid}: {','.join(kinds)}"
                            for rid, kinds in sorted(problems.items()))
        raise ValueError("agent translation QA regression: " + details)

    return {
        "schema_version": 1,
        "kind": "p3_private_agent_semantic_regression_audit",
        "unique_contexts_checked": len(review_checked),
        "known_semantic_regressions": 0,
        "candidate_source_maps_checked": coverage["source_maps_with_validated_draft"],
        "source_maps_still_missing": coverage["source_maps_outstanding"],
        "status": "KNOWN_REGRESSION_CHECK_PASSED_NOT_FULL_SEMANTIC_PROOF",
        "qualified_human_review_required": False,
        "agent_context_review_still_required": True,
        "ready_to_ship": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--draft-dir", required=True, type=Path)
    p.add_argument("--allow-partial", action="store_true")
    args = p.parse_args()
    try:
        result = audit_private_translation_semantics(
            args.draft_dir, require_complete=not args.allow_partial,
        )
    except (ValueError, OSError, KeyError, TypeError, IndexError, UnicodeError):
        print("P3 agent semantic regression REJECTED (texts withheld)",
              file=sys.stderr)
        return 1
    print(
        "P3 known semantic regressions:", result["known_semantic_regressions"],
        "in", result["unique_contexts_checked"],
        "contexts; agent context QA still required; NOT SHIPPABLE",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

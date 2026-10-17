#!/usr/bin/env python3
"""Read-only P0 audit of identity scope for Mini App browser storage keys.

This scanner never reads browser storage, contacts the user, imports FastAPI,
logs a lesson/quiz body or modifies runtime code. Existing unscoped keys are
recorded as review blockers, not rewritten before account-switch QA.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = Path("localization/review/miniapp_client_storage_scope_20261017.json")
STORAGE_CALL = re.compile(
    r"""(?<!\w)(localStorage|sessionStorage)\s*\.\s*(getItem|setItem|removeItem)\s*\(\s*(['"])([^'"]+)\3"""
)
REQUIRED_KEY_FUNCTIONS = {
    "lessonDataKey", "lessonResumeKey", "lessonMasteryKey",
    "foundationCacheKey", "studySetupTimeKey",
}


def _function_line(source: str, name: str) -> str:
    match = re.search(
        r"\bfunction\s+" + re.escape(name) + r"\s*\([^)]*\)\s*\{([\s\S]{0,750}?)\}", source
    )
    return match.group(1) if match else ""


def audit_source(sources: dict[str, str], registry: dict) -> dict:
    aliases = registry.get("sources", {})
    if not isinstance(aliases, dict) or set(aliases) != {"course", "memorize"}:
        raise ValueError("Mini App storage source set changed")
    if set(sources) != set(aliases):
        raise ValueError("Mini App source alias mismatch")

    found: Counter = Counter()
    for alias, source in sources.items():
        for match in STORAGE_CALL.finditer(source):
            found[(alias, match.group(1), match.group(4), match.group(2))] += 1

    expected: Counter = Counter()
    for row in registry.get("literal_key_classes", []):
        if row.get("source") not in aliases:
            raise ValueError("Unknown storage source alias in registry")
        for op in row.get("expected_operations", []):
            expected[(row["source"], row["storage"], row["key"], op)] += 1
    if len(registry.get("literal_key_classes", [])) != 11:
        raise ValueError("Missing literal key classification")

    regressions = []
    for key, actual in sorted((found - expected).items()):
        regressions.append({
            "kind": "new_or_extra_storage_access", "source": key[0],
            "storage": key[1], "key": key[2], "op": key[3], "count": actual,
        })
    for key, missing in sorted((expected - found).items()):
        regressions.append({
            "kind": "missing_reviewed_storage_access", "source": key[0],
            "storage": key[1], "key": key[2], "op": key[3], "count": missing,
        })

    dynamic = {}
    names = set()
    for row in registry.get("dynamic_key_contracts", []):
        name, alias = row["function"], row["source"]
        names.add(name)
        body = _function_line(sources[alias], name)
        has_scope = "localUserScope()" in body
        expected_scope = bool(row["expected_identity_scope"])
        dynamic[name] = {
            "source": alias, "found": bool(body),
            "local_user_scope_called": has_scope,
            "scope_review": "scope_helper_used" if has_scope else "helper_not_used",
        }
        if not body or has_scope != expected_scope:
            regressions.append({"kind": "dynamic_cache_key_contract_drift", "function": name})
    if names != REQUIRED_KEY_FUNCTIONS:
        raise ValueError("Dynamic Mini App cache-key registry incomplete")

    if "localUserScope()" not in _function_line(sources["course"], "lessonMasteryKey"):
        regressions.append({"kind": "mastery_identity_scope_missing"})
    if "localUserScope()" not in _function_line(sources["course"], "foundationCacheKey"):
        regressions.append({"kind": "foundation_identity_scope_missing"})

    if 'localStorage.getItem("hsk_memo")' not in sources["memorize"] or (
        'localStorage.setItem("hsk_memo",' not in sources["memorize"]
    ):
        regressions.append({"kind": "memorize_mastery_storage_changed"})

    return {
        "schema_version": 1,
        "status": "SOURCE_REVIEW_PENDING_ACCOUNT_SWITCH_QA" if not regressions else "REGRESSION",
        "literal_storage_calls": sum(found.values()),
        "classified_literal_keys": len(registry["literal_key_classes"]),
        "dynamic_cache_key_functions": dynamic,
        "risks": registry.get("risks", []),
        "regressions": regressions,
        "limits": "Source key names only, no values, user IDs, browser storage or runtime session inspection.",
    }


def audit(root: Path = ROOT) -> dict:
    registry = json.loads((root / REGISTRY).read_text(encoding="utf-8"))
    return audit_source({
        alias: (root / relative).read_text(encoding="utf-8")
        for alias, relative in registry["sources"].items()
    }, registry)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, UnicodeError, KeyError, TypeError) as exc:
        print("P0 Mini App storage audit blocked:", exc, file=sys.stderr)
        return 1
    print("P0 Mini App storage:", result["status"],
          "literal calls:", result["literal_storage_calls"],
          "regressions:", len(result["regressions"]))
    return int(bool(result["regressions"]))


if __name__ == "__main__":
    raise SystemExit(main())

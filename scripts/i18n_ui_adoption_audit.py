#!/usr/bin/env python3
"""Reject new unclassified Python three-locale UI maps outside local catalogs.

Existing learning material, provider metadata, admin/dynamic copy and explicit
compatibility fallbacks are reviewed by content-free AST hashes. A new fixed UI
map must be centrally authored instead. This is source coverage, not device QA.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXCEPTIONS = "localization/review/ui_map_exceptions.json"
CATEGORIES = {"legacy_fallback", "learning_material", "provider_metadata",
              "dynamic_campaign", "locale_adapter", "admin_only", "qa_only"}


def map_fingerprint(node: ast.Dict) -> str:
    # Python 3.13+ can omit empty Call.keywords/args from ast.dump. Preserve
    # the 3.11 representation so local tooling and CI classify the same source.
    options = {"include_attributes": False}
    if sys.version_info >= (3, 13):
        options["show_empty"] = True
    return hashlib.sha256(ast.dump(node, **options).encode()).hexdigest()


def locale_maps(root: Path = ROOT):
    for directory in ("app/bot", "app/services", "app/api"):
        for path in sorted((root / directory).rglob("*.py")):
            if "generated" in path.relative_to(root).parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            functions = [n for n in ast.walk(tree)
                         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            for node in ast.walk(tree):
                if (not isinstance(node, ast.Dict) or len(node.keys) != 3
                        or not all(isinstance(key, ast.Constant) for key in node.keys)
                        or {key.value for key in node.keys} != {"uz", "ru", "tj"}):
                    continue
                scope = max((f for f in functions if f.lineno <= node.lineno <= f.end_lineno),
                            key=lambda f: f.lineno, default=None)
                digest = map_fingerprint(node)
                yield {"source": path.relative_to(root).as_posix(), "line": node.lineno,
                       "function": scope.name if scope else "module", "sha256": digest}


def audit(root: Path = ROOT):
    registry = json.loads((root / EXCEPTIONS).read_text(encoding="utf-8"))
    if (set(registry) != {"schema_version", "scope", "exceptions"}
            or registry["schema_version"] != 1 or not isinstance(registry["exceptions"], list)):
        raise ValueError("Invalid UI map classification registry")
    allowed, categories = Counter(), {}
    for row in registry["exceptions"]:
        if (set(row) != {"source", "sha256", "category", "count"}
                or row["category"] not in CATEGORIES or type(row["count"]) is not int
                or row["count"] < 1 or len(row["sha256"]) != 64
                or not row["source"].startswith(("app/bot/", "app/services/", "app/api/"))):
            raise ValueError("Invalid UI map exception")
        key = (row["source"], row["sha256"])
        if key in allowed:
            raise ValueError("Duplicate UI map classification")
        allowed[key] = row["count"]
        categories[key] = row["category"]
    actual, rows = Counter(), list(locale_maps(root))
    for row in rows:
        actual[(row["source"], row["sha256"])] += 1
    unclassified = [{"source": source, "sha256": digest, "count": count}
                    for (source, digest), count in (actual - allowed).items()]
    stale = [{"source": source, "sha256": digest, "count": count}
             for (source, digest), count in (allowed - actual).items()]
    return {"schema_version": 1,
            "status": "LOCAL_UI_OWNERSHIP_CHECKED_NOT_DEVICE_ACCEPTANCE",
            "classified_maps": sum(actual.values()),
            "categories": dict(Counter(categories[key] for key in actual.elements() if key in categories)),
            "unclassified": unclassified, "stale_classifications": stale}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(args.root)
    except (OSError, ValueError, TypeError, SyntaxError) as exc:
        print("UI adoption audit failed:", exc, file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Python UI maps:", report["classified_maps"], "classified;",
          len(report["unclassified"]), "unclassified;",
          len(report["stale_classifications"]), "stale")
    return int(bool(report["unclassified"] or report["stale_classifications"]))


if __name__ == "__main__":
    raise SystemExit(main())

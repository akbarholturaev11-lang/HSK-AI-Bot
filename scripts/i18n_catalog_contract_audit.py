#!/usr/bin/env python3
"""P0 read-only key/placeholder inventory of existing Bot and Desktop catalogs.

The Python catalog is parsed using ast.literal_eval, never imported/executed.
The desktop static catalog is read as source; it is not evaluated in JS.
Results identify drift for manual review, not automatic translation defects.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ("uz", "ru", "tj")
BOT_SOURCE = "app/bot/utils/i18n.py"
DESKTOP_SOURCE = "desktop/ui/js/i18n.js"
PLACEHOLDER = re.compile(r"(?<!\{)\{([A-Za-z_]\w*)\}(?!\})")
HTML_TAG = re.compile(r"</?([a-zA-Z][\w-]*)\b")
JS_SECTION = re.compile(r"^  (uz|ru|tj): \{$", re.M)
JS_KEY = re.compile(r"^ {4}([A-Za-z_$][\w$]*)\s*:", re.M)


def signature(value: str) -> list[tuple[str, int]]:
    return sorted(Counter(PLACEHOLDER.findall(value)).items())


def html_signature(value: str) -> list[tuple[str, int]]:
    return sorted(Counter(HTML_TAG.findall(value)).items())


def comparison(catalog: dict, *, source: str, table: str) -> dict:
    if set(catalog) != set(LOCALES):
        raise ValueError(f"{source}/{table}: incomplete locale table")
    for locale in LOCALES:
        if not isinstance(catalog[locale], dict):
            raise ValueError(f"{source}/{table}: invalid {locale} map")
        if any(not isinstance(k, str) or not isinstance(v, str)
               for k, v in catalog[locale].items()):
            raise ValueError(f"{source}/{table}: non-string resource")
    union = set().union(*(catalog[locale] for locale in LOCALES))
    missing, placeholder_review, markup_review = [], [], []
    for key in sorted(union):
        present = [lang for lang in LOCALES if key in catalog[lang]]
        absent = [lang for lang in LOCALES if lang not in present]
        if absent:
            missing.append({"key": key, "absent": absent})
        if len(present) < 2:
            continue
        expected = catalog[present[0]][key]
        if any(signature(catalog[lang][key]) != signature(expected)
               for lang in present[1:]):
            placeholder_review.append({
                "key": key,
                "signatures": {lang: signature(catalog[lang][key]) for lang in present},
            })
        if any(html_signature(catalog[lang][key]) != html_signature(expected)
               for lang in present[1:]):
            markup_review.append({"key": key, "locales": present})
    return {
        "source": source, "table": table, "keys_union": len(union),
        "key_counts": {lang: len(catalog[lang]) for lang in LOCALES},
        "missing_keys": missing,
        "placeholder_drift": placeholder_review,
        "html_tag_count_drift": markup_review,
    }


def _assigned_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        return node.targets[0].id if isinstance(node.targets[0], ast.Name) else None
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def _entry_duplicates(dictionary: ast.Dict) -> list[str]:
    keys = [k.value for k in dictionary.keys
            if isinstance(k, ast.Constant) and isinstance(k.value, str)]
    return sorted(k for k, n in Counter(keys).items() if n > 1)


def python_tables(source: str) -> tuple[dict, list[dict]]:
    """Extract static locale dictionaries and detect duplicate source keys."""
    tree = ast.parse(source)
    tables, duplicate_keys = {}, []
    for node in tree.body:
        name = _assigned_name(node)
        if not name or (name not in ("TEXTS", "COURSE_I18N") and not name.endswith("_I18N")):
            continue
        value = node.value
        if not isinstance(value, ast.Dict):
            raise ValueError(f"Bot catalog {name} is no longer a static dict; manual review required")
        table = ast.literal_eval(value)
        if not isinstance(table, dict) or set(table) != set(LOCALES):
            raise ValueError(f"Bot catalog {name}: unexpected locales")
        for language, child in zip(value.keys, value.values):
            if not isinstance(language, ast.Constant) or language.value not in LOCALES:
                raise ValueError(f"Bot catalog {name}: unsupported locale key")
            if not isinstance(child, ast.Dict):
                raise ValueError(f"Bot catalog {name}: non-literal locale mapping")
            for key in _entry_duplicates(child):
                duplicate_keys.append({"table": name, "locale": language.value, "key": key})
        tables[name] = table
    if "TEXTS" not in tables or "COURSE_I18N" not in tables:
        raise ValueError("Bot base catalogs absent")
    return tables, duplicate_keys


def _update_destination(node: ast.For) -> str | None:
    """Recognize the existing setdefault(...).update(_texts) pattern only."""
    for child in node.body:
        if not isinstance(child, ast.Expr) or not isinstance(child.value, ast.Call):
            continue
        call = child.value
        if not isinstance(call.func, ast.Attribute) or call.func.attr != "update":
            continue
        receiver = call.func.value
        if not isinstance(receiver, ast.Call) or not isinstance(receiver.func, ast.Attribute):
            continue
        if receiver.func.attr != "setdefault" or not isinstance(receiver.func.value, ast.Name):
            continue
        if len(call.args) == 1 and isinstance(call.args[0], ast.Name) and call.args[0].id == "_texts":
            return receiver.func.value.id
    return None


def bot_catalogs(source: str) -> dict:
    tables, duplicate_keys = python_tables(source)
    audits = [comparison(data, source=BOT_SOURCE, table=name)
              for name, data in sorted(tables.items())]
    effective = {
        base: {lang: dict(tables[base][lang]) for lang in LOCALES}
        for base in ("TEXTS", "COURSE_I18N")
    }
    tree = ast.parse(source)
    merges, overrides, unrecognized = [], [], []
    for node in tree.body:
        if not isinstance(node, ast.For) or not isinstance(node.iter, ast.Call):
            continue
        iterator = node.iter.func
        if not isinstance(iterator, ast.Attribute) or iterator.attr != "items":
            continue
        if not isinstance(iterator.value, ast.Name):
            continue
        name = iterator.value.id
        if name not in tables:
            continue
        destination = _update_destination(node)
        if destination not in effective:
            unrecognized.append(name)
            continue
        merges.append({"from": name, "into": destination})
        for lang in LOCALES:
            overlap = set(effective[destination][lang]) & set(tables[name][lang])
            overrides.extend({"catalog": destination, "locale": lang, "key": k, "from": name}
                             for k in sorted(overlap))
            effective[destination][lang].update(tables[name][lang])
    return {
        "tables": audits,
        "effective": [comparison(data, source=BOT_SOURCE, table=name + "_effective")
                      for name, data in sorted(effective.items())],
        "detected_merges": merges,
        "unrecognized_merges": unrecognized,
        "duplicate_literal_keys": duplicate_keys,
        "overrides": overrides,
    }


def desktop_catalogs(source: str) -> dict:
    """Only accept the current top-level three-locale static JS dictionary.

    Lines containing a key but not its full string are included as text up to
    the next key. This deliberately does not interpret JS template expressions.
    """
    sections = list(JS_SECTION.finditer(source))
    if [match.group(1) for match in sections] != list(LOCALES):
        raise ValueError("Desktop locale sections changed; JS scanner requires review")
    catalogs, duplicate_keys = {}, []
    for index, section in enumerate(sections):
        lang = section.group(1)
        end = sections[index + 1].start() if index + 1 < len(sections) else source.find("\n};", section.end())
        if end < 0:
            raise ValueError("Desktop messages object is not closed")
        body = source[section.end():end]
        matches = list(JS_KEY.finditer(body))
        if not matches:
            raise ValueError(f"Desktop {lang} source has no keys")
        values = {}
        for pos, item in enumerate(matches):
            name = item.group(1)
            text = body[item.end():matches[pos + 1].start() if pos + 1 < len(matches) else len(body)]
            if name in values:
                duplicate_keys.append({"locale": lang, "key": name})
            values[name] = text
        catalogs[lang] = values
    return {"comparison": comparison(catalogs, source=DESKTOP_SOURCE, table="messages"),
            "duplicate_literal_keys": duplicate_keys,
            "parsing_limit": "static indented property scan, not execution of JS or rendered screenshots"}


def audit(root: Path = ROOT) -> dict:
    bot = bot_catalogs((root / BOT_SOURCE).read_text(encoding="utf-8"))
    desktop = desktop_catalogs((root / DESKTOP_SOURCE).read_text(encoding="utf-8"))
    warnings = [
        "Candidate drift is not a verified translation error. Bot text may fall back to Russian.",
        "Desktop and Bot use separate fallback rules; P0 does not change runtime behavior.",
        "Bot catalog merges and overrides are source-level evidence, not payment or auth changes.",
    ]
    return {"schema_version": 1, "status": "review_required", "bot": bot,
            "desktop": desktop, "warnings": warnings}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        report = audit(args.root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, SyntaxError, TypeError) as exc:
        print("P0 Bot/Desktop catalog audit failed:", exc, file=sys.stderr)
        return 1
    print("Bot source catalogs:", len(report["bot"]["tables"]),
          "| Desktop keys:", report["desktop"]["comparison"]["key_counts"],
          "| Bot ambiguous merges:", len(report["bot"]["unrecognized_merges"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Bundle remaining fixed browser UI maps, preserving legacy shape/fallbacks.

Only UI strings belong here. Existing common/course keys are references; icons
and other fixed identifiers remain layout literals. No course answer data or
per-string runtime translation request is introduced.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ("uz", "ru", "tj")
TARGET = "app/static/course_v3_data/hsk-miniapp-i18n.js"
KEY = re.compile(r"[a-zA-Z][a-zA-Z0-9_.]*")
VARIABLE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _unique_pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("Duplicate Mini App JSON key: " + key)
        result[key] = value
    return result


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs)


def _signature(value):
    residual = VARIABLE.sub("", value)
    if "{" in residual or "}" in residual:
        raise ValueError("Unsupported Mini App UI placeholder")
    if re.search(r"<\s*/?\s*(?:script|iframe|object|embed)\b|\bon\w+\s*=|javascript:", value, re.I):
        raise ValueError("Unsafe Mini App UI markup")
    return Counter(VARIABLE.findall(value))


def read_sources(root: Path = ROOT):
    catalogs = {}
    for locale in LOCALES:
        data = _read(root / f"localization/ui/{locale}/miniapp.json")
        if (set(data) != {"schema_version", "namespace", "locale", "messages", "maps"}
                or type(data["schema_version"]) is not int or data["schema_version"] != 1
                or data["namespace"] != "miniapp" or data["locale"] != locale
                or not isinstance(data["messages"], dict) or not isinstance(data["maps"], dict)
                or not data["maps"]):
            raise ValueError("Invalid Mini App catalog metadata")
        for key, value in data["messages"].items():
            if not KEY.fullmatch(key) or "__" in key or not isinstance(value, str) or not value.strip():
                raise ValueError("Invalid Mini App UI message: " + str(key))
            _signature(value)
        shared = {namespace: _read(root / f"localization/ui/{locale}/{namespace}.json")["messages"]
                  for namespace in ("common", "course")}
        def validate(node):
            if not isinstance(node, dict) or len(node) != 1:
                raise ValueError("Invalid Mini App UI map")
            kind, value = next(iter(node.items()))
            if kind == "message":
                if value not in data["messages"]:
                    raise ValueError("Unknown Mini App UI message")
            elif kind == "reference":
                if (not isinstance(value, dict) or set(value) != {"namespace", "key"}
                        or value["namespace"] not in shared
                        or value["key"] not in shared[value["namespace"]]):
                    raise ValueError("Invalid Mini App shared reference")
            elif kind == "literal":
                if not isinstance(value, str):
                    raise ValueError("Invalid Mini App identifier")
            elif kind == "object" and isinstance(value, dict):
                for key, child in value.items():
                    if key in {"__proto__", "prototype", "constructor"}:
                        raise ValueError("Unsafe Mini App layout key")
                    validate(child)
            elif kind == "list" and isinstance(value, list):
                for child in value:
                    validate(child)
            else:
                raise ValueError("Invalid Mini App UI layout kind")
        for key, node in data["maps"].items():
            if not KEY.fullmatch(key) or "__" in key:
                raise ValueError("Invalid Mini App map key")
            validate(node)
        if "ui.subscription.renewalDates.copy1" in data["maps"]:
            raise ValueError("Intl locale identifiers are metadata, not UI copy")
        # Android benefit rows are [icon identifier, translated label]. The
        # identifier must remain in the source layout even if copy is edited.
        promo = data["maps"].get("ui.desktop_download.ANDROID_PROMO_COPY.copy1", {})
        for context in promo.get("object", {}).values():
            benefits = context.get("object", {}).get("benefits", {}).get("list", [])
            for benefit in benefits:
                pair = benefit.get("list", [])
                if len(pair) != 2 or set(pair[0]) != {"literal"}:
                    raise ValueError("Android promo icon identifiers must stay literal")
        data["_shared"] = shared
        catalogs[locale] = data
    first = catalogs["uz"]
    for locale, data in catalogs.items():
        if set(data["messages"]) != set(first["messages"]) or data["maps"] != first["maps"]:
            raise ValueError("Mini App UI locale/layout parity")
        for key, text in data["messages"].items():
            if _signature(text) != _signature(first["messages"][key]):
                raise ValueError("Mini App UI placeholder parity: " + key)
    return catalogs


def output_files(catalogs):
    def encode(value):
        return (json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                .replace("<", r"\u003c").replace("\u2028", r"\u2028").replace("\u2029", r"\u2029"))
    # Keep admin-only copy out of learner bundles; one canonical namespace
    # supplies a small, separately generated public Admin PWA catalog.
    messages = {locale: {key: value for key, value in data["messages"].items()
                         if not key.startswith("ui.admin_pwa.")}
                for locale, data in catalogs.items()}
    references = {"common": set(), "course": set()}
    def collect(node):
        if "reference" in node:
            ref = node["reference"]
            references[ref["namespace"]].add(ref["key"])
        elif "object" in node:
            for child in node["object"].values():
                collect(child)
        elif "list" in node:
            for child in node["list"]:
                collect(child)
    for layout in catalogs["uz"]["maps"].values():
        collect(layout)
    shared = {namespace: {locale: {key: data["_shared"][namespace][key] for key in sorted(keys)}
                          for locale, data in catalogs.items()}
              for namespace, keys in references.items()}
    body = (
        "/* Generated by scripts/i18n_build_miniapp_catalogs.py; do not edit. */\n"
        '(function(window){"use strict";\n'
        "var messages=" + encode(messages) + ";\n"
        "var maps=" + encode(catalogs["uz"]["maps"]) + ";\n"
        "var shared=" + encode(shared) + ";\n"
        "window.HSKAI_MINIAPP_I18N=messages;\n"
        "window.HSKAILocaleMap=function(key,fallback){\n"
        "  var layout=maps[key];if(!layout||!fallback||typeof fallback!==\"object\")return fallback;\n"
        "  function render(node,base,locale){\n"
        "    var text;if(node.message){text=(messages[locale]||{})[node.message]}\n"
        "    else if(node.reference){var ref=node.reference,catalog=ref.namespace===\"common\"?window.HSKAI_COMMON_I18N:window.HSKAI_COURSE_I18N;text=((catalog||{})[locale]||{})[ref.key];if(typeof text!==\"string\"||!text)text=shared[ref.namespace][locale][ref.key]}\n"
        "    else if(Object.prototype.hasOwnProperty.call(node,\"literal\"))return base;\n"
        "    else if(node.list&&Array.isArray(base))return base.map(function(value,index){return node.list[index]?render(node.list[index],value,locale):value});\n"
        "    else if(node.object&&base&&typeof base===\"object\"&&!Array.isArray(base)){var copy={};Object.keys(base).forEach(function(name){copy[name]=node.object[name]?render(node.object[name],base[name],locale):base[name]});return copy}\n"
        "    return typeof text===\"string\"&&text?text:base;\n"
        "  }\n"
        "  var result={};Object.keys(fallback).forEach(function(locale){result[locale]=render(layout,fallback[locale],locale)});return result;\n"
        "};\n})(window);\n"
    )
    admin = {locale: {key.removeprefix("ui.admin_pwa."): value
                      for key, value in data["messages"].items() if key.startswith("ui.admin_pwa.")}
             for locale, data in catalogs.items()}
    for locale, data in catalogs.items():
        for key, shared_key in {"close": "action.close", "logout": "action.logout",
                                "retry": "desktopAuth.retry", "loading": "state.loading"}.items():
            admin[locale][key] = data["_shared"]["common"][shared_key]
    return {TARGET: body, "app/static/admin-pwa/catalog.js":
            "/* Generated from canonical Mini App/common catalogs; do not edit. */\n"
            + "window.HSKAI_ADMIN_I18N=" + encode(admin) + ";\n"}


def generate(root: Path = ROOT, *, check: bool):
    changed = []
    for relative, body in output_files(read_sources(root)).items():
        target = root / relative
        if not target.is_file() or target.read_text(encoding="utf-8") != body:
            changed.append(relative)
            if not check:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(body, encoding="utf-8")
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        changed = generate(args.root, check=args.check)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print("Mini App catalog generation failed:", exc, file=sys.stderr)
        return 1
    if args.check and changed:
        print("Stale Mini App catalog:", ", ".join(changed), file=sys.stderr)
        return 1
    print("Mini App fixed maps:", len(read_sources(args.root)["uz"]["maps"]),
          "maps;", len(changed), "stale" if args.check else "written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

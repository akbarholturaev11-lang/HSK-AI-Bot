#!/usr/bin/env python3
"""Validate the repository's first-party Admin Analytics coverage registry."""

import argparse
import ast
import json
from pathlib import Path
import re
import sys


REGISTRY = "docs/analytics/FEATURE_ANALYTICS_COVERAGE.json"
ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = ("android", "telegram", "iphone_pwa", "macos", "windows")
SECTIONS = ("home", "overview", "platform", "course", "funnel", "money", "sources", "report")
STORES = ("course_miniapp_events", "conversion_funnel_events")
STATUSES = ("covered", "partial", "not_instrumented", "not_applicable")
ID = re.compile(r"[a-z][a-z0-9_]*")
FILE = re.compile(r"(?:[a-zA-Z0-9_.-]+/)*[a-zA-Z0-9_.-]+")
TEST_SYMBOL = re.compile(r"(?:[A-Za-z][A-Za-z0-9_]*::)?test_[A-Za-z0-9_]+")


class CoverageError(ValueError):
    pass


def require(condition, label, message):
    if not condition:
        raise CoverageError(f"{label}: {message}")


def fields(value, label, required, optional=()):
    require(isinstance(value, dict), label, "expected an object")
    missing = set(required) - value.keys()
    unknown = value.keys() - set(required) - set(optional)
    require(not missing and not unknown, label,
            f"invalid fields (missing: {sorted(missing)}, unknown: {sorted(unknown)})")


def rows(value, label, *, required=False):
    require(isinstance(value, list) and (value or not required), label,
            "expected a non-empty list" if required else "expected a list")
    return value


def identifier(value, label):
    require(isinstance(value, str) and ID.fullmatch(value), label, "expected a stable snake_case identifier")
    return value


def unique(values, label, allowed=None):
    for value in rows(values, label, required=True):
        require(isinstance(value, str) and (allowed is None or value in allowed),
                label, f"invalid value {value!r}")
    require(len(values) == len(set(values)), label, "duplicate values")
    return values


def explanation(value, label):
    require(isinstance(value, str) and value.strip(), label, "a non-empty reason is required")


def exact_file(root, value, label):
    require(isinstance(value, str) and FILE.fullmatch(value)
            and all(part not in {".", ".."} for part in value.split("/"))
            and (root / value).is_file() and (root / value).resolve().is_relative_to(root.resolve()),
            label, f"expected an exact existing file path, got {value!r}")
    return root / value


def validate_chain(root, reference, label):
    require(isinstance(reference, str) and "::" in reference, label,
            "covered requires a chain_test as tests/file.py::test_name")
    path, symbol = reference.split("::", 1)
    require(path.startswith("tests/") and path.endswith(".py") and TEST_SYMBOL.fullmatch(symbol),
            label, "chain_test must name an executable Python test")
    source = exact_file(root, path, label)
    nodes = ast.parse(source.read_text(encoding="utf-8"), filename=path).body
    if "::" in symbol:
        classname, symbol = symbol.split("::")
        nodes = next((node.body for node in nodes if isinstance(node, ast.ClassDef)
                      and node.name == classname), ())
    require(any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol
                for node in nodes), label, f"chain test not found: {reference}")


def validate_platforms(root, platforms, label):
    fields(platforms, label, PLATFORMS)
    for platform, cell in platforms.items():
        scope = f"{label}/{platform}"
        fields(cell, scope, ("status",), ("reason", "chain_test"))
        require(cell["status"] in STATUSES, scope, f"invalid status {cell['status']!r}")
        if cell["status"] == "covered":
            validate_chain(root, cell.get("chain_test"), scope)
        else:
            require("chain_test" not in cell, scope, "only covered entries can name a chain test")
            explanation(cell.get("reason"), scope)


def validate_schema(registry, root=ROOT):
    fields(registry, "registry", ("version", "metrics", "flows", "critical_paths", "exemptions"))
    require(type(registry["version"]) is int and registry["version"] == 1, "registry", "unsupported version")
    metrics = set()
    for row in rows(registry["metrics"], "metrics", required=True):
        fields(row, "metric", ("section", "key", "kind", "filters"), ("platforms",))
        section, key = row["section"], identifier(row["key"], "metric key")
        label = f"metric {section}.{key}"
        require(section in SECTIONS, label, "unknown section")
        require((section, key) not in metrics, label, "duplicate metric")
        metrics.add((section, key))
        unique(row["filters"], label, ("overall", *PLATFORMS))
        require(row["kind"] in ("metric", "metadata"), label, "kind must be metric or metadata")
        if row["kind"] == "metric":
            validate_platforms(root, row.get("platforms"), label)
        else:
            require("platforms" not in row, label, "projection metadata does not have platform coverage")

    flows = set()
    events = set()
    for flow in rows(registry["flows"], "flows", required=True):
        fields(flow, "flow", ("id", "description", "events", "platforms"))
        flow_id = identifier(flow["id"], "flow id")
        label = f"flow {flow_id}"
        require(flow_id not in flows, label, "duplicate flow")
        flows.add(flow_id)
        explanation(flow["description"], label)
        validate_platforms(root, flow["platforms"], label)
        for group in rows(flow["events"], label):
            fields(group, label, ("store", "role", "names"), ("reason",))
            store, role = group["store"], group["role"]
            require(store in STORES, label, f"unknown event store {store!r}")
            require(role in ("declared", "internal", "no_writer"), label, f"unknown event role {role!r}")
            if role != "declared":
                explanation(group.get("reason"), label)
            for name in unique(group["names"], label):
                identifier(name, label)
                require((store, name) not in events, label, f"duplicate event {store}:{name}")
                events.add((store, name))

    paths = set()
    for row in rows(registry["critical_paths"], "critical_paths", required=True):
        fields(row, "critical path", ("path", "flows"))
        path = row["path"]
        exact_file(root, path, "critical path")
        require(path not in paths, path, "duplicate critical path")
        paths.add(path)
        unique(row["flows"], path, flows)

    exemptions = set()
    for row in rows(registry["exemptions"], "exemptions"):
        fields(row, "exemption", ("reason",), ("path", "store", "event"))
        explanation(row["reason"], "exemption")
        if "path" in row:
            require("store" not in row and "event" not in row, "exemption", "name one exact path or event")
            exact_file(root, row["path"], "exemption")
            target = (row["path"],)
        else:
            require(row.get("store") in STORES, "exemption", "an event exemption must name its store")
            target = (row["store"], identifier(row.get("event"), "exemption event"))
            require(target not in events, "exemption", f"{target} already has a registry entry")
        require(target not in exemptions, "exemption", f"duplicate exemption {target}")
        exemptions.add(target)
    return registry


def no_duplicate_fields(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "registry JSON", f"duplicate field {key!r}")
        result[key] = value
    return result


def load_registry(text):
    return json.loads(text, object_pairs_hook=no_duplicate_fields)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema-only", action="store_true", help="validate registry structure only")
    parser.parse_args(argv)
    try:
        registry = validate_schema(load_registry((ROOT / REGISTRY).read_text(encoding="utf-8")))
    except (OSError, ValueError, SyntaxError) as exc:
        print(f"Analytics coverage failed: {exc}", file=sys.stderr)
        return 1
    print(f"Analytics registry valid: {len(registry['metrics'])} projection keys, {len(registry['flows'])} flows")
    return 0


if __name__ == "__main__":
    sys.exit(main())

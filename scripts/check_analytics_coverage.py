#!/usr/bin/env python3
"""Check the Admin Analytics registry, event sources and changed flow paths."""

import argparse
import ast
from collections import defaultdict
import json
from pathlib import Path
import re
import subprocess
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


_COURSE_STORE = "course_miniapp_events"
_CONVERSION_STORE = "conversion_funnel_events"
_EVENT_DECLARATIONS = {
    "app/db/models/course_miniapp_event.py": {
        "COURSE_MINIAPP_EVENT_NAMES": _COURSE_STORE,
        "CLIENT_COURSE_MINIAPP_EVENT_NAMES": _COURSE_STORE,
    },
    "app/db/models/conversion_funnel_event.py": {
        "CONVERSION_FUNNEL_EVENT_NAMES": _CONVERSION_STORE,
    },
    "app/admin_api/pwa_metrics.py": {"COURSE_EVENTS": _COURSE_STORE},
    "app/services/course_miniapp_admin_analytics_service.py": {
        "FOUNDATION_FUNNEL_EVENT_NAMES": _COURSE_STORE,
        "FOUNDATION_MEANINGFUL_LEARNING_EVENTS": _COURSE_STORE,
    },
}
_EVENT_FIELDS = {
    "app/api/pwa_auth.py": ("PwaProUiEvent", "event", _CONVERSION_STORE),
    "app/api/android_events.py": ("AndroidEventRequest", "event_name", _COURSE_STORE),
}
_EVENT_MODELS = {
    "CourseMiniAppEvent": _COURSE_STORE,
    "ConversionFunnelEvent": _CONVERSION_STORE,
}
_COURSE_WRITERS = {"record_client_event", "record_server_event"}
_CONVERSION_WRITERS = {"record", "record_once", "record_in_transaction"}
_EVENT_SCAN_MARKERS = (*_EVENT_MODELS, *_COURSE_WRITERS, "ConversionFunnelService")


def _event_ast_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _event_assignments(nodes):
    for node in nodes:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    yield target.id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            yield node.target.id, node.value


def _event_definitions(tree):
    values = dict(_event_assignments(tree.body))
    imports = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and not node.level and node.module:
            for alias in node.names:
                imports[alias.asname or alias.name] = (node.module, alias.name)
    return values, imports


def _event_strings(node, path, definitions, load_module, seen=frozenset()):
    """Resolve literals/branches and simple named constants, not arbitrary data flow."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        yield node.value, path
    elif isinstance(node, ast.Name):
        binding = path, node.id
        if binding in seen:
            return
        values, imports = definitions
        if node.id in values:
            yield from _event_strings(values[node.id], path, definitions, load_module, seen | {binding})
        elif node.id in imports:
            module, symbol = imports[node.id]
            imported_path, imported = load_module(module)
            yield from _event_strings(ast.Name(id=symbol), imported_path, imported, load_module,
                                      seen | {binding})
    elif isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        for item in node.elts:
            yield from _event_strings(item, path, definitions, load_module, seen)
    elif isinstance(node, ast.IfExp):
        for branch in (node.body, node.orelse):
            yield from _event_strings(branch, path, definitions, load_module, seen)
    elif isinstance(node, ast.Starred):
        yield from _event_strings(node.value, path, definitions, load_module, seen)
    elif isinstance(node, ast.Call) and _event_ast_name(node.func) in {"tuple", "set", "frozenset", "list"}:
        if len(node.args) == 1 and not node.keywords:
            yield from _event_strings(node.args[0], path, definitions, load_module, seen)


def _event_module_loader(read_source=None):
    cache = {}

    def load_module(module):
        path = module.replace(".", "/") + ".py"
        if read_source is None or not module.startswith("app."):
            return path, ({}, {})
        if path not in cache:
            cache[path] = _event_definitions(ast.parse(read_source(path), filename=path))
        return path, cache[path]

    return load_module


def _events_from_source(path, source, load_module):
    declarations = _EVENT_DECLARATIONS.get(path, {})
    field = _EVENT_FIELDS.get(path)
    if not declarations and not field and not any(name in source for name in _EVENT_SCAN_MARKERS):
        return
    tree = ast.parse(source, filename=path)
    definitions = values, imports = _event_definitions(tree)
    constructors = {**_EVENT_MODELS, **{local: _EVENT_MODELS[remote]
                    for local, (_, remote) in imports.items() if remote in _EVENT_MODELS}}
    conversion_classes = {"ConversionFunnelService", *(local for local, (_, remote) in imports.items()
                                                       if remote == "ConversionFunnelService")}
    conversion_instances = {
        target for target, value in _event_assignments(ast.walk(tree))
        if isinstance(value, ast.Call) and _event_ast_name(value.func) in conversion_classes
    }

    for symbol, store in declarations.items():
        for event, source_path in _event_strings(values.get(symbol), path, definitions, load_module):
            yield (store, event), {path, source_path}

    if field:
        cls, attribute, store = field
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or node.name != cls:
                continue
            for member in node.body:
                if (isinstance(member, ast.AnnAssign) and _event_ast_name(member.target) == attribute
                        and isinstance(member.annotation, ast.Subscript)
                        and _event_ast_name(member.annotation.value) == "Literal"):
                    for event, source_path in _event_strings(member.annotation.slice, path,
                                                             definitions, load_module):
                        yield (store, event), {path, source_path}

    for call in ast.walk(tree):
        if not isinstance(call, ast.Call):
            continue
        argument = next((kw.value for kw in call.keywords if kw.arg == "event_name"), None)
        if argument is None:
            continue
        name = _event_ast_name(call.func)
        store = constructors.get(name)
        if name in _COURSE_WRITERS or (path == "app/services/desktop_download_service.py" and name == "_record_event"):
            store = _COURSE_STORE
        elif name in _CONVERSION_WRITERS and isinstance(call.func, ast.Attribute):
            receiver = call.func.value
            if ((isinstance(receiver, ast.Call) and _event_ast_name(receiver.func) in conversion_classes)
                    or (isinstance(receiver, ast.Name) and receiver.id in conversion_instances)):
                store = _CONVERSION_STORE
        if store:
            for event, source_path in _event_strings(argument, path, definitions, load_module):
                yield (store, event), {path, source_path}


def events_in_file(path, source, *, load_module=None):
    """Return qualified event names declared/read/attempted in one Python blob."""
    path = Path(path).as_posix()
    if not path.startswith("app/") or not path.endswith(".py"):
        return set()
    load_module = load_module or _event_module_loader()
    return {event for event, _ in _events_from_source(path, source, load_module)}


def inventory(root):
    """Return {(store, event): {repository-relative evidence paths}} without importing the app."""
    root = Path(root)
    result = defaultdict(set)

    def read_source(path):
        file = root / path
        return file.read_text(encoding="utf-8") if file.is_file() else ""

    load_module = _event_module_loader(read_source)
    for file in sorted((root / "app").rglob("*.py")):
        path = file.relative_to(root).as_posix()
        for event, paths in _events_from_source(path, read_source(path), load_module):
            result[event].update(paths)
    return dict(result)


def registered_events(registry):
    return {
        (group["store"], name): flow["id"]
        for flow in registry.get("flows", ())
        for group in flow["events"]
        for name in group["names"]
    }


def validate_events(registry, found):
    declared = set(registered_events(registry))
    exempt = {(row["store"], row["event"]) for row in registry["exemptions"] if "event" in row}
    errors = [
        f"{path}: unregistered event {store}:{event}"
        for store, event in sorted(found.keys() - declared - exempt)
        for path in sorted(found[store, event])
    ]
    errors.extend(f"stale registry event {store}:{event}"
                  for store, event in sorted(declared - found.keys()))
    errors.extend(f"stale event exemption {store}:{event}"
                  for store, event in sorted(exempt - found.keys()))
    if errors:
        raise CoverageError("\n".join(errors))


def validate_diff(registry, previous, paths, event_changes):
    """Require a change to a related flow or a fresh, exact exemption."""
    old_flows = {row["id"]: row for row in previous.get("flows", ())}
    new_flows = {row["id"]: row for row in registry["flows"]}
    changed_flows = {key for key in old_flows.keys() | new_flows.keys()
                     if old_flows.get(key) != new_flows.get(key)}
    old_events = registered_events(previous)
    new_events = registered_events(registry)
    reviewed = [row for row in registry["exemptions"] if row not in previous.get("exemptions", ())]
    exempt_paths = {row["path"] for row in reviewed if "path" in row}
    exempt_events = {(row["store"], row["event"]) for row in reviewed if "event" in row}
    affected = {}
    for row in (*previous.get("critical_paths", ()), *registry["critical_paths"]):
        affected.setdefault(row["path"], set()).update(row["flows"])

    errors = []
    for path in sorted(set(paths) - exempt_paths):
        for store, event in sorted(event_changes.get(path, ())):
            key = (store, event)
            if key not in exempt_events and not ({old_events.get(key), new_events.get(key)} & changed_flows):
                errors.append(f"{path}: {store}:{event} changed without a matching flow update or exemption")
        flows = affected.get(path, set())
        if flows and not flows & changed_flows:
            errors.append(f"{path}: update a related flow ({', '.join(sorted(flows))}) "
                          "or add a reviewed exact-path exemption")
    if errors:
        raise CoverageError("\n".join(errors))


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, encoding="utf-8").stdout


def git_blob(root, ref, path):
    if not git(root, "ls-tree", "-z", ref, "--", path):
        return ""
    return git(root, "show", f"{ref}:{path}")


def check_git_diff(root, registry, base, head, mode):
    base = git(root, "rev-parse", "--verify", "--end-of-options", f"{base}^{{commit}}").strip()
    head = git(root, "rev-parse", "--verify", "--end-of-options", f"{head}^{{commit}}").strip()
    require(head == git(root, "rev-parse", "HEAD").strip(), "diff", "--head must be the checked out commit")
    if mode == "pull_request":
        base = git(root, "merge-base", base, head).strip()
    paths = git(root, "diff", "--name-only", "--no-renames", "-z", base, head, "--").split("\0")
    previous = git_blob(root, base, REGISTRY)
    old_imports = _event_module_loader(lambda path: git_blob(root, base, path))
    new_imports = _event_module_loader(lambda path: git_blob(root, head, path))
    changes = {}
    for path in paths:
        if path.startswith("app/") and path.endswith(".py"):
            before = events_in_file(path, git_blob(root, base, path), load_module=old_imports)
            after = events_in_file(path, git_blob(root, head, path), load_module=new_imports)
            changes[path] = before ^ after
    validate_diff(registry, load_registry(previous) if previous else {}, paths, changes)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema-only", action="store_true", help="validate registry structure only")
    parser.add_argument("--base", help="base commit for the coverage diff")
    parser.add_argument("--head", default="HEAD", help="checked out head commit for the coverage diff")
    parser.add_argument("--mode", choices=("push", "pull_request"), default="push")
    args = parser.parse_args(argv)
    if args.schema_only and args.base:
        parser.error("--schema-only and --base cannot be combined")
    try:
        registry = validate_schema(load_registry((ROOT / REGISTRY).read_text(encoding="utf-8")))
        if not args.schema_only:
            validate_events(registry, inventory(ROOT))
        if args.base:
            check_git_diff(ROOT, registry, args.base, args.head, args.mode)
    except subprocess.CalledProcessError as exc:
        print(f"Analytics coverage could not read the Git diff: {exc.stderr.strip()}", file=sys.stderr)
        return 1
    except (OSError, ValueError, SyntaxError) as exc:
        print(f"Analytics coverage failed: {exc}", file=sys.stderr)
        return 1
    print(f"Analytics registry valid: {len(registry['metrics'])} projection keys, {len(registry['flows'])} flows")
    return 0


if __name__ == "__main__":
    sys.exit(main())

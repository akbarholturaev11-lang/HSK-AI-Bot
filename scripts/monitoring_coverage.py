"""Monitoring section of the shared coverage check (design D10).

Imported by ``scripts/check_analytics_coverage.py`` so Analytics and
Monitoring keep one registry, one checker run and one workflow. Stdlib only;
the application is never imported. The runtime catalog is read by path.
"""

import ast
from hashlib import sha256
import importlib.util
from pathlib import Path
import re

ANDROID_SOURCE_DIR = "android/app/src"
ANDROID_FEATURE_DIR = f"{ANDROID_SOURCE_DIR}/main/java/com/pomp/hskai/feature"
ANDROID_FEATURE_DIRS = tuple(ANDROID_FEATURE_DIR.replace("/main/", f"/{source}/")
                             for source in ("main", "direct", "play"))
CATALOG = "app/services/monitoring/catalog.py"
INBOX_MODULE = "app/admin_api/pwa_inbox.py"
ADMIN_INBOX_ROUTE = "/api/admin/v1/inbox/list"
CHAIN_HELPER = "assert_monitoring_chain"
PLATFORMS = ("android", "iphone_pwa", "telegram", "server")
MODES = ("declare", "require_covered")
STATUSES = ("covered", "partial", "not_instrumented", "not_applicable")
PENDING_CONSUMER = "Admin consumer pending"
ROUTE_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace", "api_route", "websocket"}
ROUTE_REGISTRARS = {"add_api_route", "add_api_websocket_route"}
INTAKE_ROUTES = {
    "android": "/api/v3/android/diagnostics",
    "iphone_pwa": "/api/v3/pwa/diagnostics",
    "telegram": "/api/miniapp/event",
    "server": "report_server_failure",
}
PAGE_PATTERNS = ("course-v3.html", "course_v3_*.html", "iphone-pwa-*.html", "subscription.html")
SOURCE_FILE = re.compile(r"(?:[a-zA-Z0-9_.-]+/)*[a-zA-Z0-9_.-]+")
KOTLIN_CATALOG = "android/app/src/main/java/com/pomp/hskai/core/diagnostics/DiagnosticCatalog.kt"
JS_REPORTER_CALL = re.compile(
    r"HskDiag\.report\(\s*['\"]([a-z][a-z0-9_]*)['\"]\s*,\s*['\"]([a-z][a-z0-9_]*)['\"]"
    r"(?:\s*,\s*['\"]([a-z][a-z0-9_]*)['\"])?")
KOTLIN_CODE = re.compile(r"\bDiag(?:Feature|Failure)\.code\(\s*\"([a-z][a-z0-9_]*)\"\s*\)"
                         r"|\bcode\s*=\s*\"([a-z][a-z0-9_]*)\"")


class MonitoringError(ValueError):
    pass


def require(condition, label, message):
    if not condition:
        raise MonitoringError(f"{label}: {message}")


def load_catalog(root):
    """Execute the data-only catalog file without importing the app package."""
    path = Path(root) / CATALOG
    spec = importlib.util.spec_from_file_location("_monitoring_catalog", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def is_learner_route(path):
    return (path.startswith("/api/") and not path.startswith("/api/admin")
            and not path.startswith("/api/v3/desktop")
            and path != "/api/internal/admin-pwa/analytics/refresh")


def _literal(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _router_prefixes(tree):
    """Names bound to ``APIRouter(prefix="...")`` anywhere in the module."""
    prefixes = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            name = call.func.attr if isinstance(call.func, ast.Attribute) else getattr(call.func, "id", "")
            if name != "APIRouter":
                continue
            prefix = next((_literal(k.value) for k in call.keywords if k.arg == "prefix"), "") or ""
            for target in node.targets:
                if isinstance(target, ast.Name):
                    prefixes[target.id] = prefix
    return prefixes


def routes_in_source(source, path):
    """{full route path: handler name} declared by HTTP/WebSocket decorators or route registration calls
    in one module, resolving ``APIRouter(prefix=...)``."""
    tree = ast.parse(source, filename=path)
    prefixes = _router_prefixes(tree)
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for deco in node.decorator_list:
                if (isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute)
                        and deco.func.attr in ROUTE_METHODS and deco.args):
                    route = _literal(deco.args[0])
                    owner = deco.func.value.id if isinstance(deco.func.value, ast.Name) else ""
                    if route is not None:
                        found.setdefault(prefixes.get(owner, "") + route, node.name)
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
              and node.func.attr in ROUTE_REGISTRARS and node.args):
            route = _literal(node.args[0])
            owner = node.func.value.id if isinstance(node.func.value, ast.Name) else ""
            handler = node.args[1].id if len(node.args) > 1 and isinstance(node.args[1], ast.Name) else ""
            if route is not None:
                found.setdefault(prefixes.get(owner, "") + route, handler)
    return found


def learner_routes(root, read_source=None):
    """{route path: (first declaring file, handler)} for every learner API route."""
    root = Path(root)
    result = {}
    for file in sorted((root / "app").rglob("*.py")):
        rel = file.relative_to(root).as_posix()
        source = read_source(rel) if read_source else file.read_text(encoding="utf-8")
        if not source or ("route" not in source and "app." not in source and "websocket" not in source):
            continue
        for route, handler in sorted(routes_in_source(source, rel).items()):
            if is_learner_route(route):
                result.setdefault(route, (rel, handler))
    return result


def android_packages(root):
    bases = (Path(root) / relative for relative in ANDROID_FEATURE_DIRS)
    return sorted({p.name for base in bases if base.is_dir() for p in base.iterdir() if p.is_dir()})


def pwa_pages(root):
    static = Path(root) / "app/static"
    return sorted({p.name for pattern in PAGE_PATTERNS for p in static.glob(pattern) if p.is_file()})


def reporter_literals(root):
    """{(kind, code): file} for codes the Android and web reporters emit."""
    root = Path(root)
    found = {}
    kotlin = root / KOTLIN_CATALOG
    if kotlin.is_file():
        for match in KOTLIN_CODE.finditer(kotlin.read_text(encoding="utf-8")):
            code = match.group(1) or match.group(2)
            found.setdefault(("code", code), KOTLIN_CATALOG)
    for file in sorted((root / "app/static").rglob("*")):
        if file.suffix not in {".js", ".html"} or not file.is_file():
            continue
        rel = file.relative_to(root).as_posix()
        for feature, failure, site in JS_REPORTER_CALL.findall(file.read_text(encoding="utf-8", errors="ignore")):
            found.setdefault(("feature", feature), rel)
            found.setdefault(("failure", failure), rel)
            if site:
                found.setdefault(("site", site), rel)
    return found


def inbox_declares_diagnostic(root):
    path = Path(root) / INBOX_MODULE
    return path.is_file() and re.search(r"['\"]diagnostic['\"]", path.read_text(encoding="utf-8")) is not None


def _exact_file(root, value, label):
    require(isinstance(value, str) and value and ".." not in value.split("/")
            and (Path(root) / value).is_file(), label, f"expected an existing file, got {value!r}")


def _critical_source(path):
    return (isinstance(path, str) and SOURCE_FILE.fullmatch(path)
            and not {".", ".."} & set(path.split("/"))
            and ((path.startswith("app/") and path.endswith(".py"))
                 or (path.startswith("app/static/") and path.endswith(".js"))
                 or (path.startswith(tuple(f"{ANDROID_SOURCE_DIR}/{flavor}/java/"
                                           for flavor in ("main", "direct", "play")))
                     and path.endswith((".kt", ".java")))))


def source_digest(text):
    return sha256(text.encode("utf-8")).hexdigest()


def _client_test_ok(root, reference, label, workflow_text, android_ci_text):
    require(isinstance(reference, str) and reference, label, "covered requires a client_test")
    path = reference.split("::", 1)[0]
    _exact_file(root, path, label)
    if path.startswith("android/"):
        require(path.startswith("android/app/src/test/") and path.endswith(".kt"), label,
                "Android client test must be a Kotlin test in android/app/src/test/")
        require(any("testPlayDebugUnitTest" in line and "testDirectDebugUnitTest" in line
                    for line in re.findall(r"(?m)^\s*run:\s*[^\n]*gradlew[^\n]*", android_ci_text)), label,
                "Android client tests must run for Play and Direct in android-ci.yml")
    elif path.endswith(".js"):
        require(f"node {path}" in workflow_text, label, f"client test is not run by the workflow: {path}")
    else:
        require(path in workflow_text, label, f"client test is not run by the workflow: {path}")


def _chain_test_ok(root, reference, label, *, platform, feature, failures, ci_modules, validate_chain):
    """Reuse the Analytics static chain proof with the Inbox route, then
    require the shared helper call with this entry's literals."""
    try:
        validate_chain(root, reference, label, platform=platform, subjects=failures,
                       ci_modules=ci_modules, admin_route=ADMIN_INBOX_ROUTE)
    except ValueError as exc:  # the Analytics CoverageError, reported as a monitoring failure
        raise MonitoringError(str(exc)) from exc
    path, symbol = reference.split("::", 1)
    tree = ast.parse((Path(root) / path).read_text(encoding="utf-8"), filename=path)
    literals = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    calls = {n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", "")
             for n in ast.walk(tree) if isinstance(n, ast.Call)}
    require(CHAIN_HELPER in calls, label, f"chain test must call {CHAIN_HELPER}: {reference}")
    require(INTAKE_ROUTES[platform] in literals or platform == "server", label,
            f"chain test must use the {platform} intake {INTAKE_ROUTES[platform]}: {reference}")
    require(feature in literals, label, f"chain test must name feature {feature!r}: {reference}")


def _validate_analytics_boundary(root, catalog, analytics_events):
    overlap = set(catalog.FAILURES) & set(analytics_events)
    require(not overlap, "monitoring", f"diagnostic codes used as Analytics events: {sorted(overlap)}")
    root = Path(root)
    paths = [*(root / "app/services/monitoring").rglob("*.py"), root / "app/api/monitoring_intake.py"]
    writer_names = {"record_client_event", "record_server_event", "ConversionFunnelService",
                    "CourseMiniAppAnalyticsService", "ConversionFunnelEvent", "CourseMiniAppEvent"}
    writer_modules = {"conversion_funnel_service", "course_miniapp_analytics_service",
                      "conversion_funnel_event", "course_miniapp_event"}
    for path in sorted(paths):
        if not path.is_file():
            continue
        label = path.relative_to(root).as_posix()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=label)):
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, ast.Attribute):
                name = node.attr
            elif isinstance(node, ast.alias):
                name = node.name
            elif isinstance(node, ast.ImportFrom):
                name = node.module or ""
            else:
                continue
            symbol = name.rsplit(".", 1)[-1]
            require(symbol not in writer_names | writer_modules, label,
                    f"monitoring must not use Analytics writer or store {symbol!r}")


def validate_monitoring(block, root, *, flow_ids, critical_paths, ci_modules, validate_chain,
                        workflow_text="", android_ci_text="", analytics_events=()):
    """Schema, source inventory and evidence checks. Returns a summary dict."""
    label = "monitoring"
    require(isinstance(block, dict), label, "expected an object")
    allowed = {"mode", "features", "android_packages", "pwa_pages", "critical_paths",
               "legacy_baseline", "exemptions"}
    require(set(block) == allowed, label, f"fields must be exactly {sorted(allowed)}")
    require(block["mode"] in MODES, label, f"mode must be one of {MODES}")
    catalog = load_catalog(root)
    _validate_analytics_boundary(root, catalog, analytics_events)
    monitoring_only = set(catalog.MONITORING_ONLY_FEATURES)
    require(not monitoring_only & set(flow_ids), "catalog",
            "a monitoring-only feature ID duplicates an Analytics flow ID")
    valid_features = set(flow_ids) | monitoring_only
    require(set(catalog.FEATURES) <= valid_features, "catalog",
            f"unknown feature IDs {sorted(set(catalog.FEATURES) - valid_features)}")

    features = {}
    for row in block["features"]:
        require(isinstance(row, dict) and set(row) == {"id", "platforms"}, label, "feature needs id and platforms")
        fid = row["id"]
        require(fid in valid_features, f"monitoring feature {fid!r}",
                "must be an Analytics flow ID or a catalog monitoring-only ID")
        require(fid in catalog.FEATURES, f"monitoring feature {fid!r}", "is missing from the catalog")
        require(fid not in features, f"monitoring feature {fid!r}", "duplicate feature ID")
        require(isinstance(row["platforms"], dict) and set(row["platforms"]) == set(PLATFORMS),
                f"monitoring feature {fid}", f"platform keys must be exactly {PLATFORMS}")
        failures = tuple(sorted(catalog.FAILURES))
        for platform, cell in row["platforms"].items():
            scope = f"monitoring {fid}/{platform}"
            require(isinstance(cell, dict) and cell.get("status") in STATUSES, scope, "invalid status")
            keys = set(cell) - {"status"}
            require(keys <= {"reason", "reporter", "client_test", "chain_test"}, scope,
                    f"unknown fields {sorted(keys - {'reason', 'reporter', 'client_test', 'chain_test'})}")
            if cell["status"] == "covered":
                _exact_file(root, cell.get("reporter"), scope)
                if platform != "server":
                    _client_test_ok(root, cell.get("client_test"), scope, workflow_text, android_ci_text)
                _chain_test_ok(root, cell.get("chain_test"), scope, platform=platform, feature=fid,
                               failures=failures, ci_modules=ci_modules, validate_chain=validate_chain)
            else:
                require("chain_test" not in cell, scope, "only covered entries can name a chain test")
                require(isinstance(cell.get("reason"), str) and cell["reason"].strip(), scope,
                        "a non-empty reason is required")
        features[fid] = row["platforms"]

    mapped_packages = block["android_packages"]
    mapped_pages = block["pwa_pages"]
    for mapping, label2 in ((mapped_packages, "android_packages"), (mapped_pages, "pwa_pages")):
        require(isinstance(mapping, dict), label2, "expected an object")
        for key, fid in mapping.items():
            require(fid in features, f"{label2}/{key}", f"maps to unknown feature {fid!r}")

    baseline = block["legacy_baseline"]
    require(isinstance(baseline, list) and len(baseline) == len(set(baseline)), "legacy_baseline",
            "expected a list without duplicates")
    for pair in baseline:
        fid, _, platform = pair.partition(":")
        require(fid in features and platform in PLATFORMS, "legacy_baseline", f"invalid pair {pair!r}")

    sources = block["critical_paths"]
    require(isinstance(sources, dict), "monitoring critical_paths", "expected an object")
    for path, pairs in sources.items():
        scope = f"monitoring critical_paths/{path}"
        require(_critical_source(path) and (root / path).is_file()
                and (root / path).resolve().is_relative_to(root.resolve()),
                scope, "expected an exact existing production source file")
        require(isinstance(pairs, list) and pairs, scope, "expected non-empty feature:platform pairs")
        for pair in pairs:
            require(isinstance(pair, str), scope, "expected a feature:platform pair")
            fid, _, platform = pair.partition(":")
            require(fid in features and platform in PLATFORMS, scope, f"invalid pair {pair!r}")
        require(len(pairs) == len(set(pairs)), scope, "duplicate feature:platform pair")

    exemptions = block["exemptions"]
    require(isinstance(exemptions, list), "monitoring exemptions", "expected a list")
    exempt = set()
    for row in exemptions:
        require(isinstance(row, dict) and {"target", "reason"} <= set(row) <= {"target", "reason", "sha256"},
                "monitoring exemption", "needs target and reason, with sha256 for critical sources")
        target = row["target"]
        require(isinstance(row["reason"], str) and row["reason"].strip(), f"exemption {target!r}",
                "a non-empty reason is required")
        require(isinstance(target, str) and target and not target.endswith("/") and "*" not in target
                and (target.startswith("/api/") or target in catalog.FEATURES
                     or target.startswith("app/static/") or target.startswith(ANDROID_FEATURE_DIR)
                     or _critical_source(target)),
                f"exemption {target!r}", "must name one exact route, page, package, feature ID or source file")
        package_target = next((target[len(base) + 1:] for base in ANDROID_FEATURE_DIRS
                               if target.startswith(base + "/")), None)
        require(not (Path(root) / target).is_dir()
                or (package_target in mapped_packages and "/" not in package_target), f"exemption {target!r}",
                "a directory cannot be exempted unless it is one mapped Android feature package")
        require(target not in exempt, f"exemption {target!r}", "duplicate target")
        if target in sources or "sha256" in row:
            require(_critical_source(target) and isinstance(row.get("sha256"), str)
                    and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]), f"exemption {target!r}",
                    "critical source exemptions need the exact Git source SHA-256")
        exempt.add(target)

    # Source inventory: everything must be mapped.
    routes = learner_routes(root)
    errors = []
    for route, (file, handler) in sorted(routes.items()):
        if route in exempt:
            continue
        mapped = catalog.ROUTE_MAP.get(route)
        if mapped is None:
            errors.append(f"{file}: learner route {route} has no catalog ROUTE_MAP entry")
            continue
        fid = mapped[0]
        if fid not in features:
            errors.append(f"{file}: route {route} maps to {fid!r}, which has no monitoring entry")
        flows, symbols = critical_paths.get(file, (set(), set()))
        if symbols and handler not in symbols:
            flows = set()
        if flows and fid not in flows and fid not in monitoring_only:
            errors.append(f"{file}: route {route} maps to {fid!r}, but its Analytics critical path "
                          f"lists {sorted(flows)}")
    stale = sorted(set(catalog.ROUTE_MAP) - set(routes))
    errors.extend(f"stale ROUTE_MAP entry {route}" for route in stale)
    for package in android_packages(root):
        if package not in mapped_packages and f"{ANDROID_FEATURE_DIR}/{package}" not in exempt:
            errors.append(f"{ANDROID_FEATURE_DIR}/{package}: Android feature package has no monitoring mapping")
    for page in pwa_pages(root):
        if page not in mapped_pages and f"app/static/{page}" not in exempt:
            errors.append(f"app/static/{page}: learner page has no monitoring mapping")
    for (kind, code), file in sorted(reporter_literals(root).items()):
        known = (catalog.FEATURES if kind == "feature" else catalog.FAILURES if kind == "failure"
                 else catalog.ALL_SITES if kind == "site"
                 else set(catalog.FEATURES) | set(catalog.FAILURES) | set(catalog.ALL_SITES))
        if code not in known:
            errors.append(f"{file}: reporter code {code!r} is not in the server catalog")
    if inbox_declares_diagnostic(root) and block["mode"] != "require_covered":
        errors.append("monitoring: the diagnostic Inbox source exists, so mode must be require_covered")
    if errors:
        raise MonitoringError("\n".join(errors))
    return {"features": features, "routes": routes, "catalog": catalog}


def _cell_ok(cell, mode):
    status = cell.get("status")
    if status in ("covered", "not_applicable"):
        return True
    return mode == "declare" and status == "partial" and PENDING_CONSUMER in str(cell.get("reason", ""))


def _status_rank(status):
    return {"not_instrumented": 0, "partial": 1, "covered": 2, "not_applicable": 2}.get(status, -1)


def validate_monitoring_diff(block, previous_block, summary, previous_routes, previous_packages,
                             previous_pages, root, *, changed_routes=(), changed_packages=(),
                             changed_pages=(), critical_diffs=None):
    """New or changed surfaces need coverage; the baseline only shrinks."""
    if previous_block is None:
        previous_block = {}
    mode = block["mode"]
    catalog = summary["catalog"]
    features = summary["features"]
    exempt_now = {row["target"] for row in block["exemptions"]}
    critical_diffs = critical_diffs or {}
    prior_exemptions = {(row["target"], " ".join(row["reason"].split()), row.get("sha256"))
                        for row in previous_block.get("exemptions", [])}
    new_exemptions = {row["target"]: row.get("sha256") for row in block["exemptions"]
                      if (row["target"], " ".join(row["reason"].split()), row.get("sha256")) not in prior_exemptions}
    errors = []

    def check(target, fid, platform, where, *, changed=False, critical=False):
        if not critical and target in (new_exemptions if changed else exempt_now):
            return
        cell = features.get(fid, {}).get(platform, {})
        if not _cell_ok(cell, mode):
            kind = "changed" if changed else "new"
            errors.append(f"{where}: {kind} {target} maps to {fid}/{platform} with status "
                          f"{cell.get('status')!r}; it must be covered or not_applicable"
                          + (" (or partial with an 'Admin consumer pending' reason)" if mode == "declare" else ""))

    for route, (file, _handler) in sorted(summary["routes"].items()):
        if route not in catalog.ROUTE_MAP:
            continue
        if route not in previous_routes:
            check(route, catalog.ROUTE_MAP[route][0], "server", file)
        elif route in changed_routes:
            check(route, catalog.ROUTE_MAP[route][0], "server", file, changed=True)
    for package in android_packages(root):
        if package in block["android_packages"] and (package not in previous_packages or package in changed_packages):
            path = f"{ANDROID_FEATURE_DIR}/{package}"
            check(path, block["android_packages"][package], "android", path, changed=package in previous_packages)
    for page in pwa_pages(root):
        if page in block["pwa_pages"] and (page not in previous_pages or page in changed_pages):
            path = f"app/static/{page}"
            check(path, block["pwa_pages"][page], "iphone_pwa", path, changed=page in previous_pages)

    old_sources = previous_block.get("critical_paths", {})
    sources = block["critical_paths"]
    for path in sorted(old_sources.keys() | sources.keys()):
        before = set(old_sources.get(path, ()))
        after = set(sources.get(path, ()))
        removed = before - after
        exempt_source = path in critical_diffs and new_exemptions.get(path) == critical_diffs[path]
        if removed and ((root / path).exists() or not exempt_source):
            errors.append(f"{path}: removed critical monitoring bindings {', '.join(sorted(removed))}; "
                          "keep the bindings for an existing file, or review its deletion with an exact-file exemption")
        if path in critical_diffs and not exempt_source:
            for pair in sorted(before | after):
                fid, platform = pair.split(":")
                check(path, fid, platform, "monitoring critical source", changed=True, critical=True)

    old_baseline = set(previous_block.get("legacy_baseline", []))
    grown = sorted(set(block["legacy_baseline"]) - old_baseline) if previous_block else []
    for pair in grown:
        errors.append(f"legacy_baseline grew with {pair}; the baseline may only shrink")
    old_features = {row["id"]: row["platforms"] for row in previous_block.get("features", [])}
    for fid, platforms in features.items():
        for platform, cell in platforms.items():
            if (previous_block and fid not in old_features and not _cell_ok(cell, mode)):
                errors.append(f"monitoring {fid}:{platform}: a new feature needs coverage or a justified not_applicable entry")
            before = old_features.get(fid, {}).get(platform)
            if before and (_status_rank(cell["status"]) < _status_rank(before.get("status"))
                           or (before["status"] == "covered" and cell["status"] == "not_applicable")):
                target = f"{fid}:{platform}"
                if target not in new_exemptions and fid not in new_exemptions:
                    errors.append(f"monitoring {target}: status lowered from {before['status']} to "
                                  f"{cell['status']} without a reviewed exemption")
    if errors:
        raise MonitoringError("\n".join(errors))


def read_chain_proof(path):
    proven = set()
    file = Path(path)
    if file.is_file():
        for line in file.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split("|")
            if len(parts) == 3 and all(parts):
                proven.add(tuple(parts))
    return proven


def validate_chain_proof(block, proof_path, *, known_failures=None):
    """Every covered entry must have been proven by the shared helper in this run."""
    entries = read_chain_proof(proof_path)
    features = {row["id"] for row in block["features"]}
    invalid = sorted((p, f, c) for p, f, c in entries
                     if p not in PLATFORMS or f not in features
                     or (known_failures is not None and c not in known_failures))
    if invalid:
        raise MonitoringError(f"invalid runtime chain proof entries: {invalid}")
    proven = {(platform, feature) for platform, feature, _ in entries}
    missing = [f"{row['id']}/{platform}" for row in block["features"]
               for platform, cell in row["platforms"].items()
               if cell["status"] == "covered" and (platform, row["id"]) not in proven]
    if missing:
        raise MonitoringError("covered entries without a runtime chain proof in this CI run: "
                              + ", ".join(sorted(missing)))
    return len(proven)

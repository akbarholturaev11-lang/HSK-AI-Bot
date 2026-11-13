"""Monitoring section of the shared coverage check (design D10, task 1.1)."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import textwrap
import unittest

from scripts import check_analytics_coverage as checker
from scripts import monitoring_coverage as monitoring

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "docs/analytics/FEATURE_ANALYTICS_COVERAGE.json"
FEATURE_DIR = monitoring.ANDROID_FEATURE_DIR

CATALOG = '''
MONITORING_ONLY_FEATURES = {"app_shell": "shell", "monitoring": "self"}
FEATURES = frozenset({"lessons", "practice", "app_shell", "monitoring"})
FAILURES = {"api_5xx": ("high", "k"), "server_5xx": ("high", "k")}
ROUTE_MAP = %s
ALL_SITES = frozenset({"lesson_open"}) | frozenset(site for _, site in ROUTE_MAP.values())
'''

ROUTES = '''
from fastapi import APIRouter

def build(app):
    router = APIRouter(prefix="/api/v3/pwa/extra")

    @app.get("/api/v3/lesson/start")
    async def lesson_start():
        return {}

    @router.post("/save")
    async def extra_save():
        return {}

    @app.get("/api/admin/v1/secret")
    async def admin_only():
        return {}

    def ping():
        return {}

    app.add_api_route("/api/v3/ping", ping, methods=["GET"])
    return router
'''

ALL_ROUTES = {
    "/api/v3/lesson/start": ("lessons", "v3_lesson_start"),
    "/api/v3/pwa/extra/save": ("practice", "v3_pwa_extra_save"),
    "/api/v3/ping": ("app_shell", "v3_ping"),
}


def cell(status="not_instrumented", reason="planned"):
    return {"status": status, "reason": reason}


def block(**overrides):
    value = {
        "mode": "declare",
        "features": [
            {"id": fid, "platforms": {p: cell() for p in monitoring.PLATFORMS}}
            for fid in ("lessons", "practice", "app_shell", "monitoring")
        ],
        "android_packages": {"lesson": "lessons"},
        "pwa_pages": {"course-v3.html": "lessons"},
        "legacy_baseline": ["lessons:server"],
        "exemptions": [],
    }
    value.update(overrides)
    return value


class Fixture:
    """A minimal repository: catalog, one route module, one Android package,
    one learner page and the workflow."""

    def __init__(self, route_map=None, routes=ROUTES, workflow="tests/test_chain.py"):
        self._dir = TemporaryDirectory()
        self.root = Path(self._dir.name)
        self.write(monitoring.CATALOG, CATALOG % json.dumps(route_map if route_map is not None else ALL_ROUTES))
        self.write("app/api/sample.py", routes)
        self.write(f"{FEATURE_DIR}/lesson/LessonScreen.kt", "class LessonScreen")
        self.write("app/static/course-v3.html", "<html></html>")
        self.write(".github/workflows/analytics-integrity.yml", f"python -m pytest {workflow}\n")

    def write(self, path, text):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(textwrap.dedent(text), encoding="utf-8")

    def validate(self, value, critical_paths=None, analytics_events=()):
        return monitoring.validate_monitoring(
            value, self.root, flow_ids={"lessons", "practice"},
            critical_paths=critical_paths or {}, ci_modules=checker.ci_test_modules(self.root),
            validate_chain=checker.validate_chain,
            workflow_text=(self.root / ".github/workflows/analytics-integrity.yml").read_text(),
            android_ci_text="testPlayDebugUnitTest", analytics_events=analytics_events)

    def close(self):
        self._dir.cleanup()


class MonitoringCoverageTests(unittest.TestCase):
    def setUp(self):
        self.repo = Fixture()
        self.addCleanup(self.repo.close)

    def assertFails(self, needle, value=None, **kwargs):
        with self.assertRaises(monitoring.MonitoringError) as caught:
            self.repo.validate(value or block(), **kwargs)
        self.assertIn(needle, str(caught.exception))

    def test_real_registry_and_catalog_pass(self):
        registry = checker.validate_schema(checker.load_registry(REGISTRY_PATH.read_text(encoding="utf-8")))
        summary = checker.validate_monitoring(registry)
        self.assertEqual(registry["monitoring"]["mode"], "require_covered")
        self.assertGreater(len(summary["routes"]), 200)

    def test_monitoring_cannot_write_analytics_or_reuse_failure_codes_as_event_names(self):
        with self.assertRaisesRegex(monitoring.MonitoringError, "diagnostic codes used as Analytics events"):
            self.repo.validate(block(), analytics_events={"api_5xx"})
        self.repo.write("app/services/monitoring/adapter.py", """
            from app.services.conversion_funnel_service import ConversionFunnelService as Funnel
        """)
        with self.assertRaisesRegex(monitoring.MonitoringError, "Analytics writer or store"):
            self.repo.validate(block())

    def test_analytics_registry_without_monitoring_still_validates(self):
        registry = checker.load_registry(REGISTRY_PATH.read_text(encoding="utf-8"))
        registry.pop("monitoring")
        checker.validate_schema(registry)
        self.assertIsNone(checker.validate_monitoring(registry))

    def test_inventory_resolves_router_prefix_and_add_api_route(self):
        routes = monitoring.learner_routes(self.repo.root)
        self.assertEqual(set(routes), set(ALL_ROUTES))
        self.assertEqual(routes["/api/v3/pwa/extra/save"][0], "app/api/sample.py")
        self.repo.validate(block())

    def test_unmapped_route_names_route_and_file(self):
        for missing in ("/api/v3/pwa/extra/save", "/api/v3/ping", "/api/v3/lesson/start"):
            with self.subTest(route=missing):
                repo = Fixture({k: v for k, v in ALL_ROUTES.items() if k != missing})
                self.addCleanup(repo.close)
                with self.assertRaises(monitoring.MonitoringError) as caught:
                    repo.validate(block())
                self.assertIn(f"app/api/sample.py: learner route {missing}", str(caught.exception))

    def test_unmapped_android_package_and_page(self):
        self.repo.write(f"{FEATURE_DIR}/wallet/Wallet.kt", "class Wallet")
        self.assertFails(f"{FEATURE_DIR}/wallet")
        self.repo.write(f"{FEATURE_DIR}/wallet/Wallet.kt", "")
        value = block(android_packages={"lesson": "lessons", "wallet": "practice"})
        self.repo.write("app/static/course_v3_new.html", "<html></html>")
        self.assertFails("app/static/course_v3_new.html", value)

    def test_unknown_reporter_literal(self):
        self.repo.write("app/static/course_v3_data/x.js", "HskDiag.report('lessons', 'made_up', 'x')")
        self.assertFails("reporter code 'made_up' is not in the server catalog")

    def test_unknown_reporter_site(self):
        self.repo.write("app/static/course_v3_data/x.js", "HskDiag.report('lessons', 'api_5xx', 'made_up')")
        self.assertFails("reporter code 'made_up' is not in the server catalog")

    def test_route_mapped_against_its_analytics_critical_path(self):
        self.assertFails("its Analytics critical path lists ['lessons']",
                         critical_paths={"app/api/sample.py": ({"lessons"}, set())})

    def test_symbol_scoped_critical_path_only_guards_its_handlers(self):
        self.repo.validate(block(), critical_paths={"app/api/sample.py": ({"lessons"}, {"lesson_start"})})

    def test_directory_and_empty_reason_exemptions_fail(self):
        self.assertFails("a non-empty reason is required",
                         block(exemptions=[{"target": "/api/v3/ping", "reason": " "}]))
        self.assertFails("must name one exact route",
                         block(exemptions=[{"target": "app/api/", "reason": "everything"}]))
        self.assertFails("a directory cannot be exempted",
                         block(exemptions=[{"target": f"{FEATURE_DIR}/lesson", "reason": "x"}]))

    def test_duplicate_or_unknown_feature_id(self):
        value = block()
        value["features"].append(deepcopy(value["features"][0]))
        self.assertFails("duplicate feature ID", value)
        value = block()
        value["features"][0]["id"] = "lesson_flow"
        self.assertFails("must be an Analytics flow ID or a catalog monitoring-only ID", value)

    def test_status_without_reason_fails(self):
        value = block()
        value["features"][0]["platforms"]["server"] = {"status": "partial"}
        self.assertFails("a non-empty reason is required", value)

    def test_declare_mode_fails_once_the_inbox_source_exists(self):
        self.repo.write(monitoring.INBOX_MODULE, 'SOURCES = ("technical", "diagnostic")\n')
        self.assertFails("mode must be require_covered")
        self.repo.validate(block(mode="require_covered"))

    def _covered(self, chain_source, workflow="tests/test_chain.py"):
        self.repo.write(".github/workflows/analytics-integrity.yml",
                        f"python -m pytest {workflow}\n      node tests/test_reporter.js\n")
        self.repo.write("tests/test_chain.py", chain_source)
        self.repo.write("tests/test_reporter.js", "// client test")
        self.repo.write("app/static/hsk-diagnostics.js", "// reporter")
        value = block()
        value["features"][0]["platforms"]["iphone_pwa"] = {
            "status": "covered", "reporter": "app/static/hsk-diagnostics.js",
            "client_test": "tests/test_reporter.js", "chain_test": "tests/test_chain.py::test_chain"}
        return value

    GOOD_CHAIN = '''
        from tests.monitoring_chain import assert_monitoring_chain

        async def test_chain():
            await assert_monitoring_chain(platform="iphone_pwa", feature="lessons", failure="api_5xx",
                                          intake="/api/v3/pwa/diagnostics", inbox="/api/admin/v1/inbox/list")
    '''

    def test_covered_with_a_real_chain_passes(self):
        self.repo.validate(self._covered(self.GOOD_CHAIN))

    def test_covered_chain_outside_the_workflow_fails(self):
        self.assertFails("is not run by", self._covered(self.GOOD_CHAIN, workflow="tests/other.py"))

    def test_covered_chain_missing_literals_or_helper_fails(self):
        no_inbox = self.GOOD_CHAIN.replace("/api/admin/v1/inbox/list", "/api/admin/v1/other")
        self.assertFails("chain test must read /api/admin/v1/inbox/list", self._covered(no_inbox))
        no_helper = '''
            async def test_chain():
                assert ("iphone_pwa", "lessons", "api_5xx", "/api/v3/pwa/diagnostics",
                        "/api/admin/v1/inbox/list")
        '''
        self.assertFails("must call assert_monitoring_chain", self._covered(no_helper))

    def test_covered_without_runtime_proof_fails(self):
        value = self._covered(self.GOOD_CHAIN)
        proof = self.repo.root / "proof.txt"
        with self.assertRaises(monitoring.MonitoringError) as caught:
            monitoring.validate_chain_proof(value, proof)
        self.assertIn("lessons/iphone_pwa", str(caught.exception))
        proof.write_text("iphone_pwa|lessons|api_5xx\n", encoding="utf-8")
        self.assertEqual(monitoring.validate_chain_proof(value, proof), 1)


class MonitoringDiffTests(unittest.TestCase):
    def setUp(self):
        self.repo = Fixture()
        self.addCleanup(self.repo.close)

    def diff(self, value, previous, previous_routes=None, packages=("lesson",), pages=("course-v3.html",)):
        summary = self.repo.validate(value)
        monitoring.validate_monitoring_diff(value, previous, summary,
                                            set(previous_routes if previous_routes is not None else ALL_ROUTES),
                                            set(packages), set(pages), self.repo.root)

    def test_cosmetic_change_passes(self):
        self.diff(block(), block())

    def test_new_route_on_an_uncovered_feature_fails(self):
        with self.assertRaises(monitoring.MonitoringError) as caught:
            self.diff(block(), block(), previous_routes=set(ALL_ROUTES) - {"/api/v3/ping"})
        self.assertIn("/api/v3/ping maps to app_shell/server", str(caught.exception))

    def test_new_route_on_a_pending_partial_feature_passes_only_in_declare(self):
        value = block()
        value["features"][2]["platforms"]["server"] = cell("partial", "Admin consumer pending 3.1")
        previous = set(ALL_ROUTES) - {"/api/v3/ping"}
        self.diff(value, block(), previous_routes=previous)
        value["mode"] = "require_covered"
        with self.assertRaises(monitoring.MonitoringError):
            self.diff(value, block(), previous_routes=previous)

    def test_new_package_and_page_need_coverage(self):
        with self.assertRaises(monitoring.MonitoringError) as caught:
            self.diff(block(), block(), packages=(), pages=())
        self.assertIn(f"{FEATURE_DIR}/lesson", str(caught.exception))
        self.assertIn("app/static/course-v3.html", str(caught.exception))

    def test_baseline_growth_and_lowered_status_need_an_exemption(self):
        grown = block(legacy_baseline=["lessons:server", "practice:server"])
        with self.assertRaises(monitoring.MonitoringError) as caught:
            self.diff(grown, block())
        self.assertIn("legacy_baseline grew with practice:server", str(caught.exception))
        previous = block()
        previous["features"][1]["platforms"]["server"] = cell("partial", "Admin consumer pending 3.1")
        with self.assertRaises(monitoring.MonitoringError) as caught:
            self.diff(block(), previous)
        self.assertIn("status lowered from partial to not_instrumented", str(caught.exception))
        exempted = block(exemptions=[{"target": "practice", "reason": "Reporter removed with the old screen."}])
        self.diff(exempted, previous)

    def test_baseline_may_shrink(self):
        self.diff(block(legacy_baseline=[]), block())


if __name__ == "__main__":
    unittest.main()

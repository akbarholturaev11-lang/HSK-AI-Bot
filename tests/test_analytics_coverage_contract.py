"""Analytics registry checks and real PostgreSQL projection contract."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts import check_analytics_coverage as checker
from tests.test_admin_pwa_v10_regression import URL, capture, postgres_fixture

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "docs/analytics/FEATURE_ANALYTICS_COVERAGE.json"


def assert_projection_keys(registry, projections):
    """Compare every covered section/filter/period, including unavailable sections."""
    expected = {}
    for row in registry["metrics"]:
        for platform in row["filters"]:
            expected.setdefault((row["section"], platform), set()).add(row["key"])

    errors = []
    for (section, platform, period), response in sorted(projections.items()):
        if section == "experiments":
            continue
        metrics = response["metrics"]
        if metrics is not None and not isinstance(metrics, dict):
            errors.append(f"{section} ({platform}/{period}): metrics must be an object or null")
            continue
        actual_keys = set(metrics) if metrics is not None else set()
        declared_keys = expected.get((section, platform), set())
        for key in sorted(actual_keys - declared_keys):
            errors.append(f"{section}.{key} ({platform}/{period}): projection key missing from registry")
        for key in sorted(declared_keys - actual_keys):
            errors.append(f"{section}.{key} ({platform}/{period}): registered key missing from projection")
    if errors:
        raise AssertionError("\n".join(errors))


@unittest.skipUnless(URL, "set ANALYTICS_TEST_DATABASE_URL for the real PostgreSQL projection contract")
class AnalyticsProjectionCoverageTests(unittest.IsolatedAsyncioTestCase):
    async def test_projection_keys_match_registry_and_detect_a_missing_metric(self):
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        async with postgres_fixture(URL) as sessions:
            projections = await capture(sessions)
        assert_projection_keys(registry, projections)
        expected_states = {}
        for row in registry["metrics"]:
            if row["kind"] == "metric":
                expected_states.setdefault(row["section"], set()).add(row["key"])
        for (section, platform, period), projection in projections.items():
            self.assertEqual(set(projection.get("metric_states", {})), expected_states.get(section, set()),
                             (section, platform, period))

        # Keep the real projection and remove only a registry row; this exercises
        # the same contract which a newly added runtime projection key must pass.
        missing = {**registry, "metrics": [
            row for row in registry["metrics"]
            if (row["section"], row["key"]) != ("course", "voice_minutes")
        ]}
        self.assertEqual(len(missing["metrics"]), len(registry["metrics"]) - 1)
        with self.assertRaisesRegex(AssertionError, r"course\.voice_minutes \(overall/weekly\): projection key missing"):
            assert_projection_keys(missing, projections)


class AnalyticsCoverageGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = checker.load_registry(REGISTRY_PATH.read_text(encoding="utf-8"))

    def test_registered_events_match_source_inventory(self):
        checker.validate_schema(self.registry)
        checker.validate_events(self.registry, checker.inventory(checker.ROOT))

    def test_unmapped_new_event_names_exact_writer_path(self):
        path = "app/services/test_writer.py"
        event = ("course_miniapp_events", "new_progress_signal")
        with TemporaryDirectory() as directory:
            source = Path(directory) / path
            source.parent.mkdir(parents=True)
            source.write_text(
                "from app.db.models.course_miniapp_event import CourseMiniAppEvent as Event\n"
                "NEW_EVENT = 'new_progress_signal'\n"
                "row = Event(event_name=NEW_EVENT)\n",
                encoding="utf-8",
            )
            found = checker.inventory(Path(directory))
        self.assertEqual(found, {event: {path}})
        with self.assertRaisesRegex(checker.CoverageError, r"app/services/test_writer.py: unregistered event .*:new_progress_signal"):
            checker.validate_events({"flows": [], "exemptions": []}, found)

    def test_stale_store_qualified_event_fails(self):
        registry = deepcopy(self.registry)
        registry["flows"][0]["events"].append({
            "store": "conversion_funnel_events", "role": "declared", "names": ["unwritten_old_event"],
        })
        found = {name: set() for name in checker.registered_events(self.registry)}
        with self.assertRaisesRegex(checker.CoverageError, "stale registry event conversion_funnel_events:unwritten_old_event"):
            checker.validate_events(registry, found)

    def test_cosmetic_resources_require_no_new_telemetry(self):
        checker.validate_diff(self.registry, self.registry, {
            "app/static/admin-pwa/styles.css", "localization/ui/uz/course.json", "localization/README.md",
        }, {})

    def test_exemption_requires_a_reason(self):
        registry = {**self.registry, "exemptions": [{"path": "app/main.py", "reason": "  "}]}
        with self.assertRaisesRegex(checker.CoverageError, "non-empty reason"):
            checker.validate_schema(registry)

    def test_exemption_cannot_cover_a_directory(self):
        for path in ("app", "app/services/*", "app/services/"):
            with self.subTest(path=path):
                registry = {**self.registry, "exemptions": [{"path": path, "reason": "synthetic"}]}
                with self.assertRaisesRegex(checker.CoverageError, "exact existing file"):
                    checker.validate_schema(registry)

    def test_covered_requires_an_existing_named_chain_test(self):
        registry = deepcopy(self.registry)
        metric = next(row for row in registry["metrics"] if row["kind"] == "metric")
        metric["platforms"]["android"] = {
            "status": "covered",
            "chain_test": "tests/test_analytics_coverage_contract.py::test_nonexistent_chain",
        }
        with self.assertRaisesRegex(checker.CoverageError, "chain test not found"):
            checker.validate_schema(registry)

    def test_only_a_related_flow_change_or_fresh_exact_exemption_passes(self):
        registry = deepcopy(self.registry)
        mapping = registry["critical_paths"][0]
        path = mapping["path"]
        related = next(row for row in registry["flows"] if row["id"] in mapping["flows"])
        unrelated = next(row for row in registry["flows"] if row["id"] not in mapping["flows"])
        unrelated["description"] += " Unrelated change."
        with self.assertRaisesRegex(checker.CoverageError, "update a related flow"):
            checker.validate_diff(registry, self.registry, {path}, {})
        related["description"] += " Analytics impact: updated related behavior."
        checker.validate_diff(registry, self.registry, {path}, {})
        reviewed = {**self.registry, "exemptions": [{"path": path, "reason": "No change to recorded results."}]}
        checker.validate_diff(reviewed, self.registry, {path}, {})
        with self.assertRaisesRegex(checker.CoverageError, "reviewed exact-path exemption"):
            checker.validate_diff(reviewed, reviewed, {path}, {})

    def test_new_event_site_requires_a_matching_flow_even_outside_exact_paths(self):
        event, flow_id = next(iter(checker.registered_events(self.registry).items()))
        path = "app/services/test_writer.py"
        with self.assertRaisesRegex(checker.CoverageError, f"{event[0]}:{event[1]} changed"):
            checker.validate_diff(self.registry, self.registry, {path}, {path: {event}})
        registry = deepcopy(self.registry)
        next(row for row in registry["flows"] if row["id"] == flow_id)["description"] += " New event caller."
        checker.validate_diff(registry, self.registry, {path}, {path: {event}})

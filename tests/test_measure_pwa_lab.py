"""The PWA lab profile must stay production-like, or its numbers mislead.

A lab run without gzip once reported a 9.9 s LCP and a 3.5 s blank dictionary
that production never shows. These checks pin the delivery rules of
``scripts/measure_pwa_lab.py`` to what ``app/main.py`` and
``app/api/pwa_auth.py`` send. Standard library only, so the CI guard job can
run them without browser or backend dependencies.
"""
import gzip
import json
import re
import threading
import time
import unittest
import urllib.error
import urllib.request

from scripts import measure_pwa_lab as lab

BIG_TEXT = "x" * 4096


class _Fixture:
    """A tiny stand-in for the e2e fixture: one HTML page, assets and an API."""

    def serve(self, route):
        path = route.request.url.split("?")[0].rsplit(":", 1)[-1].split("/", 1)[-1]
        if path == "page":
            route.fulfill(content_type="text/html", body=(
                '<link href="https://cdnjs.cloudflare.com/ajax/libs/x.css">' + BIG_TEXT))
        elif path == "app.js":
            route.fulfill(content_type="application/javascript", body=BIG_TEXT)
        elif path == "tiny.js":
            route.fulfill(content_type="application/javascript", body="x=1")
        elif path == "assets/logo.png":
            route.fulfill(content_type="image/png", body=BIG_TEXT)
        elif path == "built":
            # A production page builder's own policy, with Starlette's lower-case keys.
            route.fulfill(content_type="text/html; charset=utf-8", body=BIG_TEXT,
                          headers={"cache-control": "no-store"})
        elif path == "api/v3/pwa/map":
            route.fulfill(json={"ok": True, "pad": BIG_TEXT})
        else:
            route.fulfill(status=204, body="")


def fetch(url, **headers):
    request = urllib.request.Request(url, headers={"Accept-Encoding": "gzip", **headers})
    try:
        with urllib.request.urlopen(request, timeout=10) as answer:
            return answer.status, dict(answer.headers), answer.read()
    except urllib.error.HTTPError as answer:
        with answer:  # a 304 arrives as HTTPError; close it like a response
            return answer.code, dict(answer.headers), answer.read()


class LabDeliveryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = lab.LabServer(_Fixture()).__enter__()
        cls.origin = cls.server.origin

    @classmethod
    def tearDownClass(cls):
        cls.server.__exit__(None, None, None)

    def test_html_is_gzip_revalidated_and_answers_304(self):
        status, headers, body = fetch(self.origin + "/page")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Encoding"], "gzip")
        self.assertEqual(headers["Cache-Control"], "private, no-cache")
        self.assertTrue(headers["ETag"].startswith('W/"'))
        page = gzip.decompress(body).decode()
        # The one third-party stylesheet is routed through the shaped link.
        self.assertIn('href="/__ext/cdnjs.cloudflare.com/ajax/libs/x.css"', page)
        status, _, body = fetch(self.origin + "/page", **{"If-None-Match": headers["ETag"]})
        self.assertEqual((status, body), (304, b""))

    def test_versioned_and_assets_files_are_immutable_and_gzip_like_starlette(self):
        for path in ("/app.js?v=20261122-abc", "/assets/logo.png"):
            status, headers, body = fetch(self.origin + path)
            self.assertEqual(status, 200, path)
            self.assertEqual(headers["Cache-Control"], lab.IMMUTABLE, path)
            # GZipMiddleware compresses every type, PNG included, from 1 KB.
            self.assertEqual(headers["Content-Encoding"], "gzip", path)
            self.assertEqual(len(gzip.decompress(body)), len(BIG_TEXT), path)
        _, headers, body = fetch(self.origin + "/tiny.js?v=1")
        self.assertNotIn("Content-Encoding", headers)
        self.assertEqual(body, b"x=1")

    def test_a_production_built_page_keeps_its_own_cache_policy(self):
        status, headers, body = fetch(self.origin + "/built")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertNotIn("ETag", headers)
        self.assertNotIn("Cache-Control", [k for k in headers if k != "cache-control"])
        self.assertEqual(gzip.decompress(body).decode(), BIG_TEXT)

    def test_api_answers_are_not_cached(self):
        _, headers, _ = fetch(self.origin + "/api/v3/pwa/map")
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_offline_word_scripts_use_the_production_alias(self):
        status, headers, body = fetch(self.origin + "/audio/words/client.js?v=1")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], lab.IMMUTABLE)
        self.assertEqual(gzip.decompress(body), lab.ALIASED_ASSETS["/audio/words/client.js"].read_bytes())

    def test_every_response_waits_for_the_profile_latency(self):
        started = time.monotonic()
        fetch(self.origin + "/tiny.js?v=2")
        self.assertGreaterEqual(time.monotonic() - started, lab.LATENCY_S)


class LinkTest(unittest.TestCase):
    def test_parallel_responses_share_one_link(self):
        link = lab.Link(bytes_per_s=200_000)

        class Sink:
            def write(self, data):
                pass

        data = b"x" * 20_000
        started = time.monotonic()
        threads = [threading.Thread(target=link.send, args=(Sink(), data)) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        # 40 KB at 200 KB/s: two parallel sends cannot finish faster than 0.2 s.
        self.assertGreaterEqual(time.monotonic() - started, 0.19)


class FlowFixtureTest(unittest.TestCase):
    """The task 1.2 actions drive the pages production serves, and say when they could not."""

    def test_lab_serves_the_files_the_production_routes_serve(self):
        source = (lab.ROOT / "app/api/pwa_auth.py").read_text(encoding="utf-8")

        def served_file(route):
            match = re.search(r'@router\.get\("' + re.escape(route) + r'"\)(.*?)(?=@router\.)', source, re.S)
            self.assertIsNotNone(match, route)
            return set(re.findall(r'"app/static/([A-Za-z0-9_.-]+\.html)"', match.group(1)))

        for kind, page in lab.PRACTICE_PAGES.items():
            self.assertEqual(served_file("/iphone-pwa/practice/" + kind), {page}, kind)
        for route, page in lab.ENTRY_FILES.items():
            self.assertIn(page, served_file(route), route)

    def test_every_practice_page_and_voice_has_a_ready_state(self):
        self.assertEqual(set(lab.PRACTICE_READY), set(lab.PRACTICE_PAGES))
        self.assertEqual(set(lab.PRACTICE_TILES), set(lab.PRACTICE_PAGES) - {"voice"})
        self.assertEqual({name for name, _, _ in lab.SESSION_STARTS.values()}, {"exam_start", "review_start"})
        self.assertEqual(set(lab.ENTRY_PAGES), {"login", "li_onboarding", "onboarding"})
        for path, _, _ in lab.ENTRY_PAGES.values():
            self.assertIn(path.split("?")[0], lab.ENTRY_FILES)

    def test_child_expressions_are_quoted_once(self):
        expr = "document.querySelector('button[onclick=\"go()\"]')"
        self.assertEqual(lab.child(expr), "lab.child(" + json.dumps(expr) + ")")

    def test_a_failed_action_is_unmeasured_not_passing(self):
        results = {}
        lab.measured(results, "ok", lambda: {"ready_ms": 5})

        def broken():
            raise TimeoutError("Timeout 30000ms exceeded.\nCall log: ...")

        lab.measured(results, "broken", broken)
        self.assertEqual(results["ok"], {"ready_ms": 5})
        self.assertEqual(results["broken"], {"unmeasured": "Timeout 30000ms exceeded."})

    def test_action_summary_uses_measured_runs_and_counts_the_rest(self):
        runs = [
            {"open": {"ready_ms": 900, "parent_only_ms": 880, "panda_ms": 870, "timed_out": False}},
            {"open": {"ready_ms": 700, "parent_only_ms": 690, "panda_ms": 0, "timed_out": False}},
            {"open": {"ready_ms": None, "parent_only_ms": 400, "panda_ms": 390, "timed_out": True}},
            {"open": {"unmeasured": "frame missing"}},
        ]
        summary = lab.summarise_actions(runs)["open"]
        self.assertEqual(summary["measured_runs"], 2)
        self.assertEqual(summary["of"], 4)
        self.assertEqual(summary["ready_ms"], 800)
        self.assertEqual(summary["parent_only_ms"], 785)
        self.assertEqual(summary["panda_seen_runs"], 1)
        self.assertEqual(summary["unmeasured"], ["frame missing", "timed out"])

    def test_an_action_that_never_ran_is_reported(self):
        summary = lab.summarise_actions([{"a": {"ready_ms": 10}}, {}])
        self.assertEqual(summary["a"]["unmeasured"], ["not run"])

    def test_session_starts_have_no_parent_only_interval(self):
        self.assertEqual(lab.drop_parent_only({"ready_ms": 3, "parent_only_ms": 0}), {"ready_ms": 3})

    def test_the_page_probe_times_actions_in_the_page(self):
        for name in ("lab.arm=", "lab.begin=", "lab.result=", "lab.child=", "lab.pandaShown="):
            self.assertIn(name, lab.PAGE_PROBE)
        # Ready is stamped one frame after the state, so the change is painted.
        self.assertIn("if(w.seen){w.ready=t-w.start", lab.PAGE_PROBE)


class HeaderCheckTest(unittest.TestCase):
    class _Response:
        def __init__(self, headers):
            self.headers = headers

    def test_refuses_a_run_without_production_headers(self):
        good_page = self._Response({"content-encoding": "gzip", "cache-control": "private, no-cache",
                                    "etag": 'W/"a"'})
        good_asset = self._Response({"cache-control": lab.IMMUTABLE})
        lab.check_production_headers(good_page, good_asset)
        with self.assertRaises(SystemExit):
            lab.check_production_headers(self._Response({"cache-control": "private, no-cache",
                                                         "etag": 'W/"a"'}), good_asset)
        with self.assertRaises(SystemExit):
            lab.check_production_headers(good_page, self._Response({"cache-control": "no-store"}))


if __name__ == "__main__":
    unittest.main()

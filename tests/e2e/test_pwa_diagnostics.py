"""Run the actual deferred learner reporter in Chromium and WebKit."""
import os
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
ORIGIN = "https://hsk.test"
ASSET = "/course_v3_data/hsk-diagnostics.js"
HTML = f'<script defer src="{ASSET}?v=20261113-0123456789ab"></script>'
REPORTER = (Path("app/static") / ASSET.lstrip("/")).read_text(encoding="utf-8")


@pytest.fixture()
def diagnostic_page():
    actor, posts, decision = {"user_id": 1}, [], {"status": 200}
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get("PWA_E2E_ENGINE", "chromium")).launch()
        try:
            context = browser.new_context(viewport={"width": 390, "height": 844})

            def session(route):
                user_id = actor["user_id"]
                route.fulfill(json={"ok": True, "user_id": user_id, "csrf": f"fixture-csrf-{user_id}"})

            def post(route):
                posts.append((route.request.headers["x-hsk-pwa-csrf"], route.request.post_data_json))
                route.fulfill(status=decision["status"], json={"accepted": 1})

            context.route(ORIGIN + "/api/v3/pwa-auth/session", session)
            context.route(ORIGIN + "/api/v3/pwa/diagnostics", post)
            context.route(ORIGIN + ASSET + "?*", lambda route: route.fulfill(
                body=REPORTER, content_type="application/javascript"))
            context.route(ORIGIN + "/iphone-pwa/course", lambda route: route.fulfill(
                body=HTML, content_type="text/html; charset=utf-8"))
            page = context.new_page()
            page.goto(ORIGIN + "/iphone-pwa/course")
            yield page, context, actor, posts, decision
        finally:
            browser.close()


def expect_report(page, trigger):
    with page.expect_response("**/api/v3/pwa/diagnostics"):
        page.evaluate(trigger)


def test_js_signals_and_offline_delivery(diagnostic_page):
    page, context, _, posts, _ = diagnostic_page
    page.evaluate("HskDiag.owner(1)")
    expect_report(page, """() => { setTimeout(() => { throw new TypeError('private-message'); }, 0); }""")
    assert posts[0][0] == "fixture-csrf-1"
    first = posts[0][1]["events"][0]
    assert (first["feature_code"], first["failure_code"], first["category"]) == ("lessons", "js_uncaught", "type")
    assert "private-message" not in str(posts)
    context.set_offline(True)
    page.wait_for_function("!navigator.onLine")
    page.evaluate("() => { Promise.reject(new RangeError('another-private-message')); }")
    queued = page.wait_for_function("""() => JSON.parse(localStorage.getItem('hsk-diag-v1')).events
        .find(entry => entry.event.failure_code === 'js_rejection')?.event.event_id""").json_value()
    assert len(posts) == 1
    with page.expect_response("**/api/v3/pwa/diagnostics"):
        context.set_offline(False)
    assert len(posts) == 2
    assert posts[1][1]["events"][0]["event_id"] == queued
    assert posts[1][1]["events"][0]["category"] == "range"
    assert "another-private-message" not in str(posts)


def test_switch_and_unauthorized_response_drop_only_that_owner(diagnostic_page):
    page, context, actor, posts, decision = diagnostic_page
    second = context.new_page()
    second.goto(ORIGIN + "/iphone-pwa/course")
    context.set_offline(True)
    page.wait_for_function("!navigator.onLine")
    page.evaluate("""() => {
        HskDiag.owner(1);
        HskDiag.report('lessons', 'load_failed', 'lesson_open', 502);
    }""")
    actor["user_id"] = 2
    second.evaluate("HskDiag.owner(2)")
    assert not page.evaluate("HskDiag.report('lessons', 'save_unconfirmed', 'lesson_complete', 502)")
    context.set_offline(False)
    second.wait_for_function("navigator.onLine")
    decision["status"] = 401
    expect_report(second, """() => {
        HskDiag.report('lessons', 'load_failed', 'progress', 502);
        HskDiag.flush();
    }""")
    second.wait_for_function("JSON.parse(localStorage.getItem('hsk-diag-v1')).events.length === 0")
    assert len(posts) == 1
    assert posts[0][0] == "fixture-csrf-2"
    assert [event["site_code"] for event in posts[0][1]["events"]] == ["progress"]


def test_reporter_does_not_bind_the_document_during_delivery(diagnostic_page):
    page, context, actor, posts, _ = diagnostic_page
    page.evaluate("""() => {
        setTimeout(() => { throw new Error('unverified document'); }, 0);
        HskDiag.flush();
    }""")
    second = context.new_page()
    second.goto(ORIGIN + "/iphone-pwa/course")
    actor["user_id"] = 2
    second.evaluate("HskDiag.owner(2)")
    assert not page.evaluate("HskDiag.owner(1)"), "a late response in the old document cannot replace the new owner"
    expect_report(second, """() => {
        HskDiag.report('lessons', 'load_failed', 'progress', 502);
        HskDiag.flush();
    }""")
    assert len(posts) == 1
    assert posts[0][0] == "fixture-csrf-2"
    assert [event["site_code"] for event in posts[0][1]["events"]] == ["progress"]


# --- Diagnostic precision (tasks 6.2/6.4): real engine errors and stacks ----
# Fixture bodies are served at allowlisted first-party URLs, so the expected
# line of each failure is known exactly; the reporter itself is the real file.
HANDOFF_JS = """window.fixtureThrow = function () {
  var state;
  return state.value;
};
window.fixtureReject = function () {
  return Promise.resolve().then(function inner() {
    return undefinedFixtureFunction();
  });
};
"""
GUIDE_JS = """window.fixtureOuter = function () {
  return window.fixtureThrow();
};
"""
VENDOR_JS = "window.vendorThrow=function(){var a;return a.b};"
FOREIGN_JS = "window.crossThrow=function(){setTimeout(function(){throw new TypeError('private-cross-origin')},0)};"
PRECISION_HTML = f"""<!doctype html><title>handoff</title>
<script defer src="{ASSET}?v=20261113-0123456789ab"></script>
<script src="/iphone-pwa-handoff.js?v=aaaaaaaaaaaa"></script>
<script src="/course_v3_data/li-onboarding-install.js?v=20261114-bbbbbbbbbbbb&token=private-query"></script>
<script src="/course_v3_data/vendor/html2canvas.min.js"></script>
<script src="https://cdn.other.test/widget.js"></script>
<script>
window.inlineThrow = function () {{ var gone = null; return gone.value; }};
window.addEventListener('error', function (event) {{
  window.__seen = {{ line: event.lineno, column: event.colno, hasError: !!event.error }};
}});
</script>"""
DEBUG_KEYS = ("error_name", "reason_code", "location", "frames")
# Nothing a page, URL, message or stack contains may leave the browser.
PRIVATE = ("private", "hsk.test", "http", "?v=", "token", "fixtureThrow", "fixtureOuter", "inner",
           "undefinedFixtureFunction", "state", "Cannot", "undefined is not", "Can't find", "not defined")


@pytest.fixture()
def precision_page():
    posts = []
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get("PWA_E2E_ENGINE", "chromium")).launch()
        try:
            context = browser.new_context(viewport={"width": 390, "height": 844})
            script = "application/javascript"

            def post(route):
                posts.append(route.request.post_data_json)
                route.fulfill(json={"accepted": 1})

            def serve(body):
                return lambda route: route.fulfill(body=body, content_type=script)

            context.route(ORIGIN + "/api/v3/pwa-auth/session", lambda route: route.fulfill(
                json={"ok": True, "user_id": 1, "csrf": "fixture-csrf-1"}))
            context.route(ORIGIN + "/api/v3/pwa/diagnostics", post)
            for path, body in ((ASSET + "?*", REPORTER), ("/iphone-pwa-handoff.js?*", HANDOFF_JS),
                               ("/course_v3_data/li-onboarding-install.js?*", GUIDE_JS),
                               ("/course_v3_data/vendor/html2canvas.min.js", VENDOR_JS)):
                context.route(ORIGIN + path, serve(body))
            context.route("https://cdn.other.test/widget.js", serve(FOREIGN_JS))
            context.route(ORIGIN + "/iphone-pwa/handoff", lambda route: route.fulfill(
                body=PRECISION_HTML, content_type="text/html; charset=utf-8"))
            page = context.new_page()
            page.goto(ORIGIN + "/iphone-pwa/handoff")
            page.evaluate("HskDiag.owner(1)")
            yield page, posts
        finally:
            browser.close()


def reported(page, posts, trigger):
    """Run one failure and return its wire event after the privacy checks."""
    expect_report(page, trigger)
    assert len(posts) == 1 and len(posts[0]["events"]) == 1
    wire = str(posts[0])
    queued = page.evaluate("localStorage.getItem('hsk-diag-v1')")
    for secret in PRIVATE:
        assert secret not in wire, secret
        assert secret not in queued, secret
    event = posts[0]["events"][0]
    assert (event["feature_code"], event["site_code"]) == ("distribution_handoff", "pwa_handoff")
    return event


def test_uncaught_error_reports_exact_first_party_file_line_and_column(precision_page):
    page, posts = precision_page
    event = reported(page, posts, "() => { setTimeout(() => window.fixtureOuter(), 0); }")
    seen = page.evaluate("window.__seen")
    assert seen["hasError"] and seen["line"] == 3
    assert (event["failure_code"], event["category"], event["error_name"], event["reason_code"]) == (
        "js_uncaught", "type", "TypeError", "null_access")
    # The browser's own ErrorEvent position, with the asset's content token.
    assert event["location"] == {"asset_id": "iphone_pwa_handoff", "line": 3, "column": seen["column"],
                                 "asset_version": "aaaaaaaaaaaa"}
    # The caller in a second first-party file; the test's own frame is not one.
    assert len(event["frames"]) == 1
    frame = event["frames"][0]
    assert (frame["asset_id"], frame["line"], frame["asset_version"]) == ("li_onboarding_install", 2, "bbbbbbbbbbbb")
    assert isinstance(frame["column"], int) and 1 <= frame["column"] <= len("  return window.fixtureThrow();")


def test_unhandled_rejection_takes_its_location_from_the_first_party_stack(precision_page):
    page, posts = precision_page
    event = reported(page, posts, "() => { window.fixtureReject(); }")
    assert (event["failure_code"], event["category"], event["error_name"], event["reason_code"]) == (
        "js_rejection", "reference", "ReferenceError", "not_defined")
    location = event["location"]
    assert (location["asset_id"], location["line"], location["asset_version"]) == (
        "iphone_pwa_handoff", 7, "aaaaaaaaaaaa")
    assert isinstance(location["column"], int) and 1 <= location["column"] <= len("    return undefinedFixtureFunction();")
    for frame in event.get("frames", []):
        assert frame["asset_id"] == "iphone_pwa_handoff"


@pytest.mark.parametrize("trigger, name, reason", [
    ("() => { setTimeout(() => window.inlineThrow(), 0); }", "TypeError", "null_access"),  # inline script
    ("() => { setTimeout(() => window.vendorThrow(), 0); }", "TypeError", "null_access"),  # vendored, minified
])
def test_inline_and_vendored_scripts_report_no_location(precision_page, trigger, name, reason):
    page, posts = precision_page
    event = reported(page, posts, trigger)
    assert page.evaluate("window.__seen.hasError")
    assert (event["failure_code"], event["error_name"], event["reason_code"]) == ("js_uncaught", name, reason)
    assert "location" not in event and "frames" not in event


def test_cross_origin_script_error_has_no_error_object_and_no_debug_fields(precision_page):
    page, posts = precision_page
    event = reported(page, posts, "() => { window.crossThrow(); }")
    seen = page.evaluate("window.__seen")
    assert not seen["hasError"] and seen["line"] == 0, "the engine hides a foreign script's error"
    assert (event["failure_code"], event["category"]) == ("js_uncaught", "other")
    assert [key for key in DEBUG_KEYS if key in event] == []

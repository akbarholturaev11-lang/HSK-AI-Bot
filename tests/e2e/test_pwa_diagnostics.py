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

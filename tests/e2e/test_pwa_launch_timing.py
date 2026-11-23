"""Task 1.4: the PWA course sends one launch-timing beacon after the course is ready.

Real course HTML with the static e2e routes, in Chromium or WebKit
(PWA_E2E_ENGINE). The beacon goes through the existing clog() to
/api/v3/clientlog; its keys are listed in
docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md ("Real-user launch beacon").

Playwright's WebKit does not expose a Blob beacon body to a route, so the body
is read where clog() hands it to sendBeacon, and the route counts what
actually reached the network.
"""
import json
import os

import pytest

from test_miniapp_smoke import (
    STATIC_ROOT, app_url, expect, json_response, mock_course_map, mock_telegram_ready,
    route_static_files,
)

pw = pytest.importorskip("playwright.sync_api")

KEYS = {"ua", "plat", "tgver", "page", "ttfb", "html_end", "fcp", "lcp", "cls",
        "slowest_event", "ready", "sw", "kb", "vp"}
TIMINGS = ("ttfb", "html_end", "fcp", "lcp", "slowest_event", "ready")
COURSE = "/iphone-pwa/course?lang=uz&tab=course"
RECORD_BEACONS = """(() => {
    const send = navigator.sendBeacon.bind(navigator);
    window.__beacons = [];
    navigator.sendBeacon = (url, data) => {
        if (String(url).includes('/api/v3/clientlog') && data instanceof Blob) {
            data.text().then(text => window.__beacons.push(JSON.parse(text)));
        }
        return send(url, data);
    };
})();"""
HIDE = """() => {
    Object.defineProperty(document, 'visibilityState', {configurable: true, get: () => 'hidden'});
    document.dispatchEvent(new Event('visibilitychange'));
    window.dispatchEvent(new PageTransitionEvent('pagehide', {persisted: true}));
}"""
SHOW = """() => {
    Object.defineProperty(document, 'visibilityState', {configurable: true, get: () => 'visible'});
    document.dispatchEvent(new Event('visibilitychange'));
}"""


def learner_map():
    data = json.loads((STATIC_ROOT / "course_v3_data/hsk1.json").read_text())
    data.update(authenticated=True, level="hsk1", user={
        "name": "Browser Learner", "language": "uz", "onboarding_completed": True,
    })
    return data


def open_page(playwright):
    browser = getattr(playwright, os.environ.get("PWA_E2E_ENGINE", "chromium")).launch()
    page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
    route_static_files(page)
    page.add_init_script(RECORD_BEACONS)
    sent = []

    def clientlog(route):
        sent.append(route.request.method)
        route.fulfill(json={"ok": True})

    page.route("**/api/v3/clientlog", clientlog)
    return browser, page, sent


@pytest.fixture()
def course():
    with pw.sync_playwright() as playwright:
        browser, page, sent = open_page(playwright)
        try:
            held = []
            answer = {"map": lambda route: json_response(
                route, learner_map(), headers={"X-HSK-PWA-User-ID": "1"})}
            page.route("**/api/v3/pwa/**", lambda route: json_response(route, {"ok": True}))
            page.route("**/api/v3/pwa-auth/session", lambda route: json_response(
                route, {"ok": True, "csrf": "fixture-csrf", "user_id": 1}))
            page.route("**/api/v3/pwa/map?*", lambda route: answer["map"](route))
            page.route("**/api/v3/pwa/ad?*", lambda route: json_response(
                route, {"ok": True, "ad": None, "placement": "screen_center"},
                headers={"X-HSK-PWA-User-ID": "1"}))
            page.route("**/iphone-pwa/course?*", lambda route: route.fulfill(
                content_type="text/html", body=(STATIC_ROOT / "course-v3.html").read_text()))
            yield page, sent, answer, held
        finally:
            browser.close()


def beacons(page, sent):
    """Every clientlog body clog() handed over; each one also reached the network."""
    page.wait_for_timeout(300)
    bodies = page.evaluate("window.__beacons")
    assert len(sent) == len(bodies) and set(sent) <= {"POST"}
    return bodies


def launches(page, sent):
    return [body for body in beacons(page, sent) if body.get("event") == "pwa_launch"]


def wait_course(page):
    expect(page.locator("#s-course .node[data-lesson-order]").first).to_be_attached(timeout=20000)


def test_one_beacon_after_the_course_is_ready_with_only_the_allowed_keys(course):
    page, sent, _, _ = course
    page.goto(app_url(COURSE))
    wait_course(page)
    assert launches(page, sent) == []  # not at ready itself: 10 s later, or when hidden
    page.wait_for_function(
        "window.__beacons.some(body => body.event === 'pwa_launch')", timeout=15000)
    found = launches(page, sent)
    assert len(found) == 1
    beacon = found[0]
    assert set(beacon) == {"event", "msg", "ctx"}
    assert set(beacon["ctx"]) == KEYS
    launch_type, html = beacon["msg"].split(" ")
    assert launch_type in {"cold", "warm", "na"}
    assert html in {"200", "304", "cache", "na"}
    ctx = beacon["ctx"]
    assert ctx["page"] == "/iphone-pwa/course"
    assert ctx["plat"] == "browser"
    assert ctx["tgver"] == ""
    assert ctx["sw"] == "0"  # the static e2e origin is not secure: no worker
    assert ctx["vp"] == "390"
    for key in TIMINGS:
        assert ctx[key] == "" or ctx[key].isdigit(), (key, ctx[key])
    assert int(ctx["ready"]) > 0
    assert ctx["fcp"].isdigit()
    assert ctx["cls"] == "" or float(ctx["cls"]) >= 0
    assert ctx["kb"] == "" or ctx["kb"].isdigit()
    # No account, text or token: no value carries the learner's name, the CSRF
    # token or the user id, and every value fits the endpoint's limit.
    flat = json.dumps(beacon)
    assert "Browser Learner" not in flat and "fixture-csrf" not in flat
    assert all(len(value) <= 220 for value in ctx.values())
    # Hiding the page, leaving it or returning to it sends nothing more.
    page.evaluate(HIDE)
    page.evaluate(SHOW)
    page.evaluate(HIDE)
    assert len(launches(page, sent)) == 1


def test_hiding_the_ready_course_sends_the_beacon_at_once(course):
    page, sent, _, _ = course
    page.goto(app_url(COURSE))
    wait_course(page)
    page.evaluate(HIDE)
    assert len(launches(page, sent)) == 1
    page.evaluate(SHOW)
    assert len(launches(page, sent)) == 1


def test_no_beacon_when_the_course_fails(course):
    page, sent, answer, _ = course
    answer["map"] = lambda route: route.fulfill(status=503, json={"ok": False})
    page.goto(app_url(COURSE))
    page.wait_for_timeout(1500)
    expect(page.locator("#s-course .node[data-lesson-order]")).to_have_count(0)
    page.evaluate(HIDE)
    assert launches(page, sent) == []


def test_no_beacon_when_the_page_was_hidden_before_the_course_was_ready(course):
    page, sent, answer, held = course
    answer["map"] = held.append
    page.goto(app_url(COURSE))
    for _ in range(100):
        if held:
            break
        page.wait_for_timeout(100)
    assert held, "the course map request never started"
    page.evaluate(HIDE)
    page.evaluate(SHOW)
    json_response(held[0], learner_map(), headers={"X-HSK-PWA-User-ID": "1"})
    wait_course(page)
    page.evaluate(HIDE)
    assert launches(page, sent) == []


def test_the_telegram_mini_app_never_sends_the_beacon():
    with pw.sync_playwright() as playwright:
        browser, page, sent = open_page(playwright)
        try:
            mock_telegram_ready(page)
            mock_course_map(page)
            page.add_init_script("localStorage.setItem('hsk_v3_onb', '1');")
            page.goto(app_url("/course-v3.html?lang=uz&level=hsk1"))
            wait_course(page)
            assert page.evaluate("pwaLaunchTiming") is None
            page.evaluate(HIDE)
            assert launches(page, sent) == []
        finally:
            browser.close()

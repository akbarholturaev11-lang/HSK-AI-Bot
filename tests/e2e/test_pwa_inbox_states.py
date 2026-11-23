"""Task 2.3: PWA Inbox loading and error states in a real browser.

Chromium or WebKit (PWA_E2E_ENGINE), real course HTML with the static e2e
routes. Both feeds are held, so the notice-shaped placeholder rows can be
measured, then released. The fixed anchors (title, Back, list) and the first
row's position stay within 8 px from placeholder to content. The behaviour
itself (pending, partial, retry, owner switch) is in tests/test_pwa_notices_ui.js.
"""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from tests.pwa_layout_geometry import assert_reserved_layout, capture_geometry
from test_miniapp_smoke import STATIC_ROOT, app_url, expect, json_response, route_static_files

pw = pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parents[2]
RETRY_UZ = json.loads((ROOT / "localization/ui/uz/course.json").read_text(encoding="utf-8"))[
    "messages"]["courseLoadError.btn"]
ERROR_UZ = json.loads((ROOT / "localization/ui/uz/course.json").read_text(encoding="utf-8"))[
    "messages"]["subscriptionPage.error"]
FIXED = {
    "title": "#hsk-pwa-notice-title",
    "back": "#hsk-pwa-notice-root .hsk-pwa-close",
    "list": "#hsk-pwa-notice-list",
}
FIRST_ROW = "#hsk-pwa-notice-list > :first-child"
SKELETON = "#hsk-pwa-notice-list .hsk-pwa-notice-row.is-skeleton"
NOTICE = "#hsk-pwa-notice-list .hsk-pwa-notice-row:not(.is-skeleton)"
NOTIFICATIONS = {"ok": True, "notifications": [
    {"id": i, "title": f"Eslatma {i}", "body": "Bugungi darsingiz sizni kutmoqda: 5 daqiqa yetadi.",
     "action": "course", "created_at": f"2026-11-2{i}T09:00:00+00:00"} for i in range(1, 4)]}
ACCOUNT = {"ok": True, "notices": [], "payment_reviews": [], "payment_action": None}


def learner_map():
    data = json.loads((STATIC_ROOT / "course_v3_data/hsk1.json").read_text())
    data.update(authenticated=True, level="hsk1", user={
        "name": "Browser Learner", "language": "uz", "onboarding_completed": True,
    })
    return data


def open_course(playwright, width, *, feeds, reduced_motion=False):
    browser = getattr(playwright, os.environ.get("PWA_E2E_ENGINE", "chromium")).launch()
    context = browser.new_context(viewport={"width": width, "height": 844},
                                  reduced_motion="reduce" if reduced_motion else "no-preference")
    page = context.new_page()
    route_static_files(page)
    page.route("**/api/v3/clientlog", lambda route: route.fulfill(json={"ok": True}))
    page.route("**/api/v3/pwa/**", lambda route: json_response(route, {"ok": True}))
    page.route("**/api/v3/pwa-auth/session", lambda route: json_response(
        route, {"ok": True, "csrf": "fixture-csrf", "user_id": 1}))
    page.route("**/api/v3/pwa/map?*", lambda route: json_response(
        route, learner_map(), headers={"X-HSK-PWA-User-ID": "1"}))
    page.route("**/api/v3/pwa/ad?*", lambda route: json_response(
        route, {"ok": True, "ad": None, "placement": "screen_center"},
        headers={"X-HSK-PWA-User-ID": "1"}))
    # The test's feed answers start with the inbox; earlier reads are answered.
    armed = []

    def feed(name):
        return lambda route: (feeds if armed else answer)(name, route)

    page.route("**/api/v3/pwa/notifications", feed("notifications"))
    page.route("**/api/v3/pwa/account-notices", feed("account-notices"))
    page.route("**/iphone-pwa/course?*", lambda route: route.fulfill(
        content_type="text/html", body=(STATIC_ROOT / "course-v3.html").read_text()))
    finished = []
    page.on("requestfinished", lambda request: finished.append(urlsplit(request.url).path))
    page.goto(app_url("/iphone-pwa/course?lang=uz&tab=course"))
    expect(page.locator("#s-course .node[data-lesson-order]").first).to_be_attached(timeout=20000)
    # The course's own payment check reads the account feed 1.9 s after load
    # and revalidates the session; let it finish so it shares nothing with the inbox.
    for _ in range(100):
        if "/api/v3/pwa/account-notices" in finished and "/api/v3/pwa-auth/session" in \
                finished[finished.index("/api/v3/pwa/account-notices"):]:
            break
        page.wait_for_timeout(100)
    else:
        raise AssertionError("the course payment check did not run")
    page.wait_for_timeout(100)
    armed.append(True)
    return browser, page


def answer(feed, route):
    json_response(route, NOTIFICATIONS if feed == "notifications" else ACCOUNT)


@pytest.mark.parametrize("width", [320, 390, 430])
def test_placeholder_rows_hold_the_notice_geometry(width):
    held = []
    with pw.sync_playwright() as playwright:
        browser, page = open_course(playwright, width, feeds=lambda feed, route: held.append((feed, route)))
        try:
            page.evaluate("() => { HskPwaInbox.open(); }")
            expect(page.locator(SKELETON)).to_have_count(3)
            for _ in range(50):
                if len(held) == 2:
                    break
                page.wait_for_timeout(100)
            assert sorted(feed for feed, _ in held) == ["account-notices", "notifications"]
            assert page.locator("#hsk-pwa-notice-list").get_attribute("aria-busy") == "true"
            assert page.locator("#hsk-pwa-notice-list .hsk-pwa-notice-empty").count() == 0, "no loading text"
            assert all(page.locator(SKELETON).nth(i).get_attribute("aria-hidden") == "true" for i in range(3))
            loading = capture_geometry(page, FIXED)
            first_loading = capture_geometry(page, {"row": FIRST_ROW})["row"]
            for feed, route in held:
                answer(feed, route)
            expect(page.locator(NOTICE)).to_have_count(3)
            expect(page.locator(SKELETON)).to_have_count(0)
            page.wait_for_timeout(300)  # the 200 ms fade
            assert page.locator("#hsk-pwa-notice-list").get_attribute("aria-busy") == "false"
            ready = capture_geometry(page, FIXED)
            first_ready = capture_geometry(page, {"row": FIRST_ROW})["row"]
            assert_reserved_layout(loading, ready)
            # Rows have content-sized heights; their slot (left edge, top, width) is fixed.
            for key in ("x", "y", "width"):
                assert abs(first_loading[key] - first_ready[key]) <= 8, (key, first_loading, first_ready)
            assert abs(first_loading["height"] - first_ready["height"]) <= 24, (first_loading, first_ready)
        finally:
            browser.close()


@pytest.mark.parametrize("reduced", [False, True])
def test_rows_fade_in_unless_reduced_motion(reduced):
    with pw.sync_playwright() as playwright:
        browser, page = open_course(playwright, 390, feeds=answer, reduced_motion=reduced)
        try:
            page.evaluate("() => { HskPwaInbox.open(); }")
            expect(page.locator(NOTICE)).to_have_count(3)
            name = page.locator(NOTICE).first.evaluate("row => getComputedStyle(row).animationName")
            assert name == ("none" if reduced else "hsk-pwa-notice-in")
            if not reduced:
                ink = page.locator("#hsk-pwa-notice-list").evaluate("""list => {
                    const row = document.createElement('div');
                    row.className = 'hsk-pwa-notice-row is-skeleton';
                    row.innerHTML = '<span class="pwa-layout-ink"></span>';
                    list.appendChild(row);
                    const name = getComputedStyle(row.firstChild).animationName;
                    row.remove();
                    return name;
                }""")
                assert ink == "hsk-pwa-layout-pulse", "placeholders pulse with the shared PWA skeleton wave"
        finally:
            browser.close()


def test_error_keeps_its_text_and_retries_in_place():
    failures = {"notifications": 1, "account-notices": 1}

    def feeds(feed, route):
        if failures[feed]:
            failures[feed] -= 1
            route.fulfill(status=503, json={"ok": False})
        else:
            answer(feed, route)

    with pw.sync_playwright() as playwright:
        browser, page = open_course(playwright, 390, feeds=feeds)
        try:
            page.evaluate("() => { HskPwaInbox.open(); }")
            error = page.locator("#hsk-pwa-notice-list .hsk-pwa-notice-error")
            expect(error).to_be_visible()
            expect(error.locator(".hsk-pwa-notice-empty")).to_have_text(ERROR_UZ)
            retry = error.locator("button[data-pwa-feed-retry]")
            expect(retry).to_have_text(RETRY_UZ)
            box = retry.bounding_box()
            assert box and box["y"] + box["height"] <= 844 and box["height"] >= 44, box
            retry.click()
            expect(page.locator(NOTICE)).to_have_count(3)
            expect(error).to_have_count(0)
            assert page.locator("#hsk-pwa-notice-root").is_visible(), "the retry stays inside the open inbox"
        finally:
            browser.close()

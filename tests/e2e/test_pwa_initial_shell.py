"""Chromium/WebKit: old response-injected skeleton must not duplicate main's native first paint.

This tests the actual unified course HTML with API requests stalled. Backend
cookie/session acceptance and data validation are tested separately.
"""
import os
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
HTML = Path("app/static/course-v3.html").read_text(encoding="utf-8")
ORIGIN = "https://hsk.test"


@pytest.mark.parametrize("pwa", [True, False])
def test_single_shell_before_any_api_and_telegram_remains_unchanged(pwa):
    engine = os.environ.get("PWA_E2E_ENGINE", "chromium")
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        try:
            page = browser.new_page(viewport={"width": 390, "height": 844})
            target = ORIGIN + ("/iphone-pwa/course" if pwa else "/course-v3.html")
            page.route("**/*", lambda route: route.fulfill(
                body="", content_type=(
                    "text/css" if route.request.url.split("?")[0].endswith(".css")
                    else "application/javascript"
                ),
            ))
            page.route("**/api/**", lambda route: None)
            page.route(target, lambda route: route.fulfill(
                body=HTML, content_type="text/html; charset=utf-8",
            ))
            page.goto(target, wait_until="domcontentloaded")
            assert page.locator(".hsk-pwa-boot-shell").count() == 0
            assert page.locator("#s-course .pwa-initial-shell").count() == (1 if pwa else 0)
            if pwa:
                assert page.locator("#s-course .pwa-initial-shell").is_visible()
                assert page.locator("#hsk-launch-splash").is_hidden()
                assert page.locator("#nav button").count() == 5
                assert page.locator("#s-profile .pwa-initial-shell").count() == 1
                assert page.locator("#s-rating .pwa-initial-shell").count() == 1
                assert "Pro" not in page.locator("#s-course").inner_text()
                logo = page.locator("#s-course .pwa-first-logo")
                assert logo.get_attribute("loading") == "eager"
                assert logo.get_attribute("fetchpriority") == "high"
            else:
                assert page.locator("#s-course .pwa-initial-shell").is_hidden()
                assert page.locator("#hsk-launch-splash").is_visible()
        finally:
            browser.close()


def test_unified_first_paint_preserves_server_auth_transport_boundaries():
    source = Path("app/api/pwa_auth.py").read_text(encoding="utf-8")
    assert "_add_pwa_course_initial_shell" not in source
    assert "_PWA_COURSE_SKELETON_OLD" not in source
    assert "def _pwa_inline_html" in source
    assert 'X-HSK-PWA-User-ID' in source
    assert "PWA_PREBOOT_TAB=s;" in HTML
    assert "function boundedSectionRequest(" in HTML
    assert 'if(PWA_COURSE_HOST&&!PROFILE_DETAIL&&!PROFILE_DETAIL_FAILED)' in HTML

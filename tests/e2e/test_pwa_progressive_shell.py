"""First-paint UX contract of PWA (and unchanged Mini App launch).

Uses the genuine HTML template and stalls all API responses. The visible
shell must be fully static; it cannot depend on authentication/Pro/map data.
"""
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")

HTML = Path("app/static/course-v3.html").read_text(encoding="utf-8")
ORIGIN = "https://hsk.test"


@pytest.mark.parametrize("pwa", [True, False])
def test_shell_renders_without_api_and_preserves_telegram_launch(pwa):
    with pw.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        # Exact source markup: no fake actor/session, no lesson JSON and no
        # cached Pro state. Resources are empty to test static resilience.
        target = ORIGIN + ("/iphone-pwa/course" if pwa else "/course-v3.html")
        page.route(target, lambda route: route.fulfill(
            body=HTML, content_type="text/html; charset=utf-8",
        ))
        page.route("**/*", lambda route: route.fulfill(
            body="", content_type=(
                "text/css" if route.request.url.split("?")[0].endswith(".css")
                else "application/javascript"
            ),
        ))
        page.goto(target, wait_until="domcontentloaded")
        page.locator("#s-course").wait_for(state="visible")
        if pwa:
            assert page.locator("#hsk-launch-splash").is_hidden()
            assert page.locator("#s-course .pwa-initial-shell").is_visible()
            assert page.locator("#nav").is_visible()
            assert page.locator("#nav button").count() == 5
            assert page.locator("#s-course .pwa-skel-card").count() == 2
            assert page.locator("#s-course .pwa-skel-node").count() == 3
            assert page.evaluate("""() => {
              const s=document.querySelector('#s-course .pwa-initial-shell');
              return s.getBoundingClientRect().height >= 500;
            }""")
            assert page.locator("#s-profile .pwa-initial-shell").count() == 1
            assert page.locator("#s-rating .pwa-initial-shell").count() == 1
            assert "Pro" not in page.locator("#s-course").inner_text()
        else:
            assert page.locator("#s-course .pwa-initial-shell").is_hidden()
            assert page.locator("#hsk-launch-splash").is_visible()
        browser.close()


def test_progressive_shell_does_not_claim_fake_user_data():
    # The static first paint must not seed XP, subscriptions, lesson statuses
    # or entitlement from localStorage or an unsourced dummy API response.
    assert 'class="pwa-initial-shell"' in HTML
    shell = HTML.split('<div class="scr on" id="s-course">', 1)[1].split(
        '<div class="scr" id="s-mashq">', 1
    )[0]
    assert "data-lesson" not in shell
    assert "PROF" not in shell
    assert "localStorage" not in shell
    assert "premium" not in shell

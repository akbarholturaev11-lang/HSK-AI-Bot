"""Ready phrases remain a static, client-side study tool in the Mini App."""

from pathlib import Path
from urllib.parse import urlparse

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright_api.sync_playwright

STATIC_ROOT = Path(__file__).resolve().parents[2] / "app" / "static"
BASE_URL = "http://hsk-ai.local"


def _serve_static(route):
    path = (STATIC_ROOT / urlparse(route.request.url).path.lstrip("/")).resolve()
    if not path.is_relative_to(STATIC_ROOT.resolve()) or not path.is_file():
        route.fulfill(status=404, content_type="text/plain", body="not found")
        return
    content_types = {
        ".css": "text/css",
        ".html": "text/html",
        ".js": "application/javascript",
        ".json": "application/json",
    }
    route.fulfill(
        status=200,
        content_type=content_types.get(path.suffix, "text/plain"),
        body=path.read_text(encoding="utf-8"),
    )


def test_practice_menu_phrasebook_search_and_favorites_are_local():
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Playwright Chromium is not installed: {exc}")

        page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        page.set_default_timeout(8000)
        api_requests = []
        page_errors = []
        page.on("request", lambda request: api_requests.append(request.url) if "/api/" in request.url else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.route(f"{BASE_URL}/**", _serve_static)
        page.route("https://**/*", lambda route: route.fulfill(status=200, body=""))

        try:
            page.goto(f"{BASE_URL}/course-v3.html", wait_until="domcontentloaded")
            assert page.evaluate("typeof renderMashq") == "function"
            page.evaluate("LANG='uz'; renderMashq()")
            row = page.locator("#m-ready-phrases")
            assert row.count() == 1
            # The Mashq tab is hidden until selected; invoke its rendered button
            # handler to exercise the same navigation without bootstrapping a user.
            row.evaluate("element => element.click()")

            page.locator(".phrase").first.wait_for()
            assert page.url.startswith(f"{BASE_URL}/hsk-gaplar.html")
            assert page.locator(".phrase").count() == 300

            page.locator("#query").fill("ni hao")
            assert "你好" in " ".join(page.locator(".hanzi").all_text_contents())
            page.locator("#query").fill("")
            page.locator(".phrase").first.locator("button.save").click()
            page.get_by_role("button", name="Saqlanganlar").click()
            assert page.locator(".phrase").count() == 1
            assert api_requests == []
            assert page_errors == []
        finally:
            browser.close()

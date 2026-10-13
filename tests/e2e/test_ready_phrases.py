"""Ready phrases remain a static, client-side study tool in the Mini App."""

import json
import re
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
        page.add_init_script("""
            Date.now = () => Date.parse('2026-10-14T12:00:00+08:00');
            const back = {
                visible: false,
                handler: null,
                show() { this.visible = true; },
                hide() { this.visible = false; },
                onClick(handler) { this.handler = handler; },
                offClick(handler) { if (this.handler === handler) this.handler = null; }
            };
            window.__hskBackButton = back;
            window.Telegram = { WebApp: { BackButton: back, initData: "test" } };
        """)
        page.set_default_timeout(8000)
        api_requests = []
        page_errors = []
        page.on("request", lambda request: api_requests.append(request.url) if "/api/" in request.url and request.frame.url.startswith(f"{BASE_URL}/hsk-gaplar.html") else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.route(f"{BASE_URL}/**", _serve_static)
        page.route("https://**/*", lambda route: route.fulfill(status=200, body=""))

        try:
            page.goto(f"{BASE_URL}/course-v3.html", wait_until="domcontentloaded")
            assert page.evaluate("typeof renderMashq") == "function"
            page.evaluate("LANG='uz'; renderMashq()")
            row = page.locator("#m-ready-phrases")
            assert row.count() == 1
            assert row.locator(".new-section-badge").inner_text() == "NEW"
            # The Mashq tab is hidden until selected; exercise the rendered row
            # handler, which opens the cached resource overlay without reloading.
            row.evaluate("element => element.click()")

            phrasebook = page.frame_locator("#resource-phrases iframe.resource-frame")
            phrasebook.locator(".phrase").first.wait_for()
            assert page.locator("#resourceov.on").count() == 1
            assert phrasebook.locator(".phrase").count() == 300
            # The phrasebook uses the same cinnabar accent as the main practice tab.
            assert phrasebook.locator(".pinyin").first.evaluate("el => getComputedStyle(el).color") == "rgb(178, 53, 48)"
            assert phrasebook.locator(".eyebrow").evaluate("el => getComputedStyle(el).color") == "rgb(178, 53, 48)"
            assert phrasebook.locator(".chip[aria-pressed='true']").first.evaluate("el => getComputedStyle(el).borderTopColor") == "rgb(224, 74, 64)"

            phrasebook.locator("#query").fill("ni hao")
            assert "你好" in " ".join(phrasebook.locator(".hanzi").all_text_contents())
            assert phrasebook.locator("#back").count() == 0
            assert phrasebook.locator("#intro").inner_text() == "Qidiring, saqlang, nusxalang."
            phrasebook.locator("#query").fill("")
            phrasebook.locator(".phrase").first.locator("button.save").click()
            phrasebook.get_by_role("button", name="Saqlanganlar").click()
            assert phrasebook.locator(".phrase").count() == 1
            assert page.evaluate("window.__hskBackButton.visible") is True
            assert page.evaluate("typeof window.__hskBackButton.handler") == "function"
            page.evaluate("window.__hskBackButton.handler()")
            page.wait_for_function("!document.getElementById('resourceov').classList.contains('on')")
            assert page.url.startswith(f"{BASE_URL}/course-v3.html")
            assert api_requests == []
            assert page_errors == []
        finally:
            browser.close()


def test_new_section_release_windows_match_on_android_and_mini_app():
    miniapp = (STATIC_ROOT / "course-v3.html").read_text(encoding="utf-8")
    android = (
        Path(__file__).resolve().parents[2]
        / "android/app/src/main/java/com/pomp/hskai/feature/practice/PracticeScreen.kt"
    ).read_text(encoding="utf-8")
    mini_registry = re.search(r"var NEW_SECTION_RELEASES=(\{[^;]+\});", miniapp)
    assert mini_registry is not None
    mini_releases = json.loads(mini_registry.group(1))

    android_ids = dict(re.findall(r'private const val ([A-Z0-9_]+_SECTION_ID) = "([^"]+)"', android))
    android_pairs = re.findall(r"([A-Z0-9_]+_SECTION_ID) to ([\d_]+)L", android)
    android_releases = {android_ids[key]: int(value.replace("_", "")) for key, value in android_pairs}
    assert mini_releases == android_releases


def test_practice_new_badge_expires_after_72_hours():
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Playwright Chromium is not installed: {exc}")

        page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        page.add_init_script("Date.now = () => Date.parse('2026-10-16T00:08:05+08:00')")
        page.route(f"{BASE_URL}/**", _serve_static)
        page.route("https://**/*", lambda route: route.fulfill(status=200, body=""))
        try:
            page.goto(f"{BASE_URL}/course-v3.html", wait_until="domcontentloaded")
            page.evaluate("LANG='uz'; renderMashq()")
            assert page.locator("#m-ready-phrases .new-section-badge").count() == 0
        finally:
            browser.close()


def test_phrasebook_loads_outside_telegram_with_shared_theme_tokens():
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Playwright Chromium is not installed: {exc}")

        page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.route(f"{BASE_URL}/**", _serve_static)
        try:
            page.goto(f"{BASE_URL}/hsk-gaplar.html?lang=uz&theme=dark", wait_until="domcontentloaded")
            page.locator(".phrase").first.wait_for()
            assert page.locator(".phrase").count() == 300
            assert page.locator("#back").count() == 0
            assert page.locator("body").evaluate("element => getComputedStyle(element).backgroundColor") == "rgb(0, 47, 73)"
            # Dark mode must use the dark-theme cinnabar tokens (cyan), not hardcoded red.
            assert page.locator(".pinyin").first.evaluate("el => getComputedStyle(el).color") == "rgb(126, 221, 246)"
            assert page.locator(".chip[aria-pressed='true']").first.evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(11, 76, 102)"
            assert page_errors == []
        finally:
            browser.close()

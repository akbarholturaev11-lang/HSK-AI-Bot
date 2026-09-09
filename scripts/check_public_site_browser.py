"""Browser smoke against the isolated local public-site preview (port 8765)."""
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from app.public_site.content import PAGES


def main():
    with sync_playwright() as p:
        kwargs = {"headless": True}
        if os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"):
            kwargs["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE"]
        browser = p.chromium.launch(**kwargs)
        page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        for width in (320, 390, 1440):
            page.set_viewport_size({"width": width, "height": 900})
            for path in PAGES:
                response = page.goto("http://127.0.0.1:8765" + path)
                page.wait_for_load_state("networkidle")
                assert response.status == 200
                assert page.locator("h1").is_visible()
                assert page.locator("a.cta").first.is_visible()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (width, path)
            if width == 390:
                page.goto("http://127.0.0.1:8765/tj/")
                Path("/tmp/hsk-seo").mkdir(exist_ok=True)
                page.screenshot(path="/tmp/hsk-seo/mobile.png", full_page=True)
        page.goto("http://127.0.0.1:8765/tj/?utm_source=bing&utm_campaign=hsk")
        page.locator('nav a[lang="ru"]').click()
        assert "utm_source=bing" in page.url
        assert "utm_campaign=hsk" in page.locator("a.cta").first.get_attribute("href")
        # Inspect the real local 302, then stop navigation before Telegram.
        redirects = []
        def intercept_cta(route):
            response = route.fetch(max_redirects=0)
            assert response.status == 302
            redirects.append(response.headers["location"])
            route.fulfill(status=200, content_type="text/html", body="CTA redirect checked")
        page.route("**/go/telegram?*", intercept_cta)
        page.locator("a.cta").first.click()
        page.wait_for_load_state("networkidle")
        assert redirects == ["https://t.me/darsi_chini_bot"]
        assert not errors, errors
        no_js = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
        source_page = no_js.new_page()
        source_page.goto("http://127.0.0.1:8765/tj/learn-chinese/")
        assert source_page.locator("h1").is_visible()
        assert source_page.get_by_text("Пинйинро ҳамчун роҳнамои садо истифода баред").is_visible()
        assert source_page.locator("a.cta").first.get_attribute("href").startswith("/go/telegram?")
        no_js.close()
        browser.close()
        print("PASS: 7 pages × 3 widths; no overflow/console errors; UTM navigation; CTA redirect; JavaScript disabled")


if __name__ == "__main__":
    main()

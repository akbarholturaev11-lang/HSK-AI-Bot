from __future__ import annotations

import json
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

import pytest

playwright = pytest.importorskip("playwright.sync_api")


STATIC_ROOT = Path(__file__).resolve().parents[2] / "app" / "static"


class _DownloadPageHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _send_bytes(
        self,
        body: bytes,
        *,
        content_type: str,
        disposition: str | None = None,
    ) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if disposition:
            self.send_header("Content-Disposition", disposition)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
        path = urlsplit(self.path).path
        if path == "/api/v3/desktop-download/public-status":
            origin = f"http://127.0.0.1:{self.server.server_port}"
            payload = {
                "ok": True,
                "enabled": True,
                "platforms": {"macos": True, "windows": True},
                "versions": {"macos": "1.3.0", "windows": "1.3.0"},
                "downloads": {
                    "macos": f"{origin}/downloads/macos",
                    "windows": f"{origin}/downloads/windows",
                },
            }
            self._send_bytes(
                json.dumps(payload).encode("utf-8"),
                content_type="application/json; charset=utf-8",
            )
            return
        if path == "/downloads/macos":
            self._send_bytes(
                b"test-dmg",
                content_type="application/x-apple-diskimage",
                disposition=(
                    'attachment; filename="Pomp-HSK-AI_1.3.0_universal.dmg"'
                ),
            )
            return
        if path == "/downloads/windows":
            self._send_bytes(
                b"test-exe",
                content_type="application/vnd.microsoft.portable-executable",
                disposition=(
                    'attachment; filename="Pomp-HSK-AI_1.3.0_x64-setup.exe"'
                ),
            )
            return
        if path == "/desktop-download":
            self.path = "/desktop-download.html"
        super().do_GET()


@pytest.fixture()
def desktop_download_url():
    handler = partial(_DownloadPageHandler, directory=str(STATIC_ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/desktop-download"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@pytest.fixture()
def browser():
    with playwright.sync_playwright() as session:
        instance = session.chromium.launch(headless=True)
        yield instance
        instance.close()


def _page(browser, **context_options):
    context = browser.new_context(**context_options)
    page = context.new_page()
    errors: list[str] = []
    page.on(
        "console",
        lambda message: errors.append(message.text)
        if message.type == "error"
        else None,
    )
    page.on("pageerror", lambda error: errors.append(str(error)))
    return context, page, errors


def _wait_until_download_ready(page) -> None:
    page.wait_for_function(
        "document.querySelector('[data-download-button]')?.getAttribute('aria-disabled') !== 'true'"
    )


def test_macos_download_keeps_default_action_and_opens_accessible_uz_guide(
    desktop_download_url,
    browser,
):
    context, page, errors = _page(browser)
    page.goto(
        f"{desktop_download_url}?platform=macos&lang=uz",
        wait_until="networkidle",
    )
    _wait_until_download_ready(page)

    download_button = page.locator("[data-download-button]")
    download_button.focus()
    with page.expect_download() as download_info:
        download_button.click()

    assert download_info.value.suggested_filename == (
        "Pomp-HSK-AI_1.3.0_universal.dmg"
    )
    dialog = page.get_by_role("dialog")
    playwright.expect(dialog).to_be_visible()
    assert dialog.get_attribute("data-platform") == "macos"
    assert dialog.get_by_role("heading", name="Yuklab bo‘lgach, shunday oching").count() == 1
    assert dialog.get_by_role("progressbar", name="Fayl yuklanmoqda").count() == 1
    assert dialog.get_by_role("button", name="Qo‘llanmani yopish").count() == 1
    assert "Applications" in dialog.inner_text()

    shots = dialog.locator(".quick-platform-macos .quick-step-shot img")
    assert shots.count() == 6
    for index in range(shots.count()):
        shot = shots.nth(index)
        assert shot.get_attribute("src").startswith("/assets/install/")
        assert shot.get_attribute("loading") == "lazy"
        assert (shot.get_attribute("alt") or "").strip() != ""
        assert shot.evaluate("node => node.naturalWidth") > 0

    page.keyboard.press("Escape")
    playwright.expect(dialog).to_be_hidden()
    playwright.expect(page.locator("body")).not_to_have_class(
        re.compile(r"(?:^|\s)quick-guide-open(?:\s|$)")
    )
    assert "quick-guide-open" not in page.locator("body").get_attribute("class")
    assert page.evaluate(
        "document.activeElement === document.querySelector('[data-download-button]')"
    )
    assert errors == []
    context.close()


def test_windows_guide_tracks_ru_and_tj_localisation(
    desktop_download_url,
    browser,
):
    context, page, errors = _page(browser)
    page.goto(
        f"{desktop_download_url}?platform=windows&lang=ru",
        wait_until="networkidle",
    )
    _wait_until_download_ready(page)

    with page.expect_download() as download_info:
        page.locator("[data-download-button]").click()
    assert download_info.value.suggested_filename == (
        "Pomp-HSK-AI_1.3.0_x64-setup.exe"
    )

    dialog = page.get_by_role("dialog")
    playwright.expect(dialog).to_be_visible()
    assert dialog.get_attribute("data-platform") == "windows"
    assert dialog.get_by_role("heading", name="После загрузки откройте так").count() == 1
    assert dialog.get_by_role("button", name="Закрыть инструкцию").count() == 1
    assert "SmartScreen" in dialog.inner_text()
    assert page.locator(".quick-platform-macos").first.evaluate(
        "node => getComputedStyle(node).display"
    ) == "none"
    page.get_by_role("button", name="Понятно").click()

    page.get_by_role("button", name="TJ", exact=True).click()
    assert page.locator("html").get_attribute("lang") == "tj"
    with page.expect_download():
        page.locator("[data-download-button]").click()
    playwright.expect(dialog).to_be_visible()
    assert dialog.get_by_role(
        "heading", name="Пас аз боргирӣ ҳамин тавр кушоед"
    ).count() == 1
    assert dialog.get_by_role("button", name="Пӯшидани дастур").count() == 1
    assert errors == []
    context.close()


def test_mobile_share_uses_public_platform_link_and_copy_fallback(
    desktop_download_url,
    browser,
):
    context, page, errors = _page(
        browser,
        viewport={"width": 390, "height": 844},
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
            "AppleWebKit/605.1.15 Mobile/15E148"
        ),
        has_touch=True,
    )
    page.add_init_script(
        """
        window.__sharePayload = null;
        window.__copiedValue = null;
        Object.defineProperty(navigator, "share", {
          configurable: true,
          value: async (payload) => { window.__sharePayload = payload; }
        });
        Object.defineProperty(navigator, "canShare", {
          configurable: true,
          value: () => true
        });
        Object.defineProperty(navigator, "clipboard", {
          configurable: true,
          value: {
            writeText: async (value) => { window.__copiedValue = value; }
          }
        });
        """
    )
    token = "a" * 32
    page.goto(
        f"{desktop_download_url}?platform=windows&lang=tj&request={token}",
        wait_until="networkidle",
    )
    _wait_until_download_ready(page)

    transfer = page.locator("[data-mobile-transfer]")
    playwright.expect(transfer).to_be_visible()
    assert f"request={token}" in page.locator("[data-download-button]").get_attribute(
        "href"
    )

    page.locator("[data-share-link]").click()
    page.wait_for_function("window.__sharePayload !== null")
    share_payload = page.evaluate("window.__sharePayload")
    assert share_payload["url"].endswith("/downloads/windows")
    assert "request=" not in share_payload["url"]
    assert page.locator("[data-transfer-status]").inner_text() == (
        "Равзанаи фиристодан кушода шуд"
    )

    page.evaluate(
        """
        Object.defineProperty(navigator, "canShare", {
          configurable: true,
          value: () => false
        });
        """
    )
    page.locator("[data-share-link]").click()
    page.wait_for_function("window.__copiedValue !== null")
    copied_value = page.evaluate("window.__copiedValue")
    assert copied_value.endswith("/downloads/windows")
    assert page.locator("[data-transfer-status]").inner_text() == "Нусха шуд"
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert errors == []
    context.close()

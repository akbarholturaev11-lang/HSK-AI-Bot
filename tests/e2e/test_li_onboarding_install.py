"""Li post-registration Home Screen guide: availability, platform and fallback.

This is a presentation-only view. It may never grant a PWA session,
start a Pro trial or request push permissions.
"""
from pathlib import Path
import os

import pytest

pw = pytest.importorskip("playwright.sync_api")
STATIC = Path("app/static")
JS = (STATIC / "course_v3_data/li-onboarding-install.js").read_text(encoding="utf-8")
CAT = (STATIC / "course_v3_data/hsk-li-onboarding-i18n.js").read_text(encoding="utf-8")
CSS = (STATIC / "course_v3_data/li-onboarding-install.css").read_text(encoding="utf-8")
IOS = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1"
ORIGIN = "https://hsk.test"


def _prepare(browser, *, ios=True, installed=False, has_video=False):
    page = browser.new_page(
        viewport={"width": 390, "height": 844},
        user_agent=IOS if ios else
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36",
    )
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    if installed:
        page.add_init_script(
            "Object.defineProperty(navigator,'standalone',{get:()=>true});"
        )
    page.route("**/course_v3_data/hsk-li-onboarding-i18n.js*", lambda route: route.fulfill(
        body=CAT, content_type="application/javascript"))
    page.route("**/course_v3_data/li-onboarding-install.js*", lambda route: route.fulfill(
        body=JS, content_type="application/javascript"))
    def video_response(route):
        if not has_video:
            route.fulfill(status=404, body="not available", content_type="text/plain")
            return
        # A fake 12-byte ftyp header is NOT a valid MP4. WebKit correctly
        # rejected that fixture. Test the committed optimized H.264 recording
        # and real Safari HTTP byte-range behaviour instead.
        video = (STATIC / "assets/onboarding/iphone-home-screen.mp4").read_bytes()
        header = route.request.headers.get("range", "")
        headers = {"Accept-Ranges": "bytes", "Content-Type": "video/mp4"}
        if header.startswith("bytes="):
            start_text, _, end_text = header[6:].partition("-")
            if start_text:
                start_byte = int(start_text)
                end_byte = min(len(video)-1, int(end_text) if end_text else len(video)-1)
            else:
                start_byte = max(0, len(video) - int(end_text))
                end_byte = len(video)-1
            if start_byte >= len(video) or end_byte < start_byte:
                route.fulfill(status=416, headers={
                    **headers, "Content-Range": f"bytes */{len(video)}"
                })
                return
            headers["Content-Range"] = f"bytes {start_byte}-{end_byte}/{len(video)}"
            route.fulfill(status=206, body=video[start_byte:end_byte + 1], headers=headers)
        else:
            route.fulfill(status=200, body=video, headers=headers)

    page.route("**/assets/onboarding/iphone-home-screen.mp4", video_response)
    html = (
        "<!doctype html><html lang='uz'><head><meta name='viewport' content='width=device-width'>"
        "<style>" + CSS + "</style></head>"
        "<body><main>Authenticated onboarding complete</main>"
        "<script src='/course_v3_data/hsk-li-onboarding-i18n.js'></script>"
        "<script src='/course_v3_data/li-onboarding-install.js'></script>"
        "</body></html>"
    )
    page.route(ORIGIN + "/iphone-pwa/onboarding/li", lambda route: route.fulfill(
        body=html, content_type="text/html; charset=utf-8"))
    page.goto(ORIGIN + "/iphone-pwa/onboarding/li")
    page.wait_for_function("window.HSKAILiInstallGuide && window.HSKAI_LI_I18N")
    return page, errors


def test_iphone_browser_after_verified_registration_shows_video_slot_and_fallback():
    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, errors = _prepare(browser)
        opened = page.evaluate("""() => {
          window.__next=0;
          return HSKAILiInstallGuide.open({userId:37,lang:"uz"},()=>window.__next++);
        }""")
        assert opened is True
        assert page.get_by_role("dialog").is_visible()
        assert page.locator(".li-install-steps li").count() == 4
        assert page.locator(".li-install-intro, .li-install-note, .li-install-continue").count() == 0
        assert page.locator(".li-install-card").evaluate(
            "(node) => Math.abs(node.getBoundingClientRect().height - innerHeight) < 2")
        page.locator(".li-install-video-fallback").wait_for(state="visible")
        assert page.locator(".li-install-video").is_hidden()
        # A missing / slow MP4 displays a readable text fallback from the
        # first frame instead of an empty grey video while Safari waits.
        assert page.locator(".li-install-media").evaluate(
            "(node) => node.classList.contains('is-fallback')") is True
        assert "aspect-ratio:9/16" in CSS
        assert page.get_by_role("dialog").get_attribute("aria-modal") == "true"
        page.locator(".li-install-close").click()
        assert page.evaluate("window.__next") == 1
        assert page.get_by_role("dialog").count() == 0
        assert page.evaluate("localStorage.getItem('hskai_li_install_guide_v1:37')") == "seen"
        assert page.evaluate("""() => HSKAILiInstallGuide.open(
            {userId:37,lang:"ru"},()=>window.__next++)""") is False
        assert not errors
        browser.close()


@pytest.mark.parametrize("ios,installed,expect", [
    (False, False, False),
    (True, True, False),
    (True, False, True),
])
def test_install_prompt_is_exclusive_to_not_yet_installed_ios_pwa(ios, installed, expect):
    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, errors = _prepare(browser, ios=ios, installed=installed)
        opened = page.evaluate("""() => HSKAILiInstallGuide.open(
            {userId:41,lang:"ru"},()=>{})""")
        assert opened is expect
        assert page.get_by_role("dialog").count() == int(expect)
        assert not errors
        browser.close()


def test_media_stays_optional_but_real_metadata_can_swap_to_vertical_video():
    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, errors = _prepare(browser, ios=True, has_video=True)
        assert page.evaluate("""() => HSKAILiInstallGuide.open(
          {userId:53,lang:"tj"},()=>{})""") is True
        # Browser player is hidden until the real MP4 decoder accepts
        # metadata. The fallback is usable during any download delay.
        assert page.locator(".li-install-video-fallback").is_visible()
        # Actual playable MP4, not a synthetic loadedmetadata event.
        page.locator(".li-install-video").wait_for(state="visible", timeout=15000)
        assert page.locator(".li-install-video").evaluate(
            "(video) => video.readyState >= HTMLMediaElement.HAVE_METADATA")
        assert page.locator(".li-install-video-fallback").is_hidden()
        page.locator(".li-install-close").click()
        assert page.get_by_role("dialog").count() == 0
        assert not errors
        browser.close()


def test_telegram_in_app_browser_shows_safari_link_not_video():
    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, errors = _prepare(browser, ios=True)
        assert page.evaluate("""() => {
          window.Telegram={WebApp:{initData:"real-verified-placeholder"}};
          return HSKAILiInstallGuide.open({userId:53,lang:"ru"},()=>{});
        }""") is True
        assert page.locator(".li-install-panda").is_visible()
        assert page.locator(".li-install-browser-link").get_attribute("href") == "https://hskai.app/iphone-pwa"
        assert page.locator(".li-install-video, .li-install-steps, .li-install-title").count() == 0
        assert not errors
        browser.close()


def test_chrome_on_ios_is_not_mistaken_for_safari():
    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, errors = _prepare(browser)
        page.add_init_script("""Object.defineProperty(navigator, 'userAgent', {
          get:()=> 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/130.0.0.0 Mobile/15E148 Safari/604.1'
        });""")
        page.reload()
        assert page.evaluate("""() => HSKAILiInstallGuide.open(
            {userId:54,lang:"uz"},()=>{})""") is True
        assert page.locator(".li-install-panda").is_visible()
        assert page.locator(".li-install-video").count() == 0
        assert page.locator(".li-install-browser-hint").inner_text().count("Safari") == 1
        assert not errors
        browser.close()


def test_install_guide_never_opens_without_verified_account_id():
    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, _ = _prepare(browser)
        for value in (None, -1, 0, "guest", 1.5):
            assert page.evaluate("""v => HSKAILiInstallGuide.open(
                {userId:v,lang:"tj"},()=>{})""", value) is False
        assert page.get_by_role("dialog").count() == 0
        browser.close()

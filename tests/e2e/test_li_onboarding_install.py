"""Li post-registration Home Screen guide: availability, platform and fallback.

This is a presentation-only view. It may never grant a PWA session,
start a Pro trial or request push permissions.
"""
from pathlib import Path

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
    page.route("**/assets/onboarding/iphone-home-screen.mp4", lambda route: route.fulfill(
        status=206 if has_video else 404,
        body=b"\0\0\0\x18ftypmp42" if has_video else "not available",
        content_type="video/mp4" if has_video else "application/json"))
    html = (
        "<!doctype html><html lang='uz'><head><meta name='viewport' content='width=device-width'></head>"
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
        browser = p.chromium.launch()
        page, errors = _prepare(browser)
        opened = page.evaluate("""() => {
          window.__next=0;
          return HSKAILiInstallGuide.open({userId:37,lang:"uz"},()=>window.__next++);
        }""")
        assert opened is True
        assert page.get_by_role("dialog").is_visible()
        assert page.locator(".li-install-steps li").count() == 3
        page.locator(".li-install-video-fallback").wait_for(state="visible")
        assert page.locator(".li-install-video").is_hidden()
        # A missing / slow MP4 displays a readable text fallback from the
        # first frame instead of an empty grey video while Safari waits.
        assert page.locator(".li-install-media").evaluate(
            "(node) => node.classList.contains('is-fallback')") is True
        assert "aspect-ratio:9/16" in CSS
        assert page.get_by_role("dialog").get_attribute("aria-modal") == "true"
        page.locator(".li-install-continue").click()
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
        browser = p.chromium.launch()
        page, errors = _prepare(browser, ios=ios, installed=installed)
        opened = page.evaluate("""() => HSKAILiInstallGuide.open(
            {userId:41,lang:"ru"},()=>{})""")
        assert opened is expect
        assert page.get_by_role("dialog").count() == int(expect)
        assert not errors
        browser.close()


def test_media_stays_optional_but_real_metadata_can_swap_to_vertical_video():
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        page, errors = _prepare(browser, ios=True, has_video=True)
        assert page.evaluate("""() => HSKAILiInstallGuide.open(
          {userId:53,lang:"tj"},()=>{})""") is True
        # Browser player is hidden until the real MP4 decoder accepts
        # metadata. The fallback is usable during any download delay.
        assert page.locator(".li-install-video-fallback").is_visible()
        page.locator(".li-install-video").evaluate(
            "(video) => video.dispatchEvent(new Event('loadedmetadata'))")
        assert page.locator(".li-install-video").is_visible()
        assert page.locator(".li-install-video-fallback").is_hidden()
        page.locator(".li-install-close").click()
        assert page.get_by_role("dialog").count() == 0
        assert not errors
        browser.close()


def test_telegram_in_app_browser_cannot_show_pwa_install_prompt():
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        page, errors = _prepare(browser, ios=True)
        assert page.evaluate("""() => {
          window.Telegram={WebApp:{initData:"real-verified-placeholder"}};
          return HSKAILiInstallGuide.open({userId:53,lang:"ru"},()=>{});
        }""") is False
        assert page.get_by_role("dialog").count() == 0
        assert not errors
        browser.close()


def test_install_guide_never_opens_without_verified_account_id():
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        page, _ = _prepare(browser)
        for value in (None, -1, 0, "guest", 1.5):
            assert page.evaluate("""v => HSKAILiInstallGuide.open(
                {userId:v,lang:"tj"},()=>{})""", value) is False
        assert page.get_by_role("dialog").count() == 0
        browser.close()

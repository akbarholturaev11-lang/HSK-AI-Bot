"""Telegram Mini App app offer: iPhone -> one-time PWA link, Android -> Play or APK.

Runs the real desktop-download.js and the generated Mini App catalog in a
browser; only the server answers and Telegram's WebApp bridge are stubbed.
Contract: docs/TELEGRAM_PWA_ANDROID_HANDOFF_CONTEXT.md.
"""
import json
import os
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
STATIC = Path("app/static")
SCRIPT = (STATIC / "course_v3_data/desktop-download.js").read_text(encoding="utf-8")
CATALOG = (STATIC / "course_v3_data/hsk-miniapp-i18n.js").read_text(encoding="utf-8")
ORIGIN = "https://app.hsk.test"
PWA = "https://hsk.test"
SECRET = "A" * 43
PLAY = "https://play.google.com/store/apps/details?id=com.pomp.hskai"


def status(platform, *, play=None):
    targets = {"macos": False, "windows": False, "android": platform == "android",
               "ios": platform == "ios"}
    return {
        "ok": True, "enabled": False, "platforms": dict(targets),
        "downloads": {"macos": None, "windows": None, "android_play": play},
        "promo": {
            "eligible": True, "reason": "eligible", "target_platform": platform,
            "cooldown_days": 14, "daily_limit": 3, "cooldown_remaining_seconds": 0,
            "platform_targets": targets,
            "placements": {"profile": True, "home_prompt": True,
                           "lesson_end_promo": False, "ad_promo": False},
        },
    }


class Harness:
    def __init__(self, playwright, platform, *, play=None, handoff=None):
        engine = os.environ.get("PWA_E2E_ENGINE", "chromium")
        self.browser = getattr(playwright, engine).launch()
        self.page = self.browser.new_page(viewport={"width": 390, "height": 844})
        self.errors, self.events, self.handoffs = [], [], []
        self.handoff = handoff or (lambda: {"status": 200, "body": {
            "ok": True, "expires_in": 120,
            "url": f"{PWA}/iphone-pwa/handoff#t={SECRET}&lang=uz"}})
        page = self.page
        page.on("pageerror", lambda exc: self.errors.append(str(exc)))
        page.add_init_script(
            "window.LANG='uz';window.SCREEN='course';window.__opened=[];"
            "window.Telegram={WebApp:{platform:%s,initData:'query_id=signed',"
            "openLink:function(u,o){window.__opened.push([u,o||null])},close:function(){}}};"
            "window.App={openSheet:function(h){document.getElementById('sheet').innerHTML=h;"
            "document.getElementById('sheet').classList.add('on')},"
            "closeSheet:function(){document.getElementById('sheet').classList.remove('on')}};"
            % json.dumps(platform))
        page.route("**/course_v3_data/hsk-miniapp-i18n.js", lambda route: route.fulfill(
            body=CATALOG, content_type="application/javascript; charset=utf-8"))
        page.route("**/course_v3_data/desktop-download.js", lambda route: route.fulfill(
            body=SCRIPT, content_type="application/javascript; charset=utf-8"))
        page.route("**/api/v3/desktop-download/status*", lambda route: route.fulfill(
            json=status(platform, play=play)))
        page.route("**/api/miniapp/event", self._event)
        page.route("**/api/v3/pwa-auth/handoff/start", self._handoff)
        page.route(ORIGIN + "/course-v3.html", lambda route: route.fulfill(
            content_type="text/html; charset=utf-8", body=(
                "<!doctype html><html><head><meta charset='utf-8'></head><body><section id='s-course' class='on'></section>"
                "<div id='sheet'></div>"
                "<script src='/course_v3_data/hsk-miniapp-i18n.js'></script>"
                "<script src='/course_v3_data/desktop-download.js'></script></body></html>")))
        page.goto(ORIGIN + "/course-v3.html")

    def _event(self, route):
        self.events.append(json.loads(route.request.post_data or "{}"))
        route.fulfill(json={"ok": True})

    def _handoff(self, route):
        request = route.request
        self.handoffs.append({"body": json.loads(request.post_data or "{}"),
                              "init": request.headers.get("x-telegram-init-data")})
        reply = self.handoff()
        route.fulfill(status=reply["status"], json=reply["body"])

    def promo_button(self):
        self.page.locator(".pdd-promo-shell").wait_for(state="visible", timeout=8000)
        return self.page.locator(".pdd-promo-shell [data-pdd-platform]")

    def opened(self):
        return self.page.evaluate("window.__opened")

    def names(self):
        return [event.get("event") for event in self.events]

    def close(self):
        assert self.errors == []
        self.browser.close()


def test_iphone_offer_opens_a_one_time_pwa_link_in_safari_and_reopens_it():
    with pw.sync_playwright() as playwright:
        h = Harness(playwright, "ios")
        buttons = h.promo_button()
        assert buttons.count() == 1
        assert buttons.get_attribute("data-pdd-platform") == "ios"
        shell = h.page.locator(".pdd-promo-shell")
        assert "iPhone ekraniga" in shell.locator("h2").inner_text()
        assert "Android" not in shell.inner_text()
        assert buttons.inner_text().strip() == "Safari’da ochish"
        buttons.click()
        h.page.wait_for_function("window.__opened.length === 1")
        assert h.opened() == [[f"{PWA}/iphone-pwa/handoff#t={SECRET}&lang=uz",
                               {"try_browser": "safari"}]]
        assert h.handoffs == [{"body": {"language": "uz", "source": "home_prompt"},
                               "init": "query_id=signed"}]
        assert buttons.inner_text().strip() == "Yana ochish"
        # A second tap reuses the still-valid link inside the gesture.
        buttons.click()
        h.page.wait_for_function("window.__opened.length === 2")
        assert len(h.handoffs) == 1
        seen = [e for e in h.events if e.get("event") == "desktop_promo_seen"]
        assert [e["target_platform"] for e in seen] == ["ios"]
        h.close()


@pytest.mark.parametrize("reply, message", [
    ({"status": 200, "body": {"ok": True, "expires_in": 120,
                              "url": f"{PWA}/iphone-pwa/handoff?t={SECRET}&lang=uz"}},
     "Havolani ochib bo‘lmadi"),
    ({"status": 200, "body": {"ok": True, "expires_in": 120,
                              "url": f"http://evil.test/iphone-pwa/handoff#t={SECRET}&lang=uz"}},
     "Havolani ochib bo‘lmadi"),
    ({"status": 429, "body": {"ok": False, "error": "pwa_handoff_rate_limited"}},
     "Urinishlar juda ko‘p"),
    ({"status": 403, "body": {"ok": False, "error": "pwa_handoff_unavailable"}},
     "Havolani ochib bo‘lmadi"),
])
def test_iphone_offer_never_opens_an_unexpected_link(reply, message):
    with pw.sync_playwright() as playwright:
        h = Harness(playwright, "ios", handoff=lambda: reply)
        h.promo_button().click()
        status_node = h.page.locator(".pdd-promo-shell [data-pdd-status]")
        h.page.wait_for_function(
            "(n => n.dataset.visible==='true' && n.dataset.pending==='false')"
            "(document.querySelector('.pdd-promo-shell [data-pdd-status]'))")
        assert message in status_node.inner_text()
        assert h.opened() == []
        assert h.promo_button().is_enabled()
        h.close()


def test_android_offer_opens_the_play_listing_when_admin_set_one():
    with pw.sync_playwright() as playwright:
        h = Harness(playwright, "android", play=PLAY)
        button = h.promo_button()
        assert button.inner_text().strip() == "Google Play’da ochish"
        button.click()
        h.page.wait_for_function("window.__opened.length === 1")
        assert h.opened()[0][0] == PLAY
        h.page.wait_for_timeout(300)
        assert "android_play_opened" in h.names()
        assert "android_apk_to_chat" not in h.names()
        played = next(e for e in h.events if e.get("event") == "android_play_opened")
        assert (played["source"], played["target_platform"]) == ("home_prompt", "android")
        assert h.handoffs == []
        h.close()


@pytest.mark.parametrize("play", [None, "https://play.google.com/store/apps/details?id=com.other.app"])
def test_android_without_a_valid_listing_keeps_the_direct_apk(play):
    with pw.sync_playwright() as playwright:
        h = Harness(playwright, "android", play=play)
        button = h.promo_button()
        assert button.inner_text().strip() == "Android"
        button.click()
        h.page.wait_for_timeout(500)
        assert "android_apk_to_chat" in h.names()
        assert "android_play_opened" not in h.names()
        assert h.opened() == []
        h.close()


def test_iphone_profile_entry_offers_safari_and_keeps_the_site_link():
    with pw.sync_playwright() as playwright:
        h = Harness(playwright, "ios")
        h.page.wait_for_function("window.PompDesktopDownload")
        h.page.locator(".pdd-promo-shell").wait_for(state="visible", timeout=8000)
        h.page.evaluate("document.querySelector('.pdd-promo-close').click()")
        h.page.evaluate("PompDesktopDownload.openProfileApps()")
        first = h.page.locator("#hp-app-apk")
        assert first.inner_text() == "Safari’da ochish"
        assert h.page.locator("#hp-app-site").inner_text() == "Yuklash saytini ochish"
        first.click()
        h.page.wait_for_function("window.__opened.length === 1")
        assert h.handoffs[0]["body"] == {"language": "uz", "source": "profile"}
        assert first.inner_text() == "Yana ochish"
        h.close()

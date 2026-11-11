"""iPhone PWA landing for the Telegram one-time sign-in link, in a real browser.

Serves the committed shell and real static assets under the production CSP;
only the two JSON endpoints are stubbed. The server-side `?v=` content tokens
are covered by tests/test_pwa_telegram_handoff.py, so this browser job needs
no backend dependencies.
Contract: docs/TELEGRAM_PWA_ANDROID_HANDOFF_CONTEXT.md.
"""
import json
import mimetypes
import os
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
STATIC = Path("app/static")
ORIGIN = "https://hsk.test"
SECRET = "S" * 43
SHELL = (STATIC / "iphone-pwa-handoff.html").read_text(encoding="utf-8").replace(
    "?v=AUTO", "?v=e2e")
IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 "
       "(KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1")
CSP = ("default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "connect-src 'self'; img-src 'self'; media-src 'self'; manifest-src 'self'; frame-ancestors 'none'; "
       "form-action 'none'; base-uri 'none'")


class Landing:
    def __init__(self, playwright, *, redeem=None, session=None, ios=False):
        engine = os.environ.get("PWA_E2E_ENGINE", "chromium")
        self.browser = getattr(playwright, engine).launch()
        self.page = self.browser.new_page(
            viewport={"width": 390, "height": 844}, user_agent=IOS if ios else None)
        self.errors, self.redeems, self.sessions, self.visited = [], [], [], []
        self.redeem_reply = redeem or (lambda body: (200, {"ok": True, "status": "complete"}))
        self.session_reply = session or (lambda: (200, {"ok": True, "user_id": 37,
                                                         "language": "uz"}))
        page = self.page
        page.on("pageerror", lambda exc: self.errors.append(str(exc)))
        # Expected 4xx answers are logged by the browser itself; CSP
        # violations and script errors are not, and still fail the test.
        page.on("console", lambda msg: (
            msg.type == "error" and not msg.text.startswith("Failed to load resource")
            and self.errors.append(msg.text)))
        page.route(ORIGIN + "/**", self._serve)

    def _serve(self, route):
        request = route.request
        path = request.url[len(ORIGIN):].split("#")[0]
        bare = path.split("?")[0]
        if bare == "/iphone-pwa/handoff":
            return route.fulfill(body=SHELL, headers={
                "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store",
                "Content-Security-Policy": CSP, "Referrer-Policy": "no-referrer"})
        if bare == "/api/v3/pwa-auth/handoff/redeem":
            body = json.loads(request.post_data or "{}")
            self.redeems.append({"body": body, "referer": request.headers.get("referer"),
                                 "page": self.page.url})
            status, reply = self.redeem_reply(body)
            return route.fulfill(status=status, json=reply)
        if bare == "/api/v3/pwa-auth/session":
            self.sessions.append(path)
            status, reply = self.session_reply()
            return route.fulfill(status=status, json=reply)
        if bare in ("/iphone-pwa/course", "/iphone-pwa"):
            self.visited.append(path)
            return route.fulfill(body="<!doctype html><title>next</title>",
                                 content_type="text/html")
        source = STATIC / ("iphone-pwa-handoff.js" if bare == "/iphone-pwa-handoff.js"
                           else bare.lstrip("/"))
        if source.is_file():
            kind = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
            if kind.startswith("text/") or kind.endswith("javascript"):
                kind += "; charset=utf-8"
            return route.fulfill(body=source.read_bytes(), content_type=kind)
        return route.fulfill(status=404, body="")

    def open(self, fragment=f"#t={SECRET}&lang=uz"):
        self.page.goto(ORIGIN + "/iphone-pwa/handoff" + fragment)

    def wait_left(self, target):
        self.page.wait_for_url(ORIGIN + target, timeout=8000)

    def status(self):
        return self.page.locator("#status").inner_text()

    def close(self):
        assert self.errors == []
        self.browser.close()


def test_secret_is_removed_before_redeem_and_signed_in_learner_reaches_course():
    with pw.sync_playwright() as playwright:
        landing = Landing(playwright)
        landing.open()
        landing.wait_left("/iphone-pwa/course")
        assert len(landing.redeems) == 1
        redeem = landing.redeems[0]
        assert redeem["body"] == {"token": SECRET}
        # The fragment is gone from the address bar before the network call,
        # and no Referer can carry anything off the page.
        assert redeem["page"] == ORIGIN + "/iphone-pwa/handoff"
        assert redeem["referer"] is None
        assert landing.sessions == ["/api/v3/pwa-auth/session"]
        landing.close()


def test_iphone_safari_sees_the_existing_install_guide_then_the_course():
    with pw.sync_playwright() as playwright:
        landing = Landing(playwright, ios=True)
        landing.open()
        card = landing.page.locator(".li-install-card")
        card.wait_for(state="visible", timeout=8000)
        assert landing.page.locator(".li-install-title").inner_text().strip()
        assert landing.visited == []
        landing.page.locator(".li-install-close").click()
        landing.wait_left("/iphone-pwa/course")
        landing.close()


def test_install_guide_runs_intro_then_video_forward_only_and_once():
    with pw.sync_playwright() as playwright:
        landing = Landing(playwright, ios=True)
        landing.open()
        page = landing.page
        intro, video = page.locator(".li-install-intro-page"), page.locator(".li-install-video-page")
        # Same two-step guide as after onboarding: hero page first, video second.
        intro.wait_for(state="visible", timeout=8000)
        assert page.locator(".li-install-hero").is_visible()
        assert video.is_hidden()
        page.locator(".li-install-how").click()
        video.wait_for(state="visible", timeout=8000)
        assert intro.is_hidden()
        # The video page has no way back to the hero page; closing it goes on.
        assert page.locator(".li-install-how").is_hidden()
        page.wait_for_function(
            "() => !document.querySelector('.li-install-video').hidden || "
            "!document.querySelector('.li-install-video-fallback').hidden", timeout=12000)
        assert intro.is_hidden()
        page.locator(".li-install-close").click()
        landing.wait_left("/iphone-pwa/course")
        # A second link in the same opening (tab) skips the guide; a new tab
        # is a new opening and shows it again (see test_li_onboarding_install).
        landing.visited.clear()
        landing.open()
        landing.wait_left("/iphone-pwa/course")
        assert page.locator(".li-install-card").count() == 0
        landing.close()


def test_another_learner_signed_in_here_is_never_replaced_silently():
    with pw.sync_playwright() as playwright:
        def reply(body):
            if body.get("switch") is True:
                return 200, {"ok": True, "status": "complete"}
            return 409, {"ok": False, "error": "pwa_handoff_account_mismatch"}
        landing = Landing(playwright, redeem=reply)
        landing.open()
        landing.page.locator("#primary").wait_for(state="visible")
        assert "boshqa hisob" in landing.status()
        assert landing.page.locator("#primary").inner_text() == "Telegram hisobiga o‘tish"
        assert landing.page.locator("#secondary").inner_text() == "Shu hisobda qolish"
        assert landing.visited == []
        landing.page.locator("#primary").click()
        landing.wait_left("/iphone-pwa/course")
        assert [r["body"] for r in landing.redeems] == [
            {"token": SECRET}, {"token": SECRET, "switch": True}]
        landing.close()


def test_keeping_the_current_account_spends_nothing_more():
    with pw.sync_playwright() as playwright:
        landing = Landing(playwright, redeem=lambda body: (
            409, {"ok": False, "error": "pwa_handoff_account_mismatch"}))
        landing.open()
        landing.page.locator("#secondary").wait_for(state="visible")
        landing.page.locator("#secondary").click()
        landing.wait_left("/iphone-pwa/course")
        assert len(landing.redeems) == 1
        landing.close()


@pytest.mark.parametrize("status, error", [
    (401, "pwa_handoff_invalid"), (410, "pwa_handoff_expired"),
    (403, "pwa_handoff_unavailable"),
])
def test_used_or_expired_link_offers_the_normal_sign_in(status, error):
    with pw.sync_playwright() as playwright:
        landing = Landing(playwright, redeem=lambda body: (status, {"ok": False, "error": error}))
        landing.open("#t=" + SECRET + "&lang=ru")
        landing.page.locator("#primary").wait_for(state="visible")
        assert "Ссылка устарела" in landing.status()
        assert landing.page.locator("#secondary").is_hidden()
        landing.page.locator("#primary").click()
        landing.wait_left("/iphone-pwa?login=1&lang=ru")
        assert landing.sessions == []
        landing.close()


def test_reload_without_a_link_only_continues_a_verified_session():
    with pw.sync_playwright() as playwright:
        landing = Landing(playwright, session=lambda: (401, {"ok": False}))
        landing.open("")
        landing.page.locator("#primary").wait_for(state="visible")
        assert landing.redeems == []
        assert landing.page.locator("#primary").inner_text() == "Войти"
        landing.close()
    with pw.sync_playwright() as playwright:
        landing = Landing(playwright)
        landing.open("#t=short&lang=tj")
        landing.wait_left("/iphone-pwa/course")
        assert landing.redeems == []
        landing.close()

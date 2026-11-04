"""Exercise the shipped learner checkout shell with controlled authenticated responses."""

import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest

playwright = pytest.importorskip("playwright.sync_api")

STATIC = Path(__file__).resolve().parents[2] / "app/static"
ORIGIN = "https://hsk-pwa-qa.invalid"


@pytest.mark.parametrize("return_action", ["back", "swipe"])
def test_checkout_return_keeps_profile_interactive_while_overview_is_pending(return_action):
    map_data = json.loads((STATIC / "course_v3_data/hsk1.json").read_text())
    map_data.update(
        authenticated=True,
        user={"name": "Browser Learner", "language": "uz", "onboarding_completed": True},
    )
    documents = []
    pending_overviews = []

    def respond(route):
        url = urlsplit(route.request.url)
        path = url.path
        if url.hostname != "hsk-pwa-qa.invalid":
            route.fulfill(status=200, content_type="text/css", body="")
        elif path == "/api/v3/pwa/subscription/overview":
            # The checkout must remain dismissible before this promise settles.
            assert route.request.headers["x-hsk-pwa-csrf"] == "qa-csrf"
            pending_overviews.append(route)
        elif path.startswith("/api/"):
            headers = {}
            if path == "/api/v3/pwa-auth/session":
                data = {"ok": True, "user_id": 7, "csrf": "qa-csrf"}
            elif path == "/api/v3/pwa/map":
                data = map_data
                headers["X-HSK-PWA-User-ID"] = "7"
            else:
                data = {"ok": True}
            route.fulfill(status=200, json=data, headers=headers)
        else:
            names = {
                "/iphone-pwa/course": "course-v3.html",
                "/iphone-pwa/checkout": "subscription.html",
                "/audio/words/index.js": "audio/words-index.js",
                "/audio/words/client.js": "audio/words-client.js",
            }
            file = STATIC / names.get(path, path.lstrip("/"))
            if not file.is_file():
                route.fulfill(status=404, body="")
                return
            headers = {}
            if path in {"/iphone-pwa/course", "/iphone-pwa/checkout"}:
                documents.append(path)
                headers["Cache-Control"] = "no-store"
            if path == "/iphone-pwa/checkout":
                headers.update({
                    "Content-Security-Policy": "frame-ancestors 'self'",
                    "X-Frame-Options": "SAMEORIGIN",
                })
            mime, _ = mimetypes.guess_type(file)
            route.fulfill(path=str(file), content_type=mime or "application/octet-stream", headers=headers)

    with playwright.sync_playwright() as pw:
        engine = os.getenv("PWA_E2E_ENGINE", "chromium")
        browser = getattr(pw, engine).launch()
        page = browser.new_context(**pw.devices["iPhone 13"]).new_page()
        page.set_default_timeout(7000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("**/*", respond)
        page.goto(ORIGIN + "/iphone-pwa/course?tab=profile", wait_until="domcontentloaded")
        page.locator("#s-profile.on .profile-pro-link").click()
        frame = page.frame_locator("#pwa-checkout-layer iframe")
        frame.locator("#countries [role=status]").wait_for()
        assert pending_overviews
        if return_action == "back":
            page.locator("#pwa-checkout-back").click()
        else:
            page.evaluate("""() => {
                const node = document.querySelector('#pwa-checkout-layer iframe').contentDocument.body;
                const emit = (type, x) => {
                    const touch = {clientX: x, clientY: 150};
                    const event = new Event(type, {bubbles: true, cancelable: true});
                    Object.defineProperties(event, {
                        touches: {value: type === 'touchend' ? [] : [touch]},
                        changedTouches: {value: [touch]},
                    });
                    node.dispatchEvent(event);
                };
                emit('touchstart', 40);
                emit('touchmove', 145);
                emit('touchend', 145);
            }""")
        page.locator("#pwa-checkout-layer").wait_for(state="detached")
        assert page.locator("#s-profile.on").is_visible()
        assert not page.locator(".wrap").evaluate("node => node.inert")
        assert documents == ["/iphone-pwa/course", "/iphone-pwa/checkout"]
        assert not errors
        browser.close()

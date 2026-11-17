"""PWA Pro card checkout: one tap opens the verified payment page in the same
window (no intermediate "page ready" step, no about:blank popup) and the
provider return brings the learner back into the app, where only the server
status decides the outcome."""
import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest

playwright = pytest.importorskip("playwright.sync_api")
STATIC = Path(__file__).resolve().parents[2] / "app/static"
ORIGIN = "https://hsk-lava-link-qa.invalid"
COURSE = """<!doctype html>
  <html lang="uz"><head><meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link rel="stylesheet" href="/course_v3_data/iphone-pwa-inline-pro.css?v=e2e">
  </head><body>
  <script src="/course_v3_data/iphone-pwa-inline-pro.js?v=e2e"></script>
  </body></html>"""


def _server(url, captured, status):
    def serve(route):
        path = urlsplit(route.request.url).path
        if route.request.url.startswith("https://app.lava.top/"):
            route.fulfill(status=200, body="<html><body>Provider checkout ready</body></html>",
                          content_type="text/html; charset=utf-8")
            return
        if path == "/iphone-pwa/course":
            route.fulfill(status=200, content_type="text/html; charset=utf-8", body=COURSE)
            return
        if path == "/api/v3/pwa-auth/session":
            route.fulfill(status=200, json={"ok": True, "csrf": "qa-csrf", "user_id": 1})
            return
        if path == "/api/v3/pwa/subscription/overview":
            route.fulfill(status=200, json={"ok": True, "lava": {
                "mode": "both", "email": "buyer@example.com",
                "plans": [
                    {"plan_type": "1_month", "amount": "7.90", "currency": "USD"},
                    {"plan_type": "12_months", "amount": "64.90", "currency": "USD"},
                ]}})
            return
        if path == "/api/v3/pwa/subscription/lava/start":
            payload = json.loads(route.request.post_data)
            assert payload["plan_type"] == "1_month"
            assert payload["email"] == "buyer@example.com"
            captured.append(("start", payload))
            route.fulfill(status=200, json={"ok": True, "checkout_id": 4242, "payment_url": url})
            return
        if path == "/api/v3/pwa/subscription/lava/status":
            payload = json.loads(route.request.post_data)
            captured.append(("status", payload["checkout_id"]))
            route.fulfill(status=200, json={"ok": True, "status": status["value"]})
            return
        if path == "/api/v3/pwa/subscription/exit-offer":
            payload = json.loads(route.request.post_data)
            captured.append(("offer", payload["action"]))
            route.fulfill(status=200, json={"ok": True, "available": True, "percent": 20})
            return
        if path == "/api/v3/pwa/subscription/inline-event":
            route.fulfill(status=200, json={"ok": True, "recorded": True})
            return
        if path.startswith("/api/"):
            route.fulfill(status=404, json={"error": "unknown"})
            return
        file = STATIC / path.lstrip("/")
        if file.is_file():
            mime, _ = mimetypes.guess_type(file)
            route.fulfill(path=str(file), content_type=mime or "application/octet-stream")
            return
        route.fulfill(status=404, body="")
    return serve


@pytest.mark.parametrize("url,expected", [
    ("https://app.lava.top/pay/demo", True),
    ("https://payments.attacker.invalid/pay/demo", False),
])
def test_pro_button_opens_verified_payment_page_directly(url, expected):
    captured = []
    with playwright.sync_playwright() as pw:
        browser = getattr(pw, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        context = browser.new_context(**pw.devices["iPhone 13"])
        page = context.new_page()
        context.route("**/*", _server(url, captured, {"value": "pending"}))
        errors = []; popups = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.on("popup", lambda popup: popups.append(popup))
        page.goto(ORIGIN + "/iphone-pwa/course")
        page.evaluate("HSKPwaInlinePro.open({source:'v3_locked_lesson',lang:'uz'})")
        cta = page.get_by_role("button", name="Pro ⭐️ olish")
        cta.wait_for()
        assert "lava" not in page.locator("#hsk-inline-pro").inner_text().lower()
        if expected:
            with page.expect_navigation(url=url):
                cta.click()
            # Straight to the provider in the same window: no "page ready"
            # step, no popup and no blank tab.
            assert page.url == url
            assert "Provider checkout ready" in page.locator("body").inner_text()
        else:
            cta.click()
            page.locator("#hsk-inline-pro .hip-error").wait_for(state="visible")
            assert page.url == ORIGIN + "/iphone-pwa/course"
            assert page.get_by_role("link", name="To‘lovga o‘tish").count() == 0
        assert len(popups) == 0, "No popup / about:blank tab may be opened"
        assert len([c for c in captured if c[0] == "start"]) == 1
        assert not errors, errors
        browser.close()


def test_provider_return_resumes_in_app_and_only_server_status_decides():
    captured = []
    status = {"value": "pending"}
    with playwright.sync_playwright() as pw:
        browser = getattr(pw, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        context = browser.new_context(**pw.devices["iPhone 13"])
        page = context.new_page()
        context.route("**/*", _server("https://app.lava.top/pay/demo", captured, status))
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        # Successful provider return: the paywall resumes on its own, checks
        # the server and removes the return parameters from the address.
        page.goto(ORIGIN + "/iphone-pwa/course?lang=uz&pro_checkout=4242&pro_return=success")
        page.get_by_role("heading", name="To‘lov tekshirilmoqda…").wait_for()
        assert "pro_checkout" not in page.url and "pro_return" not in page.url
        assert page.url.endswith("/iphone-pwa/course?lang=uz")
        assert ("status", 4242) in captured
        # The redirect itself never shows success; the webhook-backed status does.
        assert page.get_by_role("heading", name="Pro faollashtirildi").count() == 0
        status["value"] = "paid"
        page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
        page.get_by_role("heading", name="Pro faollashtirildi").wait_for()
        page.get_by_role("button", name="O‘qishga qaytish").click()
        assert page.locator("#hsk-inline-pro").is_hidden()

        # Cancelled payment: back to the plans; X offers the real 20% first.
        page.goto(ORIGIN + "/iphone-pwa/course?lang=uz&pro_checkout=4243&pro_return=cancel")
        page.locator("#hsk-inline-pro button.hip-plan").first.wait_for()
        assert page.get_by_role("heading", name="Limit tugadi").is_visible()
        assert ("status", 4243) not in captured
        page.locator("#hsk-inline-pro .hip-close").click()
        page.get_by_role("button", name="Chegirmani olish").wait_for()
        assert ("offer", "view") in captured
        # Malformed ids are ignored and stripped.
        page.goto(ORIGIN + "/iphone-pwa/course?lang=uz&pro_checkout=abc&pro_return=success")
        page.wait_for_timeout(300)
        assert page.locator("#hsk-inline-pro").count() == 0 or page.locator("#hsk-inline-pro").is_hidden()
        assert "pro_checkout" not in page.url
        assert not errors, errors
        browser.close()

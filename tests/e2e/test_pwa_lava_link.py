"""PWA Pro checkout requests the verified payment page externally, keeps the
app available and offers a user-gesture link to the same invoice if a popup
is blocked. Only server status decides the payment outcome."""
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
            checkout_id = 4241 + sum(c[0] == "start" for c in captured)
            route.fulfill(status=200, json={"ok": True, "checkout_id": checkout_id, "payment_url": url})
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


@pytest.mark.parametrize("url,expected,throws", [
    ("https://app.lava.top/pay/demo", True, False),
    ("https://app.lava.top/pay/demo", True, True),
    ("https://payments.attacker.invalid/pay/demo", False, False),
])
def test_pro_button_opens_verified_payment_page_directly(url, expected, throws):
    captured = []
    status = {"value": "pending"}
    with playwright.sync_playwright() as pw:
        browser = getattr(pw, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        context = browser.new_context(**pw.devices["iPhone 13"])
        page = context.new_page()
        context.route("**/*", _server(url, captured, status))
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(ORIGIN + "/iphone-pwa/course")
        # Model a browser that refuses the asynchronous popup, including the
        # case where window.open throws. The fallback must be a real link.
        page.evaluate("""throws => {
            window.paymentOpens = [];
            window.open = (...args) => {
                window.paymentOpens.push(args);
                if (throws) throw new Error("popup unavailable");
                return null;
            };
        }""", throws)
        page.evaluate("HSKPwaInlinePro.open({source:'v3_locked_lesson',lang:'uz'})")
        cta = page.get_by_role("button", name="Pro ⭐️ olish")
        cta.wait_for()
        assert "lava" not in page.locator("#hsk-inline-pro").inner_text().lower()
        cta.click()
        if expected:
            link = page.get_by_role("link", name="To‘lovga o‘tish")
            link.wait_for()
            assert page.evaluate("window.paymentOpens") == [[url, "_blank", "noopener"]]
            assert link.get_attribute("href") == url
            assert link.get_attribute("target") == "_blank"
            assert link.get_attribute("rel") == "noopener noreferrer"
            assert page.url == ORIGIN + "/iphone-pwa/course"
            # The fallback click actually opens a separate browser page; it
            # neither navigates the learner away nor creates another invoice.
            with context.expect_page() as external:
                link.click()
            provider = external.value
            provider.wait_for_url(url)
            assert "Provider checkout ready" in provider.locator("body").inner_text()
            provider.close()
            assert page.url == ORIGIN + "/iphone-pwa/course"
            assert link.is_visible()
            assert page.get_by_role("heading", name="Pro faollashtirildi").count() == 0
            status["value"] = "paid"
            page.bring_to_front()
            page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
            page.get_by_role("heading", name="Pro faollashtirildi").wait_for()
        else:
            page.locator("#hsk-inline-pro .hip-error").wait_for(state="visible")
            assert page.url == ORIGIN + "/iphone-pwa/course"
            assert page.get_by_role("link", name="To‘lovga o‘tish").count() == 0
            assert page.evaluate("window.paymentOpens") == []
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

def test_retry_after_server_confirmed_failure_polls_new_invoice():
    captured = []
    status = {"value": "failed"}
    with playwright.sync_playwright() as pw:
        browser = getattr(pw, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        context = browser.new_context(**pw.devices["iPhone 13"])
        page = context.new_page()
        context.route("**/*", _server("https://app.lava.top/pay/demo", captured, status))
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(ORIGIN + "/iphone-pwa/course")
        page.evaluate("window.open = () => null")
        page.evaluate("HSKPwaInlinePro.open({source:'v3_locked_lesson',lang:'uz'})")
        cta = page.get_by_role("button", name="Pro ⭐️ olish")
        cta.click()
        page.locator("#hsk-inline-pro .hip-error").wait_for(state="visible")
        assert ("status", 4242) in captured
        assert page.get_by_role("link", name="To‘lovga o‘tish").count() == 0

        # A new checkout is intentional only after the server reports failure.
        # The previous polling lock must not suppress its status request.
        status["value"] = "paid"
        cta.click()
        page.get_by_role("heading", name="Pro faollashtirildi").wait_for()
        assert ("status", 4243) in captured
        assert len([c for c in captured if c[0] == "start"]) == 2
        assert not errors, errors
        browser.close()


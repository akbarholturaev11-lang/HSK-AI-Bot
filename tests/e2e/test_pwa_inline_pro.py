"""Real-browser contract for the PWA inline Pro UX with controlled payment endpoints."""
import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest

playwright = pytest.importorskip("playwright.sync_api")
STATIC = Path(__file__).resolve().parents[2] / "app/static"
ORIGIN = "https://hsk-inline-pro-qa.invalid"


def _overview(discount=False):
    terms = (
        ("1_month", "10.00"),
        ("3_months", "27.00"),
        ("6_months", "50.00"),
        ("12_months", "90.00"),
    )
    plans = []
    for code, value in terms:
        row = {"plan_type": code, "currency": "USD",
               "amount": f"{float(value)*0.8:.2f}" if discount else value}
        if discount:
            row.update(base_amount=value, discount_percent=20)
        plans.append(row)
    return {"ok": True, "lava": {"mode": "both", "plans": plans, "email": "buyer@example.com"}}


def test_inline_pro_two_primary_plans_other_terms_and_real_exit_discount():
    seen = []
    def respond(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(status=200, content_type="text/html", body="""
                <!DOCTYPE html><html lang="ru"><head>
                <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
                <link rel="stylesheet" href="/course_v3_data/iphone-pwa-inline-pro.css?v=qa">
                </head><body><button id="starter">open</button>
                <script src="/course_v3_data/iphone-pwa-inline-pro.js?v=qa"></script>
                </body></html>""")
            return
        if path == "/api/v3/pwa-auth/session":
            route.fulfill(status=200, json={"ok": True, "user_id": 7, "csrf": "qa-csrf"})
            return
        if path == "/api/v3/pwa/subscription/inline-event":
            payload = json.loads(route.request.post_data or "{}")
            assert route.request.headers["x-hsk-pwa-csrf"] == "qa-csrf"
            seen.append(("event", payload["event"]))
            route.fulfill(status=200, json={"ok": True,"recorded": True})
            return
        if path == "/api/v3/pwa/subscription/overview":
            payload = json.loads(route.request.post_data or "{}")
            assert route.request.headers["x-hsk-pwa-csrf"] == "qa-csrf"
            assert payload["inline_preview"] is True
            seen.append(("overview", payload["mode"]))
            route.fulfill(status=200, json=_overview(payload.get("mode") == "exit_discount"))
            return
        if path == "/api/v3/pwa/subscription/exit-offer":
            payload = json.loads(route.request.post_data or "{}")
            seen.append(("offer", payload["action"]))
            route.fulfill(status=200, json={"ok": True, "available": True, "percent": 20})
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

    with playwright.sync_playwright() as pw:
        browser = getattr(pw, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        page = browser.new_context(**pw.devices["iPhone 13"]).new_page()
        page.set_default_timeout(8000)
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.route("**/*", respond)
        page.goto(ORIGIN + "/iphone-pwa/course")
        page.evaluate("HSKPwaInlinePro.open({source:'v3_locked_lesson',lang:'ru'})")
        assert page.get_by_role("heading", name="Лимит исчерпан").is_visible()
        assert page.locator("#hsk-inline-pro .hip-panda svg").is_visible()
        assert page.locator("#hsk-inline-pro .hip-benefit").count() == 3
        assert page.locator("#hsk-inline-pro .hip-sheet").evaluate(
            "(node) => getComputedStyle(node).animationName"
        ) != "none"
        page.locator("#hsk-inline-pro button.hip-plan").first.wait_for()
        assert page.locator("#hsk-inline-pro button.hip-plan").count() == 2
        assert "1 месяц" in page.locator("#hsk-inline-pro .hip-body").inner_text()
        assert "1 год" in page.locator("#hsk-inline-pro .hip-body").inner_text()
        assert "12.99" in page.locator("#hsk-inline-pro .hip-body").inner_text()
        page.get_by_role("button", name="Другие тарифы").click()
        page.get_by_role("button", name="Visa / Mastercard — Lava.top").click()
        assert page.locator("#hsk-inline-pro button.hip-plan").count() == 4
        page.locator("#hsk-inline-pro .hip-close").click()
        page.get_by_role("button", name="Забрать скидку").click()
        page.locator("#hsk-inline-pro button.hip-plan").first.wait_for()
        assert page.locator("#hsk-inline-pro button.hip-plan").count() == 2
        assert "8.00 USD" in page.locator("#hsk-inline-pro .hip-body").inner_text()
        assert page.locator("#hsk-inline-pro button.hip-plan .comparison").first.inner_text() == "10.00"
        assert ("offer", "view") in seen
        assert ("offer", "claim") in seen
        assert ("overview", "exit_discount") in seen
        page.wait_for_load_state("networkidle")
        assert ("event", "pwa_pro_opened") in seen
        assert ("event", "pwa_pro_more_opened") in seen
        assert ("event", "pwa_pro_method_selected") in seen
        assert ("event", "pwa_pro_exit_offered") in seen
        assert ("event", "pwa_pro_exit_claimed") in seen
        page.locator("#hsk-inline-pro .hip-close").click()
        assert page.locator("#hsk-inline-pro").is_hidden()
        assert not errors
        browser.close()

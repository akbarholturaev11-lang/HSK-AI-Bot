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
                <script src="/course_v3_data/hsk-subscription-presentation.js?v=qa"></script>
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
        # The course mascot (pandaChar geometry) in the Pro-card pose.
        assert page.locator("#hsk-inline-pro .hip-panda svg.hip-pd-char").get_attribute("viewBox") == "-6 -8 112 116"
        assert page.locator("#hsk-inline-pro .hip-panda").get_attribute("data-pose") == "pro"
        # Opening focuses the dialog itself, never a button with a focus ring.
        assert page.evaluate("document.activeElement.classList.contains('hip-sheet')")
        # iPhone full viewport, not a partial-height bottom sheet.
        layout = page.evaluate("""() => {
            const r=document.getElementById("hsk-inline-pro").getBoundingClientRect();
            const s=document.querySelector("#hsk-inline-pro .hip-sheet").getBoundingClientRect();
            return {rootW:r.width,rootH:r.height,sheetW:s.width,sheetH:s.height,
              vw:window.innerWidth,vh:window.innerHeight,
              background:getComputedStyle(document.getElementById("hsk-inline-pro")).backgroundColor};
        }""")
        assert abs(layout["rootW"] - layout["vw"]) <= 2
        assert abs(layout["rootH"] - layout["vh"]) <= 2
        assert abs(layout["sheetH"] - layout["vh"]) <= 2
        assert layout["background"] == "rgb(253, 249, 240)"
        assert page.locator("#hsk-inline-pro").evaluate(
            "(node) => getComputedStyle(node).animationName"
        ) != "none"
        page.locator("#hsk-inline-pro button.hip-plan").first.wait_for()
        assert page.locator("#hsk-inline-pro button.hip-plan").count() == 2
        assert "1 месяц" in page.locator("#hsk-inline-pro .hip-body").inner_text()
        assert "1 год" in page.locator("#hsk-inline-pro .hip-body").inner_text()
        assert "12.99" in page.locator("#hsk-inline-pro .hip-body").inner_text()
        assert page.locator("#hsk-inline-pro .hip-region").is_visible()
        assert "не предыдущая цена" in page.locator("#hsk-inline-pro .hip-reference-note").inner_text()
        page.get_by_role("button", name="Другие тарифы").click()
        # The title is never covered by the 44px back and close controls.
        no_overlap=page.evaluate("""() => {
            const h=document.querySelector("#hsk-inline-pro .hip-title").getBoundingClientRect();
            const a=document.querySelector("#hsk-inline-pro .hip-back").getBoundingClientRect();
            const b=document.querySelector("#hsk-inline-pro .hip-close").getBoundingClientRect();
            return h.right <= b.left && h.left >= a.right;
        }""")
        assert no_overlap
        # "Other plans" is ONE screen: all four terms plus the regular method.
        # No provider choice step and no provider names for the learner.
        assert page.get_by_role("heading", name="Другие тарифы").is_visible()
        assert page.locator("#hsk-inline-pro button.hip-plan").count() == 4
        assert page.locator("#hsk-inline-pro .hip-method").count() == 1
        assert "lava" not in page.locator("#hsk-inline-pro").inner_text().lower()
        assert "≈ 7.50 USD / мес" in page.locator("#hsk-inline-pro .hip-body").inner_text()
        page.locator("#hsk-inline-pro button.hip-plan").nth(1).click()
        assert page.locator("#hsk-inline-pro button.hip-plan").nth(1).get_attribute("aria-pressed") == "true"
        page.locator("#hsk-inline-pro .hip-close").click()
        page.get_by_role("button", name="Забрать скидку").wait_for()
        assert page.locator("#hsk-inline-pro .hip-panda").get_attribute("data-pose") == "gift"
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
        assert ("event", "pwa_pro_plan_selected") in seen
        assert ("event", "pwa_pro_exit_offered") in seen
        assert ("event", "pwa_pro_exit_claimed") in seen
        page.locator("#hsk-inline-pro .hip-close").click()
        assert page.locator("#hsk-inline-pro").is_hidden()
        assert not errors
        browser.close()


def _serve_static(route, path):
    file = STATIC / path.lstrip("/")
    if file.is_file():
        mime, _ = mimetypes.guess_type(file)
        route.fulfill(path=str(file), content_type=mime or "application/octet-stream")
        return
    route.fulfill(status=404, body="")


@pytest.mark.parametrize("lava,expected", [
    (None, "manual"),
    ({"mode": "both", "plans": [{"plan_type": "1_month", "currency": "USD", "amount": "10.00"}],
      "blocked_reason": "subscription_active"}, "status"),
])
def test_inline_pro_manual_only_and_blocked_states_are_honest(lava, expected):
    def respond(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(status=200, content_type="text/html", body="""
                <!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
                <meta name="viewport" content="width=device-width,initial-scale=1">
                <link rel="stylesheet" href="/course_v3_data/iphone-pwa-inline-pro.css?v=qa">
                </head><body><script src="/course_v3_data/hsk-subscription-presentation.js?v=qa"></script>
                <script src="/course_v3_data/iphone-pwa-inline-pro.js?v=qa"></script>
                </body></html>""")
            return
        if path == "/api/v3/pwa-auth/session":
            route.fulfill(status=200, json={"ok": True, "user_id": 7, "csrf": "qa-csrf"})
            return
        if path == "/api/v3/pwa/subscription/overview":
            route.fulfill(status=200, json={"ok": True, "lava": lava})
            return
        if path == "/api/v3/pwa/subscription/inline-event":
            route.fulfill(status=200, json={"ok": True})
            return
        if path.startswith("/iphone-pwa/checkout"):
            route.fulfill(status=200, content_type="text/html", body="<body>manual</body>")
            return
        if path.startswith("/api/"):
            route.fulfill(status=404, json={"error": "unknown"})
            return
        _serve_static(route, path)

    with playwright.sync_playwright() as pw:
        browser = getattr(pw, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        page = browser.new_context(**pw.devices["iPhone 13"]).new_page()
        page.set_default_timeout(8000)
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.route("**/*", respond)
        page.goto(ORIGIN + "/iphone-pwa/course")
        page.evaluate("HSKPwaInlinePro.open({source:'v3_locked_lesson',lang:'ru'})")
        if expected == "manual":
            # Card checkout off: no fake "unavailable" error, the one CTA opens
            # the regular receipt checkout inside the same Pro surface.
            cta = page.get_by_role("button", name="Получить Pro")
            cta.wait_for()
            assert page.locator("#hsk-inline-pro .hip-error").count() == 0
            assert "недоступны" not in page.locator("#hsk-inline-pro").inner_text()
            assert page.get_by_role("button", name="Другие тарифы").count() == 0
            cta.click()
            frame = page.locator("#hsk-inline-pro iframe")
            frame.wait_for()
            assert "inline_manual=1" in frame.get_attribute("src")
            assert page.locator("#hsk-inline-pro .hip-back").is_hidden()
            page.evaluate("HSKPwaInlinePro.closeEmbeddedCheckout(document.querySelector('#hsk-inline-pro iframe').contentWindow)")
            assert page.get_by_role("heading", name="Лимит исчерпан").is_visible()
        else:
            heading = page.get_by_role("heading", name="Проверьте текущий платёж или действующую подписку")
            heading.wait_for()
            assert page.locator("#hsk-inline-pro button.hip-plan").count() == 0
            assert page.locator("#hsk-inline-pro .hip-panda").get_attribute("data-pose") == "read"
            page.get_by_role("button", name="Вернуться к обучению").click()
            assert page.locator("#hsk-inline-pro").is_hidden()
        assert not errors, errors
        browser.close()


@pytest.mark.parametrize("lang,source,expected", [
    ("uz", "v3_locked_lesson", "Pro bilan HSK darslarini davom ettiring."),
    ("ru", "v3_mistake_review", "Продолжайте работу над ошибками с Pro."),
    ("tj", "v3_locked_lesson", "Бо Pro дарсҳои HSK-ро идома диҳед."),
])
def test_inline_pro_learning_benefit_requires_authorized_offer(lang, source, expected):
    overview = {}
    attempts = []

    def respond(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(status=200, content_type="text/html", body="""
                <!DOCTYPE html><html><head><meta charset="utf-8">
                <meta name="viewport" content="width=device-width,initial-scale=1">
                <link rel="stylesheet" href="/course_v3_data/iphone-pwa-inline-pro.css?v=qa">
                <script src="/course_v3_data/hsk-course-i18n.js?v=qa"></script>
                </head><body><script src="/course_v3_data/hsk-subscription-presentation.js?v=qa"></script>
                <script src="/course_v3_data/iphone-pwa-inline-pro.js?v=qa"></script>
                </body></html>""")
        elif path == "/api/v3/pwa-auth/session":
            route.fulfill(status=200, json={"ok": True, "user_id": 7, "csrf": "qa-csrf"})
        elif path == "/api/v3/pwa/subscription/overview":
            attempts.append(json.loads(route.request.post_data or "{}"))
            route.fulfill(status=200, json=overview)
        elif path.startswith("/api/"):
            route.fulfill(status=200, json={"ok": True, "available": False})
        else:
            _serve_static(route, path)

    offers = (
        ({**_overview(), "learning_pro_eligible": True}, "main", True),
        ({**_overview(), "learning_pro_eligible": False}, "main", False),
        ({"ok": True, "learning_pro_eligible": True, "lava": {"mode": "lava_only", "plans": []}},
         "main", False),
        ({"ok": True, "learning_pro_eligible": False, "pending_payment": {"status": "pending"}},
         "status", False),
        ({"ok": True, "learning_pro_eligible": False, "access": {"is_paid": True}},
         "status", False),
    )

    with playwright.sync_playwright() as pw:
        browser = getattr(pw, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        page = browser.new_context(is_mobile=True, has_touch=True, viewport={"width": 320, "height": 750}).new_page()
        page.set_default_timeout(8000)
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.route("**/*", respond)
        for offer, screen, shows_benefit in offers:
            overview = offer
            page.goto(ORIGIN + "/iphone-pwa/course")
            page.evaluate("opts => HSKPwaInlinePro.open(opts)", {"source": source, "lang": lang})
            panel = page.locator(f'#hsk-inline-pro[data-screen="{screen}"]')
            panel.wait_for()
            assert panel.get_by_text(expected, exact=True).is_visible() == shows_benefit
            if screen == "main":
                assert panel.locator(".hip-benefit").count() == 3
            else:
                assert panel.locator(".hip-plan").count() == 0
            assert panel.locator(".hip-close").count() == 1
        assert len(attempts) == len(offers)
        assert all(a.get("source") == source and a.get("inline_preview") is True for a in attempts)
        assert not errors
        browser.close()


def test_inline_region_changes_use_verified_prices_without_overview_reload():
    seen = []
    usd = [{"plan_type": "1_month", "currency": "USD", "amount": "10.00"}]
    rub = [{"plan_type": "1_month", "currency": "RUB", "amount": "900.00"}]
    overview = {
        "ok": True,
        "prices": {
            "visa": {"1_month": {"currency": "TJS", "final_amount": 49, "base_amount": 49}},
            "alipay": {"1_month": {"currency": "CNY", "final_amount": 35, "base_amount": 35}},
        },
        "card_prices": {
            "uz": {"1_month": {"currency": "UZS", "final_amount": 55000, "base_amount": 55000}},
            "ru": {"1_month": {"currency": "RUB", "final_amount": 500, "base_amount": 500}},
            "other": {"1_month": {"currency": "USD", "final_amount": 5, "base_amount": 5}},
        },
        "lava": {"mode": "both", "currency": "USD", "plans": usd,
                 "plans_by_currency": {"USD": usd, "RUB": rub}, "email": "test@example.com"},
    }

    def respond(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(status=200, content_type="text/html", body="""
                <!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
                <meta name="viewport" content="width=device-width,initial-scale=1">
                <link rel="stylesheet" href="/course_v3_data/iphone-pwa-inline-pro.css?v=qa">
                </head><body>
                <script src="/course_v3_data/hsk-subscription-presentation.js?v=qa"></script>
                <script src="/course_v3_data/iphone-pwa-inline-pro.js?v=qa"></script>
                </body></html>""")
        elif path == "/api/v3/pwa-auth/session":
            route.fulfill(status=200, json={"ok": True, "user_id": 7, "csrf": "qa-csrf"})
        elif path == "/api/v3/pwa/subscription/overview":
            seen.append("overview")
            route.fulfill(status=200, json=overview)
        elif path == "/iphone-pwa/checkout":
            seen.append(route.request.url)
            route.fulfill(status=200, content_type="text/html", body="<html><body>Manual checkout</body></html>")
        elif path == "/api/v3/pwa/subscription/inline-event":
            route.fulfill(status=200, json={"ok": True, "recorded": True})
        else:
            _serve_static(route, path)

    with playwright.sync_playwright() as pw:
        browser = getattr(pw, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        page = browser.new_context(**pw.devices["iPhone 13"]).new_page()
        page.set_default_timeout(8000)
        page.route("**/*", respond)
        page.goto(ORIGIN + "/iphone-pwa/course")
        page.evaluate("localStorage.setItem('hsk_sub_region_v1:pwa:7','tj')")
        page.evaluate("HSKPwaInlinePro.open({source:'v3_locked_lesson',lang:'ru'})")
        region = page.locator("#hsk-inline-pro .hip-region")
        region.wait_for()
        assert region.input_value() == "tj"
        assert "49.00 TJS" in page.locator("#hsk-inline-pro .hip-plan").first.inner_text()
        region.select_option("ru")
        assert "900.00 RUB" in page.locator("#hsk-inline-pro .hip-plan").first.inner_text()
        region.select_option("uz")
        assert "10.00 USD" in page.locator("#hsk-inline-pro .hip-plan").first.inner_text()
        region.select_option("cn")
        assert "35.00 CNY" in page.locator("#hsk-inline-pro .hip-plan").first.inner_text()
        assert seen.count("overview") == 1
        assert page.evaluate("localStorage.getItem('hsk_sub_region_v1:pwa:7')") == "cn"
        assert page.evaluate("document.characterSet") == "UTF-8"
        cta = page.locator("#hsk-inline-pro .hip-actions button.hip-primary")
        assert cta.count() == 1, page.locator("#hsk-inline-pro").inner_text()
        assert "Получить Pro" in cta.inner_text(), cta.inner_text()
        cta.click()
        frame = page.locator("#hsk-inline-pro iframe")
        frame.wait_for()
        assert "country=cn" in frame.get_attribute("src")
        assert "plan=1_month" in frame.get_attribute("src")
        page.evaluate("HSKPwaInlinePro.closeEmbeddedCheckout(document.querySelector('#hsk-inline-pro iframe').contentWindow)")
        assert page.get_by_role("heading", name="Лимит исчерпан").is_visible()
        assert page.locator("#hsk-inline-pro .hip-region").input_value() == "cn"
        browser.close()

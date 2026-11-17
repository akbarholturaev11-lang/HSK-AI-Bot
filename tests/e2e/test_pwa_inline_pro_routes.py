"""PWA inline Pro opens at each authenticated limit entry point.

Synthetic pages focus on the runtime bridge contract. Full PWA/Telegram
HTML remains separately source-guarded; real iOS payments require device QA.
"""
import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest

playwright = pytest.importorskip("playwright.sync_api")
STATIC = Path(__file__).resolve().parents[2] / "app/static"
ORIGIN = "https://inline-route-qa.invalid"
PRACTICES = ("voice", "recognition", "memorize", "pronunciation", "test", "mistakes")


def _markup(path):
    if path == "/iphone-pwa/course":
        stub = "window.oldCalls=0;window.App={openPaywall:function(){oldCalls++},goPay:function(){oldCalls++}};"
    elif path.endswith("/voice"):
        stub = "window.oldCalls=0;window.showPaywall=function(){oldCalls++};window.goPremium=function(){oldCalls++};"
    else:
        stub = "window.oldCalls=0;window.showLimitNow=function(){oldCalls++};window.goPremium=function(){oldCalls++};window.goPay=function(){oldCalls++};"
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <link rel="stylesheet" href="/course_v3_data/iphone-pwa-inline-pro.css?v=e2e">
      </head><body><div id="secov"></div><button id="go">Start</button>
      <script>{stub}</script>
      <script src="/course_v3_data/iphone-pwa-inline-pro.js?v=e2e"></script>
      <script src="/course_v3_data/iphone-pwa-inline-pro-bridge.js?v=e2e"></script>
      </body></html>"""


def _serve(route):
    path = urlsplit(route.request.url).path
    if path == "/iphone-pwa/course" or path in (
        "/iphone-pwa/practice/" + name for name in PRACTICES
    ):
        route.fulfill(status=200, body=_markup(path), content_type="text/html; charset=utf-8")
        return
    if path == "/iphone-pwa/checkout":
        route.fulfill(status=200, body="<html><body>Manual checkout</body></html>",
                      content_type="text/html; charset=utf-8")
        return
    if path == "/api/v3/pwa-auth/session":
        route.fulfill(status=200, json={"ok":True,"csrf":"testcsrf","user_id":1})
        return
    if path == "/api/v3/pwa/subscription/overview":
        request = json.loads(route.request.post_data or "{}")
        assert request.get("inline_preview") is True
        route.fulfill(status=200, json={"ok":True,"lava":{"mode":"both","plans":[
            {"plan_type":"1_month","amount":"10.00","currency":"USD"},
            {"plan_type":"12_months","amount":"90.00","currency":"USD"},
        ]}})
        return
    if path == "/api/v3/pwa/subscription/exit-offer":
        route.fulfill(status=200,json={"ok":True,"available":False})
        return
    if path == "/api/v3/pwa/subscription/inline-event":
        route.fulfill(status=200,json={"ok":True,"recorded":True})
        return
    file = STATIC / path.lstrip("/")
    if file.is_file():
        mime, _ = mimetypes.guess_type(file)
        route.fulfill(path=str(file), content_type=mime or "application/octet-stream")
        return
    route.fulfill(status=404, body="")


@pytest.mark.parametrize("pathname,invoke,original", [
    ("/iphone-pwa/course","App.openPaywall('lockedLesson')",0),
    ("/iphone-pwa/course","App.goPay('v3_recognition_limit')",0),
    ("/iphone-pwa/practice/voice","showPaywall()",0),
    ("/iphone-pwa/practice/recognition","showLimitNow()",0),
    ("/iphone-pwa/practice/memorize","showLimitNow()",0),
    ("/iphone-pwa/practice/pronunciation","showLimitNow()",0),
    ("/iphone-pwa/practice/test","showLimitNow()",0),
    ("/iphone-pwa/practice/mistakes","showLimitNow()",0),
])
def test_inline_offer_is_entered_from_each_limit(pathname,invoke,original):
    with playwright.sync_playwright() as pw:
        browser = getattr(pw,os.getenv("PWA_E2E_ENGINE","chromium")).launch()
        page = browser.new_context(**pw.devices["iPhone 13"]).new_page()
        page.route("**/*",_serve)
        errors=[]
        page.on("pageerror",lambda exc:errors.append(str(exc)))
        page.goto(ORIGIN+pathname)
        page.evaluate(invoke)
        page.locator("#hsk-inline-pro button.hip-plan").first.wait_for()
        assert page.get_by_role("heading",name="Лимит исчерпан").is_visible()
        assert page.locator("#hsk-inline-pro .hip-benefit").count()==3
        assert page.evaluate("oldCalls")==original
        page.locator("#hsk-inline-pro .hip-close").click()
        if pathname == "/iphone-pwa/course":
            page.locator("#hsk-inline-pro").wait_for(state="hidden")
        else:
            page.wait_for_url(ORIGIN + "/iphone-pwa/course?lang=ru")
        assert not errors
        browser.close()


def test_inline_manual_skips_card_question_without_modifying_shared_checkout():
    # The hosted manual checkout normally starts with a Visa/Lava question
    # whenever two payment methods exist. Here the parent chose manual.
    with playwright.sync_playwright() as pw:
        browser = getattr(pw,os.getenv("PWA_E2E_ENGINE","chromium")).launch()
        page = browser.new_context(**pw.devices["iPhone 13"]).new_page()
        page.route("**/*",_serve)
        page.goto(ORIGIN+"/iphone-pwa/course")
        # Exercise the exact PWA checkout bridge against the canonical
        # function signature and state names used in subscription.html.
        js=(STATIC/"course_v3_data/iphone-pwa-inline-pro-bridge.js").read_text("utf-8")
        page.evaluate("""() => {
          history.replaceState({}, '', '/iphone-pwa/checkout?inline_manual=1');
          window.state={path:'',lavaStatus:null};
          window.flow=function(){return ['card','country','plans','pay']};
          window.renderPlans=function(){return 1};
        }""")
        page.evaluate(js)
        assert page.evaluate("flow()") == ["country","plans","pay"]
        assert page.evaluate("state.path") == "manual"
        page.evaluate("state.path='lava'")
        assert page.evaluate("flow()") == ["card","country","plans","pay"]
        browser.close()


@pytest.mark.parametrize("legacy_html,selector", [
    ("<div id='rc-body'><div class='rc-done'><button class='rc-prem'>Pro</button></div></div>",
     "#rc-body .rc-done"),
    ("<div id='mk-limit'><button class='go'>Pro</button></div>",
     "#mk-limit:not([hidden])"),
])
def test_private_course_limit_shows_only_one_pwa_paywall(legacy_html,selector):
    with playwright.sync_playwright() as pw:
        browser = getattr(pw,os.getenv("PWA_E2E_ENGINE","chromium")).launch()
        page = browser.new_context(**pw.devices["iPhone 13"]).new_page()
        page.route("**/*",_serve)
        page.goto(ORIGIN + "/iphone-pwa/course")
        page.evaluate("(html) => document.getElementById('secov').innerHTML = html",legacy_html)
        page.locator("#hsk-inline-pro button.hip-plan").first.wait_for()
        # The MutationObserver removes (or hides) the legacy screen before
        # opening the single PWA paywall, instead of stacking both layers.
        assert page.locator(selector).count() == 0
        assert page.locator("#hsk-inline-pro").is_visible()
        assert page.get_by_role("heading", name="Лимит исчерпан").is_visible()
        browser.close()


def test_manual_flow_stays_in_same_pwa_modal():
    with playwright.sync_playwright() as pw:
        browser = getattr(pw,os.getenv("PWA_E2E_ENGINE","chromium")).launch()
        page = browser.new_context(**pw.devices["iPhone 13"]).new_page()
        page.route("**/*",_serve)
        page.goto(ORIGIN+"/iphone-pwa/course")
        page.evaluate("App.openPaywall('lockedLesson')")
        page.get_by_role("button",name="Другие тарифы").click()
        page.get_by_role("button",name="Обычный способ оплаты").click()
        frame=page.locator("#hsk-inline-pro iframe")
        frame.wait_for()
        assert frame.get_attribute("src").startswith("/iphone-pwa/checkout?")
        assert "inline_manual=1" in frame.get_attribute("src")
        # The embedded checkout owns its header X and bottom button; the parent
        # Back/X are not stacked on top of it.
        assert page.locator("#hsk-inline-pro .hip-back").is_hidden()
        assert page.locator("#hsk-inline-pro .hip-close").is_hidden()
        page.evaluate("HSKPwaInlinePro.closeEmbeddedCheckout(document.querySelector('#hsk-inline-pro iframe').contentWindow)")
        assert page.get_by_role("heading",name="Другие тарифы").is_visible()
        assert page.locator("#hsk-inline-pro iframe").count()==0
        browser.close()


def test_real_manual_checkout_fills_screen_with_header_x_and_bottom_button():
    """Real subscription.html in the PWA iframe, injected like the auth route."""
    inject = "".join(
        '<script src="/course_v3_data/iphone-pwa-inline-pro-bridge.js?v=e2e"></script>'
        for _ in range(1))
    checkout = (STATIC / "subscription.html").read_text("utf-8").replace("</body>", inject + "</body>", 1)

    def serve(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(status=200, body=_markup(path), content_type="text/html; charset=utf-8")
            return
        if path == "/iphone-pwa/checkout":
            route.fulfill(status=200, body=checkout, content_type="text/html; charset=utf-8")
            return
        if path == "/api/v3/pwa-auth/session":
            route.fulfill(status=200, json={"ok": True, "csrf": "testcsrf", "user_id": 1})
            return
        if path == "/api/v3/pwa/subscription/overview":
            route.fulfill(status=200, json={"ok": True, "lava": {"mode": "both", "plans": [
                {"plan_type": "1_month", "amount": "10.00", "currency": "USD"},
                {"plan_type": "12_months", "amount": "90.00", "currency": "USD"},
            ]}})
            return
        if path.startswith("/api/"):
            route.fulfill(status=200, json={"ok": True})
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
        page.set_default_timeout(10000)
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.route("**/*", serve)
        page.goto(ORIGIN + "/iphone-pwa/course")
        # Playwright has no notch: stand in for the measured iPhone insets.
        page.evaluate("HSKPwaInlinePro.safeArea=function(){return {top:47,bottom:34}}")
        page.evaluate("App.openPaywall('lockedLesson')")
        page.get_by_role("button", name="Другие тарифы").click()
        page.get_by_role("button", name="Обычный способ оплаты").click()
        frame_el = page.locator("#hsk-inline-pro iframe")
        frame_el.wait_for()
        frame = page.frame_locator("#hsk-inline-pro iframe")
        frame.locator("#nextBtn").wait_for()
        box = frame_el.bounding_box()
        vw, vh = page.viewport_size["width"], page.viewport_size["height"]
        # Edge to edge: no parent toolbar band above, no strip below.
        assert abs(box["y"]) <= 1 and abs(box["x"]) <= 1
        assert abs(box["height"] - vh) <= 1 and abs(box["width"] - vw) <= 1
        assert page.locator("#hsk-inline-pro .hip-close").is_hidden()
        assert page.locator("#hsk-inline-pro .hip-back").is_hidden()
        metrics = page.frames[1].evaluate("""() => {
            const b=document.getElementById('bottom').getBoundingClientRect();
            const x=document.getElementById('pwaCheckoutBackBtn');
            return {bottomEdge:Math.round(b.bottom), height:innerHeight,
              pad:getComputedStyle(document.getElementById('bottom')).paddingBottom,
              top:getComputedStyle(document.querySelector('.app')).paddingTop,
              x:x && !x.hidden && x.innerHTML.includes('M6 6l12 12'), label:x && x.getAttribute('aria-label')};
        }""")
        assert metrics["bottomEdge"] == metrics["height"]  # button bar sits on the bottom edge
        assert metrics["pad"] == "45px"                    # 11px + home indicator
        assert metrics["top"] == "63px"                    # 16px + status bar
        assert metrics["x"] and metrics["label"] == "Закрыть"
        # The header X leaves the regular checkout back to the Pro plans.
        frame.locator("#pwaCheckoutBackBtn").click()
        page.get_by_role("heading", name="Другие тарифы").wait_for()
        assert page.locator("#hsk-inline-pro iframe").count() == 0
        assert not errors, errors
        browser.close()

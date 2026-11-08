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
      </head><body><button id="go">Start</button>
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
        page.locator("#hsk-inline-pro .hip-back").click()
        assert page.get_by_role("heading",name="Выберите способ оплаты").is_visible()
        assert page.locator("#hsk-inline-pro iframe").count()==0
        browser.close()

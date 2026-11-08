"""Safari-safe Lava checkout: no about:blank, user opens verified provider URL."""
import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest

playwright = pytest.importorskip("playwright.sync_api")
STATIC = Path(__file__).resolve().parents[2] / "app/static"
ORIGIN = "https://hsk-lava-link-qa.invalid"


@pytest.mark.parametrize("url,expected", [
    ("https://app.lava.top/pay/demo", True),
    ("https://payments.attacker.invalid/pay/demo", False),
])
def test_lava_provider_link_is_available_only_when_invoice_has_real_url(url,expected):
    captured=[]
    def serve(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(status=200, content_type="text/html; charset=utf-8", body="""<!doctype html>
              <html lang="uz"><head><meta charset="utf-8">
              <meta name="viewport" content="width=device-width,initial-scale=1">
              <link rel="stylesheet" href="/course_v3_data/iphone-pwa-inline-pro.css?v=e2e">
              </head><body>
              <script src="/course_v3_data/iphone-pwa-inline-pro.js?v=e2e"></script>
              </body></html>""")
            return
        if path == "/api/v3/pwa-auth/session":
            route.fulfill(status=200,json={"ok":True,"csrf":"qa-csrf","user_id":1});return
        if path == "/api/v3/pwa/subscription/overview":
            route.fulfill(status=200,json={"ok":True,"lava":{
                "mode":"both","email":"buyer@example.com",
                "plans":[
                    {"plan_type":"1_month","amount":"7.90","currency":"USD"},
                    {"plan_type":"12_months","amount":"64.90","currency":"USD"},
                ]
            }});return
        if path == "/api/v3/pwa/subscription/lava/start":
            payload=json.loads(route.request.post_data)
            assert payload["plan_type"] == "1_month"
            assert payload["email"] == "buyer@example.com"
            captured.append(("start",payload))
            route.fulfill(status=200,json={
                "ok":True,"checkout_id":"11111111-1111-4111-8111-111111111111",
                "payment_url":url
            });return
        if path == "/api/v3/pwa/subscription/lava/status":
            route.fulfill(status=200,json={"ok":True,"status":"pending"});return
        if path == "/api/v3/pwa/subscription/inline-event":
            route.fulfill(status=200,json={"ok":True,"recorded":True});return
        if path.startswith("/api/"):
            route.fulfill(status=404,json={"error":"unknown"});return
        if route.request.url.startswith("https://app.lava.top/"):
            route.fulfill(status=200,body="<html><body>Provider checkout ready</body></html>",
                          content_type="text/html; charset=utf-8");return
        file=STATIC/path.lstrip("/")
        if file.is_file():
            mime,_=mimetypes.guess_type(file)
            route.fulfill(path=str(file),content_type=mime or "application/octet-stream")
            return
        route.fulfill(status=404,body="")

    with playwright.sync_playwright() as pw:
        browser=getattr(pw,os.getenv("PWA_E2E_ENGINE","chromium")).launch()
        context=browser.new_context(**pw.devices["iPhone 13"])
        page=context.new_page()
        context.route("**/*",serve)
        errors=[]; popups=[]
        page.on("pageerror",lambda exc:errors.append(str(exc)))
        page.on("popup",lambda popup:popups.append(popup))
        page.goto(ORIGIN+"/iphone-pwa/course")
        page.evaluate("HSKPwaInlinePro.open({source:'v3_locked_lesson',lang:'uz'})")
        page.get_by_role("button",name="Pro olish").wait_for()
        page.get_by_role("button",name="Pro olish").click()
        assert len(popups)==0, "No premature about:blank popup may be opened"
        if expected:
            link=page.get_by_role("link",name="To‘lovga o‘tish")
            link.wait_for()
            assert link.get_attribute("href")==url
            assert link.get_attribute("target")=="_blank"
            assert "noopener" in link.get_attribute("rel")
            with page.expect_popup() as opened:
                link.click()
            popup=opened.value
            popup.wait_for_load_state()
            assert popup.url==url
            assert "Provider checkout ready" in popup.locator("body").inner_text()
            # The learner sees a neutral payment step, never the provider name.
            assert "lava" not in page.locator("#hsk-inline-pro").inner_text().lower()
            assert page.locator("#hsk-inline-pro .hip-checking").is_visible()
        else:
            assert page.get_by_role("link",name="To‘lovga o‘tish").count()==0
            page.locator("#hsk-inline-pro .hip-error").wait_for(state="visible")
            assert page.locator("#hsk-inline-pro .hip-error").is_visible()
        assert len(captured)==1
        assert not errors, errors
        browser.close()

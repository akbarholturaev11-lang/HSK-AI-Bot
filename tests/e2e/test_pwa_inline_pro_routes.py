"""PWA inline Pro opens at each authenticated limit entry point.

Synthetic pages focus on the runtime bridge contract. Full PWA/Telegram
HTML remains separately source-guarded; real iOS payments require device QA.
"""
import json
import ast
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest

playwright = pytest.importorskip("playwright.sync_api")
STATIC = Path(__file__).resolve().parents[2] / "app/static"
ORIGIN = "https://inline-route-qa.invalid"
PRACTICES = ("voice", "recognition", "memorize", "pronunciation", "test", "mistakes")


def _regional_overview():
    return {"ok": True, "mode": "subscription", "language": "ru", "analytics_user_id": 1,
            "prices": {"visa": {plan: {"base_amount": 10, "final_amount": 10, "currency": "TJS"}
                                for plan in ["1_month", "10_days", "3_months"]}},
            "lava": {"mode": "both", "currency": "USD", "plans": [
                {"plan_type": "1_month", "amount": "10.00", "currency": "USD"},
                {"plan_type": "12_months", "amount": "90.00", "currency": "USD"},
                {"plan_type": "3_months", "amount": "27.00", "currency": "USD"},
            ]}}


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
      <script src="/course_v3_data/hsk-miniapp-i18n.js?v=qa"></script>
                <script src="/course_v3_data/hsk-course-i18n.js?v=qa"></script>
                <script src="/course_v3_data/hsk-subscription-presentation.js?v=e2e"></script>
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
        route.fulfill(status=200, json=_regional_overview())
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


@pytest.mark.parametrize('lang',['uz','ru','tj'])
@pytest.mark.parametrize('pathname,filename',[
    ('/iphone-pwa/course','course-v3.html'),
    ('/iphone-pwa/practice/recognition','course_v3_recognition.html'),
])
def test_real_learner_documents_keep_named_country_and_visible_other_plans(lang,pathname,filename):
    # Use the real learner document and exactly the route's inline module tags.
    # The backend renderer separately proves catalog pinning/old-tag rollover.
    api_source=(STATIC.parents[1]/'app/api/pwa_auth.py').read_text()
    tree=ast.parse(api_source)
    injection=next(ast.literal_eval(node.value.func.value) for node in tree.body
                   if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name)
                   and target.id=='_PWA_INLINE_PRO_HTML' for target in node.targets))
    html=(STATIC/filename).read_text().replace('</body>',
        '<script src="/course_v3_data/hsk-subscription-presentation.js?v=qa"></script>'
        +injection+'</body>')
    messages=json.loads((STATIC.parents[1]/f'localization/ui/{lang}/miniapp.json').read_text())['messages']
    more=messages['ui.subscription.regional.more']
    with playwright.sync_playwright() as pw:
        browser=getattr(pw,os.getenv('PWA_E2E_ENGINE','chromium')).launch()
        context=browser.new_context(**pw.devices['iPhone 13'])
        page=context.new_page();errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        def serve(route):
            if urlsplit(route.request.url).path==pathname:
                route.fulfill(body=html,content_type='text/html; charset=utf-8')
            else:_serve(route)
        context.route('**/*',serve)
        page.goto(ORIGIN+pathname,wait_until='domcontentloaded')
        page.evaluate('(lang)=>HSKPwaInlinePro.open({source:"v3_locked_lesson",lang})',lang)
        other=page.get_by_role('button',name=more,exact=True)
        other.wait_for(state='visible')
        box=other.bounding_box()
        assert box and box['y']>=0 and box['y']+box['height']<=page.viewport_size['height']
        select=page.locator('#hsk-inline-pro .hip-region')
        for country in ['tj','uz','ru','cn','other']:
            assert messages['ui.subscription.regional.'+country] in select.locator('option[value="'+country+'"]').inner_text()
        other.click()
        page.get_by_role('heading',name=more,exact=True).wait_for()
        assert page.locator('#hsk-inline-pro .hip-plan').count()==3
        assert not errors,errors
        browser.close()


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
          history.replaceState({}, '', '/iphone-pwa/checkout?inline_manual=1&plan=1_month');
          window.state={path:'',lavaStatus:null};
          window.flow=function(){return ['card','country','plans','pay']};
          window.renderPlans=function(){return 1};
        }""")
        page.evaluate(js)
        assert page.evaluate("flow()") == ["country","plans","pay"]
        assert page.evaluate("state.path") == "manual"
        page.evaluate("state.mode='subscription';state.plan='1_month';state.overview={checkout_allowed:true};window.hasCurrentPrice=()=>true")
        assert page.evaluate("flow()") == ["country","pay"]
        for guard in ["state.pending=true", "state.offerExpired=true", "state.overview.checkout_allowed=false", "state.mode='hsk30_unlock'", "state.plan='3_months'", "window.hasCurrentPrice=()=>false"]:
            page.evaluate("state.pending=false;state.offerExpired=false;state.overview.checkout_allowed=true;state.mode='subscription';state.plan='1_month';window.hasCurrentPrice=()=>true")
            page.evaluate(guard)
            assert page.evaluate("flow()") == ["country","plans","pay"], guard
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
        page.locator('#hsk-inline-pro .hip-region').select_option('tj')
        assert page.get_by_role("button",name="Другие тарифы").is_visible()
        page.locator('#hsk-inline-pro .hip-primary').click()
        frame=page.locator("#hsk-inline-pro iframe")
        frame.wait_for()
        assert frame.get_attribute("src").startswith("/iphone-pwa/checkout?")
        assert "inline_manual=1" in frame.get_attribute("src")
        # The embedded checkout owns its header X and bottom button; the parent
        # Back/X are not stacked on top of it.
        assert page.locator("#hsk-inline-pro .hip-back").is_hidden()
        assert page.locator("#hsk-inline-pro .hip-close").is_hidden()
        page.evaluate("HSKPwaInlinePro.closeEmbeddedCheckout(document.querySelector('#hsk-inline-pro iframe').contentWindow)")
        assert page.get_by_role("heading",name="Лимит исчерпан").is_visible()
        assert page.locator('#hsk-inline-pro .hip-region').input_value() == 'tj'
        assert page.locator("#hsk-inline-pro iframe").count()==0
        browser.close()


@pytest.mark.parametrize("selected_plan", ["1_month", "3_months"])
def test_real_manual_checkout_fills_screen_with_header_x_and_bottom_button(selected_plan):
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
            route.fulfill(status=200, json=_regional_overview())
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
        page.locator('#hsk-inline-pro .hip-region').select_option('tj')
        assert page.get_by_role("button", name="Другие тарифы").is_visible()
        if selected_plan == "3_months":
            page.get_by_role("button", name="Другие тарифы").click()
            page.locator('#hsk-inline-pro .hip-plan[data-plan="3_months"]').click()
        page.locator('#hsk-inline-pro .hip-primary').click()
        frame_el = page.locator("#hsk-inline-pro iframe")
        frame_el.wait_for()
        frame = page.frame_locator("#hsk-inline-pro iframe")
        frame.locator('[data-screen="method"].active').wait_for()
        assert not frame.locator('[data-screen="plans"]').is_visible()
        assert page.frames[1].evaluate("state.plan") == selected_plan
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
        page.get_by_role("heading", name="Другие тарифы" if selected_plan == "3_months" else "Лимит исчерпан").wait_for()
        assert page.locator("#hsk-inline-pro iframe").count() == 0
        assert not errors, errors
        browser.close()


@pytest.mark.parametrize("pwa, saved_email", [
    (True, "receipt@example.com"),
    (False, "learner@example.com"),
    (True, None),
])
def test_shared_checkout_only_prompts_when_email_is_missing(pwa, saved_email):
    starts = []
    prefix = "/api/v3/pwa/subscription" if pwa else "/api/subscription-miniapp"
    checkout_path = "/iphone-pwa/checkout" if pwa else "/subscription.html"
    checkout_file = STATIC / "subscription.html"

    def serve(route):
        path = urlsplit(route.request.url).path
        if path == checkout_path:
            route.fulfill(path=str(checkout_file), content_type="text/html; charset=utf-8")
        elif path == "/api/v3/pwa-auth/session":
            route.fulfill(json={"ok": True, "csrf": "synthetic", "user_id": 7})
        elif path == prefix + "/overview":
            route.fulfill(json={"ok": True, "language": "ru", "mode": "subscription", "lava": {
                "mode": "lava_only", "currency": "USD", "email": saved_email,
                "plans": [{"plan_type": "1_month", "amount": "10.00", "currency": "USD"}],
            }})
        elif path == prefix + "/lava/start":
            starts.append(json.loads(route.request.post_data or "{}"))
            route.fulfill(json={"ok": True, "checkout_id": 81, "payment_url": "https://app.lava.top/test"})
        elif path == prefix + "/lava/status":
            route.fulfill(json={"ok": True, "status": "pending"})
        elif path.startswith("/api/"):
            route.fulfill(json={"ok": True})
        else:
            _serve(route)

    with playwright.sync_playwright() as pw:
        browser = getattr(pw, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        page = browser.new_context(**pw.devices["iPhone 13"]).new_page()
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.route("**/*", serve)
        page.add_init_script("window.open=()=>null")
        suffix = "" if pwa else "#tgWebAppData=synthetic-telegram-init-data"
        page.goto(ORIGIN + checkout_path + "?lang=ru" + suffix)
        page.locator("#lavaPlans [data-lava-plan='1_month']").wait_for()
        page.locator("#nextBtn").click()
        if saved_email is None:
            assert not starts
            page.locator("#lavaEmail").fill("first@example.com")
            page.locator("#nextBtn").click()
        page.locator('[data-screen="lavaWait"].active').wait_for()
        assert not page.locator("#lavaEmail").is_visible()
        assert [row["email"] for row in starts] == [saved_email or "first@example.com"]
        assert not errors
        browser.close()


@pytest.mark.parametrize('saved_email', [None, 'saved@example.com'])
@pytest.mark.parametrize('from_more', [False, True])
def test_limit_selected_lava_plan_goes_to_email_or_invoice_without_reopening_limit(saved_email, from_more):
    starts = []
    reads = []
    def serve(route):
        path = urlsplit(route.request.url).path
        if path == '/api/v3/pwa/subscription/overview':
            reads.append(path)
            data = _regional_overview()
            data['lava']['email'] = saved_email
            route.fulfill(json=data)
        elif path == '/api/v3/pwa/subscription/lava/start':
            starts.append(json.loads(route.request.post_data or '{}'))
            route.fulfill(json={'ok': True, 'checkout_id': 81, 'payment_url': 'https://app.lava.top/fixture-invoice'})
        elif path == '/api/v3/pwa/subscription/lava/status':
            route.fulfill(json={'ok': True, 'status': 'pending'})
        else:
            _serve(route)
    with playwright.sync_playwright() as pw:
        browser = getattr(pw, os.getenv('PWA_E2E_ENGINE', 'chromium')).launch()
        page = browser.new_context(**pw.devices['iPhone 13']).new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.route('**/*', serve)
        page.add_init_script('window.open=()=>null')
        page.goto(ORIGIN + '/iphone-pwa/course')
        page.evaluate("App.openPaywall('lockedLesson')")
        plan = '3_months' if from_more else '1_month'
        if from_more:
            page.get_by_role('button', name='Другие тарифы').click()
        page.locator('#hsk-inline-pro .hip-plan[data-plan="' + plan + '"]').click()
        page.locator('#hsk-inline-pro .hip-actions .hip-primary').click()
        if saved_email is None:
            page.locator('#hsk-inline-pro[data-screen="email"] input[type=email]').wait_for()
            assert not starts
            assert page.locator('#hsk-inline-pro .hip-plan').count() == 0
            page.locator('#hsk-inline-pro input[type=email]').fill('new@example.com')
            page.locator('#hsk-inline-pro .hip-body .hip-primary').click()
        page.locator('#hsk-inline-pro[data-screen="waiting"]').wait_for()
        assert page.locator('#hsk-inline-pro input[type=email],#hsk-inline-pro .hip-plan').count() == 0
        assert page.locator('#hsk-inline-pro a.hip-primary').get_attribute('href') == 'https://app.lava.top/fixture-invoice'
        assert len(reads) == 1 and len(starts) == 1
        assert starts[0]['plan_type'] == plan
        assert starts[0]['email'] == (saved_email or 'new@example.com')
        assert starts[0]['attempt_id']
        assert not errors, errors
        browser.close()

"""Real Chromium presentation checks for the original iPhone PWA overlay modules.

This fixture serves the actual shipped CSS/JS and generated UZ/RU/TJ catalogs.
Only authenticated API responses are synthetic: it never exercises production
billing, grants access, or replaces the original Mini App in a browser.
"""
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright_api.sync_playwright

ROOT = Path(__file__).resolve().parents[2] / "app" / "static"
BASE = "https://hsk-pwa-qa.invalid"
PAGE = BASE + "/iphone-pwa/course"


def asset(path):
    return (ROOT / path).read_text(encoding="utf-8")


def bootstrap(page, *, notices=None, account=None, release=None, ordinary=None):
    """Install real stylesheet, catalogs and both shipping browser modules."""
    notices = notices if notices is not None else [
        {"id": 11, "title": "Dars tayyor", "body": "HSK 3", "action": "course",
         "created_at": "2026-11-03T12:00:00+00:00"},
    ]
    account = account if account is not None else {
        "ok": True, "notices": [
            {"id": 4, "title": "Hisob xabari", "body": "Qabul qilindi", "action": "course",
             "created_at": "2026-11-03T13:00:00+00:00"},
        ], "payment_reviews": [
            {"payment_id": 40, "status": "approved", "plan_type": "1_month"},
            {"payment_id": 41, "status": "rejected", "plan_type": "1_month"},
        ], "payment_action": None,
    }
    release = release or []
    posts = []

    def intercept(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(
                content_type="text/html",
                body='<!doctype html><html class="hsk-pwa-browser" lang="uz"><head>'
                     '<meta name="viewport" content="width=device-width,initial-scale=1">'
                     '</head><body style="margin:0;min-height:100dvh;background:var(--hsk-paper)">'
                     '<div class="nav" style="position:fixed;bottom:12px;height:72px;width:calc(100% - 24px)"></div>'
                     '<main style="padding:24px 16px"><h1>HSK AI</h1>'
                     '<div class="row-card">HSK 3</div></main></body></html>',
            )
        elif path == "/api/v3/pwa-auth/session":
            route.fulfill(content_type="application/json", body=json.dumps({
                "ok": True, "user_id": 7, "csrf": "browser-csrf",
            }))
        elif path == "/api/v3/pwa/notifications":
            route.fulfill(content_type="application/json", body=json.dumps({
                "ok": True, "notifications": notices,
            }))
        elif path == "/api/v3/pwa/account-notices":
            route.fulfill(content_type="application/json", body=json.dumps(account))
        elif path == "/api/v3/pwa/feedback/available":
            route.fulfill(content_type="application/json", body=json.dumps({
                "ok": True, "release": release, "ordinary": ordinary,
            }))
        elif path == "/api/v3/pwa/feedback/ordinary/prepare":
            route.fulfill(content_type="application/json", body=json.dumps({
                "ok": True, "ordinary": None,
            }))
        elif path == "/api/v3/pwa/feedback/lesson/prepare":
            route.fulfill(content_type="application/json", body=json.dumps({
                "ok": True, "ordinary": ordinary,
            }))
        elif path == "/api/v3/pwa/feedback/ordinary/submit":
            posts.append({
                "headers": route.request.headers,
                "body": json.loads(route.request.post_data),
            })
            route.fulfill(content_type="application/json", body=json.dumps({
                "ok": True, "completed": True,
            }))
        elif path == "/api/v3/pwa/feedback/release/respond":
            posts.append({
                "headers": route.request.headers,
                "body": json.loads(route.request.post_data),
            })
            route.fulfill(content_type="application/json", body=json.dumps({
                "ok": True, "response_id": 31, "discount_campaign_id": None,
                "trial_until": None,
            }))
        else:
            route.fulfill(status=404, content_type="text/plain", body="unsupported synthetic API")

    page.route("**/*", intercept)
    page.goto(PAGE, wait_until="domcontentloaded")
    page.add_style_tag(content=asset("course_v3_data/design-tokens.css"))
    page.add_style_tag(content=asset("course_v3_data/iphone-pwa-glass.css"))
    page.add_script_tag(content=asset("course_v3_data/hsk-common-i18n.js"))
    page.add_script_tag(content=asset("course_v3_data/hsk-course-i18n.js"))
    page.evaluate("""() => {
      window.LANG = 'uz';
      window.pwaCourseActor = async () => ({user_id:7, csrf:'browser-csrf'});
      window.courseMessage = (key, fallback = '') =>
        (window.HSKAI_COURSE_I18N?.uz || {})[key] || fallback;
      window.commonMessage = (key, fallback = '') =>
        (window.HSKAI_COMMON_I18N?.uz || {})[key] || fallback;
      window.App = {show: (screen) => {window.__lastScreen = screen;}};
    }""")
    page.add_script_tag(content=asset("course_v3_data/iphone-pwa-notices.js"))
    page.add_script_tag(content=asset("course_v3_data/iphone-pwa-feedback.js"))
    return posts


@pytest.mark.parametrize("width,height", [(320, 568), (390, 844), (430, 932)])
def test_real_browser_inbox_is_one_full_screen_feed(width, height):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=2, is_mobile=True, has_touch=True,
        )
        page = context.new_page()
        bootstrap(page)
        page.evaluate("window.HskPwaInbox.open()")
        dialog = page.locator("#hsk-pwa-notice-root .hsk-pwa-notice-card")
        assert dialog.is_visible()
        rows = page.locator("#hsk-pwa-notice-list .hsk-pwa-notice-row")
        assert rows.count() == 4
        assert rows.first.get_by_text("Hisob xabari").is_visible()
        assert rows.nth(1).get_by_text("Dars tayyor").is_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        box = dialog.bounding_box()
        assert box and box["x"] == box["y"] == 0
        assert box["width"] == width
        assert box["height"] == page.evaluate("innerHeight")
        assert page.get_by_role("tab").count() == 0
        assert page.locator("#hsk-pwa-notice-list").get_attribute("role") == "region"
        assert page.locator('[data-payment-status="approved"]').evaluate(
            "node => node.classList.contains('is-approved')"
        )
        assert page.locator('[data-payment-status="rejected"]').evaluate(
            "node => node.classList.contains('is-rejected')"
        )
        page.locator(".hsk-pwa-close").click()
        assert not page.locator("#hsk-pwa-notice-root").is_visible()
        context.close()
        browser.close()



def test_browser_qa_profiler_collects_only_coarse_tab_timing():
    """The optional profiler observes real Chromium paint, never account data."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width":390, "height":844})
        bootstrap(page)
        page.add_script_tag(content=asset("course_v3_data/iphone-pwa-perf.js"))
        page.evaluate("window.App.show('rating')")
        page.wait_for_function(
            "window.HskPwaPerf && window.HskPwaPerf.snapshot().samples.some(x => x.kind === 'tab-paint')"
        )
        report = page.evaluate("window.HskPwaPerf.snapshot()")
        assert report["samples"]
        assert any(x["name"] == "rating" and x["kind"] == "tab-paint" for x in report["samples"])
        assert all("user_id" not in str(item) and "initData" not in str(item)
                   for item in report["samples"])
        browser.close()



def test_iphone_share_uses_public_referral_link_not_telegram_identity():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        bootstrap(page)
        page.evaluate("""() => {
          window.App.openSheet = html => {window.__inviteHtml = html;};
        }""")
        page.add_script_tag(content=asset("course_v3_data/iphone-pwa-invite.js"))
        page.evaluate("""() => window.HskPwaInvite.open({
          link: 'https://hskai.app/apps?ref=abcd1234&mode=trial',
          joined_count: 3, active_count: 1, required: 5
        })""")
        html = page.evaluate("window.__inviteHtml")
        assert "hskai.app/apps?ref=abcd1234" in html
        assert "Telegram" not in html
        assert "telegram_id" not in html
        assert "window.HskPwaInvite.share()" in html
        browser.close()


def test_pwa_read_only_avatar_has_no_telegram_edit_affordance():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width":390, "height":844},is_mobile=True)
        bootstrap(page)
        page.evaluate("""() => {
          const div=document.createElement('div');
          div.className='phero';
          div.innerHTML='<div class="pav"><span class="ed">Edit</span></div>';
          document.body.appendChild(div);
        }""")
        assert page.locator(".phero .pav .ed").evaluate(
            "el=>getComputedStyle(el).display"
        ) == "none"
        assert page.locator(".phero .pav").evaluate(
            "el=>getComputedStyle(el).pointerEvents"
        ) == "none"
        browser.close()

def test_rejected_receipt_centered_with_original_locale_and_one_action():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2, is_mobile=True, has_touch=True,
        )
        bootstrap(page, account={
            "ok": True, "notices": [], "payment_action": {
                "payment_id": 42, "status": "rejected", "plan_type": "1_month",
                "reviewed_at": "2026-11-03T13:00:00+00:00",
            },
        })
        page.evaluate("window.dispatchEvent(new Event('load'))")
        dialog = page.locator("#hsk-pwa-notice-root .hsk-pwa-notice-card")
        dialog.wait_for(state="visible", timeout=7000)
        title = page.locator("#hsk-pwa-urgent-title")
        assert title.inner_text() == page.evaluate(
            "window.HSKAI_COURSE_I18N.uz['subscriptionPage.proRejectedTitle']"
        )
        assert page.locator("[data-pwa-retry]").is_visible()
        assert not page.locator("#hsk-pwa-notice-list").is_visible()
        box = dialog.bounding_box()
        assert box and box["x"] > 0 and box["y"] > 0
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        browser.close()


def test_feedback_is_lesson_contextual_and_uses_csrf():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2, is_mobile=True, has_touch=True,
        )
        ordinary = {
            "feedback_id": 71,
            "paid": False,
            "choices": {
                "liked": [{"code": "course", "label": "Kurs"}],
                "liked_sub": {},
                "disliked": [{"code": "price", "label": "Narx"}],
                "disliked_detail_required": [],
            },
        }
        posts = bootstrap(page, ordinary=ordinary)
        page.evaluate("window.HskPwaFeedback.open()")
        assert not page.locator("#hsk-pwa-feedback-root").is_visible(), (
            "feedback without a confirmed completed lesson stays closed"
        )
        page.evaluate("window.HskPwaFeedback.open({confirmed:true,lessonId:3,level:'hsk1'})")
        dialog = page.locator("#hsk-pwa-feedback-root .hsk-pwa-feedback-card")
        assert dialog.is_visible()
        assert "3-dars" in page.locator("#hsk-pwa-feedback-title").inner_text()
        assert "Hozirgina tugatgan darsingiz" in page.locator("#hsk-pwa-feedback-context").inner_text()
        # Feedback uses accessible radio buttons, not legacy <select> controls.
        page.locator('#hsk-pwa-feedback-form [data-mark="👍"] [data-code="course"]').click()
        page.locator('#hsk-pwa-feedback-form [data-mark="👎"] [data-code="price"]').click()
        page.locator("#hsk-pwa-feedback-submit").click()
        page.wait_for_function(
            "document.querySelector('#hsk-pwa-feedback-submit').hidden === true"
        )
        assert len(posts) == 1
        assert posts[0]["headers"].get("x-hsk-pwa-csrf") == "browser-csrf"
        assert posts[0]["body"] == {
            "feedback_id": 71, "liked_code": "course", "liked_sub_code": None,
            "liked_other_text": None, "disliked_code": "price", "disliked_detail_text": None,
        }
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        browser.close()


@pytest.mark.parametrize("status,ordinary", [
    (200, None),
    (409, None),
    (200, {"feedback_id": 80, "paid": False, "choices": {}}),
    (200, {"feedback_id": 80, "paid": False, "choices": {
        "liked": [{"code": "course", "label": "Kurs"}],
        "disliked": [{"code": "price", "label": "Narx"}],
    }}),
])
def test_post_lesson_feedback_waits_for_valid_form_and_current_screen(status, ordinary):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        bootstrap(page)
        pending = []
        page.route("**/api/v3/pwa/feedback/lesson/prepare", lambda route: pending.append(route))
        page.locator("main").evaluate("""node => {
            node.tabIndex = -1;
            node.focus();
        }""")
        with page.expect_request("**/api/v3/pwa/feedback/lesson/prepare"):
            page.evaluate("""() => {
                window.feedbackContextCurrent = true;
                window.feedbackPending = window.HskPwaFeedback.open({
                    confirmed: true, lessonId: 3, level: "hsk1",
                    canOpen: () => window.feedbackContextCurrent,
                });
            }""")
        root = page.locator("#hsk-pwa-feedback-root")
        assert not root.is_visible()
        assert page.locator("main").evaluate("node => document.activeElement === node")
        if ordinary and ordinary.get("choices"):
            # A valid response arriving after the learner moved away stays silent.
            page.evaluate("window.feedbackContextCurrent = false")
        pending[0].fulfill(status=status, json={"ok": status == 200, "ordinary": ordinary})
        page.evaluate("window.feedbackPending")
        assert not root.is_visible()
        assert page.locator("main").evaluate("node => document.activeElement === node")
        browser.close()


def test_rejected_payment_never_interrupts_feedback():
    """The important receipt cannot steal focus from a visible feedback dialog."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            viewport={"width": 320, "height": 568},
            device_scale_factor=2, is_mobile=True, has_touch=True,
        )
        bootstrap(
            page,
            account={"ok": True, "notices": [], "payment_action": {
                "payment_id": 91,
                "status": "rejected",
                "plan_type": "1_month",
                "reviewed_at": "2026-11-03T13:00:00+00:00",
            }},
            ordinary={
                "feedback_id": 72,
                "paid": False,
                "choices": {
                    "liked": [{"code": "course", "label": "Kurs"}],
                    "liked_sub": {},
                    "disliked": [{"code": "other", "label": "Boshqa"}],
                    "disliked_detail_required": ["other"],
                },
            },
        )
        page.evaluate("window.HskPwaFeedback.open({confirmed:true,lessonId:3,level:'hsk1'})")
        card = page.locator("#hsk-pwa-feedback-root .hsk-pwa-feedback-card")
        assert card.is_visible()
        page.locator('#hsk-pwa-feedback-form [data-mark="👎"] [data-code="other"]').click()
        page.locator(".hsk-pwa-feedback-field textarea").focus()
        page.evaluate("window.dispatchEvent(new Event('load'))")
        page.wait_for_timeout(2300)
        assert card.is_visible()
        assert not page.locator("#hsk-pwa-notice-root").is_visible()
        assert page.evaluate(
            "document.activeElement === document.querySelector('#hsk-pwa-feedback-root textarea')"
        ), "payment recheck must not take keyboard focus"
        page.locator(".hsk-pwa-feedback-close").click()
        page.wait_for_timeout(1400)
        assert not page.locator("#hsk-pwa-notice-root").is_visible(), (
            "closing feedback must not reveal a queued surprise payment dialog"
        )
        browser.close()


@pytest.mark.parametrize("width,height", [(320, 568), (390, 844), (430, 932)])
def test_shake_report_is_single_bottom_sheet_with_direct_permission_and_csrf(width, height):
    """Exercise the actual PWA JS/CSS in Chromium, not only string/gesture contracts."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": height},
            device_scale_factor=2, is_mobile=True, has_touch=True,
        )
        bootstrap(page)
        page.add_style_tag(content=asset("course_v3_data/iphone-pwa-shake-report.css"))
        page.evaluate("""() => {
          Object.defineProperty(navigator, "standalone", {configurable:true,value:true});
          window.__motionRequests = 0;
          Object.defineProperty(window, "DeviceMotionEvent", {
            configurable:true,
            value:class MotionEventMock {}
          });
          window.DeviceMotionEvent.requestPermission = () => {
            window.__motionRequests++;
            return Promise.resolve("granted");
          };
          window.SCREEN = "settings";
          window.__settingsRefreshes = 0;
          window.renderPwaSettings = () => {window.__settingsRefreshes++};
        }""")
        page.add_script_tag(content=asset("course_v3_data/iphone-pwa-shake-report.js"))
        page.evaluate("window.dispatchEvent(new Event('load'))")
        page.wait_for_function(
            "window.HskPwaShake && window.HskPwaShake.settingsRowHtml().includes('role=\"switch\"')"
        )
        report = page.locator("#hsk-pwa-shake-root")
        assert not report.is_visible(), "first use cannot open an unsolicited consent dialog"
        page.evaluate("""() => {
          const host = document.createElement("div");
          host.id = "shake-toggle-fixture";
          host.innerHTML = window.HskPwaShake.settingsRowHtml();
          document.body.appendChild(host);
        }""")
        setting = page.locator("#shake-toggle-fixture [role='switch']")
        assert setting.count() == 1
        assert setting.get_attribute("aria-checked") == "false"
        setting.click()
        assert page.evaluate("window.__motionRequests") == 1
        assert page.evaluate("window.__settingsRefreshes") >= 1
        assert "aria-checked=\"true\"" in page.evaluate("window.HskPwaShake.settingsRowHtml()")
        assert not report.is_visible(), "granting sensor permission must not open extra app modals"
        # Use the public test hook to trigger the same end-form code path as a real shake.
        page.evaluate("window.HskPwaShake.manual()")
        sheet = page.locator("#hsk-pwa-shake-root .hsk-shake-dialog")
        assert sheet.is_visible()
        assert sheet.get_attribute("data-stage") == "form"
        assert page.evaluate("window.HskPwaShake.backTarget() !== null")
        assert page.locator("#hsk-shake-description").is_visible()
        assert page.locator("#hsk-shake-actions button").count() == 1
        assert page.locator("#hsk-shake-close").count() == 1
        # Wait for the intentional 250ms bottom-up entrance animation to finish;
        # otherwise the first paint is deliberately translated +28px offscreen.
        page.wait_for_function("""() => {
          const sheet = document.querySelector('#hsk-pwa-shake-root .hsk-shake-dialog');
          return sheet && sheet.getAnimations().every(a => a.playState === 'finished');
        }""")
        box = sheet.bounding_box()
        assert box and box["height"] < height * .9
        assert abs(box["y"] + box["height"] - height) <= 2, "sheet must dock to the bottom"
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        posts = []
        def report_post(route):
            posts.append({
                "headers": route.request.headers,
                "body": json.loads(route.request.post_data),
            })
            route.fulfill(content_type="application/json", body='{"ok":true}')
        page.route("**/api/v3/pwa/bug-report", report_post)
        page.locator("#hsk-shake-description").fill("Dars ochilmay qolyapti")
        page.locator("#hsk-shake-actions button").click()
        page.wait_for_function(
            "document.querySelector('.hsk-shake-dialog')?.dataset.stage === 'sent'"
        )
        assert len(posts) == 1
        assert posts[0]["headers"].get("x-hsk-pwa-csrf") == "browser-csrf"
        assert posts[0]["body"]["description"] == "Dars ochilmay qolyapti"
        assert posts[0]["body"]["app_version"] == "iphone-pwa"
        assert page.locator("#hsk-shake-close").is_hidden(), "success has one Done action"
        assert page.locator("#hsk-shake-actions button").count() == 1
        page.locator("#hsk-shake-actions button").click()
        assert not report.is_visible()
        assert page.evaluate("window.HskPwaShake.backTarget() === null")
        page.evaluate("window.HskPwaShake.toggle()")
        assert not page.evaluate("window.HskPwaShake.isListening()")
        browser.close()


def test_shake_report_never_captures_embedded_checkout_even_after_async_renderer():
    """Top-level installed PWA checkout iframe may contain receipts/financial data."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            viewport={"width": 390, "height": 844},
            is_mobile=True, has_touch=True,
        )
        bootstrap(page)
        page.add_style_tag(content=asset("course_v3_data/iphone-pwa-shake-report.css"))
        page.evaluate("""() => {
          Object.defineProperty(navigator, 'standalone', {configurable:true,value:true});
          window.__captureCalls = 0;
          window.html2canvas = () => { window.__captureCalls++; throw Error('Must not run on checkout'); };
        }""")
        page.add_script_tag(content=asset("course_v3_data/iphone-pwa-shake-report.js"))
        page.evaluate("window.dispatchEvent(new Event('load'))")
        page.wait_for_function("window.HskPwaShake && window.HskPwaShake.settingsRowHtml().includes('role=\"switch\"')")
        # Same JavaScript turn: renderer is already available, but viewport privacy
        # must be checked again after the await before screenshot materializes.
        page.evaluate("""() => {
          window.HskPwaShake.manual();
          let layer = document.createElement('section');
          layer.id = 'pwa-checkout-layer';
          layer.innerHTML = '<iframe title="Checkout"></iframe>';
          document.body.appendChild(layer);
        }""")
        page.wait_for_function(
            "document.querySelector('#hsk-pwa-shake-root .hsk-shake-preview')?.textContent.includes('rasm')"
        )
        assert page.evaluate("window.__captureCalls") == 0
        assert page.locator("#hsk-shake-attach").count() == 0
        posts = []
        def accept_report(route):
            posts.append(json.loads(route.request.post_data))
            route.fulfill(content_type="application/json", body='{"ok":true}')
        page.route("**/api/v3/pwa/bug-report", accept_report)
        page.locator("#hsk-shake-description").fill("Obuna sahifasida muammo bor")
        page.locator("#hsk-shake-actions button").click()
        page.wait_for_function(
            "document.querySelector('.hsk-shake-dialog')?.dataset.stage === 'sent'"
        )
        assert len(posts) == 1
        assert posts[0]["screenshot_data_url"] == ""
        browser.close()


@pytest.mark.parametrize("width,height", [(320, 568), (390, 844), (430, 932)])
def test_embedded_checkout_cta_uses_exactly_one_bottom_safe_area(width, height):
    """Render the actual parent + checkout inline CSS in nested Chromium frames."""
    course_html = asset("course-v3.html")
    checkout_html = asset("subscription.html")
    course_css = re.search(r"<style>([\s\S]*?)</style>", course_html).group(1)
    checkout_css = re.search(r"<style>([\s\S]*?)</style>", checkout_html).group(1)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            viewport={"width":width,"height":height},
            device_scale_factor=2, is_mobile=True, has_touch=True,
        )
        page.set_content(
            '<!doctype html><html class="hsk-pwa-browser"><head>'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<style>' + course_css + '</style></head><body>'
            '<section id="pwa-checkout-layer">'
            '<iframe name="checkout" title="HSK AI Pro"></iframe>'
            '</section></body></html>'
        )
        layer = page.locator("#pwa-checkout-layer")
        assert layer.evaluate(
            "node => getComputedStyle(node).paddingBottom"
        ) == "0px", "parent checkout must not consume home-indicator space twice"
        parent_frame = page.frame(name="checkout")
        assert parent_frame is not None
        parent_frame.set_content(
            '<!doctype html><html class="hsk-pwa-browser"><head>'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<style>' + checkout_css + '</style></head><body>'
            '<main class="app"><section class="screen">HSK AI Pro</section></main>'
            '<footer class="bottom" id="bottom">'
            '<div class="bottom-inner">'
            '<button id="backBtn" class="back hide"></button>'
            '<button id="nextBtn" class="cta">Continue</button>'
            '</div></footer></body></html>'
        )
        button = parent_frame.locator("#nextBtn")
        box = button.bounding_box()
        assert box is not None
        bottom_gap = height - (box["y"] + box["height"])
        assert 28 <= bottom_gap <= 34, f"CTA should clear the home gesture area once: {bottom_gap}"
        assert box["x"] >= 0 and box["x"] + box["width"] <= width
        assert box["height"] >= 50
        browser.close()

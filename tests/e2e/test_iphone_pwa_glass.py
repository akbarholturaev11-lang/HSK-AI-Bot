"""Real Chromium presentation checks for the original iPhone PWA overlay modules.

This fixture serves the actual shipped CSS/JS and generated UZ/RU/TJ catalogs.
Only authenticated API responses are synthetic: it never exercises production
billing, grants access, or replaces the original Mini App in a browser.
"""
import json
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
        {"id": 11, "title": "Dars tayyor", "body": "HSK 3", "action": "course"},
    ]
    account = account if account is not None else {
        "ok": True, "notices": [
            {"id": 4, "title": "Hisob xabari", "body": "Qabul qilindi", "action": "course"},
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
def test_real_browser_inbox_glass_and_safe_width(width, height):
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
        assert page.locator("#hsk-pwa-notice-list .hsk-pwa-notice-row").count() == 1
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        box = dialog.bounding_box()
        assert box and abs(box["x"] + box["width"] / 2 - width / 2) < 3
        assert box["x"] >= 0 and box["x"] + box["width"] <= width + 1
        blur = dialog.evaluate(
            "(node) => getComputedStyle(node).backdropFilter || "
            "getComputedStyle(node).webkitBackdropFilter"
        )
        assert "blur(" in blur, "actual optical glass not applied"
        page.locator('[data-pwa-tab="account"]').click()
        assert page.get_by_text("Hisob xabari").is_visible()
        page.locator(".hsk-pwa-close").click()
        assert not page.locator("#hsk-pwa-notice-root").is_visible()
        context.close()
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
        assert not page.locator(".hsk-pwa-notice-tabs").is_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        browser.close()


def test_release_feedback_low_rating_requires_comment_and_csrf():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2, is_mobile=True, has_touch=True,
        )
        posts = bootstrap(page, release=[{
            "campaign_id": 19,
            "title": "Yangi kurs versiyasi",
            "message_text": "Yangi darslarni sinab ko'ring",
        }])
        page.evaluate("window.HskPwaFeedback.open()")
        dialog = page.locator("#hsk-pwa-feedback-root .hsk-pwa-feedback-card")
        assert dialog.is_visible()
        assert page.locator("#hsk-pwa-feedback-title").inner_text() == "Yangi kurs versiyasi"
        page.locator(".hsk-pwa-feedback-stars button").first.click()
        page.locator("#hsk-pwa-feedback-submit").click()
        assert not posts, "invalid feedback must never reach POST"
        textarea = page.locator(".hsk-pwa-feedback-field textarea")
        assert textarea.evaluate("(node) => getComputedStyle(node).fontSize") == "16px"
        textarea.fill("Dars yuklanishi sekin.")
        page.locator("#hsk-pwa-feedback-submit").click()
        page.wait_for_function(
            "document.querySelector('#hsk-pwa-feedback-submit').hidden === true"
        )
        assert len(posts) == 1
        assert posts[0]["headers"].get("x-hsk-pwa-csrf") == "browser-csrf"
        assert posts[0]["body"] == {
            "campaign_id": 19, "rating": 1, "comment_text": "Dars yuklanishi sekin.",
        }
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        browser.close()

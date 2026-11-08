"""Real PWA onboarding must not silently enable a track while API is pending/failed."""
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")

SOURCE = Path("app/static/course_v3_onboarding.html")


def test_track_loading_is_visible_retryable_and_server_authoritative():
    html = SOURCE.read_text(encoding="utf-8")
    init = """
window.Telegram = {WebApp:{initData:""}};
window.__trackCallbacks = [];
window.fetch = function(path) {
  if (String(path).includes("/api/v3/pwa-auth/session"))
    return Promise.resolve(new Response(JSON.stringify({
      ok:true,user_id:23,csrf:"unit-test-csrf"
    }),{status:200,headers:{"Content-Type":"application/json"}}));
  if (String(path).includes("/api/v3/pwa/course-tracks"))
    return new Promise(function(resolve) {window.__trackCallbacks.push(resolve)});
  return Promise.reject(new Error("unexpected_fetch:"+path));
};
"""
    with playwright.sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.add_init_script(init)
        page.route("https://hsk.test/iphone-pwa/onboarding", lambda route: route.fulfill(
            body=html, status=200, content_type="text/html; charset=utf-8",
        ))
        page.route("**/*.css*", lambda route: route.fulfill(body="", status=200, content_type="text/css"))
        page.route("**/*.js*", lambda route: route.fulfill(body="", status=200,
                                                       content_type="application/javascript"))
        page.goto("https://hsk.test/iphone-pwa/onboarding")

        page.locator("#cta").click()
        assert page.locator(".onb-remote-state").is_visible()
        assert page.locator(".onb-remote-state .loader").is_visible()
        assert page.locator("#cta").is_disabled()
        assert page.locator(".track-switch").count() == 0
        page.evaluate("""window.__trackCallbacks.shift()(new Response(
          JSON.stringify({ok:false,error:"temporary_failure"}),
          {status:503,headers:{"Content-Type":"application/json"}}));""")
        page.locator(".onb-remote-state .loader").wait_for(state="detached")
        assert page.locator("#cta").is_enabled()
        assert page.locator(".track-switch").count() == 0

        page.locator("#cta").click()
        assert page.locator("#cta").is_disabled()
        page.evaluate("""window.__trackCallbacks.shift()(new Response(
          JSON.stringify({ok:true,tracks:{hsk30:{
            access:{feature_enabled:false,allowed:false},live_levels:[]
          }},hsk30_unlock:{}}),
          {status:200,headers:{"Content-Type":"application/json"}}));""")
        page.locator(".track-switch").wait_for(state="visible")
        assert page.locator(".onb-remote-state").count() == 0
        assert page.locator("#cta").is_enabled()
        assert page.locator('img[src*="hsk20-course-books.jpg"]').count() == 1
        assert not errors
        browser.close()

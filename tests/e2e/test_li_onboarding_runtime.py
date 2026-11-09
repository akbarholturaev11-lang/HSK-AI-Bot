"""Real browser contract for the isolated 23-state Li onboarding view.

The original user demo remains the visual/copy reference. This test ensures
the runtime does not fake course readiness, account writes or trial grants.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")

STATIC = Path("app/static")
HTML = (STATIC / "course_v3_li_onboarding.html").read_text(encoding="utf-8")
RUNTIME = (STATIC / "course_v3_data/li-onboarding-runtime.js").read_text(encoding="utf-8")
CATALOG = (STATIC / "course_v3_data/hsk-li-onboarding-i18n.js").read_text(encoding="utf-8")
COMMON_CATALOG = (STATIC / "course_v3_data/hsk-common-i18n.js").read_text(encoding="utf-8")
TELEGRAM_ID = "12345678-1234-4123-8123-123456789abc"
INSTALL_JS = (STATIC / "course_v3_data/li-onboarding-install.js").read_text(encoding="utf-8")
INSTALL_CSS = (STATIC / "course_v3_data/li-onboarding-install.css").read_text(encoding="utf-8")
IOS_SAFARI = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1"
CAST = (STATIC / "assets/characters/hsk-character-pack.js").read_text(encoding="utf-8")
ORIGIN = "https://hsk.test"


def _page(browser, *, pwa=True, trial_eligible=False, trial_start_ok=True, saved=False, trial_status_fail=False, guest=False, ios=False):
    options = {"viewport": {"width": 390, "height": 844}}
    if ios:
        options["user_agent"] = IOS_SAFARI
    page = browser.new_page(**options)
    captured = {"post": [], "trial_start": [], "track_get": 0, "pageerrors": [],
                "resume": 0, "oauth": [], "telegram_start": [],
                "telegram_claim": [], "telegram_state": "pending",
                "public_track_get": 0,
                "auth_state": {"verified": not guest}}
    page.on("pageerror", lambda err: captured["pageerrors"].append(str(err)))
    captured["navigations"] = []
    captured["request_failed"] = []
    page.on("framenavigated", lambda frame: captured["navigations"].append(frame.url)
            if frame == page.main_frame else None)
    page.on("requestfailed", lambda request: captured["request_failed"].append(
        (request.url, request.failure)))
    # A PWA Safari page may load the shared Telegram SDK file, but it must
    # not magically possess signed Mini App initData. Only the Telegram route
    # gets this proof, and only the browser route gets cookie/CSRF identity.
    telegram_init = "" if pwa else "signed-test-init-data"
    page.route("**/assets/telegram-web-app.js*", lambda route: route.fulfill(
        body='window.Telegram={WebApp:{initData:' + json.dumps(telegram_init) + ','
             'initDataUnsafe:{user:{id:111}},HapticFeedback:{selectionChanged:function(){}}}};',
        content_type="application/javascript",
    ))
    page.route("**/assets/characters/hsk-character-pack.js*", lambda route: route.fulfill(
        body=CAST, content_type="application/javascript",
    ))
    page.route("**/course_v3_data/hsk-li-onboarding-i18n.js*", lambda route: route.fulfill(
        body=CATALOG, content_type="application/javascript",
    ))
    page.route("**/course_v3_data/hsk-common-i18n.js*", lambda route: route.fulfill(
        body=COMMON_CATALOG, content_type="application/javascript",
    ))
    page.route("**/course_v3_data/li-onboarding-runtime.js*", lambda route: route.fulfill(
        body=RUNTIME, content_type="application/javascript",
    ))
    page.route("**/course_v3_data/li-onboarding-install.js*", lambda route: route.fulfill(
        body=INSTALL_JS, content_type="application/javascript",
    ))
    page.route("**/assets/hsk*-course-books.jpg*", lambda route: route.fulfill(
        body=(STATIC / "assets" / route.request.url.split("/assets/")[1].split("?")[0]).read_bytes(),
        content_type="image/jpeg",
    ))
    page.route("**/*.css*", lambda route: route.fulfill(
        body=INSTALL_CSS if "li-onboarding-install.css" in route.request.url else "",
        content_type="text/css",
    ))
    page.route("**/assets/onboarding/iphone-home-screen.mp4*", lambda route: route.fulfill(
        body="not published", status=404, content_type="text/plain",
    ))
    page.route("**/assets/onboarding/iphone-install-home-focus.jpg*", lambda route: route.fulfill(
        body=(STATIC / "assets/onboarding/iphone-install-home-focus.jpg").read_bytes(),
        content_type="image/jpeg",
    ))
    url = ORIGIN + ("/iphone-pwa/onboarding/li" if pwa else
                    "/course_v3_li_onboarding.html") + "?lang=uz"
    page.route(url, lambda route: route.fulfill(
        body=HTML, content_type="text/html; charset=utf-8",
    ))
    # Simulate a complete browser-side OAuth return in the same tab.
    # A synthetic intercepted 302 can end in chromium-error:// even though
    # a real provider uses an HTML navigation and a verified callback.
    page.route("https://accounts.example.test/**", lambda route: route.fulfill(
        status=200, content_type="text/html",
        body="<html><script>location.replace(" + json.dumps(url) + ")</script></html>",
    ))
    page.route(ORIGIN + "/iphone-pwa/course?*", lambda route: route.fulfill(
        body="COURSE PAGE", content_type="text/html",
    ))
    page.route(ORIGIN + "/iphone-pwa/course", lambda route: route.fulfill(
        body="COURSE PAGE", content_type="text/html",
    ))
    page.route(ORIGIN + "/iphone-pwa", lambda route: route.fulfill(
        body='<html><script>location.replace("/iphone-pwa/onboarding/li?lang=uz")</script></html>',
        content_type="text/html",
    ))
    page.route(ORIGIN + "/course-v3.html?*", lambda route: route.fulfill(
        body="COURSE PAGE", content_type="text/html",
    ))

    def api(route):
        req = route.request
        path = req.url.split("?", 1)[0].split(ORIGIN, 1)[-1]
        body = req.post_data_json if req.method == "POST" and req.post_data else {}
        status = 200
        if path == "/api/v3/pwa-auth/session":
            if not captured["auth_state"]["verified"]:
                status = 401
                payload = {"ok": False, "error": "pwa_session_required"}
            else:
                payload = {"ok": True, "user_id": 37, "csrf": "test-csrf"}
        elif path == "/api/v3/pwa-auth/providers":
            payload = {"ok": True, "providers": ["google"]}  # Actual API lists OAuth only
        elif path == "/api/v3/pwa/onboarding/li/resume":
            assert req.method == "POST"
            captured["resume"] += 1
            payload = {"ok": True}
        elif path == "/api/v3/pwa-auth/telegram/start":
            assert req.method == "POST"
            assert body["language"] == "uz"
            captured["telegram_start"].append(body)
            payload = {"ok": True, "link_request_id": TELEGRAM_ID,
                       "authorize_url": "https://t.me/hskai_bot?start=pwa_link_" + TELEGRAM_ID + "_uz"}
        elif path == "/api/v3/pwa-auth/telegram/claim":
            assert req.method == "POST"
            assert body["link_request_id"] == TELEGRAM_ID
            captured["telegram_claim"].append(body)
            if captured["telegram_state"] == "complete":
                captured["auth_state"]["verified"] = True
                payload = {"ok": True, "status": "complete"}
            elif captured["telegram_state"] == "expired":
                status = 409
                payload = {"ok": False, "error": "pwa_telegram_expired"}
            elif captured["telegram_state"] == "denied":
                status = 409
                payload = {"ok": False, "error": "pwa_telegram_not_approved"}
            else:
                payload = {"ok": True, "status": "pending"}
        elif path == "/api/v3/pwa-auth/start":
            assert req.method == "POST"
            assert body["provider"] == "google"
            captured["oauth"].append(body)
            # Synthetic callback: the actual origin/nonce and credential
            # binding are checked in tests/test_pwa_browser_auth.py.
            captured["auth_state"]["verified"] = True
            payload = {"ok": True, "authorize_url": "https://accounts.example.test/oauth"}
        elif path == "/api/v3/pwa/onboarding/public-tracks":
            captured["public_track_get"] += 1
            payload = {"ok": True, "tracks": {"hsk20": {"track": "hsk20"},
                "hsk30": {"access": {"feature_enabled": True, "allowed": False},
                          "live_levels": ["nhsk1"]}}, "hsk30_unlock": {}}
        elif path in {"/api/v3/pwa/onboarding/status", "/api/miniapp/onboarding/status"}:
            payload = {"ok": True, "saved": saved, "level": "hsk1",
                       "profile": {"goal": "hsk_exam"} if saved else None}
        elif path in {"/api/v3/pwa/course-tracks", "/api/v3/course-tracks"}:
            captured["track_get"] += 1
            if not pwa:
                assert req.headers.get("x-telegram-init-data") == "signed-test-init-data"
            payload = {"ok": True, "tracks": {"hsk20": {"level": "hsk1"},
                "hsk30": {"access": {"feature_enabled": False, "allowed": False},
                          "live_levels": []}}, "hsk30_unlock": {}}
        elif path in {"/api/v3/pwa/onboarding", "/api/miniapp/onboarding"}:
            assert req.method == "POST"
            if pwa:
                assert req.headers.get("x-hsk-pwa-csrf") == "test-csrf"
                assert "x-telegram-init-data" not in req.headers
            else:
                assert req.headers.get("x-telegram-init-data") == "signed-test-init-data"
            captured["post"].append(body)
            payload = {"ok": True, "level": "hsk1", "lesson": 1, "tab": "course",
                       "foundation_required": False}
        elif path in {"/api/v3/pwa/trial/status", "/api/v3/trial/status"}:
            if trial_status_fail:
                status = 503
                payload = {"ok": False, "error": "provider_unavailable"}
            else:
                payload = {"ok": True, "trial": {"eligible": trial_eligible, "days": 7}}
        elif path in {"/api/v3/pwa/trial/start", "/api/v3/trial/start"}:
            captured["trial_start"].append(body)
            if trial_start_ok:
                payload = {"ok": True, "days": 7,
                           "ends_at": "2026-11-15T12:00:00+00:00"}
            else:
                status = 409
                payload = {"ok": False, "error": "trial_already_used"}
        else:
            raise AssertionError("Unexpected API " + path)
        route.fulfill(status=status, body=json.dumps(payload),
                      content_type="application/json")

    page.route("**/api/**", api)
    page.goto(url)
    page.wait_for_function("window.LiRuntime && typeof window.go==='function'")
    # Safari must recognize an installable app even while the post-signup
    # guide is open on the Li page. This is a *PWA-only* head contract; the
    # shared Telegram Mini App HTML must not advertise a PWA identity.
    if pwa:
        assert page.locator('link[rel="manifest"]').get_attribute("href") == (
            "/iphone-pwa/manifest.webmanifest")
        assert page.locator('link[rel="apple-touch-icon"]').get_attribute("href") == (
            "/assets/hsk-ai-logo-256.png")
        assert page.locator('meta[name="apple-mobile-web-app-capable"]').get_attribute(
            "content") == "yes"
    else:
        assert page.locator('link[rel="manifest"]').count() == 0
        assert page.locator('link[rel="apple-touch-icon"]').count() == 0
    try:
        page.wait_for_function("document.querySelector('#footer .cta')!==null", timeout=8000)
    except Exception:
        snapshot = page.evaluate("""() => ({
          screen: String(window.screen), hasCatalog: !!window.HSKAI_LI_I18N,
          title: document.title, stage: document.querySelector('#stage')?.innerText?.slice(0,120),
          footer: document.querySelector('#footer')?.innerHTML?.slice(0,240)
        })""")
        raise AssertionError(f"Onboarding did not paint its initial action: {snapshot}; "
                             f"JS page errors: {captured['pageerrors']}") from None
    return page, captured


def _advance_to_profile(page, *, chosen_track="hsk20", guest=False):
    # Existing authenticated users begin at the same panda-first scene; no
    # second provider login is required by the real Mini App/PWA adapters.
    assert page.locator("h1.bub.q").is_visible()
    page.locator("#footer .cta").first.click()  # first-time path
    assert page.locator("#stage .center").is_visible()
    page.locator("#footer .cta").click()  # intro
    page.locator("#footer .cta").click()  # load real track data
    page.locator(".track-switch").wait_for(state="visible")
    assert page.locator('img[src*="hsk20-course-books.jpg"]').is_visible()
    hsk30_button = page.locator('button[onclick*="hsk30"]')
    # Guest preview (not an entitlement) is selectable when HSK 3.0 is live.
    if chosen_track == "hsk30":
        assert hsk30_button.is_enabled()
        hsk30_button.click()
        assert page.evaluate("window.track") == "hsk30"
        assert page.locator('img[src*="hsk30-course-books.jpg"]').is_visible()
    page.locator("#footer .cta").click()  # level
    page.locator(".choices .lv").nth(0 if chosen_track == "hsk30" else 1).click()
    page.locator("#footer .cta").click()  # multi-goal
    page.locator(".choices .lv").nth(0).click()  # HSK exam
    page.locator(".choices .lv").nth(2).click()  # travel (demo GOALS order)
    page.locator("#footer .cta").click()  # time
    page.locator(".choices .lv").nth(1).click()  # 10m
    page.locator("#footer .cta").click()  # focus
    page.locator(".choices .lv").nth(0).click()  # speaking
    page.locator("#footer .cta").click()  # ready
    page.locator("#footer .cta").click()  # real lesson track readiness
    page.locator("#stage .center").wait_for(state="visible")  # habit
    page.locator("#footer .cta").click()  # streak
    page.locator(".choices .lv").nth(1).click()  # 14 days
    page.locator("#footer .cta").click()  # final profile screen
    if guest:
        # No intermediate 'create account' CTA: the final card is sign-in.
        assert page.evaluate("window.screen") == "signup"
        assert page.locator("#stage .provider").count() == 3
        assert page.locator("#footer .cta").count() == 0
        assert page.evaluate("window.trail[window.trail.length-1]") == "streak"
    else:
        assert page.evaluate("window.screen") == "profile"
        assert page.locator("#stage .center").is_visible()


def test_li_shell_is_visible_when_external_scripts_fail():
    # Even a blocked CDN/Telegram SDK may not produce a black or blank page.
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.route(ORIGIN + "/iphone-pwa/onboarding/li?lang=uz", lambda route: route.fulfill(
            body=HTML, content_type="text/html; charset=utf-8",
        ))
        page.route("**/*.js*", lambda route: route.abort())
        page.route("**/*.css*", lambda route: route.fulfill(
            body="", content_type="text/css",
        ))
        page.goto(ORIGIN + "/iphone-pwa/onboarding/li?lang=uz")
        # The first shell exists before any script executes. Once optional
        # character/catalog scripts fail, the inline fail-closed handler must
        # replace the busy skeleton with an actionable error; leaving an
        # endlessly busy skeleton would violate the loading UX contract.
        assert page.locator("#top .li-first-brand").is_visible()
        assert page.locator('#stage [role="alert"]').is_visible()
        assert page.locator("#stage").get_attribute("aria-busy") == "false"
        assert page.locator("#footer button.cta").is_visible()
        assert page.locator("#footer button.cta").inner_text().strip()
        assert page.locator("#stage .li-first-shell").count() == 0
        assert page.locator("#stage .pro-offer").count() == 0
        browser.close()


def test_li_course_sections_load_independently_without_blocking_shell():
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, captured = _page(browser, pwa=True, guest=True)
        page.locator("#footer .cta").first.click()  # hello
        page.locator("#footer .cta").click()  # intro
        page.evaluate("""() => {
          const originalFetch=window.fetch.bind(window);
          window.fetch=(url,opts) => String(url).includes('/api/v3/pwa/onboarding/public-tracks')
            ? new Promise(() => {}) : originalFetch(url,opts);
        }""")
        page.locator("#footer .cta").click()
        section = page.locator('[data-remote-section="tracks"]')
        section.wait_for(state="visible")
        assert page.locator("#top").is_visible()
        assert page.locator("#stage .li-loading-options .li-skel").count() == 2
        assert page.locator("#stage .li-loading-lines .li-skel").count() == 2
        assert page.locator('#stage img[src*="hsk20-course-books.jpg"]').is_visible()
        assert page.locator('#stage img[src*="hsk20-course-books.jpg"]').get_attribute("fetchpriority") == "high"
        assert page.locator("#stage").get_attribute("aria-busy") == "true"
        assert captured["post"] == []
        assert not captured["pageerrors"]
        browser.close()


def test_li_cached_public_tracks_show_version_while_fresh_refresh_is_stalled():
    # Only safe public HSK metadata can be presented stale. Never cache a
    # PWA actor, paid access, trial or lesson progress in the onboarding view.
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, captured = _page(browser, pwa=True, guest=True)
        page.locator("#footer .cta").first.click()
        page.locator("#footer .cta").click()
        page.locator("#footer .cta").click()
        page.locator(".track-switch").wait_for(state="visible")
        assert captured["public_track_get"] >= 1
        page.evaluate("""() => {
          const realFetch=window.fetch.bind(window);
          window.fetch=(url,opts) => String(url).includes('/api/v3/pwa/onboarding/public-tracks')
            ? new Promise(() => {}) : realFetch(url,opts);
          LiRuntime.retryTrack();
        }""")
        page.locator(".track-switch").wait_for(state="visible", timeout=2500)
        assert page.locator('button[onclick*="hsk30"]').is_enabled()
        assert captured["post"] == []
        assert captured["track_get"] == 0
        assert not captured["pageerrors"]
        browser.close()


def test_li_cached_public_tracks_do_not_refetch_on_rapid_back_navigation():
    # Network-limited Safari should not start a fresh metadata fetch on
    # every revisit. This is PUBLIC preview cache only, not auth/Pro/progress.
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, captured = _page(browser, pwa=True, guest=True)
        page.locator("#footer .cta").first.click()
        page.locator("#footer .cta").click()
        page.locator("#footer .cta").click()
        page.locator(".track-switch").wait_for(state="visible")
        first = captured["public_track_get"]
        assert first == 1
        for _ in range(3):
            page.evaluate("LiRuntime.retryTrack()")
            page.locator(".track-switch").wait_for(state="visible")
        page.wait_for_timeout(200)
        assert captured["public_track_get"] == first
        assert captured["track_get"] == 0  # no personal entitlement API
        assert captured["post"] == []
        assert not captured["pageerrors"]
        browser.close()


def test_li_cancel_slow_track_read_never_applies_late_api_response():
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, captured = _page(browser, pwa=True, guest=True)
        page.locator("#footer .cta").first.click()
        page.locator("#footer .cta").click()
        page.evaluate("""() => {
          const realFetch=window.fetch.bind(window);
          window.fetch=(url,opts) => String(url).includes('/api/v3/pwa/onboarding/public-tracks')
            ? new Promise((resolve) => {window.__releaseTracks=resolve;})
            : realFetch(url,opts);
        }""")
        page.locator("#footer .cta").click()
        page.locator('[data-remote-section="tracks"]').wait_for(state="visible")
        assert page.locator("#top .li-loading-back").is_enabled()
        page.locator("#top .li-loading-back").click()
        assert page.evaluate("window.screen") == "intro"
        page.evaluate("""() => window.__releaseTracks({
          ok:true,
          json:()=>Promise.resolve({
            ok:true,tracks:{hsk20:{track:'hsk20'},
              hsk30:{access:{allowed:false,feature_enabled:true},live_levels:['nhsk1']}}
          })
        })""")
        page.wait_for_timeout(150)
        assert page.evaluate("window.screen") == "intro"
        assert page.locator("#stage .center").is_visible()
        assert captured["post"] == []
        assert not captured["pageerrors"]
        browser.close()


def test_li_save_has_local_skeleton_without_wiping_profile_scene():
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, captured = _page(browser, pwa=True)
        _advance_to_profile(page)
        page.evaluate("""() => {
          const realFetch=window.fetch.bind(window);
          window.fetch=(url,opts) => String(url).endsWith('/api/v3/pwa/onboarding') &&
            opts && opts.method === 'POST' ? new Promise(() => {}) : realFetch(url,opts);
        }""")
        page.locator("#footer .cta").click()
        panel=page.locator('#stage .li-inline-pending[data-section="save"]')
        panel.wait_for(state="visible")
        assert page.locator("#stage .center").is_visible()
        assert page.locator("#stage .bub").is_visible()
        assert page.locator("#footer .cta").is_disabled()
        assert captured["post"] == []
        assert not captured["pageerrors"]
        browser.close()


@pytest.mark.parametrize("pwa", [True, False])
def test_authenticated_li_flow_persists_choices_and_real_launch(pwa):
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, captured = _page(browser, pwa=pwa, trial_eligible=False)
        _advance_to_profile(page)
        page.locator("#footer .cta").click()
        page.wait_for_function("window.screen==='end'")
        assert len(captured["post"]) == 1
        chosen = captured["post"][0]
        assert chosen["level"] == "hsk1"
        assert chosen["goal"] == "hsk_exam"
        assert chosen["goals"] == ["hsk_exam", "travel"]
        assert chosen["daily_minutes"] == 10
        assert chosen["preferred_focus"] == "speaking"
        assert chosen["streak_target_days"] == 14
        assert chosen["start_mode"] == "continue"
        assert captured["track_get"] >= 2
        assert captured["trial_start"] == []
        assert not captured["pageerrors"]
        page.locator("#footer .cta").click()
        assert ("/iphone-pwa/course?" if pwa else "/course-v3.html?") in page.url
        assert "onboarded=1" in page.url
        browser.close()


def test_guest_profile_has_telegram_google_without_duplicate_create_account_step():
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get("PWA_E2E_ENGINE", "chromium")).launch()
        page, captured = _page(browser, pwa=True, guest=True)
        _advance_to_profile(page, guest=True)
        assert page.locator("#stage .bub").inner_text() == "Progressingizni yo'qotmang! Keling, sizga profil ochamiz."
        assert page.locator("#stage .halo--gold .panda").is_visible()
        assert page.locator("#stage h1").count() == 0  # no duplicate new-account title
        # Provider discovery is asynchronous; retain honest skeleton until it finishes.
        page.locator("#stage .provider").nth(0).wait_for(state="visible")
        page.locator("#stage .provider").nth(1).wait_for(state="visible")
        assert page.locator("#stage .provider").nth(2).is_hidden()
        assert page.locator("#footer .cta").count() == 0
        # Back returns straight to the last preference screen, not an extra page.
        page.evaluate("back()")
        assert page.evaluate("window.screen") == "streak"
        page.locator("#footer .cta").click()
        assert page.evaluate("window.screen") == "signup"
        assert page.evaluate("window.goals") == ["hsk_exam", "travel"]
        assert page.evaluate("window.streakGoal") == 14
        assert captured["post"] == [] and captured["trial_start"] == []
        assert not captured["pageerrors"]
        browser.close()


@pytest.mark.parametrize("provider_index", [0, 1])

@pytest.mark.parametrize("provider", ["google", "telegram"])
def test_auth_return_keeps_original_locale_at_first_panda_paint(provider):
    """The provider callback can lose ?lang; the pending, recent handoff
    retains the exact user's selected locale BEFORE first visible text.
    The marker never acts as an identity or bypasses the real session API.
    """
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get("PWA_E2E_ENGINE", "chromium")).launch()
        page, captured = _page(browser, pwa=True, guest=True, ios=True)
        # The callback URL still carries the old UZ query, but RU is the
        # most recent language selected just before provider navigation.
        page.evaluate("""(provider) => sessionStorage.setItem(
          'hsk_li_auth_handoff_v1',
          JSON.stringify({at:Date.now(),provider:provider,lang:'ru'})
        )""", provider)
        page.add_init_script("""(() => {
          const previous = window.fetch.bind(window);
          window.fetch = (url, options) => {
            if (String(url).includes('/api/v3/pwa-auth/session')) {
              return new Promise(resolve => {
                window.__authSessionRelease = () => resolve(previous(url, options));
              });
            }
            return previous(url, options);
          };
        })();""")
        page.reload()
        page.locator(".li-auth-wait-title").wait_for(state="visible")
        assert page.locator(".li-auth-wait-title").inner_text() == "Ожидаем вход…"
        assert page.locator(".li-auth-wait-subtitle").inner_text() == "Проверяем ваш аккаунт"
        assert page.evaluate("window.LANG") == "ru"
        assert page.evaluate("document.documentElement.lang") == "ru"
        assert page.locator(".li-auth-wait-panda .hc-loading-prop").count() == 1
        assert page.locator(".li-auth-wait-panda .hc-loading-prop").is_hidden()
        # No hidden permission change: guest is still 401 until the
        # server issues the verified cookie.
        assert captured["post"] == [] and captured["trial_start"] == []
        page.evaluate("window.__authSessionRelease()")
        page.locator(".li-auth-wait").wait_for(state="detached")
        assert captured["auth_state"]["verified"] is False
        assert not captured["pageerrors"]
        browser.close()


def test_google_and_telegram_immediately_show_same_panda_wait_before_server_auth(provider_index):
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get("PWA_E2E_ENGINE", "chromium")).launch()
        page, captured = _page(browser, pwa=True, guest=True, ios=True)
        _advance_to_profile(page, guest=True)
        # Keep the first network step pending: the loading screen must paint
        # synchronously from the person's actual provider click.
        page.evaluate("""() => {
          const original = fetch.bind(window);
          window.fetch = (path, options) => {
            if (String(path).includes('/api/v3/pwa/onboarding/li/resume'))
              return new Promise((resolve) => {
                window.__releaseProviderWait = () => resolve(original(path, options));
              });
            return original(path, options);
          };
        }""")
        page.locator("#stage .provider").nth(provider_index).click()
        page.locator(".li-auth-wait").wait_for(state="visible")
        assert page.locator(".li-auth-wait-panda .hsk-character").is_visible()
        assert page.locator(".li-auth-wait-title").inner_text() == "Kirish kutilmoqda…"
        assert page.locator(".li-auth-wait-dots i").count() == 3
        assert page.locator(".li-auth-wait button, .li-auth-wait .li-loading-back").count() == 0
        assert page.evaluate("document.querySelector('.wrap').inert") is True
        assert captured["post"] == [] and captured["trial_start"] == []
        assert captured["oauth"] == []
        assert not captured["pageerrors"]
        browser.close()


def test_guest_li_telegram_starts_from_original_profile_without_welcome_page():
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get("PWA_E2E_ENGINE", "chromium")).launch()
        page, captured = _page(browser, pwa=True, guest=True, saved=True)
        _advance_to_profile(page, guest=True)
        page.route("https://t.me/**", lambda route: route.fulfill(
            status=200, content_type="text/html",
            body="<html><body>Telegram bot approval</body></html>",
        ))
        telegram = page.locator("#stage .provider").nth(0)
        telegram.wait_for(state="visible")
        assert page.locator("#stage .provider").nth(1).is_visible()
        assert page.locator("#stage .provider").nth(2).is_hidden()
        telegram.click()
        page.wait_for_url("https://t.me/hskai_bot?start=pwa_link_" + TELEGRAM_ID + "_uz")
        page.go_back()
        page.wait_for_function("""() =>
          sessionStorage.getItem('hskai.pwa.telegram.pending')===
          '12345678-1234-4123-8123-123456789abc'""")
        assert captured["resume"] == 1
        assert len(captured["telegram_start"]) == 1
        assert captured["oauth"] == []
        assert captured["post"] == [] and captured["trial_start"] == []
        assert "/iphone-pwa?login=1" not in captured["navigations"]
        # A pending bot approval must not expose the old profile speech
        # bubble or a second login card in front of the auth waiting panda.
        assert page.locator(".li-auth-wait").is_visible()
        assert page.locator(".li-auth-wait-title").inner_text() == "Kirish kutilmoqda…"
        assert page.evaluate("document.querySelector('.wrap').inert") is True
        page.locator("#stage .status").wait_for(state="visible")
        assert "Telegram botida" in page.locator("#stage .status").inner_text()
        # The bot's approval is the ONLY thing allowed to verify this browser.
        assert not captured["auth_state"]["verified"]
        captured["telegram_state"] = "complete"
        page.evaluate("window.dispatchEvent(new Event('focus'))")
        page.wait_for_url(ORIGIN + "/iphone-pwa/course", timeout=12000)
        assert captured["auth_state"]["verified"]
        assert page.locator("body").inner_text() == "COURSE PAGE"
        assert captured["post"] == [] and captured["trial_start"] == []
        assert len(captured["telegram_claim"]) >= 1
        assert not captured["pageerrors"]
        browser.close()


def test_new_user_telegram_claim_resumes_guest_choices_without_welcome_screen():
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get("PWA_E2E_ENGINE", "chromium")).launch()
        page, captured = _page(browser, pwa=True, guest=True, saved=False)
        _advance_to_profile(page, guest=True)
        page.route("https://t.me/**", lambda route: route.fulfill(
            status=200, content_type="text/html",
            body="<html><body>Telegram bot approval</body></html>",
        ))
        page.locator("#stage .provider").nth(0).click()
        page.wait_for_url("https://t.me/hskai_bot?start=pwa_link_" + TELEGRAM_ID + "_uz")
        page.go_back()
        page.wait_for_function(
            "() => sessionStorage.getItem('hskai.pwa.telegram.pending')"
        )
        assert captured["post"] == [] and captured["trial_start"] == []
        # Browser page can reload after returning from the Telegram native app.
        page.reload()
        page.wait_for_function(
            "() => window.screen==='signup' && sessionStorage.getItem('hskai.pwa.telegram.pending')"
        )
        assert page.locator(".li-auth-wait").is_visible()
        assert page.locator(".li-auth-wait-panda .hsk-character").is_visible()
        captured["telegram_state"] = "complete"
        page.evaluate("window.dispatchEvent(new Event('focus'))")
        # The same-tab verified Telegram claim auto-saves the previously
        # selected draft. No redundant profile Continue screen is allowed.
        page.wait_for_function("window.screen==='end'", timeout=12000)
        assert captured["auth_state"]["verified"]
        assert page.evaluate("window.goals") == ["hsk_exam", "travel"]
        assert page.evaluate("window.streakGoal") == 14
        assert "/iphone-pwa?login=1" not in captured["navigations"]
        assert len(captured["post"]) == 1
        assert captured["post"][0]["goals"] == ["hsk_exam", "travel"]
        assert captured["trial_start"] == []
        assert not captured["pageerrors"]
        browser.close()


def test_li_telegram_expired_does_not_sign_in_and_can_retry_without_welcome():
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get("PWA_E2E_ENGINE", "chromium")).launch()
        page, captured = _page(browser, pwa=True, guest=True)
        _advance_to_profile(page, guest=True)
        page.route("https://t.me/**", lambda route: route.fulfill(
            status=200, content_type="text/html",
            body="<html><body>Telegram bot approval</body></html>",
        ))
        page.locator("#stage .provider").nth(0).click()
        page.wait_for_url("https://t.me/hskai_bot?start=pwa_link_" + TELEGRAM_ID + "_uz")
        page.go_back()
        page.wait_for_function("() => window.screen==='signup'")
        # A new link is never already expired; expire only while awaiting bot approval.
        captured["telegram_state"] = "expired"
        page.evaluate("window.dispatchEvent(new Event('focus'))")
        page.wait_for_function(
            "() => document.querySelector('#stage .status')?.textContent?.includes('muddati tugadi')"
        )
        assert page.evaluate("sessionStorage.getItem('hskai.pwa.telegram.pending')") is None
        assert page.evaluate("sessionStorage.getItem('hsk_li_auth_handoff_v1')") is None
        assert page.locator("#stage .provider").nth(0).is_enabled()
        assert page.locator(".li-auth-wait").count() == 0
        assert page.evaluate("document.querySelector('.wrap').inert") is False
        assert captured["auth_state"]["verified"] is False
        assert captured["post"] == []
        assert "/iphone-pwa?login=1" not in captured["navigations"]
        assert not captured["pageerrors"]
        browser.close()


def test_guest_can_select_hsk30_but_locked_account_must_use_canonical_unlock():
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get("PWA_E2E_ENGINE", "chromium")).launch()
        page, captured = _page(browser, pwa=True, guest=True)
        _advance_to_profile(page, chosen_track="hsk30", guest=True)
        assert page.evaluate("window.track") == "hsk30"
        assert page.evaluate("window.level") == "nhsk1"
        assert captured["post"] == []
        assert captured["track_get"] == 0
        assert page.evaluate("window.screen") == "signup"
        with page.expect_response("**/api/v3/pwa-auth/start") as started:
            page.locator("#stage .provider").nth(1).click()
        assert started.value.status == 200
        page.locator("#stage .li-remote-error").wait_for(state="visible")
        assert "HSK 3.0" in page.locator("#stage .li-remote-error").inner_text()
        assert "Kursda HSK 3.0 ni ochish" in page.locator("#footer").inner_text()
        assert captured["post"] == []  # Authorization did not bypass the paid track.
        page.locator("#footer .cta.ghost").click()
        page.locator(".track-switch").wait_for(state="visible")
        assert page.evaluate("window.track") == "hsk20"
        assert captured["post"] == []
        assert not captured["pageerrors"]
        browser.close()


def test_pwa_guest_sees_panda_first_and_oauth_resumes_saved_draft_safely():
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, captured = _page(browser, pwa=True, guest=True, trial_eligible=False)
        _advance_to_profile(page, guest=True)
        assert captured["post"] == []  # Public guest may NEVER save a course.
        # Initial public metadata is cached for this page. Repeated reads
        # must not manufacture duplicate requests merely to enter later steps.
        assert captured["public_track_get"] == 1
        assert captured["track_get"] == 0  # anonymous users cannot fetch personal tracks
        # Providers appear immediately on the final profile step.
        assert page.evaluate("window.screen") == "signup"
        assert captured["post"] == []
        assert page.locator("#stage .provider").count() == 3
        assert page.locator("#stage .provider").nth(2).is_hidden()  # Apple disabled
        # OAuth is asynchronous: the resume hint POST must complete before
        # the verified provider-start POST. Wait for the actual HTTP reply,
        # not for an in-memory callback list immediately after click().
        with page.expect_response("**/api/v3/pwa-auth/start") as started:
            page.locator("#stage .provider").nth(1).click()  # real Google OAuth start
        assert started.value.status == 200
        assert captured["resume"] == 1
        assert len(captured["oauth"]) == 1
        # PWA OAuth API tests independently verify the callback. The
        # synthetic provider's HTML already redirects to the original URL.
        # A competing manual page.goto() here aborts that navigation.
        # Leave the real same-tab journey and sessionStorage intact.
        try:
            page.wait_for_function("window.screen==='end'", timeout=15000)
        except Exception:
            # A failed cross-origin navigation can leave chromium-error://
            # where sessionStorage itself throws SecurityError. Never let
            # diagnostics mask the original provider-navigation failure.
            try:
                snapshot = page.evaluate("""() => ({
                  url: location.href, screen: String(window.screen),
                  stage: document.querySelector('#stage')?.innerText?.slice(0,300),
                  footer: document.querySelector('#footer')?.innerText?.slice(0,150),
                  pending: document.querySelector('#stage')?.getAttribute('aria-busy')
                })""")
            except Exception as diagnostic:
                snapshot = {"url": page.url,
                            "diagnostic": str(diagnostic).splitlines()[0]}
            snapshot["navigations"] = captured["navigations"]
            snapshot["request_failed"] = captured["request_failed"]
            raise AssertionError(
                f"OAuth did not restore Li onboarding: {snapshot}; "
                f"requests: {captured!r}"
            ) from None
        assert captured["resume"] == 1
        assert len(captured["oauth"]) == 1
        assert captured["oauth"][0]["provider"] == "google"
        assert page.evaluate("window.goals") == ["hsk_exam", "travel"]
        assert page.evaluate("window.streakGoal") == 14
        # Explicit guest choices are saved automatically after OAuth proves
        # the same account. No extra profile/Continue action.
        assert len(captured["post"]) == 1
        assert page.evaluate("window.screen") == "end"
        assert page.locator(".li-auth-wait").count() == 0
        assert captured["post"][0]["goals"] == ["hsk_exam", "travel"]
        assert not captured["pageerrors"]
        browser.close()


def test_existing_account_after_full_guest_onboarding_skips_new_profile_and_trial():
    """Returning owner must reach the existing course, not save a guest draft.

    The same Google provider button appears on the Li signup screen for both
    first-time registration and sign-in. Its actual identity comes only from
    the verified server session, and status.saved wins over anonymous choices.
    """
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get("PWA_E2E_ENGINE", "chromium")).launch()
        page, captured = _page(
            browser, pwa=True, guest=True, saved=True, trial_eligible=True,
        )
        # The real course redirect does not need URL parameters when onboarding
        # is already complete; cover the exact route as well as deep links.
        page.route(ORIGIN + "/iphone-pwa/course", lambda route: route.fulfill(
            body="COURSE PAGE", content_type="text/html",
        ))
        _advance_to_profile(page, guest=True)
        assert captured["post"] == []
        assert page.evaluate("window.goals") == ["hsk_exam", "travel"]
        assert page.evaluate("window.screen") == "signup"

        with page.expect_response("**/api/v3/pwa-auth/start") as started:
            page.locator("#stage .provider").nth(1).click()  # existing Google owner
        assert started.value.status == 200
        page.wait_for_url(ORIGIN + "/iphone-pwa/course", timeout=10000)
        assert page.locator("body").inner_text() == "COURSE PAGE"
        assert captured["resume"] == 1
        assert len(captured["oauth"]) == 1
        assert captured["post"] == []  # no onboarding overwrites
        assert captured["trial_start"] == []  # no repeat Pro trial
        assert captured["track_get"] == 0  # no ownership/track changes after return
        assert page.evaluate(
            "sessionStorage.getItem('hsk_li_draft_v1:pwa:guest')"
        ) is None
        assert captured["pageerrors"] == []
        browser.close()


def test_unrelated_pwa_login_does_not_silently_adopt_old_guest_draft():
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, captured = _page(browser, pwa=True, guest=True)
        _advance_to_profile(page, guest=True)
        # An anonymous guest may have chosen everything, but no canonical
        # OAuth/resume was initiated in this tab for the newly signed-in actor.
        page.evaluate("""() => {
          const key='hsk_li_draft_v1:pwa:guest';
          const value=JSON.parse(sessionStorage.getItem(key));
          value.step='signup';value.at=Date.now();
          sessionStorage.setItem(key,JSON.stringify(value));
          sessionStorage.removeItem('hsk_li_auth_handoff_v1');
        }""")
        captured["auth_state"]["verified"] = True  # separate login, not Li OAuth
        page.goto(ORIGIN + "/iphone-pwa/onboarding/li?lang=uz")
        page.wait_for_function("window.LiRuntime && window.screen==='account'")
        assert page.evaluate("window.goals") == []
        assert page.evaluate("window.streakGoal") is None
        assert len(captured["post"]) == 0
        assert not captured["pageerrors"]
        browser.close()


def test_new_iphone_signup_shows_install_video_guide_after_verified_save_only():
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, captured = _page(browser, pwa=True, guest=True, ios=True)
        _advance_to_profile(page, guest=True)
        assert page.locator(".li-install-card").count() == 0  # unauthenticated
        with page.expect_response("**/api/v3/pwa-auth/start") as started:
            page.locator("#stage .provider").nth(1).click()  # OAuth
        assert started.value.status == 200
        assert captured["oauth"][0]["provider"] == "google"
        # The mocked OAuth provider redirects in the SAME tab. Do not
        # interrupt that navigation with an extra manual page.goto().
        page.locator(".li-install-card").wait_for(state="visible", timeout=15000)
        assert page.locator(".li-auth-wait").count() == 0
        assert len(captured["post"]) == 1  # verified auto-save
        assert page.locator(".li-install-hero").is_visible()
        assert page.locator(".li-install-how").inner_text() == "Qanday?"
        assert page.locator(".li-install-video-page").is_hidden()
        assert page.locator("#footer .cta").count() == 0
        page.locator(".li-install-how").click()
        page.locator(".li-install-video-fallback").wait_for(state="visible")
        assert page.locator(".li-install-video-fallback .li-install-steps li").count() == 3
        page.locator(".li-install-close").click()
        page.wait_for_function("window.screen==='end'")
        assert not captured["trial_start"]
        assert page.evaluate("localStorage.getItem('hskai_li_install_guide_v1:37')") == "seen"
        assert not captured["pageerrors"]
        browser.close()


def test_partial_json_response_cannot_leave_loading_screen_stuck():
    # A response may deliver status/headers but stall forever reading JSON.
    # The frontend timeout must wrap the *whole* body read, not only fetch.
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, captured = _page(browser, pwa=True, guest=True)
        page.evaluate("""() => {
          const originalFetch = window.fetch.bind(window);
          const originalTimeout = window.setTimeout.bind(window);
          window.fetch = function(path, options) {
            if (String(path).includes('/api/v3/pwa/onboarding/public-tracks'))
              return Promise.resolve({ok: true, json: () => new Promise(() => {})});
            return originalFetch(path, options);
          };
          window.setTimeout = (fn, ms, ...args) =>
            originalTimeout(fn, ms === 12000 ? 110 : ms, ...args);
        }""")
        page.locator("#footer .cta").first.click()
        page.locator("#footer .cta").click()
        page.locator("#footer .cta").click()
        page.locator(".li-remote-error").wait_for(state="visible", timeout=4000)
        assert page.get_by_role("button", name="Qayta urinish").is_visible()
        assert page.evaluate("window.screen") == "loadCourse"
        assert not captured["post"]
        assert not captured["pageerrors"]
        browser.close()


def test_trial_status_network_failure_is_retryable_and_free_continuation_exists():
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, captured = _page(browser, pwa=True, trial_status_fail=True)
        _advance_to_profile(page)
        page.locator("#footer .cta").click()  # server save succeeds; trial status fails
        page.locator(".li-remote-error").wait_for(state="visible")
        assert page.locator("#footer .cta").count() == 2
        assert page.locator("#footer .cta.ghost").is_visible()
        assert len(captured["post"]) == 1
        assert captured["trial_start"] == []
        page.locator("#footer .cta.ghost").click()  # continue free without fake eligibility
        assert page.evaluate("window.screen") == "end"
        assert not captured["pageerrors"]
        browser.close()


def test_trial_activation_denial_offers_real_retry_and_free_course():
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, captured = _page(
            browser, pwa=True, trial_eligible=True, trial_start_ok=False,
        )
        _advance_to_profile(page)
        page.locator("#footer .cta").click()
        page.wait_for_function("window.screen==='trialIntro'")
        for _ in range(4):
            page.locator("#footer .cta").click()
        page.locator(".li-remote-error").wait_for(state="visible")
        assert page.locator(".li-remote-error").count() == 1
        assert len(captured["trial_start"]) == 1
        page.get_by_role("button", name="Qayta urinish").click()
        page.locator(".li-remote-error").wait_for(state="visible")
        assert len(captured["trial_start"]) == 2
        assert page.locator(".li-remote-error").count() == 1
        page.locator("#footer .cta.ghost").click()
        assert page.evaluate("window.screen") == "end"
        assert not captured["pageerrors"]
        browser.close()


def test_pwa_lost_trial_start_reply_reconciles_without_duplicate_grant():
    # Server committed the grant, but Safari received an error instead of the
    # /start response. Read the real account trial state before retrying.
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, captured = _page(browser, pwa=True, trial_eligible=True)
        expiry = "2026-11-16T12:00:00+00:00"

        def intercepted_start(route):
            captured["trial_start"].append({})
            route.fulfill(
                status=503, body=json.dumps({"ok": False, "error": "reply_lost"}),
                content_type="application/json",
            )

        def read_authoritative_status(route):
            active = bool(captured["trial_start"])
            route.fulfill(
                body=json.dumps({"ok": True, "trial": {
                    "eligible": not active, "reason": "trial_already_used" if active else "",
                    "days": 7, "active": active,
                    "ends_at": expiry if active else None,
                }}), content_type="application/json",
            )

        page.route("**/api/v3/pwa/trial/start", intercepted_start)
        page.route("**/api/v3/pwa/trial/status", read_authoritative_status)
        _advance_to_profile(page)
        page.locator("#footer .cta").click()
        page.wait_for_function("window.screen==='trialIntro'")
        for _ in range(4):
            page.locator("#footer .cta").click()
        page.wait_for_function("window.screen==='trialDone'")
        assert len(captured["trial_start"]) == 1
        assert page.locator(".li-remote-error").count() == 0
        assert page.locator("#stage").get_attribute("aria-busy") == "false"
        assert len(captured["post"]) == 1
        assert not captured["pageerrors"]
        browser.close()


def test_trial_slides_cannot_forge_activation_or_two_day_push_claim():
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, captured = _page(browser, pwa=True, trial_eligible=True)
        _advance_to_profile(page)
        page.locator("#footer .cta").click()
        page.wait_for_function("window.screen==='trialIntro'")
        assert len(captured["post"]) == 1
        assert captured["trial_start"] == []
        assert page.locator(".li-pro-welcome h1").inner_text() == "HSK AI PRO"
        assert page.locator(".li-pro-welcome-panda").is_visible()
        for expected in ["trial1", "trial2", "trial3"]:
            page.locator("#footer .cta").click()
            assert page.evaluate("window.screen") == expected
            if expected == "trial2":
                assert "Safarda" in page.locator("#stage .trial h2").inner_text()
            if expected == "trial3":
                assert "HSK" in page.locator("#stage .trial h2").inner_text()
        page.locator("#footer .cta").click()
        page.wait_for_function("window.screen==='trialDone'")
        assert len(captured["trial_start"]) == 1
        # PWA T-48h push is not implemented yet: no fake reminder promise.
        assert "2 kun" not in page.locator("#stage .trial h2").inner_text()
        assert not captured["pageerrors"]
        browser.close()


@pytest.mark.parametrize("missing_asset", ["catalog", "character"])
def test_missing_public_view_bundle_shows_retry_without_fake_account_or_pro(missing_asset):
    # A CDN/offline failure must never crash the inline render or leave the
    # skeleton stuck. Neither provider auth nor trial should be attempted.
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get("PWA_E2E_ENGINE", "chromium")).launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        pageerrors, api_requests = [], []
        page.on("pageerror", lambda e: pageerrors.append(str(e)))
        page.on("request", lambda r: api_requests.append(r.url)
                if "/api/" in r.url else None)
        page.route("**/*", lambda route: route.fulfill(
            body="", status=200,
            content_type=("text/css" if ".css" in route.request.url
                          else "application/javascript"),
        ))
        if missing_asset == "character":
            page.route("**/course_v3_data/hsk-li-onboarding-i18n.js*",
                       lambda route: route.fulfill(
                           body=CATALOG, content_type="application/javascript"))
        page.route(ORIGIN + "/iphone-pwa/onboarding/li?lang=uz",
                   lambda route: route.fulfill(
                       body=HTML, content_type="text/html; charset=utf-8"))
        page.goto(ORIGIN + "/iphone-pwa/onboarding/li?lang=uz",
                  wait_until="domcontentloaded")
        alert = page.locator("#stage [role=alert]")
        alert.wait_for(state="visible")
        assert page.locator("#stage").get_attribute("aria-busy") == "false"
        assert page.locator("#footer button").count() == 1
        assert page.locator("#footer button").is_enabled()
        assert not page.locator("#stage .provider").count()
        assert not api_requests
        assert not pageerrors
        browser.close()

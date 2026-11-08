"""Real browser contract for the isolated 23-state Li onboarding view.

The original user demo remains the visual/copy reference. This test ensures
the runtime does not fake course readiness, account writes or trial grants.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")

STATIC = Path("app/static")
HTML = (STATIC / "course_v3_li_onboarding.html").read_text(encoding="utf-8")
RUNTIME = (STATIC / "course_v3_data/li-onboarding-runtime.js").read_text(encoding="utf-8")
CATALOG = (STATIC / "course_v3_data/hsk-li-onboarding-i18n.js").read_text(encoding="utf-8")
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
                "resume": 0, "oauth": [], "public_track_get": 0,
                "auth_state": {"verified": not guest}}
    page.on("pageerror", lambda err: captured["pageerrors"].append(str(err)))
    captured["navigations"] = []
    captured["request_failed"] = []
    page.on("framenavigated", lambda frame: captured["navigations"].append(frame.url)
            if frame == page.main_frame else None)
    page.on("requestfailed", lambda request: captured["request_failed"].append(
        (request.url, request.failure)))
    page.route("**/assets/telegram-web-app.js*", lambda route: route.fulfill(
        body='window.Telegram={WebApp:{initData:"signed-test-init-data",'
             'initDataUnsafe:{user:{id:111}},HapticFeedback:{selectionChanged:function(){}}}};',
        content_type="application/javascript",
    ))
    page.route("**/assets/characters/hsk-character-pack.js*", lambda route: route.fulfill(
        body=CAST, content_type="application/javascript",
    ))
    page.route("**/course_v3_data/hsk-li-onboarding-i18n.js*", lambda route: route.fulfill(
        body=CATALOG, content_type="application/javascript",
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
    page.route("**/assets/onboarding/iphone-home-screen.mp4", lambda route: route.fulfill(
        body="not published", status=404, content_type="text/plain",
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
            payload = {"ok": True, "providers": ["google", "telegram"]}
        elif path == "/api/v3/pwa/onboarding/li/resume":
            assert req.method == "POST"
            captured["resume"] += 1
            payload = {"ok": True}
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


def _advance_to_profile(page):
    # Existing authenticated users begin at the same panda-first scene; no
    # second provider login is required by the real Mini App/PWA adapters.
    assert page.locator("h1.bub.q").is_visible()
    page.locator("#footer .cta").first.click()  # first-time path
    assert page.locator("#stage .center").is_visible()
    page.locator("#footer .cta").click()  # intro
    page.locator("#footer .cta").click()  # load real track data
    page.locator(".track-switch").wait_for(state="visible")
    assert page.locator('img[src*="hsk20-course-books.jpg"]').is_visible()
    assert page.locator('button[onclick*="hsk30"]').is_disabled()
    page.locator("#footer .cta").click()  # level
    page.locator(".choices .lv").nth(1).click()  # HSK 1
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
    page.locator("#footer .cta").click()  # profile
    assert page.locator("#stage .center").is_visible()


@pytest.mark.parametrize("pwa", [True, False])
def test_authenticated_li_flow_persists_choices_and_real_launch(pwa):
    with pw.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
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


def test_pwa_guest_sees_panda_first_and_oauth_resumes_saved_draft_safely():
    with pw.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page, captured = _page(browser, pwa=True, guest=True, trial_eligible=False)
        _advance_to_profile(page)
        assert captured["post"] == []  # Public guest may NEVER save a course.
        assert captured["public_track_get"] >= 2
        assert captured["track_get"] == 0  # anonymous users cannot fetch personal tracks
        page.locator("#footer .cta").click()  # provider sign-up, not POST
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
        # The provider's real verified callback is exercised separately by
        # PWA auth API tests. Simulate its return in the SAME tab without
        # relying on a third-party origin that Chromium may block in CI.
        # Crucially, sessionStorage is NOT re-seeded here.
        page.goto(ORIGIN + "/iphone-pwa/onboarding/li?lang=uz")
        try:
            page.wait_for_function("window.screen==='profile'", timeout=10000)
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
        assert captured["post"] == []  # Still no write until authenticated consent.
        page.locator("#footer .cta").click()
        page.wait_for_function("window.screen==='end'")
        assert len(captured["post"]) == 1
        assert captured["post"][0]["goals"] == ["hsk_exam", "travel"]
        assert not captured["pageerrors"]
        browser.close()


def test_unrelated_pwa_login_does_not_silently_adopt_old_guest_draft():
    with pw.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page, captured = _page(browser, pwa=True, guest=True)
        _advance_to_profile(page)
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
        browser = playwright.chromium.launch()
        page, captured = _page(browser, pwa=True, guest=True, ios=True)
        _advance_to_profile(page)
        assert page.locator(".li-install-card").count() == 0  # unauthenticated
        page.locator("#footer .cta").click()  # signup
        with page.expect_response("**/api/v3/pwa-auth/start") as started:
            page.locator("#stage .provider").nth(1).click()  # OAuth
        assert started.value.status == 200
        assert captured["oauth"][0]["provider"] == "google"
        # Simulate the verified provider callback in the same browser tab.
        # Server authorizes the actor in /api/v3/pwa-auth/session on reload.
        page.goto(ORIGIN + "/iphone-pwa/onboarding/li?lang=uz")
        page.wait_for_function("window.screen==='profile'")
        assert page.locator(".li-install-card").count() == 0  # not saved yet
        page.locator("#footer .cta").click()
        page.locator(".li-install-card").wait_for(state="visible")
        assert len(captured["post"]) == 1  # actual owner-scoped save occurred
        page.locator(".li-install-video-fallback").wait_for(state="visible")
        assert page.locator(".li-install-video").is_hidden()
        assert page.locator(".li-install-steps li").count() == 3
        assert page.evaluate("window.screen") == "profile"  # no mock Pro grant
        page.locator(".li-install-continue").click()
        page.wait_for_function("window.screen==='end'")
        assert not captured["trial_start"]
        assert page.evaluate("localStorage.getItem('hskai_li_install_guide_v1:37')") == "seen"
        assert not captured["pageerrors"]
        browser.close()


def test_trial_status_network_failure_is_retryable_and_free_continuation_exists():
    with pw.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
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


def test_trial_slides_cannot_forge_activation_or_two_day_push_claim():
    with pw.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page, captured = _page(browser, pwa=True, trial_eligible=True)
        _advance_to_profile(page)
        page.locator("#footer .cta").click()
        page.wait_for_function("window.screen==='pro'")
        assert len(captured["post"]) == 1
        assert captured["trial_start"] == []
        # Pro intro + three intact demo promo scenes
        for expected in ["trialIntro", "trial1", "trial2", "trial3"]:
            page.locator("#footer .cta").click()
            assert page.evaluate("window.screen") == expected
        page.locator("#footer .cta").click()
        page.wait_for_function("window.screen==='trialDone'")
        assert len(captured["trial_start"]) == 1
        # PWA T-48h push is not implemented yet: no fake reminder promise.
        assert "2 kun" not in page.locator("#stage .trial h2").inner_text()
        assert not captured["pageerrors"]
        browser.close()

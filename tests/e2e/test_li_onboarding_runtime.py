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
CAST = (STATIC / "assets/characters/hsk-character-pack.js").read_text(encoding="utf-8")
ORIGIN = "https://hsk.test"


def _page(browser, *, pwa=True, trial_eligible=False, trial_start_ok=True, saved=False):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    captured = {"post": [], "trial_start": [], "track_get": 0, "pageerrors": []}
    page.on("pageerror", lambda err: captured["pageerrors"].append(str(err)))
    page.route("**/assets/telegram-web-app.js*", lambda route: route.fulfill(
        body='window.Telegram={WebApp:{initData:"signed-test-init-data",'
             'initDataUnsafe:{user:{id:111}},HapticFeedback:{selectionChanged:function(){}}}};',
        content_type="application/javascript",
    ))
    page.route("**/assets/characters/hsk-character-pack.js*", lambda route: route.fulfill(
        body=CAST, content_type="application/javascript",
    ))
    page.route("**/course_v3_data/li-onboarding-runtime.js*", lambda route: route.fulfill(
        body=RUNTIME, content_type="application/javascript",
    ))
    page.route("**/assets/hsk*-course-books.jpg*", lambda route: route.fulfill(
        body=(STATIC / "assets" / route.request.url.split("/assets/")[1].split("?")[0]).read_bytes(),
        content_type="image/jpeg",
    ))
    page.route("**/*.css*", lambda route: route.fulfill(
        body="", content_type="text/css",
    ))
    url = ORIGIN + ("/iphone-pwa/onboarding/li" if pwa else
                    "/course_v3_li_onboarding.html") + "?lang=uz"
    page.route(url, lambda route: route.fulfill(
        body=HTML, content_type="text/html; charset=utf-8",
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
            payload = {"ok": True, "user_id": 37, "csrf": "test-csrf"}
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
    page.wait_for_function("document.querySelector('#footer .cta')!==null")
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
    page.locator(".choices .lv").nth(4).click()  # travel
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

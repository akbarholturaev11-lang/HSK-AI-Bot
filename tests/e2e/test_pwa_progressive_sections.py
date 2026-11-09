"""Independent PWA section loading with real bundled JS and mocked HTTP.

Runs in Chromium and WebKit; every request is handled locally, no production
credentials or account data. Start the canonical PWA course with the same
public bootstrap shell the authenticated delivery injects.
"""
import ast
import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from playwright.sync_api import sync_playwright

STATIC = Path(__file__).resolve().parents[2] / "app/static"
ORIGIN = "http://hsk-ai.local"


def pwa_document():
    # Reconstruct only the actual authenticated PWA response-side CSS and SDK
    # optimization. Current main owns the ONE static first-paint shell in the
    # canonical shared HTML; no deprecated response-injected shell is allowed.
    source = (STATIC / "course-v3.html").read_text(encoding="utf-8")
    tree = ast.parse((Path("app/api/pwa_auth.py")).read_text(encoding="utf-8"))
    css = next(
        ast.literal_eval(node.value).decode("utf-8")
        for node in tree.body if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "_PWA_PROGRESSIVE_SECTIONS_CSS"
                for t in node.targets)
    )
    sdk = '<script src="/assets/telegram-web-app.js?v=20261019-1"></script>'
    assert source.count(sdk) == 1
    # The first Course shell and all four layout-specific existing tab shells
    # must be present; variant classes are required for geometry fidelity.
    assert source.count('class="pwa-initial-shell') >= 5
    return source.replace("</head>", css + "</head>", 1).replace(sdk, "", 1)


def test_course_ready_while_rating_referrals_and_profile_stats_load_independently():
    data = json.loads((STATIC / "course_v3_data/hsk1.json").read_text(encoding="utf-8"))
    data["authenticated"] = True
    data["level"] = "hsk1"
    data["user"] = {
        "name": "Verified Test", "avatar": "阿", "language": "ru",
        "is_paid": True, "state": "TRIAL_ACTIVE", "onboarding_completed": True,
        "referral_code": "", "display_name": "", "avatar_key": "",
    }
    data["progress"]["completed"] = 0
    data["notify"] = {"enabled": True}
    held = {"rating": [], "profile": [], "friends": [], "voice": []}
    errors = []

    def serve(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(status=200, content_type="text/html", body=pwa_document())
        elif path == "/api/v3/pwa-auth/session":
            route.fulfill(status=200, json={"ok": True, "user_id": 31, "csrf": "test-csrf"})
        elif path == "/api/v3/pwa/map":
            route.fulfill(
                status=200, json=data,
                headers={"X-HSK-PWA-User-ID": "31", "Cache-Control": "no-store"},
            )
        elif path == "/api/v3/pwa/gamification":
            held["rating"].append(route)
        elif path == "/api/v3/pwa/profile":
            held["profile"].append(route)
        elif path == "/api/v3/pwa/invite":
            held["friends"].append(route)
        elif path == "/api/v3/pwa/voice/me":
            held["voice"].append(route)
        elif path.startswith("/api/"):
            route.fulfill(status=404, json={"ok": False, "error": "not_mocked"})
        else:
            file = (STATIC / path.lstrip("/")).resolve()
            if file.is_file() and file.is_relative_to(STATIC.resolve()):
                mime, _ = mimetypes.guess_type(file)
                route.fulfill(path=str(file), content_type=mime or "application/octet-stream")
            else:
                route.fulfill(status=404, body="")

    with sync_playwright() as playwright:
        engine = os.getenv("PWA_E2E_ENGINE", "chromium")
        browser = getattr(playwright, engine).launch()
        try:
            page = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True).new_page()
            page.set_default_timeout(12000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route("**/*", serve)
            page.goto(ORIGIN + "/iphone-pwa/course?lang=ru&onboarded=1", wait_until="domcontentloaded")
            page.locator("#s-course .uban").first.wait_for()
            assert page.locator("#s-course .hsk-pwa-boot-shell").count() == 0
            assert not page.locator("#nav").get_attribute("inert")

            # Onboarded PWA startup resolves legacy trial-status locally. It
            # must not undo lazy Profile mounting while Course is active.
            page.wait_for_function("() => typeof TRIAL_LOADED !== 'undefined' && TRIAL_LOADED")
            assert page.locator("#s-profile .profile-display-name").count() == 0
            assert page.evaluate("refreshCourseProgress()") is True
            assert page.locator("#s-profile .profile-display-name").count() == 0
            assert page.locator("#s-course .uban").count() > 0

            # PWA first viewport must not synchronously build offscreen
            # Practice cards. The existing App.show() entry point builds
            # them on the first visit, and subsequent locale changes update
            # the mounted screen (including when it is offscreen).
            assert page.locator("#s-mashq .row-card").count() == 0
            page.evaluate("App.setLang('uz')")
            assert page.locator("#s-mashq .row-card").count() == 0
            page.locator('#nav button[data-s="mashq"]').click()
            assert page.locator("#s-mashq .row-card").count() == 6
            assert page.locator("#s-mashq .section-title").inner_text() == "Mashq"
            page.evaluate("App.setLang('ru')")
            assert page.locator("#s-mashq .section-title").inner_text() == "Практика"
            page.locator('#nav button[data-s="course"]').click()
            page.evaluate("App.setLang('uz')")
            assert page.locator("#s-mashq .section-title").inner_text() == "Mashq"
            assert page.locator("#s-mashq .row-card").count() == 6

            page.locator('#nav button[data-s="rating"]').click()
            # Upstream main's first-rating skeleton stays mounted while the
            # independent API is pending; re-renders must not erase it.
            page.locator("#s-rating [aria-busy='true']").first.wait_for()
            assert len(held["rating"]) == 1
            page.evaluate("App.setLang('uz')")
            assert page.locator("#s-rating [aria-busy='true']").first.is_visible()
            assert len(held["rating"]) == 1
            # The course has already loaded; a slow leaderboard cannot undo it.
            assert page.locator("#s-course .uban").count() > 0
            held["rating"].pop().fulfill(status=200, json={
                "ok": True, "league": "Bronze", "league_size": 1,
                "leaderboard": [{"name": "Rank verified", "rank": 1, "xp": 27}],
            })
            page.get_by_text("Rank verified").wait_for()
            assert page.locator("#s-rating .hsk-pwa-section-loading").count() == 0
            assert page.locator("#s-rating .pwa-initial-shell").count() == 0

            page.locator('#nav button[data-s="profile"]').click()
            page.locator("#s-profile .hsk-pwa-profile-accuracy-loading").wait_for()
            assert len(held["profile"]) == 1
            # The independently loaded accuracy block must not rebuild Profile.
            from tests.pwa_layout_geometry import capture_geometry, assert_reserved_layout
            accuracy_anchors = {
                "overall-ring": "#s-profile .profile-accuracy>div:nth-child(1) .accuracy-ring",
                "today-ring": "#s-profile .profile-accuracy>div:nth-child(2) .accuracy-ring",
                "accuracy": "#s-profile .profile-accuracy",
                "nav": "#nav",
            }
            profile_loading_boxes = capture_geometry(page, accuracy_anchors)
            page.locator("#s-profile .profile-head").evaluate(
                "(node) => node.dataset.apiPreserve = 'yes'"
            )
            # Profile settings/name are present even though accuracy is pending.
            assert page.locator("#s-profile .profile-display-name").is_visible()
            assert page.locator("#s-profile .profile-settings").is_visible()
            # MAP.is_paid means unlocked content, not a paid subscription:
            # even before analytics responds, the verified trial badge must
            # never momentarily claim this user purchased Pro.
            assert "Sinov" in page.locator("#s-profile .profile-access-badge").inner_text()
            held["profile"].pop().fulfill(status=200, headers={"X-HSK-PWA-User-ID": "31"}, json={
                "ok": True,
                "stats": {"answer_accuracy": {
                    "overall": {"percent": 79}, "today": {"percent": 80},
                }},
            })
            page.wait_for_function(
                "() => !!document.querySelector('#s-profile .profile-accuracy') &&"
                " !document.querySelector('#s-profile .hsk-pwa-profile-accuracy-loading')"
            )
            profile_ready_boxes = capture_geometry(page, accuracy_anchors)
            assert_reserved_layout(profile_loading_boxes, profile_ready_boxes)
            assert page.locator("#s-profile .profile-head").get_attribute("data-api-preserve") == "yes"
            assert "79%" in page.locator("#s-profile .profile-accuracy").inner_text()
            assert page.locator("#s-profile .hsk-pwa-profile-accuracy-loading").count() == 0

            page.evaluate("App.show('rating', 'friends')")
            page.locator("#s-rating .hsk-pwa-section-loading").wait_for()
            assert len(held["friends"]) == 1
            page.evaluate("App.setLang('ru')")
            assert len(held["friends"]) == 1
            held["friends"].pop().fulfill(status=200, headers={"X-HSK-PWA-User-ID": "31"}, json={
                "ok": True, "joined_count": 0, "active_count": 0,
                "required": 2, "referrals": [],
            })
            page.wait_for_function(
                "() => typeof referralMeta !== 'undefined' && !referralMeta.loading"
            )
            assert page.locator("#s-rating .hsk-pwa-section-loading").count() == 0

            # Returning to the same verified PWA account inside the short
            # freshness window must reuse memory (no duplicate SQL-backed GET).
            page.locator('#nav button[data-s="profile"]').click()
            page.locator("#s-profile .profile-accuracy").wait_for()
            assert len(held["profile"]) == 0
            page.evaluate("PROFILE_DETAIL_LOADED_AT=Date.now()-31000")
            page.locator('#nav button[data-s="rating"]').click()
            # When cache becomes stale, the background read is revalidated;
            # failures remain local and never erase the rest of the page.
            page.locator('#nav button[data-s="profile"]').click()
            page.wait_for_function("() => typeof PROFILE_DETAIL_PENDING !== 'undefined' && PROFILE_DETAIL_PENDING")
            assert len(held["profile"]) == 1
            held["profile"].pop().fulfill(status=503, json={"ok": False})
            page.locator("#s-profile .hsk-pwa-profile-stats-error").wait_for()
            assert_reserved_layout(
                profile_ready_boxes, capture_geometry(page, accuracy_anchors)
            )
            assert page.locator("#s-profile .profile-head").get_attribute("data-api-preserve") == "yes"
            assert page.locator("#s-profile .profile-display-name").is_visible()
            page.locator("#s-profile .hsk-pwa-profile-stats-error button").click()
            page.locator("#s-profile .hsk-pwa-profile-accuracy-loading").wait_for()
            assert len(held["profile"]) == 1
            held["profile"].pop().fulfill(status=200, headers={"X-HSK-PWA-User-ID": "31"}, json={
                "ok": True, "stats": {"answer_accuracy": {
                    "overall": {"percent": 84}, "today": {"percent": 88},
                }},
            })
            page.locator("#s-profile .profile-accuracy").wait_for()
            assert page.locator("#s-profile .hsk-pwa-profile-stats-error").count() == 0
            assert errors == []

            # Rendering Voice again while a quota GET is unresolved must
            # share the original request. A later visit must fetch fresh quota.
            page.locator('#nav button[data-s="voice"]').click()
            page.wait_for_function("() => !!renderVoice._quotaPending")
            assert len(held["voice"]) == 1
            page.evaluate("App.setLang('uz')")
            assert len(held["voice"]) == 1
            held["voice"].pop().fulfill(
                status=200, headers={"X-HSK-PWA-User-ID": "31"}, json={"ok": True, "remaining_voice_limit": 2},
            )
            page.locator("#voice-quota").wait_for(state="visible")
            assert "2" in page.locator("#voice-quota").inner_text()
            page.locator('#nav button[data-s="course"]').click()
            page.locator('#nav button[data-s="voice"]').click()
            page.wait_for_function("() => !!renderVoice._quotaPending")
            assert len(held["voice"]) == 1
            held["voice"].pop().fulfill(
                status=200, headers={"X-HSK-PWA-User-ID": "31"}, json={"ok": True, "remaining_voice_limit": 1},
            )
            page.locator("#voice-quota").wait_for(state="visible")
            assert "1" in page.locator("#voice-quota").inner_text()
            assert errors == []

            # A failed optional quota read must not leave a blank status.
            # Both HTTP 503 and transport failure expose a localized retry,
            # without blocking the already rendered course or duplicating GETs.
            for failure_mode in ("http", "network"):
                page.locator('#nav button[data-s="course"]').click()
                page.locator('#nav button[data-s="voice"]').click()
                page.wait_for_function("() => !!renderVoice._quotaPending")
                assert len(held["voice"]) == 1
                failed_request = held["voice"].pop()
                if failure_mode == "http":
                    failed_request.fulfill(status=503, json={"ok": False})
                else:
                    failed_request.abort("failed")
                retry = page.locator("#voice-quota button")
                retry.wait_for(state="visible")
                assert page.locator("#s-course .uban").count() > 0
                retry.click()
                page.wait_for_function("() => !!renderVoice._quotaPending")
                assert len(held["voice"]) == 1
                held["voice"].pop().fulfill(
                    status=200, headers={"X-HSK-PWA-User-ID": "31"},
                    json={"ok": True, "remaining_voice_limit": 2},
                )
                page.wait_for_function(
                    "() => document.querySelector('#voice-quota') &&"
                    " document.querySelector('#voice-quota').textContent.includes('2')"
                )
                assert page.locator("#voice-quota button").count() == 0
                assert errors == []

            # A stalled GET must time out and release single-flight state:
            # otherwise the quota stays in "checking" and Retry never appears.
            page.clock.install()
            page.locator('#nav button[data-s="course"]').click()
            page.locator('#nav button[data-s="voice"]').click()
            page.wait_for_function("() => !!renderVoice._quotaPending")
            assert len(held["voice"]) == 1
            page.clock.fast_forward(10100)
            page.locator("#voice-quota button").wait_for(state="visible")
            assert page.locator("#s-course .uban").count() > 0
            held["voice"].clear()  # The timed-out route was aborted.
            page.locator("#voice-quota button").click()
            page.wait_for_function("() => !!renderVoice._quotaPending")
            assert len(held["voice"]) == 1
            held["voice"].pop().fulfill(
                status=200, headers={"X-HSK-PWA-User-ID": "31"},
                json={"ok": True, "remaining_voice_limit": 3},
            )
            page.wait_for_function(
                "() => document.querySelector('#voice-quota') &&"
                " document.querySelector('#voice-quota').textContent.includes('3')"
            )
            assert page.locator("#voice-quota button").count() == 0
            assert errors == []

            # A cookie replaced in another tab could return a different
            # learner's GET payload while the old map is still in memory.
            # Refuse that response before rendering any cross-account data.
            page.evaluate("App.show('rating', 'friends');retryReferrals()")
            page.wait_for_function("() => typeof referralMeta !== 'undefined' && referralMeta.loading")
            assert len(held["friends"]) == 1
            held["friends"].pop().fulfill(
                status=200, headers={"X-HSK-PWA-User-ID": "32"},
                json={"ok": True, "referrals": [{"name": "Other account secret"}]},
            )
            page.wait_for_url(ORIGIN + "/iphone-pwa")
            assert "Other account secret" not in page.content()
        finally:
            browser.close()
@pytest.mark.parametrize("surface", ["course", "standalone"])
@pytest.mark.parametrize("outcome", ["account_replaced", "session_expired"])
def test_voice_status_refuses_other_session_owners(surface, outcome):
    """An already-open PWA Voice view cannot use another cookie owner's quota."""
    data = json.loads((STATIC / "course_v3_data/hsk1.json").read_text(encoding="utf-8"))
    data["authenticated"] = True
    data["level"] = "hsk1"
    data["user"] = {
        "name": "Original account", "avatar": "阿", "language": "ru",
        "is_paid": True, "state": "PRO_ACTIVE", "onboarding_completed": True,
        "referral_code": "", "display_name": "", "avatar_key": "",
    }
    data["notify"] = {"enabled": True}
    held = []

    def serve(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(status=200, content_type="text/html", body=pwa_document())
        elif path == "/iphone-pwa/practice/voice":
            route.fulfill(
                status=200, content_type="text/html",
                body=(STATIC / "course_v3_voice.html").read_text(encoding="utf-8"),
            )
        elif path == "/iphone-pwa":
            route.fulfill(status=200, content_type="text/html", body="<html><body>Sign in</body></html>")
        elif path == "/api/v3/pwa-auth/session":
            route.fulfill(status=200, json={"ok": True, "user_id": 31, "csrf": "test-csrf"})
        elif path == "/api/v3/pwa/map":
            route.fulfill(status=200, json=data, headers={"X-HSK-PWA-User-ID": "31"})
        elif path == "/api/v3/pwa/voice/me":
            held.append(route)
        elif path.startswith("/api/"):
            route.fulfill(status=404, json={"ok": False, "error": "not_mocked"})
        else:
            file = (STATIC / path.lstrip("/")).resolve()
            if file.is_file() and file.is_relative_to(STATIC.resolve()):
                mime, _ = mimetypes.guess_type(file)
                route.fulfill(path=str(file), content_type=mime or "application/octet-stream")
            else:
                route.fulfill(status=404, body="")

    with sync_playwright() as playwright:
        engine = os.getenv("PWA_E2E_ENGINE", "chromium")
        browser = getattr(playwright, engine).launch()
        try:
            page = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True).new_page()
            page.set_default_timeout(12000)
            page.route("**/*", serve)
            path = "/iphone-pwa/course?lang=ru&onboarded=1" if surface == "course" else "/iphone-pwa/practice/voice"
            if surface == "course":
                page.goto(ORIGIN + path, wait_until="domcontentloaded")
                page.locator("#s-course .uban").first.wait_for()
                with page.expect_request("**/api/v3/pwa/voice/me"):
                    page.locator('#nav button[data-s="voice"]').click()
                page.wait_for_function("() => !!renderVoice._quotaPending")
            else:
                with page.expect_request("**/api/v3/pwa/voice/me"):
                    page.goto(ORIGIN + path, wait_until="domcontentloaded")
                page.wait_for_function("() => !!PWA_VOICE_SESSION")
            assert len(held) == 1
            if outcome == "account_replaced":
                held.pop().fulfill(
                    status=200, headers={"X-HSK-PWA-User-ID": "32"},
                    json={"ok": True, "remaining_voice_limit": 999},
                )
            else:
                held.pop().fulfill(status=401, json={"ok": False, "error": "pwa_session_required"})
            page.wait_for_url(ORIGIN + "/iphone-pwa")
            assert "999" not in page.content()
        finally:
            browser.close()


@pytest.mark.parametrize("width", [320, 390, 430])
@pytest.mark.parametrize("reduced_motion", ["reduce", "no-preference"])
def test_rating_live_loading_geometry_matches_podium_rows_and_nav(width, reduced_motion):
    """Compare ACTUAL rendered Rating slots, not invented box coordinates."""
    from tests.pwa_layout_geometry import capture_geometry, assert_reserved_layout

    payload = json.loads((STATIC / "course_v3_data/hsk1.json").read_text(encoding="utf-8"))
    payload["authenticated"] = True
    payload["level"] = "hsk1"
    payload["user"] = {
        "name": "Verified test account", "avatar": "阿",
        "language": "ru", "is_paid": True, "state": "PRO_ACTIVE",
        "onboarding_completed": True,
    }
    held = []
    errors = []

    def serve(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(status=200, content_type="text/html", body=pwa_document())
        elif path == "/api/v3/pwa-auth/session":
            route.fulfill(status=200, json={"ok": True, "user_id": 31, "csrf": "test-csrf"})
        elif path == "/api/v3/pwa/map":
            route.fulfill(status=200, json=payload, headers={
                "X-HSK-PWA-User-ID": "31", "Cache-Control": "no-store",
            })
        elif path == "/api/v3/pwa/gamification":
            held.append(route)
        elif path.startswith("/api/"):
            route.fulfill(status=404, json={"ok": False, "error": "not_mocked"})
        else:
            file = (STATIC / path.lstrip("/")).resolve()
            if file.is_file() and file.is_relative_to(STATIC.resolve()):
                mime, _ = mimetypes.guess_type(file)
                route.fulfill(path=str(file), content_type=mime or "application/octet-stream")
            else:
                route.fulfill(status=404, body="")

    anchors = {
        "title": "#s-rating .rating-title",
        "podium": "#s-rating .rating-podium-list",
        "members": "#s-rating .rating-podium-meta",
        "top-five": "#s-rating .rating-podium-queue",
        "row-1": "#s-rating .lr",
        "nav": "#nav",
    }
    with sync_playwright() as playwright:
        browser = getattr(playwright, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        try:
            page = browser.new_context(
                viewport={"width": width, "height": 844}, is_mobile=True,
                reduced_motion=reduced_motion,
            ).new_page()
            page.set_default_timeout(15000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.add_init_script(
                """(() => {
                  window.__ratingCLS = null;
                  if ('PerformanceObserver' in window &&
                      PerformanceObserver.supportedEntryTypes &&
                      PerformanceObserver.supportedEntryTypes.includes('layout-shift')) {
                    window.__ratingCLS = 0;
                    new PerformanceObserver(list => list.getEntries().forEach(e => {
                      if (!e.hadRecentInput) window.__ratingCLS += e.value;
                    })).observe({type:'layout-shift', buffered:true});
                  }
                })();"""
            )
            page.route("**/*", serve)
            page.goto(ORIGIN + "/iphone-pwa/course?lang=ru&onboarded=1", wait_until="domcontentloaded")
            page.locator("#s-course .uban").first.wait_for()
            page.evaluate("if (window.__ratingCLS !== null) window.__ratingCLS = 0")
            page.locator('#nav button[data-s="rating"]').click()
            page.locator("#s-rating .pwa-rating-shell[aria-busy=true]").wait_for()
            assert len(held) == 1
            assert page.locator("#s-rating .pwa-rating-trophy").count() == 3
            assert page.locator("#s-rating .pwa-rating-row").count() == 5
            if reduced_motion == "reduce":
                assert page.locator("#s-rating .pwa-rating-trophy").first.evaluate(
                    "(node) => getComputedStyle(node).animationName"
                ) == "none"
            before = capture_geometry(page, anchors)
            held.pop().fulfill(status=200, json={
                "ok": True, "league": "Bronze", "league_size": 12,
                "leaderboard": [
                    {"name": f"Student {i}", "rank": i, "xp": 110-i*10,
                     "total_xp": 900-i*20}
                    for i in range(1, 6)
                ],
            })
            page.get_by_text("Student 1").wait_for()
            after = capture_geometry(page, anchors)
            assert_reserved_layout(before, after, max_anchor_shift_px=8, max_dimension_delta_px=16)
            observed_cls = page.evaluate("window.__ratingCLS")
            if observed_cls is not None:  # WebKit versions without LayoutShift support
                assert observed_cls <= 0.1
            assert page.locator("#s-course .uban").count() > 0
            assert errors == []
        finally:
            browser.close()


def test_rating_retry_keeps_podium_and_rows_in_place():
    """Failure and retry preserve every initial slot, without repeating GETs."""
    from tests.pwa_layout_geometry import capture_geometry, assert_reserved_layout

    payload = json.loads((STATIC / "course_v3_data/hsk1.json").read_text(encoding="utf-8"))
    payload["authenticated"] = True
    payload["level"] = "hsk1"
    payload["user"] = {"name":"Verified", "avatar":"阿", "language":"ru",
                       "is_paid":True, "state":"PRO_ACTIVE", "onboarding_completed":True}
    held = []
    def serve(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(status=200, content_type="text/html", body=pwa_document())
        elif path == "/api/v3/pwa-auth/session":
            route.fulfill(status=200, json={"ok":True, "user_id":31, "csrf":"test-csrf"})
        elif path == "/api/v3/pwa/map":
            route.fulfill(status=200, json=payload, headers={"X-HSK-PWA-User-ID":"31"})
        elif path == "/api/v3/pwa/gamification":
            held.append(route)
        elif path.startswith("/api/"):
            route.fulfill(status=404, json={"ok":False})
        else:
            file = (STATIC / path.lstrip("/")).resolve()
            if file.is_file() and file.is_relative_to(STATIC.resolve()):
                mime, _ = mimetypes.guess_type(file)
                route.fulfill(path=str(file), content_type=mime or "application/octet-stream")
            else:
                route.fulfill(status=404, body="")
    anchors = {
        "podium": "#s-rating .rating-podium-list",
        "members": "#s-rating .rating-podium-meta",
        "top-five": "#s-rating .rating-podium-queue",
        "row-1": "#s-rating .pwa-rating-row",
        "nav": "#nav",
    }
    with sync_playwright() as playwright:
        browser = getattr(playwright, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        try:
            page = browser.new_context(viewport={"width":390,"height":844}, is_mobile=True).new_page()
            page.set_default_timeout(15000)
            page.route("**/*", serve)
            page.goto(ORIGIN + "/iphone-pwa/course?lang=ru", wait_until="domcontentloaded")
            page.locator("#s-course .uban").first.wait_for()
            page.locator('#nav button[data-s="rating"]').click()
            page.locator("#s-rating .pwa-rating-shell").wait_for()
            before = capture_geometry(page, anchors)
            assert len(held) == 1
            held.pop().fulfill(status=503, json={"ok":False})
            retry = page.locator("#s-rating .pwa-rating-error button")
            retry.wait_for(state="visible")
            after_error = capture_geometry(page, anchors)
            assert_reserved_layout(before, after_error)
            retry.click()
            page.locator("#s-rating .pwa-rating-body[aria-busy=true]").wait_for()
            assert len(held) == 1
            assert page.locator("#s-course .uban").count() > 0
        finally:
            browser.close()

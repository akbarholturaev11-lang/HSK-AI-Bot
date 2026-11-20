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


@pytest.mark.parametrize("width", [320, 390, 430])
@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("language", ["uz", "ru", "tj"])
def test_practice_profile_root_headers_share_stable_accessible_geometry(width, theme, language):
    """Real root renderers: matching chrome, not matching whole-page heights.

    APIs are synthetic; this establishes layout/navigation acceptance only,
    never real-account, checkout or installed-device acceptance.
    """
    from tests.pwa_layout_geometry import assert_reserved_layout, capture_geometry

    payload = json.loads((STATIC / "course_v3_data/hsk1.json").read_text(encoding="utf-8"))
    payload.update(authenticated=True, level="hsk1")
    payload["user"] = {
        "name": "Layout fixture", "avatar": "阿", "language": language,
        "is_paid": True, "state": "TRIAL_ACTIVE", "onboarding_completed": True,
    }
    maps, errors, profile_reads = [], [], []

    def serve(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(status=200, content_type="text/html", body=pwa_document().replace('lang="ru"', f'lang="ru" data-hsk-theme="{theme}"', 1))
        elif path == "/api/v3/pwa-auth/session":
            route.fulfill(status=200, json={"ok": True, "user_id": 31, "csrf": "test-csrf"})
        elif path == "/api/v3/pwa/map":
            maps.append(route)
        elif path == "/api/v3/pwa/profile":
            profile_reads.append(route)
        elif path.startswith("/api/"):
            route.fulfill(status=404, json={"ok": False, "error": "not_mocked"})
        else:
            file = (STATIC / path.lstrip("/")).resolve()
            if file.is_file() and file.is_relative_to(STATIC.resolve()):
                mime, _ = mimetypes.guess_type(file)
                route.fulfill(path=str(file), content_type=mime or "application/octet-stream")
            else:
                route.fulfill(status=404, body="")

    def geometry(page, tab):
        return capture_geometry(page, {
            "header": f"#s-{tab} .htop",
            "title": f"#s-{tab} h1",
            "nav": "#nav",
        })

    with sync_playwright() as playwright:
        engine = os.getenv("PWA_E2E_ENGINE", "chromium")
        browser = getattr(playwright, engine).launch()
        try:
            page = browser.new_page(
                viewport={"width": width, "height": 568 if width == 320 else 932},
                is_mobile=True, reduced_motion="reduce", color_scheme=theme,
            )
            page.set_default_timeout(15000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route("**/*", serve)
            page.goto(ORIGIN + f"/iphone-pwa/course?lang={language}", wait_until="domcontentloaded")
            page.wait_for_function("() => typeof App === 'object' && typeof App.show === 'function'")
            shells = {}
            for tab in ("mashq", "profile"):
                page.evaluate("tab => App.show(tab)", tab)
                page.locator(f"#s-{tab} .pwa-initial-shell").wait_for()
                shells[tab] = geometry(page, tab)
            assert len(maps) == 1
            maps.pop().fulfill(status=200, json=payload, headers={"X-HSK-PWA-User-ID": "31"})
            page.locator("#s-profile .profile-display-name").wait_for()
            assert len(profile_reads) == 1
            profile_reads.pop().fulfill(status=503, json={"ok": False})
            page.locator("#s-profile .hsk-pwa-profile-stats-error").wait_for()
            ready = {"profile": geometry(page, "profile")}
            page.locator("#s-profile .hsk-pwa-profile-stats-error button").click()
            page.locator("#s-profile .hsk-pwa-profile-accuracy-loading").wait_for()
            assert_reserved_layout(ready["profile"], geometry(page, "profile"), max_anchor_shift_px=1, max_dimension_delta_px=1)
            assert len(profile_reads) == 1
            profile_reads.pop().fulfill(status=200, headers={"X-HSK-PWA-User-ID": "31"}, json={
                "ok": True, "stats": {"answer_accuracy": {
                    "overall": {"percent": 77}, "today": {"percent": 83},
                }},
            })
            page.get_by_text("77%", exact=True).wait_for()
            assert_reserved_layout(ready["profile"], geometry(page, "profile"), max_anchor_shift_px=1, max_dimension_delta_px=1)
            artifacts = os.getenv("HSK_HEADER_REVIEW_DIR")
            for tab in ("profile", "mashq"):
                page.locator(f'#nav button[data-s="{tab}"]').click()
                page.locator(f"#s-{tab}.on > .htop").wait_for()
                ready[tab] = geometry(page, tab)
                if artifacts:
                    folder = Path(artifacts)
                    folder.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(folder / f"{engine}-{width}-{theme}-{language}-{tab}.png"))
            if artifacts:
                (Path(artifacts) / f"{engine}-{width}-{theme}-{language}.json").write_text(
                    json.dumps({"shells": shells, "ready": ready}, indent=2), encoding="utf-8",
                )
            for tab in ("mashq", "profile"):
                assert_reserved_layout(shells[tab], ready[tab], max_anchor_shift_px=1, max_dimension_delta_px=1)
            # A title-only Practice row and a Profile row with actions occupy
            # the same root-header slot, with the same title center/gutter.
            for key in ("y", "height"):
                assert abs(ready["mashq"]["header"][key] - ready["profile"]["header"][key]) <= 1
            for key in ("x", "y", "height"):
                assert abs(ready["mashq"]["title"][key] - ready["profile"]["title"][key]) <= 1
            # Stress long actual localized titles at 200% text size: natural
            # header growth, no ellipsis/clipping/overlap or horizontal scroll.
            for tab in ("mashq", "profile"):
                page.locator(f'#nav button[data-s="{tab}"]').click()
                title = page.locator(f"#s-{tab} h1")
                title.evaluate("el => {el.textContent = Array(8).fill(el.textContent).join(' '); el.style.fontSize = '40px'}")
                assert title.evaluate("el => el.scrollHeight <= el.clientHeight + 1 && el.scrollWidth <= el.clientWidth + 1")
                header = page.locator(f"#s-{tab} > .htop").bounding_box()
                body = page.locator(f"#s-{tab} > .htop + *").bounding_box()
                assert body["y"] >= header["y"] + header["height"] - 1
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                if tab == "profile":
                    for button in page.locator(".profile-head-actions button").all():
                        box = button.bounding_box()
                        assert box["width"] >= 44 and box["height"] >= 44
                        assert title.bounding_box()["x"] + title.bounding_box()["width"] <= box["x"]
            assert errors == []
        finally:
            browser.close()


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


def test_course_goal_ring_navigates_and_renders_profile_once():
    """The XP ring must not remount the Profile immediately after App.show."""
    data = json.loads((STATIC / "course_v3_data/hsk1.json").read_text(encoding="utf-8"))
    data["authenticated"] = True
    data["level"] = "hsk1"
    data["user"] = {
        "name": "Verified", "avatar": "阿", "language": "ru",
        "is_paid": True, "state": "TRIAL_ACTIVE",
        "onboarding_completed": True,
    }

    def serve(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(status=200, content_type="text/html", body=pwa_document())
        elif path == "/api/v3/pwa-auth/session":
            route.fulfill(status=200, json={"ok": True, "user_id": 31, "csrf": "test-csrf"})
        elif path == "/api/v3/pwa/map":
            route.fulfill(status=200, json=data, headers={"X-HSK-PWA-User-ID": "31"})
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
        browser = getattr(playwright, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        try:
            page = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True).new_page()
            page.set_default_timeout(15000)
            page.route("**/*", serve)
            page.goto(ORIGIN + "/iphone-pwa/course?lang=ru&onboarded=1", wait_until="domcontentloaded")
            page.locator("#s-course .uban").first.wait_for()
            assert page.locator("#goalring").count() == 1
            renders = page.evaluate("""() => {
                const previous = window.renderProfile;
                if (typeof previous !== "function") throw new Error("Profile renderer missing");
                let count = 0;
                window.renderProfile = function () {
                    count++;
                    return previous.apply(this, arguments);
                };
                try {
                    document.getElementById("goalring").click();
                    if (window.SCREEN !== "profile") throw new Error("Goal ring did not navigate");
                    return count;
                } finally {
                    window.renderProfile = previous;
                }
            }""")
            assert renders == 1
            assert page.locator("#s-profile").get_attribute("class").split().count("on") == 1
        finally:
            browser.close()


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
            # A failed Friends GET must retain the independent reserved
            # invite/summary/row slots, then retry a fresh request.
            friends_anchors = {
                "invite": "#s-rating .pwa-friends-body .pwa-friends-invite",
                "summary": "#s-rating .pwa-friends-body .pwa-friends-summary",
                "first-row": "#s-rating .pwa-friends-body .pwa-rating-row",
                "nav": "#nav",
            }
            friends_loading_boxes = capture_geometry(page, friends_anchors)
            held["friends"].pop().fulfill(status=503, json={"ok": False})
            page.locator("#s-rating .pwa-rating-error button").wait_for(state="visible")
            assert_reserved_layout(
                friends_loading_boxes, capture_geometry(page, friends_anchors)
            )
            assert page.locator("#s-course .uban").count() > 0
            page.locator("#s-rating .pwa-rating-error button").click()
            page.locator("#s-rating .pwa-friends-body[aria-busy=true]").wait_for()
            assert len(held["friends"]) == 1
            assert_reserved_layout(
                friends_loading_boxes, capture_geometry(page, friends_anchors)
            )
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
            # App.show(profile) intentionally remounts on NAVIGATION. The
            # independent analytics response must preserve this current header.
            page.locator("#s-profile .profile-head").evaluate(
                "(node) => node.dataset.apiPreserve = 'yes'"
            )
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
            # The quota is already visible as "checking access"; wait for the
            # verified response to replace it rather than reading a race.
            page.wait_for_function(
                "() => /2/.test(document.getElementById('voice-quota').textContent)"
            )
            assert "2" in page.locator("#voice-quota").inner_text()
            page.locator('#nav button[data-s="course"]').click()
            page.locator('#nav button[data-s="voice"]').click()
            page.wait_for_function("() => !!renderVoice._quotaPending")
            assert len(held["voice"]) == 1
            held["voice"].pop().fulfill(
                status=200, headers={"X-HSK-PWA-User-ID": "31"}, json={"ok": True, "remaining_voice_limit": 1},
            )
            # The quota is already visible as "checking access"; wait for the
            # verified response to replace it rather than reading a race.
            page.wait_for_function(
                "() => /1/.test(document.getElementById('voice-quota').textContent)"
            )
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
                body=(STATIC / "iphone-pwa-voice.html").read_text(encoding="utf-8"),
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
                page.wait_for_function("() => !!window.HskPwaPracticeBoot")
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


@pytest.mark.parametrize("width", [320, 390, 430])
@pytest.mark.parametrize("motion", ["reduce", "no-preference"])
@pytest.mark.parametrize("language", ["uz", "ru", "tj"])
def test_practice_initial_loading_geometry_matches_six_real_cards(width, motion, language):
    """Measure the actual Practice first-paint placeholders against rendered cards.

    Keep /api/v3/pwa/map unresolved while App.show selects Practice. No real
    user information or Pro/Trial data may be used to build these placeholders.
    """
    from tests.pwa_layout_geometry import assert_reserved_layout, capture_geometry

    payload = json.loads((STATIC / "course_v3_data/hsk1.json").read_text(encoding="utf-8"))
    payload["authenticated"] = True
    payload["level"] = "hsk1"
    payload["user"] = {
        "name": "Authorized test account", "avatar": "阿",
        "language": language, "is_paid": True, "state": "PRO_ACTIVE",
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

    def geometry(page):
        anchors = capture_geometry(page, {
            "title": "#s-mashq .section-title",
            "header": "#s-mashq .htop",
            "first-section": "#s-mashq .sech",
            "nav": "#nav",
        })
        rows = page.locator("#s-mashq .mashq-group > *")
        assert rows.count() == 6
        groups = page.locator("#s-mashq .mashq-group")
        assert groups.count() == 2
        for i in range(2):
            rect = groups.nth(i).bounding_box()
            assert rect is not None
            anchors[f"group-{i+1}"] = rect
        for i in range(6):
            rect = rows.nth(i).bounding_box()
            assert rect is not None
            anchors[f"card-{i+1}"] = rect
        return anchors

    with sync_playwright() as playwright:
        browser = getattr(playwright, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        try:
            page = browser.new_context(
                viewport={"width": width, "height": 844},
                is_mobile=True, reduced_motion=motion,
            ).new_page()
            page.set_default_timeout(15000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route("**/*", serve)
            page.goto(ORIGIN + f"/iphone-pwa/course?lang={language}", wait_until="domcontentloaded")
            page.wait_for_function("() => typeof App === 'object' && typeof App.show === 'function'")
            page.wait_for_function("() => !!document.querySelector('#s-mashq .pwa-mashq-shell')")
            page.evaluate("App.show('mashq')")
            page.locator("#s-mashq .pwa-mashq-shell[aria-busy=true]").wait_for()
            assert len(held) == 1
            assert page.locator("#s-mashq .row-card").count() == 0
            # Known labels use the exact ready typography and natural font
            # wrapping; only the icon slots remain placeholders. No links or
            # buttons become actionable before the authenticated map arrives.
            rows = page.locator("#s-mashq .pwa-practice-row")
            assert rows.count() == 6
            initial_title = rows.first.locator("b").inner_text()
            page.evaluate("language => App.setLang(language === 'ru' ? 'uz' : 'ru')", language)
            assert rows.first.locator("b").inner_text() != initial_title
            page.evaluate("language => App.setLang(language)", language)
            assert rows.first.locator("b").inner_text() == initial_title
            assert page.locator("#s-mashq .pwa-mashq-shell button, #s-mashq .pwa-mashq-shell a").count() == 0
            shell_copy = page.evaluate("""() => ({
                title: document.querySelector('#s-mashq h1').textContent,
                subtitle: document.querySelector('#s-mashq .sub').textContent,
                sections: [...document.querySelectorAll('#s-mashq .sech')].map(el => el.textContent),
                rows: [...document.querySelectorAll('#s-mashq .pwa-practice-row .rt')].map(el => el.textContent),
            })""")
            assert shell_copy["title"] and shell_copy["subtitle"]
            for row in rows.all():
                assert row.evaluate("el => parseFloat(getComputedStyle(el).minHeight)") == 68
                assert row.locator("b").is_visible() and row.locator("b").inner_text().strip()
                assert row.locator("small").is_visible() and row.locator("small").inner_text().strip()
                assert row.locator(".ti2.pwa-layout-ink[aria-hidden=true]").count() == 1
                assert row.get_attribute("aria-hidden") is None
            before = geometry(page)
            if motion == "reduce":
                assert page.locator("#s-mashq .pwa-layout-ink").first.evaluate(
                    "(el) => getComputedStyle(el).animationName"
                ) == "none"
            held.pop().fulfill(status=200, json=payload, headers={
                "X-HSK-PWA-User-ID": "31", "Cache-Control": "no-store",
            })
            page.locator("#s-mashq .row-card").first.wait_for()
            after = geometry(page)
            assert_reserved_layout(before, after)
            assert shell_copy == page.evaluate("""() => ({
                title: document.querySelector('#s-mashq h1').textContent,
                subtitle: document.querySelector('#s-mashq .sub').textContent,
                sections: [...document.querySelectorAll('#s-mashq .sech')].map(el => el.textContent),
                rows: [...document.querySelectorAll('#s-mashq .row-card .rt')].map(el => el.textContent),
            })""")
            assert page.locator("#s-mashq .pwa-mashq-shell").count() == 0
            assert page.locator("#s-mashq .row-card").count() == 6
            assert page.locator("#s-course .uban").count() > 0
            assert errors == []
        finally:
            browser.close()


@pytest.mark.parametrize("width", [320, 390, 430])
@pytest.mark.parametrize("motion", ["reduce", "no-preference"])
def test_voice_shell_matches_panda_quota_and_call_layout(width, motion):
    """Check real Voice static→verified DOM geometry with optional quota held."""
    from tests.pwa_layout_geometry import assert_reserved_layout, capture_geometry

    payload = json.loads((STATIC / "course_v3_data/hsk1.json").read_text(encoding="utf-8"))
    payload["authenticated"] = True
    payload["level"] = "hsk1"
    payload["user"] = {
        "name": "Verified", "avatar": "阿", "language": "ru",
        "is_paid": True, "state": "PRO_ACTIVE", "onboarding_completed": True,
    }
    maps, quotas, errors = [], [], []

    def serve(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(status=200, content_type="text/html", body=pwa_document())
        elif path == "/api/v3/pwa-auth/session":
            route.fulfill(status=200, json={"ok":True, "user_id":31, "csrf":"test-csrf"})
        elif path == "/api/v3/pwa/map":
            maps.append(route)
        elif path == "/api/v3/pwa/voice/me":
            quotas.append(route)
        elif path.startswith("/api/"):
            route.fulfill(status=404, json={"ok":False, "error":"not_mocked"})
        else:
            file = (STATIC / path.lstrip("/")).resolve()
            if file.is_file() and file.is_relative_to(STATIC.resolve()):
                mime, _ = mimetypes.guess_type(file)
                route.fulfill(path=str(file), content_type=mime or "application/octet-stream")
            else:
                route.fulfill(status=404, body="")

    slots = {
        "title": ("#s-voice .section-title", "#s-voice .section-title"),
        "header": ("#s-voice .htop", "#s-voice .htop"),
        "panel": ("#s-voice .voicebox", "#s-voice .voicebox"),
        "panda": ("#s-voice .voicebox .pd", "#s-voice .voicebox .pd"),
        "title-line": ("#s-voice .voicebox h3", "#s-voice .voicebox h3"),
        "description": ("#s-voice .voicebox > p:not(.voice-quota)", "#s-voice .voicebox > p:not(.voice-quota)"),
        "quota": ("#s-voice .voice-quota", "#s-voice .voice-quota"),
        "call": ("#s-voice .pwa-voice-call", "#s-voice .voicebox button"),
        "nav": ("#nav", "#nav"),
    }
    def geometry(page, ready=False):
        return capture_geometry(page, {
            key: pair[int(ready)] for key, pair in slots.items()
        })

    with sync_playwright() as playwright:
        browser = getattr(playwright, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        try:
            page = browser.new_context(
                viewport={"width":width, "height":844}, is_mobile=True,
                reduced_motion=motion,
            ).new_page()
            page.set_default_timeout(15000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route("**/*", serve)
            page.goto(ORIGIN + "/iphone-pwa/course?lang=ru", wait_until="domcontentloaded")
            page.wait_for_function("() => typeof App === 'object' && typeof App.show === 'function'")
            page.evaluate("App.show('voice')")
            page.locator("#s-voice .pwa-voice-shell[aria-busy=true]").wait_for()
            assert len(maps) == 1
            assert page.locator("#s-voice .voicebox button").count() == 0
            before = geometry(page)
            if motion == "reduce":
                assert page.locator("#s-voice .pwa-voice-panda").evaluate(
                    "(el) => getComputedStyle(el).animationName"
                ) == "none"
            maps.pop().fulfill(status=200, json=payload, headers={
                "X-HSK-PWA-User-ID":"31", "Cache-Control":"no-store",
            })
            page.locator("#s-voice .voicebox button").wait_for()
            page.wait_for_function("() => typeof renderVoice !== 'undefined' && !!renderVoice._quotaPending")
            # Existing Panda entrance animates the illustration's transform for
            # 620ms. Measure stable layout after it settles, not its intentional
            # visual bounce; reduced-motion is measured without any delay.
            if motion != "reduce":
                page.wait_for_timeout(650)
            after = geometry(page, ready=True)
            assert_reserved_layout(before, after)
            assert page.locator("#s-voice .pwa-voice-shell").count() == 0
            assert len(quotas) == 1
            quotas.pop().fulfill(
                status=200, headers={"X-HSK-PWA-User-ID":"31"},
                json={"ok":True, "remaining_voice_limit":2},
            )
            page.locator("#voice-quota").get_by_text("2", exact=False).wait_for()
            assert page.locator("#s-course .uban").count() > 0
            assert errors == []
        finally:
            browser.close()



@pytest.mark.parametrize("width", [320, 390, 430])
@pytest.mark.parametrize("motion", ["reduce", "no-preference"])
def test_profile_first_paint_shell_matches_identity_accuracy_and_calendar(width, motion):
    """Compare the initial unverified shell with verified Profile DOM anchors."""
    from tests.pwa_layout_geometry import assert_reserved_layout, capture_geometry

    payload = json.loads((STATIC / "course_v3_data/hsk1.json").read_text(encoding="utf-8"))
    payload["authenticated"] = True
    payload["level"] = "hsk1"
    payload["user"] = {
        "name": "Authorized", "avatar": "阿", "language": "ru",
        "is_paid": True, "state": "TRIAL_ACTIVE", "onboarding_completed": True,
    }
    maps, profile_reads, errors = [], [], []

    def serve(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(status=200, content_type="text/html", body=pwa_document())
        elif path == "/api/v3/pwa-auth/session":
            route.fulfill(status=200, json={"ok":True, "user_id":31, "csrf":"test-csrf"})
        elif path == "/api/v3/pwa/map":
            maps.append(route)
        elif path == "/api/v3/pwa/profile":
            profile_reads.append(route)
        elif path.startswith("/api/"):
            route.fulfill(status=404, json={"ok":False, "error":"not_mocked"})
        else:
            file = (STATIC / path.lstrip("/")).resolve()
            if file.is_file() and file.is_relative_to(STATIC.resolve()):
                mime, _ = mimetypes.guess_type(file)
                route.fulfill(path=str(file), content_type=mime or "application/octet-stream")
            else:
                route.fulfill(status=404, body="")

    selectors = {
        "header": "#s-profile .profile-head",
        "title": "#s-profile .profile-title",
        "hero": "#s-profile .phero",
        "avatar": "#s-profile .pav",
        "friend-row": "#s-profile .profile-friends-link",
        "accuracy": "#s-profile .profile-accuracy",
        "ring-1": "#s-profile .profile-accuracy .accuracy-ring",
        "first-section": "#s-profile .sech",
        "calendar": "#s-profile .card2",
        "achievements": "#s-profile .profile-compact-ach",
        "nav": "#nav",
    }

    with sync_playwright() as playwright:
        browser = getattr(playwright, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        try:
            page = browser.new_context(
                viewport={"width":width, "height":844}, is_mobile=True,
                reduced_motion=motion,
            ).new_page()
            page.set_default_timeout(15000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route("**/*", serve)
            page.goto(ORIGIN + "/iphone-pwa/course?lang=ru", wait_until="domcontentloaded")
            page.wait_for_function("() => typeof App === 'object' && typeof App.show === 'function'")
            page.evaluate("App.show('profile')")
            page.locator("#s-profile .pwa-profile-shell[aria-busy=true]").wait_for()
            assert len(maps) == 1
            assert page.locator("#s-profile .profile-display-name").count() == 0
            before = capture_geometry(page, selectors)
            maps.pop().fulfill(status=200, json=payload, headers={
                "X-HSK-PWA-User-ID":"31", "Cache-Control":"no-store",
            })
            page.locator("#s-profile .profile-display-name").wait_for()
            page.locator("#s-profile .hsk-pwa-profile-accuracy-loading").wait_for()
            after = capture_geometry(page, selectors)
            assert_reserved_layout(before, after)
            assert page.locator("#s-profile .pwa-profile-shell").count() == 0
            assert len(profile_reads) == 1
            profile_reads.pop().fulfill(
                status=200, headers={"X-HSK-PWA-User-ID":"31"},
                json={"ok":True,"stats":{"answer_accuracy":{
                    "overall":{"percent":77}, "today":{"percent":83},
                }}},
            )
            page.get_by_text("77%", exact=True).wait_for()
            badge = page.locator("#s-profile .profile-access-badge").inner_text().strip()
            assert "Пробный" in badge, "Trial access must retain the trial label"
            assert badge != "Pro", "Trial access must never appear as paid Pro"
            assert errors == []
        finally:
            browser.close()


@pytest.mark.parametrize("width", [320, 390, 430])
@pytest.mark.parametrize("participant_count", [0, 1, 4])
def test_rating_short_leaderboard_preserves_first_row_geometry(width, participant_count):
    """PWA Top-5 heading is a reserved slot even with fewer than five users."""
    from tests.pwa_layout_geometry import capture_geometry, assert_reserved_layout
    payload = json.loads((STATIC / "course_v3_data/hsk1.json").read_text(encoding="utf-8"))
    payload["authenticated"] = True
    payload["level"] = "hsk1"
    payload["user"] = {"name":"Verified", "avatar":"阿","language":"ru","is_paid":True,
                       "state":"PRO_ACTIVE","onboarding_completed":True}
    held = []
    errors = []
    def serve(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(status=200, content_type="text/html", body=pwa_document())
        elif path == "/api/v3/pwa-auth/session":
            route.fulfill(status=200, json={"ok":True,"user_id":31,"csrf":"test-csrf"})
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
        "title":"#s-rating .rating-title",
        "podium":"#s-rating .rating-podium-list",
        "members":"#s-rating .rating-podium-meta",
        "top-five":"#s-rating .rating-podium-queue",
        "nav":"#nav",
    }
    with sync_playwright() as playwright:
        browser = getattr(playwright, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        try:
            page = browser.new_context(viewport={"width":width,"height":844},
                                       is_mobile=True,reduced_motion="reduce").new_page()
            page.set_default_timeout(15000)
            page.on("pageerror", lambda err: errors.append(str(err)))
            page.route("**/*", serve)
            page.goto(ORIGIN + "/iphone-pwa/course?lang=ru", wait_until="domcontentloaded")
            page.locator("#s-course .uban").first.wait_for()
            page.locator('#nav button[data-s="rating"]').click()
            page.locator("#s-rating .pwa-rating-shell[aria-busy=true]").wait_for()
            if participant_count:
                anchors["first-row"] = "#s-rating .lr"
            before = capture_geometry(page, anchors)
            assert len(held) == 1
            held.pop().fulfill(status=200, json={
                "ok":True,"league":"Bronze","league_size":12,
                "leaderboard":[{"name":f"Student {i}","rank":i,"xp":100-i*10,
                                "total_xp":900-i*25}
                               for i in range(1,participant_count+1)]
            })
            if participant_count:
                page.get_by_text("Student 1", exact=True).wait_for()
            else:
                page.locator("#s-rating .pwa-rating-empty[role=status]").wait_for()
            ready = capture_geometry(page, anchors)
            assert_reserved_layout(before, ready)
            assert page.locator("#s-rating .rating-podium-queue").count() == 1
            assert page.locator("#s-rating .lr").count() == participant_count
            if participant_count == 0:
                assert page.locator("#s-rating .pwa-rating-empty").is_visible()
                assert page.locator("#s-rating .pwa-rating-empty").evaluate("(node) => node.getBoundingClientRect().height >= 305")
                assert page.locator("#s-rating [aria-busy=true]").count() == 0
            else:
                assert page.locator("#s-rating .pwa-rating-empty").count() == 0
            assert page.locator("#s-course .uban").count() > 0
            assert not errors
        finally:
            browser.close()


@pytest.mark.parametrize("width", [320, 390, 430])
@pytest.mark.parametrize("language", ["uz", "ru", "tj"])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_rating_and_friends_headers_match_root_chrome_across_states(width, language, theme):
    """Compare real text/header anchors; all API responses are synthetic."""
    payload = json.loads((STATIC / "course_v3_data/hsk1.json").read_text())
    payload.update(authenticated=True, level="hsk1")
    payload["user"] = {"name": "Layout fixture", "avatar": "阿", "language": language,
                       "is_paid": True, "state": "PRO_ACTIVE", "onboarding_completed": True}
    held, errors, snapshots = {"rating": [], "friends": []}, [], {}

    def serve(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(status=200, content_type="text/html", body=pwa_document().replace(
                'lang="ru"', f'lang="ru" data-hsk-theme="{theme}"', 1))
        elif path == "/api/v3/pwa-auth/session":
            route.fulfill(status=200, json={"ok": True, "user_id": 31, "csrf": "test-csrf"})
        elif path == "/api/v3/pwa/map":
            route.fulfill(status=200, json=payload, headers={"X-HSK-PWA-User-ID": "31"})
        elif path == "/api/v3/pwa/gamification":
            held["rating"].append(route)
        elif path == "/api/v3/pwa/invite":
            held["friends"].append(route)
        elif path.startswith("/api/"):
            route.fulfill(status=404, json={"ok": False})
        else:
            file = (STATIC / path.lstrip("/")).resolve()
            if file.is_file() and file.is_relative_to(STATIC.resolve()):
                mime, _ = mimetypes.guess_type(file)
                route.fulfill(path=str(file), content_type=mime or "application/octet-stream")
            else:
                route.fulfill(status=404, body="")

    def snapshot(page, name, selector):
        snapshots[name] = page.locator(selector).evaluate("""el => {
            const range = document.createRange(); range.selectNodeContents(el);
            const text = range.getBoundingClientRect(), box = el.getBoundingClientRect();
            return {text: {x:text.x,y:text.y,height:text.height},
                    box:{x:box.x,y:box.y,width:box.width,height:box.height},
                    navY:document.querySelector('#nav').getBoundingClientRect().y};
        }""")
        folder = os.getenv("HSK_RATING_REVIEW_DIR")
        if folder:
            Path(folder).mkdir(parents=True, exist_ok=True)
            engine = os.getenv("PWA_E2E_ENGINE", "chromium")
            page.screenshot(path=str(Path(folder) / f"{engine}-{width}-{language}-{theme}-{name}.png"))

    with sync_playwright() as playwright:
        browser = getattr(playwright, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        try:
            page = browser.new_page(viewport={"width": width, "height": 568 if width == 320 else 932},
                                    is_mobile=True, color_scheme=theme, reduced_motion="reduce")
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route("**/*", serve)
            page.goto(ORIGIN + f"/iphone-pwa/course?lang={language}", wait_until="domcontentloaded")
            page.locator("#s-course .uban").first.wait_for()
            page.locator('#nav button[data-s="mashq"]').click()
            snapshot(page, "reference", "#s-mashq h1")
            reference_header = page.locator("#s-mashq > .htop").bounding_box()
            page.locator('#nav button[data-s="rating"]').click()
            page.locator("#s-rating .pwa-rating-shell[aria-busy=true]").wait_for()
            snapshot(page, "initial", "#s-rating h1")
            assert len(held["rating"]) == 1
            held["rating"].pop().fulfill(status=503, json={"ok": False})
            page.locator("#s-rating .pwa-rating-error button").wait_for()
            snapshot(page, "error", "#s-rating h1")
            page.locator("#s-rating .pwa-rating-error button").click()
            page.locator("#s-rating [aria-busy=true]").wait_for()
            snapshot(page, "retry", "#s-rating h1")
            held["rating"].pop().fulfill(status=200, json={
                "ok": True, "league": "Bronze", "league_size": 0, "leaderboard": []})
            page.locator("#s-rating .pwa-rating-empty").wait_for()
            snapshot(page, "empty", "#s-rating h1")
            page.evaluate("App.openFriends()")
            page.locator("#s-rating .pwa-friends-body[aria-busy=true]").wait_for()
            snapshot(page, "friends-pending", "#s-rating h1")
            assert len(held["friends"]) == 1
            held["friends"].pop().fulfill(status=503, json={"ok": False})
            page.locator("#s-rating .pwa-rating-error button").wait_for()
            snapshot(page, "friends-error", "#s-rating h1")
            page.locator("#s-rating .pwa-rating-error button").click()
            page.locator("#s-rating .pwa-friends-body[aria-busy=true]").wait_for()
            snapshot(page, "friends-retry", "#s-rating h1")
            assert len(held["friends"]) == 1
            held["friends"].pop().fulfill(status=200, headers={"X-HSK-PWA-User-ID": "31"}, json={
                "ok": True, "joined_count": 0, "active_count": 0, "required": 3, "referrals": []})
            page.locator("#s-rating .ref-stat").wait_for()
            snapshot(page, "friends-empty", "#s-rating h1")
            folder = os.getenv("HSK_RATING_REVIEW_DIR")
            if folder:
                (Path(folder) / f"{width}-{language}-{theme}.json").write_text(json.dumps(snapshots, indent=2))
            for name, actual in snapshots.items():
                if name == "reference":
                    continue
                for key in ("x", "y", "height"):
                    assert abs(actual["text"][key] - snapshots["reference"]["text"][key]) <= 1, (name, snapshots)
                assert abs(actual["box"]["height"] - reference_header["height"]) <= 1, (name, snapshots)
                assert abs(actual["navY"] - snapshots["reference"]["navY"]) <= 1
            # Long localized text remains fully visible and grows in normal flow.
            title = page.locator("#s-rating h1")
            title.evaluate("el => {el.textContent = Array(4).fill(el.textContent).join(' '); el.style.fontSize='40px'}")
            assert title.evaluate("el => el.scrollWidth <= el.clientWidth + 1 && el.scrollHeight <= el.clientHeight + 1")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert title.evaluate("el => {const a=el.getBoundingClientRect(),b=el.nextElementSibling.getBoundingClientRect(); return b.y >= a.bottom-1}")
            page.locator('#nav button[data-s="course"]').click()
            assert page.locator("#s-course.on .uban").first.is_visible()
            assert not errors
        finally:
            browser.close()

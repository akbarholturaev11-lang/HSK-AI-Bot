"""Independent PWA section loading with real bundled JS and mocked HTTP.

Runs in Chromium and WebKit; every request is handled locally, no production
credentials or account data. Start the canonical PWA course with the same
public bootstrap shell the authenticated delivery injects.
"""
import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

from test_pwa_initial_shell import parts

STATIC = Path(__file__).resolve().parents[2] / "app/static"
ORIGIN = "http://hsk-ai.local"


def pwa_document():
    source = (STATIC / "course-v3.html").read_text(encoding="utf-8")
    fragments = parts()
    source = source.replace(
        "</head>", fragments["_PWA_COURSE_BOOT_HEAD"] + "</head>", 1
    ).replace(
        '<body class="hsk-scene-page">',
        '<body class="hsk-scene-page hsk-pwa-shell-loading">', 1
    ).replace(
        '<div class="scr on" id="s-course"><div class="loading">…</div></div>',
        fragments["_PWA_COURSE_SKELETON_NEW"], 1
    ).replace('<nav class="nav" id="nav">', '<nav class="nav" id="nav" inert>', 1)
    source = source.replace(
        '<script src="/assets/telegram-web-app.js?v=20261019-1"></script>', "", 1
    )
    source = source.replace(
        "</body>", fragments["_PWA_COURSE_BOOT_SCRIPT"] + "</body>", 1
    )
    return source


def test_course_ready_while_rating_referrals_and_profile_stats_load_independently():
    data = json.loads((STATIC / "course_v3_data/hsk1.json").read_text(encoding="utf-8"))
    data["authenticated"] = True
    data["level"] = "hsk1"
    data["user"] = {
        "name": "Verified Test", "avatar": "阿", "language": "ru",
        "is_paid": False, "state": "FREE", "onboarding_completed": True,
        "referral_code": "", "display_name": "", "avatar_key": "",
    }
    data["progress"]["completed"] = 0
    data["notify"] = {"enabled": True}
    held = {"rating": [], "profile": [], "friends": []}
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

            page.locator('#nav button[data-s="rating"]').click()
            page.locator("#s-rating .hsk-pwa-section-loading").wait_for()
            assert len(held["rating"]) == 1
            page.evaluate("App.setLang('uz')")
            assert page.locator("#s-rating .hsk-pwa-section-loading").is_visible()
            assert len(held["rating"]) == 1
            # The course has already loaded; a slow leaderboard cannot undo it.
            assert page.locator("#s-course .uban").count() > 0
            held["rating"].pop().fulfill(status=200, json={
                "ok": True, "league": "Bronze", "league_size": 1,
                "leaderboard": [{"name": "Rank verified", "rank": 1, "xp": 27}],
            })
            page.get_by_text("Rank verified").wait_for()
            assert page.locator("#s-rating .hsk-pwa-section-loading").count() == 0

            page.locator('#nav button[data-s="profile"]').click()
            page.locator("#s-profile .hsk-pwa-profile-accuracy-loading").wait_for()
            assert len(held["profile"]) == 1
            # Profile settings/name are present even though accuracy is pending.
            assert page.locator("#s-profile .profile-display-name").is_visible()
            assert page.locator("#s-profile .profile-settings").is_visible()
            held["profile"].pop().fulfill(status=200, json={
                "ok": True,
                "stats": {"answer_accuracy": {
                    "overall": {"percent": 79}, "today": {"percent": 80},
                }},
            })
            page.locator("#s-profile .profile-accuracy").wait_for()
            assert page.locator("#s-profile .hsk-pwa-profile-accuracy-loading").count() == 0

            page.evaluate("App.show('rating', 'friends')")
            page.locator("#s-rating .hsk-pwa-section-loading").wait_for()
            assert len(held["friends"]) == 1
            page.evaluate("App.setLang('ru')")
            assert len(held["friends"]) == 1
            held["friends"].pop().fulfill(status=200, json={
                "ok": True, "joined_count": 0, "active_count": 0,
                "required": 2, "referrals": [],
            })
            page.wait_for_function(
                "() => typeof referralMeta !== 'undefined' && !referralMeta.loading"
            )
            assert page.locator("#s-rating .hsk-pwa-section-loading").count() == 0
            assert errors == []
        finally:
            browser.close()

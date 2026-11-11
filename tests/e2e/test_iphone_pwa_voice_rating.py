"""Real course UI with isolated browser-session fixtures."""

import json
from urllib.parse import urlsplit

import pytest

from test_miniapp_smoke import STATIC_ROOT, app_url, expect, json_response, page


@pytest.fixture()
def learner_page(page):
    data = json.loads((STATIC_ROOT / "course_v3_data/hsk1.json").read_text())
    data.update(authenticated=True, level="hsk1", user={
        "name": "Browser Learner", "language": "uz", "onboarding_completed": True,
    })
    page.route("**/api/v3/pwa/**", lambda route: json_response(route, {"ok": True}))
    page.route("**/api/v3/pwa-auth/session", lambda route: json_response(
        route, {"ok": True, "csrf": "fixture-csrf", "user_id": 1},
    ))
    page.route("**/api/v3/pwa/map?*", lambda route: json_response(
        route, data, headers={"X-HSK-PWA-User-ID": "1"},
    ))
    page.route("**/iphone-pwa/course?*", lambda route: route.fulfill(
        content_type="text/html", body=(STATIC_ROOT / "course-v3.html").read_text(),
    ))
    page.goto(app_url("/iphone-pwa/course?lang=uz&tab=course"))
    expect(page.locator("#s-course.on")).to_be_visible()
    return page


def swipe_back(page):
    page.evaluate("""() => {
        const target = document.elementFromPoint(105, 440);
        for (const [type, x] of [['touchstart', 105], ['touchmove', 205], ['touchend', 215]]) {
            const event = new Event(type, {bubbles: true, cancelable: true});
            Object.defineProperty(event, 'touches', {
                value: type === 'touchend' ? [] : [{clientX: x, clientY: 440}]
            });
            target.dispatchEvent(event);
        }
    }""")


def test_voice_swipe_closes_top_layer_and_old_reply_cannot_cross_sessions(learner_page):
    page = learner_page
    pending = []
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    # The real Voice status read names its verified owner; PR #284 rejects a
    # response that cannot prove it belongs to the course map's account.
    page.route("**/api/v3/pwa/voice/me", lambda route: json_response(
        route, {"ok": True, "remaining_voice_limit": 2},
        headers={"X-HSK-PWA-User-ID": "1"},
    ))
    page.route("**/api/v3/pwa/voice/session/start", lambda route: json_response(route, {
        "ok": True, "session_id": "voice-test", "live_available": False,
        "opening_message": {"chinese_reply": "你好！", "pinyin": "nǐ hǎo", "translation": "Salom"},
    }))
    page.route("**/api/v3/pwa/voice/message", lambda route: pending.append(route))
    page.locator('.nav [data-s="voice"]').click()
    expect(page.locator("#voice-quota")).to_contain_text("2")
    start = page.locator("#s-voice .voicebox button")
    start.click()
    expect(page.locator("#vc-chat .msg.ai")).to_contain_text("你好")
    page.locator("#vc-root .top .ic").last.click()
    expect(page.locator("#vc-setSheet.on")).to_be_visible()
    swipe_back(page)
    expect(page.locator("#vc-setSheet.on")).to_have_count(0)
    expect(page.locator("#secov.on")).to_be_visible()
    page.locator("#vc-root .row .sq").first.click()
    page.locator("#vc-kbText").fill("我很好")
    page.locator("#vc-kbSend").click()
    expect(page.locator("#vc-typing")).to_be_visible()
    swipe_back(page)
    expect(page.locator("#vc-kbPanel.on")).to_have_count(0)
    swipe_back(page)
    expect(page.locator("#secov.on")).to_have_count(0)
    start.click()
    expect(page.locator("#vc-chat .msg.ai")).to_contain_text("你好")
    assert len(pending) == 1
    assert pending[0].request.headers["x-hsk-pwa-csrf"] == "fixture-csrf"
    assert "initData" not in pending[0].request.post_data
    with page.expect_response("**/api/v3/pwa/voice/message"):
        json_response(pending[0], {"ok": True, "chinese_reply": "你好吗？"})
    page.wait_for_timeout(200)
    expect(page.locator("#vc-chat .msg.ai")).to_have_count(1)
    assert not errors


def test_browser_rating_shows_user_profile_without_telegram_controls(learner_page):
    page = learner_page
    requests = []
    page.on("request", lambda request: requests.append(urlsplit(request.url).path))
    page.route("**/api/v3/pwa/gamification", lambda route: json_response(route, {
        "ok": True, "league": "Gold", "league_size": 1,
        "leaderboard": [{
            "name": "League Learner", "rank": 1, "xp": 35, "league": "Gold",
            "telegram_id": 42, "username": "legacy-link",
        }],
    }))
    page.locator('.nav [data-s="rating"]').click()
    # Layout-matched skeleton rows reuse the decorative `.lr` geometry but are
    # aria-hidden <div>s; only verified leaderboard rows are buttons.
    page.locator("#s-rating button.lr").click()
    expect(page.locator("#upov.on .nm")).to_have_text("League Learner")
    expect(page.locator("#upov .bg-lg")).to_have_text("青龙")
    expect(page.locator("#upov .upacts")).to_have_count(0)
    assert not any(path.startswith("/api/v3/avatar/") for path in requests)
    swipe_back(page)
    expect(page.locator("#upov.on")).to_have_count(0)
    expect(page.locator("#s-rating.on")).to_be_visible()

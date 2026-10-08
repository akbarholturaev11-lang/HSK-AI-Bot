"""A server-confirmed streak follows the result and preserves the next action."""
import json
import re

import pytest

from test_miniapp_smoke import (
    app_url,
    expect,
    json_response,
    mock_course_map,
    mock_learning_audio,
    mock_price_preview,
    mock_telegram_ready,
    page,
)


def complete_lesson(page, *, checkpoint=False, updated=True, duplicate=False, snapshot_duplicate=False):
    mock_price_preview(page)
    mock_telegram_ready(page)
    mock_course_map(page)
    mock_learning_audio(page)
    page.route("**/api/miniapp/event", lambda r: json_response(r, {"ok": True}))
    completed = []

    def reply(route):
        completed.append(json.loads(route.request.post_data))
        json_response(route, {
            "ok": True,
            "duplicate": duplicate,
            "completed_lessons_count": 3 if checkpoint else 1,
            "gamification": {
                "duplicate": snapshot_duplicate,
                "streak": 6,
                "previous_streak": 5 if updated else 6,
                "streak_updated": updated,
                "awarded_xp": 20,
                "local_date": "2026-10-08",
                "week_start": "2026-10-05",
                "week_activity_dates": ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08"],
            },
        })

    page.route("**/api/v3/lesson/complete", reply)
    page.add_init_script("localStorage.setItem('hsk_v3_onb','1');")
    page.goto(app_url('/course-v3.html?lang=uz&level=hsk1&onboarded=1'), wait_until='networkidle')
    page.evaluate("""(index) => {
        Flow.lessonIdx = index; Flow.exitRequired = [];
        Flow.graded = 1; Flow.correct = 1; Flow.startedAt = Date.now() - 20000;
        flowDone();
    }""", 2 if checkpoint else 0)
    expect(page.locator('#levelup')).to_have_class(re.compile(r'\bon\b'))
    expect(page.locator('#lu-cta')).to_be_visible(timeout=7000)
    assert completed and completed[0]['lesson_id'] == (3 if checkpoint else 1)
    return completed


@pytest.mark.parametrize('checkpoint', [False, True])
def test_fresh_streak_appears_after_the_result_then_continues(page, checkpoint, tmp_path):
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    completed = complete_lesson(page, checkpoint=checkpoint)
    expect(page.locator('#lu-cta')).to_contain_text('Davom etish')
    expect(page.locator('#lu-stage .sk-flame')).to_have_count(0)
    page.locator('#lu-cta').click()
    # The actual cinematic entrance remains wired, followed by the flame/week.
    expect(page.locator('#levelup')).to_have_class(re.compile(r'\bcine\b'))
    expect(page.locator('#lu-stage .sk-num')).to_have_text('6', timeout=7000)
    expect(page.locator('#lu-stage .sk-days .sk-day')).to_have_count(7)
    expect(page.locator('#lu-cta')).to_be_visible()
    page.locator('#levelup').evaluate("""async el => {
        await Promise.all(el.getAnimations({subtree: true})
            .filter(a => a.effect.getTiming().iterations !== Infinity)
            .map(a => a.finished.catch(() => {})));
    }""")
    page.screenshot(path=str(tmp_path / 'streak.png'))
    assert page.evaluate('window._pendingStreak') is None
    if checkpoint:
        expect(page.locator('#lu-cta')).to_contain_text('Keyingi darsni ochish')
    page.locator('#lu-cta').click()
    expect(page.locator('#levelup')).not_to_have_class(re.compile(r'\bon\b'))
    if checkpoint:
        # This free-user map protects part 4. The celebration must retain
        # the existing next-lesson access boundary.
        expect(page.locator('#paywall')).to_have_class(re.compile(r'\bon\b'))
        expect(page.locator('#paywall')).to_contain_text("darslaring tugadi")
    else:
        expect(page.locator('#s-course')).to_be_visible()
    assert len(completed) == 1
    assert not errors


@pytest.mark.parametrize('updated,duplicate,snapshot_duplicate', [
    (False, False, False),
    (True, True, False),
    (True, False, True),
])
def test_already_counted_completion_returns_without_replaying_streak(page, updated, duplicate, snapshot_duplicate):
    complete_lesson(page, updated=updated, duplicate=duplicate, snapshot_duplicate=snapshot_duplicate)
    page.locator('#lu-cta').click()
    expect(page.locator('#levelup')).not_to_have_class(re.compile(r'\bon\b'))
    expect(page.locator('#s-course')).to_be_visible()
    expect(page.locator('#lu-stage .sk-flame')).to_have_count(0)

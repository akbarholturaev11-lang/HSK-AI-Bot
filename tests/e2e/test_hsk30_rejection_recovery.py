"""Receipt rejection while the real Mini App document remains open or reloads."""
import json
import re

import pytest
from playwright.sync_api import expect
from test_miniapp_smoke import (
    STATIC_ROOT, app_url, json_response, mock_course_map, mock_price_preview,
    mock_telegram_ready, page,
)


def setup_rejection(page, *, denied=False, level="nhsk1", paid=False, language="uz", boot_level=None):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    mock_telegram_ready(page)
    mock_price_preview(page)
    mock_course_map(page, level=level)
    page.add_init_script("localStorage.setItem('hsk_v3_tour','1');localStorage.setItem('hsk_v3_onboarded','1')")
    state = {"denied": denied, "paid": paid, "status_calls": 0, "offline": False, "level": level}
    def access():
        allowed = not state["denied"] or state["paid"]
        return {"feature_enabled": True, "payment_enabled": True, "allowed": allowed,
                "payment_pending": not state["denied"] and not state["paid"], "provisional_access": not state["denied"] and not state["paid"],
                "payment_rejected": state["denied"], "paid_access": state["paid"],
                "reason": "paid_subscription" if state["paid"] else "payment_rejected" if state["denied"] else "payment_pending"}
    def tracks():
        return {"ok": True, "active_track": "hsk30" if state["level"].startswith("n") else "hsk20", "active_level": state["level"],
                "tracks": {"hsk30": {"level": "nhsk1", "live_levels": ["nhsk1"], "access": access()},
                           "hsk20": {"level": "hsk1", "has_state": True}},
                "hsk30_unlock": {"payment_enabled": True, "price_tjs": 10, "price_display": "10 TJS"},
                "hsk30_promo": {"eligible": False}}
    def status_route(route):
        state["status_calls"] += 1
        json_response(route, {"ok": False} if state["offline"] else tracks(), status=503 if state["offline"] else 200)
    page.route("**/api/v3/course-tracks", status_route)
    data = json.loads((STATIC_ROOT / ("course_v3_data/" + level + ".json")).read_text())
    data.update({"ok": True, "authenticated": True, "level": level,
                 "user": {"language": language, "name": "QA", "onboarding_completed": True, "is_paid": paid},
                 "progress": {"xp": 0, "streak": 0, "completed": 0}})
    def map_route(route):
        if state["denied"] and not state["paid"] and state["level"].startswith("n"):
            json_response(route, {"ok": False, "error": "payment_rejected", "level": level, "hsk30_access": access()}, status=403)
        else:
            current = data
            if state["level"] != level:
                current = {**json.loads((STATIC_ROOT / ("course_v3_data/" + state["level"] + ".json")).read_text()),
                           "ok": True, "authenticated": True, "level": state["level"], "user": data["user"]}
            json_response(route, {**current, "lesson_limit": {"allowed": True, "hsk30_access": access()}})
    page.route(re.compile(r".*/api/v3/map(?:\?.*)?$"), map_route)
    def switch_route(route):
        body = json.loads(route.request.post_data)
        assert body["target_track"] == "hsk20"
        state["level"] = "hsk1"
        json_response(route, tracks())
    page.route("**/api/v3/course-tracks/switch", switch_route)
    page.goto(app_url("/course-v3.html?lang=" + language + "&level=" + (boot_level or level) + "&onboarded=1"), wait_until="networkidle")
    page.wait_for_function("typeof MAP!=='undefined' && MAP!==null")
    return state, errors


def rejected_sheet(page):
    expect(page.locator("#sheet.on #sheet-body")).to_contain_text("to‘lovi qabul qilinmadi", timeout=8000)
    expect(page.locator("#sheet-body")).to_contain_text("HSK 2.0 ga qaytish")
    expect(page.locator("#sheet-body")).to_contain_text("HSK 3.0 ni ochish")
    expect(page.locator("#toast")).not_to_contain_text("Progress saqlanmadi")


def test_rejection_appears_without_navigation_and_removes_cached_practice(page, tmp_path):
    state, errors = setup_rejection(page)
    page.evaluate("App.show('mashq')")
    page.evaluate("MAP.progress.xp=42")
    state["denied"] = True
    rejected_sheet(page)
    assert page.evaluate("MAP.course_access_locked") is True
    assert page.evaluate("MAP.progress.xp") == 42
    page.evaluate("renderAll()")
    page.screenshot(path=str(tmp_path / "hsk30-rejected.png"))
    page.evaluate("App.closeSheet()")
    expect(page.locator("#s-course")).to_contain_text("HSK 2.0 ga qaytish")
    expect(page.locator("#s-mashq")).to_contain_text("to‘lovi qabul qilinmadi")
    assert not page.locator("#flow.on").count()
    assert not errors


def test_rejected_cold_boot_shows_existing_gate_and_nonempty_screens(page):
    state, errors = setup_rejection(page, denied=True)
    rejected_sheet(page)
    page.evaluate("App.closeSheet()")
    assert page.locator("#s-course").inner_text().strip()
    assert page.locator("#s-mashq").inner_text().strip()
    page.reload(wait_until="networkidle")
    rejected_sheet(page)
    assert not errors


def test_paid_access_survives_rejected_one_time_receipt(page):
    state, errors = setup_rejection(page, denied=True, paid=True)
    assert page.evaluate("refreshHsk30Access()") is True
    assert not page.evaluate("Boolean(MAP.course_access_locked)")
    expect(page.locator("#sheet.on")).to_have_count(0)
    assert not errors


def test_network_failure_is_not_treated_as_rejection(page):
    state, errors = setup_rejection(page)
    state["offline"] = True
    assert page.evaluate("refreshHsk30Access()") is False
    assert not page.evaluate("Boolean(MAP.course_access_locked)")
    expect(page.locator("#sheet.on")).to_have_count(0)
    assert not errors


def test_rejection_on_resume_and_later_approval_restore_the_map(page):
    state, errors = setup_rejection(page)
    state["denied"] = True
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    rejected_sheet(page)
    state["paid"] = True
    page.evaluate("refreshHsk30Access()")
    page.wait_for_function("MAP && !MAP.course_access_locked && MAP.units.length>0")
    expect(page.locator("#sheet.on")).to_have_count(0)
    assert not errors


def test_back_to_hsk20_recovers_saved_course_and_practice(page):
    state, errors = setup_rejection(page, denied=True)
    rejected_sheet(page)
    page.evaluate("switchCourseTrack('hsk20',null)")
    page.wait_for_function("MAP && MAP.level==='hsk1' && MAP.units.length>0")
    expect(page.locator("#sheet.on")).to_have_count(0)
    page.evaluate("App.show('mashq')")
    expect(page.locator("#s-mashq")).to_have_class(re.compile(r".*\bon\b.*"))
    expect(page.locator("#s-mashq")).not_to_contain_text("to‘lovi qabul qilinmadi")
    assert not errors


def test_hsk20_does_not_poll_or_open_hsk30_rejection(page):
    state, errors = setup_rejection(page, level="hsk1", denied=True)
    calls = state["status_calls"]
    assert page.evaluate("refreshHsk30Access()") is False
    assert state["status_calls"] == calls
    assert not page.evaluate("Boolean(MAP.course_access_locked)")
    expect(page.locator("#sheet.on")).to_have_count(0)
    assert not errors


def test_denied_lesson_start_opens_gate_instead_of_progress_error(page):
    state, errors = setup_rejection(page)
    page.route("**/api/v3/lesson/start", lambda route: json_response(route, {
        "ok": False, "allowed": False, "error": "payment_rejected"}, status=403))
    state["denied"] = True
    page.evaluate("startLesson(0,{foundationCleared:true})")
    rejected_sheet(page)
    assert not errors


def test_late_map_response_cannot_restore_revoked_access(page):
    state, errors = setup_rejection(page)
    pending = []
    page.route(re.compile(r".*/api/v3/map(?:\?.*)?$"), lambda route: pending.append(route))
    page.evaluate("() => { window.__lateMap=loadLevel('nhsk1'); }")
    page.wait_for_timeout(100)
    assert pending
    state["denied"] = True
    page.evaluate("refreshHsk30Access()")
    rejected_sheet(page)
    old_map = json.loads((STATIC_ROOT / "course_v3_data/nhsk1.json").read_text())
    old_map.update({"ok": True, "authenticated": True, "level": "nhsk1"})
    json_response(pending[0], old_map)
    page.evaluate("window.__lateMap")
    assert page.evaluate("MAP.course_access_locked") is True
    rejected_sheet(page)
    assert not errors


@pytest.mark.parametrize("language,title", [
    ("ru", "Платёж за HSK 3.0 не принят"),
    ("tj", "Пардохти HSK 3.0 қабул нашуд"),
])
def test_rejection_uses_existing_localized_dialog(page, language, title):
    state, errors = setup_rejection(page, denied=True, language=language)
    expect(page.locator("#sheet.on #sheet-body")).to_contain_text(title)
    assert not errors


def test_server_denied_track_overrides_stale_hsk20_boot_level(page):
    state, errors = setup_rejection(page, denied=True, boot_level="hsk1")
    rejected_sheet(page)
    assert page.evaluate("MAP.level") == "nhsk1"
    assert not errors

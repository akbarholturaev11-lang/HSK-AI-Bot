"""A spent allowance keeps the learner's place, and fresh attempts stay gated."""
import json
import re

import pytest

from test_miniapp_smoke import (
    STATIC_ROOT,
    _mock_drill_environment,
    app_url,
    expect,
    json_response,
    mock_course_map,
    mock_learning_audio,
    mock_price_preview,
    page,
)


REASON = "Bepul rejimda jami 1 ta mashq. Qoldi: 0."


def _promo_status(eligible=False):
    return {
        "ok": True, "active_track": "hsk20", "active_level": "hsk1",
        "tracks": {
            "hsk20": {"track": "hsk20", "level": "hsk1"},
            "hsk30": {
                "track": "hsk30", "level": "nhsk1", "live_levels": ["nhsk1", "nhsk2", "nhsk3"],
                "access": {"feature_enabled": eligible, "allowed": False, "reason": "hsk30_unlock_required"},
            },
        },
        "hsk30_unlock": {"payment_enabled": False},
        "hsk30_promo": {"eligible": eligible, "recommended_level": "nhsk1"},
    }


def _prepare(page, level="hsk1"):
    _mock_drill_environment(page, level=level)
    mock_price_preview(page)
    mock_course_map(page, level=level)
    mock_learning_audio(page)
    page.route("**/api/v3/course-tracks", lambda r: json_response(r, _promo_status()))
    page.add_init_script("localStorage.setItem('hsk_v3_onb','1');")


def _limited_gate(page):
    requests, used = [], set()

    def gate(route):
        body = json.loads(route.request.post_data)
        requests.append(body)
        key = (body["feature"], body["ref"])
        if not used or key in used:
            used.add(key)
            json_response(route, {"ok": True, "allowed": True})
        else:
            json_response(route, {"ok": False, "allowed": False,
                "error": "free_feature_limit_reached", "limit_text": REASON}, status=403)

    page.route("**/api/v3/practice/daily-gate", gate)
    return requests


def _checkpoint_map(level, allowed):
    data = json.loads((STATIC_ROOT / f"course_v3_data/{level}.json").read_text())
    data.update(authenticated=True, level=level,
        user={"language": "uz", "name": "Limit Test", "is_paid": False})
    data.setdefault("progress", {})["completed"] = 2
    data["lesson_limit"] = {"allowed": allowed, "limit_text": REASON}
    if level.startswith("nhsk"):
        data["lesson_limit"]["hsk30_access"] = {"allowed": True, "permanently_unlocked": True}
    for unit in data["units"]:
        unit.pop("status", None)
        for lesson in unit["lessons"]:
            order = lesson["n"]
            lesson["status"] = "done" if order < 3 else "current" if order == 3 else "locked"
            lesson["completion_allowed"] = order < 3 or order == 3 and allowed
            lesson["locked_premium"] = order == 3 and not allowed
            if order == 3:
                lesson["checkpoint"] = True
                lesson["completion_error"] = "" if allowed else "free_feature_limit_reached"
    return data


@pytest.mark.parametrize("level", ["hsk1", "nhsk1"])
def test_spent_checkpoint_stays_red_and_opens_the_limit_window(page, level):
    _prepare(page, level)
    data = _checkpoint_map(level, allowed=False)
    page.route(re.compile(r".*/api/v3/map(\?.*)?$"), lambda r: json_response(r, data))
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(app_url(f"/course-v3.html?lang=uz&level={level}&onboarded=1"), wait_until="networkidle")

    node = page.locator('.node[data-lesson-order="3"]')
    expect(node).to_have_class(re.compile(r"\bcurrent\b"))
    assert node.locator(".ring").evaluate("e => getComputedStyle(e).animationName") == "pl"
    node.click()
    expect(page.locator("#paywall")).to_have_class(re.compile(r"\bon\b"))
    expect(page.locator("#paywall")).to_contain_text(REASON)
    expect(node).to_have_class(re.compile(r"\bcurrent\b"))
    expect(page.locator('#flow')).not_to_have_class(re.compile(r"\bon\b"))
    expect(page.locator('.node[data-lesson-order="4"]')).to_have_class(re.compile(r"\blocked\b"))
    assert errors == []


def test_expiry_while_starting_keeps_the_red_marker(page):
    _prepare(page)
    data = _checkpoint_map("hsk1", allowed=True)
    page.route(re.compile(r".*/api/v3/map(\?.*)?$"), lambda r: json_response(r, data))
    page.route("**/api/v3/lesson/start", lambda r: json_response(r, {
        "ok": False, "allowed": False, "error": "free_feature_limit_reached", "limit_text": REASON,
    }, status=403))
    page.goto(app_url("/course-v3.html?lang=uz&level=hsk1&onboarded=1"), wait_until="networkidle")
    page.locator('.node[data-lesson-order="3"]').click()
    page.locator('#sheet .scta').click()
    expect(page.locator('#paywall')).to_have_class(re.compile(r"\bon\b"))
    expect(page.locator('#paywall')).to_contain_text(REASON)
    expect(page.locator('.node[data-lesson-order="3"]')).to_have_class(re.compile(r"\bcurrent\b"))
    expect(page.locator('#flow')).not_to_have_class(re.compile(r"\bon\b"))


@pytest.mark.parametrize("module,ready", [("RECOG", "#rc-body .rc-tile"), ("PRON", "#pr-word")])
def test_reopening_embedded_practice_consumes_a_new_attempt(page, module, ready):
    _prepare(page)
    requests = _limited_gate(page)
    page.goto(app_url("/course-v3.html?lang=uz&onboarded=1"), wait_until="networkidle")
    page.evaluate(f"{module}.open()")
    expect(page.locator(ready).first).to_be_visible()
    page.evaluate(f"{module}.close();{module}.open()")
    expect(page.locator('body')).to_contain_text(REASON)
    assert len(requests) == 2
    assert requests[0]["ref"] != requests[1]["ref"]


@pytest.mark.parametrize("module,ready", [("RECOG", "#rc-body .rc-tile"), ("PRON", "#pr-word")])
def test_an_old_attempt_loading_data_cannot_replace_a_new_limit_screen(page, module, ready):
    _prepare(page)
    _limited_gate(page)
    page.goto(app_url("/course-v3.html?lang=uz&onboarded=1"), wait_until="networkidle")
    pending = []
    page.route("**/hsk-words.js*", lambda route: pending.append(route))
    with page.expect_response("**/api/v3/practice/daily-gate"):
        page.evaluate(f"{module}.open()")
    page.evaluate(f"{module}.close();{module}.open()")
    expect(page.locator('body')).to_contain_text(REASON)
    assert pending
    for route in pending:
        route.fulfill(content_type="application/javascript", body=(STATIC_ROOT / "hsk-words.js").read_text())
    page.wait_for_function("typeof WORDS!=='undefined' && WORDS.length>0")
    expect(page.locator(ready)).to_have_count(0)
    expect(page.locator('body')).to_contain_text(REASON)


@pytest.mark.parametrize("feature", ["recognition", "pronunciation", "memorize"])
def test_standalone_reload_gets_a_new_attempt_and_server_limit_copy(page, feature):
    _prepare(page)
    requests = _limited_gate(page)
    page.goto(app_url(f"/course_v3_{feature}.html?lang=uz"), wait_until="networkidle")
    page.wait_for_function("typeof ATTEMPT_REF==='string' && ATTEMPT_REF.length>0")
    page.reload(wait_until="networkidle")
    expect(page.locator('body')).to_contain_text(REASON)
    assert len(requests) == 2
    assert requests[0]["ref"] != requests[1]["ref"]


@pytest.mark.parametrize("module,ready", [("RECOG", "#rc-body .rc-tile"), ("PRON", "#pr-word")])
@pytest.mark.parametrize("payload,status", [({}, 503), ({}, 200), ({"ok": True, "allowed": False}, 200)])
def test_gate_errors_do_not_start_practice_and_retry_reuses_the_attempt(page, module, ready, payload, status):
    _prepare(page)
    requests = []

    def gate(route):
        requests.append(json.loads(route.request.post_data))
        json_response(route, payload if len(requests) == 1 else {"ok": True, "allowed": True},
            status=status if len(requests) == 1 else 200)

    page.route("**/api/v3/practice/daily-gate", gate)
    page.goto(app_url("/course-v3.html?lang=uz&onboarded=1"), wait_until="networkidle")
    page.evaluate(f"{module}.open()")
    expect(page.locator('#secov')).to_contain_text("Ruxsatni tekshirib bo'lmadi")
    expect(page.locator(ready)).to_have_count(0)
    page.get_by_role('button', name='Qayta urinish', exact=True).click()
    expect(page.locator(ready).first).to_be_visible()
    assert len(requests) == 2
    assert requests[0]["ref"] == requests[1]["ref"]


@pytest.mark.parametrize("feature,ready", [("recognition", ".tile"), ("pronunciation", "#word"), ("memorize", "#body .opt")])
def test_standalone_gate_error_can_retry_without_spending_twice(page, feature, ready):
    _prepare(page)
    requests = []

    def gate(route):
        requests.append(json.loads(route.request.post_data))
        json_response(route, {} if len(requests) == 1 else {"ok": True, "allowed": True},
            status=503 if len(requests) == 1 else 200)

    page.route("**/api/v3/practice/daily-gate", gate)
    page.goto(app_url(f"/course_v3_{feature}.html?lang=uz"), wait_until="networkidle")
    expect(page.locator('body')).to_contain_text("Ruxsatni tekshirib bo'lmadi")
    page.get_by_role('button', name='Qayta urinish', exact=True).click()
    expect(page.locator(ready).first).to_be_visible()
    assert requests[0]["ref"] == requests[1]["ref"]


@pytest.mark.parametrize("embedded", [True, False])
def test_placement_reopening_is_a_new_attempt(page, embedded):
    _prepare(page)
    requests = _limited_gate(page)
    path = "/course-v3.html?lang=uz&onboarded=1" if embedded else "/course_v3_test.html?lang=uz"
    page.goto(app_url(path), wait_until="networkidle")
    if embedded:
        page.evaluate("TEST.open();TEST.open2('placement')")
        expect(page.locator('#tc-placement')).to_have_class(re.compile(r"\bon\b"))
        page.evaluate("TEST.showHub();TEST.open2('placement')")
    else:
        page.evaluate("openExam('placement')")
        expect(page.locator('#placement')).to_have_class(re.compile(r"\bon\b"))
        page.evaluate("showHub();openExam('placement')")
    expect(page.locator('body')).to_contain_text(REASON)
    assert len(requests) == 2
    assert requests[0]["ref"] != requests[1]["ref"]


def _promo_routes(page, status, *, recorded=True):
    marks = []
    page.route("**/api/v3/course-tracks", lambda r: json_response(r, status))

    def mark(route):
        marks.append(route.request.url)
        json_response(route, {"ok": True, "hsk30_promo": {
            "recorded": recorded, "recommended_level": "nhsk1",
        }})

    page.route("**/api/v3/course-tracks/promo-shown", mark)
    return marks


def test_release_reminder_waits_for_the_deep_link_sheet_to_close(page):
    _prepare(page)
    marks = _promo_routes(page, _promo_status(True))
    page.goto(app_url('/course-v3.html?lang=uz&lesson=1&onboarded=1'), wait_until='networkidle')
    expect(page.locator('#sheet')).to_contain_text("Yangi so'zlar")
    assert marks == []
    page.evaluate("App.closeSheet()")
    dialog = page.get_by_role('dialog', name='HSK 3.0 ni ochish')
    expect(dialog).to_be_visible()
    assert len(marks) == 1
    assert page.locator('#sheet .si').evaluate(
        'e => Math.abs((e.getBoundingClientRect().top+e.getBoundingClientRect().bottom)/2-innerHeight/2)'
    ) < 8


@pytest.mark.parametrize("return_action", ["foreground", "course_tab"])
def test_admin_enable_is_seen_without_restarting_the_miniapp(page, return_action):
    _prepare(page)
    status = _promo_status(False)
    marks = _promo_routes(page, status)
    page.goto(app_url('/course-v3.html?lang=uz&onboarded=1'), wait_until='networkidle')
    status.update(_promo_status(True))
    if return_action == 'foreground':
        page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    else:
        page.evaluate("App.show('mashq');App.show('course')")
    expect(page.get_by_role('dialog', name='HSK 3.0 ni ochish')).to_be_visible()
    assert len(marks) == 1


def test_release_reminder_respects_another_clients_server_claim(page):
    _prepare(page)
    marks = _promo_routes(page, _promo_status(True), recorded=False)
    page.goto(app_url('/course-v3.html?lang=uz&onboarded=1'), wait_until='networkidle')
    assert len(marks) == 1
    expect(page.get_by_role('dialog', name='HSK 3.0 ni ochish')).to_have_count(0)

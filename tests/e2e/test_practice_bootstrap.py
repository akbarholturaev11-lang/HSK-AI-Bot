"""Practice gates run in parallel with deferred UI helpers and fail closed."""

import json
from http import HTTPStatus
from urllib.parse import urlparse

import pytest

from test_miniapp_smoke import STATIC_ROOT, app_url, expect, json_response, mock_telegram_ready, page


FEATURES = ("recognition", "pronunciation", "memorize")
READY = {
    "recognition": "quiz.length > 0 && document.querySelectorAll('.tile').length === 4",
    "pronunciation": "list.length > 0 && document.getElementById('ctrl').style.display === 'flex'",
    "memorize": "deck.length > 0 && document.querySelector('#body').innerText !== '…'",
}


def environment(page, feature, status=200):
    errors, gates, reports, helper_requests = {"runtime": [], "console": []}, [], [], []
    state = {"status": status}
    page.on("pageerror", lambda error: errors["runtime"].append(str(error)))
    page.on("console", lambda message: errors["console"].append(
        (urlparse(message.location.get("url", "")).path, message.text)) if message.type == "error" else None)
    mock_telegram_ready(page)
    # These generated audio assets are absent from the static fixture checkout.
    # Keep every actual practice/helper script and all runtime errors observable.
    for asset in ("index.js", "client.js"):
        page.route("**/audio/words/" + asset + "?*", lambda route: route.fulfill(
            status=200, content_type="application/javascript", body=""))
    page.route("**/api/voice-practice/me*", lambda route: json_response(
        route, {"ok": True, "level": "hsk1", "completed_lessons": 40}))
    page.route("**/api/v3/practice/words", lambda route: json_response(route, {
        "ok": True, "words": [{"zh": "你", "kind": "new", "box": 0},
                                  {"zh": "好", "kind": "new", "box": 0}]}))
    page.route("**/api/v3/tts*", lambda route: route.fulfill(status=204, body=""))

    def gate(route):
        payload = json.loads(route.request.post_data)
        assert payload["feature"] == feature
        gates.append(payload)
        response = ({"ok": True, "allowed": True} if state["status"] == 200 else
                    {"ok": False, "error": "free_feature_limit_reached", "limit_text": "Daily practice is locked"}
                    if state["status"] == 403 else {"ok": False, "error": "unavailable"})
        json_response(route, response, status=state["status"])

    def report(route):
        reports.append(json.loads(route.request.post_data))
        json_response(route, {"ok": True, "recorded": 10, "scheduled": 10})

    page.route("**/api/v3/practice/daily-gate", gate)
    page.route("**/api/v3/practice/report", report)
    page.route("**/assets/characters/hsk-study-preparing.js?*", lambda route: helper_requests.append(route))
    page.add_init_script("""(() => {
      const original = window.fetch;
      window.fetch = function(input, options) {
        const request = original.call(this, input, options);
        if (String(input).includes('/api/v3/practice/daily-gate')) {
          request.then(response => { window.__practiceGateStatus = response.status; });
        }
        return request;
      };
    })();""")
    return errors, gates, reports, state, helper_requests


def release_helper(page, helper_requests):
    assert len(helper_requests) == 1
    helper_requests[0].fulfill(status=200, content_type="application/javascript",
        body=(STATIC_ROOT / "assets/characters/hsk-study-preparing.js").read_text())
    page.wait_for_load_state("networkidle")


def assert_browser_errors(errors, expected_gate_status=None):
    # A deliberate HTTP rejection emits Chromium's resource-error console item.
    # Require its exact source/status and continue rejecting every JS error.
    expected = [] if expected_gate_status is None else [("/api/v3/practice/daily-gate",
        "Failed to load resource: the server responded with a status of "
        f"{expected_gate_status} ({HTTPStatus(expected_gate_status).phrase})")]
    assert errors == {"runtime": [], "console": expected}


@pytest.mark.parametrize("feature", FEATURES)
def test_practice_gate_starts_before_deferred_helper_and_opens_after_it(page, feature):
    errors, gates, _, _, helper = environment(page, feature)
    page.goto(app_url(f"/course_v3_{feature}.html?lang=uz&level=hsk1"), wait_until="commit")
    page.wait_for_function("window.__practiceGateStatus === 200", timeout=5000)
    assert page.evaluate("typeof HSKStudyPreparing") == "undefined"
    assert len(gates) == 1
    release_helper(page, helper)
    page.wait_for_function(READY[feature])
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    assert_browser_errors(errors)


@pytest.mark.parametrize("feature", FEATURES)
def test_denied_practice_gate_never_opens_questions_after_helper_load(page, feature):
    errors, gates, reports, _, helper = environment(page, feature, status=403)
    page.goto(app_url(f"/course_v3_{feature}.html?lang=uz&level=hsk1"), wait_until="commit")
    page.wait_for_function("window.__practiceGateStatus === 403", timeout=5000)
    release_helper(page, helper)
    expect(page.locator("body")).to_contain_text("Daily practice is locked")
    assert not page.evaluate(READY[feature])
    assert len(gates) == 1 and reports == []
    assert_browser_errors(errors, expected_gate_status=403)


@pytest.mark.parametrize("feature", FEATURES)
def test_failed_gate_keeps_retry_after_late_helper_and_rechecks_permission(page, feature):
    errors, gates, reports, state, helper = environment(page, feature, status=500)
    page.goto(app_url(f"/course_v3_{feature}.html?lang=uz&level=hsk1"), wait_until="commit")
    page.wait_for_function("window.__practiceGateStatus === 500", timeout=5000)
    expect(page.get_by_role("button", name="Qayta urinish", exact=True)).to_be_visible()
    release_helper(page, helper)
    expect(page.get_by_role("button", name="Qayta urinish", exact=True)).to_be_visible()
    assert not page.evaluate(READY[feature])
    assert reports == []
    state["status"] = 200
    page.get_by_role("button", name="Qayta urinish", exact=True).click()
    page.wait_for_function(READY[feature])
    assert len(gates) == 2 and gates[0]["ref"] == gates[1]["ref"]
    assert_browser_errors(errors, expected_gate_status=500)


def test_recognition_completes_and_submits_correct_answers_after_bootstrap(page):
    errors, _, reports, _, helper = environment(page, "recognition")
    page.goto(app_url("/course_v3_recognition.html?lang=uz&level=hsk1"), wait_until="commit")
    page.wait_for_function("window.__practiceGateStatus === 200", timeout=5000)
    release_helper(page, helper)
    page.wait_for_function(READY["recognition"])
    total = page.evaluate("quiz.length")
    for question_index in range(total):
        page.wait_for_function("index => qi === index && !answered", arg=question_index)
        selected = page.evaluate("quiz[qi].opts.findIndex(option => option.ok)")
        page.locator(".tile").nth(selected).click()
    expect(page.locator("#body .done")).to_be_visible(timeout=10000)
    assert len(reports) == 1
    assert reports[0]["feature"] == "recognition"
    assert len(reports[0]["results"]) == total == 10
    assert all(item["correct"] for item in reports[0]["results"])
    assert "mistakes" not in reports[0]
    assert_browser_errors(errors)

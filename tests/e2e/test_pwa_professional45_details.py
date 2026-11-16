"""Professional 45: real asset JavaScript, independent iPhone-layout contracts.

Synthetic actor data in an isolated browser only. Tests do not contact any
production endpoint, mutate account data or authorise payments.
"""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest

playwright = pytest.importorskip("playwright.sync_api")
STATIC = Path(__file__).resolve().parents[2] / "app/static"
ORIGIN = "https://p45-browser-qa.invalid"


def _page(pw, width=390):
    browser = getattr(pw, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
    context = browser.new_context(viewport={"width": width, "height": 844}, is_mobile=True,
                                  reduced_motion="reduce", has_touch=True)
    return browser, context.new_page()


def _static(route):
    path = urlsplit(route.request.url).path
    if path == "/iphone-pwa/course":
        route.fulfill(status=200, content_type="text/html", body=(
            "<!doctype html><html><head><meta name='viewport' "
            "content='width=device-width,initial-scale=1'></head>"
            "<body><div class='wrap'><button id='course'>Course</button>"
            "<div id='flow'><div id='f-stage'></div><div id='f-body'></div>"
            "<button id='f-cta'>Next</button></div></div></body></html>"
        ))
        return
    item = (STATIC / path.lstrip("/")).resolve()
    if item.is_file() and item.is_relative_to(STATIC.resolve()):
        route.fulfill(path=str(item))
    else:
        route.fulfill(status=404, body="not found")


@pytest.mark.parametrize("width", [320, 390, 430])
def test_xp_streak_full_screens_keep_genuine_values_and_unknown_days(width):
    with playwright.sync_playwright() as pw:
        browser, page = _page(pw, width)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.route("**/*", _static)
        try:
            page.goto(ORIGIN + "/iphone-pwa/course", wait_until="domcontentloaded")
            page.evaluate("""() => {
                window.PWA_COURSE_HOST = true;
                window.LANG = "ru";
                window.MAP = {progress:{
                  xp:1250,daily_xp:20,weekly_xp:150,streak:7,longest_streak:12,
                  local_date:"2026-11-16",week_start:"2026-11-16",
                  week_activity_dates:["2026-11-16"]
                },study_setup:{streak_target_days:14,daily_goal_xp:40}};
                window.STUDY_SETUP = MAP.study_setup;
                window.NavBack = {sync(){}};
                window.App = {show(){window.__returned=true}};
                window.savePreferences = async function(payload){
                  window.__saved=payload;
                  return {ok:true,profile:{streak_target_days:payload.streak_target_days}};
                };
            }""")
            page.add_style_tag(url=ORIGIN + "/course_v3_data/pwa-professional45.css")
            page.add_script_tag(url=ORIGIN + "/course_v3_data/pwa-professional45-course.js")
            page.evaluate("HskPwaProgress.open('xp')")
            assert page.locator("#p45-progress").is_visible()
            assert page.locator("#p45-progress .p45-progress-hero").inner_text().find("1 250") >= 0 or "1 250" in page.locator("#p45-progress .p45-progress-hero").inner_text()
            assert "150" in page.locator("#p45-progress").inner_text()
            assert page.locator("#p45-progress .p45-progress-hero").bounding_box()["width"] <= width
            assert page.locator(".wrap").evaluate("(node) => node.inert") is True
            page.locator("[data-p45=back]").click()
            assert page.locator("#p45-progress").count() == 0
            assert page.locator(".wrap").evaluate("(node) => node.inert") is False

            page.evaluate("HskPwaProgress.open('streak')")
            assert "14" in page.locator("#p45-progress .p45-progress-line").first.inner_text()
            assert page.locator(".p45-cal-day.active").count() == 1
            assert page.locator(".p45-cal-day.unknown").count() > 0
            assert page.locator(".p45-cal-day.today").count() == 1
            assert page.locator(".p45-cal-day").count() == 30
            page.locator("[data-p45=select]").click()
            assert page.locator(".p45-progress-goals button").count() == 4
            page.locator('.p45-progress-goals button[data-value="30"]').click()
            page.wait_for_function("window.STUDY_SETUP.streak_target_days === 30")
            assert page.evaluate("window.__saved.streak_target_days") == 30
            assert errors == []
        finally:
            browser.close()


def test_flashcards_only_from_previous_word_and_never_grade_the_lesson():
    with playwright.sync_playwright() as pw:
        browser, page = _page(pw)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.route("**/*", _static)
        try:
            page.goto(ORIGIN + "/iphone-pwa/course", wait_until="domcontentloaded")
            page.evaluate("""() => {
                window.PWA_COURSE_HOST = true;
                window.LANG = "ru";
                window.Flow = {
                  queue:[
                    {type:"active_word",word:{zh:"以前",pinyin:"yǐqián",meaning:{ru:"раньше"}}},
                    {type:"choice"},{type:"choice"},{type:"choice"},{type:"choice"},
                    {type:"choice"},{type:"choice"},{type:"choice"}
                  ],
                  i:4,lessonIdx:0,startedAt:Date.now(),answered:false,correct:2,graded:3
                };
                window.tr = m => m.ru;
                window.renderFlowCard = () => {
                  window.__rendered=(window.__rendered||0)+1;
                  document.querySelector("#f-body").textContent="Normal lesson card";
                  document.querySelector("#f-cta").style.display="flex";
                };
            }""")
            page.add_script_tag(url=ORIGIN + "/course_v3_data/pwa-professional45-course.js")
            page.evaluate("renderFlowCard()")
            assert page.locator(".p45-lesson-flash").count() == 1
            assert page.get_by_text("以前", exact=True).count() == 1
            assert page.locator(".p45-lesson-flash-meaning").count() == 0
            page.locator(".p45-lesson-flash-reveal").click()
            assert page.get_by_text("yǐqián").count() == 1
            page.locator(".p45-lesson-flash-know").click()
            assert page.get_by_text("Normal lesson card").count() == 1
            assert page.evaluate("({i:Flow.i,correct:Flow.correct,graded:Flow.graded})") == {
                "i":4,"correct":2,"graded":3
            }
            page.evaluate("renderFlowCard()")
            assert page.locator(".p45-lesson-flash").count() == 0
            assert errors == []
        finally:
            browser.close()

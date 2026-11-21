"""Actual PWA course XP/Streak renderer, synthetic account/API data only."""
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright

from tests.e2e.test_pwa_learning_parity import LearningPage
from tests.e2e.test_pwa_progressive_sections import pwa_document
from tests.pwa_layout_geometry import capture_geometry, assert_reserved_layout


class ProgressPage(LearningPage):
    def __init__(self, lang="uz", theme="light"):
        super().__init__(lang=lang, paid=True)
        self.theme = theme
        self.preferences = []
        self.data["study_setup"] = {"streak_target_days": 14, "daily_goal_xp": 40}
        self.data["progress"].update(
            xp=137, daily_xp=25, weekly_xp=65, streak=3, longest_streak=11,
            local_date="2026-11-21", week_start="2026-11-16",
            week_activity_dates=["2026-11-16", "2026-11-19", "2026-11-20"],
        )

    def serve(self, route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(content_type="text/html", body=pwa_document().replace(
                '<html lang="ru">', f'<html lang="ru" data-hsk-theme="{self.theme}">', 1,
            ))
        elif path == "/api/v3/pwa/preferences":
            assert route.request.headers["x-hsk-pwa-csrf"] == "test-csrf"
            assert set(route.request.post_data_json) == {"streak_target_days"}
            self.preferences.append(route)
        else:
            super().serve(route)

    def respond(self, *, ok=True):
        route = self.preferences.pop(0)
        if ok:
            self.data["study_setup"].update(route.request.post_data_json)
        route.fulfill(status=200 if ok else 503, json={
            "ok": ok, "profile": self.data["study_setup"] if ok else None,
        })


@pytest.fixture
def browser():
    with sync_playwright() as pw:
        app = getattr(pw, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        yield app
        app.close()


def select_goal(page, days=30):
    page.locator('[data-p45="select"]').click()
    page.locator(f'[data-p45="goal"][data-value="{days}"]').click()


def assert_readable(page):
    assert page.locator("#p45-progress").evaluate("""root => {
        function lum(v) {return v.map(x => {x/=255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0)}
        const style=getComputedStyle(root),rgb=s=>s.match(/[0-9.]+/g).slice(0,3).map(Number);
        const a=lum(rgb(style.color)),b=lum(rgb(style.backgroundColor));
        return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)>=4.5;
    }""")
    assert page.locator(".p45-progress-body").evaluate("el => el.scrollWidth<=el.clientWidth+1")
    for button in page.locator("#p45-progress button").all():
        box = button.bounding_box()
        assert box["width"] >= 44 and box["height"] >= 44


@pytest.mark.parametrize("width", [320, 390, 430])
@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("language", ["uz", "ru", "tj"])
def test_progress_destinations_real_data_theme_calendar_and_return(browser, width, theme, language):
    fixture = ProgressPage(language, theme)
    page = fixture.open(browser, width)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_viewport_size({"width": width, "height": 568 if width == 320 else 932})
    for kind in ("xp", "streak"):
        trigger = page.locator(f'#s-course [data-progress="{kind}"]')
        trigger.click()
        page.locator("#p45-progress").wait_for()
        assert page.locator(".p45-progress-hero strong").inner_text() == ("137" if kind == "xp" else "3")
        assert page.locator(".wrap").evaluate("el => el.inert")
        assert page.locator(".p45-progress-back").evaluate("el => el===document.activeElement")
        assert_readable(page)
        if kind == "streak":
            assert page.locator(".p45-cal-day.active").all_text_contents() == ["16", "19", "20"]
            assert page.locator(".p45-cal-day.missed").all_text_contents() == ["17", "18"]
            assert page.locator(".p45-cal-day.unknown.today").inner_text() == "21"
            assert page.locator(".p45-cal-day.future").count() == 9
            labels = page.evaluate("HSKAI_COURSE_I18N[LANG]")
            assert labels["pwaProgress.legendFuture"] in page.locator(".p45-cal-day.future").first.get_attribute("aria-label")
            assert labels["pwaProgress.legendToday"] not in page.locator(".p45-cal-day.future").first.get_attribute("aria-label")
        directory = os.environ.get("HSK_PROGRESS_REVIEW_DIR")
        if directory:
            Path(directory).mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(Path(directory) / f'{os.getenv("PWA_E2E_ENGINE", "chromium")}-{width}-{language}-{theme}-{kind}.png'))
        page.keyboard.press("Escape")
        assert page.locator("#p45-progress").count() == 0
        assert not page.locator(".wrap").evaluate("el => el.inert")
        assert trigger.evaluate("el => el===document.activeElement")
    page.locator('#nav [data-s="profile"]').click()
    page.locator('#s-profile [data-progress="streak"]').click()
    page.evaluate("NavBack.goBack()")
    assert page.locator("#s-profile.on").count() == 1
    assert page.locator('#s-profile [data-progress="streak"]').evaluate("el => el===document.activeElement")
    assert not fixture.preferences
    assert errors == []


def test_streak_save_waits_for_ack_rejects_failure_and_restores_after_reload(browser):
    fixture = ProgressPage()
    page = fixture.open(browser)
    page.locator('#s-course [data-progress="streak"]').click()
    select_goal(page)
    page.wait_for_function("document.querySelector('[data-p45=goal]').disabled")
    assert page.locator(".p45-progress-line b").first.inner_text() == "14 kun"
    assert page.locator('[data-p45="goal"]:not([disabled])').count() == 0
    fixture.respond(ok=False)
    page.locator('.p45-progress-save-status').get_by_text('Maqsad saqlanmadi', exact=True).wait_for()
    assert page.locator(".p45-progress-line b").first.inner_text() == "14 kun"
    select_goal(page)
    page.wait_for_timeout(30)
    fixture.respond()
    page.wait_for_function("STUDY_SETUP.streak_target_days===30")
    assert page.locator(".p45-progress-line b").first.inner_text() == "30 kun"
    assert page.locator('[data-p45="select"]').evaluate("el => el===document.activeElement")
    page.reload(wait_until="networkidle")
    page.locator('#s-course [data-progress="streak"]').click()
    assert page.locator(".p45-progress-line b").first.inner_text() == "30 kun"


def test_pending_goal_close_reopen_and_owner_map_fence(browser):
    fixture = ProgressPage()
    page = fixture.open(browser)
    page.locator('#s-course [data-progress="streak"]').click()
    select_goal(page)
    page.wait_for_timeout(30)
    page.keyboard.press("Escape")
    page.locator('#s-course [data-progress="xp"]').click()
    fixture.respond(ok=False)
    page.wait_for_function("document.querySelector('.p45-progress-hero strong').textContent==='137'")
    page.keyboard.press("Escape")
    page.locator('#s-course [data-progress="streak"]').click()
    select_goal(page)
    page.wait_for_timeout(30)
    page.evaluate("MAP=Object.assign({},MAP,{study_setup:{streak_target_days:7,daily_goal_xp:25}});STUDY_SETUP=MAP.study_setup;PWA_COURSE_USER_ID=99")
    fixture.respond()
    page.wait_for_timeout(50)
    assert page.evaluate("STUDY_SETUP") == {"streak_target_days": 7, "daily_goal_xp": 25}
    assert page.evaluate("dailyGoal") == 40


def test_goal_timeout_unknown_values_calendar_rollover_and_refresh_geometry(browser):
    fixture = ProgressPage()
    page = fixture.open(browser)
    page.clock.install()
    page.locator('#s-course [data-progress="streak"]').click()
    select_goal(page)
    page.wait_for_timeout(30)
    page.clock.fast_forward(10010)
    page.locator('.p45-progress-save-status').get_by_text('Maqsad saqlanmadi', exact=True).wait_for()
    assert page.locator('[data-p45="select"]').is_enabled()
    page.evaluate("MAP.progress={streak:null,longest_streak:null,local_date:'2026-12-01',week_start:'2026-11-30',week_activity_dates:['2026-11-30']};HskPwaProgress.refresh()")
    assert page.locator(".p45-progress-hero strong").inner_text() == "—"
    assert page.locator(".p45-cal-day.missed,.p45-cal-day.active").count() == 0
    assert page.locator(".p45-cal-day.future").count() == 30
    page.evaluate("delete MAP.progress.week_activity_dates;MAP.progress.local_date='2026-11-21';MAP.progress.week_start='2026-11-16';HskPwaProgress.refresh()")
    assert page.locator(".p45-cal-day.missed").count() == 0
    page.keyboard.press("Escape")
    page.locator('#s-course [data-progress="xp"]').click()
    assert "—" in page.locator(".p45-progress-hero strong").inner_text()
    before = capture_geometry(page, {"header": ".p45-progress-header", "title": ".p45-progress-title", "hero": ".p45-progress-hero"})
    page.evaluate("MAP.progress.xp=0;MAP.progress.daily_xp=0;MAP.progress.weekly_xp=0;renderCourse()")
    assert page.locator(".p45-progress-hero strong").inner_text() == "0"
    assert_reserved_layout(before, capture_geometry(page, {"header": ".p45-progress-header", "title": ".p45-progress-title", "hero": ".p45-progress-hero"}), max_anchor_shift_px=1, max_dimension_delta_px=1)
    page.locator('.p45-progress-title').evaluate("el => {el.textContent=Array(6).fill(el.textContent).join(' ');el.style.fontSize='40px'}")
    assert_readable(page)
    page.keyboard.press("Escape")
    assert page.locator('#s-course [data-progress="xp"]').evaluate("el => el===document.activeElement")


@pytest.mark.parametrize("language", ["uz", "ru", "tj"])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_progress_large_text_keeps_goal_controls_and_month_scroll_reachable(browser, language, theme):
    fixture = ProgressPage(language, theme)
    page = fixture.open(browser, 320)
    page.set_viewport_size({"width": 320, "height": 568})
    page.locator('#s-course [data-progress="streak"]').click()
    page.locator('[data-p45="select"]').click()
    page.locator('#p45-progress').evaluate("""root=>{
        const rules=[];
        for(const el of root.querySelectorAll('*')){
            if(el.tagName==='I'||el.closest('svg'))continue;
            const path=[];
            for(let node=el;node!==root;node=node.parentElement){
                path.unshift(node.tagName.toLowerCase()+[...node.classList].map(x=>'.'+CSS.escape(x)).join(''));
            }
            rules.push('#p45-progress>'+path.join('>')+'{font-size:'+(parseFloat(getComputedStyle(el).fontSize)*2)+'px!important}');
        }
        // Keep the same scale after a legitimate save/error rerenders nodes.
        const style=document.createElement('style');style.textContent=rules.join('');document.head.appendChild(style);
    }""")
    assert_readable(page)
    # Enlarged text changes the natural height; no fixed page/body height or
    # spacing assertion may hide a lost goal action or the month calendar.
    goal=page.locator('[data-p45="goal"][data-value="30"]')
    goal.scroll_into_view_if_needed()
    box=goal.bounding_box()
    header=page.locator('.p45-progress-header').bounding_box()
    assert box['y']>=header['y']+header['height']-1 and box['y']+box['height']<=568
    goal.click()
    page.wait_for_function("document.querySelector('[data-p45=goal]').disabled")
    fixture.respond(ok=False)
    page.wait_for_function("document.querySelector('.p45-progress-save-status').textContent===HSKAI_COURSE_I18N[LANG]['pwaProgress.saveError']")
    page.locator('.p45-progress-save-status').scroll_into_view_if_needed()
    assert page.locator('.p45-progress-save-status').is_visible()
    day=page.locator('.p45-cal-day').last
    day.scroll_into_view_if_needed()
    assert day.is_visible()
    assert page.locator('.p45-progress-body').evaluate('el=>el.scrollHeight>el.clientHeight&&el.scrollTop>0')
    assert_readable(page)
    page.keyboard.press('Escape')
    assert page.locator('#s-course [data-progress="streak"]').evaluate('el=>el===document.activeElement')

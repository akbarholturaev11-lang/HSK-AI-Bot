"""Actual, unchanged learner PWA assets served by credential-free visual QA.

Unlike a reconstructed HTML mock, this imports the repo's genuine HTML/CSS/JS.
Runs isolated localhost preview only and never sends credentials to production.
"""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

pw_api = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).resolve().parents[2]
PORT = 18974
BASE = f"http://127.0.0.1:{PORT}"
SHOT = Path(os.environ.get("PWA_QA_SCREENSHOT_DIR", "/tmp/pwa-professional45-shots"))
PROJECT = "06a405a4-9ec7-4d1f-87b6-b2f745d8fc76"
ENVIRONMENT = "aa22456f-c3f7-47d8-ad90-904856fc10bd"


@pytest.fixture(scope="module")
def real_source_qa():
    env = os.environ.copy()
    for key in (
        "BOT_TOKEN","DATABASE_URL","REDIS_URL","LAVA_API_KEY","LAVA_WEBHOOK_SECRET",
        "STRIPE_SECRET_KEY","TELEGRAM_BOT_TOKEN","GOOGLE_CLIENT_SECRET",
        "R2_ACCESS_KEY_ID","AWS_SECRET_ACCESS_KEY","OPENAI_API_KEY",
    ):
        env.pop(key, None)
    env.update({"HSK_PROFESSIONAL45_QA":"1","RAILWAY_PROJECT_ID":PROJECT,
                "RAILWAY_ENVIRONMENT_ID":ENVIRONMENT})
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.qa_professional45_preview:app",
         "--host", "127.0.0.1", "--port", str(PORT), "--no-access-log"],
        cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(80):
            if server.poll() is not None:
                pytest.fail(f"QA source server exited early: {server.returncode}")
            try:
                with socket.create_connection(("127.0.0.1", PORT), timeout=0.15):
                    break
            except OSError:
                time.sleep(0.15)
        else:
            pytest.fail("QA source server did not bind localhost")
        SHOT.mkdir(parents=True, exist_ok=True)
        yield BASE
    finally:
        server.terminate()
        try:
            server.wait(timeout=8)
        except subprocess.TimeoutExpired:
            server.kill()


@pytest.mark.parametrize("width", [320,390,430])
def test_real_course_practice_profile_and_detail_flow(real_source_qa, width):
    with pw_api.sync_playwright() as pw:
        browser = getattr(pw, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        context = browser.new_context(
            viewport={"width":width,"height":844},device_scale_factor=2,
            is_mobile=True,has_touch=True,reduced_motion="reduce",
        )
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        try:
            page.goto(BASE + "/iphone-pwa/course?lang=ru", wait_until="domcontentloaded", timeout=25000)
            page.wait_for_function("window.MAP && Array.isArray(MAP.units) && MAP.units.length > 0", timeout=20000)
            assert page.locator("#s-course").count() == 1
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 4"), "Course overflows viewport"
            page.screenshot(path=str(SHOT/f"source-course-{width}.png"),full_page=True)

            page.evaluate('App.show("mashq")')
            assert page.locator("#s-mashq .row-card").count() >= 4
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 4"), "Practice overflows viewport"
            page.screenshot(path=str(SHOT/f"source-practice-{width}.png"),full_page=True)
            page.evaluate('App.show("profile")')
            assert page.locator("#s-profile").count() == 1
            page.screenshot(path=str(SHOT/f"source-profile-{width}.png"),full_page=True)

            try:
                page.wait_for_function("typeof window.HskPwaProgress?.open === 'function'",timeout=12000)
            except Exception:
                pass  # the diagnostic assertion below reports what did not load
            progress_diag=page.evaluate("""() => ({
                url:location.href,
                pwa:document.documentElement.classList.contains('hsk-pwa-browser'),
                loaded:!!window.HskPwaProgress,
                scripts:[...document.scripts].filter(x=>x.src.includes('professional45')).map(x=>x.src),
                resources:performance.getEntriesByType('resource').filter(x=>x.name.includes('professional45')).map(x=>({name:x.name,duration:x.duration,transferSize:x.transferSize})),
                css:document.querySelector('link[href*="professional45"]')?.href||null
            })""")
            assert progress_diag["loaded"], "Real XP/Streak source was not loaded: "+str(progress_diag)+" JS "+str(errors[:10])
            page.evaluate('HskPwaProgress.open("streak")')
            assert page.locator("#p45-progress").is_visible()
            # Iconography: line icons, never emoji or text-glyph icons in new UI.
            assert not page.evaluate("/[\\u{1F300}-\\u{1FAFF}\\u2039\\u203A]/u.test(document.querySelector('#p45-progress').innerText)")
            assert page.locator("#p45-progress .p45-progress-back .ti-chevron-left").count() == 1
            assert page.locator(".p45-cal-day.active").count() >= 1
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 4"), "Streak overflows viewport"
            page.screenshot(path=str(SHOT/f"source-streak-{width}.png"),full_page=True)
            page.locator('[data-p45="back"]').click()

            page.evaluate('HskPwaProgress.open("xp")')
            assert page.locator("#p45-progress .p45-progress-hero").is_visible()
            assert "1" in page.locator("#p45-progress .p45-progress-hero").inner_text()
            page.screenshot(path=str(SHOT/f"source-xp-{width}.png"),full_page=True)
            page.locator('[data-p45="back"]').click()
            assert not errors, f"Unexpected JS exceptions: {errors[:6]}"
        finally:
            browser.close()


def test_real_canonical_lesson_and_saved_dictionary(real_source_qa):
    with pw_api.sync_playwright() as pw:
        browser = getattr(pw, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        page = browser.new_page(viewport={"width":390,"height":844},
                                reduced_motion="reduce",is_mobile=True,has_touch=True)
        errors=[]
        page.on("pageerror", lambda e: errors.append(str(e)))
        try:
            page.goto(BASE+"/iphone-pwa/course?lang=ru",wait_until="domcontentloaded",timeout=25000)
            page.wait_for_function("window.MAP && MAP.units",timeout=20000)
            page.evaluate("startLesson(28)")
            page.wait_for_function("window.Flow && Flow.lessonIdx === 28 && Flow.queue.length > 0",timeout=20000)
            assert page.locator("#flow").count() == 1
            page.screenshot(path=str(SHOT/"source-lesson-hsk3-29.png"),full_page=True)

            page.goto(BASE+"/iphone-pwa/dictionary?lang=ru&level=hsk3&version=hsk20&filter=all",
                      wait_until="domcontentloaded",timeout=25000)
            page.wait_for_selector(".row[data-idx]",timeout=20000)
            assert page.locator("[data-saved-word]").count() > 0
            first=page.locator("[data-saved-word]").first
            text=first.get_attribute("data-saved-word")
            first.click()
            page.wait_for_function("w => document.querySelector('[data-saved-word='+JSON.stringify(w)+']')?.getAttribute('aria-pressed')==='true'",arg=text,timeout=12000)
            page.screenshot(path=str(SHOT/"source-dictionary-saved.png"),full_page=True)
            assert not errors, f"Unexpected JS exceptions: {errors[:6]}"
        finally:
            browser.close()


def _page(pw, width=320):
    browser = getattr(pw, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
    page = browser.new_page(viewport={"width": width, "height": 844}, is_mobile=True,
                            has_touch=True, reduced_motion="reduce")
    return browser, page


def test_audit_fixes_on_real_source_screens(real_source_qa):
    """Regressions for the 2026-11-16 professional-45 audit fixes (real assets)."""
    with pw_api.sync_playwright() as pw:
        browser, page = _page(pw)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        try:
            # UIUX-004 phrases: line icons (no emoji/text glyphs), 44px targets at 320px.
            page.goto(BASE + "/iphone-pwa/phrases?lang=ru", wait_until="domcontentloaded", timeout=25000)
            page.wait_for_selector(".phrase-play svg", timeout=15000)
            assert page.evaluate("[...document.querySelectorAll('.phrase-play')].every(b => !/🔊|…/.test(b.textContent))")
            assert page.evaluate("document.querySelector('.search-icon svg') !== null")
            sizes = page.evaluate("[...document.querySelectorAll('.phrase-play,.phrase-actions .save')].slice(0,6)"
                                  ".map(b => {const r=b.getBoundingClientRect(); return Math.min(r.width,r.height)})")
            assert min(sizes) >= 44, sizes
            page.locator(".phrase-toggle").first.click()
            copy = page.locator(".phrase-details:not([hidden]) .copy").first
            assert copy.locator("svg").count() == 1 and copy.get_attribute("aria-label")

            # UIUX-003 dictionary: one level row, automatic version, version-scoped badge.
            page.goto(BASE + "/iphone-pwa/dictionary?lang=ru&level=hsk3", wait_until="domcontentloaded", timeout=25000)
            page.wait_for_selector(".row[data-idx]", timeout=20000)
            assert not page.locator("#filter-toggle").is_visible()
            assert page.evaluate("document.getElementById('level-filters').getBoundingClientRect().height <= 48")
            assert page.evaluate("document.getElementById('filter-count').textContent") == ""
            badges = page.evaluate("[...document.querySelectorAll('.row .lv')].slice(0,5).map(x => x.textContent)")
            assert badges and all(b.startswith("HSK ") and "3.0" not in b for b in badges), badges
            # Hanzi keeps main's reading space before pinyin (3-character words touched it).
            gaps = page.evaluate("[...document.querySelectorAll('.list .row')].slice(0,30).map(r => {"
                                 "const h=r.querySelector('.h'), i=r.querySelector('.info'); if(!h||!i) return 99;"
                                 "return Math.round(i.getBoundingClientRect().left-h.getBoundingClientRect().right)})")
            assert gaps and min(gaps) >= 12, gaps

            # Li onboarding language picker is a full 44px touch target.
            page.goto(BASE + "/iphone-pwa/onboarding/li?lang=uz", wait_until="domcontentloaded", timeout=25000)
            page.wait_for_selector(".lang-control .language", timeout=20000)
            picker = page.evaluate("(() => {const r=document.querySelector('.lang-control .language').getBoundingClientRect(); return [r.width, r.height]})()")
            assert min(picker) >= 44, picker

            # Practice error state: one primary action, no pre-session counter.
            page.goto(BASE + "/iphone-pwa/practice/recognition?lang=ru", wait_until="domcontentloaded", timeout=25000)
            page.wait_for_selector(".done button.ghost", timeout=20000)
            assert page.evaluate("getComputedStyle(document.querySelector('.done button.ghost')).backgroundColor") in ("rgba(0, 0, 0, 0)", "transparent")
            assert page.evaluate("getComputedStyle(document.querySelector('.top .pill')).visibility") == "hidden"

            # AI Voice resting composer: "+" 44px target, composer aligned with 48px buttons.
            page.goto(BASE + "/iphone-pwa/practice/voice?lang=ru", wait_until="domcontentloaded", timeout=25000)
            page.wait_for_selector("#plus", timeout=20000)
            plus = page.evaluate("(() => {const r=document.getElementById('plus').getBoundingClientRect(); return [r.width, r.height]})()")
            assert min(plus) >= 44, plus
            assert page.evaluate("document.querySelector('.composer').getBoundingClientRect().height") >= 48

            # Course map: no node label slides under the next node.
            page.goto(BASE + "/iphone-pwa/course?lang=ru", wait_until="domcontentloaded", timeout=25000)
            page.wait_for_function("window.MAP && Array.isArray(MAP.units) && MAP.units.length > 0", timeout=20000)
            overlaps = page.evaluate("""(() => {const nodes=[...document.querySelectorAll('#s-course .node')]; let n=0;
              for (const node of nodes) {const lab=node.parentElement.querySelector('.nlabel'); if(!lab) continue;
                const r=lab.getBoundingClientRect();
                if (nodes.some(o => {if(o===node) return false; const q=o.getBoundingClientRect();
                  return q.top<r.bottom && q.bottom>r.top && q.left<r.right && q.right>r.left})) n++;}
              return n})()""")
            assert overlaps == 0, overlaps
            # The current node's "continue" bubble must not hide the previous label.
            page.wait_for_selector("#s-course .bubble", timeout=15000)
            covered = page.evaluate("""(() => {const bub=document.querySelector('#s-course .bubble'); const b=bub.getBoundingClientRect();
              return [...document.querySelectorAll('#s-course .nlabel')].filter(l => !bub.contains(l)).map(l => {const r=l.getBoundingClientRect();
                return Math.max(0,Math.min(r.right,b.right)-Math.max(r.left,b.left))*Math.max(0,Math.min(r.bottom,b.bottom)-Math.max(r.top,b.top))})
                .reduce((a,c)=>a+c,0)})()""")
            assert covered == 0, covered

            # UIUX-005 profile: one titled accuracy block from catalog copy.
            page.evaluate('App.show("profile")')
            page.wait_for_selector("#s-profile .p45-accuracy .p45-acc-cell strong", timeout=15000)
            assert page.locator("#s-profile .accuracy-ring").count() == 0
            assert page.locator("#s-profile .p45-accuracy-title").inner_text().strip() == "Точность ответов"

            # Rating load error never shows the loading skeleton at the same time.
            page.evaluate('App.show("rating")')
            page.wait_for_selector("#s-rating .pwa-rating-error", timeout=15000)
            assert page.evaluate("[...document.querySelectorAll('#s-rating .pwa-rating-body > :not(.pwa-rating-error)')]"
                                 ".every(e => getComputedStyle(e).visibility === 'hidden')")
            assert not errors, f"Unexpected JS exceptions: {errors[:6]}"
        finally:
            browser.close()

"""First-paint UX contract of PWA (and unchanged Mini App launch).

Uses the genuine HTML template and stalls all API responses. The visible
shell must be fully static; it cannot depend on authentication/Pro/map data.
"""
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")

HTML = Path("app/static/course-v3.html").read_text(encoding="utf-8")
ORIGIN = "https://hsk.test"


@pytest.mark.parametrize("pwa", [True, False])
def test_shell_renders_without_api_and_preserves_telegram_launch(pwa):
    with pw.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        # Exact source markup: no fake actor/session, no lesson JSON and no
        # cached Pro state. Resources are empty to test static resilience.
        target = ORIGIN + ("/iphone-pwa/course" if pwa else "/course-v3.html")
        page.route("**/*", lambda route: route.fulfill(
            body="", content_type=(
                "text/css" if route.request.url.split("?")[0].endswith(".css")
                else "application/javascript"
            ),
        ))
        # API never responds. Prove the shell does not depend on headers.
        page.route("**/api/**", lambda route: None)
        # Last matching route wins in Playwright.
        page.route(target, lambda route: route.fulfill(
            body=HTML, content_type="text/html; charset=utf-8",
        ))
        page.goto(target, wait_until="domcontentloaded")
        page.locator("#s-course").wait_for(state="visible")
        if pwa:
            assert page.locator("#hsk-launch-splash").is_hidden()
            assert page.locator("#s-course .pwa-initial-shell").is_visible()
            assert page.locator("#nav").is_visible()
            assert page.locator("#nav button").count() == 5
            assert page.locator("#s-course .pwa-skel-card").count() == 2
            assert page.locator("#s-course .pwa-skel-node").count() == 3
            logo = page.locator("#s-course .pwa-first-logo")
            assert logo.count() == 1
            assert logo.get_attribute("fetchpriority") == "high"
            assert logo.get_attribute("loading") == "eager"
            assert logo.get_attribute("width") == "48"
            assert logo.get_attribute("height") == "48"
            assert page.evaluate("""() => {
              const s=document.querySelector('#s-course .pwa-initial-shell');
              return s.getBoundingClientRect().height >= 500;
            }""")
            assert page.locator("#s-profile .pwa-initial-shell").count() == 1
            assert page.locator("#s-rating .pwa-initial-shell").count() == 1
            assert "Pro" not in page.locator("#s-course").inner_text()
        else:
            assert page.locator("#s-course .pwa-initial-shell").is_hidden()
            assert page.locator("#hsk-launch-splash").is_visible()
        browser.close()


def test_progressive_shell_does_not_claim_fake_user_data():
    # The static first paint must not seed XP, subscriptions, lesson statuses
    # or entitlement from localStorage or an unsourced dummy API response.
    assert 'class="pwa-initial-shell"' in HTML
    shell = HTML.split('<div class="scr on" id="s-course">', 1)[1].split(
        '<div class="scr" id="s-mashq">', 1
    )[0]
    assert "data-lesson" not in shell
    assert "PROF" not in shell
    assert "localStorage" not in shell
    assert "premium" not in shell

def test_profile_and_navigation_render_independently_after_map_confirmation():
    # Real course HTML explicitly preserves the currently selected shell tab
    # until a verified map arrives; a slow course request must not reset it.
    assert "PWA_PREBOOT_TAB=s;" in HTML
    assert "App.show(tab);" in HTML
    # Profile accuracy has its own bounded layout while its API is in flight.
    assert 'if(PWA_COURSE_HOST&&!PROFILE_DETAIL&&!PROFILE_DETAIL_FAILED)' in HTML
    assert 'class="profile-accuracy" aria-busy="true"' in HTML
    assert 'if(s==="profile")' in HTML and "loadProfileDetail();" in HTML
    # Render the profile once its asynchronous accuracy boundary is active,
    # not a stale "—" placeholder immediately before replacing with skeleton.
    assert 'if(SCREEN==="profile")renderProfile();' in HTML


@pytest.mark.parametrize("lang,label,accessibility", [
    ("ru", "Профиль", "Загрузка"),
    ("uz", "Profil", "Yuklanmoqda"),
    ("tj", "Профил", "Бор шуда истодааст"),
])
def test_first_paint_localizes_before_any_account_api(lang, label, accessibility):
    with pw.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.route("**/*", lambda route: route.fulfill(
            body="", content_type="text/css" if ".css" in route.request.url
            else "application/javascript",
        ))
        url = ORIGIN + "/iphone-pwa/course?lang=" + lang
        page.route("**/api/**", lambda route: None)
        page.route(url, lambda route: route.fulfill(
            body=HTML, content_type="text/html; charset=utf-8",
        ))
        page.goto(url, wait_until="domcontentloaded")
        assert page.locator('#nav [data-i="profile"]').inner_text() == label
        assert page.locator('#s-course .pwa-initial-shell').get_attribute(
            "aria-label"
        ) == accessibility
        # App locale uses "tj"; HTML language uses BCP 47 "tg" for Tajik.
        assert page.evaluate("document.documentElement.lang") == ("tg" if lang == "tj" else lang)
        browser.close()


def test_rating_second_render_does_not_replace_pending_skeleton_with_empty_results():
    # Isolate the exact rating controller from the bundled application. The
    # second App.show() after renderAll() must not race rating API completion.
    func = "function renderRating(){" + HTML.split("function renderRating(){", 1)[1].split(
        "function retryRating(){", 1
    )[0]
    retry = "function retryRating(){" + HTML.split("function retryRating(){", 1)[1].split(
        "/* Trophy art", 1
    )[0]
    with pw.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content('<div id="s-rating"><div class="pwa-initial-shell">Loading…</div></div>')
        page.evaluate("""() => {
          window.PWA_COURSE_HOST=true;
          window.INIT_DATA='';
          window.ratingLoaded=false;
          window.ratingPending=false;
          window.ratingTabCur='league';
          window.ratingMeta={};
          window.ratingUsers=[];
          window.requests=0;
          window.rendered=0;
          window.$=s=>document.querySelector(s);
          window.T=()=>({nav:{rating:'Рейтинг'}});
          window.courseMessage=(k,v)=>v;
          window.esc=x=>String(x);
          window._renderRatingContent=()=>{
            document.querySelector('#s-rating').textContent='SERVER RESULT';
            window.rendered++;
          };
          window.loadLatestRating=()=>{
            window.requests++;
            return new Promise(resolve=>{window.releaseRating=resolve});
          };
        }""")
        page.evaluate("() => { " + func + "\n" + retry + "\nwindow.renderRating=renderRating;window.retryRating=retryRating; }")
        page.evaluate("() => { renderRating();renderRating();retryRating(); }")
        assert page.evaluate("requests") == 1
        assert page.evaluate("rendered") == 0
        assert page.locator("#s-rating .pwa-initial-shell").count() == 1
        page.evaluate("releaseRating({ok:true})")
        page.wait_for_function("window.rendered===1")
        assert page.locator("#s-rating").inner_text() == "SERVER RESULT"
        assert page.evaluate("ratingPending") is False
        browser.close()


def test_profile_accuracy_has_independent_loading_success_and_error_states():
    func = "function profileAccuracyHtml(){" + HTML.split(
        "function profileAccuracyHtml(){", 1
    )[1].split("function renderProfile(){", 1)[0]
    with pw.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto("about:blank")
        page.evaluate("""() => {
          window.PWA_COURSE_HOST=true;
          window.PROFILE_DETAIL=null;
          window.PROFILE_DETAIL_FAILED=false;
          window.PROFILE_DETAIL_ERROR=false;
          window.PROFILE_DETAIL_SETTLED=false;
          window.LANG="ru";
          window.profileCopy=()=>({overall:'Всего',today:'Сегодня'});
          window.esc=x=>String(x);
        }""")
        page.evaluate("() => { " + func + "\nwindow.profileAccuracyHtml=profileAccuracyHtml; }")
        page.evaluate("document.body.innerHTML=profileAccuracyHtml()")
        assert page.locator(".profile-accuracy[aria-busy='true']").count() == 1
        assert page.locator(".profile-accuracy [aria-hidden='true']").count() == 2
        page.evaluate("""() => {
          PROFILE_DETAIL={stats:{answer_accuracy:{
            overall:{percent:75},today:{percent:60}}}};
          document.body.innerHTML=profileAccuracyHtml();
        }""")
        assert page.locator(".accuracy-ring").count() == 2
        assert "75%" in page.locator(".profile-accuracy").inner_text()
        assert page.locator(".profile-accuracy[aria-busy='true']").count() == 0
        page.evaluate("""() => {
          PROFILE_DETAIL=null;PROFILE_DETAIL_FAILED=true;
          document.body.innerHTML=profileAccuracyHtml();
        }""")
        assert page.locator(".profile-accuracy[aria-busy='true']").count() == 0
        assert "—" in page.locator(".profile-accuracy").inner_text()
        page.evaluate("""() => {
          PROFILE_DETAIL_ERROR=true;
          document.body.innerHTML=profileAccuracyHtml();
        }""")
        assert page.locator(".hsk-pwa-profile-stats-error").count() == 1
        assert page.get_by_role("button", name="Повторить").is_visible()
        browser.close()


def test_optional_prefetch_runs_after_map_first_paint_and_does_not_change_telegram():
    # Scheduling nearby lesson fetches after first paint prevents a large
    # course map from doing extra traversal before displaying the visible tab.
    assert 'if(PWA_COURSE_HOST&&typeof requestAnimationFrame==="function")' in HTML
    assert 'if(document.visibilityState!=="hidden"&&MAP)prefetchNearbyLessons()' in HTML
    assert 'else prefetchNearbyLessons();' in HTML
    assert 'App.show(tab);' in HTML


def test_rating_friends_section_stays_independent_of_leaderboard_network():
    # During a slow league API response, the learner can still enter the
    # independent friends/referral pane. A pending league request must not
    # block that view or invent a completed leaderboard.
    rating = HTML.split("function renderRating(){", 1)[1].split(
        "function retryRating()", 1
    )[0]
    assert rating.index('if(ratingTabCur==="friends")') < rating.index(
        'if(PWA_COURSE_HOST&&ratingPending)'
    )


def test_first_pwa_course_map_recovers_transient_failure_but_never_retries_auth():
    # Execute the production map loader in an isolated browser with a fake
    # read-only map transport. No fake course/identity enters the app itself.
    loader = "function retryTransientCourseMap(" + HTML.split(
        "function retryTransientCourseMap(", 1
    )[1].split("var PWA_LEVEL_REQUEST_SEQ", 1)[0]
    with pw.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content("<div>map loader test</div>")
        result = page.evaluate(
            """async (source) => {
              window.PWA_COURSE_HOST=true;
              window.isHsk30AccessError=()=>false;
              window._ensureSmartTimezone=()=>{};
              const events=[];
              window.clog=(name,kind,extra)=>events.push({name,kind,attempt:extra.attempt});
              (0,eval)(source);
              const good={_status:200,authenticated:true,units:[],level:'hsk1'};
              let calls=0;
              window._fetchCourseMap=()=>{
                calls++;
                return Promise.resolve(calls===1?{_status:503}:good);
              };
              const recovered=await loadCourseMap('hsk1',0);
              const transientCalls=calls;
              calls=0;
              window._fetchCourseMap=()=>{
                calls++;
                return Promise.reject(new TypeError('network disconnected'));
              };
              const failed=await loadCourseMap('hsk1',0);
              const limitedCalls=calls;
              calls=0;
              window._fetchCourseMap=()=>{calls++;return Promise.resolve({
                _status:401,authenticated:false
              })};
              const expired=await loadCourseMap('hsk1',0);
              const authCalls=calls;
              calls=0;
              window._fetchCourseMap=()=>{calls++;return Promise.resolve({
                _status:403,error:'hsk30_unlock_required'
              })};
              const denied=await loadCourseMap('nhsk1',0);
              const deniedCalls=calls;
              calls=0;
              window._fetchCourseMap=()=>{calls++;return Promise.reject(new Error('pwa_actor_changed'))};
              const changed=await loadCourseMap('hsk1',0);
              return {recovered:!!recovered.data,transientCalls,
                failed:failed.error===true,limitedCalls,
                auth:expired.auth===false,authCalls,
                denied:denied.error===true,deniedCalls,
                changed:changed.auth===false,changedCalls:calls,events};
            }""",
            loader,
        )
        assert result["recovered"] is True
        assert result["transientCalls"] == 2
        assert result["failed"] is True
        assert result["limitedCalls"] == 2
        assert result["auth"] is True and result["authCalls"] == 1
        assert result["denied"] is True and result["deniedCalls"] == 1
        assert result["changed"] is True and result["changedCalls"] == 1
        assert result["events"] == [
            {"name": "pwa_course_map_retry", "kind": "http_5xx", "attempt": 1},
            {"name": "pwa_course_map_retry", "kind": "network", "attempt": 1},
            {"name": "pwa_course_map_failed", "kind": "network", "attempt": 2},
        ]
        browser.close()

"""Source-level guardrails for iPhone PWA navigation on constrained networks.

These fast checks complement browser/e2e QA; they do not measure real iPhone
performance or prove payment delivery. Run:
    python -m unittest tests.test_iphone_pwa_navigation_contract
"""
import unittest
from pathlib import Path

COURSE = Path("app/static/course-v3.html").read_text(encoding="utf-8")
CHECKOUT = Path("app/static/subscription.html").read_text(encoding="utf-8")
AUTH = Path("app/api/pwa_auth.py").read_text(encoding="utf-8")
PUSH = Path("app/static/iphone-pwa-sw.js").read_text(encoding="utf-8")


class IphonePwaNavigationContractTests(unittest.TestCase):
    def test_returning_user_skips_login_welcome_on_server(self):
        route = AUTH.split('@router.get("/iphone-pwa")', 1)[1].split(
            '@router.get("/iphone-pwa/course")', 1
        )[0]
        self.assertIn("async def login_page(request: Request)", route)
        self.assertIn("request.cookies.get(PWA_SESSION_COOKIE)", route)
        self.assertIn("await PwaAuthService(db, settings_obj).actor(cookie)", route)
        self.assertIn('"/iphone-pwa/course", status_code=303', route)

    def test_pwa_course_progress_refresh_uses_browser_actor(self):
        refresh = COURSE.split("function refreshCourseProgress(afterWrite)", 1)[1].split(
            "function notifTimesHtml()", 1
        )[0]
        self.assertIn("(!INIT_DATA&&!PWA_COURSE_HOST)", refresh)
        self.assertIn("_fetchCourseMap(level", refresh)
        self.assertIn("if(MAP===snapshot", refresh)

    def test_bfcache_checkout_restore_unblocks_navigation_and_access_refresh(self):
        handler = COURSE.split('window.addEventListener("pageshow",function(e){', 1)[1].split(
            "});", 1
        )[0]
        self.assertIn("CHECKOUT_NAVIGATING=false", handler)
        self.assertIn("(!INIT_DATA&&!PWA_COURSE_HOST)", handler)
        self.assertIn("d._status>=400", handler)
        self.assertIn("renderAll()", handler)

    def test_hidden_dictionary_preload_only_telegram(self):
        body = COURSE.split("function schedulePracticeBackgroundLoad()", 1)[1].split(
            "/* Limit holatini", 1
        )[0]
        self.assertIn("if(!PWA_COURSE_HOST){if(window.RESOURCE)RESOURCE.warm();}", body)
        self.assertIn('if(SCREEN!=="mashq")return', body)
        # On-demand dictionary entry remains available in both hosts.
        self.assertIn('openDict:function(){RESOURCE.open("dict")}', COURSE)

    def test_checkout_returns_to_same_origin_course_without_forcing_reload(self):
        action = CHECKOUT.split("function returnToCourseFromCheckout()", 1)[1].split(
            "function initTelegramCourseReturn()", 1
        )[0]
        self.assertIn('stored.token===token', action)
        self.assertIn('Number(stored.at)>0', action)
        self.assertIn('window.history.back()', action)
        self.assertIn('window.location.replace(courseReturnUrl())', action)
        self.assertIn('PWA_CHECKOUT_HOST', action)
        self.assertIn('sessionStorage.setItem("hskai.pwa.checkout.return"', COURSE)
        self.assertIn('&pwa_return=', COURSE)

    def test_checkout_does_not_block_on_external_telegram_sdk(self):
        self.assertIn('/assets/telegram-web-app.js?v=20261019-1', CHECKOUT)
        self.assertNotIn("https://telegram.org/js/telegram-web-app.js", CHECKOUT)
        self.assertIn("PWA_CHECKOUT_HOST", CHECKOUT)
        self.assertIn("/api/v3/pwa/subscription/overview", CHECKOUT)

    def test_settings_is_fullscreen_and_preferences_are_pwa_authorized(self):
        css = Path("app/static/course_v3_data/iphone-pwa-glass.css").read_text(
            encoding="utf-8"
        )
        self.assertIn('"/api/v3/preferences":"/api/v3/pwa/preferences"', COURSE)
        self.assertIn('if(PWA_COURSE_HOST)$("#sheet").classList.add("pwa-settings-page")', COURSE)
        self.assertIn('#sheet.pwa-settings-page .si', css)
        self.assertIn('if(!INIT_DATA&&!PWA_COURSE_HOST)return Promise.resolve(null)', COURSE)
        self.assertIn('_apiPost("/api/v3/preferences",body)', COURSE)
        self.assertIn('if(!saved||saved.ok!==true){dailyGoal=previous;', COURSE)

    def test_slow_network_cannot_restore_an_older_hsk_level(self):
        logic = COURSE.split("function loadLevel(lv){", 1)[1].split(
            "function applyLessonDone(", 1
        )[0]
        self.assertIn("var PWA_LEVEL_REQUEST_SEQ=0;", COURSE)
        self.assertIn("++PWA_LEVEL_REQUEST_SEQ", logic)
        self.assertIn("PWA_LEVEL_ABORT.abort()", logic)
        self.assertIn("loadCourseMap(lv,0,reqSignal)", logic)
        self.assertIn("requestId!==PWA_LEVEL_REQUEST_SEQ", logic)
        self.assertGreaterEqual(logic.count("requestId!==PWA_LEVEL_REQUEST_SEQ"), 2)
        self.assertIn("setSelectedLevel(MAP.level||lv)", logic)

    def test_cancelled_hsk_map_request_is_not_retried(self):
        loader = COURSE.split("function loadCourseMap(lv,tries,signal)", 1)[1].split(
            "var PWA_LEVEL_REQUEST_SEQ=", 1
        )[0]
        self.assertIn("signal&&signal.aborted", loader)
        self.assertIn("_fetchCourseMap(lv,signal)", loader)
        self.assertIn("_retryCourseMap(lv,tries,signal)", loader)
        self.assertIn("signal&&signal.aborted?{cancelled:true}", loader)

    def test_pwa_does_not_render_hidden_profile_carousel_on_map_refresh(self):
        render = COURSE.split("function renderAll(){", 1)[1].split("navInit();", 1)[0]
        self.assertIn('if(!PWA_COURSE_HOST||SCREEN==="profile")renderProfile()', render)
        # The Profile tab still owns and refreshes its complete UI on entry.
        show = COURSE.split('show:function(s,ratingSource){', 1)[1].split('openSheet:function', 1)[0]
        self.assertIn('if(s==="profile"){', show)
        self.assertIn('renderProfile();', show)
        self.assertIn('loadProfileDetail();', show)

    def test_course_tab_paints_before_expensive_trails(self):
        open_course = COURSE.split('if(s==="course"){', 1)[1].split(
            'if(s==="course"&&previous!=="course")', 1
        )[0]
        self.assertIn('if(PWA_COURSE_HOST&&typeof requestAnimationFrame==="function")', open_course)
        self.assertIn('if(SCREEN!=="course")return', open_course)
        self.assertIn('drawTrails();scrollToCurrentNode()', open_course)

    def test_production_telemetry_disabled_by_default_and_no_user_identifiers(self):
        profiler = Path("app/static/course_v3_data/iphone-pwa-perf.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('get("pwa_perf")==="1"', COURSE)
        self.assertIn('iphone-pwa-perf.js?v=20261105-0dbef5d08a9d', COURSE)
        self.assertIn("window", profiler)
        self.assertIn("snapshot:function()", profiler)
        self.assertNotIn("localStorage", profiler)
        self.assertNotIn("fetch(", profiler)
        self.assertNotIn("user_id", profiler)
        self.assertNotIn("initData", profiler)

    def test_browser_voice_permission_uses_local_microphone_copy(self):
        self.assertIn('LD[locale].micDeny=copy["pronunciation.micDeny"]', COURSE)
        self.assertIn('if(PWA_COURSE_HOST)Object.keys(LD)', COURSE)

    def test_browser_profile_reads_account_owned_stats_and_no_telegram_avatar(self):
        self.assertIn('"/api/miniapp/profile":"/api/v3/pwa/profile"', COURSE)
        self.assertIn("function avatarImgHtml(tgId){return !PWA_COURSE_HOST&&tgId?", COURSE)
        self.assertIn('function myAvatarImgHtml(){if(PWA_COURSE_HOST)return "";', COURSE)
        self.assertIn("(PWA_COURSE_HOST?'':'<span class=", COURSE)
        self.assertIn('async def pwa_profile(request: Request)', AUTH)
        self.assertIn('get_profile_payload(actor)', AUTH)
        self.assertIn('result["user"].pop("telegram_username", None)', AUTH)

    def test_telegram_avatar_edit_not_advertised_on_iphone(self):
        css = Path("app/static/course_v3_data/iphone-pwa-glass.css").read_text(
            encoding="utf-8"
        )
        self.assertIn('html.hsk-pwa-browser .phero .pav .ed {display:none!important}', css)
        self.assertIn('html.hsk-pwa-browser .phero .pav {cursor:default;pointer-events:none}', css)

    def test_iphone_friends_are_authenticated_and_telegram_free(self):
        self.assertIn('"/api/v3/invite":"/api/v3/pwa/invite"', COURSE)
        self.assertIn('if(!referralMeta.loaded&&(INIT_DATA||PWA_COURSE_HOST))', COURSE)
        self.assertIn('if(INIT_DATA||PWA_COURSE_HOST){', COURSE)
        self.assertIn('var acts=(u.me||PWA_COURSE_HOST)?"":', COURSE)
        self.assertIn("HskPwaInvite.open(d)", COURSE)
        self.assertIn("/api/v3/pwa/invite", AUTH)
        profiler = Path("app/static/course_v3_data/iphone-pwa-invite.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("navigator.share", profiler)
        self.assertNotIn("telegram_id", profiler)
        self.assertNotIn("initData", profiler)
        self.assertIn("rating.inviteFallbackShare", profiler)

    def test_push_stays_bound_to_authenticated_inbox(self):
        self.assertIn('/iphone-pwa/course?notice=1', PUSH)
        self.assertNotIn("payment_status", PUSH)
        self.assertNotIn("user_id", PUSH)


if __name__ == "__main__":
    unittest.main()

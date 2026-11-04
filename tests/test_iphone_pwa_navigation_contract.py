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
        self.assertIn("if(window.RESOURCE&&!PWA_COURSE_HOST)RESOURCE.warm()", body)
        self.assertIn('if(SCREEN!=="mashq")return', body)
        # On-demand dictionary entry remains available in both hosts.
        self.assertIn('openDict:function(){RESOURCE.open("dict")}', COURSE)

    def test_checkout_returns_to_same_origin_course_without_forcing_reload(self):
        action = CHECKOUT.split("function returnToCourseFromCheckout()", 1)[1].split(
            "function initTelegramCourseReturn()", 1
        )[0]
        self.assertIn('from.origin===location.origin', action)
        self.assertIn('from.pathname==="/iphone-pwa/course"', action)
        self.assertIn('window.history.back()', action)
        self.assertIn('window.location.replace(courseReturnUrl())', action)
        self.assertIn('PWA_CHECKOUT_HOST', action)

    def test_checkout_does_not_block_on_external_telegram_sdk(self):
        self.assertIn('/assets/telegram-web-app.js?v=20261019-1', CHECKOUT)
        self.assertNotIn("https://telegram.org/js/telegram-web-app.js", CHECKOUT)
        self.assertIn("PWA_CHECKOUT_HOST", CHECKOUT)
        self.assertIn("/api/v3/pwa/subscription/overview", CHECKOUT)

    def test_push_stays_bound_to_authenticated_inbox(self):
        self.assertIn('/iphone-pwa/course?notice=1', PUSH)
        self.assertNotIn("payment_status", PUSH)
        self.assertNotIn("user_id", PUSH)


if __name__ == "__main__":
    unittest.main()

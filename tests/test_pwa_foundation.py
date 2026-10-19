"""Source-level regression for phase-1 install-only PWA integration.

No database, OAuth provider, Telegram bot, network or Playwright required.
This does not replace live Safari/Telegram WebView staging acceptance.
"""
import json
from pathlib import Path
import unittest

from app.api.pwa import create_pwa_router

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"


class PwaFoundationTests(unittest.TestCase):
    def test_manifest_reuses_existing_course_entry(self):
        manifest = json.loads((STATIC / "pwa.webmanifest").read_text("utf-8"))
        self.assertEqual(manifest["start_url"], "/course-v3.html?source=pwa")
        self.assertEqual(manifest["id"], "/hsk-ai-pwa")
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(manifest["scope"], "/")
        self.assertEqual(manifest["icons"][0]["src"], "/assets/hsk-ai-logo-256.png")

    def test_routes_are_asset_only_and_not_authenticated_apis(self):
        routes = {route.path for route in create_pwa_router().routes}
        self.assertEqual(routes, {
            "/pwa.webmanifest", "/pwa-bootstrap.js", "/pwa-sw.js"
        })
        module = (ROOT / "app" / "api" / "pwa.py").read_text("utf-8")
        self.assertNotIn("DesktopAuthService", module)
        self.assertNotIn("UserRepository", module)

    def test_shared_course_page_includes_pwa_without_removing_telegram(self):
        page = (STATIC / "course-v3.html").read_text("utf-8")
        self.assertIn('href="/pwa.webmanifest"', page)
        self.assertIn('src="/pwa-bootstrap.js?v=20261019-1"', page)
        self.assertIn('src="/assets/telegram-web-app.js?v=20261019-1"', page)
        self.assertIn('var INIT_DATA=(tg&&tg.initData)||"";', page)
        self.assertIn('if(!INIT_DATA){hideCourseTrackSwitchPreparing();showAuthGate();return;}', page)

    def test_sw_caches_public_branding_only(self):
        worker = (STATIC / "pwa-sw.js").read_text("utf-8")
        start = worker.index("const PUBLIC_BRANDING")
        end = worker.index("]);", start)
        allowlist = worker[start:end]
        self.assertIn("/assets/hsk-ai-logo-256.png", allowlist)
        self.assertIn("/assets/hsk-ai-avatar.webp", allowlist)
        for forbidden in ("/api/", "/course_v3_data/", "/subscription.html",
                          "/course-v3.html", "lesson_", "/audio/"):
            self.assertNotIn(forbidden, allowlist)
        self.assertIn('request.method !== "GET"', worker)
        self.assertIn("url.search", worker)
        self.assertIn("!PUBLIC_BRANDING.has(url.pathname)", worker)
        self.assertIn("url.origin !== self.location.origin", worker)

    def test_telegram_mode_skips_service_worker_registration(self):
        js = (STATIC / "pwa-bootstrap.js").read_text("utf-8")
        self.assertLess(
            js.index("if (telegramAuthenticated ||"),
            js.index('navigator.serviceWorker.register("/pwa-sw.js"')
        )
        self.assertIn("HSKAI_WEB_HOST", js)
        self.assertNotIn("localStorage", js)
        self.assertNotIn("sessionStorage", js)


if __name__ == "__main__":
    unittest.main()

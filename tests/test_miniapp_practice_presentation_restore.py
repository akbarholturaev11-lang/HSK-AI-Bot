"""Presentation-only regression checks for Mini App practice loading and limit overlays.

Limit enforcement, payment and trial eligibility must remain server-driven.
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "static"
SCENE = (ROOT / "assets/characters/hsk-scene-background.css").read_text(encoding="utf-8")
PREPARING = (ROOT / "assets/characters/hsk-study-preparing.js").read_text(encoding="utf-8")
ADS = (ROOT / "course_v3_data/ads.js").read_text(encoding="utf-8")

PAGES = (
    "course-v3.html",
    "course_v3_memorize.html",
    "course_v3_mistakes.html",
    "course_v3_onboarding.html",
    "course_v3_pronunciation.html",
    "course_v3_recognition.html",
    "course_v3_test.html",
    "course_v3_voice.html",
)


class MiniAppPracticePresentationTests(unittest.TestCase):
    def test_restore_original_dark_limit_promo_not_flat_white_paywall(self):
        self.assertIn(".caa-ov{position:fixed;inset:0;z-index:9000;background:#15120f", ADS)
        self.assertIn(".caa-ov.limit .caa-promo{height:auto;min-height:210px}", ADS)
        self.assertIn(".caa-ov.caa-done .caa-promo{display:flex}", ADS)
        self.assertIn("startPromo();", ADS)
        self.assertNotIn(".caa-ov.limit{background:var(--hsk-paper)", ADS)
        self.assertNotIn(".caa-ov.limit .caa-promo{display:none!important}", ADS)

    def test_entitlement_and_trial_functions_stay_active(self):
        self.assertIn('fetch("/api/v3/limits/status"', ADS)
        self.assertIn("function showLimitPromo(opts)", ADS)
        self.assertIn("trialStatus().then(function(eligible)", ADS)
        self.assertIn("els.pay.onclick=function()", ADS)

    def test_preparing_panda_stays_compact_with_separate_copy(self):
        self.assertIn("width:110px;", SCENE)
        self.assertIn("height:121px;", SCENE)
        self.assertIn("max-width:30vw;", SCENE)
        self.assertIn(".hsk-study-preparing b{", SCENE)
        self.assertIn(".hsk-study-preparing small{", SCENE)
        self.assertIn('width:110px;height:121px;max-width:30vw', PREPARING)
        self.assertIn('<b style="display:block;', PREPARING)
        self.assertIn('<small style="display:block;', PREPARING)
        self.assertIn("HSKStudyPreparing={render:render}", PREPARING)

    def test_all_miniapp_pages_refresh_scene_asset(self):
        for page in PAGES:
            with self.subTest(page=page):
                html = (ROOT / page).read_text(encoding="utf-8")
                self.assertIn("hsk-scene-background.css?v=20261009-preparing-compact-1", html)
                self.assertNotIn("hsk-scene-background.css?v=20261008-scene-1", html)

    def test_practice_pages_refresh_loading_and_limit_assets(self):
        for page in PAGES:
            html = (ROOT / page).read_text(encoding="utf-8")
            if "hsk-study-preparing.js?" in html:
                with self.subTest(page=page, resource="preparing"):
                    self.assertIn("hsk-study-preparing.js?v=20261009-compact-1", html)
            if "course_v3_data/ads.js?" in html:
                with self.subTest(page=page, resource="ads"):
                    self.assertIn("course_v3_data/ads.js?v=20261009-limit-restore-1", html)


if __name__ == "__main__":
    unittest.main()

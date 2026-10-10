"""Lightweight source contracts for the Mini App profile and limit paywall.

These checks do not replace Telegram WebView screenshots or end-to-end checkout
testing. They prevent regressions in screen hierarchy and trial/Pro CTA wiring.
"""
import unittest
from pathlib import Path

PROFILE = Path("app/static/course-v3.html").read_text(encoding="utf-8")
ADS = Path("app/static/course_v3_data/ads.js").read_text(encoding="utf-8")


class MiniAppProfileHierarchyTests(unittest.TestCase):
    def test_real_progress_fields_are_used_for_metrics(self):
        body = PROFILE.split("function renderProfile(){", 1)[1].split(
            "/* ---------- sales_value_v1", 1
        )[0]
        self.assertIn("class=\"stats profile-stats\"", body)
        self.assertIn("Number(MAP&&MAP.progress&&MAP.progress.xp||0)", body)
        self.assertIn("completedLessons.toLocaleString", body)
        self.assertLess(body.index("profile-stats"), body.index("proProfileCard()"))
        self.assertLess(body.index('class="pgoal"'), body.index("profile-stats"))

    def test_localized_stat_labels_exist(self):
        for label in (
            "Статистика обучения",
            "O‘qish statistikasi",
            "Омори омӯзиш",
            "Пройдено уроков",
            "Tugatilgan darslar",
            "Дарсҳои анҷомшуда",
        ):
            with self.subTest(label=label):
                self.assertIn(label, PROFILE)


class MiniAppLimitHierarchyTests(unittest.TestCase):
    def test_limit_is_not_the_ad_carousel(self):
        self.assertIn(".caa-ov.limit .caa-promo{display:none!important}", ADS)
        self.assertIn(".caa-ov.limit .caa-box{display:flex;", ADS)
        self.assertIn("els.subTitle.textContent=t.limitTitle;", ADS)

    def test_authoritative_server_limit_copy_can_be_fetched(self):
        self.assertIn("if(!opts.reason){", ADS)
        self.assertIn('fetch("/api/v3/limits/status"', ADS)
        self.assertIn("els.whyT.textContent=text;", ADS)

    def test_payment_trial_and_close_actions_stay_wired(self):
        body = ADS.split("function showLimitPromo(opts){", 1)[1].split(
            "/* ============================================================", 1
        )[0]
        self.assertIn("opts.onSubscribe", body)
        self.assertIn("opts.onTrial", body)
        self.assertIn("opts.trialEligible", body)
        self.assertIn("els.x.onclick", body)
        self.assertIn("stopPromo();", body)
        self.assertNotIn("startPromo();", body)


if __name__ == "__main__":
    unittest.main()

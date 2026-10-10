"""Lightweight source contracts for Mini App profile and restored original limit UI.

These checks do not replace Telegram WebView screenshots or end-to-end checkout
testing. They prevent regressions in screen hierarchy and trial/Pro CTA wiring.
"""
import unittest
from pathlib import Path

PROFILE = Path("app/static/course-v3.html").read_text(encoding="utf-8")
ADS = Path("app/static/course_v3_data/ads.js").read_text(encoding="utf-8")
ANDROID_DIRECT_LIMIT = Path("android/app/src/direct/java/com/pomp/hskai/feature/limit/SectionLimitBlock.kt").read_text(encoding="utf-8")


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


class MiniAppLimitRestorationTests(unittest.TestCase):
    """The Mini App paywall must match the Oct 9 design, not the newer compact one."""

    def test_original_carousel_and_heading(self):
        self.assertNotIn(".caa-ov.limit .caa-promo{display:none!important}", ADS)
        self.assertNotIn(".caa-ov.limit.trial-eligible .caa-lim-ad{", ADS)
        self.assertIn('els.subTitle.textContent="";', ADS)
        body = ADS.split("function showLimitPromo(opts){", 1)[1].split(
            "/* ============================================================", 1
        )[0]
        self.assertIn("startPromo();", body)
        self.assertIn("if(!why){", body)

    def test_original_trial_pro_and_close_handlers(self):
        body = ADS.split("function showLimitPromo(opts){", 1)[1].split(
            "/* ============================================================", 1
        )[0]
        self.assertIn("opts.onSubscribe", body)
        self.assertIn("opts.onTrial", body)
        self.assertIn("opts.trialEligible", body)
        self.assertIn("els.x.onclick", body)
        self.assertIn('limitTrial:"Или 7 дней бесплатно"', ADS)
        self.assertIn('limitSubscribe:"Получить HSK AI Pro ⭐️"', ADS)
        self.assertIn("var controls=[els.x,els.pay,els.limAd]", ADS)


class AndroidDirectLimitChoicesTests(unittest.TestCase):
    def test_no_extra_later_button_but_close_x_still_works(self):
        self.assertNotIn('R.string.limit_later', ANDROID_DIRECT_LIMIT)
        self.assertNotIn('tertiaryLabel =', ANDROID_DIRECT_LIMIT)
        self.assertIn('primaryLabel = if (trialOffered) stringResource(R.string.limit_try_trial)', ANDROID_DIRECT_LIMIT)
        self.assertIn('secondaryLabel = if (trialOffered) stringResource(R.string.limit_unlock_button) else null', ANDROID_DIRECT_LIMIT)
        self.assertIn('onPrimary = if (trialOffered) limit.actions.onStartTrial else openSubscription', ANDROID_DIRECT_LIMIT)
        self.assertIn('onSecondary = if (trialOffered) openSubscription else null', ANDROID_DIRECT_LIMIT)
        overlay = Path('android/app/src/main/java/com/pomp/hskai/feature/limit/SectionLimitOverlay.kt').read_text(encoding="utf-8")
        self.assertIn('onClick = onClose', overlay)



if __name__ == "__main__":
    unittest.main()

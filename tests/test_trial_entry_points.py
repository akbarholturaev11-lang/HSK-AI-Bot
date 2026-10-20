"""Trialga kirish nuqtalari — u ko'rinmasa, yo'q bilan barobar.

Server tomoni tayyor bo'lgani bilan foydalanuvchi trialni BOSHLAY olmasa, u
xususiyat emas. Shu fayl to'rtala kirish nuqtasi joyida turganini tekshiradi:

* onboardingdan keyingi tanlov ekrani,
* limitga urilgandagi paywall,
* obuna sahifasi,
* profil karuseli (Mini App va Android direct versiyasida).
  Google Play versiyasida xarid tugmasi yo'q.

Ustiga bitta qat'iy qoida: klient "bu odam trial ola oladimi" degan qarorni
O'ZI qabul qilmaydi. Bir Telegram akkaunt bir marta trial olishi kerak va
buni faqat server biladi.
"""

import re
import unittest
from pathlib import Path


COURSE = Path("app/static/course-v3.html").read_text(encoding="utf-8")
SUBSCRIPTION = Path("app/static/subscription.html").read_text(encoding="utf-8")
ADS = Path("app/static/course_v3_data/ads.js").read_text(encoding="utf-8")
CAROUSEL = Path("app/static/course_v3_data/profile-carousel.js").read_text(encoding="utf-8")

ANDROID = Path("android/app/src/main/java/com/pomp/hskai")
ANDROID_MAIN = (ANDROID / "MainActivity.kt").read_text(encoding="utf-8")
ANDROID_PROFILE = (ANDROID / "feature/profile/ProfileScreen.kt").read_text(
    encoding="utf-8"
)
ANDROID_LIMIT_OVERLAY = (ANDROID / "feature/limit/SectionLimitOverlay.kt").read_text(
    encoding="utf-8"
)
ANDROID_SETTINGS = (ANDROID / "core/settings/AppSettings.kt").read_text(encoding="utf-8")
ANDROID_APPLICATION = (ANDROID / "HskAiApplication.kt").read_text(encoding="utf-8")
ANDROID_LIMIT_DIRECT = Path(
    "android/app/src/direct/java/com/pomp/hskai/feature/limit/SectionLimitBlock.kt"
).read_text(encoding="utf-8")
ANDROID_LIMIT_PLAY = Path(
    "android/app/src/play/java/com/pomp/hskai/feature/limit/SectionLimitBlock.kt"
).read_text(encoding="utf-8")


class TrialEntryPointTests(unittest.TestCase):
    def test_the_plan_choice_appears_after_onboarding(self):
        self.assertIn("function maybeShowPlanChoice()", COURSE)
        # Onboardingdan endigina qaytganda chaqiriladi.
        self.assertIn('bootParams.get("onboarded")==="1"', COURSE)
        # Ikki yo'l: Pro olish yoki 7 kun sinash.
        self.assertIn(r"App.goPay(\'onboarding_plan\')", COURSE)
        self.assertIn(r"App.startTrial(\'onboarding_plan\')", COURSE)
        # Bir marta ko'rsatiladi.
        self.assertIn("hsk_v3_plan_choice", COURSE)

    def test_the_lesson_and_practice_limit_paywalls_offer_pro_only(self):
        # Trial is still available in onboarding/profile, never on a limit sheet.
        self.assertIn("isLimitPaywallContext(ctx)", COURSE)
        self.assertIn("!isLimitPaywallContext(ctx)&&trialEligible()", COURSE)
        self.assertIn('trialStart("paywall_practice")', COURSE)
        sheet = ADS.split("function showLimitPromo(opts){", 1)[1].split(
            "/* ============================================================", 1
        )[0]
        self.assertIn("els.limitPay.onclick", sheet)
        self.assertNotIn("trialStatus(", sheet)
        self.assertNotIn("showTrialButton(", sheet)
        self.assertNotIn("opts.onTrial", sheet)

    def test_the_subscription_checkout_does_not_offer_the_trial(self):
        self.assertNotIn('id="trialOffer"', SUBSCRIPTION)
        self.assertNotIn('"/api/v3/trial/start"', SUBSCRIPTION)
        self.assertNotIn("loadTrial();", SUBSCRIPTION)

    def test_the_profile_carousel_uses_server_trial_status(self):
        self.assertIn('id="hsk-profile-promo-root"', COURSE)
        self.assertIn('var ORDER=["apps","hsk30","pro"]', CAROUSEL)
        self.assertIn('if(plan==="trial")', CAROUSEL)
        self.assertIn("trialLeftText(until)", CAROUSEL)
        self.assertIn("TRIAL_LOADED&&trialEligible()", CAROUSEL)
        self.assertIn('App.startTrial("profile")', CAROUSEL)
        self.assertNotIn("function proProfileCard()", COURSE)

    def test_the_profile_never_draws_two_subscription_cards(self):
        body = COURSE.split("function renderProfile()")[1][:4000]
        self.assertEqual(1, body.count('<div id="hsk-profile-promo-root"></div>'))
        self.assertNotIn("proProfileCard()", body)
        self.assertNotIn('<div class="pro"', body)

    def test_a_learner_who_used_the_trial_is_offered_only_the_purchase(self):
        self.assertIn('TRIAL_LOADED&&trialEligible()?t.trialCta:t.unlockBtn', CAROUSEL)
        self.assertIn('TRIAL_LOADED&&trialEligible()?"trial":"pay"', CAROUSEL)
        self.assertIn('App.goPay(', CAROUSEL)
        self.assertIn('if(!TRIAL_LOADED||!trialEligible())return;', CAROUSEL)

    def test_only_explicit_trial_cta_can_start_the_trial(self):
        # Clicking the body of a trial-eligible Pro card opens checkout;
        # clicking the dedicated 7-day CTA starts the server-authorised trial.
        self.assertIn('function doAction(explicitCta,kind){', CAROUSEL)
        self.assertIn('event.stopPropagation();doAction(true,slide.dataset.promoKind)', CAROUSEL)
        self.assertIn('if(p.action==="trial"&&explicitCta===true)', CAROUSEL)
        self.assertIn('App.goPay(p.renew?', CAROUSEL)
        self.assertNotIn('if(p.action==="trial"){', CAROUSEL)


class AndroidOffersTheSameTrialTests(unittest.TestCase):
    """Android direct profilidagi ixcham Pro karuseli server trial holatiga amal qiladi.

    Onboardingdan keyin majburiy alohida Pro/trial oynasi chiqmaydi.
    Limit paywalliga va Google Play obuna mexanizmiga tegilmaydi.
    """

    def test_onboarding_does_not_interrupt_with_a_plan_choice(self):
        self.assertNotIn("PlanChoiceSheet(", ANDROID_MAIN)
        self.assertNotIn("planChoiceSeen", ANDROID_MAIN)
        self.assertNotIn('onUnlock("onboarding_plan")', ANDROID_MAIN)

    def test_the_limit_block_has_one_action_without_trial_in_both_channels(self):
        for name, source in (("direct", ANDROID_LIMIT_DIRECT), ("play", ANDROID_LIMIT_PLAY)):
            with self.subTest(channel=name):
                self.assertNotIn("limit.actions.onStartTrial", source)
                self.assertNotIn("R.string.limit_try_trial", source)
                self.assertNotIn("secondaryLabel =", source)

    def test_profile_has_one_carousel_and_reuses_the_existing_trial_callback(self):
        self.assertNotIn("TrialCard(", ANDROID_PROFILE)
        self.assertIn("ProfilePromoCarousel(", ANDROID_PROFILE)
        self.assertIn("onStartTrial = onStartTrial", ANDROID_PROFILE)
        self.assertIn("onStartTrial = profileViewModel::startTrial", ANDROID_MAIN)

    def test_the_trial_is_still_reachable_from_the_limit_gate(self):
        # Karta ketdi, lekin `startTrial` o'z joyida va `LimitGate` ga
        # ulangan — aks holda paywalldagi tugma hech narsa qilmaydi.
        self.assertIn("fun startTrial()", _android_profile_view_model())
        self.assertIn("onStartTrial = profileViewModel::startTrial", ANDROID_MAIN)

    def test_the_client_never_decides_eligibility_on_its_own(self):
        # Serverdan kelgan bayroq O'QILADI, klient o'zi hisoblamaydi.
        self.assertIn("profileState.trial?.eligible == true", ANDROID_MAIN)
        self.assertIn("api/v3/android/trial/status", _android_api())

    def test_watching_an_ad_is_no_longer_offered_as_a_way_through(self):
        # Reklama hech narsani ochmaydi. Eski tugma qolib ketmasin.
        for name, source in (
            ("direct", ANDROID_LIMIT_DIRECT),
            ("play", ANDROID_LIMIT_PLAY),
        ):
            with self.subTest(channel=name):
                self.assertNotIn("onWatchAd", source)
                self.assertNotIn("limit_watch_ad", source)

    def test_android_ads_start_only_after_a_limit_screen_has_been_seen(self):
        # Limit oynasi haqiqatan ko'ringanda gate ochiladi va yopilgani ham
        # AppRoot'ga qaytadi — markaziy reklama paywall ustiga chiqmasin.
        self.assertIn("limit.actions.onPresented()", ANDROID_LIMIT_OVERLAY)
        self.assertIn("limit.actions.onDismissed()", ANDROID_LIMIT_OVERLAY)
        self.assertIn("app.appSettings.unlockAdsAfterLimit()", ANDROID_MAIN)
        self.assertIn("adsUnlockedAfterLimit &&", ANDROID_MAIN)
        self.assertIn("completed && adsUnlockedAfterLimit", ANDROID_MAIN)
        # Qaror restartdan keyin ham qoladi, ammo boshqa accountga oqib o'tмайди.
        self.assertIn("ADS_UNLOCKED_AFTER_LIMIT_KEY", ANDROID_SETTINGS)
        self.assertIn("clearAdsUnlockedAfterLimit()", ANDROID_APPLICATION)


def _android_api() -> str:
    return (ANDROID / "data/api/AndroidFeatureApi.kt").read_text(encoding="utf-8")


def _android_profile_view_model() -> str:
    return (ANDROID / "feature/profile/ProfileViewModel.kt").read_text(
        encoding="utf-8"
    )


class TheServerDecidesTests(unittest.TestCase):
    def test_the_client_never_decides_eligibility_on_its_own(self):
        # Klient faqat serverdan kelgan bayroqni O'QIYDI.
        self.assertIn('"/api/v3/trial/status"', COURSE)
        self.assertIn("return !!(TRIAL_STATE&&TRIAL_STATE.eligible)", COURSE)
        # `trial_used` ni klient o'zi localStorage'da hisoblab yurmasin.
        self.assertNotIn("localStorage.setItem(\"hsk_trial_used\"", COURSE)

    def test_a_refusal_is_shown_rather_than_swallowed(self):
        # Jimgina "hech narsa bo'lmadi" eng yomon variant.
        self.assertIn("trialFail", COURSE)


class TrialCopyIsThreeLanguagesTests(unittest.TestCase):
    """CLAUDE.md: har qanday yangi ko'rinadigan matn uz/ru/tj uchalasida."""

    def test_the_mini_app_copy_exists_three_times(self):
        for key in ("trialTitle", "trialCta", "planTitle", "planPay", "planFree"):
            with self.subTest(key=key):
                self.assertEqual(
                    3,
                    len(re.findall(rf"\b{key}:", COURSE)),
                    f"{key} uchala tilda ham bo'lishi kerak",
                )

    def test_the_paywall_button_copy_exists_three_times(self):
        self.assertEqual(3, len(re.findall(r"\blimitTrial:", ADS)))

    def test_the_subscription_page_has_no_trial_copy(self):
        self.assertNotIn("function trialCopy()", SUBSCRIPTION)


if __name__ == "__main__":
    unittest.main()

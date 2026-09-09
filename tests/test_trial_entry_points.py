"""Trialga kirish nuqtalari — u ko'rinmasa, yo'q bilan barobar.

Server tomoni tayyor bo'lgani bilan foydalanuvchi trialni BOSHLAY olmasa, u
xususiyat emas. Shu fayl to'rtala kirish nuqtasi joyida turganini tekshiradi:

* onboardingdan keyingi tanlov ekrani,
* limitga urilgandagi paywall,
* obuna sahifasi,
* profil kartasi.

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

ANDROID = Path("android/app/src/main/java/com/pomp/hskai")
ANDROID_MAIN = (ANDROID / "MainActivity.kt").read_text(encoding="utf-8")
ANDROID_PROFILE = (ANDROID / "feature/profile/ProfileScreen.kt").read_text(
    encoding="utf-8"
)
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

    def test_the_paywall_offers_the_trial(self):
        """Dars paywalli ham, mashq paywalli ham trialni taklif qiladi.

        Dars uchun taklif ilgari `startLessonAdGate` ichida edi va o'sha
        funksiya hech qachon chaqirilmasdi (`lessonNeedsAd()` doim `false`),
        ya'ni test o'lik kodni tekshirib "o'tyapti" derdi. Endi u odam
        ko'radigan `paywallHtml` ichida.
        """
        self.assertIn(r"App.startTrial(\'paywall_lesson\')", COURSE)
        self.assertIn("trialStart(\"paywall_practice\")", COURSE)
        # Reklama o'rniga trial — eski parametr qolmasin.
        self.assertNotIn("onContinueAd:", COURSE)

    def test_the_lesson_paywall_hides_the_trial_once_it_is_used(self):
        # Trial olingan bo'lsa yagona tugma obuna bo'lib qoladi.
        block = COURSE.split("function paywallHtml(ctx)")[1][:1600]
        self.assertIn("trialEligible()", block)

    def test_the_subscription_page_offers_the_trial(self):
        self.assertIn('id="trialOffer"', SUBSCRIPTION)
        self.assertIn('"/api/v3/trial/start"', SUBSCRIPTION)
        self.assertIn("loadTrial();", SUBSCRIPTION)

    def test_the_profile_shows_a_trial_card(self):
        """Profilda BITTA HSK AI Pro kartasi.

        Ilgari ikkita qora karta ketma-ket chiqardi — "7 kun bepul" va
        "Hammasini oching" — ikkalasi ham ayni bitta obuna haqida. Odam
        ularni ikki xil mahsulot deb o'qirdi.
        """
        self.assertIn("function proProfileCard()", COURSE)
        self.assertIn(r"App.startTrial(\'profile\')", COURSE)
        # Faol trialda qolgan kun ko'rsatiladi — endi server yorlig'i
        # (MAP.user.plan) orqali, markaziy dvigateldan.
        self.assertIn('if(plan==="trial")', COURSE)
        self.assertIn("trialLeft", COURSE)

    def test_the_profile_never_draws_two_subscription_cards(self):
        body = COURSE.split("function renderProfile()")[1][:4000]
        self.assertEqual(1, body.count("proProfileCard()"))
        self.assertNotIn('<div class="pro"', body)

    def test_a_learner_who_used_the_trial_is_offered_only_the_purchase(self):
        card = COURSE.split("function proProfileCard()")[1][:1400]
        self.assertIn("canTrial", card)
        self.assertIn("trialCta", card)
        self.assertIn("unlockBtn", card)


class AndroidOffersTheSameTrialTests(unittest.TestCase):
    """Android'da ham AYNI kirish nuqtalari.

    Bitta hisob, bir nechta qurilma: telefonda trial taklif qilinmasa,
    foydalanuvchi uchun u yo'q bilan barobar. Mini App'dagi to'rtta joyning
    Android'dagi ekvivalenti shu yerda qotiriladi (obuna sahifasi Android'da
    alohida ekran emas — u profilning o'zi).
    """

    def test_the_plan_choice_appears_after_onboarding(self):
        self.assertIn("PlanChoiceSheet(", ANDROID_MAIN)
        # Faqat endigina onboarding tugatgan odamga: `launch` shu chaqiruvda
        # to'ladi va allaqachon ro'yxatdan o'tgan hisobda null bo'lib qoladi.
        self.assertIn("onboardingState.launch != null", ANDROID_MAIN)
        # Bir marta.
        self.assertIn("planChoiceSeen", ANDROID_MAIN)

    def test_the_limit_block_offers_the_trial_in_both_channels(self):
        for name, source in (
            ("direct", ANDROID_LIMIT_DIRECT),
            ("play", ANDROID_LIMIT_PLAY),
        ):
            with self.subTest(channel=name):
                self.assertIn("limit.actions.onStartTrial", source)
                self.assertIn("R.string.limit_try_trial", source)

    def test_the_profile_offers_the_trial(self):
        self.assertIn("TrialCard(", ANDROID_PROFILE)
        self.assertIn("onStartTrial", ANDROID_PROFILE)

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


def _android_api() -> str:
    return (ANDROID / "data/api/AndroidFeatureApi.kt").read_text(encoding="utf-8")


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

    def test_the_subscription_page_copy_covers_three_languages(self):
        for lang in ("uz:", "ru:", "tj:"):
            with self.subTest(lang=lang):
                self.assertIn(lang, SUBSCRIPTION.split("function trialCopy()")[1][:900])


if __name__ == "__main__":
    unittest.main()

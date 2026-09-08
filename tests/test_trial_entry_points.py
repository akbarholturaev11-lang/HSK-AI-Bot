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
        self.assertIn("trialStart(\"paywall_lesson\")", COURSE)
        self.assertIn("trialStart(\"paywall_practice\")", COURSE)
        # Reklama o'rniga trial — eski parametr qolmasin.
        self.assertNotIn("onContinueAd:", COURSE)

    def test_the_subscription_page_offers_the_trial(self):
        self.assertIn('id="trialOffer"', SUBSCRIPTION)
        self.assertIn('"/api/v3/trial/start"', SUBSCRIPTION)
        self.assertIn("loadTrial();", SUBSCRIPTION)

    def test_the_profile_shows_a_trial_card(self):
        self.assertIn("function trialProfileCard()", COURSE)
        self.assertIn(r"App.startTrial(\'profile\')", COURSE)
        # Faol trialda qolgan kun ko'rsatiladi.
        self.assertIn("TRIAL_STATE.active", COURSE)


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

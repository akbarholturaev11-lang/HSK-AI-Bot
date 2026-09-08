"""Paywall va trial matnlari — uchala tilda.

CLAUDE.md qat'iy talab qiladi: har qanday yangi ko'rinadigan matn ru/tj/uz
uchalasida ham bo'lishi kerak. Bu fayl uni qotiradi, chunki matn qo'shishda
bitta tilni unutib qo'yish oson va natijasi jimgina buziladi: `t()` topilmagan
kalit o'rniga KALITNING O'ZINI qaytaradi, ya'ni foydalanuvchi
`paywall_lesson_title` degan yozuvni ko'radi.

Ustiga: matn serverda renderlanadi, shuning uchun bu yerdagi tekshiruv
to'rtala klient uchun ham amal qiladi.
"""

import unittest

from app.bot.utils.i18n import t
from app.services.entitlements import actions as A
from app.services.entitlements.decision import (
    RECOMMENDED_PLAN,
    REASON_LIMIT_REACHED,
    paywall_for,
    refuse,
)


LANGUAGES = ("tj", "ru", "uz")

SURFACES = ("lesson", "ai", "voice", "speaking", "practice", "study")

TRIAL_KEYS = (
    "trial_offer_title",
    "trial_offer_body",
    "trial_offer_cta",
    "trial_started_notice",
    "trial_expiring_soon",
    "trial_expired_notice",
    "limit_reached_generic",
)


class PaywallCopyTests(unittest.TestCase):
    def test_every_surface_has_a_title_body_and_cta_in_every_language(self):
        for surface in SURFACES:
            for part in ("title", "body", "cta"):
                key = f"paywall_{surface}_{part}"
                for lang in LANGUAGES:
                    with self.subTest(key=key, lang=lang):
                        value = t(key, lang)
                        # `t()` topilmagan kalitni O'ZI qaytaradi.
                        self.assertNotEqual(key, value, f"{key} {lang} tilida yo'q")
                        self.assertTrue(value.strip())

    def test_every_trial_string_exists_in_every_language(self):
        for key in TRIAL_KEYS:
            for lang in LANGUAGES:
                with self.subTest(key=key, lang=lang):
                    self.assertNotEqual(key, t(key, lang))

    def test_the_languages_are_actually_different(self):
        # Bitta tildagi matnni uchalasiga nusxalab qo'yish ham xato.
        for surface in SURFACES:
            key = f"paywall_{surface}_title"
            with self.subTest(surface=surface):
                self.assertEqual(3, len({t(key, lang) for lang in LANGUAGES}))

    def test_the_countdown_string_formats_without_a_key_error(self):
        for lang in LANGUAGES:
            with self.subTest(lang=lang):
                rendered = t("trial_expiring_soon", lang, days=2)
                self.assertIn("2", rendered)

    def test_every_action_maps_to_a_surface_that_has_copy(self):
        for action in A.ACTIONS:
            with self.subTest(action=action):
                hint = paywall_for(action)
                self.assertIn(hint.surface, SURFACES)
                for lang in LANGUAGES:
                    rendered = hint.render(lang)
                    self.assertNotEqual(hint.title_key, rendered["title"])
                    self.assertNotEqual(hint.cta_key, rendered["cta"])

    def test_a_refusal_carries_rendered_text_and_the_keys(self):
        decision = refuse(
            action=A.LESSON_START,
            state="FREE",
            limit=2,
            used=2,
            window="daily",
            reason=REASON_LIMIT_REACHED,
        )
        payload = decision.as_dict(is_paid=False, language="uz")["paywall"]

        # Klient tayyor matnni ham, kalitni ham oladi — oflayn zaxira uchun.
        self.assertIn("title", payload)
        self.assertIn("title_key", payload)
        self.assertTrue(payload["title"].strip())

    def test_a_refusal_without_a_language_carries_keys_only(self):
        decision = refuse(
            action=A.AI_TEXT,
            state="FREE",
            limit=5,
            used=5,
            window="daily",
            reason=REASON_LIMIT_REACHED,
        )
        payload = decision.as_dict()["paywall"]

        self.assertIn("title_key", payload)
        self.assertNotIn("title", payload)

    def test_every_cta_points_at_the_recommended_plan(self):
        # Bitta CTA — bitta nishon.
        for action in A.ACTIONS:
            with self.subTest(action=action):
                self.assertEqual(RECOMMENDED_PLAN, paywall_for(action).plan_hint)

    def test_the_voice_surface_is_kept_apart_from_the_rest_of_ai(self):
        # Bot ovozi o'z matnini oladi: "AI limiti tugadi" degan xabar
        # ovoz uchun chalkash bo'lardi.
        self.assertEqual("voice", paywall_for(A.AI_VOICE).surface)
        self.assertEqual("ai", paywall_for(A.AI_TEXT).surface)
        self.assertNotEqual(
            t("paywall_voice_title", "uz"), t("paywall_ai_title", "uz")
        )


if __name__ == "__main__":
    unittest.main()

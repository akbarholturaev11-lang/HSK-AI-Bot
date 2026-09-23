"""Bir xil foydalanuvchi — barcha klientda bir xil qulf.

Bu loyihadagi eng ko'zga tashlanadigan nomutanosiblik edi: Mini App keng
predikatni (`has_unlimited_course_access` — obuna YOKI vaqtinchalik kirish),
desktop va Android esa torini (`is_paid_user` — faqat tasdiqlangan to'lov)
ishlatardi.

Natijasi: referral mukofoti yoki otziv bonusi olgan odam telefonda darsni
ochardi, o'sha lahzada desktopda esa "obuna kerak" devoriga urilardi. Hech
qanday xato yozilmasdi — shunchaki ikki javob.

Endi ikkalasi ham `has_full_access(resolve_state(user))` ga qaraydi.
"""

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from app.services.course_miniapp_access_service import CourseMiniAppAccessService
from app.services.entitlements.state import (
    EntitlementState,
    has_full_access,
    resolve_state,
)
from app.services.study_miniapp_service import StudyMiniAppService


def _user(**overrides) -> SimpleNamespace:
    values = {"status": "free", "payment_status": "none", "end_date": None}
    values.update(overrides)
    return SimpleNamespace(**values)


PAID = _user(
    status="active",
    payment_status="approved",
    end_date=datetime.now(timezone.utc) + timedelta(days=30),
)
#: Referral mukofoti va otziv bonusi shu shaklni qoldiradi.
TEMP_ACCESS = _user(status="active", end_date=datetime.now(timezone.utc) + timedelta(days=2))
FREE = _user()
EXPIRED = _user(status="active", payment_status="approved", end_date=None)
BLOCKED = _user(status="blocked")
#: 7 kunlik Pro trial `status` ga TEGMAYDI — u alohida ustunlarda yashaydi.
TRIAL = _user(pro_trial_ends_at=datetime.now(timezone.utc) + timedelta(days=3))
TRIAL_OVER = _user(pro_trial_ends_at=datetime.now(timezone.utc) - timedelta(days=1))


class OnePredicateForContentTests(unittest.TestCase):
    def test_the_temporary_access_user_is_the_one_that_used_to_differ(self):
        # Eski ikki predikat aynan SHU foydalanuvchida ajralardi.
        self.assertFalse(CourseMiniAppAccessService.is_paid_user(TEMP_ACCESS))
        self.assertTrue(
            CourseMiniAppAccessService.has_unlimited_course_access(TEMP_ACCESS)
        )
        # Yangi predikat kengrog'ini tanlaydi — kontent ochiq.
        self.assertTrue(has_full_access(resolve_state(TEMP_ACCESS)))

    def test_the_trial_user_is_the_one_that_differed_next(self):
        """Trial faol paytda Mini App uni "to'lamagan" deb bilardi.

        Natijasi ko'rinib turardi: trial ochilgan bo'lsa ham reklama chiqar,
        profilda "HSK AI Pro oling" tugmasi turar edi. Reklama servisi
        allaqachon markaziy dvigatelga qaraydi — endi bu predikat ham.
        """
        self.assertFalse(CourseMiniAppAccessService.is_paid_user(TRIAL))
        self.assertTrue(CourseMiniAppAccessService.has_unlimited_course_access(TRIAL))
        self.assertEqual(EntitlementState.TRIAL_ACTIVE, resolve_state(TRIAL))

    def test_the_trial_closes_when_it_runs_out(self):
        """Muddat o'tgach hech qanday fon vazifasini kutmasdan yopiladi."""
        self.assertFalse(
            CourseMiniAppAccessService.has_unlimited_course_access(TRIAL_OVER)
        )
        self.assertFalse(StudyMiniAppService.has_unlimited_course_access(TRIAL_OVER))

    def test_every_user_shape_gets_one_answer(self):
        expected = {
            "paid": (PAID, True),
            "temp_access": (TEMP_ACCESS, True),
            "trial": (TRIAL, True),
            "trial_over": (TRIAL_OVER, False),
            "free": (FREE, False),
            "expired": (EXPIRED, False),
            "blocked": (BLOCKED, False),
        }
        for name, (user, opens) in expected.items():
            with self.subTest(user=name):
                self.assertEqual(opens, has_full_access(resolve_state(user)))

    def test_the_new_predicate_matches_the_wide_legacy_one(self):
        # Mini App bugungi xatti-harakatini SAQLAYDI — u kengini ishlatardi.
        for user in (PAID, TEMP_ACCESS, TRIAL, TRIAL_OVER, FREE, EXPIRED, BLOCKED):
            with self.subTest(user=user.status):
                self.assertEqual(
                    CourseMiniAppAccessService.has_unlimited_course_access(user),
                    has_full_access(resolve_state(user)),
                )

    def test_the_study_mini_app_agrees_too(self):
        for user in (PAID, TEMP_ACCESS, TRIAL, TRIAL_OVER, FREE):
            with self.subTest(user=user.status):
                self.assertEqual(
                    StudyMiniAppService.has_unlimited_course_access(user),
                    has_full_access(resolve_state(user)),
                )

    def test_billing_and_content_stay_separate(self):
        # To'lov UI si vaqtinchalik kirishni OBUNA deb ko'rsatmasligi kerak.
        state = resolve_state(TEMP_ACCESS)
        self.assertEqual(EntitlementState.TEMP_ACCESS, state)
        self.assertTrue(has_full_access(state))
        self.assertFalse(CourseMiniAppAccessService.is_paid_user(TEMP_ACCESS))


class DesktopUsesTheSharedPredicateTests(unittest.TestCase):
    def test_the_desktop_course_service_no_longer_uses_the_narrow_predicate(self):
        source = Path("app/services/desktop_course_service.py").read_text(
            encoding="utf-8"
        )
        # Xarita, yengil sync, dars va yakunlash — barchasi yagona predikatga
        # o'tdi. Sync endi to'liq xaritani so'ramasdan access o'zgarganini
        # kuzatadi, shuning uchun unga ham ayni qaror kerak.
        # Xarita `resolve_state` natijasini qayta ishlatadi, shuning uchun bu
        # himoya formatga emas, to'rtta haqiqiy `has_full_access` qaroriga bog'liq.
        self.assertEqual(4, source.count("has_full_access("))
        self.assertNotIn("is_paid = CourseMiniAppAccessService.is_paid_user(user)", source)
        self.assertNotIn("is_paid = access.is_paid_user(user)", source)


if __name__ == "__main__":
    unittest.main()

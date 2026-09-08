"""Referral triali byudjeti foydalanuvchi oynasiga qanday bog'langan.

`AccessService._get_current_referral_trial_budget` byudjetni faqat uning
`starts_at`/`ends_at` i foydalanuvchining `start_date`/`end_date` iga
**±5 soniya** ichida mos kelsa qabul qiladi. Ya'ni bu ikki ustun byudjet uchun
amalda birlamchi kalit.

Bu fayl o'sha bog'lanishni qotiradi. Kelajakda kimdir `start_date`/`end_date`
ga yozadigan yangi yo'l qo'shsa (masalan 7 kunlik Pro trial), shu testlar
darhol qizil bo'ladi — chunki byudjet jimgina uzilib qolishi mumkin va
foydalanuvchi hech qanday xatosiz AI kirishini yo'qotadi.
"""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.access_service import AccessService


BASE = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)
END = BASE + timedelta(days=3)


def _service() -> AccessService:
    # `_is_same_active_window` sof solishtiruv — sessiyaga umuman tegmaydi.
    return AccessService(None)


def _user(start=BASE, end=END) -> SimpleNamespace:
    return SimpleNamespace(start_date=start, end_date=end)


def _budget(start=BASE, end=END) -> SimpleNamespace:
    return SimpleNamespace(starts_at=start, ends_at=end)


class ReferralBudgetBindingTests(unittest.TestCase):
    def test_an_exact_window_matches(self):
        self.assertTrue(_service()._is_same_active_window(_user(), _budget()))

    def test_the_tolerance_is_five_seconds_on_the_start(self):
        for drift, expected in ((0, True), (5, True), (6, False), (-5, True), (-6, False)):
            with self.subTest(drift=drift):
                budget = _budget(start=BASE + timedelta(seconds=drift))
                self.assertEqual(
                    expected, _service()._is_same_active_window(_user(), budget)
                )

    def test_the_tolerance_is_five_seconds_on_the_end(self):
        for drift, expected in ((0, True), (5, True), (6, False), (-5, True), (-6, False)):
            with self.subTest(drift=drift):
                budget = _budget(end=END + timedelta(seconds=drift))
                self.assertEqual(
                    expected, _service()._is_same_active_window(_user(), budget)
                )

    def test_a_naive_datetime_is_read_as_utc(self):
        # Postgres timezone bilan qaytaradi, SQLite naive. Bog'lanish ikkalasida
        # ham bir xil ishlashi kerak.
        naive_user = _user(start=BASE.replace(tzinfo=None), end=END.replace(tzinfo=None))
        self.assertTrue(_service()._is_same_active_window(naive_user, _budget()))

    def test_a_missing_date_never_matches(self):
        # Yarim to'ldirilgan qator byudjetni "mos" deb ko'rsatmasligi kerak.
        self.assertFalse(_service()._is_same_active_window(_user(start=None), _budget()))
        self.assertFalse(_service()._is_same_active_window(_user(end=None), _budget()))
        self.assertFalse(_service()._is_same_active_window(_user(), _budget(start=None)))
        self.assertFalse(_service()._is_same_active_window(_user(), _budget(end=None)))

    def test_a_different_window_does_not_match(self):
        # Yangi kirish oynasi ochilsa (masalan mukofot yangilansa), eski
        # byudjet unga bog'lanmaydi.
        other = _budget(start=BASE + timedelta(days=1), end=END + timedelta(days=1))
        self.assertFalse(_service()._is_same_active_window(_user(), other))


if __name__ == "__main__":
    unittest.main()

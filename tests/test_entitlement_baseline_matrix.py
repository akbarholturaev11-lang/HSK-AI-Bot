"""Bugungi kirish holati — to'liq haqiqat jadvali.

Bu yerda yangi qoida yo'q. Jadval `UserAccessStateService` ning HOZIRGI
javoblaridan olingan va shu holicha qotirilgan.

Nima uchun kerak: markaziy entitlement dvigateli (`resolve_state`) shu
javoblarni bir-biriga bir xil takrorlashi shart. Dvigatel yozilgach, uning
testi shu faylning aynan o'zini takrorlaydi — agar biror katakcha farq qilsa,
bu ko'chirish emas, xatti-harakat o'zgarishi degani.

Jadvaldagi eng muhim uch qatorni alohida ta'kidlash kerak, chunki ular
intuitiv emas:

* `active` + `pending` + kelasi `end_date` → `temporary_trial` va kurs
  KIRISHI OCHIQ. Ya'ni to'lovi hali tasdiqlanmagan odam ham to'liq kirishga
  ega bo'lishi mumkin — bu holatga referral/otziv bonusi ham tushadi.
* `active` + `approved`, lekin `end_date` YO'Q → `expired`, `paid` emas.
* `trial` statusi `end_date` ga umuman qaramaydi va hech qachon kursni ochmaydi.
"""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.user_access_state_service import (
    UserAccessState,
    UserAccessStateService,
)


NOW = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
PAST = NOW - timedelta(days=1)
FUTURE = NOW + timedelta(days=1)

_END = {"past": PAST, "future": FUTURE, "none": None}

# (status, payment_status, end_date kaliti) -> (classify, is_paid, has_unlimited)
BASELINE = {
    # --- free: hech qanday kombinatsiya kirish bermaydi -------------------
    ("free", "none", "past"): ("free", False, False),
    ("free", "none", "future"): ("free", False, False),
    ("free", "none", "none"): ("free", False, False),
    ("free", "approved", "past"): ("free", False, False),
    ("free", "approved", "future"): ("free", False, False),
    ("free", "approved", "none"): ("free", False, False),
    ("free", "pending", "past"): ("free", False, False),
    ("free", "pending", "future"): ("free", False, False),
    ("free", "pending", "none"): ("free", False, False),
    # --- active: yagona holat, unda uch xil natija chiqadi ----------------
    ("active", "none", "past"): ("free", False, False),
    ("active", "none", "future"): ("temporary_trial", False, True),
    ("active", "none", "none"): ("free", False, False),
    ("active", "approved", "past"): ("expired", False, False),
    ("active", "approved", "future"): ("paid", True, True),
    ("active", "approved", "none"): ("expired", False, False),
    ("active", "pending", "past"): ("free", False, False),
    ("active", "pending", "future"): ("temporary_trial", False, True),
    ("active", "pending", "none"): ("free", False, False),
    # --- trial: end_date umuman hisobga olinmaydi -------------------------
    ("trial", "none", "past"): ("trial", False, False),
    ("trial", "none", "future"): ("trial", False, False),
    ("trial", "none", "none"): ("trial", False, False),
    ("trial", "approved", "past"): ("trial", False, False),
    ("trial", "approved", "future"): ("trial", False, False),
    ("trial", "approved", "none"): ("trial", False, False),
    ("trial", "pending", "past"): ("trial", False, False),
    ("trial", "pending", "future"): ("trial", False, False),
    ("trial", "pending", "none"): ("trial", False, False),
    # --- expired ----------------------------------------------------------
    ("expired", "none", "past"): ("expired", False, False),
    ("expired", "none", "future"): ("expired", False, False),
    ("expired", "none", "none"): ("expired", False, False),
    ("expired", "approved", "past"): ("expired", False, False),
    ("expired", "approved", "future"): ("expired", False, False),
    ("expired", "approved", "none"): ("expired", False, False),
    ("expired", "pending", "past"): ("expired", False, False),
    ("expired", "pending", "future"): ("expired", False, False),
    ("expired", "pending", "none"): ("expired", False, False),
    # --- blocked: hamma narsadan ustun ------------------------------------
    ("blocked", "none", "past"): ("blocked", False, False),
    ("blocked", "none", "future"): ("blocked", False, False),
    ("blocked", "none", "none"): ("blocked", False, False),
    ("blocked", "approved", "past"): ("blocked", False, False),
    ("blocked", "approved", "future"): ("blocked", False, False),
    ("blocked", "approved", "none"): ("blocked", False, False),
    ("blocked", "pending", "past"): ("blocked", False, False),
    ("blocked", "pending", "future"): ("blocked", False, False),
    ("blocked", "pending", "none"): ("blocked", False, False),
    # --- noma'lum status: doim `free` ga tushadi --------------------------
    ("wat", "none", "past"): ("free", False, False),
    ("wat", "none", "future"): ("free", False, False),
    ("wat", "none", "none"): ("free", False, False),
    ("wat", "approved", "past"): ("free", False, False),
    ("wat", "approved", "future"): ("free", False, False),
    ("wat", "approved", "none"): ("free", False, False),
    ("wat", "pending", "past"): ("free", False, False),
    ("wat", "pending", "future"): ("free", False, False),
    ("wat", "pending", "none"): ("free", False, False),
}


def _user(status, payment_status, end_key):
    return SimpleNamespace(
        status=status,
        payment_status=payment_status,
        end_date=_END[end_key],
    )


class EntitlementBaselineMatrixTests(unittest.TestCase):
    def test_every_combination_matches_the_recorded_baseline(self):
        for key, expected in BASELINE.items():
            with self.subTest(status=key[0], payment=key[1], end=key[2]):
                user = _user(*key)
                actual = (
                    UserAccessStateService.classify(user, now=NOW),
                    UserAccessStateService.is_paid(user, now=NOW),
                    UserAccessStateService.has_unlimited_course_access(user, now=NOW),
                )
                self.assertEqual(expected, actual)

    def test_the_matrix_covers_every_status_the_code_can_produce(self):
        # Jadval to'liq bo'lib qolsin: yangi holat qo'shilsa shu test qizil bo'ladi.
        produced = {expected[0] for expected in BASELINE.values()}
        self.assertEqual(
            {
                UserAccessState.FREE,
                UserAccessState.TEMPORARY_TRIAL,
                UserAccessState.PAID,
                UserAccessState.TRIAL,
                UserAccessState.EXPIRED,
                UserAccessState.BLOCKED,
            },
            produced,
        )

    def test_a_missing_user_is_unknown_and_belongs_to_no_state_set(self):
        self.assertEqual(UserAccessState.UNKNOWN, UserAccessStateService.classify(None))
        self.assertFalse(UserAccessStateService.is_paid(None))
        self.assertFalse(UserAccessStateService.has_unlimited_course_access(None))
        self.assertNotIn(
            UserAccessState.UNKNOWN, UserAccessStateService.COURSE_ELIGIBLE_STATES
        )
        self.assertNotIn(UserAccessState.UNKNOWN, UserAccessStateService.FREE_TIER_STATES)

    def test_only_paid_and_temporary_trial_open_the_course(self):
        # Kontent qulfi uchun yagona predikat shu bo'lishi kerak.
        opens = {key[:2] + (key[2],) for key, value in BASELINE.items() if value[2]}
        states = {BASELINE[key][0] for key in opens}
        self.assertEqual({UserAccessState.PAID, UserAccessState.TEMPORARY_TRIAL}, states)

    def test_a_naive_end_date_is_read_as_utc(self):
        # Postgres timezone bilan, SQLite naive qaytaradi — natija bir xil.
        aware = _user("active", "approved", "future")
        naive = SimpleNamespace(
            status="active",
            payment_status="approved",
            end_date=FUTURE.replace(tzinfo=None),
        )
        self.assertEqual(
            UserAccessStateService.classify(aware, now=NOW),
            UserAccessStateService.classify(naive, now=NOW),
        )

    def test_status_and_payment_are_compared_case_insensitively(self):
        loud = SimpleNamespace(
            status="  ACTIVE ", payment_status="Approved", end_date=FUTURE
        )
        self.assertEqual(
            UserAccessState.PAID, UserAccessStateService.classify(loud, now=NOW)
        )


if __name__ == "__main__":
    unittest.main()

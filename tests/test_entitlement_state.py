"""`resolve_state` eski klassifikatorni aynan takrorlashi.

`tests/test_entitlement_baseline_matrix.py` bugungi haqiqat jadvalini
qotirgan. Bu fayl o'sha jadvalning HAR BIR katakchasini yangi dvigatel
javobiga solishtiradi: agar biror katakcha farq qilsa, bu ko'chirish emas,
xatti-harakat o'zgarishi degani.

Ustiga — 7 kunlik Pro trial. Uning ustunlari hali bazada yo'q (4-bosqichda
qo'shiladi), shuning uchun bu modul ular BO'LMAGANDA ham ishlashi shart.
"""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.entitlements.state import (
    ENTITLEMENT_STATES,
    EntitlementState,
    access_expires_at,
    has_active_pro_trial,
    has_full_access,
    is_billing_paid,
    resolve_state,
)
from app.services.user_access_state_service import UserAccessState

from tests.test_entitlement_baseline_matrix import BASELINE, NOW, _user


#: Eski holat -> yangi nom. Baza matritsasi eski nomlarda yozilgan.
_EXPECTED = {
    UserAccessState.PAID: EntitlementState.PRO_ACTIVE,
    UserAccessState.TEMPORARY_TRIAL: EntitlementState.TEMP_ACCESS,
    UserAccessState.EXPIRED: EntitlementState.EXPIRED,
    UserAccessState.BLOCKED: EntitlementState.BLOCKED,
    UserAccessState.TRIAL: EntitlementState.FREE,
    UserAccessState.FREE: EntitlementState.FREE,
}


def _trial_user(*, ends_in_days: float = 3, revoked=None, **overrides):
    base = {
        "status": "free",
        "payment_status": "none",
        "end_date": None,
        "pro_trial_started_at": NOW - timedelta(days=1),
        "pro_trial_ends_at": NOW + timedelta(days=ends_in_days),
        "pro_trial_revoked_at": revoked,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class ResolveStateMatchesBaselineTests(unittest.TestCase):
    def test_every_baseline_row_maps_to_the_same_state(self):
        for key, expected in BASELINE.items():
            with self.subTest(status=key[0], payment=key[1], end=key[2]):
                self.assertEqual(
                    _EXPECTED[expected[0]], resolve_state(_user(*key), now=NOW)
                )

    def test_full_access_matches_the_old_unlimited_predicate(self):
        # `has_full_access` eski `has_unlimited_course_access` ni takrorlashi
        # kerak — trialsiz foydalanuvchilar uchun.
        for key, expected in BASELINE.items():
            with self.subTest(status=key[0], payment=key[1], end=key[2]):
                state = resolve_state(_user(*key), now=NOW)
                self.assertEqual(expected[2], has_full_access(state))

    def test_billing_paid_matches_the_old_is_paid_predicate(self):
        for key, expected in BASELINE.items():
            with self.subTest(status=key[0], payment=key[1], end=key[2]):
                state = resolve_state(_user(*key), now=NOW)
                self.assertEqual(expected[1], is_billing_paid(state))


class ProTrialStateTests(unittest.TestCase):
    def test_a_user_without_the_columns_is_never_on_trial(self):
        # 4-bosqich migratsiyasidan OLDINGI holat: ustunlar umuman yo'q.
        legacy = SimpleNamespace(status="free", payment_status="none", end_date=None)
        self.assertFalse(has_active_pro_trial(legacy, now=NOW))
        self.assertEqual(EntitlementState.FREE, resolve_state(legacy, now=NOW))

    def test_an_active_trial_opens_the_content(self):
        user = _trial_user()
        state = resolve_state(user, now=NOW)

        self.assertEqual(EntitlementState.TRIAL_ACTIVE, state)
        self.assertTrue(has_full_access(state))
        # Lekin trial OBUNA emas — to'lov UI si uni pullik deb ko'rsatmasin.
        self.assertFalse(is_billing_paid(state))

    def test_an_expired_trial_falls_back_to_free(self):
        user = _trial_user(ends_in_days=-1)
        self.assertEqual(EntitlementState.FREE, resolve_state(user, now=NOW))

    def test_a_revoked_trial_is_over_immediately(self):
        user = _trial_user(revoked=NOW - timedelta(hours=1))
        self.assertEqual(EntitlementState.FREE, resolve_state(user, now=NOW))

    def test_a_paid_subscription_wins_over_an_active_trial(self):
        # Obunachi trialni "sarflab" qo'ymasligi kerak.
        user = _trial_user(
            status="active", payment_status="approved", end_date=NOW + timedelta(days=20)
        )
        self.assertEqual(EntitlementState.PRO_ACTIVE, resolve_state(user, now=NOW))

    def test_referral_temp_access_wins_over_an_active_trial(self):
        # TEMP_ACCESS `users.status` ga tayanadi, trial esa unga tegmaydi —
        # ikkalasi bir vaqtda bo'lishi mumkin va TEMP_ACCESS ustun turadi.
        user = _trial_user(status="active", end_date=NOW + timedelta(days=2))
        self.assertEqual(EntitlementState.TEMP_ACCESS, resolve_state(user, now=NOW))

    def test_a_blocked_user_stays_blocked_even_with_a_trial(self):
        user = _trial_user(status="blocked")
        self.assertEqual(EntitlementState.BLOCKED, resolve_state(user, now=NOW))
        self.assertFalse(has_full_access(EntitlementState.BLOCKED))

    def test_a_naive_trial_end_is_read_as_utc(self):
        user = _trial_user()
        user.pro_trial_ends_at = (NOW + timedelta(days=3)).replace(tzinfo=None)
        self.assertEqual(EntitlementState.TRIAL_ACTIVE, resolve_state(user, now=NOW))


class ExpiryTests(unittest.TestCase):
    def test_each_state_reports_the_right_end(self):
        trial = _trial_user()
        self.assertEqual(
            trial.pro_trial_ends_at,
            access_expires_at(trial, EntitlementState.TRIAL_ACTIVE, now=NOW),
        )

        paid = _user("active", "approved", "future")
        self.assertEqual(
            paid.end_date, access_expires_at(paid, EntitlementState.PRO_ACTIVE, now=NOW)
        )

        free = _user("free", "none", "none")
        self.assertIsNone(access_expires_at(free, EntitlementState.FREE, now=NOW))


class StateSetTests(unittest.TestCase):
    def test_a_missing_user_is_free_rather_than_an_error(self):
        # Limit yo'lida `None` user hech qachon exception bermasin.
        self.assertEqual(EntitlementState.FREE, resolve_state(None, now=NOW))

    def test_every_state_is_listed(self):
        self.assertEqual(
            {
                EntitlementState.FREE,
                EntitlementState.TRIAL_ACTIVE,
                EntitlementState.PRO_ACTIVE,
                EntitlementState.TEMP_ACCESS,
                EntitlementState.EXPIRED,
                EntitlementState.BLOCKED,
            },
            set(ENTITLEMENT_STATES),
        )


if __name__ == "__main__":
    unittest.main()

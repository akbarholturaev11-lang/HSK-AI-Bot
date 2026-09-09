"""Profil statusi HAQIQIY holatga moslashadi.

Foydalanuvchi buni jonli ilovada aytdi: profilда statusni to'g'ri ko'rsat —
"sinov muddati" (trial), maqsad va boshqalar barcha holatga moslashsin.

Ikki qism:

1. **Server** — `/api/v3/map` javobidagi `user` obyekti markaziy entitlement
   dvigatelidan aniq holatni (`state`), sodda yorliqni (`plan`) va kirish
   muddatini (`access_ends_at`) beradi. Klient sanani o'zi taxmin qilmaydi.

2. **Mini App** — profil kartasi shu yorliqqa qarab ko'rinadi: pro/temp da
   holatni AYTADI (taklif emas), trial da nechchi kun qolganini, free da
   taklif qiladi. Maqsad esa onboarding bilan ayni nomlar bilan chiqadi.
"""

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.entitlements.state import EntitlementState, access_expires_at, resolve_state


MINIAPP = Path("app/static/course-v3.html").read_text(encoding="utf-8")


class _User:
    def __init__(self, **kw):
        self.status = kw.get("status", "free")
        self.payment_status = kw.get("payment_status", "none")
        self.end_date = kw.get("end_date")
        self.pro_trial_ends_at = kw.get("pro_trial_ends_at")


def _plan_for(state):
    return {
        EntitlementState.PRO_ACTIVE: "pro",
        EntitlementState.TRIAL_ACTIVE: "trial",
        EntitlementState.TEMP_ACCESS: "temp",
    }.get(state, "free")


class ServerStatePayloadTests(unittest.TestCase):
    """`resolve_state` + `access_expires_at` — payload aynan shularга tayanadi."""

    def test_a_free_learner_is_free_with_no_end(self):
        user = _User()
        state = resolve_state(user)
        self.assertEqual("free", _plan_for(state))
        self.assertIsNone(access_expires_at(user, state))

    def test_an_active_trial_reports_trial_and_its_end(self):
        ends = datetime.now(timezone.utc) + timedelta(days=5)
        user = _User(status="trial", pro_trial_ends_at=ends)
        state = resolve_state(user)
        self.assertEqual(EntitlementState.TRIAL_ACTIVE, state)
        self.assertEqual("trial", _plan_for(state))
        self.assertEqual(ends, access_expires_at(user, state))

    def test_a_paid_learner_reports_pro_and_its_end(self):
        ends = datetime.now(timezone.utc) + timedelta(days=30)
        user = _User(status="active", payment_status="approved", end_date=ends)
        state = resolve_state(user)
        self.assertEqual(EntitlementState.PRO_ACTIVE, state)
        self.assertEqual("pro", _plan_for(state))
        self.assertEqual(ends, access_expires_at(user, state))

    def test_a_paid_subscription_outranks_a_trial(self):
        # Obunachi trialini "sarflab" qo'ymasin: holat PRO bo'lib qoladi.
        now = datetime.now(timezone.utc)
        user = _User(status="active", payment_status="approved",
                     end_date=now + timedelta(days=30),
                     pro_trial_ends_at=now + timedelta(days=5))
        self.assertEqual("pro", _plan_for(resolve_state(user)))


class MiniAppProfileMarkupTests(unittest.TestCase):
    def test_the_map_payload_carries_state_plan_and_end(self):
        main = Path("app/main.py").read_text(encoding="utf-8")
        self.assertIn('"state": access_state', main)
        self.assertIn('"access_ends_at": access_ends.isoformat() if access_ends else None', main)
        for plan in ('"pro"', '"trial"', '"temp"'):
            self.assertIn(plan, main)

    def test_the_status_card_reads_the_server_plan(self):
        self.assertIn("var plan=u.plan||(isPaidUser()?", MINIAPP)
        # Faol holat (pro/temp) taklif EMAS — holatni aytadi.
        self.assertIn('if(plan==="pro"||plan==="temp")', MINIAPP)
        self.assertIn('if(plan==="trial")', MINIAPP)

    def test_the_end_date_comes_from_the_server(self):
        self.assertIn("function fmtAccessDate(iso)", MINIAPP)
        self.assertIn("u.access_ends_at", MINIAPP)

    def test_the_goal_badge_uses_the_onboarding_labels(self):
        # Maqsad nomlari onboarding bilan AYNI manba (studySetupT), ya'ni
        # profildagi maqsad tanlov ekranidagidek yoziladi.
        self.assertIn("function goalLabel()", MINIAPP)
        self.assertIn("studySetupT().goals", MINIAPP)
        self.assertIn('<span class="lvb goal">', MINIAPP)


if __name__ == "__main__":
    unittest.main()

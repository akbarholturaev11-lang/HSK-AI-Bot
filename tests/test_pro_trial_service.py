"""7 kunlik Pro trial.

Eng muhim tekshiruv bu faylda emas — u `tests/test_referral_trial_contract.py`
da: trial qo'shilgandan keyin ham referral shartnomasi o'zgarmagan bo'lishi
kerak. Bu yerda esa o'sha xavfsizlikning sababi qotiriladi:

* `start()` `status`, `payment_status`, `start_date` va `end_date` ga
  TEGMAYDI — referral byudjeti aynan o'sha ikki sanaga bog'langan;
* faol byudjeti bor odamga trial berilmaydi, chunki byudjet yaratish avval
  hamma faol byudjetni `expired` qiladi;
* trial tugashi foydalanuvchini bepul darajaga tushiradi, progressiga
  tegmaydi.
"""

import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.ai_usage import AIUsageBudget
from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from app.db.models.user import User
from app.services.ai_usage_budget_service import REFERRAL_TRIAL_PLAN_TYPE
from app.services.entitlements.limits_config import LimitConfigService
from app.services.entitlements.state import EntitlementState, resolve_state
from app.services.pro_trial_service import (
    PRO_TRIAL_PLAN_TYPE,
    REASON_ACTIVE_BUDGET,
    REASON_ALREADY_USED,
    REASON_NOT_APPLICABLE,
    ProTrialService,
)


TELEGRAM_ID = 8200


def _user(**overrides) -> User:
    now = datetime.now(timezone.utc)
    fields = dict(
        id=1,
        telegram_id=TELEGRAM_ID,
        full_name="Trial tester",
        language="uz",
        level="hsk1",
        learning_mode="course",
        voice_mode="none",
        status="free",
        payment_status="none",
        question_limit=5,
        questions_used=0,
        bonus_questions=0,
        bonus_questions_used=0,
        discount_referral_count=0,
        discount_eligible=False,
        discount_used=False,
        created_at=now - timedelta(days=10),
        last_active_at=now,
    )
    fields.update(overrides)
    return User(**fields)


class ProTrialServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)
        # Voronka ataylab o'z sessiyasida yozadi.
        self.funnel_patch = patch(
            "app.services.conversion_funnel_service.async_session_maker", self.sessions
        )
        self.funnel_patch.start()

    async def asyncTearDown(self):
        self.funnel_patch.stop()
        await self.db.dispose()

    async def _seed(self, **overrides):
        async with self.sessions() as session:
            session.add(_user(**overrides))
            await session.commit()

    async def _get(self, session) -> User:
        return (
            await session.execute(select(User).where(User.telegram_id == TELEGRAM_ID))
        ).scalar_one()

    async def _budgets(self):
        async with self.sessions() as session:
            return list(
                (
                    await session.execute(
                        select(AIUsageBudget).order_by(AIUsageBudget.id)
                    )
                )
                .scalars()
                .all()
            )

    async def _events(self):
        async with self.sessions() as session:
            return [
                row.event_name
                for row in (
                    await session.execute(select(ConversionFunnelEvent))
                ).scalars().all()
            ]

    # --- boshlash ---------------------------------------------------------

    async def test_a_free_user_can_start_the_trial_once(self):
        await self._seed()

        async with self.sessions() as session:
            user = await self._get(session)
            first = await ProTrialService(session).start(user, source="miniapp")
            await session.commit()

        self.assertTrue(first["ok"])
        self.assertEqual(7, first["days"])

        async with self.sessions() as session:
            user = await self._get(session)
            self.assertEqual(EntitlementState.TRIAL_ACTIVE, resolve_state(user))
            second = await ProTrialService(session).start(user, source="miniapp")

        self.assertFalse(second["ok"])
        self.assertEqual(REASON_ALREADY_USED, second["error"])

    async def test_starting_the_trial_never_touches_the_subscription_columns(self):
        """Butun modulning eng muhim invarianti.

        `AccessService._is_same_active_window` referral byudjetini
        `start_date`/`end_date` ga ±5 soniya bilan bog'laydi. Bu ustunlarga
        yozuv o'sha byudjetni jimgina uzib qo'yadi.
        """
        await self._seed()

        async with self.sessions() as session:
            user = await self._get(session)
            before = (
                user.status,
                user.payment_status,
                user.start_date,
                user.end_date,
            )
            await ProTrialService(session).start(user, source="miniapp")
            await session.commit()

        async with self.sessions() as session:
            user = await self._get(session)
            after = (user.status, user.payment_status, user.start_date, user.end_date)

        self.assertEqual(before, after)
        self.assertEqual("free", after[0])
        self.assertEqual("none", after[1])
        self.assertIsNone(after[2])
        self.assertIsNone(after[3])

    async def test_the_trial_budget_is_capped_and_its_own_plan_type(self):
        await self._seed()

        async with self.sessions() as session:
            await ProTrialService(session).start(await self._get(session), source="bot")
            await session.commit()

        budgets = await self._budgets()
        self.assertEqual(1, len(budgets))
        self.assertEqual(PRO_TRIAL_PLAN_TYPE, budgets[0].plan_type)
        self.assertEqual("active", budgets[0].status)
        self.assertGreater(float(budgets[0].total_budget_usd), 0)

    async def test_an_active_budget_blocks_the_trial_instead_of_killing_it(self):
        # Referral mukofoti olgan odam trial tugmasini bossa, byudjeti
        # o'chib ketmasligi kerak.
        await self._seed()
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            session.add(
                AIUsageBudget(
                    user_telegram_id=TELEGRAM_ID,
                    plan_type=REFERRAL_TRIAL_PLAN_TYPE,
                    amount=2,
                    currency="usd",
                    total_budget_usd=2.0,
                    segment_1_budget_usd=1.0,
                    segment_2_budget_usd=1.0,
                    segment_1_spent_usd=0.0,
                    segment_2_spent_usd=0.0,
                    current_window_spent_usd=0.0,
                    window_started_at=now,
                    starts_at=now,
                    ends_at=now + timedelta(days=3),
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.commit()

            result = await ProTrialService(session).start(
                await self._get(session), source="miniapp"
            )
            await session.commit()

        self.assertFalse(result["ok"])
        self.assertEqual(REASON_ACTIVE_BUDGET, result["error"])

        budgets = await self._budgets()
        self.assertEqual(1, len(budgets))
        self.assertEqual("active", budgets[0].status)
        self.assertEqual(REFERRAL_TRIAL_PLAN_TYPE, budgets[0].plan_type)

        async with self.sessions() as session:
            self.assertFalse((await self._get(session)).trial_used)

    async def test_a_paid_user_is_not_offered_the_trial(self):
        await self._seed(
            status="active",
            payment_status="approved",
            end_date=datetime.now(timezone.utc) + timedelta(days=30),
        )

        async with self.sessions() as session:
            result = await ProTrialService(session).start(
                await self._get(session), source="miniapp"
            )

        self.assertFalse(result["ok"])
        self.assertEqual(REASON_NOT_APPLICABLE, result["error"])

    async def test_a_blocked_user_is_not_offered_the_trial(self):
        await self._seed(status="blocked")

        async with self.sessions() as session:
            result = await ProTrialService(session).start(
                await self._get(session), source="miniapp"
            )

        self.assertFalse(result["ok"])

    # --- kill-switch ------------------------------------------------------

    async def test_the_kill_switch_stops_new_trials_immediately(self):
        # Fake akkauntlar ko'paysa admin bir bosishda yopadi — deploy kerak emas.
        await self._seed()
        async with self.sessions() as session:
            await LimitConfigService(session).save_config(
                {
                    "plans": {
                        EntitlementState.FREE: {
                            "lesson.start": {"limit": 2, "window": "daily"}
                        }
                    },
                    "trial": {"enabled": False, "disabled_reason": "fake akkauntlar"},
                }
            )
            await session.commit()

            result = await ProTrialService(session).start(
                await self._get(session), source="miniapp"
            )

        self.assertFalse(result["ok"])
        self.assertEqual("fake akkauntlar", result["error"])
        self.assertEqual([], await self._budgets())

    async def test_a_configured_minimum_account_age_is_enforced(self):
        await self._seed(created_at=datetime.now(timezone.utc) - timedelta(minutes=5))
        async with self.sessions() as session:
            await LimitConfigService(session).save_config(
                {
                    "plans": {
                        EntitlementState.FREE: {
                            "lesson.start": {"limit": 2, "window": "daily"}
                        }
                    },
                    "trial": {"enabled": True, "min_account_age_hours": 24},
                }
            )
            await session.commit()

            verdict = await ProTrialService(session).eligibility(await self._get(session))

        self.assertFalse(verdict["eligible"])
        self.assertEqual("trial_account_too_new", verdict["reason"])

    # --- tugash -----------------------------------------------------------

    async def test_an_expired_trial_drops_to_free_and_keeps_everything(self):
        await self._seed()

        async with self.sessions() as session:
            user = await self._get(session)
            await ProTrialService(session).start(user, source="miniapp")
            await session.commit()

        # Muddatni o'tmishga suramiz.
        async with self.sessions() as session:
            user = await self._get(session)
            user.pro_trial_ends_at = datetime.now(timezone.utc) - timedelta(hours=1)
            await session.commit()

            count, ids = await ProTrialService(session).expire_due()
            await session.commit()

        self.assertEqual(1, count)
        self.assertEqual([TELEGRAM_ID], ids)

        async with self.sessions() as session:
            user = await self._get(session)

        self.assertEqual(EntitlementState.FREE, resolve_state(user))
        # Trial tarixi saqlanadi — qachon va qancha berilgani ko'rinib tursin.
        self.assertIsNotNone(user.pro_trial_started_at)
        self.assertIsNotNone(user.pro_trial_ends_at)
        self.assertTrue(user.trial_used)
        # Obuna ustunlari hamon tegilmagan.
        self.assertEqual("free", user.status)
        self.assertIsNone(user.end_date)

    async def test_expiry_is_idempotent(self):
        await self._seed(
            trial_used=True,
            pro_trial_started_at=datetime.now(timezone.utc) - timedelta(days=8),
            pro_trial_ends_at=datetime.now(timezone.utc) - timedelta(days=1),
        )

        async with self.sessions() as session:
            first, _ = await ProTrialService(session).expire_due()
            await session.commit()
            second, _ = await ProTrialService(session).expire_due()

        self.assertEqual(1, first)
        self.assertEqual(0, second)

    async def test_a_running_trial_is_left_alone(self):
        await self._seed(
            trial_used=True,
            pro_trial_started_at=datetime.now(timezone.utc),
            pro_trial_ends_at=datetime.now(timezone.utc) + timedelta(days=3),
        )

        async with self.sessions() as session:
            count, _ = await ProTrialService(session).expire_due()

        self.assertEqual(0, count)

    async def test_an_admin_can_revoke_a_running_trial(self):
        await self._seed()

        async with self.sessions() as session:
            user = await self._get(session)
            await ProTrialService(session).start(user, source="miniapp")
            revoked = await ProTrialService(session).revoke(
                user, admin_telegram_id=777, reason="suiiste'mol"
            )
            await session.commit()

        self.assertTrue(revoked)
        async with self.sessions() as session:
            user = await self._get(session)
        self.assertEqual(EntitlementState.FREE, resolve_state(user))
        # Qayta olishga ham yo'l yo'q.
        self.assertTrue(user.trial_used)

    # --- analitika --------------------------------------------------------

    async def test_the_funnel_records_the_start_and_the_end(self):
        await self._seed()

        async with self.sessions() as session:
            user = await self._get(session)
            await ProTrialService(session).start(user, source="miniapp")
            await session.commit()

        async with self.sessions() as session:
            user = await self._get(session)
            user.pro_trial_ends_at = datetime.now(timezone.utc) - timedelta(hours=1)
            await session.commit()
            await ProTrialService(session).expire_due()
            await session.commit()

        events = await self._events()
        self.assertIn("trial_started", events)
        self.assertIn("trial_expired", events)


if __name__ == "__main__":
    unittest.main()

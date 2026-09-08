"""Referral mukofotining aynan hozirgi shartnomasi.

Bu fayl yangi imkoniyat qo'shmaydi — u bugungi xatti-harakatni qotiradi.
Sabab: markaziy entitlement dvigateli qurilayotganda referral mantiqi
O'ZGARMASLIGI shart, lekin u loyihadagi eng nozik pul yo'li bo'la turib
birorta test bilan qoplanmagan edi.

Ayniqsa muhim ikki narsa:

1. Mukofot `status="active"` qo'yadi va `payment_status` ga TEGMAYDI —
   ya'ni odam `TEMPORARY_TRIAL` bo'ladi, `PAID` emas. Yangi dvigateldagi
   TEMP_ACCESS shartnomasi shunga tayanadi.
2. Byudjetning `starts_at`/`ends_at` foydalanuvchining `start_date`/`end_date`
   siga AYNAN teng bo'lishi kerak: `AccessService._is_same_active_window`
   ularni ±5 soniya aniqlik bilan solishtiradi. Bu ustunlarga tegilsa,
   byudjet jimgina uzilib qoladi va odam hech qanday xatosiz kirishni yo'qotadi.
"""

import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401 — barcha jadval Base ga ro'yxatdan o'tsin
from app.db.base import Base
from app.db.models.ai_usage import AIUsageBudget
from app.db.models.user import User
from app.services.ai_usage_budget_service import REFERRAL_TRIAL_PLAN_TYPE
from app.services.referral_service import (
    REFERRAL_TRIAL_ACCESS_DAYS,
    REFERRAL_TRIAL_AI_BUDGET_USD,
    REFERRAL_TRIAL_REQUIRED_ACTIVE,
    ReferralService,
)
from app.services.user_access_state_service import (
    UserAccessState,
    UserAccessStateService,
)


REFERRER_TELEGRAM_ID = 5000


def _user(user_id: int, telegram_id: int, *, questions_used: int = 0) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
        telegram_id=telegram_id,
        full_name=f"User {telegram_id}",
        language="uz",
        level="hsk1",
        learning_mode="course",
        voice_mode="none",
        status="free",
        payment_status="none",
        question_limit=5,
        questions_used=questions_used,
        bonus_questions=0,
        bonus_questions_used=0,
        discount_referral_count=0,
        discount_eligible=False,
        discount_used=False,
        created_at=now,
        last_active_at=now,
    )


class ReferralTrialContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()

    # --- yordamchilar -----------------------------------------------------

    async def _seed(self, *, invited_count: int, referrer_kwargs=None):
        """Taklif qiluvchi + `invited_count` ta taklif qilingan odam.

        Har bir taklif qilingan odamda `questions_used=2` — ya'ni aktivatsiya
        chegarasidan o'tgan; aks holda servis ularni sanamaydi.
        """
        async with self.sessions() as session:
            referrer = _user(1, REFERRER_TELEGRAM_ID)
            for key, value in (referrer_kwargs or {}).items():
                setattr(referrer, key, value)
            session.add(referrer)
            for index in range(invited_count):
                session.add(_user(10 + index, 6000 + index, questions_used=2))
            await session.commit()

            service = ReferralService(session)
            for index in range(invited_count):
                await service.referral_repo.create(
                    referrer_telegram_id=REFERRER_TELEGRAM_ID,
                    invited_user_telegram_id=6000 + index,
                )
            await session.commit()

    async def _activate(self, index: int) -> None:
        async with self.sessions() as session:
            await ReferralService(session).activate_referral_if_eligible(
                bot=None,
                invited_user_telegram_id=6000 + index,
            )

    async def _referrer(self) -> User:
        async with self.sessions() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == REFERRER_TELEGRAM_ID)
            )
            return result.scalar_one()

    async def _budgets(self) -> list[AIUsageBudget]:
        async with self.sessions() as session:
            result = await session.execute(
                select(AIUsageBudget)
                .where(AIUsageBudget.user_telegram_id == REFERRER_TELEGRAM_ID)
                .order_by(AIUsageBudget.id)
            )
            return list(result.scalars().all())

    async def _activate_until_rewarded(self, *, available: int) -> int:
        """Mukofot chiqquncha aktivatsiya qiladi, nechtasi ketganini qaytaradi.

        0 qaytsa — `available` ta aktivatsiya yetmadi.
        """
        for index in range(available):
            await self._activate(index)
            referrer = await self._referrer()
            if referrer.status == "active":
                return index + 1
        return 0

    # --- chegara ----------------------------------------------------------

    async def test_the_reward_needs_the_required_number_of_activations(self):
        # Chegaradan bittasi kam bo'lsa — mukofot ham, byudjet qatori ham yo'q.
        await self._seed(invited_count=REFERRAL_TRIAL_REQUIRED_ACTIVE - 1)

        spent = await self._activate_until_rewarded(
            available=REFERRAL_TRIAL_REQUIRED_ACTIVE - 1
        )

        self.assertEqual(0, spent, "chegaradan kam aktivatsiya mukofot bermasligi kerak")
        referrer = await self._referrer()
        self.assertEqual("free", referrer.status)
        self.assertIsNone(referrer.end_date)
        self.assertEqual([], await self._budgets())

    async def test_the_first_activation_does_not_count_toward_its_own_window(self):
        """AMALDAGI holat: konstanta 5 deydi, mukofot esa 6-aktivatsiyada keladi.

        Sababi ketma-ketlikda: `referral_repo.activate()` avval `activated_at`
        ni yozadi, keyin `get_trial_activation_progress()` hisoblagich oynasini
        `now()` ga qo'yadi. Birinchi taklifning `activated_at` i o'sha oynadan
        bir lahza OLDIN bo'lgani uchun u hech qachon sanalmaydi.

        Bu test bugungi xatti-harakatni qotiradi, uni to'g'ri deb tasdiqlamaydi:
        bot foydalanuvchiga "5 ta do'st" deb va'da beradi, amalda 6 ta kerak.
        Tuzatish alohida qaror — 0-bosqich hech qanday xatti-harakatni
        o'zgartirmaydi.
        """
        available = REFERRAL_TRIAL_REQUIRED_ACTIVE + 3
        await self._seed(invited_count=available)

        spent = await self._activate_until_rewarded(available=available)

        self.assertEqual(REFERRAL_TRIAL_REQUIRED_ACTIVE + 1, spent)

    async def test_an_invitee_below_the_question_threshold_does_not_activate(self):
        # Aktivatsiya sharti: taklif qilingan odam kamida 2 ta savol bergan.
        await self._seed(invited_count=1)
        async with self.sessions() as session:
            result = await session.execute(select(User).where(User.telegram_id == 6000))
            invitee = result.scalar_one()
            invitee.questions_used = 1
            await session.commit()

        await self._activate(0)

        async with self.sessions() as session:
            service = ReferralService(session)
            referral = await service.referral_repo.get_by_invited_user_telegram_id(6000)
        self.assertEqual("pending", referral.status)
        self.assertIsNone(referral.activated_at)

    # --- bonus ------------------------------------------------------------

    async def test_the_first_activation_grants_exactly_five_bonus_questions(self):
        await self._seed(invited_count=1)

        await self._activate(0)
        self.assertEqual(5, (await self._referrer()).bonus_questions)

        # Takroriy chaqiruv ikkinchi marta bonus bermaydi.
        await self._activate(0)
        self.assertEqual(5, (await self._referrer()).bonus_questions)

    async def test_the_discount_counter_moves_once_per_referral(self):
        # Chegirma hisoblagichi faqat taklif chegirma oynasi ochilgandan
        # KEYIN faollashgan bo'lsa oshadi.
        #
        # `discount_offer_started_at` shu sessiyada qo'yiladi, chunki
        # `referral_service.py:391` ikki sanani XOM solishtiradi. Postgres
        # `DateTime(timezone=True)` ustunini timezone bilan qaytaradi, SQLite
        # esa naive qaytaradi — shuning uchun bu yerda production bilan bir xil
        # (aware) qiymat beriladi. Xom solishtiruv o'zi alohida masala.
        await self._seed(invited_count=1)

        async with self.sessions() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == REFERRER_TELEGRAM_ID)
            )
            # Havola ATAYLAB o'zgaruvchida saqlanadi: `flush()` dan keyin obyekt
            # yana "toza" bo'ladi va identity map uni faqat zaif havola bilan
            # ushlaydi. Havolasiz u yig'ib tashlanadi va servis bazadan yangi
            # (SQLite'da naive) qiymat yuklaydi.
            referrer = result.scalar_one()
            referrer.discount_offer_started_at = datetime.now(timezone.utc) - timedelta(
                days=1
            )
            await session.flush()
            await ReferralService(session).activate_referral_if_eligible(
                bot=None, invited_user_telegram_id=6000
            )
        self.assertEqual(1, (await self._referrer()).discount_referral_count)

        # Takroriy chaqiruv hisoblagichni ikkinchi marta oshirmaydi.
        await self._activate(0)
        self.assertEqual(1, (await self._referrer()).discount_referral_count)

    # --- mukofotning o'zi -------------------------------------------------

    async def test_the_reward_grants_temporary_access_and_never_marks_the_user_paid(self):
        available = REFERRAL_TRIAL_REQUIRED_ACTIVE + 2
        await self._seed(invited_count=available)
        before = datetime.now(timezone.utc)

        spent = await self._activate_until_rewarded(available=available)
        self.assertTrue(spent, "mukofot berilishi kerak edi")

        referrer = await self._referrer()
        # Butun TEMP_ACCESS shartnomasi shu ikki qatorda.
        self.assertEqual("active", referrer.status)
        self.assertEqual("none", referrer.payment_status)
        self.assertEqual(
            UserAccessState.TEMPORARY_TRIAL,
            UserAccessStateService.classify(referrer),
        )
        self.assertFalse(UserAccessStateService.is_paid(referrer))
        self.assertTrue(UserAccessStateService.has_unlimited_course_access(referrer))

        # Muddat: hozirdan REFERRAL_TRIAL_ACCESS_DAYS kun.
        expected_end = before + timedelta(days=REFERRAL_TRIAL_ACCESS_DAYS)
        self.assertLess(
            abs((_as_utc(referrer.end_date) - expected_end).total_seconds()),
            60,
        )
        # Limit hisoblagichi tozalanadi, hisoblagich oynasi mukofot oxiriga suriladi.
        self.assertEqual(0, referrer.questions_used)
        self.assertEqual(
            _as_utc(referrer.end_date),
            _as_utc(referrer.referral_trial_count_started_at),
        )

    async def test_the_reward_budget_is_bound_to_the_user_window_to_the_second(self):
        # `AccessService._is_same_active_window` shu ikki juftlikni ±5 soniya
        # bilan solishtiradi. Farq katta bo'lsa byudjet jimgina uziladi.
        available = REFERRAL_TRIAL_REQUIRED_ACTIVE + 2
        await self._seed(invited_count=available)

        self.assertTrue(await self._activate_until_rewarded(available=available))

        referrer = await self._referrer()
        budgets = await self._budgets()
        self.assertEqual(1, len(budgets))
        budget = budgets[0]

        self.assertEqual(REFERRAL_TRIAL_PLAN_TYPE, budget.plan_type)
        self.assertEqual("active", budget.status)
        self.assertAlmostEqual(
            REFERRAL_TRIAL_AI_BUDGET_USD, float(budget.total_budget_usd), places=6
        )
        self.assertEqual(
            _as_utc(referrer.start_date), _as_utc(budget.starts_at)
        )
        self.assertEqual(_as_utc(referrer.end_date), _as_utc(budget.ends_at))

    async def test_granting_the_reward_expires_any_earlier_budget(self):
        available = REFERRAL_TRIAL_REQUIRED_ACTIVE + 2
        await self._seed(invited_count=available)
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            session.add(
                AIUsageBudget(
                    user_telegram_id=REFERRER_TELEGRAM_ID,
                    payment_id=None,
                    plan_type="1_month",
                    amount=89,
                    currency="TJS",
                    total_budget_usd=4.0,
                    segment_1_budget_usd=2.0,
                    segment_2_budget_usd=2.0,
                    segment_1_spent_usd=0.0,
                    segment_2_spent_usd=0.0,
                    current_window_spent_usd=0.0,
                    window_started_at=now,
                    starts_at=now,
                    ends_at=now + timedelta(days=30),
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.commit()

        self.assertTrue(await self._activate_until_rewarded(available=available))

        budgets = await self._budgets()
        self.assertEqual(2, len(budgets))
        self.assertEqual("expired", budgets[0].status)
        self.assertEqual("active", budgets[1].status)
        self.assertEqual(REFERRAL_TRIAL_PLAN_TYPE, budgets[1].plan_type)

    async def test_a_longer_existing_access_is_never_shortened(self):
        far_end = datetime.now(timezone.utc) + timedelta(days=40)
        available = REFERRAL_TRIAL_REQUIRED_ACTIVE + 2
        await self._seed(
            invited_count=available,
            referrer_kwargs={"status": "active", "end_date": far_end},
        )

        self.assertTrue(await self._activate_until_rewarded(available=available))

        referrer = await self._referrer()
        self.assertEqual(
            far_end.replace(microsecond=0),
            _as_utc(referrer.end_date).replace(microsecond=0),
        )

    async def test_a_paid_referrer_gets_no_trial_reward(self):
        available = REFERRAL_TRIAL_REQUIRED_ACTIVE + 2
        await self._seed(
            invited_count=available,
            referrer_kwargs={
                "status": "active",
                "payment_status": "approved",
                "end_date": datetime.now(timezone.utc) + timedelta(days=20),
            },
        )

        for index in range(available):
            await self._activate(index)

        # Obunachiga trial berilmaydi: byudjet qatori umuman yaratilmaydi.
        self.assertEqual([], await self._budgets())
        referrer = await self._referrer()
        self.assertEqual("approved", referrer.payment_status)
        self.assertEqual(UserAccessState.PAID, UserAccessStateService.classify(referrer))
        # Bonus esa baribir beriladi — u obunadan mustaqil.
        self.assertEqual(5 * available, referrer.bonus_questions)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


if __name__ == "__main__":
    unittest.main()

"""Dvigatel limitlarni qanday sanaydi va yozadi.

Xotiradagi haqiqiy baza bilan ishlaydi, chunki tekshirilayotgan narsa aynan
saqlash: dvigatel YANGI hisoblagich yaratmasligi va eski yo'ldan ko'proq
bermasligi kerak.

Ikkita eng muhim tekshiruv:

* `test_the_engine_reads_the_same_rows_the_legacy_path_writes` — eski yo'l
  yozgan slotni dvigatel ko'radi. Aks holda ko'chirish kunida hamma
  foydalanuvchi limitini noldan boshlab qo'yardi.
* `test_a_spent_lifetime_slot_is_never_reopened` — bir joyda umrbod slotni
  sarflagan odam dvigatel orqali yangisini olmaydi.
"""

import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.course_feature_usage import CourseFeatureUsage
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.user import User
from app.services.course_miniapp_access_service import CourseMiniAppAccessService
from app.services.entitlements import actions as A
from app.services.entitlements import decision as D
from app.services.entitlements.engine import EntitlementEngine
from app.services.entitlements.limits_config import (
    WINDOW_DAILY,
    LimitConfig,
    config_from_payload,
    default_config,
)
from app.services.entitlements.state import EntitlementState


def _user(user_id=1, telegram_id=4100, **overrides) -> User:
    now = datetime.now(timezone.utc)
    fields = dict(
        id=user_id,
        telegram_id=telegram_id,
        full_name="Engine tester",
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
        created_at=now,
        last_active_at=now,
    )
    fields.update(overrides)
    return User(**fields)


def _config_with(state: str, action: str, limit, window=WINDOW_DAILY) -> LimitConfig:
    return config_from_payload(
        {"plans": {state: {action: {"limit": limit, "window": window}}}}
    )


class EngineLimitTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine_db = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.engine_db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine_db, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine_db.dispose()

    async def _seed(self, **overrides) -> None:
        async with self.sessions() as session:
            session.add(_user(**overrides))
            await session.commit()

    async def _get_user(self, session) -> User:
        from sqlalchemy import select

        return (
            await session.execute(select(User).where(User.telegram_id == 4100))
        ).scalar_one()

    # --- asosiy oqim ------------------------------------------------------

    async def test_a_free_user_spends_the_configured_number_of_slots(self):
        await self._seed()
        config = _config_with(EntitlementState.FREE, A.PRACTICE_RECOGNITION, 2)

        async with self.sessions() as session:
            user = await self._get_user(session)
            engine = EntitlementEngine(session, config=config)

            first = await engine.consume(user, A.PRACTICE_RECOGNITION)
            second = await engine.consume(user, A.PRACTICE_RECOGNITION)
            third = await engine.consume(user, A.PRACTICE_RECOGNITION)

        self.assertTrue(first.allowed)
        self.assertEqual(1, first.remaining)
        self.assertTrue(second.allowed)
        self.assertEqual(0, second.remaining)
        self.assertFalse(third.allowed)
        self.assertEqual(D.REASON_LIMIT_REACHED, third.reason)
        self.assertEqual(D.LEGACY_LIMIT_ERROR, third.legacy_error)

    async def test_check_never_spends_a_slot(self):
        await self._seed()
        config = _config_with(EntitlementState.FREE, A.PRACTICE_RECOGNITION, 1)

        async with self.sessions() as session:
            user = await self._get_user(session)
            engine = EntitlementEngine(session, config=config)

            for _ in range(5):
                self.assertTrue((await engine.check(user, A.PRACTICE_RECOGNITION)).allowed)
            self.assertTrue((await engine.consume(user, A.PRACTICE_RECOGNITION)).allowed)
            self.assertFalse((await engine.check(user, A.PRACTICE_RECOGNITION)).allowed)

    async def test_the_same_ref_is_idempotent(self):
        # Sahifa qayta yuklanishi yoki tarmoq retry ikkinchi slotni yemasin.
        await self._seed()
        config = _config_with(EntitlementState.FREE, A.PRACTICE_RECOGNITION, 2)

        async with self.sessions() as session:
            user = await self._get_user(session)
            engine = EntitlementEngine(session, config=config)

            first = await engine.consume(user, A.PRACTICE_RECOGNITION, ref="abc")
            again = await engine.consume(user, A.PRACTICE_RECOGNITION, ref="abc")
            other = await engine.consume(user, A.PRACTICE_RECOGNITION, ref="xyz")
            third = await engine.consume(user, A.PRACTICE_RECOGNITION, ref="zzz")

        self.assertTrue(first.allowed)
        self.assertTrue(again.allowed)
        self.assertTrue(again.idempotent)
        self.assertTrue(other.allowed)
        self.assertFalse(third.allowed)

    # --- eski hisob bilan umumiylik ---------------------------------------

    async def test_the_engine_reads_the_same_rows_the_legacy_path_writes(self):
        # Eski yo'l bitta slotni yozadi; dvigatel uni KO'RISHI shart.
        await self._seed()
        config = _config_with(EntitlementState.FREE, A.PRACTICE_RECOGNITION, 2)

        async with self.sessions() as session:
            user = await self._get_user(session)
            legacy = CourseMiniAppAccessService(session)
            spent = await legacy.consume_daily_use(user, feature_key="recognition")
            self.assertTrue(spent["allowed"])
            await session.commit()

            decision = await EntitlementEngine(session, config=config).check(
                user, A.PRACTICE_RECOGNITION
            )

        self.assertEqual(1, decision.used)
        self.assertEqual(1, decision.remaining)

    async def test_the_legacy_path_sees_what_the_engine_writes(self):
        # Teskari yo'nalish: ko'chirish paytida ikkala yo'l yonma-yon ishlaydi.
        await self._seed()
        config = _config_with(EntitlementState.FREE, A.PRACTICE_MEMORIZE, 3)

        async with self.sessions() as session:
            user = await self._get_user(session)
            await EntitlementEngine(session, config=config).consume(
                user, A.PRACTICE_MEMORIZE
            )
            await session.commit()

            status = await CourseMiniAppAccessService(session).daily_status(
                user, "memorize"
            )

        self.assertEqual(1, status["used"])

    async def test_a_spent_lifetime_slot_is_never_reopened(self):
        # `course_feature_usages` da sarflangan umrbod slot dvigatelda ham
        # sarflangan bo'lib qolishi kerak — bu ikki jadval o'rtasidagi ko'prik.
        await self._seed()
        config = _config_with(
            EntitlementState.FREE, A.LESSON_START, 1, window="lifetime"
        )

        async with self.sessions() as session:
            user = await self._get_user(session)
            session.add(
                CourseFeatureUsage(user_id=user.id, feature_key="lesson", usage_ref="old")
            )
            await session.commit()

            decision = await EntitlementEngine(session, config=config).check(
                user, A.LESSON_START
            )

        self.assertEqual(1, decision.used)
        self.assertFalse(decision.allowed)

    async def test_the_legacy_trial_column_still_counts_as_a_spent_lesson(self):
        # Eski bot triali `trial_course_completed_at` bilan belgilangan edi.
        await self._seed(trial_course_completed_at=datetime.now(timezone.utc))
        config = _config_with(
            EntitlementState.FREE, A.LESSON_START, 1, window="lifetime"
        )

        async with self.sessions() as session:
            user = await self._get_user(session)
            decision = await EntitlementEngine(session, config=config).check(
                user, A.LESSON_START
            )

        self.assertFalse(decision.allowed)

    # --- holatlar ---------------------------------------------------------

    async def test_a_paid_user_is_unlimited_and_nothing_is_written(self):
        await self._seed(
            status="active",
            payment_status="approved",
            end_date=datetime.now(timezone.utc) + timedelta(days=10),
        )

        async with self.sessions() as session:
            user = await self._get_user(session)
            engine = EntitlementEngine(session, config=default_config())

            for _ in range(5):
                decision = await engine.consume(user, A.PRACTICE_RECOGNITION)
                self.assertTrue(decision.allowed)
                self.assertTrue(decision.unlimited)
                self.assertIsNone(decision.remaining)
            await session.commit()

            status = await CourseMiniAppAccessService(session).daily_status(
                user, "recognition"
            )

        self.assertEqual(EntitlementState.PRO_ACTIVE, decision.state)
        self.assertEqual(0, status["used"])

    async def test_a_referral_temp_access_user_is_unlimited_too(self):
        # Bu aynan bugungi nomutanosiblik yopiladigan joy: Mini App bu odamga
        # ochiq, desktop yopiq edi. Endi bitta javob.
        await self._seed(status="active", end_date=datetime.now(timezone.utc) + timedelta(days=2))

        async with self.sessions() as session:
            user = await self._get_user(session)
            decision = await EntitlementEngine(session, config=default_config()).check(
                user, A.PRACTICE_RECOGNITION
            )

        self.assertEqual(EntitlementState.TEMP_ACCESS, decision.state)
        self.assertTrue(decision.allowed)
        self.assertTrue(decision.unlimited)

    async def test_a_trial_user_gets_the_trial_numbers_not_unlimited(self):
        await self._seed()

        async with self.sessions() as session:
            user = await self._get_user(session)
            # `pro_trial_*` ustunlari 4-bosqichda qo'shiladi. Bu yerda ular
            # oddiy Python atributi sifatida qo'yiladi — dvigatel migratsiyadan
            # OLDIN ham to'g'ri ishlashi kerakligini shu ko'rsatadi.
            user.pro_trial_ends_at = datetime.now(timezone.utc) + timedelta(days=5)
            decision = await EntitlementEngine(session, config=default_config()).check(
                user, A.PRACTICE_RECOGNITION
            )

        self.assertEqual(EntitlementState.TRIAL_ACTIVE, decision.state)
        self.assertTrue(decision.allowed)
        self.assertFalse(decision.unlimited)
        self.assertEqual(10, decision.limit)

    async def test_a_blocked_user_is_refused_without_a_checkout_offer(self):
        await self._seed(status="blocked")

        async with self.sessions() as session:
            user = await self._get_user(session)
            decision = await EntitlementEngine(session, config=default_config()).consume(
                user, A.PRACTICE_RECOGNITION
            )

        self.assertFalse(decision.allowed)
        self.assertEqual(D.REASON_BLOCKED, decision.reason)
        self.assertFalse(decision.paywall.checkout_allowed)

    # --- javob shakli -----------------------------------------------------

    async def test_a_refusal_always_carries_a_reset_time(self):
        # Bugun Android 403 da `reset_at` bor, Mini App da yo'q. Endi ikkalasi.
        await self._seed()
        config = _config_with(EntitlementState.FREE, A.PRACTICE_RECOGNITION, 1)

        async with self.sessions() as session:
            user = await self._get_user(session)
            engine = EntitlementEngine(session, config=config)
            await engine.consume(user, A.PRACTICE_RECOGNITION)
            decision = await engine.consume(user, A.PRACTICE_RECOGNITION)

        self.assertIsNotNone(decision.reset_at)
        payload = decision.as_dict(is_paid=False)
        self.assertEqual(D.LEGACY_LIMIT_ERROR, payload["error"])
        self.assertEqual("practice", payload["paywall"]["surface"])
        self.assertFalse(payload["is_paid"])

    async def test_the_reset_time_follows_the_learner_timezone(self):
        await self._seed()
        config = _config_with(EntitlementState.FREE, A.PRACTICE_RECOGNITION, 1)

        async with self.sessions() as session:
            user = await self._get_user(session)
            session.add(
                CourseMiniAppProfile(user_id=user.id, timezone_offset_minutes=300)
            )
            await session.commit()

            engine = EntitlementEngine(session, config=config)
            await engine.consume(user, A.PRACTICE_RECOGNITION)
            decision = await engine.consume(user, A.PRACTICE_RECOGNITION)
            snapshot = await engine.snapshot(user)

        self.assertEqual(300, snapshot.offset_minutes)
        self.assertEqual(snapshot.reset_at.isoformat(), decision.reset_at)

    async def test_status_map_answers_many_actions_from_one_snapshot(self):
        await self._seed()

        async with self.sessions() as session:
            user = await self._get_user(session)
            statuses = await EntitlementEngine(session, config=default_config()).status_map(
                user, [A.LESSON_START, A.AI_TEXT, A.PRACTICE_RECOGNITION]
            )

        self.assertEqual(
            {A.LESSON_START, A.AI_TEXT, A.PRACTICE_RECOGNITION}, set(statuses)
        )
        self.assertEqual(2, statuses[A.LESSON_START].limit)
        self.assertEqual(5, statuses[A.AI_TEXT].limit)

    async def test_an_unknown_action_never_raises(self):
        await self._seed()

        async with self.sessions() as session:
            user = await self._get_user(session)
            decision = await EntitlementEngine(session, config=default_config()).check(
                user, "totally.made.up"
            )

        self.assertIsNotNone(decision)


class AiCounterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine_db = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.engine_db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine_db, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine_db.dispose()

    async def test_ai_text_reads_the_existing_questions_counter(self):
        # Bot AI matn hisobi `users.questions_used` da — dvigatel yangi
        # hisoblagich ochmasdan o'shani o'qiydi.
        async with self.sessions() as session:
            session.add(_user(questions_used=5))
            await session.commit()

            from sqlalchemy import select

            user = (
                await session.execute(select(User).where(User.telegram_id == 4100))
            ).scalar_one()
            decision = await EntitlementEngine(session, config=default_config()).check(
                user, A.AI_TEXT
            )

        self.assertEqual(5, decision.used)
        self.assertFalse(decision.allowed)
        self.assertEqual("ai", decision.paywall.surface)

    async def test_ai_voice_has_its_own_paywall_surface(self):
        async with self.sessions() as session:
            session.add(_user())
            await session.commit()

            from sqlalchemy import select

            user = (
                await session.execute(select(User).where(User.telegram_id == 4100))
            ).scalar_one()
            engine = EntitlementEngine(
                session, config=_config_with(EntitlementState.FREE, A.AI_VOICE, 0)
            )
            decision = await engine.check(user, A.AI_VOICE)

        self.assertFalse(decision.allowed)
        self.assertEqual("voice", decision.paywall.surface)


if __name__ == "__main__":
    unittest.main()

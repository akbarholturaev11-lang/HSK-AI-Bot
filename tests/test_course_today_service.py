"""«Bugungi reja» — haqiqiy baza ustida, kun barqarorligi bilan.

Eng muhim xossa: reja kuniga BIR MARTA quriladi va uning task identity'si
kun davomida o'zgarmaydi. Busiz ertalab ko'rilgan reja kechqurun boshqa
vazifalarga almashib qolardi, chunki `course_mistakes` upsert jadvali —
zaiflikning kun boshidagi holatini qayta tiklab bo'lmaydi.
"""

import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_mistake import CourseMistake
from app.db.models.user import User
from app.services.course_today_service import CourseTodayService
from app.services.daily_plan_service import (
    ACCESS_LOCKED,
    ACCESS_OPEN,
    TASK_CONTINUE_LESSON,
)


class FakePolicy:
    def __init__(self, requirement="open", free_active=False):
        self._requirement = requirement
        self.free_active = free_active

    def requirement_for(self, *, lesson_order, is_paid, free_lessons):
        return self._requirement


def learner() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=1,
        telegram_id=777,
        full_name="Today",
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
        daily_practice_streak=0,
        created_at=now,
        last_active_at=now,
    )


def mistake(key: str, category: str, weight: int) -> CourseMistake:
    now = datetime.now(timezone.utc)
    return CourseMistake(
        user_id=1,
        mistake_key=key,
        category=category,
        source="lesson",
        level="hsk1",
        prompt="p",
        correct_answer="a",
        wrong_count=weight,
        resolved_count=0,
        first_seen_at=now,
        last_seen_at=now,
    )


class CourseTodayServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.user = learner()
        self.profile = CourseMiniAppProfile(
            user_id=1, goal="hsk_exam", daily_minutes=20, start_mode="lesson_1",
            timezone_offset_minutes=0, current_streak=2,
        )
        self.progress = SimpleNamespace(completed_lessons_count=12, level="hsk1")
        async with self.factory() as session:
            session.add(self.user)
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _payload(self, *, is_paid=True, policy=None, voice_left=None):
        async with self.factory() as session:
            service = CourseTodayService(session)
            with patch(
                "app.services.course_today_service.VoicePracticeService",
                return_value=SimpleNamespace(
                    remaining_free_sessions=AsyncMock(return_value=voice_left)
                ),
            ):
                return await service.payload(
                    self.user,
                    profile=self.profile,
                    progress=self.progress,
                    level="hsk1",
                    is_paid=is_paid,
                    access_policy=policy or FakePolicy(),
                )

    async def _add(self, *rows):
        async with self.factory() as session:
            for row in rows:
                session.add(row)
            await session.commit()

    async def test_plan_is_built_and_frozen_on_the_profile(self):
        view = await self._payload()

        self.assertTrue(view["tasks"])
        self.assertEqual(view["tasks"][0]["type"], TASK_CONTINUE_LESSON)
        self.assertTrue(self.profile.daily_plan_key.startswith("v1:hsk1:"))
        stored = json.loads(self.profile.daily_plan_json)
        self.assertEqual(len(stored), view["total"])

    async def test_the_plan_does_not_change_when_weakness_changes_mid_day(self):
        # Kun davomida yangi xato paydo bo'lsa ham ERTALABGI reja qoladi.
        first = await self._payload()
        frozen = self.profile.daily_plan_json

        await self._add(
            mistake("m1", "character", 50),
            mistake("m2", "grammar", 40),
        )
        second = await self._payload()

        self.assertEqual(self.profile.daily_plan_json, frozen)
        self.assertEqual(
            [item["type"] for item in first["tasks"]],
            [item["type"] for item in second["tasks"]],
        )

    async def test_a_new_day_rebuilds_the_plan(self):
        await self._payload()
        self.profile.daily_plan_key = "v1:hsk1:2000-01-01"
        await self._add(mistake("m1", "character", 50))

        view = await self._payload()

        self.assertTrue(self.profile.daily_plan_key.startswith("v1:hsk1:"))
        self.assertNotEqual(self.profile.daily_plan_key, "v1:hsk1:2000-01-01")
        self.assertTrue(view["tasks"])

    async def test_a_band_change_rebuilds_the_plan(self):
        # Aks holda mavjud bo'lmagan qism raqamlari qolib ketardi.
        await self._payload()
        old_key = self.profile.daily_plan_key
        async with self.factory() as session:
            service = CourseTodayService(session)
            with patch(
                "app.services.course_today_service.VoicePracticeService",
                return_value=SimpleNamespace(remaining_free_sessions=AsyncMock(return_value=None)),
            ):
                await service.payload(
                    self.user, profile=self.profile, progress=self.progress,
                    level="hsk2", is_paid=True, access_policy=FakePolicy(),
                )

        self.assertNotEqual(self.profile.daily_plan_key, old_key)
        self.assertTrue(self.profile.daily_plan_key.startswith("v1:hsk2:"))

    async def test_progress_is_recomputed_even_though_identity_is_frozen(self):
        await self._payload()
        self.assertEqual((await self._payload())["done"], 0)

        self.progress.completed_lessons_count = 13
        view = await self._payload()

        self.assertEqual(view["tasks"][0]["done"], True)
        self.assertGreaterEqual(view["done"], 1)

    async def test_a_free_learner_without_voice_never_gets_a_voice_task(self):
        # Voice'da reklama yo'li YO'Q: limit tugasa faqat obuna, ya'ni
        # vazifani hozir boshlab bo'lmaydi.
        view = await self._payload(is_paid=False, voice_left=0)

        self.assertNotIn("voice_dialog", [item["type"] for item in view["tasks"]])

    async def test_a_locked_course_is_not_offered_as_a_task(self):
        view = await self._payload(
            is_paid=False, voice_left=0, policy=FakePolicy(requirement="subscription")
        )

        self.assertNotIn(TASK_CONTINUE_LESSON, [item["type"] for item in view["tasks"]])

    async def test_ad_supported_work_still_reaches_the_plan(self):
        view = await self._payload(
            is_paid=False, voice_left=1, policy=FakePolicy(requirement="ad")
        )

        lesson = next(
            item for item in view["tasks"] if item["type"] == TASK_CONTINUE_LESSON
        )
        self.assertEqual(lesson["access"], "ad")
        self.assertTrue(lesson["available"])

    async def test_paid_learner_sees_everything_open(self):
        view = await self._payload(is_paid=True, voice_left=None)
        self.assertTrue(all(item["access"] == ACCESS_OPEN for item in view["tasks"]))

    async def test_a_broken_plan_never_breaks_the_map(self):
        async with self.factory() as session:
            service = CourseTodayService(session)
            service.signals = SimpleNamespace(load=AsyncMock(side_effect=RuntimeError("boom")))
            view = await service.payload(
                self.user, profile=self.profile, progress=self.progress,
                level="hsk1", is_paid=True, access_policy=FakePolicy(),
            )

        self.assertIsNone(view)

    async def test_a_corrupt_stored_plan_is_rebuilt(self):
        await self._payload()
        self.profile.daily_plan_json = "{not json"

        view = await self._payload()

        self.assertTrue(view["tasks"])
        self.assertEqual(json.loads(self.profile.daily_plan_json)[0]["t"], TASK_CONTINUE_LESSON)


if __name__ == "__main__":
    unittest.main()

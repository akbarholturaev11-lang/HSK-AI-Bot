"""O'quv signallari — haqiqiy baza ustida.

Bu qatlam qaror qabul qilmaydi, lekin uning so'rovlari noto'g'ri bo'lsa reja
ham noto'g'ri bo'ladi, shuning uchun ular mock emas, HAQIQIY jadvallar
ustida tekshiriladi.
"""

import json
import unittest
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.course_mistake import CourseMistake
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.user import User
from app.services.learning_signals import LearningSignalsService





def learner() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=1,
        telegram_id=555,
        full_name="Signals",
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


def mistake(key: str, *, category: str, weight: int, material: dict | None = None) -> CourseMistake:
    now = datetime.now(timezone.utc)
    return CourseMistake(
        user_id=1,
        mistake_key=key,
        category=category,
        source="lesson",
        level="hsk1",
        prompt="p",
        correct_answer="a",
        material_json=json.dumps(material) if material else None,
        wrong_count=weight,
        resolved_count=0,
        first_seen_at=now,
        last_seen_at=now,
    )


def xp_event(activity_type: str, ref: str, day: date, xp: int = 20) -> CourseXpEvent:
    return CourseXpEvent(
        user_id=1,
        activity_type=activity_type,
        activity_ref=ref,
        xp=xp,
        activity_date=day,
        week_start=day - timedelta(days=day.weekday()),
    )


class LearningSignalsTests(unittest.IsolatedAsyncioTestCase):
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
        async with self.factory() as session:
            session.add(self.user)
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _add(self, *rows):
        async with self.factory() as session:
            for row in rows:
                session.add(row)
            await session.commit()

    async def _load(self, *, completed=12, minutes=20, focus=None, goal="hsk_exam"):
        profile = CourseMiniAppProfile(
            user_id=1, goal=goal, daily_minutes=minutes, start_mode="lesson_1",
            timezone_offset_minutes=0, preferred_focus=focus, current_streak=3,
        )
        progress = type("P", (), {"completed_lessons_count": completed, "level": "hsk1"})()
        async with self.factory() as session:
            service = LearningSignalsService(session)
            return await service.load(self.user, profile=profile, progress=progress, level="hsk1")

    async def test_listening_is_separated_without_a_schema_change(self):
        # `course_mistakes` da tinglash kategoriyasi YO'Q — u saqlangan
        # material formatidan chiqariladi.
        await self._add(
            mistake("a", category="word", weight=5, material={"format": "listening_choice"}),
            mistake("b", category="word", weight=3),
            mistake("c", category="grammar", weight=2),
        )
        signals = await self._load()

        self.assertEqual(signals.weakness["listening"], 5)
        self.assertEqual(signals.weakness["word"], 3)
        self.assertEqual(signals.weakness["grammar"], 2)

    async def test_resolved_mistakes_stop_counting(self):
        item = mistake("a", category="character", weight=4)
        item.resolved_count = 4
        await self._add(item, mistake("b", category="character", weight=2))
        signals = await self._load()

        self.assertEqual(signals.weakness["character"], 2)
        self.assertEqual(signals.mistakes_total, 2)

    async def test_only_todays_work_counts_towards_today(self):
        today = date.fromisoformat((await self._load()).local_day)
        await self._add(
            xp_event("lesson", "v3-part:hsk1:13:complete", today, xp=25),
            xp_event("training", "practice:1", today, xp=8),
            # Kechagi ish bugungi hisobga kirmasligi kerak.
            xp_event("voice", "v:1", today - timedelta(days=1), xp=10),
        )
        signals = await self._load()

        self.assertEqual(signals.done_types_today, frozenset({"lesson", "training"}))
        self.assertEqual(signals.today_xp, 33)
        self.assertIn("v3-part:hsk1:13:complete", signals.done_refs_today)

    async def test_gamification_rows_never_count_as_study_pace(self):
        # Sovg'a ochgan kun "o'qigan kun" bo'lib ko'rinmasligi kerak.
        today = date.fromisoformat((await self._load()).local_day)
        await self._add(
            xp_event("reward_chest", "chest:1", today),
            xp_event("challenge_win", "ch:1", today),
        )
        signals = await self._load()

        self.assertEqual(signals.evidence_count, 0)
        self.assertEqual(signals.active_days_7, 0)

    async def test_learning_rows_build_pace_and_evidence(self):
        today = date.fromisoformat((await self._load()).local_day)
        await self._add(
            xp_event("lesson", "l1", today),
            xp_event("lesson", "l2", today - timedelta(days=1)),
            xp_event("voice", "v1", today - timedelta(days=2)),
            xp_event("lesson", "old", today - timedelta(days=30)),
        )
        signals = await self._load()

        self.assertEqual(signals.evidence_count, 4)
        self.assertEqual(signals.active_days_7, 3)

    async def test_today_marks_done_types_for_the_plan(self):
        today = date.fromisoformat((await self._load()).local_day)
        await self._add(xp_event("mistake_review", "mr:1", today, xp=5))
        signals = await self._load()

        self.assertIn("mistake_review", signals.done_types_today)
        self.assertEqual(signals.today_xp, 5)

    async def test_prior_fades_as_evidence_grows(self):
        empty = await self._load(focus="listening")
        self.assertEqual(empty.prior_weight, 1.0)

        today = date.fromisoformat(empty.local_day)
        await self._add(*[xp_event("lesson", f"l{n}", today) for n in range(10)])
        experienced = await self._load(focus="listening")
        self.assertEqual(experienced.prior_weight, 0.0)

    async def test_no_stated_focus_means_no_prior(self):
        signals = await self._load(focus=None)
        self.assertEqual(signals.prior_weight, 0.0)
        none_focus = await self._load(focus="none")
        self.assertEqual(none_focus.prior_weight, 0.0)

    async def test_position_comes_from_progress_and_the_manifest(self):
        signals = await self._load(completed=12)
        self.assertEqual(signals.current_part, 13)
        self.assertEqual(signals.total_parts, 63)
        self.assertTrue(signals.has_next_part)

    async def test_plan_size_and_goal_come_from_the_profile(self):
        signals = await self._load(minutes=30, goal="travel")
        self.assertEqual(signals.plan_size, 4)
        self.assertEqual(signals.daily_goal_xp, 50)
        self.assertEqual(signals.goal, "travel")


if __name__ == "__main__":
    unittest.main()

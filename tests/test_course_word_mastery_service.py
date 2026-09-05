"""Interval takrori: so'z qachon qaytadi va mashq nimani beradi.

Haqiqiy baza ustida — tanlash so'rovlari va jadval qoidalari mock bilan
tekshirilsa ma'nosini yo'qotadi.
"""

import unittest
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.course_mistake import CourseMistake
from app.db.models.course_word_mastery import (
    WORD_MASTERY_INTERVALS,
    WORD_MASTERY_MAX_BOX,
    CourseWordMastery,
)
from app.db.models.user import User
from app.services.course_word_mastery_service import (
    REVIEW_SLOTS,
    CourseWordMasteryService,
    local_today,
)


def learner(user_id: int = 1) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
        telegram_id=4200 + user_id,
        full_name="Mastery",
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


def mistake(zh: str, *, source: str, weight: int) -> CourseMistake:
    now = datetime.now(timezone.utc)
    return CourseMistake(
        user_id=1,
        mistake_key=f"{source}:{zh}",
        category="character",
        source=source,
        level="hsk1",
        prompt="p",
        correct_answer=zh,
        wrong_count=weight,
        resolved_count=0,
        first_seen_at=now,
        last_seen_at=now,
    )


class MasteryTestCase(unittest.IsolatedAsyncioTestCase):
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
        self.today = local_today(0)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _add(self, *rows):
        async with self.factory() as session:
            for row in rows:
                session.add(row)
            await session.commit()

    async def _apply(self, results, *, skill="recognition", offset=0):
        async with self.factory() as session:
            service = CourseWordMasteryService(session)
            written = await service.apply_results(
                self.user, skill=skill, results=results, timezone_offset_minutes=offset
            )
            await session.commit()
            return written

    async def _rows(self, skill="recognition") -> dict[str, CourseWordMastery]:
        async with self.factory() as session:
            result = await session.execute(
                select(CourseWordMastery).where(CourseWordMastery.skill == skill)
            )
            return {row.zh: row for row in result.scalars().all()}

    async def _select(self, *, skill="recognition", level="hsk1", part=30, limit=10, offset=0):
        async with self.factory() as session:
            service = CourseWordMasteryService(session)
            return await service.select(
                self.user,
                skill=skill,
                level=level,
                current_part=part,
                limit=limit,
                timezone_offset_minutes=offset,
            )


class ScheduleTests(MasteryTestCase):
    async def test_first_correct_answer_schedules_the_word_for_tomorrow(self):
        await self._apply([{"hanzi": "你", "correct": True}])
        row = (await self._rows())["你"]

        self.assertEqual(row.box, 1)
        self.assertEqual(row.due_on, self.today + timedelta(days=1))
        self.assertEqual(row.correct_count, 1)
        self.assertEqual(row.wrong_count, 0)

    async def test_first_wrong_answer_brings_the_word_back_today(self):
        await self._apply([{"hanzi": "你", "correct": False}])
        row = (await self._rows())["你"]

        self.assertEqual(row.box, 0)
        self.assertEqual(row.due_on, self.today)
        self.assertEqual(row.wrong_count, 1)

    async def test_the_ladder_climbs_one_step_per_due_day(self):
        expected = [(1, 1), (2, 3), (3, 7), (4, 21)]
        for box, gap in expected:
            async with self.factory() as session:
                service = CourseWordMasteryService(session)
                rows = await service._all_rows(1, "recognition")
                row = rows.get("你")
                # Muddat kelgan kunni taqlid qilamiz: so'zni bugunga tortamiz,
                # aks holda kunlik clamp ko'tarilishga yo'l qo'ymaydi.
                if row:
                    row.due_on = self.today
                await service.apply_results(
                    self.user,
                    skill="recognition",
                    results=[{"hanzi": "你", "correct": True}],
                    timezone_offset_minutes=0,
                )
                await session.commit()
            row = (await self._rows())["你"]
            self.assertEqual(row.box, box)
            self.assertEqual((row.due_on - self.today).days, gap)

    async def test_the_last_box_repeats_and_the_word_never_disappears(self):
        await self._add(
            CourseWordMastery(
                user_id=1, skill="recognition", zh="你",
                box=WORD_MASTERY_MAX_BOX, due_on=self.today,
                correct_count=9, wrong_count=0,
                last_result_at=datetime.now(timezone.utc),
            )
        )
        await self._apply([{"hanzi": "你", "correct": True}])
        row = (await self._rows())["你"]

        self.assertEqual(row.box, WORD_MASTERY_MAX_BOX)
        self.assertEqual(
            row.due_on, self.today + timedelta(days=WORD_MASTERY_INTERVALS[-1])
        )

    async def test_only_one_promotion_per_day(self):
        # Aks holda bir kunda to'rt marta mashq qilib so'zni +21 kunga surib
        # yuborish mumkin bo'lardi — bu interval takrori emas.
        await self._apply([{"hanzi": "你", "correct": True}])
        await self._apply([{"hanzi": "你", "correct": True}])
        await self._apply([{"hanzi": "你", "correct": True}])
        row = (await self._rows())["你"]

        self.assertEqual(row.box, 1)
        self.assertEqual(row.due_on, self.today + timedelta(days=1))
        self.assertEqual(row.correct_count, 3)

    async def test_a_wrong_answer_resets_the_word_from_any_box(self):
        await self._add(
            CourseWordMastery(
                user_id=1, skill="recognition", zh="你",
                box=4, due_on=self.today + timedelta(days=21),
                correct_count=9, wrong_count=0,
                last_result_at=datetime.now(timezone.utc),
            )
        )
        await self._apply([{"hanzi": "你", "correct": False}])
        row = (await self._rows())["你"]

        self.assertEqual(row.box, 0)
        self.assertEqual(row.due_on, self.today)

    async def test_repeated_attempts_in_one_session_count_as_one_result(self):
        # Talaffuzda 3 urinish bitta xato natijasini beradi.
        await self._apply(
            [
                {"hanzi": "你", "correct": False},
                {"hanzi": "你", "correct": False},
                {"hanzi": "你", "correct": False},
            ]
        )
        row = (await self._rows())["你"]
        self.assertEqual(row.wrong_count, 1)

    async def test_a_word_failed_then_passed_still_counts_as_weak(self):
        await self._apply(
            [{"hanzi": "你", "correct": False}, {"hanzi": "你", "correct": True}]
        )
        row = (await self._rows())["你"]
        self.assertEqual(row.box, 0)
        self.assertEqual(row.due_on, self.today)

    async def test_skills_are_scheduled_independently(self):
        # Ieroglifni tanish va uni ayta olish — boshqa-boshqa ko'nikmalar.
        await self._apply([{"hanzi": "你", "correct": True}], skill="recognition")
        await self._apply([{"hanzi": "你", "correct": False}], skill="pronunciation")

        self.assertEqual((await self._rows("recognition"))["你"].box, 1)
        self.assertEqual((await self._rows("pronunciation"))["你"].box, 0)


class GuardTests(MasteryTestCase):
    async def test_a_forged_character_is_never_stored(self):
        written = await self._apply(
            [{"hanzi": "ZZZ"}, {"hanzi": "🙂"}, {"hanzi": ""}, {"hanzi": "李月"}]
        )
        self.assertEqual(written, 0)
        self.assertEqual(await self._rows(), {})

    async def test_an_unknown_skill_is_rejected(self):
        async with self.factory() as session:
            service = CourseWordMasteryService(session)
            with self.assertRaises(ValueError):
                await service.apply_results(self.user, skill="dancing", results=[])

    async def test_an_empty_report_writes_nothing(self):
        self.assertEqual(await self._apply([]), 0)

    async def test_timezone_offsets_are_respected(self):
        for offset in (-720, 0, 840):
            self.assertIsInstance(local_today(offset), date)
        await self._apply([{"hanzi": "你", "correct": True}], offset=840)
        row = (await self._rows())["你"]
        self.assertEqual(row.due_on, local_today(840) + timedelta(days=1))


class SelectionTests(MasteryTestCase):
    async def test_a_fresh_learner_gets_only_new_words(self):
        words = await self._select()
        self.assertEqual(len(words), 10)
        self.assertTrue(all(item["kind"] == "new" for item in words))

    async def test_cold_start_widens_instead_of_returning_three_words(self):
        # HSK1 ning 1-qismida atigi 3 ta so'z bor.
        words = await self._select(part=1)
        self.assertGreaterEqual(len(words), 8)

    async def test_due_words_come_back_and_are_marked_as_review(self):
        await self._add(
            CourseWordMastery(
                user_id=1, skill="recognition", zh="你",
                box=0, due_on=self.today - timedelta(days=1),
                correct_count=0, wrong_count=2,
                last_result_at=datetime.now(timezone.utc),
            )
        )
        words = await self._select()
        review = [item for item in words if item["kind"] == "review"]

        self.assertEqual([item["zh"] for item in review], ["你"])
        self.assertEqual(words[0]["zh"], "你")

    async def test_a_word_that_is_not_due_yet_is_not_offered(self):
        await self._add(
            CourseWordMastery(
                user_id=1, skill="recognition", zh="你",
                box=3, due_on=self.today + timedelta(days=7),
                correct_count=5, wrong_count=0,
                last_result_at=datetime.now(timezone.utc),
            )
        )
        words = await self._select()
        self.assertNotIn("你", [item["zh"] for item in words if item["kind"] == "review"])

    async def test_reviews_are_capped_and_spread_through_the_drill(self):
        due = []
        for zh in ("你", "好", "您", "我", "是", "叫"):
            due.append(
                CourseWordMastery(
                    user_id=1, skill="recognition", zh=zh,
                    box=0, due_on=self.today - timedelta(days=1),
                    correct_count=0, wrong_count=1,
                    last_result_at=datetime.now(timezone.utc),
                )
            )
        await self._add(*due)
        words = await self._select()
        kinds = [item["kind"] for item in words]

        self.assertEqual(kinds.count("review"), REVIEW_SLOTS)
        # Takrorlar boshiga to'planib qolmasin.
        self.assertNotEqual(kinds[:REVIEW_SLOTS], ["review"] * REVIEW_SLOTS)

    async def test_old_mistakes_seed_the_first_review_before_any_mastery_exists(self):
        await self._add(
            mistake("好", source="recognition", weight=5),
            mistake("你", source="pronunciation", weight=2),
            # Bu manba ishonchsiz — `correct_answer` variant matni bo'lishi mumkin.
            mistake("是", source="training", weight=99),
        )
        words = await self._select()
        reviews = [item["zh"] for item in words if item["kind"] == "review"]

        self.assertIn("好", reviews)
        self.assertNotIn("是", reviews)

    async def test_selection_is_deterministic(self):
        first = await self._select()
        second = await self._select()
        self.assertEqual(first, second)

    async def test_finishing_a_drill_moves_the_next_one_forward(self):
        first = await self._select()
        await self._apply([{"hanzi": item["zh"], "correct": True} for item in first])
        second = await self._select()

        self.assertNotEqual([item["zh"] for item in first], [item["zh"] for item in second])

    async def test_recognition_only_offers_single_characters(self):
        for item in await self._select(skill="recognition", part=60):
            self.assertEqual(len(item["zh"]), 1, item["zh"])

    async def test_pronunciation_may_offer_longer_words(self):
        words = await self._select(skill="pronunciation", part=60)
        self.assertTrue(any(len(item["zh"]) > 1 for item in words))

    async def test_mastery_survives_a_band_change(self):
        # Band almashganda progress nolga tushadi, lekin o'quvchi hsk1
        # so'zlarini unutmaydi — takror qatorlari saqlanib qolishi kerak.
        await self._add(
            CourseWordMastery(
                user_id=1, skill="recognition", zh="你",
                box=0, due_on=self.today - timedelta(days=2),
                correct_count=0, wrong_count=3,
                last_result_at=datetime.now(timezone.utc),
            )
        )
        words = await self._select(level="hsk2", part=1)
        reviews = [item["zh"] for item in words if item["kind"] == "review"]

        self.assertIn("你", reviews)

    async def test_a_short_limit_is_respected(self):
        self.assertEqual(len(await self._select(limit=3)), 3)


if __name__ == "__main__":
    unittest.main()

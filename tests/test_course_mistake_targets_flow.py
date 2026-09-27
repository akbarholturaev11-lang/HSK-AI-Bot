"""Universal Xatolarim takrori (v3): haqiqiy baza bilan to'liq oqim.

Xato yoziladi -> nishonga bog'lanadi -> takror har nishonni 3 xil mashqda
beradi -> uchalasi to'g'ri bo'lsa nishon yopiladi va xato qatorlari
`resolved` bo'ladi. Xato javob progressni nolga tushiradi.
"""

import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.course_mistake import CourseMistake
from app.db.models.course_mistake_target import CourseMistakeTarget
from app.db.models.user import User
from app.services import mistake_drill_factory as drills
from app.services.course_lesson_mistake_material_service import CourseLessonMistakeMaterialService
from app.services.course_mistake_service import CourseMistakeService


ALL_FORMATS = sorted(drills.ALL_FORMATS)


def learner() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=1,
        telegram_id=777,
        full_name="Learner",
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
    )


def lesson_items(*refs_and_choice):
    return CourseLessonMistakeMaterialService.canonicalize_items(
        level="hsk1",
        lesson_order=1,
        lang="uz",
        items=[{"material_ref": ref, "selected_index": index} for ref, index in refs_and_choice],
    )


class MistakeTargetsFlowTests(unittest.IsolatedAsyncioTestCase):
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
        self.ref_counter = 0

    async def asyncTearDown(self):
        await self.engine.dispose()

    def service(self, session) -> CourseMistakeService:
        service = CourseMistakeService(session)
        service.access = SimpleNamespace(
            normalize_access_ref=lambda value: value,
            consume_free_use=AsyncMock(return_value={"allowed": True}),
            verify_ad_authorization=AsyncMock(return_value={"allowed": True}),
        )
        service.gamification = SimpleNamespace(
            award=AsyncMock(return_value={"awarded_xp": 5, "duplicate": False})
        )
        return service

    async def record(self, items, *, source="lesson"):
        async with self.factory() as session:
            user = await session.get(User, 1)
            recorded = await self.service(session).record_items(
                user, items, source=source, level="hsk1", lesson_order=1
            )
            await session.commit()
            return recorded

    async def start(self, *, category=None, formats=ALL_FORMATS, language="uz"):
        self.ref_counter += 1
        async with self.factory() as session:
            return await self.service(session).start_review(
                777,
                access_ref=f"review-ref-{self.ref_counter:04d}",
                category=category,
                formats=formats,
                language=language,
            )

    async def answer_all(self, session_payload, *, correct=True, wrong_ids=()):
        """Har savolga javob beradi (to'g'ri javobni snapshot'dan oladi)."""
        async with self.factory() as session:
            from app.db.models.course_miniapp_event import CourseMiniAppEvent

            started = (
                await session.execute(
                    select(CourseMiniAppEvent).where(
                        CourseMiniAppEvent.event_name == "mistake_review_started",
                        CourseMiniAppEvent.session_id == session_payload["id"],
                    )
                )
            ).scalar_one()
            snapshot = {
                question["id"]: question
                for question in json.loads(started.payload_json)["questions"]
            }
        results = []
        for public in session_payload["questions"]:
            stored = snapshot[public["id"]]
            right = correct and public["id"] not in wrong_ids
            if stored.get("tokens"):
                answer = list(stored["answer_tokens"]) if right else list(reversed(stored["answer_tokens"]))
            else:
                answer = stored["answer_index"] if right else (stored["answer_index"] + 1) % len(stored["options"])
            async with self.factory() as session:
                results.append(
                    await self.service(session).answer_review_question(
                        777,
                        session_id=session_payload["id"],
                        question_id=public["id"],
                        selected_index=answer,
                    )
                )
        async with self.factory() as session:
            completed = await self.service(session).complete_review(
                777, session_id=session_payload["id"], answers=[]
            )
        return results, completed

    async def targets(self):
        async with self.factory() as session:
            return list((await session.execute(select(CourseMistakeTarget))).scalars().all())

    async def mistakes(self):
        async with self.factory() as session:
            return list((await session.execute(select(CourseMistake))).scalars().all())

    # ------------------------------------------------------------------

    async def test_lesson_mistake_becomes_word_target_with_three_distinct_drills(self):
        # meaning_guess kartasi (你) — noto'g'ri variant tanlandi.
        await self.record(lesson_items(("lesson:hsk1:1:section:1:card:3", 0)))
        targets = await self.targets()
        self.assertEqual(len(targets), 1)
        self.assertEqual((targets[0].kind, targets[0].zh), ("word", "你"))

        started = await self.start()
        self.assertTrue(started["ok"], started)
        questions = started["session"]["questions"]
        self.assertEqual(len(questions), 3)
        self.assertEqual(len({question["format"] for question in questions}), 3)
        for question in questions:
            self.assertNotIn("answer_index", question)
            self.assertNotIn("answer_tokens", question)
            self.assertNotIn("explanation", question)
            if question["format"] in drills.LISTEN_FORMATS:
                self.assertTrue(question["audio_text"])
                self.assertTrue(question["autoplay"])
                self.assertEqual(question["sentence"], "")

        results, completed = await self.answer_all(started["session"])
        self.assertTrue(all(result["correct"] for result in results))
        self.assertTrue(completed["ok"], completed)
        self.assertEqual((completed["score"], completed["total"]), (3, 3))
        self.assertEqual(completed["cleared"], 1)
        self.assertEqual(completed["remaining"], 0)

        [target] = await self.targets()
        self.assertEqual(target.status, "cleared")
        [row] = await self.mistakes()
        self.assertEqual(row.resolved_count, row.wrong_count)

    async def test_one_wrong_answer_resets_progress_and_keeps_target_active(self):
        await self.record(lesson_items(("lesson:hsk1:1:section:1:card:3", 0)))
        started = await self.start()
        last_id = started["session"]["questions"][-1]["id"]
        _, completed = await self.answer_all(started["session"], wrong_ids={last_id})
        self.assertEqual(completed["cleared"], 0)
        self.assertEqual(completed["remaining"], 1)
        [target] = await self.targets()
        self.assertEqual(target.status, "active")
        self.assertEqual(target.passed_formats, "")
        [row] = await self.mistakes()
        self.assertLess(row.resolved_count, row.wrong_count)

        # Keyingi sessiya: yana 3 xil mashq, uchalasi to'g'ri -> yopiladi.
        again = await self.start()
        _, completed = await self.answer_all(again["session"])
        self.assertEqual(completed["cleared"], 1)

    async def test_voice_mistake_never_shows_the_prompt_as_an_option(self):
        await self.record(
            [
                {
                    "question": "我是学生吗",
                    "selected_answer": "我是学生吗",
                    "correct_answer": "我是学生。",
                    "explanation": "我是学生。",
                    "category": "grammar",
                }
            ],
            source="voice",
        )
        [target] = await self.targets()
        self.assertEqual(target.kind, "sentence")
        self.assertEqual(target.zh, "我是学生。")

        started = await self.start(category="grammar")
        self.assertTrue(started["ok"], started)
        formats = {question["format"] for question in started["session"]["questions"]}
        self.assertIn("correct_choice", formats)
        self.assertGreaterEqual(len(formats), 3)
        for question in started["session"]["questions"]:
            options = question.get("options") or []
            self.assertNotIn(question["prompt"], options)
            if question["format"] == "correct_choice":
                self.assertIn("我是学生吗", options)

    async def test_legacy_client_gets_only_choice_questions(self):
        await self.record(
            [
                {
                    "question": "我是学生吗",
                    "selected_answer": "我是学生吗",
                    "correct_answer": "我是学生。",
                    "category": "grammar",
                }
            ],
            source="voice",
        )
        started = await self.start(formats=None)
        self.assertTrue(started["ok"], started)
        for question in started["session"]["questions"]:
            self.assertIn(question["format"], drills.CHOICE_FORMATS)
            self.assertGreaterEqual(len(question["options"]), 2)

    async def test_category_scope_only_reviews_that_category(self):
        await self.record(lesson_items(("lesson:hsk1:1:section:1:card:3", 0)))
        await self.record(
            [{"question": "我是学生吗", "selected_answer": "我是学生吗", "correct_answer": "我是学生。", "category": "grammar"}],
            source="voice",
        )
        grammar = await self.start(category="grammar")
        self.assertEqual({q["category"] for q in grammar["session"]["questions"]}, {"grammar"})
        words = await self.start(category="word")
        self.assertEqual({q["category"] for q in words["session"]["questions"]}, {"word"})
        empty = await self.start(category="pronunciation")
        self.assertEqual(empty, {"ok": False, "error": "mistake_review_empty", "category": "pronunciation"})

    async def test_new_mistake_reopens_a_cleared_target(self):
        await self.record(lesson_items(("lesson:hsk1:1:section:1:card:3", 0)))
        started = await self.start()
        await self.answer_all(started["session"])
        [target] = await self.targets()
        self.assertEqual(target.status, "cleared")

        await self.record(lesson_items(("lesson:hsk1:1:section:1:card:3", 1)))
        [target] = await self.targets()
        self.assertEqual(target.status, "active")
        self.assertEqual(target.passed_formats, "")

    async def test_legacy_rows_without_target_are_backfilled_lazily(self):
        now = datetime.now(timezone.utc)
        async with self.factory() as session:
            session.add_all(
                [
                    # Eski dars oqimi: materialsiz tinglash savoli.
                    CourseMistake(
                        user_id=1, mistake_key="legacy-1", category="word", source="lesson",
                        level="hsk1", prompt="Tinglang va javobni tanlang", user_answer="好",
                        correct_answer="你", wrong_count=2, resolved_count=0,
                        first_seen_at=now, last_seen_at=now,
                    ),
                    # Hech narsa ajratib bo'lmaydigan yozuv: ovozi saqlanmagan
                    # tinglash savoli, javobi lug'atda yo'q ism.
                    CourseMistake(
                        user_id=1, mistake_key="legacy-2", category="word", source="lesson",
                        level="hsk1", prompt="Tinglang — qaysi so'z?", user_answer="Li Yue (ism)",
                        correct_answer="Xie Peng (ism)", wrong_count=1, resolved_count=0,
                        first_seen_at=now, last_seen_at=now,
                    ),
                ]
            )
            await session.commit()

        async with self.factory() as session:
            overview = await self.service(session).overview(777, view="targets", language="uz")
        self.assertTrue(overview["ok"])
        self.assertEqual(overview["summary"]["total"], 1)
        [item] = overview["targets"]
        self.assertEqual((item["kind"], item["zh"], item["pinyin"]), ("word", "你", "nǐ"))
        self.assertEqual(item["meaning"], "sen (birlik)")
        self.assertEqual((item["passed"], item["required"]), (0, 3))
        self.assertEqual(item["wrong"], "好")

        rows = {row.mistake_key: row for row in await self.mistakes()}
        self.assertEqual(rows["legacy-2"].target_key, "-")
        self.assertTrue(rows["legacy-1"].target_key)

    async def test_start_retry_returns_the_same_v3_session(self):
        await self.record(lesson_items(("lesson:hsk1:1:section:1:card:3", 0)))
        async with self.factory() as session:
            first = await self.service(session).start_review(777, access_ref="same-ref-000001", formats=ALL_FORMATS)
        async with self.factory() as session:
            second = await self.service(session).start_review(777, access_ref="same-ref-000001", formats=ALL_FORMATS)
        self.assertTrue(second["duplicate"])
        self.assertEqual(first["session"]["questions"], second["session"]["questions"])

    async def test_many_targets_are_interleaved(self):
        items = lesson_items(
            ("lesson:hsk1:1:section:1:card:3", 0),
            ("lesson:hsk1:1:section:1:card:4", 0),
            ("lesson:hsk1:1:section:1:card:5", 0),
        )
        await self.record(items)
        started = await self.start()
        questions = started["session"]["questions"]
        self.assertGreaterEqual(started["session"]["targets"], 2)
        for first, second in zip(questions, questions[1:]):
            self.assertNotEqual(first["id"].split(":")[1], second["id"].split(":")[1])


if __name__ == "__main__":
    unittest.main()

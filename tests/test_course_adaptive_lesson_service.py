"""Dars ichidagi shaxsiy takror (UIUX-007): qoidalar, oqim va xavfsizlik.

Asosiy kafolatlar:
- faqat serverda tekshirilgan xato, ko'nikma alohida;
- 3 (qiyin bo'lsa 4) mustaqil kun, bir kunda takror progress bermaydi;
- Xatolarim yopgan nishon >=3 kundan keyin bitta yakuniy tekshiruv oladi;
- adaptive javob dars natijasi/XP/progress/streak ga TEGMAYDI (ON/OFF teng).
"""

import asyncio
import json
import os
import unittest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.course_adaptive_plan import CourseAdaptivePlan
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_mistake_target import CourseMistakeTarget
from app.db.models.course_progress import CourseProgress
from app.db.models.course_word_mastery import CourseWordMastery
from app.db.models.user import User
from app.services import course_adaptive_lesson_service as adaptive
from app.services import mistake_drill_factory as drills
from app.services.course_adaptive_lesson_service import (
    AdaptiveRequestError,
    CourseAdaptiveLessonService,
)
from app.services.course_adaptive_schedule import final_check_due_on
from app.services.course_lesson_mistake_material_service import CourseLessonMistakeMaterialService
from app.services.course_mistake_service import CourseMistakeService
from app.services.course_question_material import canonicalize_hsk_exam_material


ALL_FORMATS = sorted(drills.ALL_FORMATS)
WORD_CARD = "lesson:hsk1:1:section:1:card:3"  # meaning_guess, 你
HIDDEN = {"answer_index", "answer_tokens", "correct_answer", "explanation", "target_id"}
# Faqat shu jadvallar shaxsiy takror holati: qolgan hamma narsa (progress,
# urinish, XP, streak, foydalanuvchi, xato dalillari) o'zgarmasligi shart.
PERSONAL_TABLES = {
    "course_adaptive_plans",
    "course_mistake_targets",
    "course_miniapp_events",
    "course_word_mastery",
}


def settings(**overrides):
    values = {
        "COURSE_ADAPTIVE_ENABLED": True,
        "COURSE_ADAPTIVE_ROLLOUT_PERCENT": 100,
        "COURSE_ADAPTIVE_ALLOWLIST": "",
        "COURSE_ADAPTIVE_SHADOW_ENABLED": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def learner(user_id=1, telegram_id=777, level="hsk1") -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
        telegram_id=telegram_id,
        full_name="Learner",
        language="uz",
        level=level,
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


def lesson_items(*refs_and_choice, lesson_order=1):
    return CourseLessonMistakeMaterialService.canonicalize_items(
        level="hsk1",
        lesson_order=lesson_order,
        lang="uz",
        items=[{"material_ref": ref, "selected_index": index} for ref, index in refs_and_choice],
    )


# ------------------------------------------------------------ pure rules ---

class AdaptiveRuleTests(unittest.TestCase):
    D0 = date(2026, 11, 2)

    def fresh(self, need=3):
        return {
            "v": adaptive.ADAPTIVE_STATE_VERSION,
            "skills": {"meaning": adaptive.new_skill(self.D0, need=need, evidence_at="2026-11-01T10:00:00+00:00")},
        }

    def answer(self, state, day, correct, kind="review"):
        return adaptive.apply_answer(
            state, skill="meaning", kind=kind, correct=correct, today=day,
            evidence_at=f"{day.isoformat()}T12:00:00+00:00",
        )

    def test_skill_comes_from_the_verified_question_format(self):
        self.assertEqual(adaptive.skill_for("meaning_guess", "word"), "meaning")
        self.assertEqual(adaptive.skill_for("hanzi_choice", "word"), "hanzi")
        self.assertEqual(adaptive.skill_for("pinyin_choice", "word"), "pinyin")
        self.assertEqual(adaptive.skill_for("listening_choice", "word"), "listening")
        self.assertEqual(adaptive.skill_for("sentence_builder", "grammar"), "grammar")
        # Formatsiz eski qator — kategoriya bo'yicha.
        self.assertEqual(adaptive.skill_for(None, "character"), "hanzi")
        self.assertEqual(adaptive.skill_for("", "pronunciation"), "pinyin")
        self.assertEqual(adaptive.skill_for("unknown", "word"), "meaning")

    def test_three_independent_days_retire_an_ordinary_mistake(self):
        state = self.fresh()
        day1 = self.D0 + timedelta(days=1)
        day4 = self.D0 + timedelta(days=4)
        self.assertTrue(self.answer(state, self.D0, True)["counted"])
        self.assertEqual(state["skills"]["meaning"]["due"], day1.isoformat())
        self.assertTrue(self.answer(state, day1, True)["counted"])
        self.assertEqual(state["skills"]["meaning"]["due"], day4.isoformat())
        result = self.answer(state, day4, True)
        self.assertTrue(result["counted"])
        self.assertTrue(result["retired"])
        skill = state["skills"]["meaning"]
        self.assertEqual(skill["phase"], "retired")
        # Uzoq muddatli SRS da qoladi (7 kun).
        self.assertEqual(skill["due"], (day4 + timedelta(days=7)).isoformat())

    def test_same_day_repeats_never_add_progress(self):
        state = self.fresh()
        self.assertTrue(self.answer(state, self.D0, True)["counted"])
        repeat = self.answer(state, self.D0, True)
        self.assertFalse(repeat["counted"])
        self.assertEqual(state["skills"]["meaning"]["ok_days"], [self.D0.isoformat()])

    def test_early_correct_answer_before_due_does_not_count(self):
        state = self.fresh()
        self.answer(state, self.D0, True)  # due -> D0+1
        early = self.D0 + timedelta(days=1)
        state["skills"]["meaning"]["due"] = (self.D0 + timedelta(days=3)).isoformat()
        self.assertFalse(self.answer(state, early, True)["counted"])
        self.assertEqual(len(state["skills"]["meaning"]["ok_days"]), 1)

    def test_wrong_answer_restarts_the_cycle_and_requires_four_days(self):
        state = self.fresh()
        self.answer(state, self.D0, True)
        day1 = self.D0 + timedelta(days=1)
        result = self.answer(state, day1, False)
        self.assertTrue(result["relearned"])
        skill = state["skills"]["meaning"]
        self.assertEqual((skill["phase"], skill["box"], skill["ok_days"], skill["need"]), ("active", 0, [], 4))
        self.assertEqual(skill["due"], day1.isoformat())
        # 4 ta mustaqil kun kerak; 3 tasi yetmaydi.
        days = [day1 + timedelta(days=offset) for offset in (1, 2, 5)]
        for day in days:
            self.assertFalse(self.answer(state, day, True)["retired"])
        self.assertTrue(self.answer(state, day1 + timedelta(days=12), True)["retired"])

    def test_repeated_mistake_is_difficult_from_the_start(self):
        self.assertEqual(adaptive.required_days(1), 3)
        self.assertEqual(adaptive.required_days(2), 4)

    def test_new_verified_evidence_restarts_only_that_skill(self):
        seen = datetime(2026, 11, 1, 10, tzinfo=timezone.utc)
        state = {"v": 1, "skills": {}}
        adaptive.derive_skills(
            state,
            {"meaning": {"wrong": 1, "seen_at": seen}, "listening": {"wrong": 1, "seen_at": seen}},
            category="word", fallback_seen_at=None, today=self.D0,
        )
        state["skills"]["meaning"].update(ok_days=["2026-11-02"], box=2)
        state["skills"]["listening"].update(ok_days=["2026-11-02"], box=2)
        later = seen + timedelta(days=3)
        changed = adaptive.derive_skills(
            state,
            {"meaning": {"wrong": 1, "seen_at": later}, "listening": {"wrong": 1, "seen_at": seen}},
            category="word", fallback_seen_at=None, today=self.D0 + timedelta(days=3),
        )
        self.assertTrue(changed)
        self.assertEqual(state["skills"]["meaning"]["ok_days"], [])
        self.assertEqual(state["skills"]["listening"]["ok_days"], ["2026-11-02"])

    def test_final_check_retires_every_skill_and_records_the_clear(self):
        state = self.fresh()
        state["skills"]["hanzi"] = adaptive.new_skill(self.D0, need=3, evidence_at="x")
        result = adaptive.apply_answer(
            state, skill="meaning", kind="final_check", correct=True, today=self.D0,
            evidence_at="y", clear_at="2026-10-29T08:00:00+00:00",
        )
        self.assertTrue(result["retired"])
        self.assertEqual({skill["phase"] for skill in state["skills"].values()}, {"retired"})
        self.assertEqual(state["final"], {"clear_at": "2026-10-29T08:00:00+00:00", "status": "passed"})

    def test_state_loader_drops_unknown_versions_and_skills(self):
        self.assertEqual(adaptive.load_state('{"v": 99, "skills": {"meaning": {}}}'), {"v": 1, "skills": {}})
        self.assertEqual(adaptive.load_state("not json"), {"v": 1, "skills": {}})
        state = adaptive.load_state('{"v": 1, "skills": {"meaning": {"box": 1}, "evil": {}}}')
        self.assertEqual(list(state["skills"]), ["meaning"])

    def test_placement_is_even_and_bounded(self):
        self.assertEqual(adaptive.placement_slots([2, 3, 4, 5, 6, 7, 8], 3), [3, 5, 7])
        self.assertEqual(adaptive.placement_slots([4, 9], 3), [4, 9])
        self.assertEqual(adaptive.placement_slots([], 2), [])
        self.assertEqual(adaptive.placement_slots([5], 0), [])

    def test_rollout_bucket_is_stable(self):
        self.assertEqual(adaptive.rollout_bucket(42), adaptive.rollout_bucket(42))
        self.assertTrue(0 <= adaptive.rollout_bucket(7) < 100)

    def test_grading_rejects_malformed_answers(self):
        choice = {"options": ["a", "b", "c"], "answer_index": 1, "explanation": "e"}
        self.assertEqual(adaptive._grade(choice, 1)[0], True)
        self.assertEqual(adaptive._grade(choice, 2)[0], False)
        for bad in (3, -1, True, "1x", ["a"]):
            self.assertIsNone(adaptive._grade(choice, bad), bad)
        builder = {"tokens": ["我", "是", "学生"], "answer_tokens": ["我", "是", "学生"], "correct_answer": "我是学生"}
        self.assertTrue(adaptive._grade(builder, ["我", "是", "学生"])[0])
        self.assertFalse(adaptive._grade(builder, ["是", "我", "学生"])[0])
        self.assertIsNone(adaptive._grade(builder, ["我", "是"]))
        self.assertIsNone(adaptive._grade(builder, ["我", "是", "老师"]))
        self.assertIsNone(adaptive._grade(builder, 0))


# --------------------------------------------------------- service flow ---

class AdaptiveLessonFlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Ixtiyoriy real PostgreSQL (FOR UPDATE, DATE/TIMESTAMPTZ): bo'sh,
        # faqat shu modul uchun yaratilgan baza nomi `_adaptive_test` bilan tugashi shart.
        url = os.environ.get("COURSE_ADAPTIVE_TEST_DATABASE_URL", "")
        self.real_pg = bool(url)
        if url:
            if not url.rsplit("/", 1)[-1].endswith("_adaptive_test"):
                self.skipTest("COURSE_ADAPTIVE_TEST_DATABASE_URL must name a *_adaptive_test database")
            self.engine = create_async_engine(url)
        else:
            self.engine = create_async_engine(
                "sqlite+aiosqlite:///:memory:",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        async with self.engine.begin() as connection:
            if url:
                await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.factory() as session:
            session.add_all([learner(1, 777), learner(2, 888)])
            await session.flush()
            session.add_all([
                CourseProgress(user_id=1, level="hsk1", completed_lessons_count=5),
                CourseProgress(user_id=2, level="hsk1", completed_lessons_count=5),
            ])
            await session.commit()
        self.settings = settings()
        self.today = date(2026, 11, 2)

    async def asyncTearDown(self):
        await self.engine.dispose()

    def mistakes(self, session) -> CourseMistakeService:
        service = CourseMistakeService(session)
        service.access = SimpleNamespace(
            normalize_access_ref=lambda value: value,
            consume_free_use=AsyncMock(return_value={"allowed": True}),
            verify_ad_authorization=AsyncMock(return_value={"allowed": True}),
        )
        service.gamification = SimpleNamespace(award=AsyncMock(return_value={"awarded_xp": 5, "duplicate": False}))
        return service

    async def record(self, items, *, source="lesson", user_id=1, lesson_order=1):
        async with self.factory() as session:
            user = await session.get(User, user_id)
            await self.mistakes(session).record_items(
                user, items, source=source, level="hsk1", lesson_order=lesson_order
            )
            await session.commit()

    async def plan(self, *, user_id=1, lesson_order=3, level="hsk1", formats=ALL_FORMATS, day=None, cfg=None):
        with patch.object(adaptive, "local_today", return_value=day or self.today):
            async with self.factory() as session:
                user = await session.get(User, user_id)
                return await CourseAdaptiveLessonService(session, cfg or self.settings).plan(
                    user, level=level, lesson_order=lesson_order, formats=formats, language="uz",
                    analytics_client="iphone_pwa",
                )

    async def stored_item(self, plan_id, item_id):
        async with self.factory() as session:
            plan = await session.get(CourseAdaptivePlan, plan_id)
            return next(item for item in json.loads(plan.items_json) if item["id"] == item_id)

    async def answer(self, plan, item, *, correct=True, user_id=1, day=None, raw=None, cfg=None):
        stored = await self.stored_item(plan["id"], item["id"])
        question = stored["question"]
        if raw is not None:
            value = raw
        elif question.get("tokens"):
            value = list(question["answer_tokens"]) if correct else list(reversed(question["answer_tokens"]))
        else:
            value = question["answer_index"] if correct else (question["answer_index"] + 1) % len(question["options"])
        with patch.object(adaptive, "local_today", return_value=day or self.today):
            async with self.factory() as session:
                user = await session.get(User, user_id)
                return await CourseAdaptiveLessonService(session, cfg or self.settings).answer(
                    user, plan_id=plan["id"], item_id=item["id"], answer=value, analytics_client="iphone_pwa",
                )

    async def target(self) -> CourseMistakeTarget:
        async with self.factory() as session:
            return (await session.execute(select(CourseMistakeTarget))).scalar_one()

    async def snapshot(self):
        """Shaxsiy takrordan tashqari BARCHA jadvallar holati."""
        result = {}
        async with self.factory() as session:
            for table in Base.metadata.sorted_tables:
                if table.name in PERSONAL_TABLES:
                    continue
                rows = (await session.execute(select(table))).all()
                result[table.name] = sorted(repr(tuple(row)) for row in rows)
        return result

    # ------------------------------------------------------------------

    async def test_disabled_flag_returns_no_plan_and_writes_nothing(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        result = await self.plan(cfg=settings(COURSE_ADAPTIVE_ENABLED=False))
        self.assertEqual(result, {"ok": True, "enabled": False, "plan": None})
        async with self.factory() as session:
            self.assertEqual((await session.execute(select(CourseAdaptivePlan))).all(), [])
        self.assertEqual((await self.target()).adaptive_state_json, "{}")

    async def test_verified_lesson_mistake_becomes_one_hidden_key_question(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        result = await self.plan()
        self.assertTrue(result["enabled"])
        [item] = result["plan"]["items"]
        self.assertEqual((item["kind"], item["skill"], item["slot"]), ("review", "meaning", 1))
        self.assertEqual(item["question"]["format"], "meaning_choice")
        self.assertEqual(item["question"]["id"], item["id"])
        self.assertFalse(HIDDEN & set(item["question"]))
        self.assertNotIn("target_id", item)
        self.assertFalse(item["answered"])
        target = await self.target()
        self.assertEqual(target.adaptive_due_on, self.today)
        self.assertIn("meaning", json.loads(target.adaptive_state_json)["skills"])

    async def test_verified_exam_blank_repeats_exact_word_in_original_context(self):
        source = json.load(open("app/static/course_v3_data/exams/hsk1.json", encoding="utf-8"))
        exam = canonicalize_hsk_exam_material(source, level="hsk1", lang="uz", source_path="exam")
        question = next(
            item for item in exam["questions"]
            if item["format"] == "text_choice" and item["sentence"] == "我___学生。"
        )
        correct = question["answer_index"]
        option = question["option_materials"][correct]
        await self.record(
            [{
                "question": question["prompt"],
                "selected_answer": question["options"][(correct + 1) % len(question["options"])],
                "correct_answer": question["options"][correct],
                "category": "word",
                "material": {
                    "material_ref": question["id"],
                    "format": question["format"],
                    "category": "word",
                    "language": "uz",
                    "prompt": question["prompt"],
                    "sentence": question["sentence"],
                    "pinyin": option["pinyin"],
                    "translation": option["translation"],
                    "options": question["options"],
                    "answer_index": correct,
                    "correct_answer": question["options"][correct],
                },
            }],
            source="test",
            lesson_order=1,
        )
        target = await self.target()
        self.assertEqual((target.kind, target.zh), ("word", option["zh"]))
        self.assertEqual(json.loads(target.payload_json)["gap"]["sentence"], question["sentence"])

        result = await self.plan()
        self.assertTrue(result["enabled"])
        [item] = result["plan"]["items"]
        self.assertEqual((item["skill"], item["question"]["format"]), ("grammar", "gap_fill"))
        self.assertEqual(item["question"]["sentence"], question["sentence"])
        self.assertFalse(HIDDEN & set(item["question"]))
        feedback = await self.answer(result["plan"], item)
        self.assertTrue(feedback["ok"] and feedback["correct"])

    async def test_plan_is_retry_stable_and_resumes_answered_items(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        first = await self.plan()
        item = first["plan"]["items"][0]
        await self.answer(first["plan"], item)
        again = await self.plan()
        self.assertEqual(again["plan"]["id"], first["plan"]["id"])
        self.assertEqual([entry["id"] for entry in again["plan"]["items"]], [item["id"]])
        self.assertTrue(again["plan"]["items"][0]["answered"])
        self.assertTrue(again["plan"]["items"][0]["feedback"]["correct"])
        async with self.factory() as session:
            self.assertEqual(len((await session.execute(select(CourseAdaptivePlan))).all()), 1)

    async def test_mistake_from_this_same_lesson_is_not_repeated_as_adaptive(self):
        await self.record(lesson_items((WORD_CARD, 0)), lesson_order=1)
        result = await self.plan(lesson_order=1)
        self.assertEqual(result["plan"]["items"], [])

    async def test_client_graded_and_ai_sources_are_never_used(self):
        for source in ("recognition", "memorize", "voice", "pronunciation"):
            await self.record(lesson_items((WORD_CARD, 0)), source=source)
        async with self.factory() as session:
            rows = (await session.execute(select(CourseMistakeTarget))).scalars().all()
        self.assertTrue(rows, "unverified sources still create Xatolarim targets")
        self.assertFalse({"lesson", "test", "training", "challenge"} & set(rows[0].sources.split(",")))
        result = await self.plan()
        self.assertEqual(result["plan"]["items"], [])

    async def test_never_more_than_three_items(self):
        refs = [f"lesson:hsk1:1:section:1:card:{index}" for index in range(1, 12)]
        await self.record(lesson_items(*[(ref, 0) for ref in refs]))
        await self.record(lesson_items(*[(ref.replace(":1:section", ":2:section"), 0) for ref in refs], lesson_order=2))
        result = await self.plan(lesson_order=4)
        self.assertLessEqual(len(result["plan"]["items"]), adaptive.MAX_ADAPTIVE_ITEMS)
        self.assertEqual(len({item["id"].split(":")[1] for item in result["plan"]["items"]}),
                         len(result["plan"]["items"]))

    async def test_correct_answer_changes_only_personal_review_state(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        before_target = await self.target()
        before = await self.snapshot()
        result = await self.plan()
        item = result["plan"]["items"][0]
        feedback = await self.answer(result["plan"], item)
        self.assertTrue(feedback["ok"] and feedback["correct"], feedback)
        self.assertEqual(await self.snapshot(), before)
        target = await self.target()
        # Xatolarim progressi va qoidalari o'zgarmaydi.
        self.assertEqual(
            (target.status, target.passed_formats, target.wrong_count, target.review_count, target.sources),
            (before_target.status, before_target.passed_formats, before_target.wrong_count,
             before_target.review_count, before_target.sources),
        )

    async def test_wrong_answer_is_a_new_verified_mistake_but_not_a_lesson_result(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        before = await self.snapshot()
        wrong_before = (await self.target()).wrong_count
        result = await self.plan()
        feedback = await self.answer(result["plan"], result["plan"]["items"][0], correct=False)
        self.assertFalse(feedback["correct"])
        self.assertIn("correct_answer", feedback)
        self.assertEqual(await self.snapshot(), before)
        target = await self.target()
        self.assertEqual(target.status, "active")
        self.assertEqual(target.wrong_count, wrong_before + 1)
        self.assertIn("adaptive", target.sources.split(","))
        skill = json.loads(target.adaptive_state_json)["skills"]["meaning"]
        self.assertEqual((skill["need"], skill["ok_days"], skill["box"]), (4, [], 0))

    async def test_duplicate_answer_returns_stored_feedback_without_double_counting(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        result = await self.plan()
        item = result["plan"]["items"][0]
        first = await self.answer(result["plan"], item)
        # Takror (masalan, tarmoq qayta yubordi) — hatto boshqa javob bilan ham.
        second = await self.answer(result["plan"], item, correct=False)
        self.assertTrue(second["duplicate"])
        self.assertEqual(second["correct"], first["correct"])
        skill = json.loads((await self.target()).adaptive_state_json)["skills"]["meaning"]
        self.assertEqual(skill["ok_days"], [self.today.isoformat()])
        async with self.factory() as session:
            events = (await session.execute(
                select(CourseMiniAppEvent).where(CourseMiniAppEvent.event_name == "adaptive_answer_verified")
            )).scalars().all()
        self.assertEqual(len(events), 1)
        self.assertEqual(json.loads(events[0].payload_json)["client"], "iphone_pwa")

    async def test_spaced_cycle_retires_after_three_days_and_hands_word_to_mastery(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        day0, day1, day2, day4 = (self.today + timedelta(days=offset) for offset in (0, 1, 2, 4))
        plan = (await self.plan(day=day0))["plan"]
        await self.answer(plan, plan["items"][0], day=day0)
        # Shu kuni boshqa darsda yana chiqmaydi.
        self.assertEqual((await self.plan(day=day0, lesson_order=4))["plan"]["items"], [])
        plan = (await self.plan(day=day1))["plan"]
        await self.answer(plan, plan["items"][0], day=day1)
        self.assertEqual((await self.plan(day=day2))["plan"]["items"], [])
        plan = (await self.plan(day=day4))["plan"]
        feedback = await self.answer(plan, plan["items"][0], day=day4)
        self.assertTrue(feedback["correct"])
        target = await self.target()
        skill = json.loads(target.adaptive_state_json)["skills"]["meaning"]
        self.assertEqual(skill["phase"], "retired")
        self.assertEqual(target.adaptive_due_on, day4 + timedelta(days=7))
        # Xatolarimdagi holat egasining qoidasi bilan qoladi.
        self.assertEqual(target.status, "active")
        async with self.factory() as session:
            mastery = (await session.execute(select(CourseWordMastery))).scalars().all()
        self.assertEqual([row.zh for row in mastery], ["你"])

    async def test_xatolarim_clear_schedules_one_final_check_after_three_days(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        cleared_at = datetime.now(timezone.utc) - timedelta(days=4)
        async with self.factory() as session:
            row = (await session.execute(select(CourseMistakeTarget))).scalar_one()
            row.status, row.cleared_at = "cleared", cleared_at
            row.adaptive_due_on = final_check_due_on(cleared_at)
            await session.commit()
        today = datetime.now(timezone.utc).date()
        result = await self.plan(day=today)
        [item] = result["plan"]["items"]
        self.assertEqual(item["kind"], "final_check")
        feedback = await self.answer(result["plan"], item, day=today)
        self.assertTrue(feedback["correct"])
        target = await self.target()
        state = json.loads(target.adaptive_state_json)
        self.assertEqual(target.status, "cleared")
        self.assertEqual(state["final"]["status"], "passed")
        self.assertEqual({skill["phase"] for skill in state["skills"].values()}, {"retired"})
        # Ertasiga yakuniy tekshiruv qayta chiqmaydi.
        self.assertEqual((await self.plan(day=today + timedelta(days=1)))["plan"]["items"], [])

    async def test_failed_final_check_reopens_the_xatolarim_target(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        cleared_at = datetime.now(timezone.utc) - timedelta(days=5)
        async with self.factory() as session:
            row = (await session.execute(select(CourseMistakeTarget))).scalar_one()
            row.status, row.cleared_at, row.passed_formats = "cleared", cleared_at, ""
            row.adaptive_due_on = (cleared_at + timedelta(days=3)).date()
            await session.commit()
        today = datetime.now(timezone.utc).date()
        result = await self.plan(day=today)
        await self.answer(result["plan"], result["plan"]["items"][0], correct=False, day=today)
        target = await self.target()
        self.assertEqual((target.status, target.passed_formats), ("active", ""))
        self.assertEqual(json.loads(target.adaptive_state_json)["final"]["status"], "failed")

    async def test_recently_cleared_target_waits_and_gets_no_ordinary_review(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        await self.plan()  # holat yaratiladi (faol ko'nikma, bugun muddati)
        async with self.factory() as session:
            row = (await session.execute(select(CourseMistakeTarget))).scalar_one()
            row.status, row.cleared_at = "cleared", datetime.now(timezone.utc) - timedelta(days=1)
            await session.commit()
        result = await self.plan(lesson_order=4)
        self.assertEqual(result["plan"]["items"], [])

    async def test_real_xatolarim_clear_sets_the_final_check_due_date(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        async with self.factory() as session:
            started = await self.mistakes(session).start_review(
                777, access_ref="review-ref-0001", formats=ALL_FORMATS, language="uz"
            )
        async with self.factory() as session:
            event = (await session.execute(
                select(CourseMiniAppEvent).where(CourseMiniAppEvent.event_name == "mistake_review_started")
            )).scalar_one()
            snapshot = {q["id"]: q for q in json.loads(event.payload_json)["questions"]}
        for public in started["session"]["questions"]:
            stored = snapshot[public["id"]]
            answer = list(stored["answer_tokens"]) if stored.get("tokens") else stored["answer_index"]
            async with self.factory() as session:
                await self.mistakes(session).answer_review_question(
                    777, session_id=started["session"]["id"], question_id=public["id"], selected_index=answer
                )
        async with self.factory() as session:
            completed = await self.mistakes(session).complete_review(777, session_id=started["session"]["id"], answers=[])
        self.assertEqual(completed["cleared"], 1)
        target = await self.target()
        self.assertEqual(target.status, "cleared")
        self.assertEqual(target.adaptive_due_on, (adaptive.aware(target.cleared_at) + timedelta(days=3)).date())

    async def test_concurrent_plan_requests_share_one_plan(self):
        if not self.real_pg:
            self.skipTest("needs real PostgreSQL row locks")
        # Parallel `patch` kontekstlari bir-birini tiklaydi: haqiqiy sana bilan.
        self.today = adaptive.local_today(0)
        await self.record(lesson_items((WORD_CARD, 0)))
        first, second = await asyncio.gather(self.plan(), self.plan())
        self.assertEqual(first["plan"]["id"], second["plan"]["id"])
        async with self.factory() as session:
            self.assertEqual(len((await session.execute(select(CourseAdaptivePlan))).all()), 1)

    async def test_concurrent_duplicate_answers_count_once(self):
        if not self.real_pg:
            self.skipTest("needs real PostgreSQL row locks")
        # Parallel `patch` kontekstlari bir-birini tiklaydi: haqiqiy sana bilan.
        self.today = adaptive.local_today(0)
        await self.record(lesson_items((WORD_CARD, 0)))
        result = await self.plan()
        item = result["plan"]["items"][0]
        answers = await asyncio.gather(*(self.answer(result["plan"], item) for _ in range(3)))
        self.assertEqual(sorted(answer["duplicate"] for answer in answers), [False, True, True])
        skill = json.loads((await self.target()).adaptive_state_json)["skills"]["meaning"]
        self.assertEqual(skill["ok_days"], [self.today.isoformat()])

    # ---------- security / context ----------

    async def test_other_account_cannot_answer_a_plan(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        result = await self.plan()
        with self.assertRaises(AdaptiveRequestError) as caught:
            await self.answer(result["plan"], result["plan"]["items"][0], user_id=2)
        self.assertEqual((caught.exception.code, caught.exception.status_code), ("adaptive_plan_not_found", 404))

    async def test_unknown_item_and_malformed_answers_are_rejected(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        result = await self.plan()
        item = result["plan"]["items"][0]
        for raw in (99, -1, ["你"], True):
            with self.assertRaises(AdaptiveRequestError) as caught:
                await self.answer(result["plan"], item, raw=raw)
            self.assertEqual(caught.exception.code, "adaptive_answer_invalid")
        with patch.object(adaptive, "local_today", return_value=self.today):
            async with self.factory() as session:
                user = await session.get(User, 1)
                with self.assertRaises(AdaptiveRequestError) as caught:
                    await CourseAdaptiveLessonService(session, self.settings).answer(
                        user, plan_id=result["plan"]["id"], item_id="a9:1:meaning_choice", answer=0
                    )
        self.assertEqual(caught.exception.code, "adaptive_answer_invalid")

    async def test_plan_requires_the_learners_current_track_and_reached_lesson(self):
        with self.assertRaises(AdaptiveRequestError) as caught:
            await self.plan(level="hsk2")
        self.assertEqual((caught.exception.code, caught.exception.status_code), ("adaptive_context_changed", 409))
        with self.assertRaises(AdaptiveRequestError) as caught:
            await self.plan(lesson_order=7)
        self.assertEqual((caught.exception.code, caught.exception.status_code), ("adaptive_lesson_unavailable", 403))
        self.assertTrue((await self.plan(lesson_order=6))["ok"])

    async def test_stale_plan_is_not_accepted(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        result = await self.plan()
        with self.assertRaises(AdaptiveRequestError) as caught:
            await self.answer(result["plan"], result["plan"]["items"][0], day=self.today + timedelta(days=2))
        self.assertEqual(caught.exception.code, "adaptive_plan_stale")
        # Yarim tundan keyin ochiq qolgan dars — qabul qilinadi.
        ok = await self.answer(result["plan"], result["plan"]["items"][0], day=self.today + timedelta(days=1))
        self.assertTrue(ok["ok"])

    async def test_rollback_flag_rejects_answers(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        result = await self.plan()
        with self.assertRaises(AdaptiveRequestError) as caught:
            await self.answer(result["plan"], result["plan"]["items"][0],
                              cfg=settings(COURSE_ADAPTIVE_ENABLED=False))
        self.assertEqual(caught.exception.code, "adaptive_disabled")

    async def test_rollout_percent_and_allowlist(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        off = await self.plan(cfg=settings(COURSE_ADAPTIVE_ROLLOUT_PERCENT=0))
        self.assertFalse(off["enabled"])
        on = await self.plan(cfg=settings(COURSE_ADAPTIVE_ROLLOUT_PERCENT=0, COURSE_ADAPTIVE_ALLOWLIST="5, 1"))
        self.assertTrue(on["enabled"])

    async def test_shadow_mode_counts_without_writing_review_state(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        result = await self.plan(cfg=settings(COURSE_ADAPTIVE_ENABLED=False, COURSE_ADAPTIVE_SHADOW_ENABLED=True))
        self.assertEqual(result, {"ok": True, "enabled": False, "plan": None})
        target = await self.target()
        self.assertEqual((target.adaptive_state_json, target.adaptive_due_on), ("{}", None))
        async with self.factory() as session:
            self.assertEqual((await session.execute(select(CourseAdaptivePlan))).all(), [])
            event = (await session.execute(
                select(CourseMiniAppEvent).where(CourseMiniAppEvent.event_name == "adaptive_shadow_planned")
            )).scalar_one()
        self.assertEqual(json.loads(event.payload_json)["count"], 1)

    async def test_client_without_any_supported_format_gets_no_plan(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        self.assertFalse((await self.plan(formats=["unknown_format"]))["enabled"])

    async def test_hsk30_track_never_sees_hsk20_material(self):
        await self.record(lesson_items((WORD_CARD, 0)))
        async with self.factory() as session:
            user = await session.get(User, 1)
            user.level = "nhsk1"
            progress = (await session.execute(select(CourseProgress).where(CourseProgress.user_id == 1))).scalar_one()
            progress.level = "nhsk1"
            await session.commit()
        result = await self.plan(level="nhsk1")
        self.assertEqual(result["plan"]["items"], [])


if __name__ == "__main__":
    unittest.main()

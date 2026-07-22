import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from app.services.course_hsk_exam_service import CourseHskExamService
from app.services.course_miniapp_access_service import CourseMiniAppAccessService
from app.services.course_miniapp_analytics_service import (
    MAX_EVENT_PAYLOAD_CHARS,
    CourseMiniAppAnalyticsService,
)
from app.services.course_question_material import (
    canonical_material_digest,
    canonicalize_hsk_exam_material,
    public_question_projection,
    public_questions_projection,
    shuffle_exam_questions,
    shuffle_question_options,
)


def _localized(uz, ru=None, tj=None):
    return {"uz": uz, "ru": ru or uz, "tj": tj or uz}


def _option(zh, pinyin, label, *, correct=False):
    item = {"zh": zh, "py": pinyin, "label": _localized(label)}
    if correct:
        item["ok"] = 1
    return item


def legacy_exam():
    return {
        "schema_version": 1,
        "level": "hsk1",
        "duration_min": 15,
        "pass_score": 60,
        "sections": [
            {
                "key": "listening",
                "title": _localized("Tinglash"),
                "title_zh": "听力",
                "questions": [
                    {
                        "no": 1,
                        "type": "audio_choice",
                        "audio_text": "你好。",
                        "stem": _localized("Eshiting va ma'noni tanlang."),
                        "options": [
                            _option("你好", "nǐ hǎo", "Salom", correct=True),
                            _option("再见", "zàijiàn", "Xayr"),
                            _option("谢谢", "xièxie", "Rahmat"),
                        ],
                    }
                ],
            },
            {
                "key": "reading",
                "title": _localized("O'qish"),
                "title_zh": "阅读",
                "questions": [
                    {
                        "no": 2,
                        "type": "text_choice",
                        "stem_zh": "我___学生。",
                        "stem": _localized("Bo'sh joyni to'ldiring."),
                        "options": [
                            _option("是", "shì", "bo'lmoq", correct=True),
                            _option("不", "bù", "emas"),
                            _option("很", "hěn", "juda"),
                        ],
                    }
                ],
            },
            {
                "key": "writing",
                "title": _localized("Yozish"),
                "title_zh": "书写",
                "questions": [
                    {
                        "no": 3,
                        "type": "text_choice",
                        "stem_zh": "我 / 学习 / 汉语",
                        "stem": _localized("To'g'ri tartibni tanlang."),
                        "options": [
                            _option("学习我汉语。", "—", "noto'g'ri"),
                            _option("我学习汉语。", "Wǒ xuéxí Hànyǔ.", "to'g'ri", correct=True),
                            _option("汉语我学习。", "—", "noto'g'ri"),
                        ],
                    }
                ],
            },
        ],
    }


def canonical_exam():
    return canonicalize_hsk_exam_material(
        legacy_exam(),
        level="hsk1",
        lang="uz",
        source_path="app/static/course_v3_data/exams/hsk1.json",
    )


def scalar_result(value):
    return SimpleNamespace(scalar_one_or_none=lambda: value)


class CourseQuestionMaterialTests(unittest.TestCase):
    def test_v2_shuffle_is_deterministic_and_keeps_answer_material_aligned(self):
        question = canonical_exam()["questions"][0]
        original_correct = question["option_materials"][question["answer_index"]]["id"]

        changed = None
        seed = None
        for index in range(100):
            candidate_seed = f"attempt-{index}"
            candidate = shuffle_question_options(question, candidate_seed)
            if candidate["options"] != question["options"]:
                changed = candidate
                seed = candidate_seed
                break

        self.assertIsNotNone(changed)
        self.assertEqual(changed, shuffle_question_options(question, seed))
        self.assertEqual(
            changed["option_materials"][changed["answer_index"]]["id"],
            original_correct,
        )
        self.assertEqual(changed["material_version"], 2)
        self.assertEqual(changed["source"]["kind"], "static_hsk_exam")

    def test_public_projection_hides_answer_and_explanation_but_keeps_section(self):
        question = canonical_exam()["questions"][0]

        public = public_question_projection(question)

        self.assertNotIn("answer_index", public)
        self.assertNotIn("explanation", public)
        self.assertNotIn("option_materials", public)
        self.assertEqual(public["section"], "listening")
        self.assertEqual(len(public["options"]), 3)

    def test_all_checked_in_materials_are_strict_and_public_projection_is_safe(self):
        for level in ("hsk1", "hsk2", "hsk3", "hsk4"):
            for lang in ("uz", "ru", "tj"):
                with self.subTest(level=level, lang=lang):
                    material = CourseHskExamService.load_material(level, lang)
                    self.assertEqual(material["level"], level)
                    self.assertEqual(material["lang"], lang)
                    self.assertTrue(material["questions"])
                    for question in public_questions_projection(material["questions"]):
                        self.assertNotIn("answer_index", question)
                        self.assertNotIn("explanation", question)
                        self.assertNotIn("option_materials", question)

    def test_compact_grading_snapshots_fit_the_event_payload_limit(self):
        for level in ("hsk1", "hsk2", "hsk3", "hsk4"):
            for lang in ("uz", "ru", "tj"):
                with self.subTest(level=level, lang=lang):
                    material = CourseHskExamService.load_material(level, lang)
                    questions = shuffle_exam_questions(material["questions"], "payload-size")
                    payload = {
                        "material_version": 2,
                        "material_id": material["id"],
                        "material_digest": canonical_material_digest(material),
                        "level": level,
                        "lang": lang,
                        "duration_min": material["duration_min"],
                        "pass_score": material["pass_score"],
                        "question_ids": [question["id"] for question in questions],
                        "shuffle_seed": f"hsk-exam:7:{level}:v2:{'x' * 24}",
                        "access_key": "x" * 24,
                        "grading_questions": CourseHskExamService._grading_snapshot(questions),
                    }
                    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
                    self.assertLessEqual(len(encoded), MAX_EVENT_PAYLOAD_CHARS)

    def test_all_wrong_completed_results_remain_idempotently_readable(self):
        for level in ("hsk1", "hsk2", "hsk3", "hsk4"):
            for lang in ("uz", "ru", "tj"):
                with self.subTest(level=level, lang=lang):
                    material = CourseHskExamService.load_material(level, lang)
                    questions = shuffle_exam_questions(material["questions"], "all-wrong")
                    wrong_items = []
                    for question in questions:
                        wrong_index = next(
                            index
                            for index in range(len(question["options"]))
                            if index != question["answer_index"]
                        )
                        wrong_items.append(
                            {
                                "question_id": question["id"],
                                "question": CourseHskExamService._question_text(question),
                                "selected_answer": question["options"][wrong_index],
                                "correct_answer": question["options"][question["answer_index"]],
                                "explanation": question["explanation"],
                                "subtype": question["section"],
                                "category": "grammar" if question["section"] == "writing" else "word",
                                "material": question,
                            }
                        )
                    completed = {
                        "material_version": 2,
                        "material_id": material["id"],
                        "score": 0,
                        "total": len(questions),
                        "percent": 0,
                        "section_scores": {
                            section: {"score": 0, "total": 4, "percent": 0}
                            for section in ("listening", "reading", "writing")
                        },
                        "pass_score": material["pass_score"],
                        "passed": False,
                        "reward": {
                            "xp": 100,
                            "awarded_xp": 10,
                            "duplicate": False,
                            "streak": 3,
                            "league": "Bronze",
                            "weekly_xp": 50,
                            "daily_xp": 10,
                        },
                        "wrong_items": wrong_items,
                    }
                    stored = CourseHskExamService._completed_event_payload(completed)
                    encoded = CourseMiniAppAnalyticsService._payload_json(stored)
                    parsed = json.loads(encoded)
                    self.assertNotIn("truncated", parsed)
                    self.assertLessEqual(len(encoded), MAX_EVENT_PAYLOAD_CHARS)
                    self.assertEqual(len(parsed["wrong_items"]), len(questions))
                    self.assertNotIn("material", parsed["wrong_items"][0])


class CourseHskExamServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session = SimpleNamespace(
            execute=AsyncMock(return_value=scalar_result(None)),
            commit=AsyncMock(),
            rollback=AsyncMock(),
        )
        self.service = CourseHskExamService(self.session)
        self.user = SimpleNamespace(id=7, telegram_id=123, level="hsk1")
        self.material = canonical_exam()
        self.service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=self.user))
        self.service.access = SimpleNamespace(
            normalize_access_ref=CourseMiniAppAccessService.normalize_access_ref,
            is_paid_user=Mock(return_value=False),
            is_free_user=Mock(return_value=True),
            consume_daily_use=AsyncMock(return_value={"allowed": True, "is_paid": False}),
            verify_ad_authorization=AsyncMock(return_value={"allowed": True, "is_paid": False}),
        )
        self.service.analytics = SimpleNamespace(
            record_server_event=AsyncMock(return_value={"ok": True, "recorded": True})
        )
        self.service.mistakes = SimpleNamespace(record_items=AsyncMock(return_value=1))
        self.service.gamification = SimpleNamespace(
            award=AsyncMock(
                return_value={
                    "xp": 10,
                    "awarded_xp": 10,
                    "duplicate": False,
                    "streak": 1,
                    "league": "Bronze",
                }
            )
        )
        self.service.load_material = Mock(return_value=self.material)

    @staticmethod
    def started_event(material, session_id, *, access_key="", include_snapshot=False):
        questions = shuffle_exam_questions(material["questions"], session_id)
        payload = {
            "material_version": 2,
            "material_id": material["id"],
            "material_digest": canonical_material_digest(material),
            "level": material["level"],
            "lang": material["lang"],
            "duration_min": material["duration_min"],
            "pass_score": material["pass_score"],
            "question_ids": [question["id"] for question in questions],
            "shuffle_seed": session_id,
        }
        if access_key:
            payload["access_key"] = access_key
        if include_snapshot:
            payload["grading_questions"] = CourseHskExamService._grading_snapshot(questions)
        return SimpleNamespace(session_id=session_id, payload_json=json.dumps(payload, ensure_ascii=False))

    def test_xp_reference_is_shared_by_all_same_level_attempts_for_one_utc_day(self):
        now = datetime(2026, 7, 22, 18, 30, tzinfo=timezone.utc)

        first = self.service._xp_activity_ref(7, "hsk1", now)
        second = self.service._xp_activity_ref(7, "hsk1", now)
        other_level = self.service._xp_activity_ref(7, "hsk2", now)

        self.assertEqual(first, "hsk-exam:7:hsk1:2026-07-22:xp")
        self.assertEqual(first, second)
        self.assertNotEqual(first, other_level)

    async def test_start_records_event_and_returns_only_public_questions(self):
        result = await self.service.start(
            123,
            level="hsk1",
            lang="uz",
            access_ref="attempt-12345678",
        )

        self.assertTrue(result["ok"])
        session = result["session"]
        self.assertEqual(session["level"], "hsk1")
        self.assertEqual(session["duration_min"], 15)
        self.assertEqual(session["pass_score"], 60)
        self.assertEqual(len(session["questions"]), 3)
        for question in session["questions"]:
            self.assertNotIn("answer_index", question)
            self.assertNotIn("explanation", question)
            self.assertNotIn("option_materials", question)
            self.assertIn(question["section"], {"listening", "reading", "writing"})
        event_kwargs = self.service.analytics.record_server_event.await_args.kwargs
        self.assertEqual(event_kwargs["event_name"], "test_started")
        self.assertEqual(event_kwargs["session_id"], session["id"])
        self.assertEqual(event_kwargs["payload"]["question_ids"], [q["id"] for q in session["questions"]])
        self.assertEqual(
            len(event_kwargs["payload"]["grading_questions"]),
            len(session["questions"]),
        )
        self.service.access.consume_daily_use.assert_awaited_once_with(
            self.user,
            feature_key="training_test",
            ref="attempt-12345678",
            lifetime=True,
        )
        self.session.commit.assert_awaited_once()

    async def test_start_retry_returns_same_session_without_consuming_again(self):
        first = await self.service.start(
            123,
            level="hsk1",
            lang="uz",
            access_ref="attempt-12345678",
        )
        event_kwargs = self.service.analytics.record_server_event.await_args.kwargs
        existing = SimpleNamespace(
            session_id=first["session"]["id"],
            payload_json=json.dumps(event_kwargs["payload"], ensure_ascii=False),
        )
        self.session.execute.reset_mock()
        self.session.execute.return_value = scalar_result(existing)
        self.service.access.consume_daily_use.reset_mock()
        self.service.analytics.record_server_event.reset_mock()
        self.session.commit.reset_mock()

        retried = await self.service.start(
            123,
            level="hsk1",
            lang="uz",
            access_ref="attempt-12345678",
        )

        self.assertTrue(retried["ok"])
        self.assertTrue(retried["duplicate"])
        self.assertEqual(retried["session"], first["session"])
        self.service.access.consume_daily_use.assert_not_awaited()
        self.service.analytics.record_server_event.assert_not_awaited()
        self.session.commit.assert_not_awaited()

    async def test_ad_supported_start_fails_closed_without_bound_authorization(self):
        self.service.access.verify_ad_authorization.return_value = {
            "allowed": False,
            "error": "ad_authorization_required",
        }

        result = await self.service.start(
            123,
            level="hsk1",
            lang="uz",
            access_ref="attempt-12345678",
            ad_supported=True,
        )

        self.assertEqual(result["error"], "ad_authorization_required")
        self.service.access.verify_ad_authorization.assert_awaited_once_with(
            self.user,
            feature_key="training_test",
            access_ref="attempt-12345678",
        )
        self.service.analytics.record_server_event.assert_not_awaited()

    async def test_complete_server_grades_records_mistake_sections_and_xp(self):
        session_id = "hsk-exam:7:hsk1:v2:abc123"
        started = self.started_event(self.material, session_id)
        self.session.execute.side_effect = [scalar_result(started), scalar_result(None)]
        questions = shuffle_exam_questions(self.material["questions"], session_id)
        answers = []
        for index, question in enumerate(questions):
            selected = question["answer_index"]
            if question["section"] == "reading":
                selected = (selected + 1) % len(question["options"])
            answers.append({"question_id": question["id"], "selected_index": selected})

        result = await self.service.complete(123, session_id=session_id, answers=answers)

        self.assertTrue(result["ok"])
        self.assertFalse(result["duplicate"])
        self.assertEqual((result["score"], result["total"], result["percent"]), (2, 3, 67))
        self.assertEqual(result["pass_score"], 60)
        self.assertTrue(result["passed"])
        self.assertEqual(result["section_scores"]["listening"], {"score": 1, "total": 1, "percent": 100})
        self.assertEqual(result["section_scores"]["reading"], {"score": 0, "total": 1, "percent": 0})
        self.assertEqual(result["section_scores"]["writing"], {"score": 1, "total": 1, "percent": 100})
        self.assertEqual(len(result["wrong_items"]), 1)
        self.assertEqual(result["wrong_items"][0]["subtype"], "reading")
        wrong = result["wrong_items"][0]
        self.assertEqual(wrong["material"]["material_version"], 2)
        self.assertEqual(wrong["material"]["language"], "uz")
        self.assertEqual(wrong["material"]["format"], "text_choice")
        self.assertEqual(wrong["material"]["source"]["kind"], "static_hsk_exam")
        self.assertEqual(wrong["material"]["material_ref"], wrong["question_id"])
        self.assertIn("pinyin", wrong["material"])
        self.assertIn("translation", wrong["material"])
        self.service.mistakes.record_items.assert_awaited_once()
        self.service.gamification.award.assert_awaited_once_with(
            self.user,
            activity_type="test",
            activity_ref=(
                f"hsk-exam:7:hsk1:{datetime.now(timezone.utc).date().isoformat()}:xp"
            ),
            base_xp=10,
            level="hsk1",
        )
        completed_kwargs = self.service.analytics.record_server_event.await_args.kwargs
        self.assertEqual(completed_kwargs["event_name"], "test_completed")
        self.assertEqual(completed_kwargs["payload"]["section_scores"], result["section_scores"])
        self.session.commit.assert_awaited_once()

    async def test_complete_grades_immutable_snapshot_after_static_material_changes(self):
        session_id = "hsk-exam:7:hsk1:v2:immutable123"
        started = self.started_event(self.material, session_id, include_snapshot=True)
        self.session.execute.side_effect = [scalar_result(started), scalar_result(None)]
        issued = shuffle_exam_questions(self.material["questions"], session_id)
        answers = [
            {"question_id": question["id"], "selected_index": question["answer_index"]}
            for question in issued
        ]
        self.service.load_material = Mock(side_effect=AssertionError("static material must not be reloaded"))

        result = await self.service.complete(123, session_id=session_id, answers=answers)

        self.assertTrue(result["ok"])
        self.assertEqual(result["score"], len(issued))
        self.assertEqual(result["wrong_items"], [])
        self.service.load_material.assert_not_called()

    async def test_complete_is_idempotent_and_does_not_repeat_side_effects(self):
        session_id = "hsk-exam:7:hsk1:v2:done123"
        started = self.started_event(self.material, session_id)
        stored = {
            "score": 3,
            "total": 3,
            "percent": 100,
            "section_scores": {
                "listening": {"score": 1, "total": 1, "percent": 100},
                "reading": {"score": 1, "total": 1, "percent": 100},
                "writing": {"score": 1, "total": 1, "percent": 100},
            },
            "pass_score": 60,
            "passed": True,
            "reward": {"awarded_xp": 10},
            "wrong_items": [],
        }
        completed = SimpleNamespace(payload_json=json.dumps(stored, ensure_ascii=False))
        self.session.execute.side_effect = [scalar_result(started), scalar_result(completed)]

        result = await self.service.complete(123, session_id=session_id, answers=[])

        self.assertTrue(result["ok"])
        self.assertTrue(result["duplicate"])
        self.assertEqual(result["percent"], 100)
        self.service.mistakes.record_items.assert_not_awaited()
        self.service.gamification.award.assert_not_awaited()
        self.service.analytics.record_server_event.assert_not_awaited()
        self.session.commit.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()

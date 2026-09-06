import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai_service import AIUsageResult
from app.services.voice_practice_service import (
    FREE_PRONOUNCE_DAILY,
    MAX_DIALOGS_PER_SESSION,
    OPENING_MESSAGES,
    ROLE_PROMPTS,
    VoicePracticeError,
    VoicePracticeService,
)


def _fake_db_session():
    """`start_session` endi DB ga o'zi murojaat qiladi.

    Sabab: bugungi gapirilmagan sessiya qatorini qidiradi (qayta ishlatish) va
    kechagi ochiq qolgan qatorlarni yopadi. Stub bo'sh natija qaytaradi, ya'ni
    "qayta ishlatiladigan qator yo'q" — yangi qator yaratiladi.
    """
    session = SimpleNamespace(
        added=[],
        commit=AsyncMock(),
        execute=AsyncMock(
            return_value=SimpleNamespace(scalar_one_or_none=lambda: None, scalar_one=lambda: 0)
        ),
    )
    session.add = lambda item: session.added.append(item)
    return session


class VoicePracticeCourseContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_characters_are_supported_and_session_keeps_lesson_words(self):
        session = _fake_db_session()
        service = VoicePracticeService(session)
        user = SimpleNamespace(id=7, telegram_id=123, status="trial", payment_status="none", end_date=None)
        service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
        service.user_status = AsyncMock(return_value={"is_paid": False, "plan": "free", "remaining_voice_limit": 1})
        service._course_context = AsyncMock(
            return_value={
                "lesson_id": 55,
                "lesson_order": 3,
                "title": "Lesson 3",
                "words": [{"zh": "你好", "pinyin": "ni hao", "meaning": "hello"}],
            }
        )

        result = await service.start_session(
            123,
            role="lily",
            level="hsk1",
            language="ru",
            voice="female",
        )

        self.assertIn("lily", ROLE_PROMPTS)
        self.assertIn("manager_wang", ROLE_PROMPTS)
        self.assertEqual(result["course_context"]["lesson_id"], 55)
        self.assertEqual(result["max_dialogs"], MAX_DIALOGS_PER_SESSION)
        possible_openings = {v["chinese_reply"] for v in OPENING_MESSAGES["friend"]}
        self.assertIn(result["opening_message"]["chinese_reply"], possible_openings)
        self.assertEqual(session.added[0].role, "lily")
        self.assertEqual(session.added[0].lesson_id, 55)
        self.assertEqual(session.added[0].target_words[0]["zh"], "你好")

    async def test_paid_session_start_uses_ai_budget_gate(self):
        session = _fake_db_session()
        service = VoicePracticeService(session)
        service.user_status = AsyncMock(
            return_value={"is_paid": True, "plan": "premium", "remaining_voice_limit": -1}
        )

        budget_access = SimpleNamespace(allowed=False, message_key="ai_budget_cooldown")
        with patch("app.services.voice_practice_service.AIUsageBudgetService") as budget_cls:
            budget_cls.return_value.can_use_ai = AsyncMock(return_value=budget_access)
            with self.assertRaises(VoicePracticeError) as ctx:
                await service.start_session(
                    123,
                    role="lily",
                    level="hsk1",
                    language="ru",
                    voice="female",
                )

        self.assertEqual(ctx.exception.code, "ai_budget_cooldown")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertFalse(session.added)

    async def test_voice_message_records_transcribe_and_reply_usage(self):
        session = SimpleNamespace(commit=AsyncMock())
        service = VoicePracticeService(session)
        item = SimpleNamespace(
            turn_count=0,
            language="ru",
            level="hsk1",
            role="lily",
            history=[],
            corrections=[],
        )
        user = SimpleNamespace(
            id=7,
            telegram_id=123,
            status="active",
            payment_status="approved",
            end_date=None,
        )
        service._get_active_session = AsyncMock(return_value=item)
        service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
        service.user_status = AsyncMock(
            return_value={"is_paid": True, "plan": "premium", "remaining_voice_limit": -1}
        )
        reply_usage = AIUsageResult(
            content='{"chinese_reply":"你好！","pinyin":"nǐ hǎo","translation":"Привет","correction":null}',
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=30,
            total_tokens=130,
        )
        service._generate_reply = AsyncMock(
            return_value=(
                {
                    "chinese_reply": "你好！",
                    "pinyin": "nǐ hǎo",
                    "translation": "Привет",
                    "correction": None,
                },
                reply_usage,
            )
        )
        transcribe_usage = AIUsageResult(
            content="你好",
            model="gpt-4o-mini-transcribe",
            prompt_tokens=50,
            completion_tokens=0,
            total_tokens=50,
        )
        ok_record = SimpleNamespace(
            cooldown_started=False,
            budget_depleted=False,
            message_key="",
            cooldown_hours=6,
        )
        cooldown_record = SimpleNamespace(
            cooldown_started=True,
            budget_depleted=False,
            message_key="ai_budget_cooldown_notice",
            cooldown_hours=6,
        )

        with patch("app.services.voice_practice_service.settings.OPENAI_API_KEY", "test-key"), patch(
            "app.services.voice_practice_service.AIService"
        ) as ai_cls, patch("app.services.voice_practice_service.AIUsageBudgetService") as budget_cls:
            ai_cls.return_value.transcribe_voice_with_usage = AsyncMock(return_value=transcribe_usage)
            budget_service = budget_cls.return_value
            budget_service.can_use_ai = AsyncMock(return_value=SimpleNamespace(allowed=True, message_key=""))
            budget_service.record_usage = AsyncMock(side_effect=[ok_record, cooldown_record])

            result = await service.process_message(
                123,
                session_id="session-1",
                audio_bytes=b"audio-bytes",
                filename="voice.webm",
            )

        self.assertEqual(result["transcription"], "你好")
        self.assertEqual(result["budget_notice"]["code"], "ai_budget_cooldown_notice")
        self.assertEqual(item.turn_count, 1)
        self.assertFalse(result["session_should_end"])
        self.assertEqual(result["max_dialogs"], MAX_DIALOGS_PER_SESSION)
        self.assertEqual(
            [call.kwargs["source"] for call in budget_service.record_usage.await_args_list],
            ["voice_practice_transcribe", "voice_practice_reply"],
        )

    async def test_seventh_voice_dialog_ends_session_after_ai_reply(self):
        session = SimpleNamespace(commit=AsyncMock())
        service = VoicePracticeService(session)
        item = SimpleNamespace(
            turn_count=MAX_DIALOGS_PER_SESSION - 1,
            language="uz",
            level="hsk1",
            role="teacher_li",
            history=[],
            corrections=[],
        )
        user = SimpleNamespace(
            id=7,
            telegram_id=123,
            status="active",
            payment_status="approved",
            end_date=None,
        )
        service._get_active_session = AsyncMock(return_value=item)
        service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
        service.user_status = AsyncMock(
            return_value={"is_paid": True, "plan": "premium", "remaining_voice_limit": -1}
        )
        reply_usage = AIUsageResult(
            content='{"chinese_reply":"我得走了，下次见！","pinyin":"wǒ děi zǒu le, xià cì jiàn","translation":"Ketishim kerak, keyingi safar ko‘rishamiz","correction":null}',
            model="gpt-4o-mini",
            prompt_tokens=80,
            completion_tokens=20,
            total_tokens=100,
        )
        service._generate_reply = AsyncMock(
            return_value=(
                {
                    "chinese_reply": "我得走了，下次见！",
                    "pinyin": "wǒ děi zǒu le, xià cì jiàn",
                    "translation": "Ketishim kerak, keyingi safar ko'rishamiz",
                    "correction": None,
                },
                reply_usage,
            )
        )
        transcribe_usage = AIUsageResult(
            content="老师再见",
            model="gpt-4o-mini-transcribe",
            prompt_tokens=40,
            completion_tokens=0,
            total_tokens=40,
        )
        ok_record = SimpleNamespace(
            cooldown_started=False,
            budget_depleted=False,
            message_key="",
            cooldown_hours=6,
        )

        with patch("app.services.voice_practice_service.settings.OPENAI_API_KEY", "test-key"), patch(
            "app.services.voice_practice_service.AIService"
        ) as ai_cls, patch("app.services.voice_practice_service.AIUsageBudgetService") as budget_cls:
            ai_cls.return_value.transcribe_voice_with_usage = AsyncMock(return_value=transcribe_usage)
            budget_service = budget_cls.return_value
            budget_service.can_use_ai = AsyncMock(return_value=SimpleNamespace(allowed=True, message_key=""))
            budget_service.record_usage = AsyncMock(return_value=ok_record)

            result = await service.process_message(
                123,
                session_id="session-1",
                audio_bytes=b"audio-bytes",
                filename="voice.webm",
            )

        self.assertEqual(item.turn_count, MAX_DIALOGS_PER_SESSION)
        self.assertTrue(result["session_should_end"])

    async def test_free_pronunciation_limit_blocks_before_ai_call(self):
        session = SimpleNamespace(commit=AsyncMock())
        service = VoicePracticeService(session)
        service._is_paid_telegram_user = AsyncMock(return_value=False)
        service._pronounce_count_today = AsyncMock(return_value=FREE_PRONOUNCE_DAILY)

        with patch("app.services.voice_practice_service.settings.OPENAI_API_KEY", "test-key"), patch(
            "app.services.voice_practice_service.AIService"
        ) as ai_cls:
            with self.assertRaises(VoicePracticeError) as ctx:
                await service.score_pronunciation(
                    123,
                    target="你好",
                    audio_bytes=b"audio-bytes",
                    filename="voice.webm",
                    language="uz",
                    level="hsk1",
                )

        self.assertEqual(ctx.exception.code, "PRONOUNCE_LIMIT_EXCEEDED")
        self.assertEqual(ctx.exception.status_code, 403)
        ai_cls.assert_not_called()

    async def test_pronunciation_score_accepts_pinyin_transcript(self):
        session = SimpleNamespace(commit=AsyncMock())
        service = VoicePracticeService(session)
        service._is_paid_telegram_user = AsyncMock(return_value=False)
        service._pronounce_count_today = AsyncMock(return_value=0)
        transcribe_usage = AIUsageResult(
            content="ni hao",
            model="gpt-4o-mini-transcribe",
            prompt_tokens=50,
            completion_tokens=0,
            total_tokens=50,
        )
        ok_record = SimpleNamespace(
            cooldown_started=False,
            budget_depleted=False,
            message_key="",
            cooldown_hours=6,
        )

        with patch("app.services.voice_practice_service.settings.OPENAI_API_KEY", "test-key"), patch(
            "app.services.voice_practice_service.AIService"
        ) as ai_cls, patch("app.services.voice_practice_service.AIUsageBudgetService") as budget_cls:
            ai_cls.return_value.transcribe_voice_with_usage = AsyncMock(return_value=transcribe_usage)
            budget_cls.return_value.record_usage = AsyncMock(return_value=ok_record)

            result = await service.score_pronunciation(
                123,
                target="你好",
                target_pinyin="nǐ hǎo",
                audio_bytes=b"audio-bytes",
                filename="voice.webm",
                language="uz",
                level="hsk1",
            )

        self.assertEqual(result["score"], 100)
        self.assertTrue(result["passed"])
        self.assertEqual(result["heard"], "ni hao")
        self.assertIn("你好", ai_cls.return_value.transcribe_voice_with_usage.await_args.kwargs["speech_hint"])


if __name__ == "__main__":
    unittest.main()


class VoiceAdaptiveContextTests(unittest.IsolatedAsyncioTestCase):
    """AI Voice endi ilovaning qolgan qismi kabi o'quvchiga moslashadi.

    Ilgari u faqat HSK darajasini va joriy dars so'zlarini bilardi; takror
    so'zlari TASODIFIY tanlanardi va o'quvchining xatolari, maqsadi hamda
    zaif tomoni suhbatga umuman kirmasdi.
    """

    def _service(self):
        return VoicePracticeService(SimpleNamespace(execute=AsyncMock(), commit=AsyncMock()))

    async def test_review_words_come_from_the_srs_schedule_not_from_chance(self):
        service = self._service()
        mastery = SimpleNamespace(
            context=AsyncMock(return_value=("hsk1", 4, 0)),
            select=AsyncMock(
                return_value=[
                    {"zh": "新词", "kind": "new"},
                    {"zh": "医院", "kind": "review"},
                    {"zh": "你好", "kind": "review"},
                ]
            ),
            record_drill=AsyncMock(),
        )
        with patch(
            "app.services.voice_practice_service.CourseWordMasteryService",
            MagicMock(return_value=mastery),
        ), patch(
            "app.services.voice_practice_service.course_v3_vocab.words_for_level",
            return_value=[{"zh": "医院", "pinyin": "yīyuàn", "meaning": {"ru": "больница"}}],
        ):
            words = await service._srs_review_words(
                SimpleNamespace(id=7), "ru", exclude={"你好"}, limit=6
            )

        # Muddati kelgan takrorlar oldinda, dars so'zi chiqarib tashlangan.
        self.assertEqual(["医院", "新词"], [w["zh"] for w in words])
        self.assertEqual("больница", words[0]["meaning"])
        # SRS faqat O'QILADI: suhbat o'quvchining rejalashtirilgan takrorlarini
        # jimgina yeb qo'ymasligi kerak.
        mastery.record_drill.assert_not_awaited()
        # Talaffuz skili — "recognition" bo'lsa faqat bir belgili so'zlar qolardi.
        self.assertEqual("pronunciation", mastery.select.await_args.kwargs["skill"])

    async def test_a_broken_srs_lookup_does_not_stop_the_conversation(self):
        service = self._service()
        with patch(
            "app.services.voice_practice_service.CourseWordMasteryService",
            MagicMock(side_effect=RuntimeError("db down")),
        ):
            self.assertEqual([], await service._srs_review_words(
                SimpleNamespace(id=7), "ru", exclude=set()
            ))

    async def test_the_plan_carries_goal_weakness_and_one_retest(self):
        service = self._service()
        service.progress_repo = SimpleNamespace(get_by_user_id=AsyncMock(return_value=None))
        service.session.execute = AsyncMock(
            return_value=SimpleNamespace(scalar_one_or_none=lambda: None)
        )
        signals = SimpleNamespace(
            goal="travel",
            preferred_focus="speaking",
            weakness={"grammar": 5, "word": 1, "pronunciation": 0},
        )
        overview = {
            "items": [
                # Xitoycha bo'lmagan yozuv retest uchun yaramaydi.
                {"question": "spasibo", "correct_answer": "rahmat"},
                {"question": "我昨天去北京", "correct_answer": "我昨天去了北京"},
                {"question": "很便易", "correct_answer": "很便宜"},
            ]
        }
        with patch(
            "app.services.voice_practice_service.LearningSignalsService",
            MagicMock(return_value=SimpleNamespace(load=AsyncMock(return_value=signals))),
        ), patch(
            "app.services.voice_practice_service.CourseMistakeService",
            MagicMock(return_value=SimpleNamespace(overview=AsyncMock(return_value=overview))),
        ):
            plan = await service._learner_plan(SimpleNamespace(id=7), 123, "hsk1")

        self.assertEqual("travel", plan["goal"])
        self.assertEqual("grammar", plan["weak"])
        # Eng ko'pi BITTA qayta sinash — suhbat so'roqqa aylanmasligi kerak.
        self.assertEqual([{"q": "我昨天去北京", "a": "我昨天去了北京"}], plan["retest"])

    async def test_broken_signals_leave_the_plan_empty(self):
        # Bo'sh reja = moslashuvdan oldingi prompt. Bu ayni paytda rollback yo'li.
        service = self._service()
        service.progress_repo = SimpleNamespace(get_by_user_id=AsyncMock(return_value=None))
        service.session.execute = AsyncMock(side_effect=RuntimeError("db down"))
        self.assertEqual({}, await service._learner_plan(SimpleNamespace(id=7), 123, "hsk1"))


class VoiceAdaptivePromptTests(unittest.IsolatedAsyncioTestCase):
    async def _prompt(self, plan, history=None, target_words=None):
        service = VoicePracticeService(SimpleNamespace())
        item = SimpleNamespace(
            id="sess-1",
            role="friend",
            level="hsk1",
            language="ru",
            history=history or [],
            turn_count=len(history or []),
            target_words=target_words or [{"zh": "医院"}],
            review_words=[],
            plan_json=plan,
        )
        usage = SimpleNamespace(content='{"chinese_reply":"好","pinyin":"hǎo","translation":"ok","correction":null}')
        completer = AsyncMock(return_value=usage)
        with patch(
            "app.services.voice_practice_service.AIService",
            MagicMock(return_value=SimpleNamespace(complete_messages_with_usage=completer)),
        ):
            await service._generate_reply(item, "我去医院")
        return completer.await_args.kwargs["messages"][0]["content"]

    async def test_the_learner_block_reaches_the_model(self):
        prompt = await self._prompt(
            {"goal": "travel", "weak": "grammar", "retest": [{"q": "我去北京", "a": "我去了北京"}]}
        )
        self.assertIn("travel", prompt)
        self.assertIn("GRAMMAR", prompt)
        self.assertIn("我去了北京", prompt)
        # ENG muhim qoida baribir birinchi bo'lib qolishi shart.
        self.assertLess(prompt.index("STRICT LEVEL RULE"), prompt.index("travel"))

    async def test_an_empty_plan_keeps_the_original_prompt(self):
        prompt = await self._prompt({})
        for marker in ("travel", "GRAMMAR", "Earlier this learner"):
            self.assertNotIn(marker, prompt)
        self.assertIn("STRICT LEVEL RULE", prompt)

    async def test_words_already_spoken_are_not_pushed_again(self):
        prompt = await self._prompt(
            {},
            history=[{"user": "我去医院", "assistant": "好"}],
            target_words=[{"zh": "医院"}, {"zh": "便宜"}],
        )
        self.assertIn("already used", prompt)
        self.assertIn("医院", prompt)

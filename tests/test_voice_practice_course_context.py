import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.ai_service import AIUsageResult
from app.services.voice_practice_service import ROLE_PROMPTS, VoicePracticeError, VoicePracticeService


class VoicePracticeCourseContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_characters_are_supported_and_session_keeps_lesson_words(self):
        session = SimpleNamespace(added=[], add=lambda item: session.added.append(item), commit=AsyncMock())
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
        self.assertEqual(session.added[0].role, "lily")
        self.assertEqual(session.added[0].lesson_id, 55)
        self.assertEqual(session.added[0].target_words[0]["zh"], "你好")

    async def test_paid_session_start_uses_ai_budget_gate(self):
        session = SimpleNamespace(added=[], add=lambda item: session.added.append(item), commit=AsyncMock())
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
        self.assertEqual(
            [call.kwargs["source"] for call in budget_service.record_usage.await_args_list],
            ["voice_practice_transcribe", "voice_practice_reply"],
        )


if __name__ == "__main__":
    unittest.main()

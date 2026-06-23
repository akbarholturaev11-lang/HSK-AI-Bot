import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.voice_practice_service import ROLE_PROMPTS, VoicePracticeService


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


if __name__ == "__main__":
    unittest.main()

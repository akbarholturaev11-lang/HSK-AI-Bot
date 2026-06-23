import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.course_miniapp_practice_service import CourseMiniAppPracticeService


def question(question_id, level="hsk1", answer=0):
    return {
        "id": question_id,
        "level": level,
        "lesson": 1,
        "type": "multiple_choice",
        "subtype": "hanzi_to_meaning",
        "prompt": "Question",
        "sentence": "",
        "audio_text": "",
        "options": ["Correct", "Wrong"],
        "answer_index": answer,
        "explanation": "Explanation",
    }


class CourseMiniAppPracticeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session = SimpleNamespace(commit=AsyncMock())
        self.service = CourseMiniAppPracticeService(self.session)
        self.user = SimpleNamespace(
            id=5,
            telegram_id=123,
            status="trial",
            payment_status="none",
            end_date=None,
        )
        self.service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=self.user))
        self.service.access = SimpleNamespace(
            is_paid_user=lambda user: False,
            consume_free_use=AsyncMock(return_value={"allowed": True}),
        )
        self.service._is_completed = AsyncMock(return_value=False)
        self.service._questions = AsyncMock(return_value=[question("q1")])
        self.service.mistakes = SimpleNamespace(record_items=AsyncMock(return_value=0))
        self.service.gamification = SimpleNamespace(
            award=AsyncMock(return_value={"xp": 20, "awarded_xp": 20, "streak": 1, "league": "Bronze"})
        )

    async def test_mock_start_consumes_shared_training_test_entitlement(self):
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        with patch(
            "app.services.course_miniapp_practice_service.CourseMiniAppAnalyticsService",
            return_value=analytics,
        ):
            result = await self.service.start(
                123,
                mode="mock",
                level="hsk2",
                lang="ru",
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["session"]["mode"], "mock")
        self.service.access.consume_free_use.assert_awaited_once_with(
            self.user,
            feature_key="training_test",
            usage_ref="practice:training_test:mock:hsk2:v1",
        )

    async def test_completed_free_feature_is_locked_before_new_session(self):
        self.service._is_completed = AsyncMock(return_value=True)
        result = await self.service.start(
            123,
            mode="training",
            level="hsk1",
            lang="ru",
            skill="listening",
        )
        self.assertEqual(result, {"ok": False, "error": "free_feature_limit_reached"})
        self.service.access.consume_free_use.assert_not_awaited()

    async def test_completion_is_server_graded_and_preserves_payment(self):
        self.service._questions = AsyncMock(
            return_value=[question("q1", "hsk1", 0), question("q2", "hsk2", 1)]
        )
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        with patch(
            "app.services.course_miniapp_practice_service.CourseMiniAppAnalyticsService",
            return_value=analytics,
        ):
            result = await self.service.complete(
                123,
                session_id="practice:5:placement:placement:hsk1:v1",
                mode="placement",
                level="hsk1",
                lang="ru",
                skill="",
                answers=[
                    {"question_id": "q1", "selected_index": 0, "percent": 100},
                    {"question_id": "q2", "selected_index": 0, "percent": 100},
                ],
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["percent"], 50)
        self.assertEqual(result["recommendation"], "HSK 1")
        self.assertEqual(self.user.payment_status, "none")
        analytics.record_server_event.assert_awaited_once()
        self.service.mistakes.record_items.assert_awaited_once()
        self.service.gamification.award.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.course_mistake_service import CourseMistakeService


def mistake(item_id=1, *, wrong_count=2, resolved_count=0, user_answer="错", correct_answer="对"):
    return SimpleNamespace(
        id=item_id,
        category="word",
        source="test",
        level="hsk1",
        lesson_order=1,
        prompt=f"Question {item_id}",
        user_answer=user_answer,
        correct_answer=correct_answer,
        explanation="Explanation",
        wrong_count=wrong_count,
        review_count=0,
        resolved_count=resolved_count,
        last_reviewed_at=None,
        last_seen_at=datetime.now(timezone.utc),
    )


class CourseMistakeServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session = SimpleNamespace(commit=AsyncMock())
        self.service = CourseMistakeService(self.session)
        self.user = SimpleNamespace(
            id=7,
            telegram_id=123,
            status="trial",
            payment_status="none",
            end_date=None,
        )
        self.service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=self.user))

    def test_category_detects_character_grammar_and_voice_sources(self):
        self.assertEqual(self.service._category({"subtype": "hanzi_to_meaning"}, "test"), "character")
        self.assertEqual(self.service._category({"type": "word_order"}, "lesson"), "grammar")
        self.assertEqual(self.service._category({}, "voice"), "pronunciation")

    async def test_review_uses_shared_training_entitlement(self):
        self.service._items = AsyncMock(return_value=[mistake()])
        self.service.access = SimpleNamespace(consume_free_use=AsyncMock(return_value={"allowed": True}))
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        with patch(
            "app.services.course_mistake_service.CourseMiniAppAnalyticsService",
            return_value=analytics,
        ):
            result = await self.service.start_review(123)

        self.assertTrue(result["ok"])
        self.assertTrue(result["session"]["id"].startswith("mistake-review:7:v1:"))
        self.service.access.consume_free_use.assert_awaited_once_with(
            self.user,
            feature_key="training_test",
            usage_ref="mistake-review:v1",
        )

    async def test_correct_review_reduces_active_weakness(self):
        item = mistake(wrong_count=2, resolved_count=0)
        question = self.service._review_question(item, [item.correct_answer])
        started = SimpleNamespace(payload_json='{"mistake_ids":[1]}')
        self.session.execute = AsyncMock(
            side_effect=[
                SimpleNamespace(scalar_one_or_none=lambda: self.user.id),
                SimpleNamespace(scalar_one_or_none=lambda: started),
                SimpleNamespace(scalar_one_or_none=lambda: None),
                SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [item])),
            ]
        )
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        with patch(
            "app.services.course_mistake_service.CourseMiniAppAnalyticsService",
            return_value=analytics,
        ):
            result = await self.service.complete_review(
                123,
                session_id="mistake-review:7:v1:test-session",
                answers=[
                    {
                        "question_id": question["id"],
                        "selected_index": question["answer_index"],
                    }
                ],
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["percent"], 100)
        self.assertEqual(result["remaining"], 1)
        self.assertEqual(item.resolved_count, 1)
        self.assertEqual(item.review_count, 1)
        analytics.record_server_event.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()

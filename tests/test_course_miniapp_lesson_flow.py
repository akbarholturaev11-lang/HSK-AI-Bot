import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.course_miniapp_lesson_flow_service import CourseMiniAppLessonFlowService


class CourseMiniAppLessonFlowBuilderTests(unittest.TestCase):
    @staticmethod
    def payload():
        vocab = [
            {"zh": f"词{index}", "pinyin": f"ci{index}", "meaning": f"word {index}"}
            for index in range(1, 6)
        ]
        questions = [
            {
                "id": "q1",
                "type": "multiple_choice",
                "subtype": "hanzi_to_meaning",
                "q": "Meaning?",
                "opts": ["word 1", "word 2", "word 3"],
                "ans": 0,
            },
            {
                "id": "q2",
                "type": "listening_choice",
                "q": "Listen",
                "audioText": "词2",
                "opts": ["词1", "词2", "词3"],
                "ans": 1,
            },
            {
                "id": "q3",
                "type": "multiple_choice",
                "q": "Translate",
                "opts": ["A", "B", "C"],
                "ans": 2,
            },
            {
                "id": "q4",
                "type": "multiple_choice",
                "q": "Quick check",
                "opts": ["X", "Y", "Z"],
                "ans": 1,
            },
        ]
        tasks = [
            {
                "id": "r1",
                "type": "build_chinese_sentence",
                "prompt": "Build",
                "tokens": ["好", "你"],
                "answer": ["你", "好"],
            }
        ]
        return {
            "title": "Lesson",
            "vocabulary": vocab,
            "quiz_questions": questions,
            "reinforcement_tasks": tasks,
        }

    def test_flow_has_three_or_four_active_words_and_required_activity_types(self):
        service = CourseMiniAppLessonFlowService(SimpleNamespace())
        first = service._build_cards(self.payload(), lang="ru", lesson_order=1)
        second = service._build_cards(self.payload(), lang="ru", lesson_order=2)

        self.assertEqual(sum(card["type"] == "active_word" for card in first), 4)
        self.assertEqual(sum(card["type"] == "active_word" for card in second), 3)
        self.assertTrue(
            {
                "meaning_guess",
                "listening_choice",
                "sentence_builder",
                "word_order",
                "translation_choice",
                "pronunciation",
                "quick_quiz",
            }.issubset({card["type"] for card in first})
        )
        self.assertNotEqual([card["type"] for card in first], [card["type"] for card in second])
        self.assertTrue(all(card["required"] for card in first))


class CourseMiniAppLessonFlowCompletionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session = SimpleNamespace(commit=AsyncMock())
        self.service = CourseMiniAppLessonFlowService(self.session)
        self.user = SimpleNamespace(
            id=8,
            telegram_id=123,
            payment_status="none",
            status="trial",
        )
        self.lesson = SimpleNamespace(id=14, lesson_order=1, level="hsk1")
        self.payload = CourseMiniAppLessonFlowBuilderTests.payload()
        self.service._context = AsyncMock(return_value=(self.user, SimpleNamespace(), self.lesson, ""))
        self.service.lesson_service = SimpleNamespace(get_payload=AsyncMock(return_value=self.payload))

    def responses(self, *, wrong_card_id=None):
        cards = self.service._build_cards(self.payload, lang="ru", lesson_order=1)
        responses = []
        for card in cards:
            if card["type"] in {"active_word", "pronunciation"}:
                response = {"card_id": card["id"], "completed": True}
            elif card["type"] in {
                "meaning_guess",
                "listening_choice",
                "translation_choice",
                "quick_quiz",
            }:
                selected = card["correct_index"]
                if card["id"] == wrong_card_id:
                    selected = (selected + 1) % len(card["options"])
                response = {"card_id": card["id"], "selected_index": selected}
            else:
                answer = list(card["answer_tokens"])
                if card["id"] == wrong_card_id:
                    answer.reverse()
                response = {"card_id": card["id"], "answer_tokens": answer}
            responses.append(response)
        return cards, responses

    async def test_server_grades_answers_and_preserves_payment_fields(self):
        cards, responses = self.responses(wrong_card_id="activity:translation")
        scored_count = sum(
            card["type"] not in {"active_word", "pronunciation"} for card in cards
        )
        expected_percent = round(((scored_count - 1) / scored_count) * 100)
        study = SimpleNamespace(
            complete_v2_lesson=AsyncMock(
                return_value={"ok": True, "completed_lesson": 1, "next_lesson": 2}
            )
        )
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))

        with (
            patch(
                "app.services.course_miniapp_lesson_flow_service.StudyMiniAppService",
                return_value=study,
            ),
            patch(
                "app.services.course_miniapp_lesson_flow_service.CourseMiniAppAnalyticsService",
                return_value=analytics,
            ),
        ):
            result = await self.service.complete_flow(
                123,
                level="hsk1",
                lesson_order=1,
                lang="ru",
                responses=responses,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["percent"], expected_percent)
        study.complete_v2_lesson.assert_awaited_once_with(
            123,
            level="hsk1",
            lesson_order=1,
            percent=expected_percent,
        )
        self.assertEqual(self.user.payment_status, "none")
        self.assertEqual(analytics.record_server_event.await_count, len(cards) + 1)

    async def test_missing_required_card_never_completes_lesson(self):
        _, responses = self.responses()
        result = await self.service.complete_flow(
            123,
            level="hsk1",
            lesson_order=1,
            lang="ru",
            responses=responses[:-1],
        )
        self.assertEqual(result, {"ok": False, "error": "lesson_required_activities_incomplete"})


if __name__ == "__main__":
    unittest.main()

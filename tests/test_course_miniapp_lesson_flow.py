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

    @classmethod
    def payload_with_word_count(cls, count: int):
        payload = cls.payload()
        payload["vocabulary"] = [
            {"zh": f"词{index}", "pinyin": f"ci{index}", "meaning": f"word {index}"}
            for index in range(1, count + 1)
        ]
        return payload

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
                "dialog_context",
                "character_trace",
            }.issubset({card["type"] for card in first})
        )
        self.assertNotEqual([card["type"] for card in first], [card["type"] for card in second])
        self.assertTrue(all(card["required"] for card in first))

    def test_short_dialog_uses_natural_context_for_verbs_and_nouns(self):
        service = CourseMiniAppLessonFlowService(SimpleNamespace())
        verb_card = service._short_dialog_card(
            [
                {"zh": "赚", "pinyin": "zhuan", "meaning": "pul daromad qilish", "pos": "v"},
                {"zh": "以前", "pinyin": "yiqian", "meaning": "avval", "pos": "n"},
            ],
            lang="ru",
        )
        noun_card = service._short_dialog_card(
            [
                {"zh": "爱情", "pinyin": "aiqing", "meaning": "love", "pos": "n"},
                {"zh": "手机", "pinyin": "shouji", "meaning": "phone", "pos": "n"},
            ],
            lang="ru",
        )

        self.assertIn("赚钱", " ".join(line["text"] for line in verb_card["dialog"]))
        self.assertNotIn("我去赚", " ".join(line["text"] for line in verb_card["dialog"]))
        self.assertIn("这是爱情", " ".join(line["text"] for line in noun_card["dialog"]))
        self.assertNotIn("我去爱情", " ".join(line["text"] for line in noun_card["dialog"]))

    def test_long_word_order_tasks_are_replaced_with_short_sentence_builds(self):
        service = CourseMiniAppLessonFlowService(SimpleNamespace())
        payload = {
            "vocabulary": [
                {"zh": "以前", "pinyin": "yiqian", "meaning": "before"},
                {"zh": "更好", "pinyin": "genghao", "meaning": "better"},
            ],
            "reinforcement_tasks": [
                {
                    "type": "word_order",
                    "prompt": "Too long",
                    "tokens": ["Ман", "фикр", "мекардам", "кори", "нав", "аз", "пешина", "беҳтар", "аст"],
                    "answer": ["Ман", "фикр", "мекардам", "кори", "нав", "аз", "пешина", "беҳтар", "аст"],
                }
            ],
        }
        cards = service._build_cards(payload, lang="tj", lesson_order=1)
        order_cards = [card for card in cards if card["type"] in {"sentence_builder", "word_order"}]

        self.assertTrue(order_cards)
        self.assertTrue(all(len(card["answer_tokens"]) <= 6 for card in order_cards))
        self.assertTrue(
            any(
                "以前" in card["answer_tokens"] or "更好" in card["answer_tokens"]
                for card in order_cards
            )
        )
        self.assertFalse(
            any(
                all(len(token) == 1 and "\u4e00" <= token <= "\u9fff" for token in card["answer_tokens"])
                for card in order_cards
            )
        )

    def test_hsk_material_splits_into_small_sections_without_singletons(self):
        service = CourseMiniAppLessonFlowService(SimpleNamespace())
        payload = {
            "vocabulary": [
                {"zh": f"词{index}", "pinyin": f"ci{index}", "meaning": f"word {index}"}
                for index in range(1, 11)
            ]
        }
        hsk3 = service._section_plan(payload, level="hsk3", lesson_order=4)
        self.assertEqual(len(hsk3), 4)
        self.assertEqual([len(item["active_words"]) for item in hsk3], [3, 3, 2, 2])

        payload["vocabulary"] = [
            {"zh": f"词{index}", "pinyin": f"ci{index}", "meaning": f"word {index}"}
            for index in range(1, 32)
        ]
        hsk4 = service._section_plan(payload, level="hsk4", lesson_order=9)
        self.assertEqual(len(hsk4), 8)
        self.assertEqual(hsk4[0]["chapter_label"], "A")
        self.assertEqual(hsk4[3]["chapter_label"], "B")
        self.assertTrue(all(len(item["active_words"]) >= 2 for item in hsk4))

    def test_book_lesson_unlock_follows_completed_lesson_count(self):
        service = CourseMiniAppLessonFlowService(SimpleNamespace())
        progress = SimpleNamespace(level="hsk1", completed_lessons_count=1)

        self.assertTrue(
            service._book_lesson_unlocked(
                SimpleNamespace(level="hsk1", lesson_order=2),
                progress,
            )
        )
        self.assertFalse(
            service._book_lesson_unlocked(
                SimpleNamespace(level="hsk1", lesson_order=3),
                progress,
            )
        )
        self.assertFalse(
            service._book_lesson_unlocked(
                SimpleNamespace(level="hsk2", lesson_order=2),
                progress,
            )
        )


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
        self.service._completed_section_keys = AsyncMock(return_value={"1.1"})
        self.service.lesson_service = SimpleNamespace(get_payload=AsyncMock(return_value=self.payload))
        self.service.mistakes = SimpleNamespace(record_items=AsyncMock(return_value=0))
        self.service.gamification = SimpleNamespace(
            award=AsyncMock(return_value={"xp": 30, "awarded_xp": 30, "streak": 1, "league": "Bronze"})
        )

    def responses(self, *, wrong_card_id=None, section_key="1.2", payload=None):
        payload = payload or self.payload
        sections = self.service._section_plan(payload, level="hsk1", lesson_order=1)
        section = next(item for item in sections if item["section_key"] == section_key)
        cards = self.service._build_cards(
            self.service._section_payload(payload, section),
            lang="ru",
            lesson_order=1,
        )
        responses = []
        for card in cards:
            if card["type"] in {"active_word", "pronunciation", "character_trace"}:
                response = {"card_id": card["id"], "completed": True}
            elif card["type"] in {
                "meaning_guess",
                "listening_choice",
                "translation_choice",
                "quick_quiz",
                "dialog_context",
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
            card["type"] not in {"active_word", "pronunciation", "character_trace"} for card in cards
        )
        expected_percent = round(((scored_count - 1) / scored_count) * 100)
        study = SimpleNamespace(
            complete_v2_lesson=AsyncMock(
                return_value={"ok": True, "completed_lesson": 1, "next_lesson": 2}
            )
        )
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        access = SimpleNamespace(
            consume_free_use=AsyncMock(return_value={"allowed": True, "recorded": True})
        )

        self.service._completed_section_keys = AsyncMock(return_value={"1.1"})
        with (
            patch(
                "app.services.course_miniapp_lesson_flow_service.StudyMiniAppService",
                return_value=study,
            ),
            patch(
                "app.services.course_miniapp_lesson_flow_service.CourseMiniAppAccessService",
                return_value=access,
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
                section_key="1.2",
            )

        self.assertTrue(result["ok"])
        self.assertTrue(result["book_lesson_completed"])
        self.assertTrue(result["chapter_completed"])
        self.assertEqual(result["percent"], expected_percent)
        study.complete_v2_lesson.assert_awaited_once_with(
            123,
            level="hsk1",
            lesson_order=1,
            percent=expected_percent,
        )
        self.assertEqual(self.user.payment_status, "none")
        self.assertGreaterEqual(analytics.record_server_event.await_count, len(cards) + 4)
        self.service.mistakes.record_items.assert_awaited_once()
        self.assertEqual(self.service.gamification.award.await_count, 3)

    async def test_missing_required_card_never_completes_lesson(self):
        _, responses = self.responses()
        result = await self.service.complete_flow(
            123,
            level="hsk1",
            lesson_order=1,
            lang="ru",
            responses=responses[:-1],
            section_key="1.2",
        )
        self.assertEqual(result, {"ok": False, "error": "lesson_required_activities_incomplete"})

    async def test_client_completed_sections_unlock_next_section_when_server_event_lags(self):
        cards, responses = self.responses()
        scored_count = sum(
            card["type"] not in {"active_word", "pronunciation", "character_trace"} for card in cards
        )
        study = SimpleNamespace(
            complete_v2_lesson=AsyncMock(
                return_value={"ok": True, "completed_lesson": 1, "next_lesson": 2}
            )
        )
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        access = SimpleNamespace(
            consume_free_use=AsyncMock(return_value={"allowed": True, "recorded": True})
        )

        self.service._completed_section_keys = AsyncMock(return_value=set())
        with (
            patch(
                "app.services.course_miniapp_lesson_flow_service.StudyMiniAppService",
                return_value=study,
            ),
            patch(
                "app.services.course_miniapp_lesson_flow_service.CourseMiniAppAccessService",
                return_value=access,
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
                section_key="1.2",
                client_completed_sections=["1.1"],
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["percent"], 100)
        self.assertEqual(scored_count, result["total"])

    async def test_section_1_1_completion_returns_next_section_1_2(self):
        payload = CourseMiniAppLessonFlowBuilderTests.payload_with_word_count(6)
        _, responses = self.responses(section_key="1.1", payload=payload)
        self.service.lesson_service = SimpleNamespace(get_payload=AsyncMock(return_value=payload))
        self.service._completed_section_keys = AsyncMock(return_value=set())
        study = SimpleNamespace(complete_v2_lesson=AsyncMock())
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        access = SimpleNamespace(
            consume_free_use=AsyncMock(return_value={"allowed": True, "recorded": True})
        )

        with (
            patch(
                "app.services.course_miniapp_lesson_flow_service.StudyMiniAppService",
                return_value=study,
            ),
            patch(
                "app.services.course_miniapp_lesson_flow_service.CourseMiniAppAccessService",
                return_value=access,
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
                section_key="1.1",
            )

        self.assertTrue(result["ok"])
        self.assertFalse(result["book_lesson_completed"])
        self.assertEqual(result["next_section"]["section_key"], "1.2")
        self.assertEqual(result["next_section"]["section_no"], 2)
        study.complete_v2_lesson.assert_not_called()

    async def test_section_1_2_completion_returns_next_section_1_3_without_book_completion(self):
        payload = CourseMiniAppLessonFlowBuilderTests.payload_with_word_count(6)
        _, responses = self.responses(section_key="1.2", payload=payload)
        self.service.lesson_service = SimpleNamespace(get_payload=AsyncMock(return_value=payload))
        self.service._completed_section_keys = AsyncMock(return_value={"1.1"})
        study = SimpleNamespace(complete_v2_lesson=AsyncMock())
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        access = SimpleNamespace(
            consume_free_use=AsyncMock(return_value={"allowed": True, "recorded": True})
        )

        with (
            patch(
                "app.services.course_miniapp_lesson_flow_service.StudyMiniAppService",
                return_value=study,
            ),
            patch(
                "app.services.course_miniapp_lesson_flow_service.CourseMiniAppAccessService",
                return_value=access,
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
                section_key="1.2",
            )

        self.assertTrue(result["ok"])
        self.assertFalse(result["book_lesson_completed"])
        self.assertEqual(result["next_section"]["section_key"], "1.3")
        self.assertEqual(result["next_section_key"], "1.3")
        study.complete_v2_lesson.assert_not_called()

    async def test_last_section_completion_unlocks_next_book_lesson_section_2_1(self):
        payload = CourseMiniAppLessonFlowBuilderTests.payload_with_word_count(6)
        _, responses = self.responses(section_key="1.3", payload=payload)
        self.service.lesson_service = SimpleNamespace(get_payload=AsyncMock(return_value=payload))
        self.service._completed_section_keys = AsyncMock(return_value={"1.1", "1.2"})
        study = SimpleNamespace(
            complete_v2_lesson=AsyncMock(
                return_value={"ok": True, "completed_lesson": 1, "next_lesson": 2}
            )
        )
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        access = SimpleNamespace(
            consume_free_use=AsyncMock(return_value={"allowed": True, "recorded": True})
        )

        with (
            patch(
                "app.services.course_miniapp_lesson_flow_service.StudyMiniAppService",
                return_value=study,
            ),
            patch(
                "app.services.course_miniapp_lesson_flow_service.CourseMiniAppAccessService",
                return_value=access,
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
                section_key="1.3",
            )

        self.assertTrue(result["book_lesson_completed"])
        self.assertIsNone(result["next_section"])
        self.assertEqual(result["next_book_lesson"]["section_key"], "2.1")
        self.assertEqual(result["next_book_lesson"]["section_no"], 1)
        study.complete_v2_lesson.assert_awaited_once()

    async def test_locked_section_1_4_requires_all_previous_sections(self):
        payload = CourseMiniAppLessonFlowBuilderTests.payload_with_word_count(8)
        self.service.lesson_service = SimpleNamespace(get_payload=AsyncMock(return_value=payload))
        self.service._completed_section_keys = AsyncMock(return_value={"1.1", "1.2"})

        result = await self.service.get_flow(
            123,
            level="hsk1",
            lesson_order=1,
            lang="ru",
            section_key="1.4",
        )

        self.assertEqual(result, {"ok": False, "error": "course_section_not_unlocked"})

    async def test_completed_section_1_1_can_be_reopened(self):
        payload = CourseMiniAppLessonFlowBuilderTests.payload_with_word_count(6)
        self.service.lesson_service = SimpleNamespace(get_payload=AsyncMock(return_value=payload))
        self.service._completed_section_keys = AsyncMock(return_value={"1.1"})
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))

        with patch(
            "app.services.course_miniapp_lesson_flow_service.CourseMiniAppAnalyticsService",
            return_value=analytics,
        ):
            result = await self.service.get_flow(
                123,
                level="hsk1",
                lesson_order=1,
                lang="ru",
                section_key="1.1",
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["flow"]["section_key"], "1.1")


if __name__ == "__main__":
    unittest.main()

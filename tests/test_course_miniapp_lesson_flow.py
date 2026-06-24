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

    def test_flow_uses_section_purpose_patterns_without_repeating_builders(self):
        service = CourseMiniAppLessonFlowService(SimpleNamespace())
        intro_payload = {**self.payload(), "section_no": 1, "section_count": 6, "section_purpose": "intro"}
        listening_payload = {**self.payload(), "section_no": 3, "section_count": 6, "section_purpose": "listening"}
        usage_payload = {**self.payload(), "section_no": 4, "section_count": 6, "section_purpose": "usage"}
        intro = service._build_cards(intro_payload, lang="ru", lesson_order=1)
        listening = service._build_cards(listening_payload, lang="ru", lesson_order=1)
        usage = service._build_cards(usage_payload, lang="ru", lesson_order=1)

        self.assertGreaterEqual(sum(card["type"] == "active_word" for card in intro), 2)
        self.assertTrue(8 <= len(intro) <= 12)
        self.assertEqual(intro[0]["type"], "active_word")
        self.assertIn("meaning_guess", {card["type"] for card in intro[:4]})
        self.assertIn("listening_choice", {card["type"] for card in listening[:3]})
        self.assertIn("pronunciation", {card["type"] for card in listening[:4]})
        self.assertIn("gap_fill", {card["type"] for card in usage[:3]})
        self.assertTrue({"sentence_builder", "word_order"} & {card["type"] for card in usage[:5]})
        self.assertNotIn("character_trace", {card["type"] for card in intro + listening + usage})
        self.assertTrue(all(card["required"] for card in intro + listening + usage))
        self.assertNotEqual([card["type"] for card in intro], [card["type"] for card in listening])
        for cards in (intro, listening, usage):
            self.assertLessEqual(
                sum(card["type"] in {"sentence_builder", "word_order"} for card in cards),
                2,
            )
        for index in range(2, len(usage)):
            self.assertFalse(
                usage[index]["type"] == usage[index - 1]["type"] == usage[index - 2]["type"]
            )

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
            "section_no": 4,
            "section_count": 6,
            "section_purpose": "usage",
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

    def test_generator_keeps_cards_section_scoped_and_removes_broken_mic_stroke(self):
        service = CourseMiniAppLessonFlowService(SimpleNamespace())
        payload = {
            "vocabulary": [
                {"zh": "一", "pinyin": "yi", "meaning": "one"},
                {"zh": "二", "pinyin": "er", "meaning": "two"},
                {"zh": "三", "pinyin": "san", "meaning": "three"},
                {"zh": "四", "pinyin": "si", "meaning": "four"},
            ]
        }
        payload["section_no"] = 3
        payload["section_count"] = 6
        payload["section_purpose"] = "listening"
        cards = service._build_cards(payload, lang="uz", lesson_order=1)
        active_zh = {item["zh"] for item in payload["vocabulary"]}

        self.assertTrue(8 <= len(cards) <= 12)
        self.assertNotIn("character_trace", {card["type"] for card in cards})
        self.assertNotIn("stroke_preview", {card["type"] for card in cards})
        pronunciation_cards = [card for card in cards if card["type"] == "pronunciation"]
        self.assertTrue(pronunciation_cards)
        self.assertTrue(all(card.get("phrase") for card in pronunciation_cards))
        self.assertFalse(any("record" in card for card in pronunciation_cards))
        self.assertGreaterEqual(len({card["type"] for card in cards}), 7)
        self.assertLessEqual(sum(card["type"] == "sentence_builder" for card in cards), 1)
        self.assertLessEqual(
            sum(card["type"] in {"sentence_builder", "word_order"} for card in cards),
            2,
        )
        for card in cards:
            self.assertNotIn("undefined", str(card).lower())
            source_words = {str(item) for item in card.get("source_words", [])}
            if card["type"] == "active_word":
                source_words.add(card["word"]["zh"])
            self.assertTrue(source_words <= active_zh)

    def test_hsk_material_uses_fixed_learning_stage_sections(self):
        service = CourseMiniAppLessonFlowService(SimpleNamespace())
        payload = {
            "vocabulary": [
                {"zh": f"词{index}", "pinyin": f"ci{index}", "meaning": f"word {index}"}
                for index in range(1, 11)
            ]
        }
        hsk3 = service._section_plan(payload, level="hsk3", lesson_order=4)
        self.assertEqual(len(hsk3), 6)
        self.assertEqual([item["section_key"] for item in hsk3], ["4.1", "4.2", "4.3", "4.4", "4.5", "4.6"])
        self.assertEqual(
            [item["section_purpose"] for item in hsk3],
            ["intro", "reinforcement", "listening", "usage", "dialog", "review"],
        )
        self.assertTrue(all(len(item["active_words"]) == 10 for item in hsk3))

        payload["vocabulary"] = [
            {"zh": f"词{index}", "pinyin": f"ci{index}", "meaning": f"word {index}"}
            for index in range(1, 32)
        ]
        hsk4 = service._section_plan(payload, level="hsk4", lesson_order=9)
        self.assertEqual(len(hsk4), 6)
        self.assertEqual(hsk4[0]["chapter_label"], "A")
        self.assertEqual(hsk4[3]["chapter_label"], "B")
        self.assertEqual([item["section_purpose"] for item in hsk4[:6]], ["intro", "reinforcement", "listening", "usage", "dialog", "review"])
        self.assertEqual(hsk4[-1]["section_purpose"], "review")
        self.assertTrue(all(len(item["active_words"]) == 31 for item in hsk4))

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

    def test_unknown_section_key_does_not_fallback_to_first_section(self):
        service = CourseMiniAppLessonFlowService(SimpleNamespace())
        sections = service._section_plan(self.payload_with_word_count(6), level="hsk1", lesson_order=1)

        self.assertIsNone(service._section_by_key(sections, "1.99", lesson_order=1))


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
            if card["type"] in {"active_word", "match_pairs", "pronunciation"}:
                response = {"card_id": card["id"], "completed": True}
            elif card["type"] in {
                "meaning_guess",
                "pinyin_choice",
                "hanzi_choice",
                "listening_choice",
                "gap_fill",
                "character_recognition",
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
        cards, responses = self.responses(wrong_card_id="activity:meaning", section_key="1.6")
        scored_count = sum(
            card["type"] not in {"active_word", "match_pairs", "pronunciation"} for card in cards
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

        self.service._completed_section_keys = AsyncMock(return_value={"1.1", "1.2", "1.3", "1.4", "1.5"})
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
                section_key="1.6",
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
            card["type"] not in {"active_word", "match_pairs", "pronunciation"} for card in cards
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
        _, responses = self.responses(section_key="1.6", payload=payload)
        self.service.lesson_service = SimpleNamespace(get_payload=AsyncMock(return_value=payload))
        self.service._completed_section_keys = AsyncMock(return_value={"1.1", "1.2", "1.3", "1.4", "1.5"})
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
                section_key="1.6",
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

    async def test_path_node_1_2_returns_section_1_2_content_and_active_words(self):
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
                section_key="1.2",
            )

        self.assertTrue(result["ok"])
        flow = result["flow"]
        self.assertEqual(flow["level"], "hsk1")
        self.assertEqual(flow["book_lesson_order"], 1)
        self.assertEqual(flow["lesson_id"], 1)
        self.assertEqual(flow["section_key"], "1.2")
        self.assertEqual(flow["section_no"], 2)
        self.assertEqual([word["zh"] for word in flow["active_words"]], ["词1", "词2", "词3", "词4", "词5", "词6"])
        active_zh = {word["zh"] for word in flow["active_words"]}
        for card in flow["cards"]:
            source_words = {str(item) for item in card.get("source_words", [])}
            if card["type"] == "active_word":
                source_words.add(card["word"]["zh"])
            self.assertTrue(source_words <= active_zh)

    async def test_section_plan_and_lesson_flow_share_section_active_words(self):
        payload = CourseMiniAppLessonFlowBuilderTests.payload_with_word_count(6)
        progress = SimpleNamespace(level="hsk1", completed_lessons_count=0, current_lesson_id=self.lesson.id)
        self.service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=self.user))
        self.service.progress_repo = SimpleNamespace(get_by_user_id=AsyncMock(return_value=progress))
        self.service.lesson_repo = SimpleNamespace(
            list_by_level=AsyncMock(return_value=[self.lesson]),
            get_by_id=AsyncMock(return_value=self.lesson),
        )
        self.service.lesson_service = SimpleNamespace(get_payload=AsyncMock(return_value=payload))
        self.service._completed_section_keys_by_lesson = AsyncMock(return_value={self.lesson.id: {"1.1"}})
        self.service._completed_section_keys = AsyncMock(return_value={"1.1"})
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))

        section_plan = await self.service.get_section_plan(123, level="hsk1", lang="uz")
        with patch(
            "app.services.course_miniapp_lesson_flow_service.CourseMiniAppAnalyticsService",
            return_value=analytics,
        ):
            lesson_flow = await self.service.get_flow(
                123,
                level="hsk1",
                lesson_order=1,
                lang="uz",
                section_key="1.2",
            )

        plan_section = next(item for item in section_plan["sections"] if item["section_key"] == "1.2")
        self.assertTrue(section_plan["ok"])
        self.assertTrue(lesson_flow["ok"])
        self.assertEqual(plan_section["section_title"], "Mustahkamlash")
        self.assertEqual(plan_section["section_purpose"], "reinforcement")
        self.assertEqual(section_plan["current_section"]["section_key"], "1.2")
        self.assertEqual(plan_section["active_words"], lesson_flow["flow"]["active_words"])
        self.assertEqual(lesson_flow["flow"]["section_key"], "1.2")

    async def test_section_plan_marks_future_section_locked_from_server_progress(self):
        payload = CourseMiniAppLessonFlowBuilderTests.payload_with_word_count(8)
        progress = SimpleNamespace(level="hsk1", completed_lessons_count=0, current_lesson_id=self.lesson.id)
        self.service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=self.user))
        self.service.progress_repo = SimpleNamespace(get_by_user_id=AsyncMock(return_value=progress))
        self.service.lesson_repo = SimpleNamespace(
            list_by_level=AsyncMock(return_value=[self.lesson]),
            get_by_id=AsyncMock(return_value=self.lesson),
        )
        self.service.lesson_service = SimpleNamespace(get_payload=AsyncMock(return_value=payload))
        self.service._completed_section_keys_by_lesson = AsyncMock(return_value={self.lesson.id: {"1.1", "1.2"}})

        section_plan = await self.service.get_section_plan(123, level="hsk1", lang="uz")
        section_13 = next(item for item in section_plan["sections"] if item["section_key"] == "1.3")
        section_14 = next(item for item in section_plan["sections"] if item["section_key"] == "1.4")

        self.assertTrue(section_plan["ok"])
        self.assertTrue(section_13["is_current"])
        self.assertFalse(section_13["is_locked"])
        self.assertTrue(section_14["is_locked"])
        self.assertEqual(section_14["node_status"], "locked")

    async def test_unknown_section_key_returns_error_instead_of_first_section_content(self):
        payload = CourseMiniAppLessonFlowBuilderTests.payload_with_word_count(6)
        self.service.lesson_service = SimpleNamespace(get_payload=AsyncMock(return_value=payload))

        result = await self.service.get_flow(
            123,
            level="hsk1",
            lesson_order=1,
            lang="ru",
            section_key="1.99",
        )

        self.assertEqual(result, {"ok": False, "error": "course_section_not_found"})

    async def test_jump_to_lesson_sets_server_progress_to_selected_lesson(self):
        selected_lesson = SimpleNamespace(id=50, lesson_order=5, level="hsk2")
        progress = SimpleNamespace(
            level="hsk1",
            completed_lessons_count=1,
            homework_status="pending",
            needs_review_prompt=True,
            next_study_at=object(),
        )
        self.service.user_repo = SimpleNamespace(
            get_by_telegram_id=AsyncMock(return_value=self.user)
        )
        self.service.lesson_repo = SimpleNamespace(
            get_by_level_and_order=AsyncMock(return_value=selected_lesson)
        )
        self.service.progress_repo = SimpleNamespace(
            get_by_user_id=AsyncMock(return_value=progress),
            create=AsyncMock(),
            set_current_lesson_and_step=AsyncMock(),
        )
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))

        with patch(
            "app.services.course_miniapp_lesson_flow_service.CourseMiniAppAnalyticsService",
            return_value=analytics,
        ):
            result = await self.service.jump_to_lesson(
                123,
                level="hsk2",
                lesson_order=5,
                section_key="5.2",
                percent=42,
                score=4,
                total=10,
                passed=False,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["lesson_id"], 5)
        self.assertEqual(result["section_key"], "5.2")
        self.assertEqual(result["completed_lessons_count"], 4)
        self.assertEqual(result["percent"], 42)
        self.assertFalse(result["passed"])
        self.assertEqual(progress.level, "hsk2")
        self.assertEqual(progress.completed_lessons_count, 4)
        self.assertEqual(progress.homework_status, "none")
        self.assertFalse(progress.needs_review_prompt)
        self.assertIsNone(progress.next_study_at)
        self.service.progress_repo.set_current_lesson_and_step.assert_awaited_once_with(
            progress=progress,
            lesson_id=50,
            step="intro",
            waiting_for="none",
        )
        analytics.record_server_event.assert_awaited_once()
        payload = analytics.record_server_event.await_args.kwargs["payload"]
        self.assertEqual(payload["section_key"], "5.2")
        self.assertEqual(payload["percent"], 42)
        self.assertFalse(payload["passed"])
        self.session.commit.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()

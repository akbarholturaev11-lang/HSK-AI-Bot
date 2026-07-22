import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app.services.course_lesson_mistake_material_service import CourseLessonMistakeMaterialService
from app.services.course_miniapp_analytics_service import MAX_EVENT_PAYLOAD_CHARS
from app.services.course_mistake_service import CourseMistakeService


def mistake(
    item_id=1,
    *,
    wrong_count=2,
    resolved_count=0,
    user_answer="错",
    correct_answer="对",
    category="word",
    source="test",
    sentence="",
    audio_text="",
    material_json=None,
):
    return SimpleNamespace(
        id=item_id,
        category=category,
        source=source,
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
        sentence=sentence,
        audio_text=audio_text,
        material_json=material_json,
    )


class CourseMistakeServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session = SimpleNamespace(commit=AsyncMock(), flush=AsyncMock())
        self.service = CourseMistakeService(self.session)
        self.user = SimpleNamespace(
            id=7,
            telegram_id=123,
            status="trial",
            payment_status="none",
            end_date=None,
            language="uz",
        )
        self.service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=self.user))
        self.service.gamification = SimpleNamespace(
            award=AsyncMock(return_value={"xp": 15, "awarded_xp": 15, "streak": 1, "league": "Bronze"})
        )

    def test_category_detects_character_grammar_and_voice_sources(self):
        self.assertEqual(self.service._category({"subtype": "hanzi_to_meaning"}, "test"), "character")
        self.assertEqual(self.service._category({"type": "word_order"}, "lesson"), "grammar")
        self.assertEqual(self.service._category({}, "voice"), "pronunciation")

    def test_review_questions_use_only_same_category_answers_and_v2_material(self):
        word = mistake(1, user_answer="错", correct_answer="对", sentence="他说得对。")
        other_word = mistake(2, user_answer=None, correct_answer="喝")
        grammar = mistake(3, user_answer="我去昨天", correct_answer="我昨天去", category="grammar")

        questions = {
            item.id: question
            for item, question in self.service._review_questions([word, other_word, grammar])
        }
        question = questions[1]

        self.assertEqual(set(question["options"]), {"错", "对", "喝"})
        self.assertEqual(question["options"][question["answer_index"]], "对")
        self.assertNotIn("我昨天去", question["options"])
        self.assertEqual(question["material_version"], 2)
        self.assertEqual(question["format"], "word_choice")
        self.assertEqual(question["source"], {"kind": "test", "level": "hsk1", "lesson": 1})
        self.assertEqual(question["sentence"], "他说得对。")
        self.assertEqual(question["audio_text"], "")

    def test_review_questions_skip_item_without_a_real_second_option(self):
        item = mistake(user_answer=None, correct_answer="对")

        self.assertEqual(self.service._review_questions([item]), [])

    def test_review_distractors_match_category_format_and_language(self):
        meaning = mistake(
            1,
            user_answer="xato",
            correct_answer="to'g'ri",
            material_json=json.dumps(
                {
                    "material_version": 2,
                    "format": "meaning_choice",
                    "language": "uz",
                    "prompt": "Ma'noni tanlang",
                    "options": [],
                }
            ),
        )
        pinyin = mistake(
            2,
            user_answer="hao",
            correct_answer="hǎo",
            material_json=json.dumps(
                {
                    "material_version": 2,
                    "format": "pinyin_choice",
                    "language": "uz",
                    "prompt": "Pinyinni tanlang",
                    "options": [],
                }
            ),
        )
        russian = mistake(
            3,
            user_answer="плохо",
            correct_answer="хорошо",
            material_json=json.dumps(
                {
                    "material_version": 2,
                    "format": "meaning_choice",
                    "language": "ru",
                    "prompt": "Выберите значение",
                    "options": [],
                }
            ),
        )

        questions = {
            item.id: question
            for item, question in self.service._review_questions([meaning, pinyin, russian])
        }

        self.assertEqual(set(questions[1]["options"]), {"xato", "to'g'ri"})
        self.assertNotIn("hǎo", questions[1]["options"])
        self.assertNotIn("хорошо", questions[1]["options"])
        self.assertEqual(questions[1]["format"], "meaning_choice")
        self.assertEqual(questions[1]["language"], "uz")

    async def test_review_uses_shared_training_entitlement(self):
        self.service._items = AsyncMock(return_value=[mistake()])
        self.session.execute = AsyncMock(
            return_value=SimpleNamespace(scalar_one_or_none=lambda: None)
        )
        self.service.access = SimpleNamespace(
            normalize_access_ref=lambda value: value,
            consume_free_use=AsyncMock(return_value={"allowed": True}),
        )
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        with patch(
            "app.services.course_mistake_service.CourseMiniAppAnalyticsService",
            return_value=analytics,
        ):
            result = await self.service.start_review(123, access_ref="review-ref-123")

        self.assertTrue(result["ok"])
        self.assertTrue(result["session"]["id"].startswith("mistake-review:7:v1:"))
        self.service.access.consume_free_use.assert_awaited_once_with(
            self.user,
            feature_key="training_test",
            usage_ref="mistake-review:v1:review-ref-123",
        )
        event_payload = analytics.record_server_event.await_args.kwargs["payload"]
        self.assertEqual(event_payload["mistake_ids"], [1])
        stored_question = event_payload["questions"][0]
        issued_question = result["session"]["questions"][0]
        self.assertEqual(stored_question["id"], issued_question["id"])
        self.assertEqual(stored_question["options"], issued_question["options"])
        self.assertIn("answer_index", stored_question)
        self.assertNotIn("answer_index", issued_question)
        self.assertNotIn("explanation", issued_question)
        self.assertTrue(event_payload["answer_commit_required"])
        self.assertNotIn("source", stored_question)
        self.assertLess(
            self.service._review_started_payload_size(event_payload),
            MAX_EVENT_PAYLOAD_CHARS,
        )

    def test_review_event_snapshot_caps_large_material_without_losing_answer_index(self):
        question = {
            "id": "mistake:1",
            "category": "word",
            "prompt": "问" * 3000,
            "options": ["甲" * 2000, "乙" * 2000, "丙" * 2000, "丁" * 2000],
            "answer_index": 2,
            "explanation": "解释" * 1500,
            "sentence": "句" * 3000,
            "audio_text": "听" * 3000,
            "pinyin": "pīn yīn " * 1000,
            "source": {"kind": "test", "path": "not-needed-in-session"},
        }

        snapshot = self.service._review_session_question(question)
        payload = {
            "question_count": 1,
            "mistake_ids": [1],
            "questions": [snapshot],
            "access_ref": "review-ref-123",
            "ad_supported": False,
        }

        self.assertEqual(snapshot["answer_index"], 2)
        self.assertEqual(len(snapshot["options"]), 4)
        self.assertNotIn("source", snapshot)
        self.assertLess(
            self.service._review_started_payload_size(payload),
            MAX_EVENT_PAYLOAD_CHARS,
        )

    async def test_unreviewable_items_do_not_consume_free_entitlement(self):
        self.service._items = AsyncMock(return_value=[mistake(user_answer=None, correct_answer="对")])
        self.session.execute = AsyncMock(
            return_value=SimpleNamespace(scalar_one_or_none=lambda: None)
        )
        self.service.access = SimpleNamespace(
            normalize_access_ref=lambda value: value,
            consume_free_use=AsyncMock(),
        )

        result = await self.service.start_review(123, access_ref="review-ref-123")

        self.assertEqual(result, {"ok": False, "error": "mistake_review_empty"})
        self.service.access.consume_free_use.assert_not_awaited()

    async def test_ad_supported_review_requires_server_authorization(self):
        self.service._items = AsyncMock(return_value=[mistake()])
        self.session.execute = AsyncMock(
            return_value=SimpleNamespace(scalar_one_or_none=lambda: None)
        )
        self.service.access = SimpleNamespace(
            normalize_access_ref=lambda value: value,
            verify_ad_authorization=AsyncMock(
                return_value={"allowed": False, "error": "ad_authorization_required"}
            ),
            consume_free_use=AsyncMock(),
        )

        result = await self.service.start_review(
            123,
            ad_supported=True,
            access_ref="review-ref-123",
        )

        self.assertEqual(result, {"ok": False, "error": "ad_authorization_required"})
        self.service.access.verify_ad_authorization.assert_awaited_once_with(
            self.user,
            feature_key="mistake_review",
            access_ref="review-ref-123",
        )
        self.service.access.consume_free_use.assert_not_awaited()

    async def test_start_retry_returns_existing_snapshot_before_reconsuming_access(self):
        snapshot = [{"id": "mistake:1", "options": ["错", "对"], "answer_index": 1}]
        event = SimpleNamespace(
            payload_json=json.dumps({"mistake_ids": [1], "questions": snapshot})
        )
        self.session.execute = AsyncMock(
            return_value=SimpleNamespace(scalar_one_or_none=lambda: event)
        )
        self.service._items = AsyncMock()
        self.service.access = SimpleNamespace(
            normalize_access_ref=lambda value: value,
            consume_free_use=AsyncMock(),
        )

        result = await self.service.start_review(123, access_ref="review-ref-123")

        self.assertTrue(result["ok"])
        self.assertTrue(result["duplicate"])
        self.assertEqual(
            result["session"]["questions"],
            [{"id": "mistake:1", "options": ["错", "对"]}],
        )
        self.service._items.assert_not_awaited()
        self.service.access.consume_free_use.assert_not_awaited()

    async def test_answer_is_committed_before_feedback_is_revealed(self):
        snapshot = {
            "id": "mistake:1",
            "options": ["错", "对"],
            "answer_index": 1,
            "explanation": "Original explanation",
        }
        started = SimpleNamespace(
            payload_json=json.dumps(
                {
                    "mistake_ids": [1],
                    "questions": [snapshot],
                    "answer_commit_required": True,
                },
                ensure_ascii=False,
            )
        )
        self.session.execute = AsyncMock(
            side_effect=[
                SimpleNamespace(scalar_one_or_none=lambda: self.user.id),
                SimpleNamespace(scalar_one_or_none=lambda: started),
                SimpleNamespace(scalar_one_or_none=lambda: None),
                SimpleNamespace(scalar_one_or_none=lambda: None),
            ]
        )
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        with patch(
            "app.services.course_mistake_service.CourseMiniAppAnalyticsService",
            return_value=analytics,
        ):
            result = await self.service.answer_review_question(
                123,
                session_id="mistake-review:7:v1:answer-test",
                question_id="mistake:1",
                selected_index=0,
            )

        self.assertTrue(result["ok"])
        self.assertFalse(result["correct"])
        self.assertEqual(result["selected_index"], 0)
        self.assertEqual(result["correct_index"], 1)
        self.assertEqual(result["correct_answer"], "对")
        self.assertEqual(result["explanation"], "Original explanation")
        event_call = analytics.record_server_event.await_args.kwargs
        self.assertEqual(event_call["event_name"], "mistake_review_answered")
        self.assertEqual(event_call["payload"]["selected_index"], 0)
        self.session.commit.assert_awaited_once()

    async def test_answer_retry_cannot_replace_original_choice(self):
        snapshot = {"id": "mistake:1", "options": ["错", "对"], "answer_index": 1}
        started = SimpleNamespace(payload_json=json.dumps({"questions": [snapshot]}))
        answered = SimpleNamespace(
            payload_json=json.dumps(
                {
                    "question_id": "mistake:1",
                    "selected_index": 0,
                    "correct_index": 1,
                    "correct_answer": "对",
                    "explanation": "Explanation",
                },
                ensure_ascii=False,
            )
        )
        self.session.execute = AsyncMock(
            side_effect=[
                SimpleNamespace(scalar_one_or_none=lambda: self.user.id),
                SimpleNamespace(scalar_one_or_none=lambda: started),
                SimpleNamespace(scalar_one_or_none=lambda: None),
                SimpleNamespace(scalar_one_or_none=lambda: answered),
            ]
        )

        result = await self.service.answer_review_question(
            123,
            session_id="mistake-review:7:v1:answer-test",
            question_id="mistake:1",
            selected_index=1,
        )

        self.assertTrue(result["ok"])
        self.assertTrue(result["duplicate"])
        self.assertEqual(result["selected_index"], 0)
        self.assertFalse(result["correct"])

    async def test_completion_uses_committed_answers_not_client_payload(self):
        item = mistake(wrong_count=2, resolved_count=0)
        snapshot = {
            "id": "mistake:1",
            "options": ["错", "对"],
            "answer_index": 1,
        }
        started = SimpleNamespace(
            payload_json=json.dumps(
                {
                    "mistake_ids": [1],
                    "questions": [snapshot],
                    "answer_commit_required": True,
                },
                ensure_ascii=False,
            )
        )
        answered = SimpleNamespace(
            payload_json=json.dumps({"question_id": "mistake:1", "selected_index": 0})
        )
        self.session.execute = AsyncMock(
            side_effect=[
                SimpleNamespace(scalar_one_or_none=lambda: self.user.id),
                SimpleNamespace(scalar_one_or_none=lambda: started),
                SimpleNamespace(scalar_one_or_none=lambda: None),
                SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [item])),
                SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [answered])),
                SimpleNamespace(scalar_one=lambda: 2),
            ]
        )
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        with patch(
            "app.services.course_mistake_service.CourseMiniAppAnalyticsService",
            return_value=analytics,
        ):
            result = await self.service.complete_review(
                123,
                session_id="mistake-review:7:v1:answer-test",
                answers=[{"question_id": "mistake:1", "selected_index": 1}],
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["score"], 0)
        self.assertEqual(item.resolved_count, 0)
        self.service.gamification.award.assert_not_awaited()

    async def test_correct_review_reduces_active_weakness(self):
        item = mistake(wrong_count=2, resolved_count=0)
        question = self.service._legacy_review_question(item, [item.correct_answer])
        started = SimpleNamespace(payload_json='{"mistake_ids":[1]}')
        self.session.execute = AsyncMock(
            side_effect=[
                SimpleNamespace(scalar_one_or_none=lambda: self.user.id),
                SimpleNamespace(scalar_one_or_none=lambda: started),
                SimpleNamespace(scalar_one_or_none=lambda: None),
                SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [item])),
                SimpleNamespace(scalar_one=lambda: 7),
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
        self.assertEqual(result["remaining"], 7)
        self.assertEqual(item.resolved_count, 1)
        self.assertEqual(item.review_count, 1)
        analytics.record_server_event.assert_awaited_once()
        self.service.gamification.award.assert_awaited_once()

    async def test_snapshot_answer_key_is_immutable_and_grants_xp_on_resolution(self):
        item = mistake(wrong_count=2, resolved_count=0, user_answer=None, correct_answer="对")
        snapshot = {
            "id": "mistake:1",
            "category": "word",
            "prompt": "Original prompt",
            "options": ["错", "对"],
            "answer_index": 1,
            "explanation": "Original explanation",
            "material_version": 2,
            "format": "word_choice",
            "source": {"kind": "test", "level": "hsk1", "lesson": 1},
            "sentence": "",
            "audio_text": "",
        }
        started = SimpleNamespace(
            payload_json=json.dumps(
                {"mistake_ids": [1], "questions": [snapshot]},
                ensure_ascii=False,
            )
        )
        self.session.execute = AsyncMock(
            side_effect=[
                SimpleNamespace(scalar_one_or_none=lambda: self.user.id),
                SimpleNamespace(scalar_one_or_none=lambda: started),
                SimpleNamespace(scalar_one_or_none=lambda: None),
                SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [item])),
                SimpleNamespace(scalar_one=lambda: 4),
            ]
        )
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        with patch("app.services.course_mistake_service.CourseMiniAppAnalyticsService", return_value=analytics):
            result = await self.service.complete_review(
                123,
                session_id="mistake-review:7:v1:snapshot",
                answers=[{"question_id": "mistake:1", "selected_index": 1}],
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["remaining"], 4)
        self.assertEqual(item.resolved_count, 1)
        self.service.gamification.award.assert_awaited_once()

    async def test_review_without_new_resolution_returns_zero_xp(self):
        item = mistake(wrong_count=2, resolved_count=0)
        snapshot = self.service._review_question(item, [item.correct_answer])
        incorrect_index = next(
            index for index in range(len(snapshot["options"]))
            if index != snapshot["answer_index"]
        )
        started = SimpleNamespace(
            payload_json=json.dumps(
                {"mistake_ids": [1], "questions": [snapshot]},
                ensure_ascii=False,
            )
        )
        self.session.execute = AsyncMock(
            side_effect=[
                SimpleNamespace(scalar_one_or_none=lambda: self.user.id),
                SimpleNamespace(scalar_one_or_none=lambda: started),
                SimpleNamespace(scalar_one_or_none=lambda: None),
                SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [item])),
                SimpleNamespace(scalar_one=lambda: 2),
            ]
        )
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        with patch("app.services.course_mistake_service.CourseMiniAppAnalyticsService", return_value=analytics):
            result = await self.service.complete_review(
                123,
                session_id="mistake-review:7:v1:no-resolution",
                answers=[{"question_id": "mistake:1", "selected_index": incorrect_index}],
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["reward"]["awarded_xp"], 0)
        self.assertEqual(item.resolved_count, 0)
        self.service.gamification.award.assert_not_awaited()

    async def test_lesson_source_resolution_never_mints_review_xp(self):
        item = mistake(source="lesson", wrong_count=1, resolved_count=0)
        snapshot = self.service._review_question(item, [item.correct_answer])
        started = SimpleNamespace(
            payload_json=json.dumps(
                {"mistake_ids": [1], "questions": [snapshot]},
                ensure_ascii=False,
            )
        )
        self.session.execute = AsyncMock(
            side_effect=[
                SimpleNamespace(scalar_one_or_none=lambda: self.user.id),
                SimpleNamespace(scalar_one_or_none=lambda: started),
                SimpleNamespace(scalar_one_or_none=lambda: None),
                SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [item])),
                SimpleNamespace(scalar_one=lambda: 0),
            ]
        )
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        with patch("app.services.course_mistake_service.CourseMiniAppAnalyticsService", return_value=analytics):
            result = await self.service.complete_review(
                123,
                session_id="mistake-review:7:v1:lesson-source",
                answers=[
                    {
                        "question_id": snapshot["id"],
                        "selected_index": snapshot["answer_index"],
                    }
                ],
            )

        self.assertTrue(result["ok"])
        self.assertEqual(item.resolved_count, 1)
        self.assertEqual(result["reward"]["awarded_xp"], 0)
        self.service.gamification.award.assert_not_awaited()
        payload = analytics.record_server_event.await_args.kwargs["payload"]
        self.assertEqual(payload["resolved"], 1)
        self.assertEqual(payload["reward_eligible_resolved"], 0)

    async def test_record_items_persists_canonical_v2_material(self):
        canonical = CourseLessonMistakeMaterialService.canonicalize_items(
            level="hsk1",
            lesson_order=1,
            lang="uz",
            items=[
                {
                    "material_ref": "lesson:hsk1:1:section:1:card:3",
                    "selected_index": 0,
                }
            ],
        )
        added = []
        session = SimpleNamespace(
            execute=AsyncMock(
                side_effect=[
                    SimpleNamespace(scalar_one_or_none=lambda: self.user.id),
                    SimpleNamespace(scalar_one_or_none=lambda: None),
                    SimpleNamespace(scalar_one_or_none=lambda: None),
                ]
            ),
            add=Mock(side_effect=added.append),
            flush=AsyncMock(),
        )
        service = CourseMistakeService(session)

        recorded = await service.record_items(
            self.user,
            canonical,
            source="lesson",
            level="hsk1",
            lesson_order=1,
        )

        self.assertEqual(recorded, 1)
        self.assertEqual(len(added), 1)
        material = json.loads(added[0].material_json)
        self.assertEqual(material["material_version"], 2)
        self.assertEqual(material["format"], "meaning_guess")
        self.assertEqual(material["language"], "uz")
        self.assertEqual(material["source"]["kind"], "lesson")
        self.assertFalse(material["source"]["trusted"])
        self.assertEqual(material["material_ref"], "lesson:hsk1:1:section:1:card:3")
        self.assertEqual(material["correct_answer"], "sen (birlik)")

    async def test_overview_paginates_filtered_items_but_keeps_global_summary(self):
        first = mistake(1, category="word")
        second = mistake(2, category="word")
        overflow = mistake(3, category="word")
        self.service._items = AsyncMock(return_value=[first, second, overflow])
        self.session.execute = AsyncMock(
            return_value=SimpleNamespace(all=lambda: [("word", 7), ("grammar", 3)])
        )

        result = await self.service.overview(
            123,
            category="word",
            limit=2,
            offset=4,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["total"], 10)
        self.assertEqual(result["summary"]["categories"], {"word": 7, "grammar": 3})
        self.assertEqual(result["filter"], {"category": "word"})
        self.assertEqual(
            result["pagination"],
            {"offset": 4, "limit": 2, "returned": 2, "has_more": True},
        )
        self.assertEqual([item["id"] for item in result["items"]], [1, 2])
        self.service._items.assert_awaited_once_with(
            self.user.id,
            limit=3,
            category="word",
            offset=4,
        )

    async def test_overview_rejects_invalid_filter(self):
        self.service._items = AsyncMock()

        result = await self.service.overview(123, category="unknown")

        self.assertEqual(result, {"ok": False, "error": "invalid_mistake_category"})
        self.service._items.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()

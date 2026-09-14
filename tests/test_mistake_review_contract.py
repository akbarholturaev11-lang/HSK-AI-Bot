import json
import unittest
from types import SimpleNamespace

from app.services.course_mistake_service import CourseMistakeService


def mistake(*, prompt, material, correct_answer="对", user_answer="错", category="pronunciation", source="lesson"):
    return SimpleNamespace(
        id=901,
        category=category,
        source=source,
        level="hsk1",
        lesson_order=1,
        prompt=prompt,
        user_answer=user_answer,
        correct_answer=correct_answer,
        explanation="Explanation",
        material_json=json.dumps(material, ensure_ascii=False),
    )


class MistakeReviewContractTests(unittest.TestCase):
    def test_listening_question_without_audio_is_not_reviewable(self):
        item = mistake(
            prompt="Tinglang va to'g'ri variantni tanlang",
            material={
                "material_version": 2,
                "format": "listening_choice",
                "language": "uz",
                "prompt": "Tinglang va to'g'ri variantni tanlang",
                "sentence": "你好",
                "audio_text": "",
                "options": ["错", "对"],
            },
        )

        self.assertIsNone(CourseMistakeService._review_question(item, []))

    def test_listening_question_with_audio_keeps_audio_and_hides_pinyin(self):
        item = mistake(
            prompt="Tinglang va to'g'ri variantni tanlang",
            material={
                "material_version": 2,
                "format": "listening_choice",
                "language": "uz",
                "prompt": "Tinglang va to'g'ri variantni tanlang",
                "sentence": "",
                "audio_text": "你好",
                "pinyin": "nǐ hǎo",
                "options": ["错", "对"],
            },
        )

        question = CourseMistakeService._review_question(item, [])

        self.assertIsNotNone(question)
        self.assertEqual(question["audio_text"], "你好")
        self.assertEqual(question["pinyin"], "")
        self.assertEqual(question["format"], "listening_choice")

    def test_retry_snapshot_preserves_interaction_contract(self):
        snapshot = CourseMistakeService._review_session_question(
            {
                "id": "mistake:901",
                "category": "pronunciation",
                "prompt": "Tinglang",
                "options": ["错", "对"],
                "answer_index": 1,
                "explanation": "Explanation",
                "material_version": 2,
                "material_ref": "lesson:hsk1:1:section:1:card:1",
                "format": "listening_choice",
                "language": "uz",
                "sentence": "",
                "audio_text": "你好",
                "pinyin": "",
            }
        )

        self.assertEqual(snapshot["material_version"], 2)
        self.assertEqual(snapshot["material_ref"], "lesson:hsk1:1:section:1:card:1")
        self.assertEqual(snapshot["format"], "listening_choice")
        self.assertEqual(snapshot["language"], "uz")
        self.assertEqual(snapshot["audio_text"], "你好")

    def test_sentence_builder_preserves_tokens_without_leaking_answer(self):
        item = mistake(
            category="grammar",
            prompt="To'g'ri gapni tuzing",
            correct_answer="我爱中国",
            user_answer="我中国爱",
            material={
                "material_version": 2,
                "format": "sentence_builder",
                "language": "uz",
                "prompt": "To'g'ri gapni tuzing",
                "tokens": ["中国", "我", "爱"],
                "answer_tokens": ["我", "爱", "中国"],
            },
        )

        question = CourseMistakeService._review_question(item, [])

        self.assertIsNotNone(question)
        self.assertEqual(question["tokens"], ["中国", "我", "爱"])
        self.assertEqual(question["answer_tokens"], ["我", "爱", "中国"])
        snapshot = CourseMistakeService._review_session_question(question)
        self.assertEqual(snapshot["answer_tokens"], ["我", "爱", "中国"])
        public = CourseMistakeService._public_review_question(snapshot)
        self.assertEqual(public["tokens"], ["中国", "我", "爱"])
        self.assertNotIn("answer_tokens", public)
        self.assertNotIn("correct_answer", public)
        self.assertNotIn("answer_index", public)

    def test_sentence_builder_without_exact_token_contract_is_skipped(self):
        item = mistake(
            category="grammar",
            prompt="To'g'ri gapni tuzing",
            correct_answer="我爱中国",
            material={
                "material_version": 2,
                "format": "sentence_builder",
                "language": "uz",
                "prompt": "To'g'ri gapni tuzing",
                "tokens": ["中国", "我", "爱"],
                "answer_tokens": [],
            },
        )

        self.assertIsNone(CourseMistakeService._review_question(item, []))

    def test_pronunciation_is_not_downgraded_to_generic_mcq(self):
        item = mistake(
            category="pronunciation",
            prompt="So'zni to'g'ri talaffuz qiling",
            correct_answer="你好",
            material={
                "material_version": 2,
                "format": "pronunciation_correction",
                "language": "uz",
                "prompt": "So'zni to'g'ri talaffuz qiling",
                "options": ["你好", "你号"],
            },
        )

        self.assertIsNone(CourseMistakeService._review_question(item, []))

    def test_builder_feedback_keeps_sequence_result(self):
        event = SimpleNamespace(
            payload_json=json.dumps(
                {
                    "question_id": "mistake:901",
                    "answer_type": "tokens",
                    "selected_tokens": ["我", "爱", "中国"],
                    "correct": True,
                    "correct_answer": "我爱中国",
                    "explanation": "Explanation",
                },
                ensure_ascii=False,
            )
        )

        feedback = CourseMistakeService._answer_feedback_from_event(event)

        self.assertTrue(feedback["correct"])
        self.assertEqual(feedback["selected_tokens"], ["我", "爱", "中国"])
        self.assertEqual(feedback["correct_answer"], "我爱中国")


if __name__ == "__main__":
    unittest.main()

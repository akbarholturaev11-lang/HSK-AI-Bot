import json
import unittest
from types import SimpleNamespace

from app.services.course_mistake_service import CourseMistakeService


def mistake(*, prompt, material, correct_answer="对", user_answer="错"):
    return SimpleNamespace(
        id=901,
        category="pronunciation",
        source="lesson",
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


if __name__ == "__main__":
    unittest.main()

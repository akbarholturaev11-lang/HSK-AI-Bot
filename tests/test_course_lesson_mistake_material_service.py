import unittest
from pathlib import Path

from app.services.course_lesson_mistake_material_service import (
    CourseLessonMistakeMaterialError,
    CourseLessonMistakeMaterialService,
)


class CourseLessonMistakeMaterialServiceTests(unittest.TestCase):
    def test_lesson_client_sends_only_reference_and_selected_material(self):
        html = Path("app/static/course-v3.html").read_text(encoding="utf-8")

        self.assertIn("function lessonMaterialRef", html)
        self.assertIn("material_ref:String(c._materialRef)", html)
        self.assertIn("selected_tokens:built", html)
        self.assertNotIn("correct_answer:String(correctAnswer", html)
        self.assertNotIn("question:String(prompt", html)

    def test_choice_uses_canonical_source_and_ignores_client_answer_key(self):
        items = CourseLessonMistakeMaterialService.canonicalize_items(
            level="hsk1",
            lesson_order=1,
            lang="uz",
            items=[
                {
                    "material_ref": "lesson:hsk1:1:section:1:card:3",
                    "selected_index": 0,
                    "selected_answer": "siz (rasmiy/hurmat)",
                    "question": "FORGED PROMPT",
                    "correct_answer": "FORGED ANSWER",
                }
            ],
        )

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["question"], "你 so'zining ma'nosini tanlang:")
        self.assertEqual(item["selected_answer"], "siz (rasmiy/hurmat)")
        self.assertEqual(item["correct_answer"], "sen (birlik)")
        self.assertEqual(item["format"], "meaning_guess")
        self.assertEqual(item["category"], "word")
        self.assertEqual(item["language"], "uz")
        self.assertEqual(item["material"]["material_version"], 2)
        self.assertEqual(
            item["material"]["source"],
            {
                "kind": "lesson",
                "trusted": False,
                "level": "hsk1",
                "lesson": 1,
                "section": 1,
                "card": 3,
                "material_ref": "lesson:hsk1:1:section:1:card:3",
                "source_schema_version": 2,
            },
        )

    def test_correct_forged_and_out_of_lesson_answers_are_ignored(self):
        items = CourseLessonMistakeMaterialService.canonicalize_items(
            level="hsk1",
            lesson_order=1,
            lang="uz",
            items=[
                {
                    "material_ref": "lesson:hsk1:1:section:1:card:3",
                    "selected_index": 2,
                    "selected_answer": "sen (birlik)",
                },
                {
                    "material_ref": "lesson:hsk1:1:section:1:card:3",
                    "selected_answer": "not in canonical options",
                },
                {
                    "material_ref": "lesson:hsk1:2:section:1:card:3",
                    "selected_index": 0,
                },
            ],
        )

        self.assertEqual(items, [])

    def test_builder_validates_tokens_and_derives_chinese_sentence(self):
        items = CourseLessonMistakeMaterialService.canonicalize_items(
            level="hsk1",
            lesson_order=1,
            lang="ru",
            items=[
                {
                    "material_ref": "lesson:hsk1:1:section:3:card:1",
                    "selected_tokens": ["好", "你"],
                },
                {
                    "material_ref": "lesson:hsk1:1:section:3:card:1",
                    "selected_tokens": ["坏", "你"],
                },
            ],
        )

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["selected_answer"], "好 你")
        self.assertEqual(item["correct_answer"], "你 好")
        self.assertEqual(item["question"], "Привет!")
        self.assertEqual(item["sentence"], "你好")
        self.assertEqual(item["material"]["translation"], "Привет!")
        self.assertEqual(item["material"]["answer_tokens"], ["你", "好"])

    def test_reverse_builder_persists_pinyin_language_and_source(self):
        items = CourseLessonMistakeMaterialService.canonicalize_items(
            level="hsk1",
            lesson_order=1,
            lang="tj",
            items=[
                {
                    "material_ref": "lesson:hsk1:1:section:3:card:3",
                    "selected_tokens": ["Салом", "навишта", "мешавад", "nǐ", "hǎo"],
                }
            ],
        )

        self.assertEqual(len(items), 1)
        material = items[0]["material"]
        self.assertEqual(material["language"], "tj")
        self.assertEqual(material["sentence"], "你好")
        self.assertEqual(material["pinyin"], "nī hǎo → nǐ hǎo")
        self.assertEqual(material["source"]["section"], 3)

    def test_missing_lesson_material_raises_a_bounded_error(self):
        with self.assertRaises(CourseLessonMistakeMaterialError):
            CourseLessonMistakeMaterialService.canonicalize_items(
                level="hsk1",
                lesson_order=999,
                lang="uz",
                items=[],
            )


if __name__ == "__main__":
    unittest.main()

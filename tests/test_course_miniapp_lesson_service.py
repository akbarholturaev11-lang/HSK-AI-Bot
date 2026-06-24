import unittest
from types import SimpleNamespace

from app.services.course_miniapp_lesson_service import CourseMiniAppLessonService


class CourseMiniAppLessonServiceQuizTests(unittest.TestCase):
    def test_word_quiz_questions_do_not_emit_generic_fill_blank(self):
        service = CourseMiniAppLessonService(SimpleNamespace())
        vocab = [
            {"zh": "对不起", "pinyin": "duibuqi", "meaning": "kechirasiz"},
            {"zh": "你好", "pinyin": "nihao", "meaning": "salom"},
            {"zh": "谢谢", "pinyin": "xiexie", "meaning": "rahmat"},
            {"zh": "再见", "pinyin": "zaijian", "meaning": "xayr"},
        ]

        questions = service._word_quiz_questions(vocab, 1, "uz")
        flattened = str(questions)

        self.assertNotIn("fill_blank", {question["type"] for question in questions})
        self.assertNotIn("Men bugun", flattened)
        self.assertNotIn("so'zini o'rgandim", flattened)

    def test_interactive_fill_blank_uses_real_sentence_context(self):
        service = CourseMiniAppLessonService(SimpleNamespace())
        vocab = [
            {"zh": "喝茶", "pinyin": "hecha", "meaning": "choy ichmoq"},
            {"zh": "看书", "pinyin": "kanshu", "meaning": "kitob o'qimoq"},
            {"zh": "买东西", "pinyin": "mai dongxi", "meaning": "narsa sotib olmoq"},
        ]
        grammar = [
            {
                "examples": [
                    {
                        "zh": "我喜欢喝茶。",
                        "translation": "Men choy ichishni yaxshi ko'raman.",
                    }
                ]
            }
        ]

        questions = service._interactive_quiz_questions(vocab, grammar, grammar, 1, "uz")
        fill = next(question for question in questions if question["type"] == "fill_blank_choice")

        self.assertEqual(fill["sentence"], "我喜欢____。")
        self.assertIn("喝茶", fill["opts"])
        self.assertEqual(fill["opts"][fill["ans"]], "喝茶")
        self.assertNotIn("Men bugun", str(fill))


if __name__ == "__main__":
    unittest.main()

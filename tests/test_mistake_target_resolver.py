"""Xatolarim v3: har manbadagi xatodan nishon (so'z/gap) ajratish."""

import glob
import json
import unittest
from collections import Counter

from app.services.course_lesson_mistake_material_service import CourseLessonMistakeMaterialService as Lessons
from app.services.course_miniapp_practice_service import CourseMiniAppPracticeService as Practice
from app.services.course_mistake_service import CourseMistakeService
from app.services.course_question_material import canonicalize_hsk_exam_material
from app.services.mistake_target_resolver import resolve_target


def voice(correction, said, category="grammar"):
    return resolve_target(
        category=category,
        source="voice",
        material={"prompt": said, "correct_answer": correction},
        prompt=said,
        correct_answer=correction,
        user_answer=said,
        explanation=correction,
        level="hsk1",
        language="uz",
    )


class LessonCoverageTests(unittest.TestCase):
    def test_almost_every_lesson_card_mistake_resolves_to_a_target(self):
        stats = Counter()
        for path in sorted(glob.glob("app/static/course_v3_data/hsk*/lesson_*.json")):
            data = json.load(open(path, encoding="utf-8"))
            level, order = data["level"], int(data["lesson_id"])
            for ref, entry in Lessons._card_lookup(data, level, order).items():
                card = entry["card"]
                card_type = card.get("type")
                raw = {"material_ref": ref}
                if card_type in {"sentence_builder", "reverse_builder"}:
                    answer = Lessons._localized_list(card.get("answer_tokens"), "uz")
                    if len(answer) < 2:
                        continue
                    raw["selected_tokens"] = list(reversed(answer))
                elif card_type == "match_pairs":
                    raw.update(selected_left_index=0, selected_right_index=1)
                elif "options" in card and "correct_index" in card:
                    raw["selected_index"] = (int(card["correct_index"]) + 1) % len(card["options"])
                else:
                    continue
                items = Lessons.canonicalize_items(level=level, lesson_order=order, lang="uz", items=[raw])
                if not items:
                    continue
                item = items[0]
                target = resolve_target(
                    category=item["category"],
                    source="lesson",
                    material=item["material"],
                    prompt=item["question"],
                    correct_answer=item["correct_answer"],
                    user_answer=item["selected_answer"],
                    explanation=item["explanation"],
                    level=level,
                    language="uz",
                )
                stats["resolved" if target else "missing"] += 1
        total = stats["resolved"] + stats["missing"]
        self.assertGreater(total, 3000)
        # Qolganlari lug'atdan ataylab chiqarilgan ismlar (李月, 小明) —
        # ular eski savol sifatida bitta formatda qaytadi.
        self.assertGreaterEqual(stats["resolved"] / total, 0.98, stats)

    def test_listening_card_target_is_the_heard_word(self):
        items = Lessons.canonicalize_items(
            level="hsk1",
            lesson_order=1,
            lang="uz",
            items=[{"material_ref": ref, "selected_index": 0} for ref in self._refs_of("listening_choice")[:1]],
        )
        item = items[0]
        target = resolve_target(
            category=item["category"], source="lesson", material=item["material"],
            prompt=item["question"], correct_answer=item["correct_answer"],
            user_answer=item["selected_answer"], explanation=item["explanation"],
            level="hsk1", language="uz",
        )
        self.assertEqual(target["zh"], item["material"]["audio_text"])

    @staticmethod
    def _refs_of(card_type):
        data = json.load(open("app/static/course_v3_data/hsk1/lesson_01.json", encoding="utf-8"))
        return [
            ref
            for ref, entry in Lessons._card_lookup(data, "hsk1", 1).items()
            if entry["card"].get("type") == card_type and int(entry["card"].get("correct_index", 0)) != 0
        ]


class ExamCoverageTests(unittest.TestCase):
    def test_every_exam_question_resolves(self):
        missing = []
        for level in ("hsk1", "hsk2", "hsk3", "hsk4"):
            raw = json.load(open(f"app/static/course_v3_data/exams/{level}.json", encoding="utf-8"))
            material = canonicalize_hsk_exam_material(raw, level=level, lang="ru", source_path="exam")
            for question in material["questions"]:
                answer = question["answer_index"]
                options = question["options"]
                option_material = question["option_materials"][answer]
                category = CourseMistakeService._category(
                    {"type": question["format"], "subtype": question["section"]}, "test"
                )
                target = resolve_target(
                    category=category,
                    source="test",
                    material={
                        "format": question["format"],
                        "language": "ru",
                        "prompt": question["prompt"],
                        "sentence": question["sentence"],
                        "audio_text": question["audio_text"],
                        "pinyin": option_material.get("pinyin", ""),
                        "translation": option_material.get("translation", ""),
                        "options": options,
                        "correct_answer": options[answer],
                    },
                    prompt=question["prompt"],
                    correct_answer=options[answer],
                    user_answer=options[(answer + 1) % len(options)],
                    explanation=question["explanation"],
                    level=level,
                    language="ru",
                )
                if not target:
                    missing.append(question["id"])
        self.assertEqual(missing, [])


class SourceTests(unittest.TestCase):
    def test_voice_correction_keeps_the_learners_wrong_sentence(self):
        target = voice("我是学生。", "我是学生吗")
        self.assertEqual((target["kind"], target["zh"]), ("sentence", "我是学生。"))
        self.assertEqual(target["payload"]["wrong"], ["我是学生吗"])

    def test_voice_correction_with_lead_in_or_explanation(self):
        self.assertEqual(voice("应该说：我是学生。", "我是学生吗")["zh"], "我是学生。")
        self.assertEqual(voice("Use 很: 他很高。", "他高")["zh"], "他很高。")
        self.assertEqual(voice("Say 我是学生 not 我是学生吗", "我是学生吗")["zh"], "我是学生")

    def test_voice_correction_equal_to_what_was_said_is_not_a_mistake(self):
        self.assertIsNone(voice("我去学校。", "我去学校。"))

    def test_training_listening_target_is_the_word_not_a_visible_sentence(self):
        data = json.load(open("app/static/course_v3_data/hsk1/lesson_01.json", encoding="utf-8"))
        card = next(
            card
            for section in data["sections"]
            for card in section["cards"]
            if card["type"] == "listening_choice"
        )
        question = Practice._static_card_question(
            card, level="hsk1", lesson_order=1, section_no=1, card_index=1, question_index=1
        )
        answer = question["options"][question["answer_index"]]
        target = resolve_target(
            category="word", source="training",
            material={**question, "correct_answer": answer, "language": "uz"},
            prompt=question["prompt"], correct_answer=answer,
            user_answer=question["options"][(question["answer_index"] + 1) % len(question["options"])],
            explanation=question["explanation"], level="hsk1", language="uz",
        )
        self.assertEqual((target["kind"], target["zh"]), ("word", card["audio_text"]))

    def test_match_pairs_target_is_the_left_word(self):
        target = resolve_target(
            category="word", source="lesson",
            material={"format": "match_pairs", "correct_answer": "你 → sen (birlik)"},
            prompt="你 → ?", correct_answer="你 → sen (birlik)", user_answer="你 → yaxshi",
            explanation="", level="hsk1", language="uz",
        )
        self.assertEqual((target["kind"], target["zh"]), ("word", "你"))

    def test_pronunciation_drill_target_is_the_practised_word(self):
        target = resolve_target(
            category="pronunciation", source="pronunciation",
            material={"format": "pronunciation_correction", "audio_text": "你好", "pinyin": "nǐ hǎo"},
            prompt="你好 (nǐ hǎo)", correct_answer="你好", user_answer="你号",
            explanation="nǐ hǎo", level="hsk1", language="uz",
        )
        self.assertEqual((target["kind"], target["zh"]), ("word", "你好"))

    def test_meaning_answer_resolves_through_the_prompt_word(self):
        target = resolve_target(
            category="word", source="lesson",
            material={"format": "meaning_guess", "prompt": "你 so'zining ma'nosini tanlang:"},
            prompt="你 so'zining ma'nosini tanlang:", correct_answer="sen (birlik)",
            user_answer="yaxshi", explanation="你 = sen (birlik) (nǐ)", level="hsk1", language="uz",
        )
        self.assertEqual(target["zh"], "你")


if __name__ == "__main__":
    unittest.main()

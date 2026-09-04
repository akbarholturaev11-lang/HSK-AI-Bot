"""Mijoz boshqaradigan mashqlarning xatosi server lug'atidan qayta quriladi.

"Ieroglif tanish" va "Yodlash" o'z savollarini o'zi quradi va o'z ekran
dizayniga ega, shuning uchun umumiy MCQ dvigatelidan foydalanmaydi. Lekin
natijasi yo'qolmasligi kerak — aks holda `character` zaifligi faqat
darslardan to'planadi.

Ishonch chegarasi: mijoz FAQAT xato bo'lgan ieroglifni aytadi. Savol matni
ham, to'g'ri javob ham serverning o'z lug'atidan (`course_v3_vocab`)
quriladi, ya'ni soxta xato yozib bo'lmaydi.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.course_drill_signal_service import CourseDrillSignalService
from app.services.course_v3_vocab import words_for_level


class BuildItemsTests(unittest.TestCase):
    def test_question_and_answer_come_from_the_server_dictionary(self):
        items = CourseDrillSignalService.build_items(
            level="hsk1",
            language="uz",
            entries=[{"hanzi": "你", "selected": "好"}],
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["correct_answer"], "你")
        self.assertEqual(items[0]["selected_answer"], "好")
        self.assertEqual(items[0]["category"], "character")
        self.assertIn("nǐ", items[0]["question"])

    def test_a_character_the_server_does_not_know_is_dropped(self):
        # Mijoz o'ylab topgan xato yozilmaydi.
        items = CourseDrillSignalService.build_items(
            level="hsk1",
            language="uz",
            entries=[{"hanzi": "ZZZ"}, {"hanzi": "🙂"}, {"hanzi": ""}],
        )

        self.assertEqual(items, [])

    def test_client_cannot_dictate_the_prompt_or_the_correct_answer(self):
        items = CourseDrillSignalService.build_items(
            level="hsk1",
            language="uz",
            entries=[
                {
                    "hanzi": "你",
                    "selected": "<script>alert(1)</script>",
                }
            ],
        )

        self.assertEqual(items[0]["correct_answer"], "你")
        self.assertNotIn("script", items[0]["question"])

    def test_repeated_characters_are_recorded_once(self):
        items = CourseDrillSignalService.build_items(
            level="hsk1",
            language="uz",
            entries=[{"hanzi": "你"}, {"hanzi": "你"}, {"hanzi": "好"}],
        )

        self.assertEqual([item["correct_answer"] for item in items], ["你", "好"])

    def test_lower_levels_stay_verifiable_for_an_advanced_learner(self):
        # Mashq quyi darajadagi so'zlarni ham beradi; ular "topilmadi" deb
        # tashlanmasligi kerak.
        items = CourseDrillSignalService.build_items(
            level="hsk3",
            language="ru",
            entries=[{"hanzi": "你"}],
        )

        self.assertEqual(len(items), 1)

    def test_a_higher_level_word_is_not_accepted_from_a_beginner(self):
        hsk1 = {word["zh"] for word in words_for_level("hsk1")}
        hsk4_only = next(
            word["zh"] for word in words_for_level("hsk4") if word["zh"] not in hsk1
        )

        items = CourseDrillSignalService.build_items(
            level="hsk1", language="uz", entries=[{"hanzi": hsk4_only}]
        )

        self.assertEqual(items, [])

    def test_unknown_language_falls_back_instead_of_failing(self):
        items = CourseDrillSignalService.build_items(
            level="hsk1", language="en", entries=[{"hanzi": "你"}]
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["language"], "ru")

    def test_a_flood_of_entries_is_capped(self):
        items = CourseDrillSignalService.build_items(
            level="hsk4",
            language="uz",
            entries=[{"hanzi": "你"}] * 500,
        )

        self.assertLessEqual(len(items), 20)


class RecordTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _service(recorder):
        item = CourseDrillSignalService(SimpleNamespace())
        return item, patch(
            "app.services.course_drill_signal_service.CourseMistakeService",
            MagicMock(return_value=SimpleNamespace(record_items=recorder)),
        )

    async def test_records_verified_items_under_the_feature_name(self):
        recorder = AsyncMock(return_value=1)
        service, patcher = self._service(recorder)
        with patcher:
            recorded = await service.record(
                SimpleNamespace(id=3),
                feature="recognition",
                level="hsk1",
                language="uz",
                entries=[{"hanzi": "你"}],
            )

        self.assertEqual(recorded, 1)
        self.assertEqual(recorder.await_args.kwargs["source"], "recognition")
        self.assertEqual(recorder.await_args.kwargs["level"], "hsk1")

    async def test_unknown_feature_is_rejected(self):
        service, patcher = self._service(AsyncMock())
        with patcher, self.assertRaises(ValueError):
            await service.record(
                SimpleNamespace(id=3),
                feature="voice",
                level="hsk1",
                language="uz",
                entries=[{"hanzi": "你"}],
            )

    async def test_nothing_verifiable_means_no_write(self):
        recorder = AsyncMock()
        service, patcher = self._service(recorder)
        with patcher:
            recorded = await service.record(
                SimpleNamespace(id=3),
                feature="recognition",
                level="hsk1",
                language="uz",
                entries=[{"hanzi": "ZZZ"}],
            )

        self.assertEqual(recorded, 0)
        recorder.assert_not_awaited()

    async def test_a_write_failure_never_breaks_the_exercise(self):
        recorder = AsyncMock(side_effect=RuntimeError("db down"))
        service, patcher = self._service(recorder)
        with patcher:
            recorded = await service.record(
                SimpleNamespace(id=3),
                feature="recognition",
                level="hsk1",
                language="uz",
                entries=[{"hanzi": "你"}],
            )

        self.assertEqual(recorded, 0)


if __name__ == "__main__":
    unittest.main()

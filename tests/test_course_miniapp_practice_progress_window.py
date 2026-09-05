"""Mashq savollari o'quvchi O'RGANGAN qismlar bilan cheklanishi.

Ilgari `start()` progress oynasini umuman uzatmasdi va savollar butun daraja
bo'ylab, hali ochilmagan darslardan ham kelardi. Bundan tashqari `max_lesson`
parametri ikki xil ma'noda ishlatilardi: DB banki DARSLIK darsi tartibida,
statik bank esa flat QISM raqamida. Endi chaqiruvchilar bitta bir ma'noli
qiymat — joriy qism — uzatadi, konvertatsiya bank ichida bo'ladi.
"""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.course_miniapp_practice_service import CourseMiniAppPracticeService
from app.services.course_v3_parts import source_lesson_for_part


def service(*, db_lessons=None, payloads=None) -> CourseMiniAppPracticeService:
    item = CourseMiniAppPracticeService(SimpleNamespace(commit=AsyncMock()))
    lessons = [
        SimpleNamespace(id=order, lesson_order=order, level="hsk1")
        for order in (db_lessons or [])
    ]
    item.lesson_repo = SimpleNamespace(list_by_level=AsyncMock(return_value=lessons))
    item.lesson_service = SimpleNamespace(
        get_payload=AsyncMock(return_value=payloads if payloads is not None else {})
    )
    return item


class StaticBankPartWindowTests(unittest.IsolatedAsyncioTestCase):
    async def test_questions_stay_inside_the_learned_parts(self):
        questions = await service()._level_questions("hsk1", "uz", 10, max_part=3)

        self.assertTrue(questions)
        self.assertTrue(all(int(item["lesson"]) <= 3 for item in questions))

    async def test_without_a_window_the_bank_reaches_unlearned_parts(self):
        # Chegara qo'yilmaganda eski xatti-harakat saqlanadi — ya'ni yuqoridagi
        # test haqiqatan filtrni tekshirmoqda, tasodifni emas.
        questions = await service()._level_questions("hsk1", "uz", 10)

        self.assertTrue(any(int(item["lesson"]) > 3 for item in questions))

    async def test_first_part_learner_only_sees_the_first_part(self):
        questions = await service()._level_questions("hsk1", "uz", 10, max_part=1)

        self.assertTrue(questions)
        self.assertTrue(all(int(item["lesson"]) == 1 for item in questions))


class DatabaseBankConversionTests(unittest.IsolatedAsyncioTestCase):
    async def test_flat_part_is_converted_to_the_textbook_lesson(self):
        # 13-qism HSK1 ning 4-darslik darsiga tegishli. DB banki darslik
        # darslari tartibida ishlaydi, shuning uchun 1..4 so'ralishi kerak.
        self.assertEqual(source_lesson_for_part("hsk1", 13), 4)
        item = service(db_lessons=list(range(1, 16)))

        await item._level_questions("hsk1", "uz", 10, max_part=13)

        asked = sorted(
            call.kwargs["lesson_order"] for call in item.lesson_service.get_payload.await_args_list
        )
        self.assertEqual(asked, [1, 2, 3, 4])

    async def test_static_bank_keeps_the_flat_part_number(self):
        # Ayni qiymat statik bankka konvertatsiyasiz borishi kerak: u yerda
        # lesson_NN.json = flat QISM. Konvertatsiya qilinsa 13-qismdagi
        # o'quvchi faqat 1-4 qismlarni ko'rardi.
        item = service(db_lessons=[])

        questions = await item._level_questions("hsk1", "uz", 10, max_part=13)

        self.assertTrue(any(int(entry["lesson"]) > 4 for entry in questions))
        self.assertTrue(all(int(entry["lesson"]) <= 13 for entry in questions))


class CurrentPartTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _with_progress(progress):
        repo = MagicMock()
        repo.return_value = SimpleNamespace(get_by_user_id=AsyncMock(return_value=progress))
        return patch(
            "app.services.course_miniapp_practice_service.CourseProgressRepository",
            repo,
        )

    async def test_current_part_is_completed_plus_one(self):
        progress = SimpleNamespace(level="hsk1", completed_lessons_count=12)
        with self._with_progress(progress):
            self.assertEqual(await service()._current_part(SimpleNamespace(id=1), "hsk1"), 13)

    async def test_fresh_learner_starts_at_part_one(self):
        progress = SimpleNamespace(level="hsk1", completed_lessons_count=0)
        with self._with_progress(progress):
            self.assertEqual(await service()._current_part(SimpleNamespace(id=1), "hsk1"), 1)

    async def test_progress_from_another_band_does_not_restrict_the_bank(self):
        progress = SimpleNamespace(level="hsk2", completed_lessons_count=40)
        with self._with_progress(progress):
            self.assertIsNone(await service()._current_part(SimpleNamespace(id=1), "hsk1"))

    async def test_missing_progress_does_not_restrict_the_bank(self):
        with self._with_progress(None):
            self.assertIsNone(await service()._current_part(SimpleNamespace(id=1), "hsk1"))

    async def test_hsk4_bands_normalise_to_the_same_bank(self):
        progress = SimpleNamespace(level="hsk4b", completed_lessons_count=100)
        with self._with_progress(progress):
            self.assertEqual(await service()._current_part(SimpleNamespace(id=1), "hsk4"), 101)


class StartAppliesTheWindowTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_limits_the_bank_and_records_the_window(self):
        # Asl nuqson shu edi: `start()` progress oynasini UMUMAN uzatmasdi,
        # ya'ni o'quvchi hali ochmagan darslardan savol olardi.
        item = CourseMiniAppPracticeService(SimpleNamespace(commit=AsyncMock()))
        user = SimpleNamespace(id=5, telegram_id=123, status="trial", payment_status="none", end_date=None)
        item.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
        item.access = SimpleNamespace(consume_daily_use=AsyncMock(return_value={"allowed": True}))
        item._questions = AsyncMock(return_value=[{"id": "q1"}])
        item._current_part = AsyncMock(return_value=13)
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))

        with patch(
            "app.services.course_miniapp_practice_service.CourseMiniAppAnalyticsService",
            return_value=analytics,
        ):
            result = await item.start(123, mode="training", level="hsk1", lang="uz", skill="listening")

        self.assertTrue(result["ok"])
        self.assertEqual(item._questions.await_args.kwargs["max_part"], 13)
        self.assertEqual(
            analytics.record_server_event.await_args.kwargs["payload"]["max_part"], 13
        )


class StartedWindowIsReusedOnCompleteTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _service_with_started_event(payload):
        item = CourseMiniAppPracticeService(SimpleNamespace(execute=AsyncMock()))
        result = MagicMock()
        result.scalars.return_value.first.return_value = (
            json.dumps(payload) if payload is not None else None
        )
        item.session.execute.return_value = result
        return item

    async def test_window_recorded_at_start_is_read_back(self):
        item = self._service_with_started_event({"mode": "training", "max_part": 13})

        max_part = await item._started_max_part(SimpleNamespace(id=1), "practice:1:x", "training")

        self.assertEqual(max_part, 13)

    async def test_legacy_session_without_a_window_returns_none(self):
        # Deploy paytida ochiq turgan eski sessiyalar yakunlanishi kerak:
        # None -> chaqiruvchi joriy qismdan qayta hisoblaydi.
        item = self._service_with_started_event({"mode": "mock"})

        self.assertIsNone(
            await item._started_max_part(SimpleNamespace(id=1), "practice:1:x", "mock")
        )

    async def test_missing_event_returns_none(self):
        item = self._service_with_started_event(None)

        self.assertIsNone(
            await item._started_max_part(SimpleNamespace(id=1), "practice:1:x", "mock")
        )


if __name__ == "__main__":
    unittest.main()

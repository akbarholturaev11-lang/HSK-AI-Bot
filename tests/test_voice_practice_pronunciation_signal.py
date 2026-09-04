"""Yiqilgan talaffuz urinishi Xatolarim bo'limiga tushishi.

Talaffuz mashqi ilgari ham SERVERDA baholanardi, lekin natija hech qayerga
yozilmasdi: o'quvchi bir so'zni o'nlab marta noto'g'ri aytsa ham "Xatolarim"
bo'sh qolardi va kunlik reja uning talaffuz zaifligini ko'rmasdi.

Ball serverda hisoblangani uchun bu yozuv ishonchli — mijoz uni soxtalashtira
olmaydi (mijoz faqat audio yuboradi).
"""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.course_mistake_service import TRUSTED_MISTAKE_REWARD_SOURCES
from app.services.voice_practice_service import (
    PRONOUNCE_PASS_SCORE,
    VoicePracticeService,
)


def service(user=SimpleNamespace(id=7, telegram_id=123)):
    item = VoicePracticeService(SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock()))
    item.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
    return item


def mistake_service_patch(recorder):
    return patch(
        "app.services.voice_practice_service.CourseMistakeService",
        MagicMock(return_value=SimpleNamespace(record_items=recorder)),
    )


class PronunciationMistakeTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_attempt_is_written_as_a_pronunciation_mistake(self):
        recorder = AsyncMock(return_value=1)
        item = service()
        with mistake_service_patch(recorder):
            await item._record_pronunciation_mistake(
                123,
                target="谢谢",
                target_pinyin="xièxie",
                heard="些些",
                score=30,
                level="hsk1",
            )

        recorder.assert_awaited_once()
        items = recorder.await_args.args[1]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["correct_answer"], "谢谢")
        self.assertEqual(items[0]["selected_answer"], "些些")
        self.assertEqual(items[0]["category"], "pronunciation")
        self.assertEqual(recorder.await_args.kwargs["source"], "pronunciation")
        self.assertEqual(recorder.await_args.kwargs["level"], "hsk1")

    async def test_the_prompt_keeps_the_pinyin_so_review_is_answerable(self):
        recorder = AsyncMock(return_value=1)
        with mistake_service_patch(recorder):
            await service()._record_pronunciation_mistake(
                123, target="好", target_pinyin="hǎo", heard="", score=10, level="hsk1"
            )

        self.assertEqual(recorder.await_args.args[1][0]["question"], "好 (hǎo)")

    async def test_unknown_user_is_ignored_quietly(self):
        recorder = AsyncMock()
        item = service(user=None)
        with mistake_service_patch(recorder):
            await item._record_pronunciation_mistake(
                123, target="好", target_pinyin="", heard="", score=10, level="hsk1"
            )

        recorder.assert_not_awaited()

    async def test_a_write_failure_never_breaks_the_exercise(self):
        # O'quvchi baribir o'z ballini ko'rishi kerak: signal yozuvi
        # yiqilsa ham talaffuz mashqi ishlayveradi.
        recorder = AsyncMock(side_effect=RuntimeError("db down"))
        item = service()
        with mistake_service_patch(recorder):
            await item._record_pronunciation_mistake(
                123, target="好", target_pinyin="", heard="", score=10, level="hsk1"
            )

        item.session.rollback.assert_awaited()


class PronunciationTrustTests(unittest.TestCase):
    def test_pronunciation_counts_as_a_server_verified_source(self):
        # Ball serverda hisoblanadi, shuning uchun uni tuzatish XP beradi.
        self.assertIn("pronunciation", TRUSTED_MISTAKE_REWARD_SOURCES)

    def test_pass_threshold_is_shared_with_the_client(self):
        # course_v3_pronunciation.html ham 60 dan foydalanadi.
        self.assertEqual(PRONOUNCE_PASS_SCORE, 60)


if __name__ == "__main__":
    unittest.main()

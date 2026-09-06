"""Suhbat yakunidagi HAQIQIY o'lchovlar va xato kategoriyasi.

Ilgari yakunda faqat "yaxshi N / xato N" chiqardi, xatolar esa hammasi
talaffuz deb yozilardi. Bu yerda ikkalasi ham qadalgan:

1. o'lchovlar QO'SHIMCHA AI chaqiruvisiz, saqlangan tarixdan hisoblanadi;
2. har bir xato AI bergan turga (`error_type`) qarab kategoriyaga tushadi;
3. tur bo'lmagan ESKI yozuvlarda `category` umuman berilmaydi, ya'ni
   `CourseMistakeService` ning `source == "voice"` fallback'i eski
   xatti-harakatni saqlaydi.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.voice_practice_service import (
    MAX_DIALOGS_PER_SESSION,
    VoicePracticeService,
)


def _session_item(history, turn_count=None):
    return SimpleNamespace(
        id="sess-1",
        status="active",
        level="hsk1",
        lesson_id=55,
        language="ru",
        history=history,
        corrections=[],
        turn_count=len(history) if turn_count is None else turn_count,
        started_at=None,
        ended_at=None,
        target_words=[{"zh": "医院"}, {"zh": "便宜"}],
        review_words=[{"zh": "谢谢"}],
    )


async def _end(history, *, turn_count=None, user=SimpleNamespace(id=7, telegram_id=123)):
    """`end_session` ni chaqirib, (natija, record_items chaqiruvi, award) qaytaradi."""
    from datetime import datetime, timezone

    item = _session_item(history, turn_count)
    item.started_at = datetime.now(timezone.utc)
    service = VoicePracticeService(SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock()))
    service._get_active_session = AsyncMock(return_value=item)
    service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
    recorder = AsyncMock(return_value=0)
    award = AsyncMock(return_value={"xp_awarded": 10})
    with patch(
        "app.services.voice_practice_service.CourseMistakeService",
        MagicMock(return_value=SimpleNamespace(record_items=recorder)),
    ), patch(
        "app.services.voice_practice_service.CourseGamificationService",
        MagicMock(return_value=SimpleNamespace(award=award)),
    ):
        result = await service.end_session(123, "sess-1")
    return result, recorder, award


GOOD = {"user": "我去医院", "assistant": "好的", "correction": None, "error_type": "none"}
GRAMMAR = {
    "user": "我昨天去北京",
    "assistant": "是吗",
    "correction": "我昨天去了北京",
    "error_type": "grammar",
}
WORD = {"user": "很便易", "assistant": "对", "correction": "很便宜", "error_type": "word"}
LEGACY = {"user": "谢谢你", "assistant": "不客气", "correction": "谢谢您"}  # error_type YO'Q


class VoiceEvaluationTests(unittest.IsolatedAsyncioTestCase):
    async def test_mistakes_are_counted_by_type(self):
        result, _, _ = await _end([GOOD, GRAMMAR, WORD])
        self.assertEqual(1, result["errors_by_type"]["grammar"])
        self.assertEqual(1, result["errors_by_type"]["word"])
        self.assertEqual(0, result["errors_by_type"]["pronunciation"])
        self.assertEqual(1, result["good_count"])
        self.assertEqual(2, result["mistake_count"])

    async def test_target_word_usage_is_measured_without_an_ai_call(self):
        # 医院 (maqsad) va 谢谢 (takror) aytilgan, 便宜 aytilmagan.
        result, _, _ = await _end([GOOD, LEGACY])
        self.assertEqual({"医院", "谢谢"}, set(result["target_used"]["words"]))
        self.assertEqual(2, result["target_used"]["used"])
        self.assertEqual(3, result["target_used"]["total"])

    async def test_average_length_and_completion_are_reported(self):
        result, _, _ = await _end([GOOD, GRAMMAR])
        # "我去医院" = 4 belgi, "我昨天去北京" = 6 belgi.
        self.assertEqual(5.0, result["avg_chars"])
        self.assertEqual(2, result["turns"])
        self.assertFalse(result["completed"])

    async def test_a_full_session_is_marked_completed(self):
        result, _, _ = await _end([GOOD], turn_count=MAX_DIALOGS_PER_SESSION)
        self.assertTrue(result["completed"])

    async def test_each_mistake_carries_its_own_category(self):
        _, recorder, _ = await _end([GRAMMAR, WORD])
        items = recorder.await_args.args[1]
        self.assertEqual(["grammar", "word"], [i["category"] for i in items])
        # `source` butun partiya uchun bitta bo'lib qoladi.
        self.assertEqual("voice", recorder.await_args.kwargs["source"])

    async def test_an_old_entry_without_a_type_gets_no_category(self):
        # `category` berilmasa CourseMistakeService voice fallback'ini ishlatadi.
        _, recorder, _ = await _end([LEGACY])
        items = recorder.await_args.args[1]
        self.assertNotIn("category", items[0])

    async def test_voice_mistakes_never_claim_a_language(self):
        # Aks holda to'liq jumlalar word_choice distraktor havzasiga aralashadi.
        _, recorder, _ = await _end([GRAMMAR])
        self.assertNotIn("language", recorder.await_args.args[1][0])

    async def test_a_session_with_no_speech_awards_nothing(self):
        # Ochib-yopish 10 XP + streak + kunlik reja vazifasini bermasligi kerak.
        result, recorder, award = await _end([], turn_count=0)
        award.assert_not_awaited()
        recorder.assert_not_awaited()
        self.assertIsNone(result["reward"])

    async def test_a_real_conversation_still_awards_xp(self):
        _, _, award = await _end([GOOD])
        award.assert_awaited_once()

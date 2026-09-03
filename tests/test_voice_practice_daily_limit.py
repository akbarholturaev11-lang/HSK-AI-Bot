"""AI Voice's free limit: once per DAY, not once per lifetime.

Until this change a free learner who opened a single AI Voice session could
never open another one — the count was filtered by "today" only for paying
users. These tests pin the new rule and the reset instant every client shows.
"""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services import course_daily_window
from app.services.voice_practice_service import (
    FREE_TOTAL_SESSIONS,
    VoicePracticeService,
)


def _service(paid: bool, used: int, offset_minutes: int = 0):
    service = VoicePracticeService(SimpleNamespace())
    user = SimpleNamespace(id=7, telegram_id=123, level="hsk1", language="ru")
    service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
    service._is_paid = staticmethod(lambda _user: paid)
    service._session_count = AsyncMock(return_value=used)
    service._offset_minutes = AsyncMock(return_value=offset_minutes)
    return service


class FreeVoiceLimitTests(unittest.IsolatedAsyncioTestCase):

    async def test_a_free_learner_is_counted_for_today_only(self):
        # The whole point: yesterday's session must not still block today.
        service = _service(paid=False, used=0)
        with patch(
            "app.services.voice_practice_service.CourseProgressRepository"
        ) as repo:
            repo.return_value.get_by_user_id = AsyncMock(return_value=None)
            await service.user_status(123)
        service._session_count.assert_awaited_once_with(123, today_only=True)

    async def test_a_paying_learner_is_also_counted_for_today(self):
        service = _service(paid=True, used=3)
        with patch(
            "app.services.voice_practice_service.CourseProgressRepository"
        ) as repo:
            repo.return_value.get_by_user_id = AsyncMock(return_value=None)
            status = await service.user_status(123)
        service._session_count.assert_awaited_once_with(123, today_only=True)
        self.assertEqual(-1, status["remaining_voice_limit"])

    async def test_one_free_session_a_day_is_left_after_using_none(self):
        service = _service(paid=False, used=0)
        with patch(
            "app.services.voice_practice_service.CourseProgressRepository"
        ) as repo:
            repo.return_value.get_by_user_id = AsyncMock(return_value=None)
            status = await service.user_status(123)
        self.assertEqual(FREE_TOTAL_SESSIONS, status["remaining_voice_limit"])

    async def test_the_free_session_used_today_blocks_until_the_reset(self):
        service = _service(paid=False, used=FREE_TOTAL_SESSIONS)
        with patch(
            "app.services.voice_practice_service.CourseProgressRepository"
        ) as repo:
            repo.return_value.get_by_user_id = AsyncMock(return_value=None)
            status = await service.user_status(123)
        self.assertEqual(0, status["remaining_voice_limit"])
        self.assertIsNotNone(status["reset_at"])


class ResetInstantTests(unittest.IsolatedAsyncioTestCase):

    async def test_a_free_learner_is_told_when_the_limit_reopens(self):
        service = _service(paid=False, used=1, offset_minutes=300)
        with patch(
            "app.services.voice_practice_service.CourseProgressRepository"
        ) as repo:
            repo.return_value.get_by_user_id = AsyncMock(return_value=None)
            status = await service.user_status(123)
        reset = datetime.fromisoformat(status["reset_at"])
        now = datetime.now(timezone.utc)
        self.assertGreater(reset, now)
        self.assertLessEqual(reset - now, timedelta(days=1))
        # The learner's own midnight, not the server's.
        self.assertEqual(course_daily_window.next_day_reset(300), reset)

    async def test_a_paying_learner_has_no_reset_because_there_is_no_limit(self):
        service = _service(paid=True, used=9)
        with patch(
            "app.services.voice_practice_service.CourseProgressRepository"
        ) as repo:
            repo.return_value.get_by_user_id = AsyncMock(return_value=None)
            status = await service.user_status(123)
        self.assertIsNone(status["reset_at"])


class SharedWindowTests(unittest.TestCase):

    def test_voice_uses_the_same_window_as_the_course_limits(self):
        # If these drift apart a learner's two limits reopen at different
        # times on the same evening, which reads as a bug to them.
        self.assertEqual(
            course_daily_window.day_start(300),
            VoicePracticeService._day_start(300),
        )


if __name__ == "__main__":
    unittest.main()

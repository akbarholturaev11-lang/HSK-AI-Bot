"""AI Voice's free limit: once per DAY, not once per lifetime.

Until this change a free learner who opened a single AI Voice session could
never open another one — the count was filtered by "today" only for paying
users. These tests pin the new rule and the reset instant every client shows.
"""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.user import User
from app.db.models.voice_practice_session import VoicePracticeSession
from app.services import course_daily_window
from app.services.entitlements import actions as A
from app.services.entitlements.limits_config import LimitConfigService
from app.services.voice_practice_service import (
    FREE_TOTAL_SESSIONS,
    VoicePracticeService,
)


class _VoiceLimitCase(unittest.IsolatedAsyncioTestCase):
    """Haqiqiy baza ustida: hisob endi dvigateldan, chegara admin sozlamasidan.

    `_session_count` ni mock qilib bo'lmaydi — dvigatel gapirilgan sessiyalarni
    o'zi sanaydi, va aynan shu hisob barcha klientlarda bir xil.
    """

    async def asyncSetUp(self):
        self.db = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.db.dispose()

    async def _status(self, *, paid, spoken_today=0, spoken_yesterday=0,
                      offset_minutes=0, limit=FREE_TOTAL_SESSIONS):
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            user = User(
                id=7, telegram_id=123, full_name="Voice", language="ru", level="hsk1",
                status="active" if paid else "free",
                payment_status="approved" if paid else "none",
                end_date=now + timedelta(days=7) if paid else None,
                created_at=now, last_active_at=now,
            )
            session.add(user)
            await session.flush()
            session.add(CourseMiniAppProfile(
                user_id=7, goal="hsk_exam", daily_minutes=20, start_mode="lesson_1",
                timezone_offset_minutes=offset_minutes,
            ))
            config = LimitConfigService(session)
            payload = (await config.get_config()).public_payload()
            payload["plans"]["FREE"][A.SPEAKING_SESSION] = {"limit": limit, "window": "daily"}
            await config.save_config(payload)
            for index in range(spoken_today):
                session.add(VoicePracticeSession(
                    id=f"today-{index}", user_telegram_id=123, role="friend", level="hsk1",
                    language="ru", voice="female", turn_count=2, started_at=now,
                ))
            for index in range(spoken_yesterday):
                session.add(VoicePracticeSession(
                    id=f"yesterday-{index}", user_telegram_id=123, role="friend", level="hsk1",
                    language="ru", voice="female", turn_count=2,
                    started_at=now - timedelta(days=2),
                ))
            await session.commit()

            service = VoicePracticeService(session)
            with patch(
                "app.services.voice_practice_service.CourseProgressRepository"
            ) as repo:
                repo.return_value.get_by_user_id = AsyncMock(return_value=None)
                return await service.user_status(123)


class FreeVoiceLimitTests(_VoiceLimitCase):

    async def test_a_free_learner_is_counted_for_today_only(self):
        # The whole point: yesterday's session must not still block today.
        status = await self._status(paid=False, spoken_yesterday=3)

        self.assertEqual(FREE_TOTAL_SESSIONS, status["remaining_voice_limit"])

    async def test_a_paying_learner_has_no_limit_at_all(self):
        status = await self._status(paid=True, spoken_today=3)

        self.assertEqual(-1, status["remaining_voice_limit"])

    async def test_one_free_session_a_day_is_left_after_using_none(self):
        status = await self._status(paid=False)

        self.assertEqual(FREE_TOTAL_SESSIONS, status["remaining_voice_limit"])

    async def test_the_free_session_used_today_blocks_until_the_reset(self):
        status = await self._status(paid=False, spoken_today=FREE_TOTAL_SESSIONS)

        self.assertEqual(0, status["remaining_voice_limit"])
        self.assertIsNotNone(status["reset_at"])

    async def test_the_admin_setting_is_what_the_learner_gets(self):
        status = await self._status(paid=False, spoken_today=1, limit=3)

        self.assertEqual(2, status["remaining_voice_limit"])
        self.assertIn("3", status["limit_status"]["limit_text"])


class ResetInstantTests(_VoiceLimitCase):

    async def test_a_free_learner_is_told_when_the_limit_reopens(self):
        status = await self._status(paid=False, spoken_today=1, offset_minutes=300)

        reset = datetime.fromisoformat(status["reset_at"])
        now = datetime.now(timezone.utc)
        self.assertGreater(reset, now)
        self.assertLessEqual(reset - now, timedelta(days=1))
        # The learner's own midnight, not the server's.
        self.assertEqual(course_daily_window.next_day_reset(300), reset)

    async def test_a_paying_learner_has_no_reset_because_there_is_no_limit(self):
        status = await self._status(paid=True, spoken_today=9)

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


class FreeSlotIsSpentOnSpeechTests(unittest.IsolatedAsyncioTestCase):
    """Bepul slot QATOR yaratilganda emas, GAPIRILGANDA yonadi.

    Ilgari sessiya qatori yaratilishi kifoya edi: AI xato bersa, mikrofonga
    ruxsat berilmasa yoki tarmoq uzilsa ham bepul o'quvchi kunlik yagona
    suhbatidan ayrilardi.
    """

    async def test_only_sessions_with_speech_are_counted(self):
        captured = {}

        async def execute(query):
            captured["sql"] = str(query)
            return SimpleNamespace(scalar_one=lambda: 0)

        service = VoicePracticeService(SimpleNamespace(execute=execute))
        service._offset_minutes = AsyncMock(return_value=0)
        await service._session_count(123, today_only=True)
        self.assertIn("turn_count >", captured["sql"])

    async def test_a_second_start_reuses_the_untouched_row(self):
        """Aks holda start tugmasini qayta bosish cheksiz qator yaratardi.

        `_session_count` endi gapirilmagan qatorni sanamaydi, shuning uchun
        qatorni qayta ishlatish kunlik bittaga cheklovchi yagona narsa.
        """
        existing = SimpleNamespace(
            id="already-open",
            role="friend",
            level="hsk1",
            language="ru",
            voice="female",
            status="active",
            turn_count=0,
            history=[],
            corrections=[],
            lesson_id=None,
            target_words=[],
            review_words=[],
            plan_json={},
            ended_at=None,
        )
        session = SimpleNamespace(added=[], commit=AsyncMock())
        session.add = lambda item: session.added.append(item)
        service = VoicePracticeService(session)
        user = SimpleNamespace(id=7, telegram_id=123)
        service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
        service.user_status = AsyncMock(
            return_value={"is_paid": False, "plan": "free", "remaining_voice_limit": 1}
        )
        service._offset_minutes = AsyncMock(return_value=0)
        service._retire_stale_sessions = AsyncMock()
        service._reusable_session = AsyncMock(return_value=existing)
        service._course_context = AsyncMock(
            return_value={"lesson_id": None, "lesson_order": None, "title": "", "words": [], "review_words": []}
        )
        service._learner_plan = AsyncMock(return_value={})

        result = await service.start_session(
            123, role="teacher_li", level="hsk1", language="ru", voice="male"
        )

        self.assertEqual("already-open", result["session_id"])
        self.assertFalse(session.added, "gapirilmagan qator uchun yangi qator yaratilmasligi kerak")
        self.assertEqual("teacher_li", existing.role)
        self.assertEqual("active", existing.status)

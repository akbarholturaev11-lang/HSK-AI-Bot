"""The Course daily-limit window as the access service exposes it.

The pure window maths lives in ``test_course_daily_window``. What this file
pins is the service surface every client depends on: with an unknown timezone
the window is still UTC midnight — the behaviour every existing user has —
and with a real offset it follows the learner's own day.
"""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy.exc import IntegrityError

from app.services import course_daily_window
from app.services.course_miniapp_access_service import CourseMiniAppAccessService


def _at(hour: int, minute: int = 0, day: int = 15) -> datetime:
    return datetime(2026, 9, day, hour, minute, tzinfo=timezone.utc)


class DailyResetWindowTests(unittest.TestCase):

    def _with_hour(self, hour):
        return patch.object(course_daily_window, "reset_hour_local", lambda: hour)

    def test_an_unknown_timezone_is_still_utc_midnight(self):
        # The behaviour every existing user already has. If this fails, the
        # setting moved someone's limit without anyone asking for it.
        with self._with_hour(0):
            self.assertEqual(_at(0), CourseMiniAppAccessService._day_start(_at(0, 0)))
            self.assertEqual(_at(0), CourseMiniAppAccessService._day_start(_at(9, 30)))
            self.assertEqual(_at(0), CourseMiniAppAccessService._day_start(_at(23, 59)))

    def test_the_default_next_reset_is_the_following_midnight(self):
        with self._with_hour(0):
            self.assertEqual(
                _at(0, day=16),
                CourseMiniAppAccessService.next_daily_reset(_at(9, 30)),
            )

    def test_a_learner_timezone_moves_the_window_to_their_own_day(self):
        # UTC+5 (Toshkent): local midnight is 19:00 UTC the day before. Before
        # this change such a learner's limit reopened at 05:00 local time.
        with self._with_hour(0):
            self.assertEqual(
                _at(19, day=14),
                CourseMiniAppAccessService._day_start(_at(3, 0), offset_minutes=300),
            )
            self.assertEqual(
                _at(19, day=15),
                CourseMiniAppAccessService.next_daily_reset(_at(3, 0), offset_minutes=300),
            )

    def test_a_configured_hour_moves_the_window(self):
        with self._with_hour(6):
            # Before the reset hour the learner is still in yesterday's window.
            self.assertEqual(
                _at(6, day=14),
                CourseMiniAppAccessService._day_start(_at(5, 59)),
            )
            # From the reset hour the new window has started.
            self.assertEqual(_at(6), CourseMiniAppAccessService._day_start(_at(6, 0)))
            self.assertEqual(_at(6), CourseMiniAppAccessService._day_start(_at(23, 0)))

    def test_next_reset_is_always_ahead_and_within_a_day(self):
        for hour in range(24):
            with self._with_hour(hour):
                for probe in range(24):
                    for offset in (-300, 0, 300, 840):
                        now = _at(probe, 17)
                        reset = CourseMiniAppAccessService.next_daily_reset(
                            now, offset_minutes=offset
                        )
                        self.assertGreater(reset, now, f"h={hour} p={probe} o={offset}")
                        self.assertLessEqual(reset - now, timedelta(days=1))

    def test_a_broken_setting_falls_back_instead_of_breaking_limits(self):
        for bad in (-1, 24, 99, None, "six"):
            with self.subTest(value=bad):
                with patch("app.config.settings") as fake:
                    fake.COURSE_DAILY_RESET_HOUR_LOCAL = bad
                    self.assertEqual(0, CourseMiniAppAccessService.daily_reset_hour_local())

    def test_a_valid_setting_is_read(self):
        with patch("app.config.settings") as fake:
            fake.COURSE_DAILY_RESET_HOUR_LOCAL = 6
            self.assertEqual(6, CourseMiniAppAccessService.daily_reset_hour_local())

    def test_the_shipped_default_is_the_unchanged_one(self):
        from app.config import Settings

        self.assertEqual(0, Settings().COURSE_DAILY_RESET_HOUR_LOCAL)


class _RaceResult:
    """Bitta `execute()` javobi: qulflangan user yoki bo'sh natija."""

    def __init__(self, value=None):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _NestedTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _RaceSession:
    """Ikkinchi so'rov shu slotni egallab ulgurgan sessiya.

    `flush()` `IntegrityError` tashlaydi — ya'ni `consume_daily_use` qayta
    sanash yo'liga tushadi. Bizni qiziqtirgani shu yo'l.
    """

    def __init__(self, locked_user):
        self._locked_user = locked_user
        self.added = []

    async def execute(self, _statement):
        # Birinchi (va yagona kerakli) so'rov — user qulfi.
        return _RaceResult(self._locked_user)

    def begin_nested(self):
        return _NestedTransaction()

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        raise IntegrityError("insert", {}, Exception("duplicate"))


class DailyLimitRaceWindowTests(unittest.IsolatedAsyncioTestCase):
    """Poyga yo'lidagi qayta sanash ham o'quvchining kunida bo'lishi kerak.

    Ilgari `consume_daily_use` ning `IntegrityError` tarmog'i `_daily_used_today`
    ni `offset_minutes` siz chaqirardi. Natijada parallel so'rov paytida UTC+5
    o'quvchi UTC oynasi bo'yicha qayta sanalardi: bir xil chaqiruv asosiy yo'lda
    bir javob, poyga yo'lida boshqa javob berardi.
    """

    async def _run_race(self, *, offset_minutes: int, counts):
        user = SimpleNamespace(
            id=7,
            telegram_id=777,
            status="free",
            payment_status="none",
            end_date=None,
        )
        service = CourseMiniAppAccessService(_RaceSession(user))
        seen = []

        async def _spy(telegram_id, feature_key, *, lifetime=False, offset_minutes=0):
            seen.append(offset_minutes)
            return counts[len(seen) - 1]

        with patch.object(service, "_daily_used_today", _spy), patch.object(
            service, "_learner_offset_minutes", AsyncMock(return_value=offset_minutes)
        ):
            # `limit_override` — bu aynan markaziy dvigatel yuboradigan yo'l.
            # Usiz chaqiruv admin sozlamasini o'qiydigan yangi tarmoqqa ketadi va
            # bu yerdagi soxta sessiya bilan poyga yo'li umuman sinalmaydi.
            result = await service.consume_daily_use(
                user, feature_key="recognition", limit_override=1
            )
        return result, seen

    async def test_the_race_recount_uses_the_learner_window(self):
        # Ikkinchi sanash limitni to'lgan deb ko'rsatadi, ya'ni qayta sanash
        # haqiqatan ham chaqirilgan — va u ham UTC+5 oynasida bo'lishi shart.
        result, seen = await self._run_race(offset_minutes=300, counts=[0, 1])

        self.assertEqual([300, 300], seen)
        self.assertFalse(result["allowed"])
        self.assertEqual("free_feature_limit_reached", result["error"])

    async def test_an_unknown_timezone_still_counts_in_utc(self):
        # Mintaqasi noma'lum o'quvchi uchun xatti-harakat o'zgarmaydi.
        _, seen = await self._run_race(offset_minutes=0, counts=[0, 1])

        self.assertEqual([0, 0], seen)


if __name__ == "__main__":
    unittest.main()

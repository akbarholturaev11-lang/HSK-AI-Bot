"""The Course daily-limit window as the access service exposes it.

The pure window maths lives in ``test_course_daily_window``. What this file
pins is the service surface every client depends on: with an unknown timezone
the window is still UTC midnight — the behaviour every existing user has —
and with a real offset it follows the learner's own day.
"""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()

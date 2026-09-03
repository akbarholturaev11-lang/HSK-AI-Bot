"""Kunlik limit oynasi o'quvchining vaqt mintaqasida.

Bu oyna hamma klientning bepul limiti qachon ochilishini belgilaydi, shuning
uchun eng qattiq qadalgan narsa — mintaqasi noma'lum (0) o'quvchi uchun
xatti-harakat eski holida qolishi.
"""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.services import course_daily_window as window


def _utc(hour: int, minute: int = 0, day: int = 15) -> datetime:
    return datetime(2026, 9, day, hour, minute, tzinfo=timezone.utc)


class OffsetNormalizationTests(unittest.TestCase):

    def test_real_offsets_pass_through(self):
        self.assertEqual(0, window.normalize_offset_minutes(0))
        self.assertEqual(300, window.normalize_offset_minutes(300))
        self.assertEqual(-240, window.normalize_offset_minutes(-240))

    def test_nonsense_is_clamped_instead_of_breaking_the_window(self):
        # The offset comes from a client, so it is not trusted.
        self.assertEqual(0, window.normalize_offset_minutes(None))
        self.assertEqual(0, window.normalize_offset_minutes("five"))
        self.assertEqual(840, window.normalize_offset_minutes(99_999))
        self.assertEqual(-720, window.normalize_offset_minutes(-99_999))


class DayStartTests(unittest.TestCase):

    def test_an_unknown_timezone_keeps_the_old_utc_behaviour(self):
        # Offset 0 with the default reset hour is exactly UTC midnight, which
        # is what every client did before this module existed.
        self.assertEqual(_utc(0), window.day_start(0, _utc(0, 0)))
        self.assertEqual(_utc(0), window.day_start(0, _utc(9, 30)))
        self.assertEqual(_utc(0), window.day_start(0, _utc(23, 59)))

    def test_utc_plus_five_resets_at_local_midnight(self):
        # UTC+5: local midnight is 19:00 UTC the previous day. Before this
        # change such a learner's limit reopened at 05:00 local time.
        offset = 300
        self.assertEqual(_utc(19, day=14), window.day_start(offset, _utc(19, 0, day=14)))
        self.assertEqual(_utc(19, day=14), window.day_start(offset, _utc(3, 0, day=15)))
        self.assertEqual(_utc(19, day=14), window.day_start(offset, _utc(18, 59, day=15)))
        # 19:00 UTC starts the learner's next local day.
        self.assertEqual(_utc(19, day=15), window.day_start(offset, _utc(19, 0, day=15)))

    def test_a_negative_offset_works_the_same_way(self):
        offset = -300  # UTC-5: local midnight is 05:00 UTC.
        self.assertEqual(_utc(5), window.day_start(offset, _utc(5, 0)))
        self.assertEqual(_utc(5), window.day_start(offset, _utc(23, 0)))
        self.assertEqual(_utc(5, day=14), window.day_start(offset, _utc(4, 59)))

    def test_a_configured_local_hour_moves_the_window(self):
        with patch.object(window, "reset_hour_local", lambda: 6):
            # UTC+5, reset at 06:00 local = 01:00 UTC.
            self.assertEqual(_utc(1), window.day_start(300, _utc(1, 0)))
            self.assertEqual(_utc(1, day=14), window.day_start(300, _utc(0, 59)))


class NextResetTests(unittest.TestCase):

    def test_the_next_reset_is_a_day_after_the_window_start(self):
        self.assertEqual(_utc(0, day=16), window.next_day_reset(0, _utc(9, 30)))
        self.assertEqual(_utc(19, day=15), window.next_day_reset(300, _utc(3, 0, day=15)))

    def test_the_next_reset_is_always_ahead_and_within_a_day(self):
        for offset in (-720, -300, 0, 210, 300, 840):
            for hour in range(24):
                now = _utc(hour, 17)
                reset = window.next_day_reset(offset, now)
                self.assertGreater(reset, now, f"offset={offset} hour={hour}")
                self.assertLessEqual(reset - now, timedelta(days=1))


class DayKeyTests(unittest.TestCase):

    def test_the_key_is_the_learner_local_date(self):
        # 03:00 UTC is still the 15th for UTC+5, and already the 15th for UTC.
        self.assertEqual("2026-09-15", window.local_day_key(0, _utc(3, 0)))
        self.assertEqual("2026-09-15", window.local_day_key(300, _utc(3, 0)))

    def test_the_key_is_stable_across_one_local_day(self):
        # Same local day for UTC+5 spans two UTC dates; the key must not flip
        # inside it, or an idempotent retry would consume a second slot.
        offset = 300
        keys = {
            window.local_day_key(offset, _utc(19, 30, day=14)),
            window.local_day_key(offset, _utc(23, 59, day=14)),
            window.local_day_key(offset, _utc(0, 1, day=15)),
            window.local_day_key(offset, _utc(18, 59, day=15)),
        }
        self.assertEqual(1, len(keys), keys)

    def test_the_key_changes_when_the_local_day_does(self):
        offset = 300
        self.assertNotEqual(
            window.local_day_key(offset, _utc(18, 59, day=15)),
            window.local_day_key(offset, _utc(19, 1, day=15)),
        )


class ResetHourSettingTests(unittest.TestCase):

    def test_a_broken_setting_falls_back_to_midnight(self):
        for bad in (-1, 24, 99, None, "six"):
            with self.subTest(value=bad):
                with patch("app.config.settings") as fake:
                    fake.COURSE_DAILY_RESET_HOUR_LOCAL = bad
                    self.assertEqual(0, window.reset_hour_local())

    def test_a_valid_setting_is_read(self):
        with patch("app.config.settings") as fake:
            fake.COURSE_DAILY_RESET_HOUR_LOCAL = 6
            self.assertEqual(6, window.reset_hour_local())

    def test_the_shipped_default_is_local_midnight(self):
        from app.config import Settings

        self.assertEqual(0, Settings().COURSE_DAILY_RESET_HOUR_LOCAL)


if __name__ == "__main__":
    unittest.main()

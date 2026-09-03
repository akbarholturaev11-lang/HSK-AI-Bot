"""When the learner is told their limit is running out, and when they are not.

Two limits behave differently and the difference is the point of this file:
the lesson allowance never comes back, so it warns before the wall; the daily
allowance returns tomorrow, so it only speaks once it is spent.
"""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.limit_notification_service import (
    LimitNotificationService,
    lesson_stage,
    lesson_warning_threshold,
)


class LessonWarningThresholdTests(unittest.TestCase):

    def test_a_single_free_part_has_no_almost_there_moment(self):
        # With one free part the learner goes from "untouched" to "spent".
        # Warning at 0 completed would fire before they had done anything.
        self.assertIsNone(lesson_warning_threshold(1))
        self.assertIsNone(lesson_warning_threshold(0))
        self.assertIsNone(lesson_warning_threshold(-3))
        self.assertIsNone(lesson_warning_threshold(None))
        self.assertIsNone(lesson_warning_threshold("six"))

    def test_a_small_allowance_warns_one_part_before_the_end(self):
        # 90% of 6 rounds up to 6, which is the same as spent — useless as a
        # warning. The threshold is capped at "one part left".
        self.assertEqual(1, lesson_warning_threshold(2))
        self.assertEqual(5, lesson_warning_threshold(6))

    def test_a_large_allowance_warns_at_ninety_percent(self):
        self.assertEqual(18, lesson_warning_threshold(20))
        self.assertEqual(9, lesson_warning_threshold(10))

    def test_the_warning_always_comes_before_the_end(self):
        for free in range(2, 60):
            with self.subTest(free=free):
                threshold = lesson_warning_threshold(free)
                self.assertIsNotNone(threshold)
                self.assertGreater(threshold, 0, free)
                self.assertLess(threshold, free, free)


class LessonStageTests(unittest.TestCase):

    def test_nothing_is_said_early_on(self):
        self.assertIsNone(lesson_stage(0, 6))
        self.assertIsNone(lesson_stage(4, 6))

    def test_the_warning_stage_is_the_last_free_part(self):
        self.assertEqual("warning", lesson_stage(5, 6))

    def test_the_spent_stage_starts_at_the_allowance(self):
        self.assertEqual("spent", lesson_stage(6, 6))
        # Past the allowance is still spent, not silence.
        self.assertEqual("spent", lesson_stage(9, 6))

    def test_a_one_part_allowance_only_ever_reports_spent(self):
        self.assertIsNone(lesson_stage(0, 1))
        self.assertEqual("spent", lesson_stage(1, 1))

    def test_an_unknown_allowance_says_nothing_rather_than_guessing(self):
        self.assertIsNone(lesson_stage(3, 0))
        self.assertIsNone(lesson_stage(3, None))
        self.assertIsNone(lesson_stage("three", 6))


class ResetClockTests(unittest.TestCase):

    def test_the_hour_is_the_learner_own(self):
        clock = LimitNotificationService._local_clock
        # 19:00 UTC is local midnight for UTC+5.
        self.assertEqual("00:00", clock("2026-09-15T19:00:00+00:00", 300))
        self.assertEqual("22:00", clock("2026-09-15T19:00:00+00:00", 180))
        self.assertEqual("19:00", clock("2026-09-15T19:00:00+00:00", 0))

    def test_a_naive_instant_is_read_as_utc(self):
        clock = LimitNotificationService._local_clock
        self.assertEqual("00:00", clock("2026-09-15T19:00:00", 300))

    def test_nothing_readable_shows_no_hour_instead_of_a_wrong_one(self):
        clock = LimitNotificationService._local_clock
        for value in (None, "", "tomorrow", "10:00"):
            with self.subTest(value=value):
                self.assertIsNone(clock(value, 300))


class DeliveryTests(unittest.IsolatedAsyncioTestCase):

    def _service(self, recorded: bool):
        service = LimitNotificationService(SimpleNamespace())
        self.record = AsyncMock(return_value=recorded)
        return service

    async def _run(self, recorded: bool, bot):
        service = self._service(recorded)
        with patch(
            "app.services.limit_notification_service.CourseNotificationService"
        ) as notifications:
            notifications.return_value.record = self.record
            return await service.lesson_progress(
                SimpleNamespace(id=1, telegram_id=99, language="uz"),
                level="hsk1",
                completed_parts=6,
                free_parts=6,
                bot=bot,
            )

    async def test_a_first_crossing_is_sent(self):
        bot = SimpleNamespace(send_message=AsyncMock())
        self.assertEqual("spent", await self._run(True, bot))
        bot.send_message.assert_awaited_once()

    async def test_the_same_crossing_is_never_sent_twice(self):
        # The feed row is what dedupes: if it was already written, the learner
        # has already been told and must not be told again.
        bot = SimpleNamespace(send_message=AsyncMock())
        self.assertIsNone(await self._run(False, bot))
        bot.send_message.assert_not_awaited()

    async def test_a_blocked_chat_does_not_break_the_lesson(self):
        bot = SimpleNamespace(send_message=AsyncMock(side_effect=RuntimeError("blocked")))
        self.assertEqual("spent", await self._run(True, bot))

    async def test_without_a_bot_the_feed_still_gets_the_notice(self):
        self.assertEqual("spent", await self._run(True, None))
        self.record.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()

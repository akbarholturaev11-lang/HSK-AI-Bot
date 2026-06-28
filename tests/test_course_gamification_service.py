import unittest
from datetime import date, datetime, timezone

from app.services.course_gamification_service import CourseGamificationService


class CourseGamificationServiceTests(unittest.TestCase):
    def test_league_thresholds(self):
        self.assertEqual(CourseGamificationService.league_for_xp(0), "Bronze")
        self.assertEqual(CourseGamificationService.league_for_xp(500), "Silver")
        self.assertEqual(CourseGamificationService.league_for_xp(1500), "Gold")
        self.assertEqual(CourseGamificationService.league_for_xp(3000), "Sapphire")

    def test_streak_only_advances_once_per_day(self):
        day = date(2026, 6, 23)
        self.assertEqual(CourseGamificationService.next_streak(day, 4, day), (4, False))
        self.assertEqual(CourseGamificationService.next_streak(date(2026, 6, 22), 4, day), (5, True))
        self.assertEqual(CourseGamificationService.next_streak(date(2026, 6, 20), 4, day), (1, True))

    def test_week_starts_on_monday(self):
        self.assertEqual(CourseGamificationService._week_start(date(2026, 6, 25)), date(2026, 6, 22))

    def test_weekly_reset_countdown_uses_next_monday_midnight(self):
        reset_at, seconds = CourseGamificationService._weekly_reset(
            0,
            datetime(2026, 6, 28, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(reset_at, "2026-06-29T00:00:00+00:00")
        self.assertEqual(seconds, 12 * 60 * 60)


if __name__ == "__main__":
    unittest.main()

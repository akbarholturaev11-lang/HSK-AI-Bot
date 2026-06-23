import unittest
from datetime import date

from app.services.course_gamification_service import CourseGamificationService


class CourseGamificationServiceTests(unittest.TestCase):
    def test_league_thresholds(self):
        self.assertEqual(CourseGamificationService.league_for_xp(0), "Bronze")
        self.assertEqual(CourseGamificationService.league_for_xp(500), "Silver")
        self.assertEqual(CourseGamificationService.league_for_xp(3000), "Diamond")
        self.assertEqual(CourseGamificationService.league_for_xp(8000), "Legend")

    def test_streak_only_advances_once_per_day(self):
        day = date(2026, 6, 23)
        self.assertEqual(CourseGamificationService.next_streak(day, 4, day), (4, False))
        self.assertEqual(CourseGamificationService.next_streak(date(2026, 6, 22), 4, day), (5, True))
        self.assertEqual(CourseGamificationService.next_streak(date(2026, 6, 20), 4, day), (1, True))

    def test_week_starts_on_monday(self):
        self.assertEqual(CourseGamificationService._week_start(date(2026, 6, 25)), date(2026, 6, 22))


if __name__ == "__main__":
    unittest.main()

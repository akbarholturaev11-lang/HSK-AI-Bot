import unittest

from app.services.course_miniapp_admin_analytics_service import (
    CourseMiniAppAdminAnalyticsService,
    LessonDropoffRow,
)


class CourseMiniAppAdminAnalyticsServiceTests(unittest.TestCase):
    def test_pct_handles_zero_denominator(self):
        self.assertEqual(CourseMiniAppAdminAnalyticsService._pct(3, 0), 0.0)
        self.assertEqual(CourseMiniAppAdminAnalyticsService._pct(3, 4), 75.0)

    def test_format_lesson_dropoff_orders_largest_gap_first(self):
        rows = [
            LessonDropoffRow(level="hsk1", lesson_order=1, started=10, completed=9),
            LessonDropoffRow(level="hsk2", lesson_order=3, started=15, completed=5),
        ]

        text = CourseMiniAppAdminAnalyticsService.format_lesson_dropoff(rows)

        self.assertTrue(text.startswith("HSK2-3"))
        self.assertIn("15", text)
        self.assertIn("5", text)

    def test_format_lesson_dropoff_empty(self):
        self.assertEqual(CourseMiniAppAdminAnalyticsService.format_lesson_dropoff([]), "hali yo'q")


if __name__ == "__main__":
    unittest.main()

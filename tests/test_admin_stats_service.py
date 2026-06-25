import unittest

from app.services.admin_stats_service import miniapp_course_stats


class _ScalarResult:
    def __init__(self, value: int):
        self.value = value

    def scalar(self) -> int:
        return self.value


class _Session:
    def __init__(self, values: list[int]):
        self.values = list(values)
        self.execute_count = 0

    async def execute(self, _stmt):
        self.execute_count += 1
        return _ScalarResult(self.values.pop(0))


class AdminStatsServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_miniapp_course_stats_uses_event_based_counts(self):
        session = _Session([12, 9, 5, 24, 4])

        stats = await miniapp_course_stats(session)

        self.assertEqual(stats.opened_users, 12)
        self.assertEqual(stats.lesson_users, 9)
        self.assertEqual(stats.completed_users, 5)
        self.assertEqual(stats.completed_sections, 24)
        self.assertEqual(stats.completed_book_lessons, 4)
        self.assertEqual(session.execute_count, 5)


if __name__ == "__main__":
    unittest.main()

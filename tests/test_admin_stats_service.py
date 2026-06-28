import unittest
from types import SimpleNamespace

from app.services.admin_stats_service import miniapp_course_stats
from app.services.admin_miniapp_service import AdminMiniAppService


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


class AdminMiniAppServiceTests(unittest.TestCase):
    def test_monitor_chart_uses_real_payload_bars(self):
        course_stats = SimpleNamespace(
            opened_users=12,
            lesson_users=8,
            completed_users=5,
            completed_sections=20,
            completed_book_lessons=4,
        )

        monitor = AdminMiniAppService._monitor(
            active_week=9,
            active_24h=4,
            pending_payments=2,
            approved_total_text="99 TJS",
            miniapp_course=course_stats,
            ad_summary={"active": 1, "delivered": 15, "failed": 1},
            channels_enabled=True,
            active_channels=1,
        )

        labels = [item["label"] for item in monitor["bars"]]
        values = {item["label"]: item["value"] for item in monitor["bars"]}
        self.assertIn("24 soat aktiv", labels)
        self.assertIn("Dars tugadi", labels)
        self.assertEqual(values["24 soat aktiv"], 4)
        self.assertEqual(values["Dars tugadi"], 5)
        self.assertEqual(values["Tekshiruvdagi to'lov"], 2)


if __name__ == "__main__":
    unittest.main()

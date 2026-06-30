import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.admin_stats_service import feature_usage_stats, miniapp_course_stats
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

    async def test_feature_usage_stats_sorted_by_week_users(self):
        # Chaqiruv tartibi: har bo'lim uchun (bugun, hafta) — 6 ta bo'lim = 12 ta query.
        # Darslar, Testlar, Mashqlar, Xatolar, Voice, AI
        session = _Session([5, 50, 2, 20, 1, 10, 0, 5, 3, 30, 8, 80])
        now = datetime.now(timezone.utc)

        features = await feature_usage_stats(session, now, now - timedelta(days=7))

        self.assertEqual(session.execute_count, 12)
        # Haftalik aktiv user bo'yicha kamayish tartibida saralanishi kerak.
        self.assertEqual([f.week_users for f in features], [80, 50, 30, 20, 10, 5])
        top = features[0]
        self.assertEqual(top.label, "🤖 AI savol-javob")
        self.assertEqual(top.today_users, 8)
        self.assertEqual(top.week_users, 80)


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
        self.assertIn("24 соат фаол", labels)
        self.assertIn("Дарс тугади", labels)
        self.assertEqual(values["24 соат фаол"], 4)
        self.assertEqual(values["Дарс тугади"], 5)
        self.assertEqual(values["Текширувдаги тўлов"], 2)

    def test_period_report_text_includes_core_metrics(self):
        report = {
            "title": "Ҳафталик",
            "note": "Охирги 7 кун",
            "generated_at": "29.06.2026 10:00",
            "metrics": {
                "user_count": 14,
                "active_users": 9,
                "approved_payment_users": 3,
                "pending_payments": 2,
                "rejected_payments": 1,
                "approved_total_text": "267 TJS",
                "bot_blocked": 4,
                "course_completion": 55.6,
            },
            "payments": {"by_plan": {"10_days": 2, "1_month": 1}},
            "course": {
                "opened_users": 18,
                "lesson_users": 12,
                "completed_users": 10,
                "completed_sections": 31,
                "completed_book_lessons": 7,
            },
        }

        text = AdminMiniAppService._period_report_text(report)

        self.assertIn("Ҳафталик статистика", text)
        self.assertIn("Янги/жами: 14", text)
        self.assertIn("Тасдиқланган user: 3", text)
        self.assertIn("Тушум: 267 TJS", text)
        self.assertIn("Курс тугатиш: 55.6%", text)


if __name__ == "__main__":
    unittest.main()

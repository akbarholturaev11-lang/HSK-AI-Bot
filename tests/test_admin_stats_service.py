import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.admin_stats_service import (
    feature_usage_stats,
    miniapp_course_stats,
    top_referrers,
)
from app.services.admin_miniapp_service import (
    HOT_LEAD_ACTIVITY_WINDOW,
    AdminMiniAppService,
    admin_miniapp_today_start,
    is_admin_active_today,
    is_admin_hot_lead,
)


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


class _FetchResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def fetchall(self):
        return self._rows


class _ScalarsResult:
    def __init__(self, values):
        self._values = list(values)

    def scalars(self):
        return self

    def all(self):
        return self._values


class _QueuedSession:
    def __init__(self, results):
        self.results = list(results)

    async def execute(self, _stmt):
        return self.results.pop(0)


class TopReferrersTests(unittest.IsolatedAsyncioTestCase):
    async def test_top_referrers_prefers_username_then_full_name(self):
        rows = [
            SimpleNamespace(tid=101, total=9, activated=5),
            SimpleNamespace(tid=102, total=4, activated=4),
            SimpleNamespace(tid=103, total=2, activated=0),
        ]
        users = [
            SimpleNamespace(telegram_id=101, username="alisher", full_name="Alisher A"),
            SimpleNamespace(telegram_id=102, username=None, full_name="Bobur B"),
            # 103 ataylab yo'q — telegram_id ko'rsatilishi kerak
        ]
        session = _QueuedSession([_FetchResult(rows), _ScalarsResult(users)])

        result = await top_referrers(session, limit=5)

        self.assertEqual([r.name for r in result], ["@alisher", "Bobur B", "103"])
        self.assertEqual([r.total for r in result], [9, 4, 2])
        self.assertEqual(result[0].activated, 5)

    async def test_top_referrers_empty(self):
        session = _QueuedSession([_FetchResult([])])
        self.assertEqual(await top_referrers(session), [])


class AdminMiniAppServiceTests(unittest.TestCase):
    def test_hot_lead_requires_unpaid_recent_active_unblocked_user(self):
        now = datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc)
        hot_since = now - HOT_LEAD_ACTIVITY_WINDOW
        hot = SimpleNamespace(
            status="trial",
            payment_status="none",
            last_active_at=now - timedelta(hours=12),
            bot_blocked_at=None,
            bot_unblocked_at=None,
        )
        cold = SimpleNamespace(
            status="trial",
            payment_status="none",
            last_active_at=now - timedelta(days=3),
            bot_blocked_at=None,
            bot_unblocked_at=None,
        )
        paid = SimpleNamespace(
            status="active",
            payment_status="approved",
            last_active_at=now - timedelta(hours=1),
            bot_blocked_at=None,
            bot_unblocked_at=None,
        )
        blocked = SimpleNamespace(
            status="free",
            payment_status="none",
            last_active_at=now - timedelta(hours=1),
            bot_blocked_at=now - timedelta(minutes=30),
            bot_unblocked_at=None,
        )

        self.assertTrue(is_admin_hot_lead(hot, hot_since))
        self.assertFalse(is_admin_hot_lead(cold, hot_since))
        self.assertFalse(is_admin_hot_lead(paid, hot_since))
        self.assertFalse(is_admin_hot_lead(blocked, hot_since))

    def test_active_today_uses_admin_timezone_day_start(self):
        now = datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc)
        today_start = admin_miniapp_today_start(now)
        active = SimpleNamespace(last_active_at=today_start)
        yesterday = SimpleNamespace(last_active_at=today_start - timedelta(seconds=1))

        self.assertTrue(is_admin_active_today(active, today_start))
        self.assertFalse(is_admin_active_today(yesterday, today_start))

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

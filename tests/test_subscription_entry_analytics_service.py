import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.subscription_entry_analytics_service import SubscriptionEntryAnalyticsService


class _RowsResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class _StatsSession:
    def __init__(self, results):
        self.results = list(results)

    async def execute(self, _stmt):
        return _RowsResult(self.results.pop(0))


class _RecordSession:
    def __init__(self):
        self.added = []
        self.commit_count = 0
        self.rollback_count = 0

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.commit_count += 1

    async def rollback(self):
        self.rollback_count += 1


class SubscriptionEntryAnalyticsServiceTests(unittest.IsolatedAsyncioTestCase):
    def test_normalize_source_keeps_stable_ascii_key(self):
        self.assertEqual(
            SubscriptionEntryAnalyticsService.normalize_source(" QA Limit!! "),
            "qa_limit",
        )
        self.assertEqual(SubscriptionEntryAnalyticsService.normalize_source(""), "unknown")

    async def test_record_entry_saves_normalized_source(self):
        session = _RecordSession()
        user = SimpleNamespace(id=7)

        ok = await SubscriptionEntryAnalyticsService(session).record_entry(
            telegram_id=123,
            user=user,
            source="Menu Subscription",
            mode="subscription",
        )

        self.assertTrue(ok)
        self.assertEqual(session.commit_count, 1)
        self.assertEqual(session.added[0].user_id, 7)
        self.assertEqual(session.added[0].telegram_id, 123)
        self.assertEqual(session.added[0].source, "menu_subscription")

    async def test_admin_text_orders_by_week_unique_users(self):
        session = _StatsSession(
            [
                [
                    SimpleNamespace(source="menu_subscription", total=12, unique_users=8),
                    SimpleNamespace(source="qa_limit", total=5, unique_users=4),
                ],
                [
                    SimpleNamespace(source="menu_subscription", total=2, unique_users=1),
                    SimpleNamespace(source="qa_limit", total=4, unique_users=3),
                ],
            ]
        )

        text = await SubscriptionEntryAnalyticsService(session).admin_text(
            week_ago=datetime.now(timezone.utc),
        )

        self.assertIn("OBUNA MANBALARI", text)
        self.assertLess(text.index("QA limit"), text.index("Menyu -&gt; Obuna"))
        self.assertIn("user <b>4</b>/<b>+3</b>", text)


if __name__ == "__main__":
    unittest.main()

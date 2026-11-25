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

    async def flush(self):
        self.added[-1].id = 42

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

    async def test_receipt_is_returned_only_after_successful_commit(self):
        session = _RecordSession()
        service = SubscriptionEntryAnalyticsService(session)
        receipt = await service.record_entry(user=SimpleNamespace(id=7), return_entry_id=True)
        self.assertIs(type(receipt), int)
        self.assertEqual(42, receipt)
        self.assertEqual(1, session.commit_count)

        async def failed_commit():
            raise RuntimeError("test write failure")
        session.commit = failed_commit
        self.assertIs(False, await service.record_entry(user=SimpleNamespace(id=7), return_entry_id=True))
        self.assertEqual(1, session.rollback_count)

    async def test_record_entry_keeps_only_a_known_route_client(self):
        # R3: routes pass their own client; anything else is stored as NULL.
        for client, stored in (("telegram", "telegram"), ("iphone_pwa", "iphone_pwa"),
                               ("android", "android"), (None, None), ("macos", None),
                               ("Android", None), ("android_subscription", None)):
            with self.subTest(client=client):
                session = _RecordSession()
                ok = await SubscriptionEntryAnalyticsService(session).record_entry(
                    user=SimpleNamespace(id=7), source="android_subscription", client=client)
                self.assertTrue(ok)
                self.assertEqual(session.added[0].client, stored)

    async def test_admin_text_orders_by_week_unique_users(self):
        session = _StatsSession(
            [
                [
                    SimpleNamespace(source="menu_subscription", telegram_id=1),
                    SimpleNamespace(source="command_subscription", telegram_id=1),
                    SimpleNamespace(source="menu_subscription", telegram_id=2),
                    SimpleNamespace(source="qa_limit", telegram_id=3),
                    SimpleNamespace(source="qa_limit", telegram_id=4),
                    SimpleNamespace(source="qa_limit", telegram_id=5),
                    SimpleNamespace(source="qa_limit", telegram_id=6),
                ],
                [
                    SimpleNamespace(source="menu_subscription", telegram_id=1),
                    SimpleNamespace(source="command_subscription", telegram_id=1),
                    SimpleNamespace(source="qa_limit", telegram_id=3),
                    SimpleNamespace(source="qa_limit", telegram_id=4),
                    SimpleNamespace(source="qa_limit", telegram_id=5),
                ],
            ]
        )

        text = await SubscriptionEntryAnalyticsService(session).admin_text(
            week_ago=datetime.now(timezone.utc),
        )

        self.assertIn("OBUNA MANBALARI", text)
        self.assertLess(text.index("QA limit"), text.index("Obuna sahifasi"))
        self.assertIn("user <b>4</b>/<b>+3</b>", text)
        self.assertIn("user <b>2</b>/<b>+1</b>", text)


if __name__ == "__main__":
    unittest.main()

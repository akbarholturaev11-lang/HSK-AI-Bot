import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.entitlements.engine import (
    EntitlementEngine,
    _PENDING_LIMIT_HIT_TASKS,
)


class DeferredLimitHitTelemetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_slow_write_finishes_after_user_facing_deadline(self):
        done = asyncio.Event()
        cancelled = False
        written = []

        async def slow_record_once(**kwargs):
            nonlocal cancelled
            try:
                await asyncio.sleep(0.03)
                written.append(kwargs)
                done.set()
                return True
            except asyncio.CancelledError:
                cancelled = True
                raise

        with patch(
            "app.services.entitlements.engine.LIMIT_HIT_ANALYTICS_TIMEOUT_SECONDS",
            0.001,
        ), patch(
            "app.services.entitlements.engine.ConversionFunnelService"
        ) as service:
            service.return_value.record_once = AsyncMock(side_effect=slow_record_once)
            await EntitlementEngine(None)._record_limit_hit(
                SimpleNamespace(id=42, telegram_id=None), "practice.recognition"
            )
            self.assertFalse(done.is_set())
            await asyncio.wait_for(done.wait(), timeout=1)

        self.assertFalse(cancelled)
        self.assertEqual(len(written), 1)
        self.assertEqual(written[0]["event_name"], "limit_hit")
        self.assertEqual(written[0]["user_id"], 42)

    async def test_background_write_has_hard_timeout(self):
        cancelled = asyncio.Event()

        async def never_finishes(**kwargs):
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                cancelled.set()
                raise

        with patch(
            "app.services.entitlements.engine.LIMIT_HIT_ANALYTICS_TIMEOUT_SECONDS",
            0.001,
        ), patch(
            "app.services.entitlements.engine.LIMIT_HIT_ANALYTICS_WRITE_TIMEOUT_SECONDS",
            0.02,
        ), patch(
            "app.services.entitlements.engine.ConversionFunnelService"
        ) as service:
            service.return_value.record_once = AsyncMock(side_effect=never_finishes)
            await EntitlementEngine(None)._record_limit_hit(
                SimpleNamespace(id=43, telegram_id=None), "lesson.start"
            )
            await asyncio.wait_for(cancelled.wait(), timeout=1)
            await asyncio.sleep(0)
        self.assertFalse(any(task.done() is False for task in _PENDING_LIMIT_HIT_TASKS))

    async def test_backlog_cap_does_not_block_limit_decision(self):
        with patch(
            "app.services.entitlements.engine.LIMIT_HIT_ANALYTICS_MAX_PENDING", 0
        ), patch(
            "app.services.entitlements.engine.ConversionFunnelService"
        ) as service:
            await EntitlementEngine(None)._record_limit_hit(
                SimpleNamespace(id=44, telegram_id=None), "lesson.start"
            )
            service.assert_not_called()


if __name__ == "__main__":
    unittest.main()

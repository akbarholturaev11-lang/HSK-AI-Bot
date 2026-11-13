"""Task 3.2 step 3: route-owned transport marker on existing checkout openings.

Source and attempt ID text on the Telegram routes come from the caller, so the
Admin funnel attributes an opening only by this server-set payload key.
"""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app.services.desktop_subscription_service import DesktopSubscriptionService


class AndroidCheckoutMarkerTests(unittest.IsolatedAsyncioTestCase):
    async def opened_payload(self, source):
        service = object.__new__(DesktopSubscriptionService)
        service.source = source
        record = AsyncMock(return_value=True)
        with patch("app.services.desktop_subscription_service.ConversionFunnelService") as funnel:
            funnel.return_value.record = record
            await service._record_checkout_opened(
                user=SimpleNamespace(telegram_id=1001), attempt_id="attempt-1",
            )
        return record.await_args.kwargs

    async def test_android_opening_carries_the_route_marker(self):
        kwargs = await self.opened_payload("android_subscription")
        self.assertEqual(kwargs["event_name"], "checkout_opened")
        self.assertEqual(kwargs["payload"], {"attempt_id": "attempt-1", "mode": "subscription",
                                             "transport": "android"})

    async def test_desktop_opening_is_unchanged_during_the_freeze(self):
        kwargs = await self.opened_payload("desktop_subscription")
        self.assertEqual(kwargs["payload"], {"attempt_id": "attempt-1", "mode": "subscription"})


class TelegramCheckoutMarkerTests(unittest.TestCase):
    def route(self, start, end):
        source = Path(__file__).resolve().parents[1].joinpath("app/main.py").read_text(encoding="utf-8")
        return source.split(start, 1)[1].split(end, 1)[0]

    def test_both_telegram_opening_writes_set_the_marker_server_side(self):
        overview = self.route('@app.post("/api/subscription-miniapp/overview")', "\n@app.")
        event = self.route('@app.post("/api/subscription-miniapp/event")', "\n@app.")
        for body in (overview, event):
            with self.subTest(route=body[:40]):
                self.assertEqual(body.count('event_name="checkout_opened"'), 1)
                self.assertEqual(body.count('"transport": "telegram"'), 1)
                # The caller never supplies the marker.
                self.assertNotIn('payload.get("transport")', body)


if __name__ == "__main__":
    unittest.main()

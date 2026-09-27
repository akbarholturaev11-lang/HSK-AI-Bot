"""The paid checkout shares the device-detecting download page."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.subscription_miniapp_service import SubscriptionMiniAppService


class ReferralDiscountLinkTests(unittest.IsolatedAsyncioTestCase):
    async def test_checkout_invite_points_to_apps_page(self):
        user = SimpleNamespace(
            telegram_id=42,
            referral_code="a1b2c3d4",
            discount_used=False,
            discount_offer_started_at=None,
        )
        with patch("app.services.subscription_miniapp_service.DiscountService") as discount, patch(
            "app.services.subscription_miniapp_service.public_origin", return_value="https://hsk.example"
        ):
            discount.return_value.sync_referral_discount_progress = AsyncMock(return_value=(0, False))
            payload = await SubscriptionMiniAppService(object())._discount_payload(user)
        self.assertEqual("https://hsk.example/apps?ref=a1b2c3d4", payload["referral_link"])

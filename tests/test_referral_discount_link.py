"""The paid checkout shares the device-detecting download page."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401 - register all tables
from app.db.base import Base
from app.db.models.referral import Referral
from app.repositories.user_repo import UserRepository
from app.services.referral_service import ReferralService
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


class ReferralOwnerAttributionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_android_and_ios_start_payloads_persist_the_link_owner(self):
        async with self.sessions() as session:
            users = UserRepository(session)
            owner = await users.create(telegram_id=7001)
            owner.referral_code = "a1b2c3d4"
            android_friend = await users.create(telegram_id=7002)
            ios_friend = await users.create(telegram_id=7003)
            await session.commit()

            referrals = ReferralService(session)
            await referrals.attach_referral_if_needed(7002, "ra_a1b2c3d4")
            await referrals.attach_referral_if_needed(7003, "ri_a1b2c3d4")

            rows = (await session.scalars(select(Referral).order_by(Referral.invited_user_telegram_id))).all()
            self.assertEqual(
                [(7001, 7002, "android"), (7001, 7003, "ios")],
                [(row.referrer_telegram_id, row.invited_user_telegram_id, row.discount_platform) for row in rows],
            )
            self.assertEqual(owner.id, android_friend.referrer_id)
            self.assertEqual(owner.id, ios_friend.referrer_id)
            self.assertEqual(7001, android_friend.referred_by_telegram_id)
            self.assertEqual(7001, ios_friend.referred_by_telegram_id)

"""Personal discounts are scoped to canonical users, not nullable Telegram IDs."""
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.user import User
from app.repositories.discount_campaign_repo import DiscountCampaignRepository
from app.services.discount_service import DiscountService


class NativeDiscountOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as con:
            await con.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all([
                User(id=1, telegram_id=None, full_name="Google native", status="free"),
                User(id=2, telegram_id=None, full_name="Apple native", status="free"),
                User(id=3, telegram_id=3003, full_name="Legacy Telegram", status="free"),
            ])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_native_personal_campaign_is_not_shared_with_another_null_telegram(self):
        async with self.sessions() as session:
            google, apple = await session.get(User, 1), await session.get(User, 2)
            now = datetime.now(timezone.utc)
            repo = DiscountCampaignRepository(session)
            campaign = await repo.create(
                title="Native personal offer",
                percent=15,
                starts_at=now - timedelta(minutes=1),
                ends_at=now + timedelta(days=1),
                target_user_id=google.id,
            )
            self.assertEqual(campaign.target_user_id, google.id)
            self.assertIsNone(campaign.target_telegram_id)
            service = DiscountService(session)
            allowed = await service.get_best_admin_discount(
                user=google, plan_type="1_month", payment_method="card",
            )
            denied = await service.get_best_admin_discount(
                user=apple, plan_type="1_month", payment_method="card",
            )
            self.assertEqual((allowed.source, allowed.percent, allowed.campaign_id),
                             ("admin_campaign", 15, campaign.id))
            self.assertEqual((denied.source, denied.percent), ("none", 0))

    async def test_legacy_telegram_target_and_mismatch_checks(self):
        async with self.sessions() as session:
            google, telegram = await session.get(User, 1), await session.get(User, 3)
            repo = DiscountCampaignRepository(session)
            now = datetime.now(timezone.utc)
            opts = dict(title="Legacy target", percent=10,
                        starts_at=now - timedelta(minutes=1),
                        ends_at=now + timedelta(days=1))
            campaign = await repo.create(target_telegram_id=3003, **opts)
            self.assertEqual(campaign.target_user_id, telegram.id)
            self.assertEqual(campaign.target_telegram_id, 3003)
            service = DiscountService(session)
            self.assertEqual((await service.get_best_admin_discount(
                user=telegram, plan_type="1_month", payment_method="card")).percent, 10)
            self.assertEqual((await service.get_best_admin_discount(
                user=google, plan_type="1_month", payment_method="card")).percent, 0)
            with self.assertRaisesRegex(ValueError, "discount_target_mismatch"):
                await repo.create(target_user_id=google.id, target_telegram_id=3003, **opts)
            with self.assertRaisesRegex(ValueError, "invalid_discount_target"):
                await repo.create(target_user_id=-1, **opts)


if __name__ == "__main__":
    unittest.main()

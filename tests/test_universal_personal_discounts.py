"""Personal offers retain canonical ownership independently of sign-in method."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy import delete, event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.discount_campaign import DiscountCampaign
from app.db.models.user import User
from app.repositories.discount_campaign_repo import DiscountCampaignRepository
from app.services.discount_notification_service import DiscountNotificationService
from app.services.discount_service import DiscountService


class UniversalPersonalDiscountTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)

        @event.listens_for(self.engine.sync_engine, "connect")
        def _enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            session.add_all([
                User(id=uid, telegram_id=tid, language="uz", level="hsk1", status="free",
                     payment_status="none") for uid, tid in ((1, None), (2, None), (3, 3003), (4, 1))
            ])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def campaign(self, session, **fields):
        return await DiscountCampaignRepository(session).create(
            title="Personal offer", percent=25,
            starts_at=self.now - timedelta(days=1), ends_at=self.now + timedelta(days=1), **fields)

    async def test_personal_offer_for_null_telegram_owner_is_not_global_or_a_numeric_telegram_guess(self):
        async with self.sessions() as session:
            campaign = await self.campaign(session, target_user_id=1)
            users = [await session.get(User, uid) for uid in (1, 2, 3, 4)]
            self.assertEqual((campaign.target_user_id, campaign.target_telegram_id), (1, None))
            service = DiscountService(session)
            for user in users:
                choice = await service.get_best_admin_discount(user=user, plan_type="1_month", payment_method="visa")
                self.assertEqual(choice.percent, 25 if user.id == 1 else 0)
            targets = await DiscountNotificationService(session)._target_users(campaign)
            self.assertEqual([user.id for user in targets], [1])

    async def test_telegram_adapter_resolves_its_owner_without_confusing_account_id(self):
        async with self.sessions() as session:
            campaign = await self.campaign(session, target_telegram_id=1)
            self.assertEqual((campaign.target_user_id, campaign.target_telegram_id), (4, 1))
            service = DiscountService(session)
            self.assertTrue(service._matches_campaign(campaign, await session.get(User, 4), "1_month", "visa"))
            self.assertFalse(service._matches_campaign(campaign, await session.get(User, 1), "1_month", "visa"))

    async def test_canonical_owner_wins_over_foreign_stale_telegram_metadata(self):
        async with self.sessions() as session:
            campaign = DiscountCampaign(title="Old personal offer", percent=25,
                target_user_id=1, target_telegram_id=3003,
                starts_at=self.now - timedelta(days=1), ends_at=self.now + timedelta(days=1))
            session.add(campaign)
            await session.flush()
            service = DiscountService(session)
            self.assertTrue(service._matches_campaign(campaign, await session.get(User, 1), "1_month", "visa"))
            self.assertFalse(service._matches_campaign(campaign, await session.get(User, 3), "1_month", "visa"))
            targets = await DiscountNotificationService(session)._target_users(campaign)
            self.assertEqual([user.id for user in targets], [1])

    async def test_unknown_legacy_telegram_target_and_legacy_rows_remain_targeted(self):
        async with self.sessions() as session:
            campaign = await self.campaign(session, target_telegram_id=8888)
            self.assertEqual((campaign.target_user_id, campaign.target_telegram_id), (None, 8888))
            service = DiscountService(session)
            for uid in (1, 2, 3, 4):
                self.assertFalse(service._matches_campaign(campaign, await session.get(User, uid), "1_month", "visa"))
            self.assertEqual(await DiscountNotificationService(session)._target_users(campaign), [])
            # A genuine legacy row remains usable by its real Telegram owner.
            campaign.target_telegram_id = 3003
            self.assertTrue(service._matches_campaign(campaign, await session.get(User, 3), "1_month", "visa"))
            self.assertFalse(service._matches_campaign(campaign, await session.get(User, 1), "1_month", "visa"))
            for invalid_target in (0, -1):
                campaign.target_telegram_id = invalid_target
                self.assertEqual(await DiscountNotificationService(session)._target_users(campaign), [])
            missing_owner = SimpleNamespace(target_user_id=9999, target_telegram_id=3003)
            self.assertEqual(await DiscountNotificationService(session)._target_users(missing_owner), [])

    async def test_explicit_target_validation_never_turns_bad_input_into_a_global_offer(self):
        async with self.sessions() as session:
            for fields, error in (
                ({"target_user_id": 0}, "invalid_discount_target"),
                ({"target_user_id": -1}, "invalid_discount_target"),
                ({"target_user_id": True}, "invalid_discount_target"),
                ({"target_telegram_id": 0}, "invalid_discount_target"),
                ({"target_telegram_id": -1}, "invalid_discount_target"),
                ({"target_user_id": 9999}, "discount_target_user_not_found"),
                ({"target_user_id": 1, "target_telegram_id": 3003}, "discount_target_mismatch"),
                ({"target_user_id": 1, "target_telegram_id": 8888}, "discount_target_mismatch"),
            ):
                with self.subTest(fields=fields):
                    with self.assertRaisesRegex(ValueError, error):
                        await self.campaign(session, **fields)
            self.assertEqual(list((await session.scalars(select(DiscountCampaign))).all()), [])
            valid = await self.campaign(session, target_user_id=3, target_telegram_id=3003)
            self.assertEqual((valid.target_user_id, valid.target_telegram_id), (3, 3003))

    async def test_post_telegram_attachment_keeps_the_same_personal_offer_owner(self):
        async with self.sessions() as session:
            campaign = await self.campaign(session, target_user_id=1)
            owner = await session.get(User, 1)
            owner.telegram_id = 9191
            await session.flush()
            service = DiscountService(session)
            self.assertTrue(service._matches_campaign(campaign, owner, "1_month", "visa"))
            self.assertFalse(service._matches_campaign(campaign, await session.get(User, 2), "1_month", "visa"))
            self.assertEqual((campaign.target_user_id, campaign.target_telegram_id), (1, None))

    async def test_global_cohort_and_best_offer_rules_still_apply_to_every_identity(self):
        async with self.sessions() as session:
            global_offer = await self.campaign(session)
            service = DiscountService(session)
            for uid in (1, 2, 3, 4):
                user = await session.get(User, uid)
                self.assertTrue(service._matches_campaign(global_offer, user, "1_month", "visa"))
                choice = await service.get_best_admin_discount(user=user, plan_type="1_month", payment_method="visa")
                self.assertEqual((choice.source, choice.percent), ("admin_campaign", 25))
            global_offer.audience_language = "tj"
            self.assertFalse(service._matches_campaign(global_offer, await session.get(User, 1), "1_month", "visa"))
            global_offer.audience_language = "uz"
            global_offer.payment_method, global_offer.plan_type = "visa", "1_month"
            self.assertTrue(service._matches_campaign(global_offer, await session.get(User, 1), "1_month", "visa"))
            self.assertFalse(service._matches_campaign(global_offer, await session.get(User, 1), "3_months", "visa"))
            self.assertFalse(service._matches_campaign(global_offer, await session.get(User, 1), "1_month", "dc"))

    async def test_deleting_the_owner_deletes_personal_offer_instead_of_making_it_global(self):
        async with self.sessions() as session:
            personal = await self.campaign(session, target_user_id=1)
            global_offer = await self.campaign(session)
            personal_id, global_id = personal.id, global_offer.id
            await session.commit()
            await session.execute(delete(User).where(User.id == 1))
            await session.commit()
            remaining = (await session.scalars(select(DiscountCampaign))).all()
            self.assertEqual([row.id for row in remaining], [global_id])
            self.assertNotIn(personal_id, [row.id for row in remaining])

    async def test_personal_notification_uses_the_existing_canonical_cross_client_delivery(self):
        async with self.sessions() as session:
            campaign = await self.campaign(session, target_user_id=1)
            delivery = SimpleNamespace(reachable=AsyncMock(return_value=True), deliver=AsyncMock(return_value="android"))
            notices = SimpleNamespace(record_from_text=AsyncMock())
            with patch("app.services.discount_notification_service.NotificationDeliveryService", return_value=delivery), \
                 patch("app.services.discount_notification_service.CourseNotificationService", return_value=notices), \
                 patch("app.services.discount_notification_service.settings", SimpleNamespace(admin_id_list=[])), \
                 patch("app.services.discount_notification_service.asyncio.sleep", new=AsyncMock()):
                result = await DiscountNotificationService(session).send_campaign_notification(SimpleNamespace(), campaign)
            self.assertEqual((result.total, result.sent, result.failed), (1, 1, 0))
            owner = delivery.deliver.await_args.args[1]
            self.assertEqual((owner.id, owner.telegram_id), (1, None))
            self.assertEqual(notices.record_from_text.await_args.args[0].id, 1)


if __name__ == "__main__":
    unittest.main()

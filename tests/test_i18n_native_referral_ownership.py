"""Native referral accounts are canonical owners, never shared NULL transports."""
import unittest
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401 - register schema
from app.db.base import Base
from app.db.models.referral import Referral
from app.db.models.user import User
from app.repositories.referral_repo import ReferralRepository
from app.services.account_identity import actual_telegram_id


class NativeReferralOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            session.add_all([
                User(id=1, telegram_id=None, full_name="Google owner", created_at=now),
                User(id=2, telegram_id=None, full_name="Apple owner", created_at=now),
                User(id=3, telegram_id=None, full_name="Google invite", created_at=now),
                User(id=4, telegram_id=None, full_name="Apple invite", created_at=now),
                User(id=5, telegram_id=5005, full_name="Telegram legacy", created_at=now),
            ])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_two_provider_owners_get_distinct_invites_and_counts(self):
        async with self.sessions() as session:
            owner1, owner2, invite1, invite2 = [
                await session.get(User, uid) for uid in (1, 2, 3, 4)
            ]
            repo = ReferralRepository(session)
            a = await repo.create(owner1, invite1)
            b = await repo.create(owner2, invite2)
            self.assertEqual((a.referrer_user_id, a.invited_user_id), (1, 3))
            self.assertEqual((b.referrer_user_id, b.invited_user_id), (2, 4))
            self.assertTrue(all(actual_telegram_id(u) is None for u in (owner1, owner2)))
            self.assertTrue(all(v is None for v in (
                a.referrer_telegram_id, a.invited_user_telegram_id,
                b.referrer_telegram_id, b.invited_user_telegram_id
            )))
            self.assertEqual(await repo.count_by_referrer(owner1), 1)
            self.assertEqual(await repo.count_by_referrer(owner2), 1)
            self.assertIs(await repo.get_by_pair(owner1, invite1), a)
            self.assertIsNone(await repo.get_by_pair(owner2, invite1))
            self.assertIs(await repo.get_by_invited_user_telegram_id(invite2), b)
            self.assertIsNone(await repo.get_by_invited_user_telegram_id(owner1))

    async def test_legacy_telegram_alias_never_overrides_canonical_owner(self):
        async with self.sessions() as session:
            owner, legacy = await session.get(User, 1), await session.get(User, 5)
            session.add_all([
                Referral(referrer_user_id=1, invited_user_id=2,
                         referrer_telegram_id=5005, invited_user_telegram_id=None,
                         status="active", bonus_granted=False),
                Referral(referrer_user_id=None, invited_user_id=None,
                         referrer_telegram_id=5005, invited_user_telegram_id=5050,
                         status="active", bonus_granted=False),
            ])
            await session.commit()
            repo = ReferralRepository(session)
            self.assertEqual(await repo.count_by_referrer(owner), 1)
            self.assertEqual(await repo.count_by_referrer(legacy), 1)
            self.assertEqual(await repo.count_by_referrer(5005), 1)
            self.assertEqual((await repo.get_by_pair(owner, await session.get(User, 2))).referrer_user_id, 1)
            self.assertIsNone(await repo.get_by_invited_user_telegram_id(owner))

    def test_model_never_requires_native_telegram_transport(self):
        for col in ("referrer_telegram_id", "invited_user_telegram_id"):
            self.assertTrue(Referral.__table__.c[col].nullable)
        for col in ("referrer_user_id", "invited_user_id"):
            self.assertTrue(Referral.__table__.c[col].nullable)


if __name__ == "__main__":
    unittest.main()

"""Exercise referral row/reward ownership races on an isolated PostgreSQL schema."""
import asyncio
from datetime import datetime, timedelta, timezone
import os
import unittest
from uuid import uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.ai_usage import AIUsageBudget
from app.db.models.assistant import AssistantConversation
from app.db.models.message import Message
from app.db.models.referral import Referral
from app.db.models.user import User
from app.repositories.referral_repo import ReferralRepository
from app.repositories.user_repo import UserRepository
from app.services.referral_service import ReferralService
from tests.native_postgres_deadlines import postgres_timeout


@unittest.skipUnless(os.environ.get("NATIVE_ACCOUNT_TEST_DATABASE_URL"), "requires isolated PostgreSQL test database")
class UniversalReferralConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        url = os.environ["NATIVE_ACCOUNT_TEST_DATABASE_URL"]
        self.schema = "referral_race_test_" + uuid4().hex
        self.admin = create_async_engine(url, connect_args={"timeout": postgres_timeout(60)})
        async with self.admin.begin() as connection:
            await connection.execute(text(f"CREATE SCHEMA {self.schema}"))
        self.engine = create_async_engine(url, connect_args={"timeout": postgres_timeout(60), "server_settings": {
            "search_path": self.schema + ",public", "lock_timeout": f"{postgres_timeout(5)}s", "statement_timeout": f"{postgres_timeout(15)}s"}})
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()
        async with self.admin.begin() as connection:
            await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
        await self.admin.dispose()

    async def account(self, session):
        return await UserRepository(session).create(telegram_id=None)

    async def activate_together(self, user_ids):
        barrier = asyncio.Barrier(len(user_ids))
        async def answer_and_activate(uid):
            async with self.sessions() as session:
                user = await session.get(User, uid)
                conversation_id = str(uuid4())
                session.add(AssistantConversation(id=conversation_id, user_id=uid))
                await session.flush()
                for _ in range(2):
                    session.add(Message(user_id=uid, conversation_id=conversation_id,
                        role="user", content="Successful Chinese question", content_type="text"))
                # Match the native Assistant's pending-success transaction:
                # these FK key shares remain held during referral activation.
                await session.flush()
                await asyncio.wait_for(barrier.wait(), timeout=postgres_timeout(15))
                await ReferralService(session).activate_referral_if_eligible(None, user)
                await session.commit()
        await asyncio.wait_for(asyncio.gather(*(answer_and_activate(uid) for uid in user_ids)), timeout=postgres_timeout(45))

    async def test_parallel_fifth_and_sixth_native_invites_grant_one_trial_and_preserve_both_bonuses(self):
        async with self.sessions() as session:
            owner = await self.account(session)
            owner.referral_trial_count_started_at = datetime.now(timezone.utc) - timedelta(days=1)
            owner.bonus_questions = 20
            repo = ReferralRepository(session)
            for _ in range(4):
                friend = await self.account(session)
                referral = await repo.create(owner, friend)
                referral.status, referral.bonus_granted = "active", True
                referral.activated_at = datetime.now(timezone.utc) - timedelta(hours=1)
            invited = [await self.account(session), await self.account(session)]
            for friend in invited:
                await repo.create(owner, friend)
            await session.commit()
            owner_id, user_ids = owner.id, [user.id for user in invited]
        await self.activate_together(user_ids)
        async with self.sessions() as session:
            owner = await session.get(User, owner_id)
            self.assertEqual((owner.status, owner.payment_status, owner.bonus_questions), ("active", "none", 30))
            budgets = list((await session.scalars(select(AIUsageBudget).where(AIUsageBudget.user_id == owner_id))).all())
            self.assertEqual(len(budgets), 1)
            self.assertEqual((budgets[0].user_telegram_id, budgets[0].total_budget_usd), (None, 2.0))
            self.assertEqual(await session.scalar(select(func.count()).select_from(Referral).where(Referral.referrer_user_id == owner_id, Referral.bonus_granted.is_(True))), 6)
            for uid in user_ids:
                await ReferralService(session).activate_referral_if_eligible(None, await session.get(User, uid))
            self.assertEqual(owner.bonus_questions, 30)

    async def test_mutual_native_invites_do_not_deadlock_with_successful_message_foreign_keys(self):
        async with self.sessions() as session:
            alice, bob = await self.account(session), await self.account(session)
            now = datetime.now(timezone.utc) - timedelta(minutes=1)
            alice.referral_trial_count_started_at = bob.referral_trial_count_started_at = now
            repo = ReferralRepository(session)
            await repo.create(alice, bob)
            await repo.create(bob, alice)
            await session.commit()
            user_ids = [alice.id, bob.id]
        await self.activate_together(user_ids)
        async with self.sessions() as session:
            for uid in user_ids:
                owner = await session.get(User, uid)
                self.assertEqual((owner.bonus_questions, owner.questions_used), (5, 0))
            self.assertEqual(await session.scalar(select(func.count()).select_from(Referral).where(Referral.status == "active")), 2)

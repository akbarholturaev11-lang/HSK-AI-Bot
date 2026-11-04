"""Real PostgreSQL locks; opt in using an isolated test database URL."""
import asyncio
import os
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.services.desktop_auth_service import DesktopAuthService
from app.services.entitlements.state import EntitlementState, has_full_access, resolve_state
from app.services.identity_link_service import IdentityLinkError, IdentityLinkService
from app.repositories.user_repo import UserRepository
from app.services.subscription_service import SubscriptionService
from tests.test_native_oauth_api import _settings, _verified
from tests.native_postgres_deadlines import postgres_timeout

from app.db.models.bot_feedback import BotFeedback
from app.db.models.release_feedback import (
    ReleaseFeedbackCampaign, ReleaseFeedbackDelivery, ReleaseFeedbackResponse,
)
from app.db.models.discount_campaign import DiscountCampaign
from app.bot.handlers.feedback import _load_feedback_context
from app.bot.handlers.release_feedback import _locked_telegram_feedback_user
from app.repositories.bot_feedback_repo import BotFeedbackRepository
from app.repositories.release_feedback_repo import ReleaseFeedbackRepository
from app.services.bot_feedback_service import BotFeedbackService
from app.services.release_feedback_service import ReleaseFeedbackService


@unittest.skipUnless(os.environ.get('NATIVE_ACCOUNT_TEST_DATABASE_URL'), 'requires isolated PostgreSQL test database')
class NativeAccountConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.schema = 'native_test_' + uuid4().hex
        self.admin = create_async_engine(os.environ['NATIVE_ACCOUNT_TEST_DATABASE_URL'],
            connect_args={'timeout': postgres_timeout(60)})
        async with self.admin.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA {self.schema}'))
        self.engine = create_async_engine(os.environ['NATIVE_ACCOUNT_TEST_DATABASE_URL'],
            connect_args={'timeout': postgres_timeout(60), 'server_settings': {'search_path': self.schema + ',public'}})
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()
        async with self.admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA {self.schema} CASCADE'))
        await self.admin.dispose()

    async def _paid_telegram_user(self):
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            user = User(telegram_id=734881223, full_name="Synthetic paid learner",
                        language="uz", level="hsk1", status="active", payment_status="approved",
                        start_date=now - timedelta(days=1), end_date=now + timedelta(days=7))
            session.add(user)
            await session.commit()
            return user.id, user.end_date

    async def test_parallel_telegram_and_browser_feedback_award_single_bonus(self):
        """Real PostgreSQL row locks serialize the two feedback transports."""
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            learner = User(
                telegram_id=9827001, full_name="Concurrent feedback learner",
                language="uz", level="hsk1", learning_mode="course",
                status="free", payment_status="none",
                created_at=now - timedelta(days=4), last_active_at=now,
            )
            db.add(learner)
            await db.flush()
            fb = await BotFeedbackRepository(db).create_pending(learner)
            user_id, feedback_id = learner.id, fb.id
            await db.commit()

        start = asyncio.Event()

        async def answer(channel):
            async with self.sessions() as db:
                await start.wait()
                if channel == "telegram":
                    _, feedback, user = await _load_feedback_context(
                        db, 9827001, feedback_id,
                    )
                else:
                    user = (await db.execute(
                        select(User).where(User.id == user_id)
                        .with_for_update().execution_options(populate_existing=True)
                    )).scalar_one()
                    feedback = (await db.execute(
                        select(BotFeedback).where(
                            BotFeedback.id == feedback_id,
                            BotFeedback.user_id == user.id,
                        ).with_for_update().execution_options(populate_existing=True)
                    )).scalar_one()
                if feedback.status != "pending":
                    await db.commit()
                    return False
                # Give the other transport a chance to contend for the lock.
                await asyncio.sleep(0.08)
                feedback.liked_code = "course"
                feedback.disliked_code = "price"
                await BotFeedbackService(db).finish_feedback(feedback, user)
                await db.commit()
                return True

        first = asyncio.create_task(answer("telegram"))
        second = asyncio.create_task(answer("pwa"))
        start.set()
        results = await asyncio.wait_for(
            asyncio.gather(first, second), timeout=postgres_timeout(15),
        )
        self.assertEqual(results.count(True), 1, results)
        async with self.sessions() as db:
            row = await db.get(BotFeedback, feedback_id)
            user = await db.get(User, user_id)
            self.assertEqual(row.status, "completed")
            self.assertIsNotNone(row.reward_granted_at)
            self.assertEqual(user.status, "active")
            self.assertIsNotNone(user.end_date)
            self.assertLessEqual(
                (user.end_date - user.start_date).total_seconds(), 30 * 60 + 1,
            )

    async def test_parallel_telegram_and_browser_release_answer_awards_one_discount(self):
        """One campaign decision, discount and trial across real PG sessions."""
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            learner = User(
                telegram_id=9827002, full_name="Concurrent release learner",
                language="uz", level="hsk1", learning_mode="course",
                status="free", payment_status="none",
                created_at=now - timedelta(days=4), last_active_at=now,
            )
            campaign = ReleaseFeedbackCampaign(
                title="Synthetic release", status="sent", send_at=now,
            )
            db.add_all((learner, campaign))
            await db.flush()
            delivery = await ReleaseFeedbackRepository(db).create_delivery(
                campaign_id=campaign.id, user=learner, status="sent",
            )
            user_id, campaign_id, delivery_id = learner.id, campaign.id, delivery.id
            await db.commit()

        start = asyncio.Event()

        async def answer(channel):
            async with self.sessions() as db:
                await start.wait()
                if channel == "telegram":
                    user = await _locked_telegram_feedback_user(db, 9827002)
                else:
                    user = (await db.execute(
                        select(User).where(User.id == user_id)
                        .with_for_update().execution_options(populate_existing=True)
                    )).scalar_one()
                service = ReleaseFeedbackService(db)
                if await service.repo.get_response(
                    campaign_id=campaign_id, user=user,
                ):
                    await db.commit()
                    return False
                await asyncio.sleep(0.08)
                campaign = await service.repo.get_campaign(campaign_id)
                response = await service.repo.create_response(
                    campaign_id=campaign_id, user=user, rating=5,
                )
                await service.create_discount_for_response(
                    campaign=campaign, response=response, user=user,
                )
                await service.grant_trial_access(campaign=campaign, user=user)
                await db.commit()
                return True

        tasks = [asyncio.create_task(answer(which))
                 for which in ("telegram", "pwa")]
        start.set()
        results = await asyncio.wait_for(
            asyncio.gather(*tasks), timeout=postgres_timeout(15),
        )
        self.assertEqual(results.count(True), 1, results)
        async with self.sessions() as db:
            replies = (await db.execute(
                select(ReleaseFeedbackResponse).where(
                    ReleaseFeedbackResponse.campaign_id == campaign_id,
                )
            )).scalars().all()
            self.assertEqual(len(replies), 1)
            self.assertEqual(replies[0].user_id, user_id)
            coupons = (await db.execute(
                select(func.count(DiscountCampaign.id)).where(
                    DiscountCampaign.target_user_id == user_id,
                )
            )).scalar_one()
            self.assertEqual(coupons, 1)
            delivery = await db.get(ReleaseFeedbackDelivery, delivery_id)
            self.assertIsNotNone(delivery.trial_granted_until)

    async def test_telegram_renewals_refresh_an_already_loaded_account(self):
        user_id, initial_end = await self._paid_telegram_user()
        async with self.sessions() as stale:
            loaded = await UserRepository(stale).get_by_telegram_id(734881223)
            async with self.sessions() as concurrent:
                self.assertTrue(await SubscriptionService(concurrent).activate_plan(734881223, "1_month"))
                await concurrent.commit()
            self.assertEqual(loaded.end_date, initial_end)
            self.assertTrue(await SubscriptionService(stale).activate_plan(734881223, "1_month"))
            await stale.commit()
        async with self.sessions() as session:
            self.assertEqual((await session.get(User, user_id)).end_date,
                             initial_end + timedelta(days=60))

    async def test_telegram_renewal_cannot_reactivate_a_concurrently_blocked_account(self):
        user_id, initial_end = await self._paid_telegram_user()
        async with self.sessions() as stale:
            loaded = await UserRepository(stale).get_by_telegram_id(734881223)
            async with self.sessions() as concurrent:
                user = await concurrent.get(User, user_id)
                user.status = "blocked"
                await concurrent.commit()
            self.assertEqual(loaded.status, "active")
            self.assertFalse(await SubscriptionService(stale).activate_plan(734881223, "1_month"))
            await stale.commit()
        async with self.sessions() as session:
            user = await session.get(User, user_id)
            self.assertEqual((user.status, user.end_date), ("blocked", initial_end))

    async def test_parallel_first_provider_signups_create_one_account_per_provider(self):
        subjects = {'google': 'concurrent-google-signup', 'apple': 'concurrent-apple-signup'}
        start = asyncio.Event()

        async def signup(provider, index):
            async with self.sessions() as session:
                await start.wait()
                uid = await IdentityLinkService(session, _settings()).resolve_signin(
                    _verified(provider=provider, subject=subjects[provider]),
                    installation_key_hash=f'install-{provider}-{index}', allow_create=True)
                await session.commit()
                return provider, uid

        tasks = [asyncio.create_task(signup(provider, index))
                 for provider in subjects for index in range(4)]
        start.set()
        outcomes = await asyncio.wait_for(asyncio.gather(*tasks), timeout=postgres_timeout(15))
        user_ids = {}
        for provider in subjects:
            with self.subTest(provider=provider):
                ids = [uid for actual_provider, uid in outcomes if actual_provider == provider]
                self.assertEqual(len(ids), 4)
                self.assertEqual(len(set(ids)), 1)
                user_ids[provider] = ids[0]
        # Both verified claims have the same email; it must not merge the accounts.
        self.assertNotEqual(user_ids['google'], user_ids['apple'])
        async with self.sessions() as session:
            users = list((await session.execute(select(User))).scalars())
            self.assertEqual(len(users), 2)
            users_by_id = {user.id: user for user in users}
            for provider, user_id in user_ids.items():
                with self.subTest(provider=provider, policy='starter'):
                    user = users_by_id[user_id]
                    self.assertIsNone(user.telegram_id)
                    self.assertTrue(user.payment_preview_available)
                    self.assertIsNone(user.payment_preview_payment_id)
                    self.assertEqual((user.status, user.payment_status), ('trial', 'none'))
                    self.assertIsNone(user.start_date)
                    self.assertIsNone(user.end_date)
                    self.assertFalse(user.trial_used)
                    self.assertIsNone(user.pro_trial_started_at)
                    self.assertIsNone(user.pro_trial_ends_at)
                    self.assertEqual(resolve_state(user), EntitlementState.FREE)
                    self.assertFalse(has_full_access(resolve_state(user)))
            identities = list((await session.execute(select(UserIdentity))).scalars())
            self.assertEqual(len(identities), 2)
            service = IdentityLinkService(session, _settings())
            self.assertCountEqual(
                [(identity.provider, identity.subject_hash, identity.user_id) for identity in identities],
                [(provider, service.subject_hash(provider, subject), user_ids[provider])
                 for provider, subject in subjects.items()],
            )

    async def test_parallel_unlinks_wait_for_account_lock_and_keep_one_method(self):
        async with self.sessions() as session:
            service = IdentityLinkService(session, _settings())
            uid = await service.resolve_signin(_verified(subject='one'), installation_key_hash='x', allow_create=True)
            await service.link_to_user(_verified(subject='two', provider='apple'), user_id=uid)
            ids = list((await session.execute(select(UserIdentity.id))).scalars())
            await session.commit()
        async def unlink(identity_id):
            async with self.sessions() as session:
                result = await IdentityLinkService(session, _settings()).unlink(identity_id, user_id=uid)
                await session.commit()
                return result
        async with self.sessions() as blocker:
            await blocker.execute(select(User).where(User.id == uid).with_for_update())
            tasks = [asyncio.create_task(unlink(identity_id)) for identity_id in ids]
            try:
                await asyncio.sleep(0.15)
                self.assertTrue(all(not task.done() for task in tasks), 'identity changes must wait for the account lock')
            finally:
                await blocker.commit()
            outcomes = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=15)
        self.assertEqual(sum(isinstance(result, dict) for result in outcomes), 1)
        errors = [result for result in outcomes if isinstance(result, IdentityLinkError)]
        self.assertEqual([error.code for error in errors], ['oauth_last_identity'])
        async with self.sessions() as session:
            self.assertEqual((await session.execute(select(func.count(UserIdentity.id)))).scalar_one(), 1)

    async def test_first_telegram_confirmations_share_one_real_account(self):
        requests = []
        for index in range(3):
            async with self.sessions() as session:
                requests.append(await DesktopAuthService(session, _settings()).start_link(
                    platform='macos', app_version='1.5.3', installation_key=str(index) * 48, language='uz'))
        async def approve(started):
            async with self.sessions() as session:
                await DesktopAuthService(session, _settings()).approve_link(display_code=started['display_code'], telegram_id=7777)
        await asyncio.wait_for(asyncio.gather(*(approve(started) for started in requests)), timeout=15)
        async with self.sessions() as session:
            users = list((await session.execute(select(User))).scalars())
            self.assertEqual([(user.telegram_id, user.language) for user in users], [(7777, 'uz')])

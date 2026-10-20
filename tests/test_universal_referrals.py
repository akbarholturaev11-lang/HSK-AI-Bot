"""Provider-independent referral ownership keeps existing reward policy."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.ai_usage import AIUsageBudget
from app.db.models.assistant import AssistantConversation
from app.db.models.desktop import DesktopDevice
from app.db.models.message import Message
from app.db.models.referral import Referral
from app.db.models.user import User
from app.repositories.referral_repo import ReferralRepository
from app.repositories.user_repo import UserRepository
from app.services.admin_stats_service import top_referrers
from app.services.discount_service import DiscountService
from app.services.identity_link_service import IdentityLinkService
from app.services.desktop_auth_service import DesktopAuthService, DesktopAuthError
from app.api.android_auth import AndroidLinkStartRequest
from app.api.desktop_auth import DesktopLinkStartRequest
from app.api.native_oauth import OAuthStartRequest
from pydantic import ValidationError
from app.services.oidc_verifier import VerifiedIdentity
from app.services.referral_service import ReferralService, public_apps_url
from app.services.onboarding_service import OnboardingService


class UniversalReferralsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def account(self, session, telegram=None):
        return await UserRepository(session).create(telegram_id=telegram, full_name="Learner", language="uz")

    async def question(self, session, user, kind="text", role="user", native=True):
        conversation = str(uuid4()) if native else None
        if conversation:
            session.add(AssistantConversation(id=conversation, user_id=user.id))
            await session.flush()
        session.add(Message(user_id=user.id, conversation_id=conversation, role=role, content="Chinese help", content_type=kind))

    async def test_five_native_friends_require_two_successful_questions_and_grant_same_trial_budget(self):
        async with self.sessions() as session:
            owner = await self.account(session)
            await session.commit()
            service = ReferralService(session)
            for index in range(5):
                friend = await self.account(session)
                await service.attach_referral_if_needed(friend, "ref_" + owner.referral_code)
                await self.question(session, friend, kind="assistant_help")
                await self.question(session, friend, role="assistant")
                await self.question(session, friend, native=False)
                await self.question(session, friend)
                await service.activate_referral_if_eligible(None, friend)
                referral = await service.referral_repo.get_by_invited_user_telegram_id(friend)
                self.assertEqual(referral.status, "pending")
                await self.question(session, friend, kind="voice" if index % 2 else "image")
                await service.activate_referral_if_eligible(None, friend)
                await service.activate_referral_if_eligible(None, friend)
                self.assertEqual(friend.questions_used, 0)
            self.assertEqual((owner.status, owner.payment_status, owner.bonus_questions), ("active", "none", 25))
            budgets = list((await session.scalars(select(AIUsageBudget).where(AIUsageBudget.user_id == owner.id))).all())
            self.assertEqual(len(budgets), 1)
            self.assertEqual((budgets[0].user_telegram_id, budgets[0].total_budget_usd), (None, 2.0))
            self.assertAlmostEqual((budgets[0].ends_at - budgets[0].starts_at).total_seconds(), 3 * 86400, delta=1)
            self.assertEqual(tuple(service._as_utc(x) for x in (owner.start_date, owner.end_date)),
                             tuple(service._as_utc(x) for x in (budgets[0].starts_at, budgets[0].ends_at)))
            self.assertEqual(await service.get_trial_activation_progress(owner), 0)
            self.assertEqual(len(await service.list_miniapp_referrals(owner)), 5)
            self.assertEqual((await top_referrers(session))[0].total, 5)

    async def test_android_discount_requires_verified_account_device_and_exactly_three_invites(self):
        async with self.sessions() as session:
            owner, unrelated = await self.account(session), await self.account(session)
            owner.discount_offer_started_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await session.commit()
            service = ReferralService(session)
            for index in range(3):
                friend = await self.account(session)
                await service.attach_referral_if_needed(friend, "ra_" + owner.referral_code)
                self.assertFalse(await service.qualify_android_discount_referral(friend))
                session.add(DesktopDevice(id=str(uuid4()), user_id=friend.id, telegram_id=None,
                    installation_key_hash=str(index) * 64, platform="android", app_version="1.0.0"))
                await session.commit()
                self.assertTrue(await service.qualify_android_discount_referral(friend))
                self.assertFalse(await service.qualify_android_discount_referral(friend))
                self.assertEqual(owner.discount_eligible, index == 2)
            self.assertEqual(owner.discount_referral_count, 3)
            choice = await DiscountService(session).get_best_discount(user=owner, plan_type="1_month", payment_method="visa")
            self.assertEqual((choice.source, choice.percent), ("referral", 20))
            self.assertEqual(await service.referral_repo.count_by_referrer(unrelated), 0)
            self.assertIsNone(await service.referral_repo.get_by_invited_user_telegram_id(None))
            await UserRepository(session).delete_by_user_id(owner.id)
            await session.commit()
            self.assertEqual(list((await session.scalars(select(Referral))).all()), [])
            self.assertIsNotNone(await session.get(User, unrelated.id))

    async def test_canonical_owner_beats_conflicting_telegram_metadata(self):
        async with self.sessions() as session:
            owner, imposter, friend = await self.account(session), await self.account(session, 12), await self.account(session)
            session.add(Referral(referrer_user_id=owner.id, invited_user_id=friend.id,
                referrer_telegram_id=12, invited_user_telegram_id=None, status="pending"))
            await session.commit()
            repo = ReferralRepository(session)
            self.assertEqual(await repo.count_by_referrer(owner), 1)
            self.assertEqual(await repo.count_by_referrer(imposter), 0)
            self.assertEqual(await repo.count_by_referrer(12), 0)
            self.assertIsNone(await repo.get_by_invited_user_telegram_id(imposter))

    async def test_verified_first_signup_attributes_once_existing_signin_and_identity_link_do_not(self):
        async with self.sessions() as session:
            owner, other = await self.account(session), await self.account(session)
            await session.commit()
            identities = IdentityLinkService(session, SimpleNamespace(DESKTOP_AUTH_SIGNING_SECRET="x" * 64))
            proof = VerifiedIdentity(provider="google", subject="new-subject", email="same@example.com", email_verified=True, display_name="New", audience="aud")
            new_id = await identities.resolve_signin(proof, installation_key_hash="i" * 64, allow_create=True, referral_code=owner.referral_code)
            await session.commit()
            user = await session.get(User, new_id)
            self.assertEqual(user.referrer_id, owner.id)
            self.assertEqual(await identities.resolve_signin(proof, installation_key_hash="j" * 64, allow_create=True, referral_code=other.referral_code), new_id)
            await session.commit()
            referral = await ReferralRepository(session).get_by_invited_user_telegram_id(user)
            self.assertEqual(referral.referrer_user_id, owner.id)
            self.assertIsNone(referral.referrer_telegram_id)
            self.assertEqual(await ReferralRepository(session).count_by_referrer(other), 0)
            await identities.link_to_user(VerifiedIdentity(provider="apple", subject="apple-sub", email="same@example.com", email_verified=True, display_name=None, audience="aud"), user_id=other.id)
            await session.commit()
            self.assertIsNone(other.referrer_id)

    async def test_both_provider_signups_attribute_without_email_merging_and_blocked_or_self_invites_are_inert(self):
        async with self.sessions() as session:
            owner = await self.account(session)
            await session.commit()
            identities = IdentityLinkService(session, SimpleNamespace(DESKTOP_AUTH_SIGNING_SECRET="x" * 64))
            user_ids = []
            for provider in ("google", "apple"):
                uid = await identities.resolve_signin(VerifiedIdentity(provider=provider, subject=provider + "-signup",
                    email="shared@example.com", email_verified=True, display_name=provider, audience="aud"),
                    installation_key_hash=provider * 10, allow_create=True, referral_code=owner.referral_code)
                await session.commit()
                user_ids.append(uid)
            self.assertNotEqual(*user_ids)
            self.assertEqual(await ReferralRepository(session).count_by_referrer(owner), 2)
            service = ReferralService(session)
            await service.attach_referral_if_needed(owner, owner.referral_code)
            self.assertIsNone(await service.referral_repo.get_by_invited_user_telegram_id(owner))
            owner.status = "blocked"
            await session.commit()
            uninvited = await self.account(session)
            await service.attach_referral_if_needed(uninvited, owner.referral_code)
            self.assertIsNone(await service.referral_repo.get_by_invited_user_telegram_id(uninvited))
            self.assertEqual(owner.bonus_questions, 0)

    async def test_telegram_native_first_signup_keeps_owner_and_returning_signin_cannot_reattribute(self):
        async with self.sessions() as session:
            owner, other = await self.account(session), await self.account(session)
            await session.commit()
            auth = DesktopAuthService(session, SimpleNamespace(DESKTOP_AUTH_SIGNING_SECRET="k" * 64))
            for index, code in enumerate((owner.referral_code, other.referral_code)):
                started = await auth.start_link(platform="windows", app_version="1.0.0",
                    installation_key=str(index) * 48, referral_code=code)
                await auth.approve_link(display_code=started["display_code"], telegram_id=991)
            newcomer = await UserRepository(session).get_by_telegram_id(991)
            self.assertEqual(newcomer.referrer_id, owner.id)
            self.assertEqual(await ReferralRepository(session).count_by_referrer(owner), 1)
            self.assertEqual(await ReferralRepository(session).count_by_referrer(other), 0)

    async def test_android_private_chat_onboarding_attributes_new_account_only(self):
        async with self.sessions() as session:
            owner, other = await self.account(session), await self.account(session)
            await session.commit()
            onboarding = OnboardingService(session)
            new_user, created = await onboarding.get_or_create_user(telegram_id=707,
                referral_code=owner.referral_code, new_account_referral_only=True)
            self.assertTrue(created)
            self.assertEqual(new_user.referrer_id, owner.id)
            returning = await self.account(session, 808)
            await session.commit()
            existing, created = await onboarding.get_or_create_user(telegram_id=808,
                referral_code=other.referral_code, new_account_referral_only=True)
            self.assertFalse(created)
            self.assertEqual(existing.id, returning.id)
            self.assertIsNone(existing.referrer_id)
            self.assertEqual(await ReferralRepository(session).count_by_referrer(other), 0)

    def test_signup_request_contract_bounds_code_for_every_transport(self):
        for model, extra in ((AndroidLinkStartRequest, {"platform": "android"}),
            (DesktopLinkStartRequest, {"platform": "windows"}),
            (OAuthStartRequest, {"platform": "android", "provider": "google", "mode": "native_id_token"})):
            base = dict(app_version="1.0.0", installation_key="k" * 48, **extra)
            self.assertEqual(model(**base, referral_code="ra_a1b2c3d4").referral_code, "ra_a1b2c3d4")
            with self.assertRaises(ValidationError):
                model(**base, referral_code="x" * 65)

    def test_public_share_url_keeps_trial_and_discount_modes_distinct(self):
        settings = SimpleNamespace(PUBLIC_SITE_URL="https://hsk.example", MINI_APP_BASE_URL="")
        self.assertEqual(public_apps_url(settings, "a1b2c3d4", trial=True), "https://hsk.example/apps?ref=a1b2c3d4&mode=trial")
        self.assertEqual(public_apps_url(settings, "a1b2c3d4"), "https://hsk.example/apps?ref=a1b2c3d4")

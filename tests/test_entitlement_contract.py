"""Klientlarga beriladigan `entitlements` blokining shakli.

Bu blok to'rtta klientga (Mini App, desktop, Android, bot) bir xil javob
berish uchun bor, shuning uchun uning kalitlari shartnoma. Shu fayl ularni
qotiradi: kalit nomi o'zgarsa yoki tushib qolsa, bu klientni sindiradi.
"""

import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.user import User
from app.services.entitlements import actions as A
from app.services.entitlements.contract import (
    ANDROID_CHANNEL_DIRECT,
    ANDROID_CHANNEL_PLAY,
    AVAILABLE_PLANS,
    CLIENT_ANDROID,
    CLIENT_DESKTOP,
    CLIENT_MINIAPP,
    CONTRACT_VERSION,
    build_entitlement_block,
    checkout_allowed_for,
    trial_block,
)
from app.services.entitlements.state import EntitlementState

from tests.test_entitlement_engine_limits import _user


class ContractShapeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.db.dispose()

    async def _block(self, *, client=CLIENT_MINIAPP, channel=None, **user_kwargs):
        async with self.sessions() as session:
            session.add(_user(**user_kwargs))
            await session.commit()
            user = (
                await session.execute(select(User).where(User.telegram_id == 4100))
            ).scalar_one()
            payload = await build_entitlement_block(
                session, user, client=client, channel=channel
            )
        return payload["entitlements"]

    async def test_the_block_carries_every_promised_key(self):
        block = await self._block()

        self.assertEqual(CONTRACT_VERSION, block["version"])
        for key in (
            "client",
            "state",
            "is_paid",
            "has_full_access",
            "expires_at",
            "trial",
            "limits",
            "paywall",
            "policy",
        ):
            with self.subTest(key=key):
                self.assertIn(key, block)

    async def test_every_action_reports_the_same_limit_shape(self):
        block = await self._block()

        self.assertEqual(set(A.ACTIONS), set(block["limits"]))
        for action, entry in block["limits"].items():
            with self.subTest(action=action):
                self.assertEqual(
                    {
                        "allowed",
                        "limit",
                        "used",
                        "remaining",
                        "window",
                        "reset_at",
                        "unlimited",
                    },
                    set(entry),
                )

    async def test_a_free_user_sees_counted_limits_and_a_paywall(self):
        block = await self._block()

        self.assertEqual(EntitlementState.FREE, block["state"])
        self.assertFalse(block["is_paid"])
        self.assertFalse(block["has_full_access"])
        self.assertTrue(block["paywall"]["enabled"])
        self.assertEqual(2, block["limits"][A.LESSON_START]["limit"])
        self.assertFalse(block["limits"][A.LESSON_START]["unlimited"])

    async def test_a_paid_user_sees_unlimited_and_no_paywall(self):
        end = datetime.now(timezone.utc) + timedelta(days=30)
        block = await self._block(
            status="active", payment_status="approved", end_date=end
        )

        self.assertEqual(EntitlementState.PRO_ACTIVE, block["state"])
        self.assertTrue(block["is_paid"])
        self.assertTrue(block["has_full_access"])
        self.assertFalse(block["paywall"]["enabled"])
        self.assertIsNotNone(block["expires_at"])
        self.assertTrue(block["limits"][A.LESSON_START]["unlimited"])
        self.assertIsNone(block["limits"][A.LESSON_START]["limit"])

    async def test_a_referral_bonus_user_is_full_access_but_not_paid(self):
        # Aynan shu holat bugun klientlar orasida ajralib turadi.
        block = await self._block(
            status="active", end_date=datetime.now(timezone.utc) + timedelta(days=2)
        )

        self.assertEqual(EntitlementState.TEMP_ACCESS, block["state"])
        self.assertTrue(block["has_full_access"])
        self.assertFalse(block["is_paid"])

    async def test_the_same_user_gets_the_same_state_on_every_client(self):
        end = datetime.now(timezone.utc) + timedelta(days=2)
        states = {}
        for client in (CLIENT_MINIAPP, CLIENT_DESKTOP, CLIENT_ANDROID):
            block = await self._block(status="active", end_date=end, client=client)
            states[client] = (block["state"], block["has_full_access"])
            # Har testda yangi baza kerak — user takrorlanmasin.
            await self.asyncTearDown()
            await self.asyncSetUp()

        self.assertEqual(1, len(set(states.values())), states)

    async def test_the_plans_are_listed_with_three_months_recommended(self):
        block = await self._block()

        self.assertEqual(list(AVAILABLE_PLANS), block["paywall"]["plans"])
        self.assertEqual("3_months", block["paywall"]["recommended"])
        self.assertIn(block["paywall"]["recommended"], block["paywall"]["plans"])

    async def test_the_policy_is_reported_without_a_settings_row(self):
        block = await self._block()

        self.assertEqual("subscription", block["policy"]["mode"])
        self.assertEqual("subscription", block["policy"]["effective_mode"])
        self.assertIsNone(block["policy"]["free_until"])


class CheckoutByClientTests(unittest.TestCase):
    def test_the_play_build_is_never_offered_a_checkout(self):
        # Do'kon qoidasi: `play` buildida obuna CTA si bo'lmasligi kerak.
        # Bugun buni faqat klient biladi (compile-time bayroq); endi server ham.
        self.assertFalse(
            checkout_allowed_for(CLIENT_ANDROID, channel=ANDROID_CHANNEL_PLAY)
        )
        self.assertFalse(checkout_allowed_for(CLIENT_ANDROID))

    def test_the_direct_build_may_hand_off_to_telegram(self):
        self.assertTrue(
            checkout_allowed_for(CLIENT_ANDROID, channel=ANDROID_CHANNEL_DIRECT)
        )

    def test_the_other_clients_may_sell(self):
        for client in (CLIENT_MINIAPP, CLIENT_DESKTOP, "bot"):
            with self.subTest(client=client):
                self.assertTrue(checkout_allowed_for(client))

    def test_an_unknown_client_defaults_to_allowed(self):
        self.assertTrue(checkout_allowed_for("wat"))


class TrialBlockTests(unittest.TestCase):
    def _settings(self, **overrides):
        base = {"enabled": True, "days": 7, "disabled_reason": ""}
        base.update(overrides)
        return base

    def test_a_fresh_free_user_is_eligible(self):
        user = _user()
        block = trial_block(user, self._settings(), state=EntitlementState.FREE)

        self.assertTrue(block["eligible"])
        self.assertFalse(block["active"])
        self.assertFalse(block["used"])
        self.assertEqual(7, block["days_total"])
        # UI hech qachon "cheksiz" demasligi kerak.
        self.assertTrue(block["ai_budget_capped"])

    def test_the_kill_switch_removes_eligibility_with_a_reason(self):
        block = trial_block(
            _user(),
            self._settings(enabled=False, disabled_reason="fake akkauntlar"),
            state=EntitlementState.FREE,
        )

        self.assertFalse(block["eligible"])
        self.assertEqual("fake akkauntlar", block["disabled_reason"])

    def test_a_spent_trial_is_never_offered_again(self):
        user = _user()
        user.trial_used = True
        block = trial_block(user, self._settings(), state=EntitlementState.FREE)

        self.assertFalse(block["eligible"])
        self.assertTrue(block["used"])
        self.assertEqual("trial_already_used", block["disabled_reason"])

    def test_a_paid_user_is_not_offered_a_trial(self):
        block = trial_block(_user(), self._settings(), state=EntitlementState.PRO_ACTIVE)
        self.assertFalse(block["eligible"])

    def test_an_active_trial_reports_itself_active(self):
        user = _user()
        user.pro_trial_ends_at = datetime.now(timezone.utc) + timedelta(days=3)
        block = trial_block(user, self._settings(), state=EntitlementState.TRIAL_ACTIVE)

        self.assertTrue(block["active"])
        self.assertFalse(block["eligible"])
        self.assertIsNotNone(block["ends_at"])

    def test_a_user_without_the_columns_reads_as_never_used(self):
        # 4-bosqich migratsiyasidan oldin ham blok to'g'ri shaklda bo'lsin.
        block = trial_block(_user(), self._settings(), state=EntitlementState.FREE)
        self.assertFalse(block["used"])
        self.assertIsNone(block["started_at"])
        self.assertIsNone(block["ends_at"])


if __name__ == "__main__":
    unittest.main()

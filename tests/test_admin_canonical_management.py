"""Admin actions name canonical accounts without confusing real Telegram IDs."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.ai_usage import AIUsageBudget
from app.db.models.discount_campaign import DiscountCampaign
from app.db.models.bot_reachability_event import BotReachabilityEvent
from app.db.models.payment import Payment
from app.db.models.portfolio import PortfolioTransaction
from app.db.models.user import User
from app.api.admin_entitlements import create_admin_entitlements_router
from app.services.admin_user_target import parse_admin_user_target
from app.services.user_access_state_service import UserAccessStateService


class CanonicalAdminManagementTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_main_imports import MainModuleImportTests
        self.main = MainModuleImportTests._import_main()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            session.add_all([User(id=uid, telegram_id=tid, full_name=name, language="uz",
                status="free", payment_status="none", created_at=self.now, last_active_at=self.now)
                for uid, tid, name in ((1, None, "Google learner"), (2, 1, "Telegram learner"),
                                      (3, None, "Apple learner"), (4, 777, "Admin"), (777, None, "Native ID collision"))])
            await session.commit()
        self.bot = SimpleNamespace(send_message=AsyncMock())
        self.invalidate = Mock()
        self.patches = [
            patch.object(self.main, "async_session_maker", self.sessions),
            patch.object(self.main, "_admin_miniapp_user_id", return_value=777),
            patch.object(self.main, "_admin_auth_error", return_value=None),
            patch.object(self.main, "_is_admin_id", side_effect=lambda tid: tid == 777),
            patch.object(self.main, "bot", self.bot),
            patch.object(self.main, "invalidate_block_cache", self.invalidate),
        ]
        for item in self.patches:
            item.start()
        app = FastAPI()
        for path, fn in (("detail", "detail"), ("give-access", "give_access"),
                         ("delete", "delete"), ("block", "block"), ("message", "message")):
            app.add_api_route("/users/" + path, getattr(self.main, "admin_miniapp_user_" + fn), methods=["POST"])
        app.add_api_route("/campaigns", self.main.admin_miniapp_campaign_create, methods=["POST"])
        app.add_api_route("/users/search", self.main.admin_miniapp_users_search, methods=["POST"])
        app.include_router(create_admin_entitlements_router(session_factory=self.sessions,
            admin_guard=lambda request: (777, None)))
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="https://admin.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        for item in reversed(self.patches):
            item.stop()
        await self.engine.dispose()

    async def test_detail_selects_native_account_and_legacy_telegram_adapter_separately(self):
        for target, uid in (({"user_id": 1}, 1), ({"telegram_id": 1}, 2), ({"user_id": 3}, 3),
                            ({"user_id": 2, "telegram_id": 1}, 2)):
            with self.subTest(target=target):
                response = await self.client.post("/users/detail", json=target)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["user"]["account_id"], uid)
                self.assertEqual(response.json()["user"]["id"], 1 if uid == 2 else None)
        self.bot.send_message.assert_not_awaited()

    async def test_native_manual_grants_extend_paid_time_without_creating_financial_facts(self):
        original_end = self.now + timedelta(days=5)
        async with self.sessions() as session:
            user = await session.get(User, 1)
            user.status, user.payment_status = "active", "approved"
            user.end_date = original_end
            user.payment_preview_available = False
            await session.commit()
        response = await self.client.post("/users/give-access", json={"user_id": 1, "duration_days": 17})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["extended"])
        async with self.sessions() as session:
            user = await session.get(User, 1)
            self.assertEqual(UserAccessStateService.as_utc(user.end_date), original_end + timedelta(days=17))
            self.assertFalse(user.payment_preview_available)
            self.assertEqual((await session.get(User, 2)).status, "free")
            for model in (Payment, PortfolioTransaction, AIUsageBudget):
                self.assertIsNone(await session.scalar(select(model)))
        self.bot.send_message.assert_not_awaited()
        response = await self.client.post("/users/give-access", json={"telegram_id": 1, "plan": "10_days"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.bot.send_message.await_args.kwargs["chat_id"], 1)

    async def test_numeric_search_returns_distinct_canonical_and_telegram_matches(self):
        response = await self.client.post("/users/search", json={"query": "1"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual({row["account_id"] for row in response.json()["users"]}, {1, 2})
        response = await self.client.post("/users/search", json={"query": "9" * 100})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["users"], [])

    async def test_detail_does_not_mix_unlinked_accounts_reachability_history(self):
        async with self.sessions() as session:
            session.add_all([BotReachabilityEvent(user_id=uid, telegram_id=9999,
                event_type="blocked", source="fixture-" + str(uid), created_at=self.now)
                for uid in (1, 3)])
            await session.commit()
        response = await self.client.post("/users/detail", json={"user_id": 1})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([row["source"] for row in response.json()["user"]["bot_reachability_history"]], ["fixture-1"])

    async def test_block_unblock_targets_account_and_protects_actual_admin_identity(self):
        for target in ({"user_id": 1}, {"user_id": 777}):
            with self.subTest(target=target):
                response = await self.client.post("/users/block", json={**target, "blocked": True})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertTrue(response.json()["blocked"])
                response = await self.client.post("/users/block", json={**target, "blocked": False})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertFalse(response.json()["blocked"])
        self.invalidate.assert_not_called()
        self.bot.send_message.assert_not_awaited()
        for target in ({"user_id": 4}, {"telegram_id": 777}):
            for path, extra in (("block", {"blocked": True}), ("delete", {"confirm": str(next(iter(target.values())))})):
                with self.subTest(path=path, target=target):
                    response = await self.client.post("/users/" + path, json={**target, **extra})
                    self.assertEqual(response.status_code, 400, response.text)
                    self.assertEqual(response.json()["error"], "cannot_" + path + "_admin")

    async def test_mismatched_dual_identifiers_and_malformed_targets_never_mutate(self):
        for path, extra in (("detail", {}), ("give-access", {"duration_days": 30}),
                            ("block", {"blocked": True}), ("delete", {"confirm": "1"}),
                            ("message", {"text": "Hello learner"})):
            for target in ({"user_id": 1, "telegram_id": 1}, {"user_id": True}, {"user_id": 1.5},
                           {"user_id": -1}, {"user_id": "9" * 100}, {}, []):
                with self.subTest(path=path, target=target):
                    payload = {**target, **extra} if isinstance(target, dict) else target
                    response = await self.client.post("/users/" + path, json=payload)
                    self.assertEqual(response.status_code, 400, response.text)
        self.bot.send_message.assert_not_awaited()
        self.invalidate.assert_not_called()
        async with self.sessions() as session:
            self.assertEqual((await session.get(User, 1)).status, "free")
            self.assertEqual((await session.get(User, 2)).status, "free")

    async def test_native_delete_requires_canonical_confirmation_and_retains_only_own_finance(self):
        async with self.sessions() as session:
            session.add_all([Payment(user_id=uid, user_telegram_id=tid, plan_type="1_month",
                amount=100, currency="TJS", payment_status="approved") for uid, tid in ((1, None), (2, 1))])
            await session.commit()
        response = await self.client.post("/users/delete", json={"user_id": 1, "confirm": "2"})
        self.assertEqual(response.status_code, 400)
        response = await self.client.post("/users/delete", json={"user_id": 1, "confirm": "1"})
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as session:
            self.assertIsNone(await session.get(User, 1))
            self.assertIsNotNone(await session.get(User, 2))
            rows = (await session.scalars(select(Payment).order_by(Payment.id))).all()
            self.assertEqual([(p.user_id, p.user_telegram_id, p.amount) for p in rows], [(None, -1, 100), (2, 1, 100)])
        self.invalidate.assert_not_called()

    async def test_delete_commit_failure_rolls_back_and_keeps_guard_cache(self):
        with patch.object(AsyncSession, "commit", new=AsyncMock(side_effect=RuntimeError("commit failed"))):
            response = await self.client.post("/users/delete", json={"telegram_id": 1, "confirm": "1"})
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual(response.json()["error"], "delete_failed")
        self.invalidate.assert_not_called()
        async with self.sessions() as session:
            self.assertIsNotNone(await session.get(User, 2))

    async def test_native_account_number_equal_to_admin_telegram_id_can_be_deleted(self):
        response = await self.client.post("/users/delete", json={"user_id": 777, "confirm": "777"})
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as session:
            self.assertIsNone(await session.get(User, 777))
            self.assertIsNotNone(await session.get(User, 4))
        self.invalidate.assert_not_called()

    async def test_personal_discount_targets_canonical_account_and_keeps_global_campaign_global(self):
        payload = {"kind": "discount", "title": "Account offer", "text": "Existing discount rules",
                   "hours": 24, "percent": 25, "status": "free", "plan": "1_month", "quota_total": 9}
        for target, expected in (({"target_user_id": 1}, (1, None)),
                                 ({"target_telegram_id": 1}, (2, 1)),
                                 ({"target_user_id": 2, "target_telegram_id": 1}, (2, 1)),
                                 ({}, (None, None))):
            with self.subTest(target=target), patch.object(self.main.DiscountTranslationService,
                    "translate_campaign_texts", new=AsyncMock(return_value={})):
                response = await self.client.post("/campaigns", json={**payload, **target})
                self.assertEqual(response.status_code, 200, response.text)
                async with self.sessions() as session:
                    campaign = await session.scalar(select(DiscountCampaign).order_by(DiscountCampaign.id.desc()))
                    self.assertEqual((campaign.target_user_id, campaign.target_telegram_id), expected)
                    self.assertEqual(campaign.percent, 25)
                    self.assertEqual(campaign.ends_at - campaign.starts_at, timedelta(hours=24))
                    self.assertEqual(campaign.quota_total, 9 if not target else None)
                    self.assertEqual(campaign.plan_type, "1_month" if not target else None)

    async def test_bad_personal_discount_target_cannot_become_global_campaign(self):
        payload = {"kind": "discount", "title": "Account offer", "text": "Existing discount rules", "percent": 25}
        for target in ({"target_user_id": 1, "target_telegram_id": 1}, {"target_user_id": True},
                       {"target_user_id": 1.5}, {"target_user_id": None}, {"target_telegram_id": 0},
                       {"target_user_id": "9" * 100}):
            with self.subTest(target=target):
                response = await self.client.post("/campaigns", json={**payload, **target})
                self.assertEqual(response.status_code, 400, response.text)
        response = await self.client.post("/campaigns", json={**payload, "target_user_id": 9999})
        self.assertEqual(response.status_code, 404, response.text)
        async with self.sessions() as session:
            self.assertIsNone(await session.scalar(select(DiscountCampaign)))

    async def test_personal_telegram_message_is_rejected_for_unlinked_account(self):
        response = await self.client.post("/users/message", json={"user_id": 1, "text": "Hello learner"})
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["error"], "telegram_not_linked")
        self.bot.send_message.assert_not_awaited()

    async def test_trial_revoke_uses_canonical_owner_without_resetting_eligibility(self):
        async with self.sessions() as session:
            for uid in (1, 2):
                user = await session.get(User, uid)
                user.trial_used = True
                user.pro_trial_started_at = self.now
                user.pro_trial_ends_at = self.now + timedelta(days=7)
            await session.commit()
        response = await self.client.post("/api/admin-miniapp/trial/revoke",
            json={"user_id": 1, "reason": "test verified abuse"})
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as session:
            user, other = await session.get(User, 1), await session.get(User, 2)
            self.assertTrue(user.trial_used)
            self.assertIsNotNone(user.pro_trial_revoked_at)
            self.assertIsNone(other.pro_trial_revoked_at)
        response = await self.client.post("/api/admin-miniapp/trial/revoke", json={"user_id": 1, "telegram_id": 1})
        self.assertEqual(response.status_code, 400, response.text)

    async def test_unauthorized_management_request_is_rejected_before_database_or_transport(self):
        with patch.object(self.main, "_admin_auth_error", return_value=JSONResponse(status_code=403,
                content={"ok": False, "error": "admin_only"})):
            for path in ("detail", "give-access", "delete", "block", "message"):
                response = await self.client.post("/users/" + path, json={"user_id": 1})
                self.assertEqual(response.status_code, 403, response.text)
        self.bot.send_message.assert_not_awaited()


class AdminTargetParsingTests(unittest.TestCase):
    def test_only_explicit_positive_integer_identifiers_are_accepted(self):
        self.assertEqual(parse_admin_user_target({"user_id": " 1 "}), (1, None))
        self.assertEqual(parse_admin_user_target({"telegram_id": 1}), (None, 1))
        self.assertEqual(parse_admin_user_target({"user_id": 2, "telegram_id": 1}), (2, 1))
        for value in (None, True, False, 0, -1, 1.5, "1.5", "", "²", "9" * 100):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_admin_user_target({"user_id": value})

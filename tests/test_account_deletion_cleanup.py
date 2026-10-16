"""Account purge keeps financial history and never treats NULL as an identity."""

import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import MetaData, event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.account_notice_delivery import AccountNoticeDelivery
from app.db.models.android_push import AndroidPushToken
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.desktop import DesktopDevice, DesktopLinkRequest, DesktopSession
from app.db.models.discount_campaign import DiscountCampaign
from app.db.models.partner import Partner, PartnerReferral
from app.db.models.payment import Payment
from app.db.models.portfolio import PortfolioTransaction
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.repositories.user_repo import UserRepository


class AccountDeletionCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )

        @event.listens_for(self.engine.sync_engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        # Exercise a future Telegram-less shape without changing the live ORM
        # metadata or shipping an unrelated identity/account-creation migration.
        schema = MetaData()
        for table in Base.metadata.sorted_tables:
            table.to_metadata(schema)
        for name in (
            "users", "desktop_devices", "course_miniapp_events",
            "account_notice_deliveries",
        ):
            schema.tables[name].c.telegram_id.nullable = True
        async with self.engine.begin() as connection:
            await connection.run_sync(schema.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _seed_accounts(self, *, telegramless=False):
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            session.add_all([
                User(id=1, telegram_id=None if telegramless else 1001, full_name="Delete me"),
                User(id=2, telegram_id=None if telegramless else 1002, full_name="Keep me",
                     referrer_id=1, referred_by_telegram_id=None if telegramless else 1001),
                User(id=3, telegram_id=1003, full_name="Independent", referrer_id=2,
                     referred_by_telegram_id=1002),
            ])
            await session.flush()
            for uid in (1, 2):
                tid = None if telegramless else 1000 + uid
                session.add_all([
                    CourseMiniAppProfile(user_id=uid, display_name=f"Learner {uid}"),
                    CourseProgress(user_id=uid, level="hsk1"),
                    DesktopDevice(id=f"device-{uid}", user_id=uid, telegram_id=tid,
                                  installation_key_hash=f"install-{uid}", platform="android",
                                  app_version="1.0.0"),
                    DesktopLinkRequest(id=f"link-{uid}", bind_user_id=uid,
                                       approved_user_id=uid, approved_telegram_id=tid,
                                       flow="google", intent="link", status="approved",
                                       display_code_hash=f"display-{uid}",
                                       polling_secret_hash=f"poll-{uid}",
                                       installation_key_hash=f"install-{uid}",
                                       platform="android", app_version="1.0.0",
                                       expires_at=now + timedelta(minutes=10)),
                    CourseMiniAppEvent(id=uid, user_id=uid, telegram_id=tid,
                                       event_name="miniapp_opened"),
                    AccountNoticeDelivery(id=uid, user_id=uid, telegram_id=tid,
                                          key="subscription", title="Notice", body="Account",
                                          status="android_pending"),
                ])
                for provider in ("google", "apple"):
                    session.add(UserIdentity(
                        id=f"{provider}-{uid}", user_id=uid, provider=provider,
                        subject_hash=f"subject-{provider}-{uid}", email_display=f"u{uid}@example.test",
                    ))
            await session.flush()
            for uid in (1, 2):
                session.add_all([
                    DesktopSession(id=f"session-{uid}", device_id=f"device-{uid}",
                                   refresh_token_hash=f"refresh-{uid}",
                                   expires_at=now + timedelta(days=30)),
                    AndroidPushToken(device_id=f"device-{uid}", token=f"push-{uid}"),
                ])
            session.add_all([
                # An anonymous event and a pending unowned OAuth attempt must
                # survive deletion of an account with no Telegram identity.
                CourseMiniAppEvent(id=3, user_id=None, telegram_id=None if telegramless else 1002,
                                   event_name="miniapp_opened"),
                DesktopLinkRequest(id="unowned-link", flow="apple", intent="signin",
                                   display_code_hash="unowned-display", polling_secret_hash="unowned-poll",
                                   installation_key_hash="unowned-install", platform="android",
                                   app_version="1.0.0", expires_at=now + timedelta(minutes=10)),
                PortfolioTransaction(id=10, transaction_type="profit", source="manual",
                                     user_telegram_id=None, amount_usd=25.0, note="Company ledger"),
            ])
            for cid, target in ((2, 1002), (3, None)):
                session.add(DiscountCampaign(
                    id=cid, title="Retain campaign", percent=10, target_telegram_id=target,
                    starts_at=now, ends_at=now + timedelta(days=10),
                ))
            if not telegramless:
                session.add(DiscountCampaign(
                    id=1, title="Personal campaign", percent=10, target_telegram_id=1001,
                    starts_at=now, ends_at=now + timedelta(days=10),
                ))
            await session.commit()

    async def _rows(self, session, model):
        return list((await session.execute(select(model))).scalars().all())

    async def _assert_account_cleanup(self, session):
        self.assertEqual({u.id for u in await self._rows(session, User)}, {2, 3})
        self.assertEqual({p.user_id for p in await self._rows(session, CourseMiniAppProfile)}, {2})
        self.assertEqual({p.user_id for p in await self._rows(session, CourseProgress)}, {2})
        self.assertEqual({i.user_id for i in await self._rows(session, UserIdentity)}, {2})
        self.assertEqual({d.id for d in await self._rows(session, DesktopDevice)}, {"device-2"})
        self.assertEqual({s.id for s in await self._rows(session, DesktopSession)}, {"session-2"})
        self.assertEqual({p.device_id for p in await self._rows(session, AndroidPushToken)}, {"device-2"})
        self.assertEqual({r.id for r in await self._rows(session, DesktopLinkRequest)},
                         {"link-2", "unowned-link"})
        self.assertEqual({e.id for e in await self._rows(session, CourseMiniAppEvent)}, {2, 3})
        self.assertEqual({n.id for n in await self._rows(session, AccountNoticeDelivery)}, {2})
        self.assertEqual({c.id for c in await self._rows(session, DiscountCampaign)}, {2, 3})
        kept = await session.get(User, 2)
        independent = await session.get(User, 3)
        self.assertIsNone(kept.referrer_id)
        self.assertIsNone(kept.referred_by_telegram_id)
        self.assertEqual(independent.referrer_id, 2)
        self.assertEqual(independent.referred_by_telegram_id, 1002)
        ledger = await session.get(PortfolioTransaction, 10)
        self.assertIsNone(ledger.user_telegram_id)
        self.assertEqual(ledger.note, "Company ledger")

    async def test_internal_id_purge_preserves_approved_financial_retention(self):
        await self._seed_accounts()
        async with self.sessions() as session:
            session.add_all([
                Payment(id=1, user_telegram_id=1001, plan_type="monthly", amount=50,
                        payment_status="approved", screenshot_file_id="private-proof",
                        admin_comment="private-comment", checkout_msg_id=10,
                        screenshot_msg_id=11, waiting_msg_id=12),
                Payment(id=2, user_telegram_id=1001, plan_type="monthly", amount=50,
                        payment_status="pending"),
                Payment(id=3, user_telegram_id=1001, plan_type="monthly", amount=50,
                        payment_status="rejected"),
                Payment(id=4, user_telegram_id=1002, plan_type="monthly", amount=100,
                        payment_status="approved"),
                PortfolioTransaction(id=1, transaction_type="profit", source="subscription_profit",
                                     payment_id=1, user_telegram_id=1001, amount_usd=5.0),
                PortfolioTransaction(id=2, transaction_type="profit", source="manual",
                                     user_telegram_id=1001, amount_usd=2.0),
                PortfolioTransaction(id=3, transaction_type="profit", source="subscription_profit",
                                     payment_id=4, user_telegram_id=1002, amount_usd=10.0),
                Partner(id=1, user_telegram_id=1001, promotion_channel="Private channel",
                        audience_size="100", contact_username="private-name"),
            ])
            await session.flush()
            session.add(PartnerReferral(partner_id=1, invited_user_telegram_id=1001))
            # Legacy event has lost its user_id but must still be erased by the
            # Telegram key when deleting through the canonical internal ID.
            session.add(CourseMiniAppEvent(id=4, user_id=None, telegram_id=1001,
                                          event_name="miniapp_opened"))
            await session.commit()

            self.assertTrue(await UserRepository(session).delete_by_user_id(1))
            await session.commit()
            await self._assert_account_cleanup(session)
            payments = {p.id: p for p in await self._rows(session, Payment)}
            self.assertEqual(set(payments), {1, 4})
            self.assertEqual((payments[1].user_telegram_id, payments[1].amount), (-1, 50))
            for field in ("screenshot_file_id", "admin_comment", "checkout_msg_id",
                          "screenshot_msg_id", "waiting_msg_id"):
                self.assertIsNone(getattr(payments[1], field))
            self.assertEqual(payments[4].user_telegram_id, 1002)
            ledgers = {p.id: p for p in await self._rows(session, PortfolioTransaction)}
            self.assertEqual((ledgers[1].user_telegram_id, ledgers[1].payment_id,
                              ledgers[1].amount_usd), (-1, 1, 5.0))
            self.assertEqual(ledgers[2].user_telegram_id, -1)
            self.assertEqual(ledgers[3].user_telegram_id, 1002)
            partner = await session.get(Partner, 1)
            self.assertEqual((partner.user_telegram_id, partner.status), (-1, "blocked"))
            self.assertEqual(partner.contact_username, "[deleted]")
            self.assertEqual((await self._rows(session, PartnerReferral))[0].invited_user_telegram_id, -1)

    async def test_telegramless_purge_does_not_match_unrelated_null_identifiers(self):
        await self._seed_accounts(telegramless=True)
        async with self.sessions() as session:
            self.assertTrue(await UserRepository(session).delete_by_user_id(1))
            await session.commit()
            await self._assert_account_cleanup(session)

    async def test_legacy_telegram_entry_point_uses_same_cleanup(self):
        await self._seed_accounts()
        async with self.sessions() as session:
            self.assertTrue(await UserRepository(session).delete_by_telegram_id(1001))
            await session.commit()
            await self._assert_account_cleanup(session)

    async def test_caller_rollback_restores_account_and_missing_user_is_noop(self):
        await self._seed_accounts()
        async with self.sessions() as session:
            repo = UserRepository(session)
            self.assertFalse(await repo.delete_by_user_id(999))
            self.assertTrue(await repo.delete_by_user_id(1))
            await session.rollback()
        async with self.sessions() as session:
            self.assertIsNotNone(await session.get(User, 1))
            self.assertIsNotNone(await session.get(DesktopSession, "session-1"))
            self.assertEqual(len(await self._rows(session, UserIdentity)), 4)


if __name__ == "__main__":
    unittest.main()

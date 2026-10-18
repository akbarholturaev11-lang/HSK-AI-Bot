"""Affiliate credits follow the payment owner; Telegram remains its transport."""

from datetime import datetime, timezone
from decimal import Decimal
import unittest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.partner import Partner, PartnerCredit, PartnerReferral
from app.db.models.payment import Payment
from app.db.models.user import User
from app.services.partner_service import PartnerService


class PartnerPaymentOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all([
                User(id=1, telegram_id=None, language="uz"),
                User(id=2, telegram_id=2002, language="uz"),
                User(id=3, telegram_id=3003, language="uz"),
                Partner(id=1, user_telegram_id=9001, status="active", promotion_channel="A",
                        audience_size="100", contact_username="partner_a"),
                Partner(id=2, user_telegram_id=9002, status="active", promotion_channel="B",
                        audience_size="100", contact_username="partner_b"),
            ])
            await session.flush()
            session.add_all([
                PartnerReferral(partner_id=1, invited_user_telegram_id=2002),
                PartnerReferral(partner_id=2, invited_user_telegram_id=3003),
                PartnerCredit(partner_id=1, credit_type="signup_bonus", amount_usd=1, is_locked=True),
                PartnerCredit(partner_id=2, credit_type="signup_bonus", amount_usd=1, is_locked=True),
            ])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def payment(self, session, *, user_id=2, telegram_id=2002, **fields):
        values = dict(user_id=user_id, user_telegram_id=telegram_id, plan_type="1_month",
                      amount=10, currency="USD", payment_status="approved",
                      reviewed_at=datetime(2026, 10, 18, tzinfo=timezone.utc))
        values.update(fields)
        payment = Payment(**values)
        session.add(payment)
        await session.flush()
        return payment

    async def assert_no_attribution(self, session, payment):
        self.assertEqual(await PartnerService(session).record_approved_payment(payment),
                         (None, Decimal("0.00"), False))
        self.assertEqual(list((await session.scalars(select(PartnerCredit).where(
            PartnerCredit.payment_id == payment.id))).all()), [])
        self.assertTrue(all(credit.is_locked for credit in (await session.scalars(
            select(PartnerCredit).where(PartnerCredit.credit_type == "signup_bonus"))).all()))
        self.assertTrue(all(referral.first_paid_at is None for referral in (
            await session.scalars(select(PartnerReferral))).all()))

    async def test_native_owner_cannot_credit_foreign_telegram_referral(self):
        async with self.sessions() as session:
            await self.assert_no_attribution(session, await self.payment(session, user_id=1, telegram_id=3003))

    async def test_canonical_owner_overrides_foreign_telegram_metadata(self):
        async with self.sessions() as session:
            payment = await self.payment(session, telegram_id=3003)
            partner, amount, unlocked = await PartnerService(session).record_approved_payment(payment)
            self.assertEqual((partner.id, amount, unlocked), (1, Decimal("2.00"), True))
            credit = await session.scalar(select(PartnerCredit).where(PartnerCredit.payment_id == payment.id))
            self.assertEqual(credit.partner_id, 1)
            foreign = await session.scalar(select(PartnerReferral).where(
                PartnerReferral.invited_user_telegram_id == 3003))
            self.assertIsNone(foreign.first_paid_at)
            foreign_bonus = await session.scalar(select(PartnerCredit).where(
                PartnerCredit.partner_id == 2, PartnerCredit.credit_type == "signup_bonus"))
            self.assertTrue(foreign_bonus.is_locked)
            self.assertEqual((payment.user_id, payment.user_telegram_id), (2, 3003))

    async def test_current_attached_telegram_is_resolved_without_rewriting_old_payment(self):
        async with self.sessions() as session:
            payment = await self.payment(session, user_id=1, telegram_id=None)
            owner = await session.get(User, 1)
            owner.telegram_id = 4004
            session.add(PartnerReferral(partner_id=1, invited_user_telegram_id=4004))
            await session.flush()
            partner, amount, unlocked = await PartnerService(session).record_approved_payment(payment)
            self.assertEqual((partner.id, amount, unlocked), (1, Decimal("2.00"), True))
            self.assertIsNone(payment.user_telegram_id)

    async def test_missing_canonical_owner_never_falls_back_to_foreign_metadata(self):
        async with self.sessions() as session:
            await self.assert_no_attribution(session, await self.payment(session, user_id=999, telegram_id=3003))

    async def test_native_without_telegram_is_not_a_partner_program_referral(self):
        async with self.sessions() as session:
            await self.assert_no_attribution(session, await self.payment(session, user_id=1, telegram_id=None))

    async def test_legacy_telegram_payment_keeps_commission_bonus_and_replay_rules(self):
        async with self.sessions() as session:
            payment = await self.payment(session, user_id=None)
            service = PartnerService(session)
            partner, amount, unlocked = await service.record_approved_payment(payment)
            self.assertEqual((partner.id, amount, unlocked), (1, Decimal("2.00"), True))
            referral = await session.scalar(select(PartnerReferral).where(
                PartnerReferral.invited_user_telegram_id == 2002))
            self.assertEqual(referral.first_paid_at.replace(tzinfo=timezone.utc), payment.reviewed_at)
            self.assertEqual(await service.record_approved_payment(payment), (None, Decimal("0.00"), False))
            credits = list((await session.scalars(select(PartnerCredit).where(
                PartnerCredit.payment_id == payment.id))).all())
            self.assertEqual(len(credits), 1)
            self.assertEqual((credits[0].credit_type, credits[0].amount_usd),
                             ("paid_referral_commission", Decimal("2.00")))

    async def test_fixed_commission_setting_is_unchanged_for_canonical_owner(self):
        async with self.sessions() as session:
            service = PartnerService(session)
            await service.set_commission_mode("fixed")
            await service.set_commission_usd(Decimal("1.25"))
            payment = await self.payment(session)
            partner, amount, _ = await service.record_approved_payment(payment)
            self.assertEqual((partner.id, amount), (1, Decimal("1.25")))

    async def test_ineligible_payments_still_do_not_credit_or_unlock_bonus(self):
        for fields in ({"plan_type": "hsk30_unlock"}, {"payment_status": "pending"},
                       {"user_id": None, "telegram_id": -123}, {"user_id": None, "telegram_id": None}):
            with self.subTest(fields=fields):
                async with self.sessions() as session:
                    await self.assert_no_attribution(session, await self.payment(session, **fields))
                    await session.rollback()

    async def test_inactive_partner_does_not_receive_credit(self):
        async with self.sessions() as session:
            partner = await session.get(Partner, 1)
            partner.status = "blocked"
            await self.assert_no_attribution(session, await self.payment(session))

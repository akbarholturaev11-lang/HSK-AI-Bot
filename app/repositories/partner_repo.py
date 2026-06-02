from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.partner import Partner, PartnerCredit, PartnerPayout, PartnerReferral


PAYOUT_EDITABLE_STATUSES = ("pending", "deadline_set")
PAYOUT_PROCESSING_STATUS = "processing"
PAYOUT_OPEN_STATUSES = (*PAYOUT_EDITABLE_STATUSES, PAYOUT_PROCESSING_STATUS)


class PartnerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, partner_id: int) -> Optional[Partner]:
        return await self.session.get(Partner, partner_id)

    async def get_by_id_for_update(self, partner_id: int) -> Optional[Partner]:
        result = await self.session.execute(
            select(Partner).where(Partner.id == partner_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Partner]:
        result = await self.session.execute(
            select(Partner).where(Partner.user_telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def submit_application(
        self,
        *,
        telegram_id: int,
        promotion_channel: str,
        audience_size: str,
        contact_username: str,
    ) -> Partner:
        partner = await self.get_by_telegram_id(telegram_id)
        if partner:
            partner.promotion_channel = promotion_channel
            partner.audience_size = audience_size
            partner.contact_username = contact_username
            partner.status = "pending"
            partner.blocked_at = None
        else:
            partner = Partner(
                user_telegram_id=telegram_id,
                status="pending",
                promotion_channel=promotion_channel,
                audience_size=audience_size,
                contact_username=contact_username,
            )
            self.session.add(partner)
        await self.session.flush()
        return partner

    async def set_status(self, partner: Partner, status: str, admin_telegram_id: int) -> None:
        now = datetime.now(timezone.utc)
        partner.status = status
        if status == "active":
            partner.approved_by_telegram_id = admin_telegram_id
            partner.approved_at = partner.approved_at or now
            partner.blocked_at = None
        elif status == "blocked":
            partner.blocked_at = now
        await self.session.flush()

    async def list_by_status(self, status: str, limit: int = 30) -> list[Partner]:
        result = await self.session.execute(
            select(Partner)
            .where(Partner.status == status)
            .order_by(Partner.created_at.asc(), Partner.id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_referral_by_invited_user(self, telegram_id: int) -> Optional[PartnerReferral]:
        result = await self.session.execute(
            select(PartnerReferral).where(PartnerReferral.invited_user_telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def create_referral(self, partner_id: int, invited_user_telegram_id: int) -> PartnerReferral:
        referral = PartnerReferral(
            partner_id=partner_id,
            invited_user_telegram_id=invited_user_telegram_id,
        )
        self.session.add(referral)
        await self.session.flush()
        return referral

    async def count_referrals(self, partner_id: int) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(PartnerReferral).where(PartnerReferral.partner_id == partner_id)
        )
        return int(result.scalar() or 0)

    async def count_paid_referrals(self, partner_id: int) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(PartnerReferral)
            .where(PartnerReferral.partner_id == partner_id)
            .where(PartnerReferral.first_paid_at.is_not(None))
        )
        return int(result.scalar() or 0)

    async def get_credit_by_payment(self, payment_id: int) -> Optional[PartnerCredit]:
        result = await self.session.execute(
            select(PartnerCredit).where(PartnerCredit.payment_id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_signup_bonus(self, partner_id: int) -> Optional[PartnerCredit]:
        result = await self.session.execute(
            select(PartnerCredit)
            .where(PartnerCredit.partner_id == partner_id)
            .where(PartnerCredit.credit_type == "signup_bonus")
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def claim_signup_bonus(self, partner_id: int) -> bool:
        existing_bonus = await self.get_signup_bonus(partner_id)
        if existing_bonus:
            await self.session.execute(
                update(Partner)
                .where(Partner.id == partner_id)
                .where(Partner.signup_bonus_granted_at.is_(None))
                .values(signup_bonus_granted_at=existing_bonus.created_at)
            )
            await self.session.flush()
            return False
        result = await self.session.execute(
            update(Partner)
            .where(Partner.id == partner_id)
            .where(Partner.signup_bonus_granted_at.is_(None))
            .values(signup_bonus_granted_at=datetime.now(timezone.utc))
            .returning(Partner.id)
        )
        await self.session.flush()
        return result.scalar_one_or_none() is not None

    async def add_credit(
        self,
        *,
        partner_id: int,
        credit_type: str,
        amount_usd: Decimal,
        payment_id: Optional[int] = None,
        is_locked: bool = False,
    ) -> PartnerCredit:
        credit = PartnerCredit(
            partner_id=partner_id,
            payment_id=payment_id,
            credit_type=credit_type,
            amount_usd=amount_usd,
            is_locked=is_locked,
        )
        self.session.add(credit)
        await self.session.flush()
        return credit

    async def unlock_signup_bonus(self, partner_id: int) -> bool:
        bonus = await self.get_signup_bonus(partner_id)
        if not bonus or not bonus.is_locked:
            return False
        bonus.is_locked = False
        bonus.unlocked_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    async def create_payout(
        self,
        *,
        partner_id: int,
        amount_usd: Decimal,
        exchange_rate: Decimal,
        local_amount: Decimal,
        local_currency: str,
        payment_method: str,
        bank_name: Optional[str],
        account_details: str,
        holder_name: Optional[str],
        note: Optional[str],
        recipient_qr_code_file_id: Optional[str],
    ) -> PartnerPayout:
        payout = PartnerPayout(
            partner_id=partner_id,
            amount_usd=amount_usd,
            exchange_rate=exchange_rate,
            local_amount=local_amount,
            local_currency=local_currency,
            status="pending",
            payment_method=payment_method,
            bank_name=bank_name,
            account_details=account_details,
            holder_name=holder_name,
            note=note,
            recipient_qr_code_file_id=recipient_qr_code_file_id,
        )
        self.session.add(payout)
        await self.session.flush()
        return payout

    async def get_payout(self, payout_id: int) -> Optional[PartnerPayout]:
        return await self.session.get(PartnerPayout, payout_id)

    async def list_open_payouts(self, limit: int = 40) -> list[PartnerPayout]:
        result = await self.session.execute(
            select(PartnerPayout)
            .where(PartnerPayout.status.in_(PAYOUT_OPEN_STATUSES))
            .order_by(PartnerPayout.created_at.asc(), PartnerPayout.id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def has_open_payout(self, partner_id: int) -> bool:
        result = await self.session.execute(
            select(PartnerPayout.id)
            .where(PartnerPayout.partner_id == partner_id)
            .where(PartnerPayout.status.in_(PAYOUT_OPEN_STATUSES))
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def claim_payout_for_payment(self, payout_id: int, admin_id: int) -> Optional[PartnerPayout]:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            update(PartnerPayout)
            .where(PartnerPayout.id == payout_id)
            .where(
                or_(
                    PartnerPayout.status.in_(PAYOUT_EDITABLE_STATUSES),
                    and_(
                        PartnerPayout.status == PAYOUT_PROCESSING_STATUS,
                        PartnerPayout.processing_by_telegram_id == admin_id,
                    ),
                )
            )
            .values(
                status=PAYOUT_PROCESSING_STATUS,
                processing_by_telegram_id=admin_id,
                processing_started_at=now,
            )
            .returning(PartnerPayout.id)
        )
        await self.session.flush()
        claimed_id = result.scalar_one_or_none()
        return await self.get_payout(claimed_id) if claimed_id is not None else None

    async def release_payout_payment(self, payout_id: int, admin_id: int) -> bool:
        result = await self.session.execute(
            update(PartnerPayout)
            .where(PartnerPayout.id == payout_id)
            .where(PartnerPayout.status == PAYOUT_PROCESSING_STATUS)
            .where(PartnerPayout.processing_by_telegram_id == admin_id)
            .values(
                status=case(
                    (PartnerPayout.deadline_at.is_not(None), "deadline_set"),
                    else_="pending",
                ),
                processing_by_telegram_id=None,
                processing_started_at=None,
            )
            .returning(PartnerPayout.id)
        )
        await self.session.flush()
        return result.scalar_one_or_none() is not None

    async def list_due_payout_reminders(self, now: Optional[datetime] = None) -> list[PartnerPayout]:
        now = now or datetime.now(timezone.utc)
        result = await self.session.execute(
            select(PartnerPayout)
            .where(PartnerPayout.status == "deadline_set")
            .where(PartnerPayout.deadline_at.is_not(None))
            .where(PartnerPayout.deadline_at <= now)
            .where(PartnerPayout.reminder_sent_at.is_(None))
            .order_by(PartnerPayout.deadline_at.asc())
        )
        return list(result.scalars().all())

    async def sum_unlocked_credits(self, partner_id: int) -> Decimal:
        result = await self.session.execute(
            select(func.sum(PartnerCredit.amount_usd))
            .where(PartnerCredit.partner_id == partner_id)
            .where(PartnerCredit.is_locked.is_(False))
        )
        return Decimal(result.scalar() or 0).quantize(Decimal("0.01"))

    async def sum_payouts(self, partner_id: int, statuses: tuple[str, ...]) -> Decimal:
        result = await self.session.execute(
            select(func.sum(PartnerPayout.amount_usd))
            .where(PartnerPayout.partner_id == partner_id)
            .where(PartnerPayout.status.in_(statuses))
        )
        return Decimal(result.scalar() or 0).quantize(Decimal("0.01"))

    async def set_payout_deadline(self, payout_id: int, deadline_at: datetime, admin_id: int) -> bool:
        result = await self.session.execute(
            update(PartnerPayout)
            .where(PartnerPayout.id == payout_id)
            .where(PartnerPayout.status.in_(PAYOUT_EDITABLE_STATUSES))
            .values(
                status="deadline_set",
                deadline_at=deadline_at,
                reminder_sent_at=None,
                reviewed_by_telegram_id=admin_id,
            )
            .returning(PartnerPayout.id)
        )
        await self.session.flush()
        return result.scalar_one_or_none() is not None

    async def mark_payout_paid(self, payout_id: int, screenshot_file_id: str, admin_id: int) -> bool:
        result = await self.session.execute(
            update(PartnerPayout)
            .where(PartnerPayout.id == payout_id)
            .where(PartnerPayout.status == PAYOUT_PROCESSING_STATUS)
            .where(PartnerPayout.processing_by_telegram_id == admin_id)
            .values(
                status="paid",
                proof_screenshot_file_id=screenshot_file_id,
                reviewed_by_telegram_id=admin_id,
                reviewed_at=datetime.now(timezone.utc),
                processing_by_telegram_id=None,
                processing_started_at=None,
            )
            .returning(PartnerPayout.id)
        )
        await self.session.flush()
        return result.scalar_one_or_none() is not None

    async def reject_payout(self, payout_id: int, admin_id: int) -> bool:
        result = await self.session.execute(
            update(PartnerPayout)
            .where(PartnerPayout.id == payout_id)
            .where(PartnerPayout.status.in_(PAYOUT_EDITABLE_STATUSES))
            .values(
                status="rejected",
                reviewed_by_telegram_id=admin_id,
                reviewed_at=datetime.now(timezone.utc),
                processing_by_telegram_id=None,
                processing_started_at=None,
            )
            .returning(PartnerPayout.id)
        )
        await self.session.flush()
        return result.scalar_one_or_none() is not None

    async def mark_reminder_sent(self, payout: PartnerPayout) -> None:
        payout.reminder_sent_at = datetime.now(timezone.utc)
        await self.session.flush()

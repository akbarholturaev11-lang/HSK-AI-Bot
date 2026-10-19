from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.discount_campaign import DiscountCampaign
from app.db.models.payment import Payment
from app.db.models.user import User
from app.repositories.payment_repo import PaymentRepository
from app.services.account_identity import account_user_id, actual_telegram_id, owner_clause


class DiscountCampaignRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _payment_owner_filter(self, actor):
        owner = await PaymentRepository(self.session).resolve_owner(actor)
        if owner is not None:
            return owner_clause(Payment, owner)
        telegram_id = actual_telegram_id(actor)
        if account_user_id(actor) is None and telegram_id is not None:
            return and_(Payment.user_id.is_(None), Payment.user_telegram_id == telegram_id)
        return false()

    async def create(
        self,
        *,
        title: str,
        title_tj: Optional[str] = None,
        title_ru: Optional[str] = None,
        title_uz: Optional[str] = None,
        reason: Optional[str] = None,
        reason_tj: Optional[str] = None,
        reason_ru: Optional[str] = None,
        reason_uz: Optional[str] = None,
        percent: int,
        starts_at: datetime,
        ends_at: datetime,
        audience_status: Optional[str] = None,
        audience_language: Optional[str] = None,
        audience_level: Optional[str] = None,
        target_user_id: Optional[int] = None,
        target_telegram_id: Optional[int] = None,
        payment_method: Optional[str] = None,
        plan_type: Optional[str] = None,
        quota_total: Optional[int] = None,
        repeat_interval_days: Optional[int] = None,
        notify_enabled: bool = False,
        notify_media_type: Optional[str] = None,
        notify_media_file_id: Optional[str] = None,
        created_by_telegram_id: Optional[int] = None,
    ) -> DiscountCampaign:
        # Personal offers belong to the account; an integer Telegram target
        # remains a real transport identity, never a guessed users.id.
        for target in (target_user_id, target_telegram_id):
            if target is not None and (isinstance(target, bool) or not isinstance(target, int) or target <= 0):
                raise ValueError("invalid_discount_target")
        if target_user_id is not None:
            target_user = await self.session.get(User, target_user_id)
            if target_user is None:
                raise ValueError("discount_target_user_not_found")
            real_telegram_id = actual_telegram_id(target_user)
            if target_telegram_id is not None and target_telegram_id != real_telegram_id:
                raise ValueError("discount_target_mismatch")
            target_telegram_id = real_telegram_id
        elif target_telegram_id is not None:
            # Unknown legacy Telegram targets must stay personal, even before
            # that Telegram account has registered with the bot.
            target_user_id = await self.session.scalar(
                select(User.id).where(User.telegram_id == target_telegram_id)
            )
        campaign = DiscountCampaign(
            title=title,
            title_tj=title_tj,
            title_ru=title_ru,
            title_uz=title_uz,
            reason=reason,
            reason_tj=reason_tj,
            reason_ru=reason_ru,
            reason_uz=reason_uz,
            percent=percent,
            starts_at=starts_at,
            ends_at=ends_at,
            audience_status=audience_status,
            audience_language=audience_language,
            audience_level=audience_level,
            target_user_id=target_user_id,
            target_telegram_id=target_telegram_id,
            payment_method=payment_method,
            plan_type=plan_type,
            quota_total=quota_total,
            repeat_interval_days=repeat_interval_days,
            notify_enabled=notify_enabled,
            notify_media_type=notify_media_type,
            notify_media_file_id=notify_media_file_id,
            created_by_telegram_id=created_by_telegram_id,
        )
        self.session.add(campaign)
        await self.session.flush()
        return campaign

    async def get_by_id(self, campaign_id: int) -> Optional[DiscountCampaign]:
        result = await self.session.execute(
            select(DiscountCampaign).where(DiscountCampaign.id == campaign_id)
        )
        return result.scalar_one_or_none()

    async def list_recent(self, limit: int = 10) -> list[DiscountCampaign]:
        result = await self.session.execute(
            select(DiscountCampaign)
            .order_by(DiscountCampaign.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_current(self, now: Optional[datetime] = None) -> list[DiscountCampaign]:
        now = now or datetime.now(timezone.utc)
        result = await self.session.execute(
            select(DiscountCampaign)
            .where(DiscountCampaign.is_active.is_(True))
            .where(DiscountCampaign.starts_at <= now)
            .where(DiscountCampaign.ends_at > now)
            .order_by(DiscountCampaign.percent.desc(), DiscountCampaign.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_due_notifications(self, now: Optional[datetime] = None) -> list[DiscountCampaign]:
        now = now or datetime.now(timezone.utc)
        result = await self.session.execute(
            select(DiscountCampaign)
            .where(DiscountCampaign.is_active.is_(True))
            .where(DiscountCampaign.notify_enabled.is_(True))
            .where(DiscountCampaign.notification_sent_at.is_(None))
            .where(DiscountCampaign.starts_at <= now)
            .where(DiscountCampaign.ends_at > now)
            .order_by(DiscountCampaign.starts_at.asc(), DiscountCampaign.id.asc())
        )
        return list(result.scalars().all())

    async def mark_notification_sent(
        self,
        campaign: DiscountCampaign,
        *,
        sent_count: int,
        failed_count: int,
        now: Optional[datetime] = None,
    ) -> None:
        campaign.notification_sent_at = now or datetime.now(timezone.utc)
        campaign.notification_sent_count = sent_count
        campaign.notification_failed_count = failed_count
        await self.session.flush()

    async def deactivate(self, campaign: DiscountCampaign) -> None:
        campaign.is_active = False
        await self.session.flush()

    async def count_used(
        self,
        campaign_id: int,
        *,
        now: Optional[datetime] = None,
        exclude_user_telegram_id: Optional[int] = None,
        exclude_user=None,
    ) -> int:
        now = now or datetime.now(timezone.utc)
        fresh_draft_after = now - timedelta(minutes=30)
        query = select(func.count()).select_from(Payment).where(
            Payment.discount_campaign_id == campaign_id,
            or_(
                Payment.payment_status.in_(("pending", "approved")),
                and_(
                    Payment.payment_status == "draft",
                    Payment.submitted_at >= fresh_draft_after,
                ),
            ),
        )
        actor = exclude_user if exclude_user is not None else exclude_user_telegram_id
        if actor is not None:
            # NULL ownership belongs to other legacy/native rows, not to the
            # excluded learner. SQL NOT(NULL) would incorrectly drop those.
            query = query.where(~func.coalesce(await self._payment_owner_filter(actor), False))
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_user_last_usage(
        self,
        campaign_id: int,
        user_telegram_id: int,
    ) -> Optional[Payment]:
        result = await self.session.execute(
            select(Payment)
            .where(Payment.discount_campaign_id == campaign_id)
            .where(await self._payment_owner_filter(user_telegram_id))
            .where(Payment.payment_status.in_(("pending", "approved")))
            .order_by(Payment.submitted_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

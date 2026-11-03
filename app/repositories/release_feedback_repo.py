from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.payment import Payment
from app.db.models.user import User
from app.services.account_identity import actual_telegram_id, owner_clause
from app.services.admin_analytics_identity import analytics_account_key
from app.db.models.release_feedback import (
    ReleaseFeedbackCampaign,
    ReleaseFeedbackDelivery,
    ReleaseFeedbackResponse,
)


def encode_languages(languages: Optional[list[str]]) -> Optional[str]:
    if not languages:
        return None
    clean = [item for item in languages if item in {"uz", "ru", "tj"}]
    return ",".join(sorted(set(clean))) or None


def decode_languages(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [item for item in value.split(",") if item in {"uz", "ru", "tj"}]


@dataclass(frozen=True)
class ReleaseFeedbackStats:
    delivered: int = 0
    failed: int = 0
    responses: int = 0
    average_rating: float = 0.0
    comments: int = 0
    rating_1: int = 0
    rating_2: int = 0
    rating_3: int = 0
    rating_4: int = 0
    rating_5: int = 0
    discount_offered: int = 0
    discount_used: int = 0
    try_clicked: int = 0
    trial_granted: int = 0


class ReleaseFeedbackRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_campaign(
        self,
        *,
        title: str,
        message_text: Optional[str],
        content_type: str,
        media_file_id: Optional[str],
        send_at: datetime,
        feature_key: str = "general",
        target_languages: Optional[list[str]] = None,
        status_filter: Optional[str] = None,
        level_filter: Optional[str] = None,
        mode_filter: Optional[str] = None,
        payment_status_filter: Optional[str] = None,
        payment_method_filter: Optional[str] = None,
        plan_filter: Optional[str] = None,
        discount_filter: Optional[str] = None,
        course_promo_filter: Optional[str] = None,
        activity_filter: Optional[str] = None,
        created_by_telegram_id: Optional[int] = None,
        discount_percent: int = 20,
        discount_hours: int = 24,
        trial_access_minutes: int = 30,
    ) -> ReleaseFeedbackCampaign:
        campaign = ReleaseFeedbackCampaign(
            title=title,
            message_text=message_text,
            content_type=content_type,
            media_file_id=media_file_id,
            feature_key=feature_key or "general",
            status="scheduled",
            send_at=send_at,
            target_languages=encode_languages(target_languages),
            status_filter=status_filter,
            level_filter=level_filter,
            mode_filter=mode_filter,
            payment_status_filter=payment_status_filter,
            payment_method_filter=payment_method_filter,
            plan_filter=plan_filter,
            discount_filter=discount_filter,
            course_promo_filter=course_promo_filter,
            activity_filter=activity_filter,
            discount_percent=discount_percent,
            discount_hours=discount_hours,
            trial_access_minutes=trial_access_minutes,
            created_by_telegram_id=created_by_telegram_id,
        )
        self.session.add(campaign)
        await self.session.flush()
        return campaign

    async def get_campaign(self, campaign_id: int) -> Optional[ReleaseFeedbackCampaign]:
        result = await self.session.execute(
            select(ReleaseFeedbackCampaign).where(ReleaseFeedbackCampaign.id == campaign_id)
        )
        return result.scalar_one_or_none()

    async def list_recent_campaigns(self, limit: int = 10) -> list[ReleaseFeedbackCampaign]:
        result = await self.session.execute(
            select(ReleaseFeedbackCampaign)
            .order_by(ReleaseFeedbackCampaign.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_due_campaigns(self, now: Optional[datetime] = None) -> list[ReleaseFeedbackCampaign]:
        now = now or datetime.now(timezone.utc)
        result = await self.session.execute(
            select(ReleaseFeedbackCampaign)
            .where(ReleaseFeedbackCampaign.status == "scheduled")
            .where(ReleaseFeedbackCampaign.send_at <= now)
            .order_by(ReleaseFeedbackCampaign.send_at.asc(), ReleaseFeedbackCampaign.id.asc())
        )
        return list(result.scalars().all())

    async def mark_sending(self, campaign: ReleaseFeedbackCampaign) -> None:
        campaign.status = "sending"
        await self.session.flush()

    async def mark_sent(
        self,
        campaign: ReleaseFeedbackCampaign,
        *,
        sent_count: int,
        failed_count: int,
        now: Optional[datetime] = None,
    ) -> None:
        campaign.status = "sent"
        campaign.sent_at = now or datetime.now(timezone.utc)
        campaign.sent_count = sent_count
        campaign.failed_count = failed_count
        await self.session.flush()

    async def stop_campaign(self, campaign: ReleaseFeedbackCampaign) -> None:
        campaign.status = "stopped"
        await self.session.flush()

    async def list_delivery_user_ids(self, campaign_id: int) -> set[int]:
        result = await self.session.execute(
            select(ReleaseFeedbackDelivery.user_telegram_id)
            .where(ReleaseFeedbackDelivery.campaign_id == campaign_id)
        )
        return {int(item) for item in result.scalars().all()}

    async def _canonical_owner(
        self, *, user: Optional[User], user_telegram_id: Optional[int],
    ) -> User:
        """Resolve a real account, never synthesize a Telegram ID from users.id."""
        tid = actual_telegram_id(user_telegram_id)
        if user is None and tid is not None:
            user = (await self.session.execute(
                select(User).where(User.telegram_id == tid)
            )).scalar_one_or_none()
        if user is None or not isinstance(user.id, int) or user.id <= 0:
            raise ValueError("feedback_account_not_found")
        if tid is not None and actual_telegram_id(user) != tid:
            raise ValueError("feedback_transport_owner_mismatch")
        return user

    async def create_delivery(
        self,
        *,
        campaign_id: int,
        user_telegram_id: Optional[int] = None,
        user: Optional[User] = None,
        status: str,
        message_id: Optional[int] = None,
        error: Optional[str] = None,
    ) -> ReleaseFeedbackDelivery:
        owner = await self._canonical_owner(
            user=user, user_telegram_id=user_telegram_id,
        )
        delivery = ReleaseFeedbackDelivery(
            campaign_id=campaign_id,
            user_id=owner.id,
            user_telegram_id=actual_telegram_id(owner),
            status=status,
            message_id=message_id,
            error=(error or "")[:300] or None,
        )
        self.session.add(delivery)
        await self.session.flush()
        return delivery

    async def get_delivery(
        self,
        *,
        campaign_id: int,
        user_telegram_id: Optional[int] = None,
        user: Optional[User] = None,
    ) -> Optional[ReleaseFeedbackDelivery]:
        actor = user if user is not None else actual_telegram_id(user_telegram_id)
        if actor is None:
            return None
        result = await self.session.execute(
            select(ReleaseFeedbackDelivery)
            .where(ReleaseFeedbackDelivery.campaign_id == campaign_id)
            .where(owner_clause(
                ReleaseFeedbackDelivery, actor, telegram_column="user_telegram_id",
            ))
            # An unowned historical TG row might be linked later to an
            # account that already answered in the browser. Canonical wins.
            .order_by(
                ReleaseFeedbackDelivery.user_id.is_(None),
                ReleaseFeedbackDelivery.id.desc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def mark_try_clicked(
        self,
        *,
        campaign_id: int,
        user_telegram_id: Optional[int] = None,
        user: Optional[User] = None,
        trial_granted_until: Optional[datetime] = None,
    ) -> ReleaseFeedbackDelivery:
        owner = await self._canonical_owner(
            user=user, user_telegram_id=user_telegram_id,
        )
        now = datetime.now(timezone.utc)
        delivery = await self.get_delivery(
            campaign_id=campaign_id, user=owner,
        )
        if not delivery:
            delivery = ReleaseFeedbackDelivery(
                campaign_id=campaign_id,
                user_id=owner.id,
                user_telegram_id=actual_telegram_id(owner),
                status="clicked",
            )
            self.session.add(delivery)
        delivery.try_clicked_at = delivery.try_clicked_at or now
        if trial_granted_until and delivery.trial_granted_until is None:
            delivery.trial_granted_until = trial_granted_until
        await self.session.flush()
        return delivery

    async def get_response(
        self,
        *,
        campaign_id: int,
        user_telegram_id: Optional[int] = None,
        user: Optional[User] = None,
    ) -> Optional[ReleaseFeedbackResponse]:
        actor = user if user is not None else actual_telegram_id(user_telegram_id)
        if actor is None:
            return None
        result = await self.session.execute(
            select(ReleaseFeedbackResponse)
            .where(ReleaseFeedbackResponse.campaign_id == campaign_id)
            .where(owner_clause(
                ReleaseFeedbackResponse, actor, telegram_column="user_telegram_id",
            ))
            # An unowned historical TG row might be linked later to an
            # account that already answered in the browser. Canonical wins.
            .order_by(
                ReleaseFeedbackResponse.user_id.is_(None),
                ReleaseFeedbackResponse.id.desc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_response(
        self,
        *,
        campaign_id: int,
        rating: int,
        user_telegram_id: Optional[int] = None,
        user: Optional[User] = None,
        comment_text: Optional[str] = None,
        attachment_file_id: Optional[str] = None,
        attachment_type: Optional[str] = None,
        discount_campaign_id: Optional[int] = None,
    ) -> ReleaseFeedbackResponse:
        owner = await self._canonical_owner(
            user=user, user_telegram_id=user_telegram_id,
        )
        now = datetime.now(timezone.utc)
        response = ReleaseFeedbackResponse(
            campaign_id=campaign_id,
            user_id=owner.id,
            user_telegram_id=actual_telegram_id(owner),
            rating=rating,
            comment_text=comment_text,
            attachment_file_id=attachment_file_id,
            attachment_type=attachment_type,
            discount_campaign_id=discount_campaign_id,
            completed_at=now,
            updated_at=now,
        )
        self.session.add(response)
        await self.session.flush()
        return response

    async def update_response_comment(
        self,
        response: ReleaseFeedbackResponse,
        *,
        comment_text: Optional[str],
        attachment_file_id: Optional[str] = None,
        attachment_type: Optional[str] = None,
    ) -> None:
        response.comment_text = comment_text
        response.attachment_file_id = attachment_file_id
        response.attachment_type = attachment_type
        response.updated_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def attach_discount_campaign(
        self,
        response: ReleaseFeedbackResponse,
        discount_campaign_id: int,
    ) -> None:
        response.discount_campaign_id = discount_campaign_id
        response.updated_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def count_deliveries(self, campaign_id: int, status: Optional[str] = None) -> int:
        query = select(func.count()).select_from(ReleaseFeedbackDelivery).where(
            ReleaseFeedbackDelivery.campaign_id == campaign_id
        )
        if status:
            query = query.where(ReleaseFeedbackDelivery.status == status)
        result = await self.session.execute(query)
        return int(result.scalar() or 0)

    async def stats(self, campaign_id: int) -> ReleaseFeedbackStats:
        delivered = await self.count_deliveries(campaign_id, "sent")
        failed = await self.count_deliveries(campaign_id, "failed")

        rows = (await self.session.execute(
            select(ReleaseFeedbackResponse.rating, func.count().label("cnt"))
            .where(ReleaseFeedbackResponse.campaign_id == campaign_id)
            .group_by(ReleaseFeedbackResponse.rating)
        )).fetchall()
        rating_counts = {int(row.rating): int(row.cnt) for row in rows}

        avg_rating = (await self.session.execute(
            select(func.avg(ReleaseFeedbackResponse.rating))
            .where(ReleaseFeedbackResponse.campaign_id == campaign_id)
        )).scalar()
        comments = (await self.session.execute(
            select(func.count())
            .select_from(ReleaseFeedbackResponse)
            .where(ReleaseFeedbackResponse.campaign_id == campaign_id)
            .where(
                (ReleaseFeedbackResponse.comment_text.is_not(None))
                | (ReleaseFeedbackResponse.attachment_file_id.is_not(None))
            )
        )).scalar() or 0
        discount_offered = (await self.session.execute(
            select(func.count())
            .select_from(ReleaseFeedbackResponse)
            .where(ReleaseFeedbackResponse.campaign_id == campaign_id)
            .where(ReleaseFeedbackResponse.discount_campaign_id.is_not(None))
        )).scalar() or 0
        discount_used = (await self.session.execute(
            select(func.count(func.distinct(analytics_account_key(Payment, telegram_column="user_telegram_id"))))
            .select_from(Payment)
            .join(
                ReleaseFeedbackResponse,
                ReleaseFeedbackResponse.discount_campaign_id == Payment.discount_campaign_id,
            )
            .where(ReleaseFeedbackResponse.campaign_id == campaign_id)
            .where(Payment.payment_status.in_(("pending", "approved")))
        )).scalar() or 0
        try_clicked = (await self.session.execute(
            select(func.count())
            .select_from(ReleaseFeedbackDelivery)
            .where(ReleaseFeedbackDelivery.campaign_id == campaign_id)
            .where(ReleaseFeedbackDelivery.try_clicked_at.is_not(None))
        )).scalar() or 0
        trial_granted = (await self.session.execute(
            select(func.count())
            .select_from(ReleaseFeedbackDelivery)
            .where(ReleaseFeedbackDelivery.campaign_id == campaign_id)
            .where(ReleaseFeedbackDelivery.trial_granted_until.is_not(None))
        )).scalar() or 0

        responses = sum(rating_counts.values())
        return ReleaseFeedbackStats(
            delivered=delivered,
            failed=failed,
            responses=responses,
            average_rating=round(float(avg_rating or 0), 2),
            comments=int(comments),
            rating_1=rating_counts.get(1, 0),
            rating_2=rating_counts.get(2, 0),
            rating_3=rating_counts.get(3, 0),
            rating_4=rating_counts.get(4, 0),
            rating_5=rating_counts.get(5, 0),
            discount_offered=int(discount_offered),
            discount_used=int(discount_used),
            try_clicked=int(try_clicked),
            trial_granted=int(trial_granted),
        )

    async def recent_comments(
        self,
        campaign_id: int,
        limit: int = 5,
    ) -> list[ReleaseFeedbackResponse]:
        result = await self.session.execute(
            select(ReleaseFeedbackResponse)
            .where(ReleaseFeedbackResponse.campaign_id == campaign_id)
            .where(
                (ReleaseFeedbackResponse.comment_text.is_not(None))
                | (ReleaseFeedbackResponse.attachment_file_id.is_not(None))
            )
            .order_by(ReleaseFeedbackResponse.completed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

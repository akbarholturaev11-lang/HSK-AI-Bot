from datetime import datetime, timedelta, timezone

from aiogram import Bot
from sqlalchemy import select

from app.bot.keyboards.subscription_churn import (
    CHURN_REASON_CODES,
    subscription_churn_followup_keyboard,
)
from app.bot.utils.i18n import t
from app.db.models.bot_feedback import BotFeedback
from app.db.models.user import User
from app.repositories.user_repo import UserRepository


FOLLOWUP_DELAY = timedelta(hours=24)
SUBSCRIPTION_CHURN_MINIAPP_SOURCES = {"subscription_expired", "subscription_churn_followup"}
DISCOUNT_REASON_CODES = {"budget", "price"}
REASON_TO_FEEDBACK_CODE = {
    "budget": "price",
    "price": "price",
    "ai_quality": "unclear",
    "course_fit": "pace",
    "trial_more": "other",
    "other": "other",
}


class SubscriptionChurnService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)

    @staticmethod
    def _aware(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    async def mark_expired_offer_sent(self, user: User, now: datetime | None = None) -> None:
        now = now or datetime.now(timezone.utc)
        user.subscription_expired_offer_sent_at = now
        user.subscription_churn_followup_sent_at = None
        user.subscription_churn_responded_at = None
        user.subscription_churn_reason = None
        await self.session.flush()

    async def mark_responded(self, user: User, *, reason: str | None = None) -> None:
        user.subscription_churn_responded_at = datetime.now(timezone.utc)
        if reason:
            user.subscription_churn_reason = reason[:64]
        await self.session.flush()

    async def mark_subscription_miniapp_opened(self, telegram_id: int, source: str | None) -> bool:
        if str(source or "").strip().lower() not in SUBSCRIPTION_CHURN_MINIAPP_SOURCES:
            return False
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user or user.subscription_churn_responded_at:
            return False
        await self.mark_responded(user)
        await self.session.commit()
        return True

    async def reset_after_paid_activation(self, user: User) -> None:
        user.subscription_expired_offer_sent_at = None
        user.subscription_churn_followup_sent_at = None
        user.subscription_churn_responded_at = None
        user.subscription_churn_reason = None
        await self.session.flush()

    async def record_reason(self, user: User, reason: str) -> tuple[BotFeedback, bool]:
        reason = str(reason or "").strip().lower()
        if reason not in CHURN_REASON_CODES:
            reason = "other"

        lang = user.language if user.language else "ru"
        now = datetime.now(timezone.utc)
        feedback_code = REASON_TO_FEEDBACK_CODE.get(reason, "other")
        label = t(f"subscription_churn_reason_{reason}", lang)
        feedback = BotFeedback(
            user_id=user.id,
            telegram_id=user.telegram_id,
            language=lang,
            status="completed",
            disliked_code=feedback_code,
            disliked_text=f"Subscription churn reason: {label}",
            completed_at=now,
            price_offer_sent_at=now if reason in DISCOUNT_REASON_CODES else None,
            created_at=now,
            updated_at=now,
        )
        self.session.add(feedback)
        await self.mark_responded(user, reason=reason)
        await self.session.flush()
        return feedback, reason in DISCOUNT_REASON_CODES

    async def send_due_followups(self, bot: Bot) -> int:
        now = datetime.now(timezone.utc)
        due_before = now - FOLLOWUP_DELAY
        result = await self.session.execute(
            select(User)
            .where(User.status == "expired")
            .where(User.payment_status == "approved")
            .where(User.subscription_expired_offer_sent_at.is_not(None))
            .where(User.subscription_expired_offer_sent_at <= due_before)
            .where(User.subscription_churn_followup_sent_at.is_(None))
            .where(User.subscription_churn_responded_at.is_(None))
            .order_by(User.subscription_expired_offer_sent_at.asc())
        )
        users = list(result.scalars().all())

        sent_count = 0
        for user in users:
            lang = user.language if user.language else "ru"
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=t("subscription_churn_followup_text", lang),
                    reply_markup=subscription_churn_followup_keyboard(lang),
                    parse_mode="HTML",
                )
                sent_count += 1
            except Exception:
                pass
            user.subscription_churn_followup_sent_at = now

        if users:
            await self.session.commit()
        return sent_count

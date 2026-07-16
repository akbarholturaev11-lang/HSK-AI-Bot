from datetime import datetime, timezone, timedelta
from typing import Optional

from app.repositories.bot_feedback_repo import BotFeedbackRepository
from app.repositories.user_repo import UserRepository
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.portfolio_service import PortfolioService
from app.services.subscription_churn_service import SubscriptionChurnService


PLAN_DURATIONS = {
    "10_days": 10,
    "1_month": 30,
    "3_months": 90,
}

MANUAL_SUBSCRIPTION_MIN_DAYS = 1
MANUAL_SUBSCRIPTION_MAX_DAYS = 36_500


def normalize_manual_subscription_days(value: object) -> Optional[int]:
    """Admin qo'lda beradigan obuna muddatini xavfsiz kun soniga aylantiradi."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        days = value
    elif isinstance(value, str):
        raw = value.strip()
        if not raw.isascii() or not raw.isdigit() or len(raw) > 5:
            return None
        days = int(raw)
    else:
        return None

    if not MANUAL_SUBSCRIPTION_MIN_DAYS <= days <= MANUAL_SUBSCRIPTION_MAX_DAYS:
        return None
    return days


class SubscriptionService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.feedback_repo = BotFeedbackRepository(session)

    async def activate_plan(
        self,
        telegram_id: int,
        plan_type: str,
        discount_source: Optional[str] = None,
        payment=None,
    ) -> bool:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return False

        duration_days = PLAN_DURATIONS.get(plan_type)
        if not duration_days:
            return False

        now = datetime.now(timezone.utc)

        user.status = "active"
        user.payment_status = "approved"
        user.start_date = now
        user.end_date = now + timedelta(days=duration_days)
        user.selected_plan_type = None
        user.expiry_reminder_sent_at = None
        await SubscriptionChurnService(self.session).reset_after_paid_activation(user)

        if discount_source == "referral" and user.discount_eligible and not user.discount_used:
            user.discount_used = True
            user.discount_eligible = False

        if discount_source == "feedback_price_offer":
            await self.feedback_repo.mark_latest_price_offer_used(telegram_id)

        if payment is not None:
            await AIUsageBudgetService(self.session).create_for_payment(
                payment=payment,
                starts_at=user.start_date,
                ends_at=user.end_date,
            )
            await PortfolioService(self.session).record_subscription_profit(payment)

        await self.session.flush()
        return True

    async def grant_manual_paid_access(
        self,
        telegram_id: int,
        duration_days: object,
    ):
        """Admin grant: userni paid-active qiladi va mavjud paid muddatni saqlaydi.

        Foydalanuvchida hali tugamagan paid obuna bo'lsa, yangi kunlar uning
        amaldagi ``end_date`` sanasiga qo'shiladi. Boshqa holatda muddat hozirdan
        boshlanadi. Bu oqim payment/revenue yoki AI budget yaratmaydi.
        """
        days = normalize_manual_subscription_days(duration_days)
        if days is None:
            return None

        user = await self.user_repo.get_by_telegram_id_for_update(telegram_id)
        if not user:
            return None

        now = datetime.now(timezone.utc)
        current_end = user.end_date
        if current_end is not None:
            if current_end.tzinfo is None:
                current_end = current_end.replace(tzinfo=timezone.utc)
            else:
                current_end = current_end.astimezone(timezone.utc)

        extends_existing_paid = bool(
            user.payment_status == "approved"
            and current_end is not None
            and current_end > now
        )
        if extends_existing_paid:
            base_end = current_end
            if user.start_date is None:
                user.start_date = now
        else:
            user.start_date = now
            base_end = now

        user.status = "active"
        user.payment_status = "approved"
        user.end_date = base_end + timedelta(days=days)
        user.selected_plan_type = None
        user.expiry_reminder_sent_at = None
        await SubscriptionChurnService(self.session).reset_after_paid_activation(user)
        await self.session.flush()
        return user, extends_existing_paid

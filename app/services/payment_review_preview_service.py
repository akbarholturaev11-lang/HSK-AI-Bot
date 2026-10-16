"""Single-use pending-payment preview, separate from paid status and trials.

Only real admin-approved subscription payments replenish the opportunity.
The ticket is attached to one immutable payment ID; resubmissions never mint
additional access. A pending receipt is NOT revenue or an approved payment.
"""
from sqlalchemy import select

from app.db.models.user import User
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.subscription_service import PLAN_DURATIONS


class PaymentReviewPreviewService:
    def __init__(self, session):
        self.session = session

    @staticmethod
    def _eligible(user, payment) -> bool:
        return bool(
            user
            and payment
            and payment.plan_type in PLAN_DURATIONS
            and payment.payment_status == "pending"
            and int(payment.user_telegram_id) == int(user.telegram_id)
            and user.status != "blocked"
        )

    async def claim(self, user, payment) -> bool:
        """Call within the same transaction as the receipt submission."""
        if not self._eligible(user, payment):
            return False
        # Force a fresh row under lock, even when an earlier query loaded user
        # into this transaction's identity map before the concurrent claimant.
        result = await self.session.execute(
            select(User).where(User.telegram_id == int(user.telegram_id))
            .with_for_update().execution_options(populate_existing=True)
        )
        locked = result.scalar_one_or_none()
        if not locked or not getattr(locked, "payment_preview_available", True):
            return False
        locked.payment_preview_available = False
        locked.payment_preview_payment_id = int(payment.id)
        await AIUsageBudgetService(self.session).create_payment_preview_budget(locked, payment)
        await self.session.flush()
        return True

    async def review(self, user, payment, *, approved: bool) -> None:
        """Called only after a payment status transition succeeds (same transaction)."""
        if not user or not payment or payment.plan_type not in PLAN_DURATIONS:
            return
        result = await self.session.execute(
            select(User).where(User.telegram_id == int(user.telegram_id))
            .with_for_update().execution_options(populate_existing=True)
        )
        locked = result.scalar_one_or_none()
        if not locked:
            return
        if getattr(locked, "payment_preview_payment_id", None) == payment.id:
            locked.payment_preview_payment_id = None
        # A rejected receipt never recharges. An approved subscription does,
        # including approval of a subsequent receipt which had no preview.
        if approved:
            locked.payment_preview_available = True
        await AIUsageBudgetService(self.session).expire_payment_preview_budget(payment.id)
        await self.session.flush()

"""Single-use pending-payment preview, separate from paid status and trials.

Only real admin-approved subscription payments replenish the opportunity.
The ticket is attached to one immutable payment ID; resubmissions never mint
additional access. A pending receipt is NOT revenue or an approved payment.
"""
from sqlalchemy import select

from app.db.models.ai_usage import AIUsageBudget
from app.db.models.user import User
from app.repositories.payment_repo import PaymentRepository
from app.services.account_identity import account_user_id
from app.services.ai_usage_budget_service import AIUsageBudgetService, PAYMENT_PREVIEW_PLAN_TYPE
from app.services.subscription_service import PLAN_DURATIONS


class PaymentReviewPreviewService:
    def __init__(self, session):
        self.session = session

    @staticmethod
    def _owns(user, payment) -> bool:
        if not user or not payment or account_user_id(user) is None:
            return False
        return PaymentRepository.is_owned_by(payment, user)

    @classmethod
    def _eligible(cls, user, payment) -> bool:
        return bool(
            cls._owns(user, payment)
            and payment.plan_type in PLAN_DURATIONS
            and payment.payment_status == "pending"
            and user.status != "blocked"
        )

    @classmethod
    def is_active(cls, user, payment) -> bool:
        """Report this receipt's existing grant without claiming another ticket."""
        return bool(
            cls._eligible(user, payment)
            and payment.id is not None
            and getattr(user, "payment_preview_payment_id", None) == payment.id
        )

    async def claim(self, user, payment) -> bool:
        """Call within the same transaction as the receipt submission."""
        if not self._eligible(user, payment):
            return False
        # Force a fresh row under lock, even when an earlier query loaded user
        # into this transaction's identity map before the concurrent claimant.
        result = await self.session.execute(
            select(User).where(User.id == int(user.id))
            .with_for_update().execution_options(populate_existing=True)
        )
        locked = result.scalar_one_or_none()
        if not self._eligible(locked, payment) or not getattr(locked, "payment_preview_available", True):
            return False
        # A different approved subscription can replenish the opportunity while
        # this old receipt is still pending. Resubmitting that immutable receipt
        # must neither spend the new ticket nor mint another capped budget.
        if getattr(locked, "payment_preview_payment_id", None) == payment.id:
            return False
        previous = await self.session.execute(
            select(AIUsageBudget.id).where(
                AIUsageBudget.payment_id == int(payment.id),
                AIUsageBudget.plan_type == PAYMENT_PREVIEW_PLAN_TYPE,
            ).limit(1)
        )
        if previous.scalar_one_or_none() is not None:
            return False
        locked.payment_preview_available = False
        locked.payment_preview_payment_id = int(payment.id)
        await AIUsageBudgetService(self.session).create_payment_preview_budget(locked, payment)
        await self.session.flush()
        return True

    async def review(self, user, payment, *, approved: bool) -> None:
        """Called only after a payment status transition succeeds (same transaction)."""
        if not user or not payment or getattr(payment, "plan_type", None) not in PLAN_DURATIONS:
            return
        if not self._owns(user, payment):
            return
        if payment.payment_status != ("approved" if approved else "rejected"):
            return
        result = await self.session.execute(
            select(User).where(User.id == int(user.id))
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

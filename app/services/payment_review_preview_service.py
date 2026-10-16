"""Single-use pending-payment preview, separate from paid status and trials.

Only real admin-approved subscription payments replenish the opportunity.
The ticket is attached to one immutable payment ID; resubmissions never mint
additional access. A pending receipt is NOT revenue or an approved payment.
"""
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
        from app.repositories.user_repo import UserRepository

        # Locked read prevents two simultaneous receipts from consuming one slot.
        locked = await UserRepository(self.session).get_by_telegram_id_for_update(
            int(user.telegram_id)
        )
        if not locked or not locked.payment_preview_available:
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
        from app.repositories.user_repo import UserRepository

        locked = await UserRepository(self.session).get_by_telegram_id_for_update(
            int(user.telegram_id)
        )
        if not locked:
            return
        if locked.payment_preview_payment_id == payment.id:
            locked.payment_preview_payment_id = None
        # A rejected receipt never recharges. An approved subscription does,
        # including approval of a subsequent receipt which had no preview.
        if approved:
            locked.payment_preview_available = True
        await AIUsageBudgetService(self.session).expire_payment_preview_budget(payment.id)
        await self.session.flush()

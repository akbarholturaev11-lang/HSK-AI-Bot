"""At-most-once post-commit attempts; no network exactly-once claims.

Telegram/FCM do not offer an end-to-end idempotency key. Claim durably BEFORE
sending. A crash or partial failure stays attempting/uncertain for explicit
reconciliation, never automatic resend. 'attempted' is not delivery proof.
"""
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import update

from app.admin_api.pwa_step_up import _enabled
from app.db.models.admin_pwa_payment_review import AdminPwaPaymentReview, AdminPwaPaymentOutbox
from app.db.models.partner import Partner
from app.db.models.payment import Payment
from app.db.models.user import User
from app.repositories.payment_repo import PaymentRepository
from app.services.admin_payment_review_service import PaymentReviewResult

logger = logging.getLogger(__name__)


async def dispatch_payment_review(*, review_id, session_factory, settings_obj, emit):
    if not _enabled(settings_obj):
        return False
    async with session_factory() as db:
        async with db.begin():
            claimed = await db.execute(update(AdminPwaPaymentOutbox).where(
                AdminPwaPaymentOutbox.review_id == review_id,
                AdminPwaPaymentOutbox.status == "pending",
            ).values(status="attempting", attempted_at=datetime.now(timezone.utc)))
            if claimed.rowcount != 1:
                return False
    status = "uncertain"
    try:
        async with session_factory() as db:
            audit = await db.get(AdminPwaPaymentReview, review_id)
            outbox = await db.get(AdminPwaPaymentOutbox, review_id)
            payment = await db.get(Payment, audit.payment_id)
            user = await db.get(User, audit.target_user_id)
            if (not user or not payment or not PaymentRepository.is_owned_by(payment, user)
                    or payment.payment_status != {"approve": "approved", "reject": "rejected"}[audit.decision]):
                raise ValueError("payment_outbox_target_changed")
            data = json.loads(outbox.effects_json)
            partner = await db.get(Partner, data["partner_id"]) if data["partner_id"] else None
            await emit(db, PaymentReviewResult(
                payment=payment, user=user, decision=audit.decision, partner=partner,
                commission_usd=Decimal(data["commission_usd"]),
                unlocked_bonus=data["unlocked_bonus"], deferred_events=data["deferred_events"],
            ))
            await db.commit()
            status = "attempted"
    except Exception:
        logger.exception("Admin PWA payment delivery requires reconciliation: %s", review_id)
    async with session_factory() as db:
        async with db.begin():
            await db.execute(update(AdminPwaPaymentOutbox).where(
                AdminPwaPaymentOutbox.review_id == review_id,
                AdminPwaPaymentOutbox.status == "attempting",
            ).values(status=status, finished_at=datetime.now(timezone.utc)))
    return status == "attempted"

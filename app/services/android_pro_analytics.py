"""Content-free native Pro UI stages, serialized by the canonical account.

Financial stages are separate server writers. Failure of this optional intake
cannot change a quote, invoice, payment or entitlement.
"""
import json

from sqlalchemy import select

from app.db.models.conversion_funnel_event import ConversionFunnelEvent as Funnel
from app.db.models.lava import LavaInvoice
from app.db.models.user import User


async def record_ui(db, *, user, data):
    await db.get(User, user.id, with_for_update=True)
    duplicate = await db.scalar(select(Funnel.id).where(
        Funnel.user_id == user.id, Funnel.event_name == data.event,
        Funnel.payload_json.like('%"event_id": "' + data.event_id + '"%'),
    ).limit(1))
    if duplicate is None:
        db.add(Funnel(user_id=user.id, telegram_id=user.telegram_id, event_name=data.event,
                      source=data.source, payload_json=json.dumps({
                          "event_id": data.event_id, "attempt_id": data.attempt_id,
                          "plan_type": data.plan_type or "", "payment_method": data.method or "",
                          "transport": "android",
                      })))
    await db.commit()
    return duplicate is None


async def record_started(db, *, user, checkout_id):
    # Read the reserved invoice's original attribution, never a retry's body.
    await db.get(User, user.id, with_for_update=True)
    invoice = await db.scalar(select(LavaInvoice).where(
        LavaInvoice.id == checkout_id, LavaInvoice.user_id == user.id,
        LavaInvoice.source == "android", LavaInvoice.kind != "renewal",
        LavaInvoice.android_inline_attempt_id.is_not(None),
    ))
    if invoice is None:
        return
    event_id = invoice.android_inline_attempt_id + ":invoice-" + str(invoice.id)
    duplicate = await db.scalar(select(Funnel.id).where(
        Funnel.user_id == user.id, Funnel.event_name == "android_pro_checkout_started",
        Funnel.payload_json.like('%"event_id": "' + event_id + '"%'),
    ).limit(1))
    if duplicate is None:
        db.add(Funnel(user_id=user.id, telegram_id=user.telegram_id,
                      event_name="android_pro_checkout_started", source=invoice.android_inline_source,
                      payload_json=json.dumps({
                          "event_id": event_id, "attempt_id": invoice.android_inline_attempt_id,
                          "checkout_id": invoice.id, "plan_type": invoice.plan_type,
                          "payment_method": "lava", "transport": "android",
                      })))
    await db.commit()

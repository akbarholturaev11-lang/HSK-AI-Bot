"""iPhone PWA Pro inline checkout funnel over existing rows (design D4, task 4.1).

Every step is a row that only the PWA path can write:
- `pwa_pro_opened` / `pwa_pro_plan_selected`: the cookie + CSRF PWA UI route;
- `pwa_pro_checkout_started`: the server, after the provider invoice exists;
- `pwa_pro_checkout_paid`: the Lava ledger, in the verified-grant transaction.
An attempt is `(canonical account, attempt_id)`. No identifier leaves this module.
"""
import json
from datetime import timedelta

from sqlalchemy import and_, func, select

from app.admin_api.pwa_analytics_learning import PAYLOAD_LIMIT, bounded_rows, owner
from app.db.models.conversion_funnel_event import ConversionFunnelEvent as Funnel
from app.db.models.lava import LavaInvoice
from app.db.models.payment import Payment
from app.db.models.user import User

STEPS = ('opened', 'plan_selected', 'checkout_started', 'paid')
STEP_EVENTS = {'pwa_pro_opened': 0, 'pwa_pro_plan_selected': 1, 'pwa_pro_checkout_started': 2,
               'pwa_pro_checkout_paid': 3}
# The ledger writes the paid row next to an approved payment; a later refund or
# chargeback changes that payment's status, so these mean "was approved".
GRANTED_PAYMENTS = ('approved', 'refunded', 'chargeback')
REVERSED_INVOICES = ('refunded', 'chargeback_lost')
GRANTED_INVOICES = ('paid', 'refunded', 'chargeback_open', 'chargeback_won', 'chargeback_lost')
# Rows this far before the window are read so an attempt that began earlier is
# not counted as starting inside it.
ATTEMPT_LOOKBACK = timedelta(days=30)


def _attempt_id(payload):
    try:
        value = json.loads(payload or '{}').get('attempt_id')
    except (TypeError, ValueError, AttributeError):
        return None
    return value if isinstance(value, str) and value else None


async def pwa_pro_attempt_funnel(db, *, since, now):
    paid_invoice = and_(LavaInvoice.payment_id == Funnel.payment_id, LavaInvoice.payment_id.is_not(None))
    window = [Funnel.created_at <= now]
    if since is not None:
        window.append(Funnel.created_at >= since - ATTEMPT_LOOKBACK)
    rows = await bounded_rows(db, select(
        Funnel.event_name, User.id, func.substr(Funnel.payload_json, 1, PAYLOAD_LIMIT + 1), Funnel.created_at,
        Payment.payment_status, LavaInvoice.status, Funnel.payment_id,
    ).select_from(Funnel).join(User, owner(Funnel))
        .outerjoin(Payment, Payment.id == Funnel.payment_id)
        .outerjoin(LavaInvoice, paid_invoice)
        .where(Funnel.event_name.in_(STEP_EVENTS), *window)
        .order_by(Funnel.created_at, Funnel.id), payload_index=2)
    if rows is None:
        return None

    attempts, linked = {}, set()
    for name, account, payload, at, payment_status, invoice_status, payment_id in rows:
        attempt = _attempt_id(payload)
        if attempt is None:
            continue
        stage = STEP_EVENTS[name]
        if stage == 3:
            # Paid only with the ledger's approved payment; a click, a return
            # URL or a failed webhook never writes this row.
            if payment_status not in GRANTED_PAYMENTS:
                continue
            linked.add(payment_id)
        state = attempts.setdefault((account, attempt), {'first': at, 'stage': -1, 'reversed': False})
        state['first'] = min(state['first'], at)
        state['stage'] = max(state['stage'], stage)
        if stage == 3 and invoice_status in REVERSED_INVOICES:
            state['reversed'] = True

    cohort = [state for state in attempts.values() if since is None or state['first'] >= since]
    steps = [{'key': key, 'attempts': sum(state['stage'] >= index for state in cohort)}
             for index, key in enumerate(STEPS)]

    # Verified PWA Lava first payments that no attempt reached.
    unlinked = select(LavaInvoice.payment_id).where(
        LavaInvoice.source == 'pwa', LavaInvoice.kind != 'renewal', LavaInvoice.payment_id.is_not(None),
        LavaInvoice.status.in_(GRANTED_INVOICES), LavaInvoice.paid_at <= now,
        *([LavaInvoice.paid_at >= since] if since is not None else []))
    unlinked_ids = {payment_id for (payment_id,) in (await db.execute(unlinked)).all()} - linked
    return {'attempts': len(cohort), 'steps': steps,
            'reversed': sum(state['reversed'] for state in cohort), 'unlinked': len(unlinked_ids)}

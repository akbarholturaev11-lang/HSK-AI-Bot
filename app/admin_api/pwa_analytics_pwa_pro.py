"""iPhone PWA Pro inline checkout funnel over existing rows (design D4, task 4.1).

Every step is a row that only the PWA path can write:
- `pwa_pro_opened` / `pwa_pro_plan_selected`: the cookie + CSRF PWA UI route;
- `pwa_pro_checkout_started`: the server, after the provider invoice exists;
- `pwa_pro_checkout_paid`: the Lava ledger, in the verified-grant transaction.
An attempt is `(canonical account, attempt_id)`. No identifier leaves this module.
"""
from datetime import timedelta

from sqlalchemy import and_, case, func, literal, or_, select

from app.admin_api.pwa_analytics_learning import owner
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
# Every writer stores a flat server-built JSON object whose `attempt_id` is a
# validated token (`pwa_auth.PwaProUiEvent`, Lava start <= 96 chars, ledger copy).
ATTEMPT_PATTERN = r'"attempt_id": ?"([^"\\]{1,96})"'


def _attempt(dialect):
    """The top-level `attempt_id` string, or NULL when absent or empty."""
    if dialect == 'postgresql':
        return func.substring(Funnel.payload_json, literal(ATTEMPT_PATTERN))
    # SQLite (browser QA): JSON1, never evaluated on malformed text.
    value = func.json_extract(Funnel.payload_json, '$.attempt_id')
    return case((func.json_valid(Funnel.payload_json) == 1,
                 case((func.json_type(Funnel.payload_json, '$.attempt_id') == 'text', func.nullif(value, '')))))


async def pwa_pro_attempt_funnel(db, *, since, now):
    """Aggregated in SQL per attempt, so no history length makes it partial (#28)."""
    paid_invoice = and_(LavaInvoice.payment_id == Funnel.payment_id, LavaInvoice.payment_id.is_not(None))
    paid = Funnel.event_name == 'pwa_pro_checkout_paid'
    window = [Funnel.created_at <= now]
    if since is not None:
        window.append(Funnel.created_at >= since - ATTEMPT_LOOKBACK)
    # Paid only with the ledger's approved payment; a click, a return URL or a
    # failed webhook never writes this row, and an unapproved one is ignored.
    rows = select(
        User.id.label('account'), _attempt(db.get_bind().dialect.name).label('attempt'),
        Funnel.created_at.label('at'), Funnel.payment_id.label('payment_id'),
        case(*[(Funnel.event_name == name, stage) for name, stage in STEP_EVENTS.items()]).label('stage'),
        case((and_(paid, LavaInvoice.status.in_(REVERSED_INVOICES)), 1), else_=0).label('reversed'),
    ).select_from(Funnel).join(User, owner(Funnel)) \
        .outerjoin(Payment, Payment.id == Funnel.payment_id) \
        .outerjoin(LavaInvoice, paid_invoice) \
        .where(Funnel.event_name.in_(STEP_EVENTS), or_(~paid, Payment.payment_status.in_(GRANTED_PAYMENTS)),
               *window).subquery()
    attempts = select(func.min(rows.c.at).label('first'), func.max(rows.c.stage).label('stage'),
                      func.max(rows.c.reversed).label('reversed')) \
        .where(rows.c.attempt.is_not(None)).group_by(rows.c.account, rows.c.attempt).subquery()
    cohort = [attempts.c.first >= since] if since is not None else []
    total, *reached, reversed_count = (await db.execute(select(
        func.count(), *[func.count().filter(attempts.c.stage >= index) for index in range(len(STEPS))],
        func.coalesce(func.sum(attempts.c.reversed), 0)).where(*cohort))).one()
    steps = [{'key': key, 'attempts': int(count)} for key, count in zip(STEPS, reached)]

    # Verified PWA Lava first payments that no attempt reached.
    linked = select(rows.c.payment_id).where(rows.c.stage == 3, rows.c.attempt.is_not(None),
                                             rows.c.payment_id.is_not(None))
    unlinked = await db.scalar(select(func.count(func.distinct(LavaInvoice.payment_id))).where(
        LavaInvoice.source == 'pwa', LavaInvoice.kind != 'renewal', LavaInvoice.payment_id.is_not(None),
        LavaInvoice.status.in_(GRANTED_INVOICES), LavaInvoice.paid_at <= now,
        *([LavaInvoice.paid_at >= since] if since is not None else []),
        LavaInvoice.payment_id.not_in(linked)))
    return {'attempts': int(total), 'steps': steps, 'reversed': int(reversed_count), 'unlinked': int(unlinked or 0)}

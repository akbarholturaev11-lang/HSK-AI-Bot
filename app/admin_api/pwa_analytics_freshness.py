"""Report freshness per platform from verified signals only (design D7, task 5.2).

For each platform and stored source: the latest record and how many records
have no resolvable canonical owner. Counts and timestamps only; no identifier
or payload leaves this module.
"""
from datetime import timedelta

from sqlalchemy import and_, case, false, func, or_, select

from app.admin_api.pwa_analytics_course_platform import (
    ANDROID_COMPLETION_SOURCE, COMPLETED, SERVER_ONLY_TAGGED, client_tag)
from app.admin_api.pwa_analytics_finance import PAYMENT_PLATFORM_SOURCES
from app.admin_api.pwa_analytics_platforms import PWA_MAP_OPEN_PREFIX
from app.db.models.course_miniapp_event import CourseMiniAppEvent as Event
from app.db.models.diagnostic import DiagnosticIncident, DiagnosticReceipt
from app.db.models.payment import Payment
from app.db.models.user import User
from app.services.monitoring.catalog import RECEIPT_RETENTION_DAYS

PLATFORMS = ('android', 'telegram', 'iphone_pwa')


def _tagged(platform, boundary):
    """The route-set final `client` key, from the same data-derived boundary as
    the Course reader: an older caller lookalike never dates a client (#37)."""
    return and_(client_tag(platform), Event.created_at >= boundary) if boundary is not None else false()


async def _boundaries(db, *, now):
    """First server-built tagged completion per client, in one grouped scan."""
    platform = case(*[(client_tag(key), key) for key in PLATFORMS], else_=None)
    rows = (await db.execute(select(platform, func.min(Event.created_at))
        .where(Event.event_name.in_(SERVER_ONLY_TAGGED), or_(*(client_tag(key) for key in PLATFORMS)),
               Event.created_at <= now).group_by(platform))).all()
    return {key: at for key, at in rows if key is not None}


def learning_predicates(boundaries):
    # Audit A1, A4, A8 and the route-set final `client` key. Internal feedback
    # reservations and other server bookkeeping rows carry none of these signals.
    return {
        'android': or_(Event.event_name == 'android_app_opened',
                       and_(Event.source == ANDROID_COMPLETION_SOURCE, Event.event_name.in_(COMPLETED)),
                       _tagged('android', boundaries.get('android'))),
        'telegram': _tagged('telegram', boundaries.get('telegram')),
        'iphone_pwa': or_(and_(Event.event_name == 'miniapp_opened', Event.dedupe_key.startswith(PWA_MAP_OPEN_PREFIX)),
                          _tagged('iphone_pwa', boundaries.get('iphone_pwa'))),
    }


def _unresolved(user_id, telegram_id):
    """No canonical account: the owned ID is gone, or an unowned row's
    Telegram ID matches nobody (the analytics owner rule)."""
    by_id = select(User.id).where(User.id == user_id).exists()
    by_telegram = select(User.id).where(User.telegram_id == telegram_id).exists()
    return ~or_(and_(user_id.is_not(None), by_id), and_(user_id.is_(None), by_telegram))


async def _grouped(db, predicates, column, user_id, telegram_id, *, now):
    platform = case(*[(predicate, key) for key, predicate in predicates.items()], else_=None)
    rows = (await db.execute(select(platform, func.max(column), func.count().filter(_unresolved(user_id, telegram_id)))
        .where(or_(*predicates.values()), column <= now).group_by(platform))).all()
    return {key: (latest, unresolved) for key, latest, unresolved in rows}


async def platform_freshness(db, *, now):
    predicates = learning_predicates(await _boundaries(db, now=now))
    learning = await _grouped(db, predicates, Event.created_at, Event.user_id, Event.telegram_id, now=now)
    payments = await _grouped(db, {key: Payment.source.in_(sources) for key, sources in PAYMENT_PLATFORM_SOURCES.items()},
        Payment.submitted_at, Payment.user_id, Payment.user_telegram_id, now=now)
    diagnostics = {}
    for platform in PLATFORMS:
        latest = await db.scalar(select(DiagnosticReceipt.received_at).join(
            DiagnosticIncident, DiagnosticIncident.id == DiagnosticReceipt.incident_id,
        ).where(DiagnosticIncident.platform == platform, DiagnosticReceipt.user_id.is_not(None),
                DiagnosticReceipt.received_at.between(now - timedelta(days=RECEIPT_RETENTION_DAYS), now),
        ).order_by(DiagnosticReceipt.received_at.desc()).limit(1))
        diagnostics[platform] = (latest, 0)
    result = []
    for platform in PLATFORMS:
        for source, values in (('learning', learning), ('payments', payments), ('diagnostics', diagnostics)):
            latest, unresolved = values.get(platform, (None, 0))
            result.append({'platform': platform, 'source': source,
                           'latest_at': latest.isoformat() if latest else None, 'unresolved_owners': unresolved})
    return result

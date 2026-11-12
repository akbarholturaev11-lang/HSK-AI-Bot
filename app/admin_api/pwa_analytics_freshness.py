"""Report freshness per platform from verified signals only (design D7, task 5.2).

For each platform and stored source: the latest record and how many records
have no resolvable canonical owner. Counts and timestamps only; no identifier
or payload leaves this module.
"""
from sqlalchemy import and_, case, func, or_, select

from app.admin_api.pwa_analytics_course_platform import ANDROID_COMPLETION_SOURCE, COMPLETED, client_tag
from app.admin_api.pwa_analytics_finance import PAYMENT_PLATFORM_SOURCES
from app.admin_api.pwa_analytics_platforms import PWA_MAP_OPEN_PREFIX
from app.db.models.course_miniapp_event import CourseMiniAppEvent as Event
from app.db.models.payment import Payment
from app.db.models.user import User

PLATFORMS = ('android', 'telegram', 'iphone_pwa')
# Audit A1, A4, A8 and the route-set final `client` key. Internal feedback
# reservations and other server bookkeeping rows carry none of these signals.
LEARNING = {
    'android': or_(Event.event_name == 'android_app_opened',
                   and_(Event.source == ANDROID_COMPLETION_SOURCE, Event.event_name.in_(COMPLETED)),
                   client_tag('android')),
    'telegram': client_tag('telegram'),
    'iphone_pwa': or_(and_(Event.event_name == 'miniapp_opened', Event.dedupe_key.startswith(PWA_MAP_OPEN_PREFIX)),
                      client_tag('iphone_pwa')),
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
    learning = await _grouped(db, LEARNING, Event.created_at, Event.user_id, Event.telegram_id, now=now)
    payments = await _grouped(db, {key: Payment.source.in_(sources) for key, sources in PAYMENT_PLATFORM_SOURCES.items()},
        Payment.submitted_at, Payment.user_id, Payment.user_telegram_id, now=now)
    result = []
    for platform in PLATFORMS:
        for source, values in (('learning', learning), ('payments', payments)):
            latest, unresolved = values.get(platform, (None, 0))
            result.append({'platform': platform, 'source': source,
                           'latest_at': latest.isoformat() if latest else None, 'unresolved_owners': unresolved})
    return result

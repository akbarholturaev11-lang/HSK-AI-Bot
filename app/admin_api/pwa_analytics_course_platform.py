"""Course metrics for one client, from route-owned attribution only (task 3.2)."""
from datetime import timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import aliased

from app.admin_api.pwa_analytics_learning import bounded_rows, foundation_query, foundation_summary, owner
from app.admin_api.pwa_metrics import _window
from app.admin_api.pwa_read import _user_segment_clause
from app.db.models.course_miniapp_event import CourseMiniAppEvent as Event
from app.db.models.user import User

COURSE_CLIENTS = ('android', 'telegram', 'iphone_pwa')
# Server-built writes never copy a caller payload, so the first row tagged for
# a client marks when route-owned tagging was live for it. Client-writable
# starts could carry a caller `client` key before that, so they count only
# from this boundary on.
# R1 (audit A7): Android lesson opens. Server-only: no client route accepts
# this name, so it can date the Android boundary. Only the Admin readers and
# bot-block diagnostics read it; reminders read `lesson_started`.
ANDROID_LESSON_STARTED = 'android_lesson_started'
SERVER_ONLY_TAGGED = ('lesson_completed', 'book_lesson_completed', 'training_completed',
                      'test_completed', 'mistake_review_answered', 'mistake_review_completed',
                      ANDROID_LESSON_STARTED)
FEATURE_EVENTS = (
    ('lessons', ('lesson_started', 'section_started')),
    ('tests', ('test_started', 'test_completed')),
    ('practice', ('training_started', 'training_completed')),
    ('mistakes', ('mistake_review_started', 'mistake_review_completed')),
)
# Android lessons are read from ANDROID_LESSON_STARTED, not the client-written
# names above. It began later than the other Android writes, so the lessons
# entry has its own boundary.
COMPLETED = ('lesson_completed', 'book_lesson_completed')
# A8: only the Android course route writes this source on a completion.
ANDROID_COMPLETION_SOURCE = 'android_course'


def client_tag(platform, model=Event):
    """Routes drop a caller `client` before tagging, so the server key is the
    document's final top-level key. A nested caller object cannot end it."""
    return model.payload_json.endswith(f'"client":"{platform}"}}', autoescape=True)


def _started_here(platform, boundary, *, since, now):
    """Accounts whose Starter 0 start is attributed to this client in the
    window. Their non-start rows are the only ones the cohort can use, so other
    clients' rows never fill this client's detail limit (audit #13)."""
    start, account = aliased(Event), aliased(User)
    owned = and_(or_(start.user_id == account.id,
                     and_(start.user_id.is_(None), start.telegram_id == account.telegram_id)),
                 or_(start.user_id.is_not(None), start.telegram_id > 0))
    return (select(account.id).select_from(start).join(account, owned)
            .where(start.event_name == 'foundation_started', client_tag(platform, start),
                   start.created_at >= boundary, *_window(start.created_at, since, now)))


async def _completed_lessons(db, *conditions, since, now):
    completed = select(User.id, Event.level, Event.lesson_order).select_from(Event).join(User, owner(Event)).where(
        Event.lesson_order.is_not(None), *conditions, *_window(Event.created_at, since, now)).distinct().subquery()
    return int(await db.scalar(select(func.count()).select_from(completed)) or 0)


async def course_platform_metrics(db, *, platform, since, now):
    detail_since = since or now - timedelta(days=30)
    boundary = await db.scalar(select(func.min(Event.created_at)).where(
        Event.event_name.in_(SERVER_ONLY_TAGGED), client_tag(platform), Event.created_at <= now))
    attributed = [client_tag(platform), Event.created_at >= boundary] if boundary else None
    since_iso = boundary.isoformat() if boundary else None

    attributed_since = {'features': since_iso}
    features = None
    if attributed is not None:
        paid = _user_segment_clause('paid', now=now)
        features = []
        for key, names in FEATURE_EVENTS:
            conditions = attributed
            if platform == 'android' and key == 'lessons':
                lessons_since = await db.scalar(select(func.min(Event.created_at)).where(
                    Event.event_name == ANDROID_LESSON_STARTED, client_tag(platform), Event.created_at <= now))
                if lessons_since is None:
                    continue
                names, conditions = (ANDROID_LESSON_STARTED,), [client_tag(platform), Event.created_at >= lessons_since]
                attributed_since['features_lessons'] = lessons_since.isoformat()
            values = (await db.execute(select(func.count(func.distinct(User.id)).filter(paid),
                func.count(func.distinct(User.id)).filter(~paid)).select_from(Event).join(User, owner(Event))
                .where(Event.event_name.in_(names), *conditions, *_window(Event.created_at, detail_since, now),
                       User.created_at <= now))).one()
            features.append({'key': key, 'paid': values[0], 'free': values[1]})

    result = {}
    if platform != 'android':
        # The Starter 0 funnel is anchored on each learner's start. Only the
        # start is attributed; the completion, objectives and paywall rows of
        # that learner follow it, so the cohort is "started on this client".
        # A10: Android writes no start, so it has no foundation cohort.
        attributed_since['foundation'] = since_iso
        rows = None if attributed is None else await bounded_rows(db, foundation_query(
            or_(and_(Event.event_name == 'foundation_started', *attributed),
                and_(Event.event_name != 'foundation_started',
                     User.id.in_(_started_here(platform, boundary, since=detail_since, now=now)))),
            since=detail_since, now=now), payload_index=5)
        result['foundation'] = foundation_summary(rows, now=now)
        result['detail_limited'] = attributed is not None and rows is None
    if platform == 'android':
        completed = await _completed_lessons(db, Event.event_name.in_((*COMPLETED, 'android_lesson_completed')),
            Event.source == ANDROID_COMPLETION_SOURCE, since=since, now=now)
    else:
        attributed_since['completed_user_lessons'] = since_iso
        completed = None if attributed is None else await _completed_lessons(
            db, Event.event_name.in_(COMPLETED), *attributed, since=since, now=now)
    return {**result, 'features': features, 'completed_user_lessons': completed,
            'attributed_since': attributed_since, 'detail_since': detail_since.isoformat()}

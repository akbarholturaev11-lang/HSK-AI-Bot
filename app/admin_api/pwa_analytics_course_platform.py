"""Course metrics for one client, from route-owned attribution only (task 3.2)."""
from datetime import timedelta

from sqlalchemy import and_, func, or_, select, union_all
from sqlalchemy.orm import aliased

from app.admin_api.pwa_analytics_learning import (
    RETURN_LEARNING_EVENTS, activation_query, activation_values, bounded_rows, foundation_query,
    foundation_summary, owner, ratio, returned_accounts, shift,
)
from app.admin_api.pwa_analytics_platforms import PWA_MAP_OPEN_PREFIX
from app.admin_api.pwa_metrics import _window
from app.admin_api.pwa_read import _user_segment_clause
from app.db.models.course_miniapp_event import CourseMiniAppEvent as Event
from app.db.models.user import User

COURSE_CLIENTS = ('android', 'telegram', 'iphone_pwa')
PWA = 'iphone_pwa'
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
# R2: only the PWA handoff redeem route writes this name (server-built, not
# client-writable). Activated: a PWA-tagged lesson start or completion within
# 24 hours of the account's first handoff.
HANDOFF_COMPLETED = 'pwa_handoff_completed'
HANDOFF_STEPS = ('lesson_started', *COMPLETED)
HANDOFF_WINDOW = timedelta(hours=24)
# R4: D1/D7 return per platform, from each account's first verified use of it.
ANDROID_OPENS = ('android_first_open', 'android_app_opened')
RETURN_LEARNING = (*RETURN_LEARNING_EVENTS, ANDROID_LESSON_STARTED)


async def _handoff_activation(db, *, boundary, since, now):
    """R2 handoff cohort as one SQL aggregate: each account's first handoff from
    the PWA boundary on is its anchor; eligible once 24 hours old; activated by
    a PWA-tagged lesson start or completion in [anchor, anchor + 24 h].

    No detail rows: reading every PWA learner's lesson rows filled the 5 000-row
    limit and hid the cohort (audit B2, 2026-11-13)."""
    in_period = (Event.created_at >= boundary, *_window(Event.created_at, since, now))
    owned_first = (select(Event.user_id.label('account'), func.min(Event.created_at).label('at'))
                   .where(Event.event_name == HANDOFF_COMPLETED, Event.user_id.is_not(None), *in_period)
                   .group_by(Event.user_id))
    legacy_first = (select(User.id.label('account'), func.min(Event.created_at).label('at'))
                    .select_from(Event).join(User, and_(Event.user_id.is_(None), Event.telegram_id == User.telegram_id))
                    .where(Event.event_name == HANDOFF_COMPLETED, Event.telegram_id > 0, *in_period)
                    .group_by(User.id))
    firsts = union_all(owned_first, legacy_first).subquery()
    anchors = (select(User.id.label('account'), User.telegram_id.label('telegram_id'),
                      func.min(firsts.c.at).label('at'))
               .select_from(firsts).join(User, User.id == firsts.c.account)
               .group_by(User.id, User.telegram_id).cte('pwa_handoff_anchor'))
    step = aliased(Event)
    in_window = (step.event_name.in_(HANDOFF_STEPS), client_tag(PWA, step), step.created_at >= boundary,
                 *_window(step.created_at, since, now), step.created_at >= anchors.c.at,
                 step.created_at <= shift(db, anchors.c.at, HANDOFF_WINDOW.days))
    owned = select(step.id).where(step.user_id == anchors.c.account, *in_window).correlate(anchors).exists()
    legacy = select(step.id).where(step.user_id.is_(None), step.telegram_id == anchors.c.telegram_id,
                                   step.telegram_id > 0, *in_window).correlate(anchors).exists()
    eligible = anchors.c.at <= now - HANDOFF_WINDOW
    activated = returned_accounts(anchors.c.account, eligible, evidence=(owned, legacy))
    total, done = (await db.execute(select(func.count().filter(eligible),
        select(func.count()).select_from(activated).scalar_subquery()).select_from(anchors))).one()
    return {'eligible': total, 'activated': done, 'percent': ratio(done, total)}


async def _pwa_activation(db, *, boundary, since, now):
    """R2. The onboarding cohort is anchored on `onboarding_completed` tagged by
    the PWA onboarding route. Onboarding is deduplicated per profile, so an
    account onboarded on another client is not in it. Only PWA-tagged steps
    count. The handoff cohort starts at the PWA boundary, when PWA learning
    rows began to carry the tag."""
    onboarded_since = await db.scalar(select(func.min(Event.created_at)).where(
        Event.event_name == 'onboarding_completed', client_tag(PWA), Event.created_at <= now))
    rows = None if onboarded_since is None else await bounded_rows(db, activation_query(
        client_tag(PWA), Event.created_at >= onboarded_since, since=since, now=now), payload_index=3)
    activation, direct = activation_values(rows, now=now)
    handoff = None if boundary is None else await _handoff_activation(db, boundary=boundary, since=since, now=now)
    limited = onboarded_since is not None and rows is None
    since_by_key = {key: at.isoformat() for key, at in
                    (('activation', onboarded_since), ('handoff_activation', boundary)) if at}
    return {'activation': activation, 'direct_activation': direct, 'handoff_activation': handoff,
            }, since_by_key, limited


def platform_use(platform, boundary, model=Event):
    """Verified use of one platform (R4).

    Android opens and PWA course-map opens are written by the server under a
    name or dedupe key that only that client's route writes, so they count for
    all history. Learning outcomes count by the route-set final client key,
    from the platform boundary on. Telegram opens have no exclusive signal
    (A3), so Telegram use is learning only."""
    signals = []
    if platform == 'android':
        signals += [model.event_name.in_(ANDROID_OPENS),
                    and_(model.event_name.in_(COMPLETED), model.source == ANDROID_COMPLETION_SOURCE)]
    if platform == PWA:
        signals.append(and_(model.event_name == 'miniapp_opened',
                            model.dedupe_key.like(PWA_MAP_OPEN_PREFIX + '%')))
    if boundary is not None:
        signals.append(and_(model.event_name.in_(RETURN_LEARNING), client_tag(platform, model),
                            model.created_at >= boundary))
    return or_(*signals) if signals else None


async def platform_return_retention(db, *, platform, boundary, since, now):
    """D1 (24-48 h) and D7 (168-192 h) after each account's first use of this
    platform, counting only this platform's use as a return. Cohorts mature as
    in Overall `_cohort_returns`. Returns (series, first use of any account)."""
    use = platform_use(platform, boundary)
    if use is None:
        return None, None
    # `owner` split into its two branches: the OR join made the planner loop
    # over every account (1.7 s on 1M rows for any period).
    owned_first = (select(Event.user_id.label('account'), func.min(Event.created_at).label('at'))
                   .where(use, Event.user_id.is_not(None), Event.created_at <= now).group_by(Event.user_id))
    legacy_first = (select(User.id.label('account'), func.min(Event.created_at).label('at'))
                    .select_from(Event).join(User, and_(Event.user_id.is_(None), Event.telegram_id == User.telegram_id))
                    .where(use, Event.telegram_id > 0, Event.created_at <= now).group_by(User.id))
    uses = union_all(owned_first, legacy_first).subquery()
    # A CTE: PostgreSQL materializes it once for the cohort counts and both
    # returned-account sets.
    first = (select(User.id.label('account'), User.telegram_id.label('telegram_id'),
                    func.min(uses.c.at).label('first_use'))
             .select_from(uses).join(User, User.id == uses.c.account)
             .group_by(User.id, User.telegram_id).cte('platform_first_use'))
    later = aliased(Event)
    columns, windows = [func.min(first.c.first_use)], []
    for days in (1, 7):
        end = now - timedelta(days=days + 1)
        start = end - (now - since) if since else None
        window = (platform_use(platform, boundary, later),
                  later.created_at >= shift(db, first.c.first_use, days),
                  later.created_at < shift(db, first.c.first_use, days + 1), later.created_at <= now)
        # Two EXISTS instead of the OR in `owner`, as in Overall return_retention,
        # each a semi-join over the cohort (see `returned_accounts`).
        owned = select(later.id).where(later.user_id == first.c.account, *window).correlate(first).exists()
        legacy = select(later.id).where(later.user_id.is_(None), later.telegram_id == first.c.telegram_id,
                                        later.telegram_id > 0, *window).correlate(first).exists()
        mature = and_(first.c.first_use <= end, *([first.c.first_use > start] if start else []))
        returned = returned_accounts(first.c.account, mature, evidence=(owned, legacy))
        columns += [func.count().filter(mature), select(func.count()).select_from(returned).scalar_subquery()]
        windows.append((days, start, end))
    # One statement, so the first-use aggregation runs once for both windows.
    started, *counts = (await db.execute(select(*columns).select_from(first))).one()
    if started is None:
        return None, None
    result = {}
    for (days, start, end), eligible, returned in zip(windows, counts[::2], counts[1::2]):
        result[f'd{days}'] = {'eligible': eligible, 'returned': returned, 'percent': ratio(returned, eligible),
                              'cohort_start': start.isoformat() if start else None, 'cohort_end': end.isoformat()}
    return result, started


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
    result['return_retention'], returns_since = await platform_return_retention(
        db, platform=platform, boundary=boundary, since=since, now=now)
    if returns_since is not None:
        attributed_since['return_retention'] = returns_since.isoformat()
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
    if platform == PWA:
        values, since_by_key, limited = await _pwa_activation(db, boundary=boundary, since=detail_since, now=now)
        result.update(values)
        attributed_since.update(since_by_key)
        result['detail_limited'] = result['detail_limited'] or limited
    if platform == 'android':
        completed = await _completed_lessons(db, Event.event_name.in_((*COMPLETED, 'android_lesson_completed')),
            Event.source == ANDROID_COMPLETION_SOURCE, since=since, now=now)
    else:
        attributed_since['completed_user_lessons'] = since_iso
        completed = None if attributed is None else await _completed_lessons(
            db, Event.event_name.in_(COMPLETED), *attributed, since=since, now=now)
    return {**result, 'features': features, 'completed_user_lessons': completed,
            'attributed_since': attributed_since, 'detail_since': detail_since.isoformat()}

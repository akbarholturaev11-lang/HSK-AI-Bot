"""Typed first-party analytics projections; no private records or provider IO."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, func, or_, select

from app.admin_api.pwa_metrics import COURSE_EVENTS, _window
from app.admin_api.pwa_read import _user_segment_clause
from app.db.models.course_miniapp_event import CourseMiniAppEvent as Event
from app.db.models.payment import Payment
from app.db.models.user import User
from app.services.admin_analytics_identity import analytics_user_join
from app.services.admin_miniapp_service import _payment_user_join, admin_miniapp_today_start

ANALYTICS_TZ = ZoneInfo('Asia/Shanghai')
LEVELS = ('beginner','hsk1','hsk2','hsk3','hsk4','hsk5','hsk6','nhsk1','nhsk2','nhsk3')
LANGUAGES = ('uz','ru','tj')


def _day(db, column):
    """Business-calendar bucket; timestamps remain UTC in storage and metadata."""
    if db.get_bind().dialect.name == 'postgresql':
        return func.date(func.timezone('Asia/Shanghai',column))
    return func.date(column,'+8 hours')


def _known(column, allowed):
    return case((column.in_(allowed),column),else_='unknown')


async def _distribution(db,column,allowed,*,now):
    key=_known(column,allowed)
    rows=(await db.execute(select(key.label('key'),func.count(User.id).label('accounts'))
        .where(User.created_at<=now).group_by(key))).all()
    values={row.key:int(row.accounts) for row in rows}
    return [{'key':key,'accounts':values[key]} for key in (*allowed,'unknown') if values.get(key)]


async def learning_activity_series(db,*,period,now):
    days=7 if period=='weekly' else 30
    today=now.astimezone(ANALYTICS_TZ).date()
    start=admin_miniapp_today_start(now)-timedelta(days=days-1)
    day=_day(db,Event.created_at)
    rows=(await db.execute(select(day.label('day'),func.count(func.distinct(User.id)).label('accounts'))
        .select_from(Event).join(User,and_(analytics_user_join(Event),
            or_(Event.user_id.is_not(None),Event.telegram_id>0)))
        .where(User.created_at<=now,Event.event_name.in_(COURSE_EVENTS),Event.created_at>=start,Event.created_at<=now)
        .group_by(day).order_by(day))).all()
    counts={str(row.day):int(row.accounts) for row in rows}
    return {'points':[{'date':(today-timedelta(days=days-1-index)).isoformat(),
                       'accounts':counts.get((today-timedelta(days=days-1-index)).isoformat(),0)}
                      for index in range(days)],
            'since':start.isoformat(),'through':now.isoformat(),'timezone':'Asia/Shanghai',
            'grain':'distinct canonical learning accounts per calendar day',
            'scope':'calendar_7_days' if days==7 else 'calendar_30_days',
            'source':'course_miniapp_events: recorded lesson/practice activity'}


async def home_overview_metrics(db,*,period,now=None,overview=False):
    """Only bounded scalar/grouped SQL. Must run in a protected read transaction."""
    now=now or datetime.now(timezone.utc)
    since=now-timedelta(days={'weekly':7,'monthly':30}[period]) if period!='all_time' else None
    active_since=since or now-timedelta(days=30)
    paid=_user_segment_clause('paid',now=now)
    expiring=_user_segment_clause('expiring_pro',now=now)
    current_block=and_(User.bot_blocked_at.is_not(None),User.bot_blocked_at<=now,or_(User.bot_unblocked_at.is_(None),
        User.bot_unblocked_at<User.bot_blocked_at))
    bot_period=and_(current_block,*_window(User.bot_blocked_at,since,now)) if since else current_block
    row=(await db.execute(select(
        func.count(User.id).label('users_total'),
        func.count(User.id).filter(and_(*_window(User.created_at,since,now))).label('new_accounts'),
        func.count(User.id).filter(and_(*_window(User.last_active_at,active_since,now))).label('active_accounts'),
        func.count(User.id).filter(and_(*_window(User.last_active_at,admin_miniapp_today_start(now),now))).label('active_today'),
        func.count(User.id).filter(paid).label('active_pro'),
        func.count(User.id).filter(expiring).label('expiring_pro'),
        func.count(User.id).filter(bot_period).label('bot_blocked'),
        func.count(User.id).filter(_user_segment_clause('blocked',now=now)).label('blocked_current'),
    ).where(User.created_at<=now))).one()
    result={key:int(value or 0) for key,value in row._mapping.items()}
    pay_date=func.coalesce(Payment.reviewed_at,Payment.submitted_at)
    payments=(await db.execute(select(Payment.payment_status,func.count(Payment.id)).where(
        Payment.payment_status.in_(('pending','approved','rejected')),*_window(pay_date,since,now))
        .group_by(Payment.payment_status))).all()
    result['payments_by_status']={key:dict(payments).get(key,0) for key in ('pending','approved','rejected')}
    result['pending_current']=int(await db.scalar(select(func.count(Payment.id)).where(
        Payment.payment_status=='pending',Payment.submitted_at<=now)) or 0)
    result['paying_accounts']=int(await db.scalar(select(func.count(func.distinct(User.id)))
        .select_from(Payment).join(User,_payment_user_join()).where(Payment.payment_status=='approved',
            or_(Payment.user_id.is_not(None),User.telegram_id>0),*_window(pay_date,since,now))) or 0)
    result['activity']=await learning_activity_series(db,period=period,now=now)
    if overview:
        course=(await db.execute(select(
            func.count(func.distinct(User.id)).label('engaged_accounts'),
            func.count(func.distinct(User.id)).filter(Event.event_name.in_(('lesson_started','android_lesson_started'))).label('started_accounts'),
            func.count(func.distinct(User.id)).filter(Event.event_name.in_(('lesson_completed','book_lesson_completed','android_lesson_completed'))).label('completed_accounts'),
        ).select_from(Event).join(User,and_(analytics_user_join(Event),
            or_(Event.user_id.is_not(None),Event.telegram_id>0)))
            .where(Event.event_name.in_(COURSE_EVENTS),*_window(Event.created_at,since,now)))).one()
        result['course_engagement']={key:int(value) for key,value in course._mapping.items()}
        result['levels']=await _distribution(db,User.level,LEVELS,now=now)
        result['languages']=await _distribution(db,User.language,LANGUAGES,now=now)
    return {'platform':'overall','period':period,'since':since.isoformat() if since else None,
            'generated_at':now.isoformat(),'timezone':'Asia/Shanghai','platform_counts_overlap':True,
            'available':True,'source':'users + payments + canonical learning events',
            'scope':{'section':'overview' if overview else 'home','active_accounts':'selected period or rolling 30 days',
                     'current_counts':'snapshot as of generated_at; action/profile/payment reads remain live',
                     'payments':'reviewed_at or submitted_at; through generated_at',
                     'expiring_pro':'paid entitlement; ends within next three days',
                     'bot_blocked':'currently bot-blocked, last block in selected period (all_time: current)'},
            'metrics':result}

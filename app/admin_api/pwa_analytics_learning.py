"""Source-bound learning projections, with bounded detailed-history calculations."""
from datetime import timedelta

from sqlalchemy import and_, func, or_, select

from app.admin_api.pwa_analytics import _known, home_overview_metrics
from app.admin_api.pwa_metrics import _window, overall_activity_metrics
from app.admin_api.pwa_read import _user_segment_clause
from app.db.models.ai_usage import AIUsageEvent
from app.db.models.conversion_funnel_event import ConversionFunnelEvent as Funnel
from app.db.models.course_miniapp_event import CourseMiniAppEvent as Event
from app.db.models.message import Message
from app.db.models.user import User
from app.db.models.payment import Payment
from app.services.admin_miniapp_service import _payment_user_join
from app.db.models.voice_practice_session import VoicePracticeSession as Voice
from app.services.admin_analytics_identity import analytics_user_join
from app.services.admin_miniapp_service import (
    _activation_funnel, _duration_seconds, _lesson_attempt_durations,
    _miniapp_session_durations, _payment_attempt_funnel,
)
from app.services.course_miniapp_admin_analytics_service import (
    FOUNDATION_FUNNEL_EVENT_NAMES, build_foundation_metrics,
)

DETAIL_LIMIT = 5000
PAYLOAD_LIMIT = 4096


def ratio(numerator, denominator):
    return round(100*numerator/denominator, 2) if denominator else None


def owner(model, telegram_column='telegram_id'):
    return and_(analytics_user_join(model, telegram_column=telegram_column),
        or_(model.user_id.is_not(None), getattr(model, telegram_column)>0))


async def bounded_rows(db, query, *, payload_index=None):
    """A sentinel refuses incomplete metrics. Never silently calculate a sample."""
    rows=(await db.execute(query.limit(DETAIL_LIMIT+1))).all()
    if len(rows)>DETAIL_LIMIT:
        return None
    if payload_index is not None and any(len(row[payload_index] or '')>=PAYLOAD_LIMIT+1 for row in rows):
        return None
    return [tuple(row) for row in rows]


def shift(db, column, days):
    if db.get_bind().dialect.name=='postgresql':
        return column+timedelta(days=days)
    return func.datetime(column, f'+{days} days')


async def retention(db, *, since, now):
    result={}
    for days in (1,7):
        end=now-timedelta(days=days+1)
        start=end-(now-since) if since else None
        returned=select(Event.id).where(owner(Event), Event.event_name=='miniapp_opened',
            Event.created_at>=shift(db,User.created_at,days),
            Event.created_at<shift(db,User.created_at,days+1),Event.created_at<=now).correlate(User).exists()
        eligible,count=(await db.execute(select(func.count(User.id),func.count(User.id).filter(returned))
            .where(User.created_at<=end,*([User.created_at>start] if start else [])))).one()
        result[f'd{days}']={'eligible':eligible,'returned':count,'percent':ratio(count,eligible),
            'cohort_start':start.isoformat() if start else None,'cohort_end':end.isoformat()}
    return result


async def learning_metrics(db, *, period, since, now):
    # Historical detail intentionally retains the existing 30-day all-time cap.
    detail_since=since or now-timedelta(days=30)
    paid=_user_segment_clause('paid',now=now)
    denominators=(await db.execute(select(func.count(User.id).filter(paid),func.count(User.id).filter(~paid))
        .where(User.created_at<=now))).one()
    features=[]
    groups=(('lessons',Event,('lesson_started','android_lesson_started','section_started')),
        ('tests',Event,('test_started','test_completed')),('practice',Event,('training_started','training_completed','android_practice_started','android_practice_completed')),
        ('mistakes',Event,('mistake_review_started','mistake_review_completed')),
        ('ai',AIUsageEvent,None),('voice',Voice,None))
    for key,model,names in groups:
        column=Voice.started_at if model is Voice else model.created_at
        tid='user_telegram_id' if model in (AIUsageEvent,Voice) else 'telegram_id'
        conditions=_window(column,detail_since,now)
        if names:conditions.append(model.event_name.in_(names))
        if model is AIUsageEvent:conditions.append(model.source=='qa')
        values=(await db.execute(select(func.count(func.distinct(User.id)).filter(paid),
            func.count(func.distinct(User.id)).filter(~paid)).select_from(model).join(User,owner(model,tid))
            .where(*conditions,User.created_at<=now))).one()
        features.append({'key':key,'paid':values[0],'free':values[1]})
    # No message contents, provider histories, answers or corrections are read.
    messages,chat_users=(await db.execute(select(func.count(Message.id),func.count(func.distinct(Message.user_id)))
        .where(Message.role=='user',Message.content_type=='text',*_window(Message.created_at,detail_since,now)))).one()
    voice_rows=await bounded_rows(db,select(Voice.started_at,Voice.ended_at).where(
        Voice.status=='completed',Voice.turn_count>0,Voice.ended_at<=now,*_window(Voice.started_at,detail_since,now)))
    durations=[seconds for start,end in voice_rows for seconds in [_duration_seconds(start,end)] if seconds] if voice_rows is not None else None
    session_rows=await bounded_rows(db,select(User.id,Event.session_id,Event.created_at)
        .select_from(Event).join(User,owner(Event)).where(Event.session_id.is_not(None),Event.session_id!='',
            *_window(Event.created_at,detail_since,now)).order_by(Event.created_at,Event.id))
    sessions,session_durations=_miniapp_session_durations(session_rows) if session_rows is not None else (None,None)
    lesson_rows=await bounded_rows(db,select(User.id,Event.level,Event.lesson_id,Event.lesson_order,Event.session_id,
        Event.event_name,Event.created_at).select_from(Event).join(User,owner(Event)).where(
            Event.event_name.in_(('lesson_started','lesson_completed','book_lesson_completed')),
            *_window(Event.created_at,detail_since-timedelta(hours=8),now)).order_by(Event.created_at,Event.id))
    lesson_durations=_lesson_attempt_durations(lesson_rows,completion_since=detail_since) if lesson_rows is not None else None
    activation_rows=await bounded_rows(db,select(Event.event_name,User.id,Event.created_at,func.substr(Event.payload_json,1,PAYLOAD_LIMIT+1))
        .select_from(Event).join(User,owner(Event)).where(Event.event_name.in_(
            ('onboarding_completed','lesson_started','section_completed','lesson_completed','book_lesson_completed')),
            *_window(Event.created_at,detail_since,now)).order_by(Event.created_at,Event.id),payload_index=3)
    activation=None
    direct_activation=None
    if activation_rows is not None:
        a=_activation_funnel(activation_rows,now=now)
        direct=a['variants'].get('direct_start_v1')
        if direct:direct_activation={'eligible':direct['lesson_started_eligible'],'started':direct['lesson_started_2m'],
            'percent':ratio(direct['lesson_started_2m'],direct['lesson_started_eligible'])}
        activation={'eligible':a['lesson_started_eligible'],'started':a['lesson_started_2m'],
            'percent':ratio(a['lesson_started_2m'],a['lesson_started_eligible'])}
    foundation_rows=await bounded_rows(db,select(Event.event_name,User.id,Event.source,Event.level,
        Event.lesson_order,func.substr(Event.payload_json,1,PAYLOAD_LIMIT+1),Event.created_at)
        .select_from(Event).join(User,owner(Event)).where(Event.event_name.in_(FOUNDATION_FUNNEL_EVENT_NAMES),
            *_window(Event.created_at,detail_since,now)).order_by(Event.created_at,Event.id),payload_index=5)
    foundation=None
    if foundation_rows is not None:
        f=build_foundation_metrics(foundation_rows,now=now)
        foundation={'started_users':f['started_users'],'completed_users':f['completed_users'],
            'completion_percent':ratio(f['completed_users'],f['started_users']),
            'first_attempt':{'objectives':f['first_attempt']['objectives'],'correct':f['first_attempt']['correct'],
                'percent':ratio(f['first_attempt']['correct'],f['first_attempt']['objectives'])},
            'checkpoint':{'eligible':f['checkpoint_to_paywall']['checkpoint_users'],'reached':f['checkpoint_to_paywall']['paywall_users'],
                'percent':ratio(f['checkpoint_to_paywall']['paywall_users'],f['checkpoint_to_paywall']['checkpoint_users'])},
            'parts':[{'part':v['part'],'completed_users':v['completed_users']} for v in f['parts']]}
    completed=select(User.id,Event.level,Event.lesson_order).select_from(Event).join(User,owner(Event)).where(
        Event.event_name.in_(('lesson_completed','book_lesson_completed','android_lesson_completed')),Event.lesson_order.is_not(None),
        *_window(Event.created_at,since,now)).distinct().subquery()
    completed_lessons=int(await db.scalar(select(func.count()).select_from(completed)) or 0)
    result=await overall_activity_metrics(db,since=since,now=now)
    result.update({'retention':await retention(db,since=since,now=now),'features':features,
        'feature_denominators':{'paid':denominators[0],'free':denominators[1]},'activation':activation,
        'direct_activation':direct_activation,'completed_user_lessons':completed_lessons,
        'foundation':foundation,'chat':{'messages':messages,'accounts':chat_users,'average':round(messages/chat_users,2) if chat_users else None},
        'voice_minutes':round(sum(durations)/60,2) if durations is not None else None,
        'session_seconds':round(sum(session_durations)/len(session_durations)) if session_durations else None,
        'sessions':sessions,'lesson_seconds':round(sum(lesson_durations)/len(lesson_durations)) if lesson_durations else None,
        'timed_lessons':len(lesson_durations) if lesson_durations is not None else None,
        'detail_since':detail_since.isoformat(),'detail_row_limit':DETAIL_LIMIT,
        'detail_limited':any(v is None for v in (durations,session_rows,lesson_rows,activation_rows,foundation_rows))})
    return result


async def funnel_metrics(db, *, since, now):
    result=await overall_activity_metrics(db,since=since,now=now)
    names=('checkout_opened','payment_screenshot_submitted','payment_approved')
    payment_owner=select(Payment.id).where(Payment.id==Funnel.payment_id,_payment_user_join(),
        (Funnel.event_name!='payment_approved') | (Payment.payment_status=='approved')).correlate(Funnel,User).exists()
    rows=await bounded_rows(db,select(Funnel.event_name,User.id,Funnel.payment_id,
        func.substr(Funnel.payload_json,1,PAYLOAD_LIMIT+1),Funnel.created_at)
        .select_from(Funnel).join(User,owner(Funnel)).where(Funnel.event_name.in_(names),
            (Funnel.event_name=='checkout_opened') | payment_owner,
            *_window(Funnel.created_at,since,now)).order_by(Funnel.created_at,Funnel.id),payload_index=3)
    if rows is None:
        result['attempt_funnel']=None
    else:
        f=_payment_attempt_funnel(rows)
        steps=[{'key':s['key'],'accounts':s['users']} for s in f['steps']]
        result['attempt_funnel']={'attempts':f['attempts'],'collecting':f['collecting'],'steps':steps,
            'drops':[{'from':a['key'],'to':b['key'],'lost':max(0,a['accounts']-b['accounts']),
                'percent':ratio(max(0,a['accounts']-b['accounts']),a['accounts'])} for a,b in zip(steps,steps[1:])]}
    return result

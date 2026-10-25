"""Lazy bounded reuse of the existing experiment estimators; no rollout decisions."""
from datetime import timedelta
from sqlalchemy import func, select
from app.admin_api.pwa_analytics_learning import PAYLOAD_LIMIT, bounded_rows, owner
from app.admin_api.pwa_metrics import _window
from app.db.models.course_miniapp_event import CourseMiniAppEvent as Event
from app.db.models.conversion_funnel_event import ConversionFunnelEvent as Funnel
from app.db.models.message import Message
from app.db.models.payment import Payment
from app.db.models.user import User
from app.services.admin_miniapp_service import (
    _d1_recovery_experiment, _matured_notification_open_proxy, _payment_user_join,
    _sales_value_experiment, SALES_VALUE_MEANINGFUL_EVENTS,
)


def numeric_tree(value):
    """Only estimator-owned numeric fields; never raw payload text or identity."""
    if value is None or isinstance(value,(int,float,bool)):
        return value
    if isinstance(value,dict):
        return {key:numeric_tree(v) for key,v in value.items() if isinstance(v,(dict,list,int,float,bool)) or v is None}
    if isinstance(value,list):return [numeric_tree(v) for v in value if not isinstance(v,str)]
    return None


async def experiment_metrics(db, *, since, now):
    since=since or now-timedelta(days=30)
    columns=(Event.event_name,User.id,Event.source,Event.level,Event.lesson_id,Event.lesson_order,
        func.substr(Event.payload_json,1,PAYLOAD_LIMIT+1),Event.created_at)
    base=select(*columns).select_from(Event).join(User,owner(Event))
    assignments=await bounded_rows(db,base.where(Event.event_name.in_(('sales_offer_assigned','d1_recovery_assigned')),
        *_window(Event.created_at,since,now)).order_by(Event.created_at,Event.id),payload_index=6)
    if assignments is None:return {'sales':None,'recovery':None,'notification':None,'since':since.isoformat()}
    ids={row[1] for row in assignments}
    course=[];funnel=[];payments=[];errors=[];blocks=[]
    if ids:
        earliest=min(row[7] for row in assignments)
        names=tuple(SALES_VALUE_MEANINGFUL_EVENTS|{'sales_bridge_seen','sales_bridge_cta','sales_offer_seen','sales_offer_dismissed',
            'paywall_seen','foundation_completed','d1_recovery_sent','d1_recovery_send_failed','miniapp_opened',
            'lesson_completed','book_lesson_completed'})
        course=await bounded_rows(db,base.where(User.id.in_(ids),Event.event_name.in_(names),
            *_window(Event.created_at,earliest,now)).order_by(Event.created_at,Event.id),payload_index=6)
        funnel=await bounded_rows(db,select(Funnel.event_name,User.id,Funnel.payment_id,
            func.substr(Funnel.payload_json,1,PAYLOAD_LIMIT+1),Funnel.created_at)
            .select_from(Funnel).join(User,owner(Funnel)).where(User.id.in_(ids),
                Funnel.event_name.in_(('checkout_opened','payment_screenshot_submitted','payment_approved')),
                *_window(Funnel.created_at,earliest,now)).order_by(Funnel.created_at,Funnel.id),payload_index=3)
        payments=await bounded_rows(db,select(Payment.id,User.id,Payment.payment_status,Payment.amount,Payment.currency,
            Payment.base_amount,Payment.reviewed_at,Payment.submitted_at).join(User,_payment_user_join())
            .where(User.id.in_(ids),Payment.submitted_at<=now))
        errors=await bounded_rows(db,select(Message.user_id,Message.created_at).where(Message.user_id.in_(ids),
            Message.content_type=='app_error_context',*_window(Message.created_at,earliest,now)))
        blocks=await bounded_rows(db,select(User.id,User.bot_blocked_at).where(User.id.in_(ids)))
    valid=all(v is not None for v in (course,funnel,payments,errors,blocks))
    sales=_sales_value_experiment(assignments+course,funnel,payments,now=now,error_rows=errors) if valid else None
    recovery=_d1_recovery_experiment(assignments+course,blocks,now=now) if valid else None
    sent=await bounded_rows(db,select(User.id,Event.created_at).select_from(Event).join(User,owner(Event))
        .where(Event.event_name=='motivation_lesson_unfinished_sent',*_window(Event.created_at,since,now)))
    opens=await bounded_rows(db,select(User.id,Event.created_at).select_from(Event).join(User,owner(Event))
        .where(Event.event_name=='miniapp_opened',Event.source=='motivation_reminder',*_window(Event.created_at,since,now))) if sent else []
    notification=_matured_notification_open_proxy(sent,opens,now=now) if sent is not None and opens is not None else None
    return {'sales':numeric_tree(sales),'recovery':numeric_tree(recovery),'notification':numeric_tree(notification),
        'since':since.isoformat(),'scope':'selected assignments; all_time detail rolling 30 days; existing mature ITT estimators',
        'sales_status':sales['status'] if sales else None,'detail_limit':5000}

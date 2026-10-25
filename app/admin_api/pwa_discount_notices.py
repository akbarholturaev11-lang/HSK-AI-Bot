"""Bounded canonical discount audiences and reviewed shared-channel copy."""
from datetime import datetime, timedelta, timezone
import html

from sqlalchemy import and_, case, exists, func, not_, or_, select

from app.admin_api.pwa_access_grants import CommandError
from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_outbound import LANGS, MAX_AUDIENCE, _hash
from app.bot.keyboards.subscription import admin_discount_entry_keyboard
from app.db.models.android_push import AndroidPushToken
from app.db.models.desktop import DesktopDevice
from app.db.models.payment import Payment
from app.db.models.user import User
from app.services.discount_notification_service import DiscountNotificationService
from app.services.notification_delivery_service import NotificationDeliveryService
from app.services.admin_miniapp_service import _payment_user_join


def notice_available(row):
    now=datetime.now(timezone.utc)
    return bool(row.is_active and not row.notify_enabled and row.notification_sent_at is None
        and _utc(row.starts_at)<=now<_utc(row.ends_at) and not row.notify_media_file_id)


def notice_recipient_hash(user):
    # Extend the ordinary transport snapshot with live offer-relevant state.
    from app.admin_api.pwa_outbound import recipient_hash
    return _hash([recipient_hash(user),user.level,user.payment_status,user.payment_method,
        _utc(user.end_date).isoformat() if user.end_date else None])


async def notice_users(db, row, settings_obj, *, lock=False, user_ids=None):
    """Bounded SQL, no per-user usage/transport loop in prepare.

    Canonical ownership/legacy payment join matches shared discount checkout.
    Global quota excludes the current user's active reservations exactly as
    DiscountCampaignRepository.count_used(exclude_user=...) does.
    """
    now=datetime.now(timezone.utc)
    active=or_(Payment.payment_status.in_(('pending','approved')),
        and_(Payment.payment_status=='draft',Payment.submitted_at>=now-timedelta(minutes=30)))
    owner=_payment_user_join()
    own_used=select(func.count()).select_from(Payment).where(Payment.discount_campaign_id==row.id,
        Payment.payment_status.in_(('pending','approved')),owner).correlate(User).scalar_subquery()
    last=select(func.max(Payment.submitted_at)).where(Payment.discount_campaign_id==row.id,
        Payment.payment_status.in_(('pending','approved')),owner).correlate(User).scalar_subquery()
    own_reserved=select(func.count()).select_from(Payment).where(Payment.discount_campaign_id==row.id,
        active,owner).correlate(User).scalar_subquery()
    total=select(func.count()).select_from(Payment).where(Payment.discount_campaign_id==row.id,active).scalar_subquery()
    telegram=and_(User.telegram_id>0,or_(User.bot_blocked_at.is_(None),User.bot_unblocked_at>=User.bot_blocked_at))
    delivery=NotificationDeliveryService(db,settings_obj)
    channels=telegram
    if delivery.android_enabled:
        native=exists(select(AndroidPushToken.device_id).join(DesktopDevice,DesktopDevice.id==AndroidPushToken.device_id)
            .where(DesktopDevice.platform=='android',DesktopDevice.revoked_at.is_(None),
                AndroidPushToken.notifications_allowed.is_(True),or_(DesktopDevice.user_id==User.id,
                    and_(DesktopDevice.user_id.is_(None),User.telegram_id>0,DesktopDevice.telegram_id==User.telegram_id))))
        channels=or_(telegram,native)
    query=select(User).where(User.status!='blocked',channels).execution_options(populate_existing=True)
    if settings_obj.admin_id_list:
        query=query.where(or_(User.telegram_id.is_(None),User.telegram_id.not_in(settings_obj.admin_id_list)))
    if row.target_user_id is not None:
        query=query.where(User.id==row.target_user_id)
    elif row.target_telegram_id is not None:
        query=query.where(User.telegram_id==row.target_telegram_id,User.telegram_id>0)
    else:
        # Shared global notification policy excludes paid, currently active users.
        query=query.where(not_(and_(func.lower(func.trim(User.status))=='active',func.lower(func.trim(func.coalesce(User.payment_status,'')))=='approved',User.end_date.is_not(None),User.end_date>now)))
    for field,column in (('audience_status',User.status),('audience_language',User.language),('audience_level',User.level)):
        value=getattr(row,field)
        if value is not None:query=query.where(column==value)
    if row.repeat_interval_days:
        query=query.where(or_(own_used==0,last<=now-timedelta(days=row.repeat_interval_days)))
    else:
        query=query.where(own_used==0)
    if row.quota_total:query=query.where(total-own_reserved<row.quota_total)
    if user_ids is not None:
        if not 1<=len(user_ids)<=MAX_AUDIENCE:raise ValueError('Invalid bounded targets')
        query=query.where(User.id.in_(user_ids))
    query=query.order_by(User.id).limit(MAX_AUDIENCE+1)
    if lock:query=query.with_for_update(of=User)
    return list((await db.scalars(query)).all())


async def notice_copy(db,row):
    # PWA-created offer fields are plain authored text; shared formatter uses HTML.
    # Escape a detached view once so no stored offer or checkout data is changed.
    from types import SimpleNamespace
    values={column.key:getattr(row,column.key) for column in row.__table__.columns}
    for key,value in list(values.items()):
        if key=='title' or key=='reason' or key.startswith(('title_','reason_')):
            values[key]=html.escape(value,quote=False) if value else value
    safe=SimpleNamespace(**values)
    service=DiscountNotificationService(db)
    texts={lang:await service._notification_text(safe,lang,None) for lang in LANGS}
    phone={lang:await service._notification_text(safe,lang,None,for_phone=True) for lang in LANGS}
    buttons={lang:admin_discount_entry_keyboard(lang,campaign_id=row.id).model_dump(mode='json') for lang in LANGS}
    if any(len(value.encode('utf-16-le'))//2>4096 for value in texts.values()):
        raise CommandError('admin_pwa_invalid_payload',400)
    return texts,phone,buttons


async def emit_discount_notice(message, *, session_factory, settings_obj, bot):
    """Dedicated shared notice session; the outer PWA claim is already durable."""
    from aiogram.types import InlineKeyboardMarkup
    from app.services.course_notification_service import CourseNotificationService
    from app.services.notification_delivery_service import DELIVERED, TelegramNotice
    async with session_factory() as db:
        user=await db.get(User,message.user_id)
        if user is None or user.status=='blocked':
            raise RuntimeError('Notice owner unavailable')
        outcome=await NotificationDeliveryService(db,settings_obj).deliver(bot,user,
            key='discount_offer',lang=message.language,
            telegram=TelegramNotice(text=message.text,reply_markup=InlineKeyboardMarkup.model_validate(message.reply_markup),
                parse_mode='HTML',disable_web_page_preview=True),reason='discount_notification',
            body=message.phone_body,release_before_io=True)
        if outcome in DELIVERED:
            await CourseNotificationService(db).record_from_text(user,key='subscription_offer',lang=message.language,
                text=message.text,action='subscription',source='discount_notification',
                dedupe_key='discount_campaign:'+str(message.notice_campaign_id))
        await db.commit()
    if outcome not in DELIVERED:
        raise RuntimeError('Notice outcome requires operator review')
    return None

"""Actual device inventory, foreground proofs and Mini App presence, kept distinct."""
import json
import re
from datetime import timedelta
from types import SimpleNamespace

from sqlalchemy import func, select

from app.admin_api.pwa_analytics import _known
from app.admin_api.pwa_analytics_learning import PAYLOAD_LIMIT, bounded_rows, owner
from app.admin_api.pwa_metrics import _window
from app.db.models.course_miniapp_event import CourseMiniAppEvent as Event
from app.db.models.desktop import DesktopDevice as Device
from app.db.models.user import User
from app.db.models.user_client_presence import UserClientPresence as Presence
from app.services.desktop_analytics_service import DesktopAnalyticsService


async def platform_metrics(db, *, since, now, platform='overall'):
    keys=('android','macos','windows') if platform=='overall' else (platform,)
    cards=[]
    for key in keys:
        if key not in ('android','macos','windows'):continue
        devices,accounts,seen=(await db.execute(select(func.count(Device.id),func.count(func.distinct(Device.user_id)),
            func.count(Device.id).filter((Device.last_seen_at>=now-timedelta(days=30)) & (Device.last_seen_at<=now))).where(
                Device.platform==key,Device.revoked_at.is_(None),Device.created_at<=now))).one()
        cards.append({'platform':key,'devices':devices,'accounts':accounts,'online_devices_30d':seen,
            'active_dau':None,'active_wau':None,'active_mau':None})
    if platform in ('overall','android'):
        active=(await db.execute(select(*[func.count(func.distinct(User.id)).filter(
            Event.created_at>=now-timedelta(days=days)) for days in (1,7,30)])
            .select_from(Event).join(User,owner(Event)).where(Event.event_name=='android_app_opened',
                *_window(Event.created_at,now-timedelta(days=30),now)))).one()
        for card in cards:
            if card['platform']=='android':card.update(dict(zip(('active_dau','active_wau','active_mau'),active)))
    detail_limited=False
    if platform in ('overall','macos','windows'):
        rows=await bounded_rows(db,select(User.id,Event.created_at,Event.source,
            func.substr(Event.payload_json,1,PAYLOAD_LIMIT+1)).select_from(Event).join(User,owner(Event))
            .where(Event.event_name.in_(('desktop_first_open','desktop_app_opened','desktop_active_day')),
                *_window(Event.created_at,now-timedelta(days=30),now)).order_by(Event.created_at,Event.id),payload_index=3)
        detail_limited=rows is None
        if rows is not None:
            counts={key:[set(),set(),set()] for key in ('macos','windows')}
            for account,created,source,payload in rows:
                try:data=json.loads(payload or '{}')
                except (ValueError,TypeError):data={}
                key=DesktopAnalyticsService._row_platform(SimpleNamespace(source=source),data if isinstance(data,dict) else {})
                if not key:continue
                if created.tzinfo is None:created=created.replace(tzinfo=now.tzinfo)
                for index,days in enumerate((1,7,30)):
                    if created>=now-timedelta(days=days):counts[key][index].add(account)
            for card in cards:
                if card['platform'] in counts:card.update({k:len(v) for k,v in zip(
                    ('active_dau','active_wau','active_mau'),counts[card['platform']])})
    if platform in ('overall','telegram'):
        values=(await db.execute(select(func.count(func.distinct(Presence.user_id)),
            func.count(func.distinct(Presence.user_id)).filter(Presence.last_foreground_at>=now-timedelta(days=30)))
            .where(Presence.surface=='telegram_miniapp',Presence.first_seen_at<=now,Presence.last_foreground_at<=now))).one()
        cards.append({'platform':'telegram','accounts':values[0],'foreground_accounts_30d':values[1]})
    versions=[]
    for key in keys:
        if key not in ('android','macos','windows'):continue
        rows=(await db.execute(select(Device.app_version,func.count(Device.id),func.count(func.distinct(Device.user_id)))
            .where(Device.platform==key,Device.revoked_at.is_(None),Device.created_at<=now)
            .group_by(Device.app_version).order_by(func.count(Device.id).desc()).limit(12))).all()
        for version,n,accounts in rows:
            versions.append({'platform':key,'version':version if re.fullmatch(r'\d{1,5}(?:\.\d{1,5}){1,3}(?:[-+][A-Za-z0-9.]{1,15})?',version or '') else 'unknown',
                'devices':n,'accounts':accounts})
    return {'platforms':cards,'versions':versions,'desktop_detail_limited':detail_limited,
        'iphone_pwa_available':False,'scope':'current nonrevoked linked-device inventory; foreground proof rolling 1/7/30 days; Mini App last foreground presence',
        'versions_scope':'top 12 current version groups per native platform; remaining groups omitted',
        'overlap':True}

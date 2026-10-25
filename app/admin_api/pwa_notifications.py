"""Template text settings with a compact exact-content passkey commitment."""
from datetime import datetime, timezone
import hashlib
import json
import logging
from string import Formatter
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError, field_validator, model_validator
from sqlalchemy import select, text

from app.admin_api.pwa_access_grants import CommandError, StepId
from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_payment_review import StrictModel
from app.admin_api.pwa_read import read_transaction
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, _authorized_admin, authenticate_admin_pwa_session
from app.admin_api.pwa_step_up import _enabled, consume_step_up_in_mutation, operation_digest
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.notification_template import NotificationTemplate
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.notification_template_service import (
    MOTIVATION_KEYS,TEMPLATE_META,CAPTION_MAX,TEXT_MAX,NotificationTemplateService,default_text,
)

logger=logging.getLogger(__name__)
_LANGS=('uz','ru','tj')


def _hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


class NoticeRead(StrictModel):
    key: Annotated[str,Field(max_length=40)] | None = None

    @field_validator('key')
    @classmethod
    def known_key(cls,value):
        if value is not None and value not in MOTIVATION_KEYS:
            raise ValueError('Unknown template')
        return value


class PrepareNotice(StrictModel):
    key: Annotated[str,Field(max_length=40)]
    enabled: bool
    text_uz: Annotated[str,Field(max_length=TEXT_MAX)]
    text_ru: Annotated[str,Field(max_length=TEXT_MAX)]
    text_tj: Annotated[str,Field(max_length=TEXT_MAX)]

    @field_validator('text_uz','text_ru','text_tj')
    @classmethod
    def clean_text(cls,value):
        value=value.strip();value.encode('utf-8')
        if any(ord(c)<32 and c not in '\n\r\t' for c in value):
            raise ValueError('Invalid template text')
        return value

    @model_validator(mode='after')
    def safe_placeholders(self):
        if self.key not in MOTIVATION_KEYS:
            raise ValueError('Unknown template')
        allowed={item[1:-1] for item in TEMPLATE_META[self.key]['placeholders']}
        for lang in _LANGS:
            for _,field,spec,conversion in Formatter().parse(getattr(self,'text_'+lang)):
                if field is not None and (field not in allowed or spec or conversion):
                    raise ValueError('Unknown or unsafe template placeholder')
        return self

    def effective(self):
        return {lang:getattr(self,'text_'+lang) or default_text(self.key,lang) for lang in _LANGS}


class NoticeCommand(PrepareNotice):
    expected_hash: Annotated[str,Field(pattern=r'^[0-9a-f]{64}$')]

    def operation(self):
        # The ceremony's existing 4096-byte limit stays unchanged. Hash both
        # canonical custom copy and effective fallback text, so no content or
        # default-version change can pass under a reviewed commitment.
        content={'custom':{lang:getattr(self,'text_'+lang) for lang in _LANGS},'effective':self.effective()}
        return {'action':'notifications.update','target':self.key,'payload':{
            'key':self.key,'enabled':self.enabled,'content_hash':_hash(content),'expected_hash':self.expected_hash}}


class ExecuteNotice(NoticeCommand):
    step_up_id: StepId


def _preview(key,row):
    custom={lang:(getattr(row,'text_'+lang) if row else '') or '' for lang in _LANGS}
    media=bool(row and row.media_type in ('photo','video') and row.media_path)
    return {'key':key,'enabled':bool(row.enabled) if row else True,'custom_texts':custom,
        'effective_texts':{lang:custom[lang].strip() or default_text(key,lang) for lang in _LANGS},
        'defaults':{lang:default_text(key,lang) for lang in _LANGS},
        'placeholders':TEMPLATE_META[key]['placeholders'],'has_media':media,'text_max':CAPTION_MAX if media else TEXT_MAX}


def _revision(row):
    return _hash(None if row is None else {'id':row.id,'key':row.key,'enabled':row.enabled,
        'texts':{lang:getattr(row,'text_'+lang) for lang in _LANGS},'media_type':row.media_type,
        'media_hash':hashlib.sha256((row.media_path or '').encode()).hexdigest(),
        'updated_at':_utc(row.updated_at).isoformat()})


async def _row(db,key,*,lock=False):
    if lock:
        await BotSettingRepository(db).lock_key('notification_template:'+key)
    statement=select(NotificationTemplate).where(NotificationTemplate.key==key).execution_options(populate_existing=True)
    return await db.scalar(statement.with_for_update() if lock else statement)


def _check_length(current,request):
    if any(len(value.encode('utf-16-le'))//2>current['text_max'] for value in request.effective().values()):
        raise CommandError('admin_pwa_notice_too_long',400)


async def _authenticate(db,cookie,settings_obj):
    actor=await authenticate_admin_pwa_session(db,cookie,settings_obj)
    if actor is None or actor.auth_method!='webauthn':
        raise CommandError('admin_pwa_unauthorized',401)
    return actor


async def read_notices(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):raise CommandError('not_found',404)
    async with read_transaction(db):
        await _authenticate(db,session_cookie,settings_obj)
        if request.key is not None:
            result={'template':_preview(request.key,await _row(db,request.key))}
        else:
            rows=(await db.execute(select(NotificationTemplate.key,NotificationTemplate.enabled)
                .where(NotificationTemplate.key.in_(MOTIVATION_KEYS)).limit(len(MOTIVATION_KEYS)))).all()
            stored={row.key:row for row in rows}
            result={'items':[{'key':key,'enabled':bool(stored[key].enabled) if key in stored else True}
                             for key in MOTIVATION_KEYS]}
    return result


async def prepare_notice(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):raise CommandError('not_found',404)
    async with read_transaction(db):
        await _authenticate(db,session_cookie,settings_obj)
        row=await _row(db,request.key);current=_preview(request.key,row);_check_length(current,request)
        command=NoticeCommand(**request.model_dump(),expected_hash=_revision(row))
    return {'operation':command.operation(),'execute_payload':command.model_dump(),'current':current,
            'proposed':{'key':command.key,'enabled':command.enabled,'effective_texts':command.effective()}}


async def execute_notice(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):raise CommandError('not_found',404)
    command=NoticeCommand.model_validate(request.model_dump(exclude={'step_up_id'}));operation=command.operation()
    async with db.begin():
        if db.get_bind().dialect.name=='postgresql':
            await db.execute(text("SET LOCAL lock_timeout = '5000'"));await db.execute(text("SET LOCAL statement_timeout = '8000'"))
        if not await consume_step_up_in_mutation(db,session_cookie=session_cookie,step_up_id=request.step_up_id,
                                                settings_obj=settings_obj,**operation):
            raise CommandError('admin_pwa_step_up_denied',403)
        step=await db.get(AdminPwaStepUp,request.step_up_id);session=await db.get(AdminPwaSession,step.session_id)
        actor=await db.get(User,step.user_id);row=await _row(db,command.key,lock=True)
        if (not _enabled(settings_obj) or not _authorized_admin(actor,settings_obj) or session.revoked_at is not None
                or min(_utc(step.expires_at),_utc(session.expires_at))<=datetime.now(timezone.utc)):
            raise CommandError('admin_pwa_step_up_denied',403)
        if _revision(row)!=command.expected_hash:raise CommandError('confirmation_changed',409)
        _check_length(_preview(command.key,row),command)
        row=await NotificationTemplateService(db).update_text(command.key,enabled=command.enabled,
            text_uz=command.text_uz,text_ru=command.text_ru,text_tj=command.text_tj,updated_by=actor.telegram_id)
        audit_id=str(uuid4());result=_preview(command.key,row)
        db.add(AdminPwaCommandAudit(id=audit_id,step_up_id=step.id,actor_user_id=actor.id,target_user_id=None,
            action=operation['action'],target=operation['target'],payload_hash=operation_digest(**operation),
            result_json=json.dumps({'key':command.key,'enabled':command.enabled,'before_hash':command.expected_hash,
                                   'after_hash':_revision(row)},sort_keys=True)))
        await db.flush()
    return {'command_id':audit_id,'template':result}


def create_admin_pwa_notifications_router(*,settings_obj,session_factory):
    router=APIRouter(tags=['admin-pwa-notifications'])
    async def handle(request,task,schema):
        failure=_guard_post(request,settings_obj)
        if failure is not None:return failure
        cookie=request.cookies.get(ADMIN_PWA_COOKIE_NAME,'')
        if not cookie:return _reply(401,'admin_pwa_unauthorized')
        try:parsed=schema.model_validate(await _body(request,64*1024))
        except ValidationError:return _reply(400,'admin_pwa_invalid_payload')
        try:
            async with session_factory() as db:
                result=await task(db,session_cookie=cookie,request=parsed,settings_obj=settings_obj)
        except CommandError as exc:return _reply(exc.status,str(exc))
        except Exception:
            logger.error('Admin PWA notification template command unavailable');return _reply(503,'admin_pwa_command_unavailable')
        return JSONResponse({'ok':True,**result},headers=_PRIVATE_HEADERS)
    @router.post('/api/admin/v1/notifications/read')
    async def read(request:Request):return await handle(request,read_notices,NoticeRead)
    @router.post('/api/admin/v1/notifications/prepare')
    async def prepare(request:Request):return await handle(request,prepare_notice,PrepareNotice)
    @router.post('/api/admin/v1/notifications/save')
    async def save(request:Request):return await handle(request,execute_notice,ExecuteNotice)
    return router

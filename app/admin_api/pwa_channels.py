"""Bounded required-channel management; no Telegram/network IO in commands."""
from datetime import datetime, timezone
import hashlib
import json
import logging
import re
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError, field_validator, model_validator
from sqlalchemy import func, select, text

from app.admin_api.pwa_access_grants import CommandError, StepId
from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_payment_review import PositiveId, StrictModel
from app.admin_api.pwa_read import read_transaction
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, _authorized_admin, authenticate_admin_pwa_session
from app.admin_api.pwa_step_up import _enabled, consume_step_up_in_mutation, operation_digest
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.bot_setting import BotSetting
from app.db.models.required_channel import RequiredChannel
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.required_channel_service import FORCE_CHANNEL_SETTING_KEY, RequiredChannelService

logger=logging.getLogger(__name__)


class ChannelRead(StrictModel):
    before_id: PositiveId | None = None


class ChannelMode(StrictModel):
    kind: Literal['mode']
    enabled: bool


class ChannelAdd(StrictModel):
    kind: Literal['add']
    chat_id: Annotated[str, Field(min_length=2,max_length=40)]
    title: Annotated[str, Field(min_length=1,max_length=180)]
    invite_link: Annotated[str, Field(max_length=300)] | None = None

    @field_validator('chat_id')
    @classmethod
    def canonical_chat(cls,value):
        value=value.strip().lower()
        if not (re.fullmatch(r'@[a-z0-9_]{1,32}',value)
                or re.fullmatch(r'-[1-9][0-9]{0,18}',value) and abs(int(value)) <= 9_223_372_036_854_775_807):
            raise ValueError('Explicit Telegram username or channel ID required')
        return value

    @field_validator('title')
    @classmethod
    def clean_title(cls,value):
        value=value.strip()
        if not value or any(ord(c)<32 or ord(c)==127 for c in value):
            raise ValueError('Invalid title')
        return value

    @field_validator('invite_link')
    @classmethod
    def telegram_invite(cls,value):
        if value is None or not value.strip():
            return None
        value=value.strip();parsed=urlsplit(value)
        if (parsed.scheme!='https' or parsed.hostname!='t.me' or parsed.username or parsed.password
                or parsed.port is not None or parsed.query or parsed.fragment
                or not re.fullmatch(r'/(?:\+[A-Za-z0-9_-]+|joinchat/[A-Za-z0-9_-]+|[A-Za-z0-9_]{1,32})/?',parsed.path)):
            raise ValueError('HTTPS Telegram invite required')
        return 'https://t.me'+parsed.path

    @model_validator(mode='after')
    def private_invite(self):
        if self.chat_id.startswith('-') and self.invite_link is None:
            raise ValueError('Private channel requires an invite')
        return self


class ChannelState(StrictModel):
    kind: Literal['state']
    channel_id: PositiveId
    is_active: bool


class ChannelDelete(StrictModel):
    kind: Literal['delete']
    channel_id: PositiveId


ChannelChange=Annotated[ChannelMode|ChannelAdd|ChannelState|ChannelDelete,Field(discriminator='kind')]


class PrepareChannel(StrictModel):
    change: ChannelChange


class ChannelCommand(PrepareChannel):
    expected_hash: Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]

    def operation(self):
        target=('mode' if self.change.kind=='mode' else
                'add-'+hashlib.sha256(self.change.chat_id.encode()).hexdigest()[:24] if self.change.kind=='add'
                else str(self.change.channel_id))
        return {'action':'channels.update','target':target,'payload':self.model_dump()}


class ExecuteChannel(ChannelCommand):
    step_up_id: StepId


def _hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _public(row):
    return {'id':row.id,'chat_id':row.chat_id,'title':row.title,'invite_link':row.invite_link,'is_active':row.is_active}


async def _target(db,change,*,lock=False):
    repo=BotSettingRepository(db)
    if change.kind=='mode':
        if lock:
            await repo.lock_key(FORCE_CHANNEL_SETTING_KEY)
        statement=select(BotSetting).where(BotSetting.key==FORCE_CHANNEL_SETTING_KEY).execution_options(populate_existing=True)
        row=await db.scalar(statement.with_for_update() if lock else statement)
        raw=None if row is None else {'value':row.value,'updated_at':_utc(row.updated_at).isoformat()}
        return None,{'enabled':await RequiredChannelService(db).is_enabled()},_hash(raw)
    if change.kind=='add':
        if lock:
            await repo.lock_key('required_channel:'+change.chat_id.casefold())
        statement=select(RequiredChannel).where(func.lower(RequiredChannel.chat_id)==change.chat_id).order_by(RequiredChannel.id).limit(2)
    else:
        statement=select(RequiredChannel).where(RequiredChannel.id==change.channel_id)
    statement=statement.execution_options(populate_existing=True)
    rows=(await db.scalars(statement.with_for_update() if lock else statement)).all()
    if len(rows)>1:
        raise CommandError('admin_pwa_channel_duplicate',409)
    row=rows[0] if rows else None
    if row is None and change.kind!='add':
        raise CommandError('admin_pwa_channel_missing',404)
    value=_public(row) if row else {'chat_id':change.chat_id,'exists':False}
    raw=None if row is None else {**_public(row),'created_at':_utc(row.created_at).isoformat()}
    return row,value,_hash(raw)


async def _authenticate(db,cookie,settings_obj):
    actor=await authenticate_admin_pwa_session(db,cookie,settings_obj)
    if actor is None or actor.auth_method!='webauthn':
        raise CommandError('admin_pwa_unauthorized',401)
    return actor


async def read_channels(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):
        raise CommandError('not_found',404)
    async with read_transaction(db):
        await _authenticate(db,session_cookie,settings_obj)
        enabled=await RequiredChannelService(db).is_enabled()
        query=select(RequiredChannel)
        if request.before_id is not None:
            query=query.where(RequiredChannel.id<request.before_id)
        rows=(await db.scalars(query.order_by(RequiredChannel.id.desc()).limit(31))).all()
        items=[_public(row) for row in rows[:30]]
    return {'enabled':enabled,'items':items,'next_before_id':items[-1]['id'] if len(rows)>30 else None}


async def prepare_channel(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):
        raise CommandError('not_found',404)
    async with read_transaction(db):
        await _authenticate(db,session_cookie,settings_obj)
        _,current,revision=await _target(db,request.change)
        command=ChannelCommand(change=request.change,expected_hash=revision)
    return {'operation':command.operation(),'current':current}


async def execute_channel(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):
        raise CommandError('not_found',404)
    command=ChannelCommand.model_validate(request.model_dump(exclude={'step_up_id'}));operation=command.operation()
    async with db.begin():
        if db.get_bind().dialect.name=='postgresql':
            await db.execute(text("SET LOCAL lock_timeout = '5000'"))
            await db.execute(text("SET LOCAL statement_timeout = '8000'"))
        if not await consume_step_up_in_mutation(db,session_cookie=session_cookie,step_up_id=request.step_up_id,
                                                settings_obj=settings_obj,**operation):
            raise CommandError('admin_pwa_step_up_denied',403)
        step=await db.get(AdminPwaStepUp,request.step_up_id);session=await db.get(AdminPwaSession,step.session_id)
        actor=await db.get(User,step.user_id)
        row,_,revision=await _target(db,command.change,lock=True)
        if (not _enabled(settings_obj) or not _authorized_admin(actor,settings_obj) or session.revoked_at is not None
                or min(_utc(step.expires_at),_utc(session.expires_at))<=datetime.now(timezone.utc)):
            raise CommandError('admin_pwa_step_up_denied',403)
        if revision!=command.expected_hash:
            raise CommandError('confirmation_changed',409)
        change=command.change;service=RequiredChannelService(db)
        if change.kind=='mode':
            await service.set_enabled(change.enabled);result={'enabled':await service.is_enabled()}
        elif change.kind=='add':
            saved=await service.add_channel(chat_id=row.chat_id if row else change.chat_id,title=change.title,
                invite_link=change.invite_link,created_by_telegram_id=actor.telegram_id)
            result=_public(saved)
        elif change.kind=='state':
            if not await service.set_channel_active(change.channel_id,change.is_active):
                raise CommandError('confirmation_changed',409)
            await db.refresh(row);result=_public(row)
        else:
            if not await service.delete_channel(change.channel_id):
                raise CommandError('confirmation_changed',409)
            result={'deleted_id':change.channel_id}
        audit_id=str(uuid4())
        db.add(AdminPwaCommandAudit(id=audit_id,step_up_id=step.id,actor_user_id=actor.id,target_user_id=None,
            action=operation['action'],target=operation['target'],payload_hash=operation_digest(**operation),
            result_json=json.dumps({'kind':change.kind,'before_hash':revision,'after_hash':_hash(result)},sort_keys=True)))
        await db.flush()
    return {'command_id':audit_id,'channel':result}


def create_admin_pwa_channels_router(*,settings_obj,session_factory):
    router=APIRouter(tags=['admin-pwa-channels'])
    async def handle(request,task,schema):
        failure=_guard_post(request,settings_obj)
        if failure is not None:
            return failure
        cookie=request.cookies.get(ADMIN_PWA_COOKIE_NAME,'')
        if not cookie:
            return _reply(401,'admin_pwa_unauthorized')
        try:
            parsed=schema.model_validate(await _body(request,4096))
        except ValidationError:
            return _reply(400,'admin_pwa_invalid_payload')
        try:
            async with session_factory() as db:
                result=await task(db,session_cookie=cookie,request=parsed,settings_obj=settings_obj)
        except CommandError as exc:
            return _reply(exc.status,str(exc))
        except Exception:
            logger.error('Admin PWA channel command unavailable')
            return _reply(503,'admin_pwa_command_unavailable')
        return JSONResponse({'ok':True,**result},headers=_PRIVATE_HEADERS)
    @router.post('/api/admin/v1/channels/read')
    async def read(request:Request):
        return await handle(request,read_channels,ChannelRead)
    @router.post('/api/admin/v1/channels/prepare')
    async def prepare(request:Request):
        return await handle(request,prepare_channel,PrepareChannel)
    @router.post('/api/admin/v1/channels/save')
    async def save(request:Request):
        return await handle(request,execute_channel,ExecuteChannel)
    return router

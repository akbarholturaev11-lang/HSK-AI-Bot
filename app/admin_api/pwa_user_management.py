"""Canonical account state/removal commands over existing shared business rules."""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError, model_validator
from sqlalchemy import select, text

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
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.blocked_user_guard import invalidate as invalidate_block_cache

logger = logging.getLogger(__name__)


class PrepareUserManagement(StrictModel):
    user_id: PositiveId
    operation: Literal['block', 'unblock', 'delete']
    confirm_user_id: PositiveId | None = None

    @model_validator(mode='after')
    def exact_confirmation(self):
        if self.operation == 'delete':
            if self.confirm_user_id != self.user_id:
                raise ValueError('Canonical account confirmation required')
        elif self.confirm_user_id is not None:
            raise ValueError('Unexpected deletion confirmation')
        return self


class UserManagementCommand(PrepareUserManagement):
    expected_hash: Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]

    def signed_operation(self):
        return {'action': 'users.delete' if self.operation == 'delete' else 'users.block',
                'target': str(self.user_id), 'payload': self.model_dump()}


class ExecuteUserManagement(UserManagementCommand):
    step_up_id: StepId


@dataclass(frozen=True)
class UnblockedNotice:
    user_id: int
    telegram_id: int
    language: str
    command_id: str


def _revision(user):
    fields = {key: getattr(user, key) for key in (
        'id','telegram_id','full_name','username','status','payment_status','selected_plan_type')}
    fields.update({key: _utc(value).isoformat() if (value := getattr(user,key)) else None
                   for key in ('created_at','start_date','end_date')})
    return hashlib.sha256(json.dumps(fields,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _preview(user):
    return {'user_id':user.id,'name':user.full_name,'username':user.username,'status':user.status,
            'telegram_linked':bool(user.telegram_id and user.telegram_id > 0),
            'end_date':_utc(user.end_date).isoformat() if user.end_date else None}


def _guard_target(user, actor_id, operation, settings_obj):
    if user is None:
        raise CommandError('admin_pwa_user_not_found',404)
    if user.id == actor_id or (user.telegram_id and user.telegram_id in getattr(settings_obj,'admin_id_list',[])):
        raise CommandError('admin_pwa_protected_account',403)
    blocked = str(user.status or '').strip().lower() == 'blocked'
    if (operation == 'block' and blocked) or (operation == 'unblock' and not blocked):
        raise CommandError('confirmation_changed',409)


async def prepare_user_management(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError('not_found',404)
    async with read_transaction(db):
        actor = await authenticate_admin_pwa_session(db,session_cookie,settings_obj)
        if actor is None or actor.auth_method != 'webauthn':
            raise CommandError('admin_pwa_unauthorized',401)
        user = await db.get(User,request.user_id)
        _guard_target(user,actor.user_id,request.operation,settings_obj)
        command = UserManagementCommand(**request.model_dump(),expected_hash=_revision(user))
        current = _preview(user)
    return {'operation':command.signed_operation(),'current':current}


async def execute_user_management(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError('not_found',404)
    command = UserManagementCommand.model_validate(request.model_dump(exclude={'step_up_id'}))
    operation = command.signed_operation()
    notice = None
    async with db.begin():
        if db.get_bind().dialect.name == 'postgresql':
            await db.execute(text("SET LOCAL lock_timeout = '5000'"))
            await db.execute(text("SET LOCAL statement_timeout = '8000'"))
        if not await consume_step_up_in_mutation(db,session_cookie=session_cookie,
                step_up_id=request.step_up_id,settings_obj=settings_obj,**operation):
            raise CommandError('admin_pwa_step_up_denied',403)
        step = await db.get(AdminPwaStepUp,request.step_up_id)
        session = await db.get(AdminPwaSession,step.session_id)
        actor = await db.get(User,step.user_id)
        user = await db.scalar(select(User).where(User.id==command.user_id)
            .with_for_update().execution_options(populate_existing=True))
        now = datetime.now(timezone.utc)
        if (not _enabled(settings_obj) or not _authorized_admin(actor,settings_obj)
                or session.revoked_at is not None
                or min(_utc(step.expires_at),_utc(session.expires_at)) <= now):
            raise CommandError('admin_pwa_step_up_denied',403)
        _guard_target(user,actor.id,command.operation,settings_obj)
        if _revision(user) != command.expected_hash:
            raise CommandError('confirmation_changed',409)
        telegram_id = int(user.telegram_id) if user.telegram_id and user.telegram_id > 0 else None
        audit_id = str(uuid4())
        if command.operation == 'delete':
            if not await UserRepository(db).delete_by_user_id(user.id):
                raise CommandError('confirmation_changed',409)
            result = {'user_id':command.user_id,'deleted':True}
        else:
            await UserRepository(db).set_blocked(user,command.operation=='block')
            result = {'user_id':user.id,'status':user.status,'blocked':user.status=='blocked'}
            if command.operation == 'unblock' and telegram_id:
                notice = UnblockedNotice(user.id,telegram_id,user.language or 'ru',audit_id)
        db.add(AdminPwaCommandAudit(id=audit_id,step_up_id=step.id,actor_user_id=actor.id,
            target_user_id=command.user_id,action=operation['action'],target=operation['target'],
            payload_hash=operation_digest(**operation),result_json=json.dumps({
                'operation':command.operation,'before_hash':command.expected_hash,'result':result},sort_keys=True)))
        await db.flush()
    if telegram_id:
        invalidate_block_cache(telegram_id)
    return {'command_id':audit_id,**result},notice


def create_admin_pwa_user_management_router(*, settings_obj, session_factory, emit_unblocked=None):
    router = APIRouter(tags=['admin-pwa-user-management'])

    async def handle(request, *, execute):
        failure = _guard_post(request,settings_obj)
        if failure is not None:
            return failure
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME,'')
        if not cookie:
            return _reply(401,'admin_pwa_unauthorized')
        try:
            parsed = (ExecuteUserManagement if execute else PrepareUserManagement).model_validate(await _body(request,2048))
        except ValidationError:
            return _reply(400,'admin_pwa_invalid_payload')
        try:
            async with session_factory() as db:
                if execute:
                    result,notice = await execute_user_management(db,session_cookie=cookie,request=parsed,settings_obj=settings_obj)
                else:
                    result = await prepare_user_management(db,session_cookie=cookie,request=parsed,settings_obj=settings_obj)
            if execute:
                delivery = 'not_requested' if parsed.operation != 'unblock' else 'not_linked'
                if notice is not None:
                    delivery = 'unavailable'
                    if emit_unblocked is not None:
                        try:
                            delivery = 'attempted' if await asyncio.wait_for(emit_unblocked(notice),10) is True else 'uncertain'
                        except Exception:
                            delivery = 'uncertain'
                result['notification_delivery'] = delivery
        except CommandError as exc:
            return _reply(exc.status,str(exc))
        except Exception:
            logger.error('Admin PWA account command unavailable')
            return _reply(503,'admin_pwa_command_unavailable')
        return JSONResponse({'ok':True,**result},headers=_PRIVATE_HEADERS)

    @router.post('/api/admin/v1/users/prepare-management')
    async def prepare(request: Request):
        return await handle(request,execute=False)

    @router.post('/api/admin/v1/users/manage')
    async def manage(request: Request):
        return await handle(request,execute=True)

    return router

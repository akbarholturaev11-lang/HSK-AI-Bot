"""Bounded partner applications and exact shared-service status decisions."""
from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError, model_validator
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
from app.db.models.partner import Partner
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.partner_service import PARTNER_SIGNUP_BONUS_USD_KEY, PartnerService

logger = logging.getLogger(__name__)
_STATES = {'approve': 'pending', 'reject': 'pending', 'block': 'active', 'unblock': 'blocked'}


class PartnerRead(StrictModel):
    before_id: PositiveId | None = None
    partner_id: PositiveId | None = None
    status: Literal['pending', 'active', 'blocked', 'rejected'] | None = None

    @model_validator(mode='after')
    def distinct_read(self):
        if self.partner_id is not None and (self.before_id is not None or self.status is not None):
            raise ValueError('Choose detail or page')
        return self


class PreparePartner(StrictModel):
    partner_id: PositiveId
    operation: Literal['approve', 'reject', 'block', 'unblock']


class PartnerCommand(PreparePartner):
    expected_hash: Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]

    def operation_payload(self):
        return {'action': 'partners.update', 'target': str(self.partner_id), 'payload': self.model_dump()}


class ExecutePartner(PartnerCommand):
    step_up_id: StepId


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(',', ':')).encode()).hexdigest()


def _public(row):
    return {'id': row.id, 'status': row.status, 'promotion_channel': row.promotion_channel[:2000],
            'audience_size': row.audience_size, 'contact_username': row.contact_username,
            'created_at': _utc(row.created_at).isoformat()}


async def _state(db, partner_id, *, lock=False):
    if lock:
        await BotSettingRepository(db).lock_key(PARTNER_SIGNUP_BONUS_USD_KEY)
    statement = select(Partner).where(Partner.id == partner_id).execution_options(populate_existing=True)
    row = await db.scalar(statement.with_for_update() if lock else statement)
    if row is None:
        raise CommandError('admin_pwa_partner_missing', 404)
    setting = await BotSettingRepository(db).get_record(PARTNER_SIGNUP_BONUS_USD_KEY)
    service = PartnerService(db)
    bonus = await service.get_signup_bonus_usd()
    if not bonus.is_finite() or bonus < 0 or bonus >= 10_000_000_000:
        raise CommandError('admin_pwa_partner_bonus_unavailable', 503)
    credit = await service.repo.get_signup_bonus(row.id)
    raw = {column.name: getattr(row, column.name) for column in Partner.__table__.columns}
    raw['bonus_setting'] = None if setting is None else (setting.value, setting.updated_at)
    raw['bonus_credit'] = None if credit is None else (credit.id, credit.amount_usd, credit.is_locked)
    projected = _public(row) | {'signup_bonus_usd': str(bonus if not row.signup_bonus_granted_at and credit is None else 0)}
    return row, projected, _hash(raw)


async def _authenticate(db, cookie, settings_obj):
    actor = await authenticate_admin_pwa_session(db, cookie, settings_obj)
    if actor is None or actor.auth_method != 'webauthn':
        raise CommandError('admin_pwa_unauthorized', 401)
    return actor


async def read_partners(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError('not_found', 404)
    async with read_transaction(db):
        await _authenticate(db, session_cookie, settings_obj)
        if request.partner_id is not None:
            _, partner, _ = await _state(db, request.partner_id)
            return {'partner': partner}
        query = select(Partner.id, Partner.status, func.substr(Partner.contact_username, 1, 128).label('contact'))
        if request.before_id is not None:
            query = query.where(Partner.id < request.before_id)
        if request.status is not None:
            query = query.where(Partner.status == request.status)
        rows = (await db.execute(query.order_by(Partner.id.desc()).limit(31))).all()
        items = [{'id': r.id, 'status': r.status, 'contact_username': r.contact} for r in rows[:30]]
    return {'items': items, 'next_before_id': items[-1]['id'] if len(rows) > 30 else None}


async def prepare_partner(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError('not_found', 404)
    async with read_transaction(db):
        await _authenticate(db, session_cookie, settings_obj)
        _, current, revision = await _state(db, request.partner_id)
        if current['status'] != _STATES[request.operation]:
            raise CommandError('confirmation_changed', 409)
        command = PartnerCommand(**request.model_dump(), expected_hash=revision)
    proposed = {'id': command.partner_id, 'operation': command.operation,
                'status': {'approve': 'active', 'reject': 'rejected', 'block': 'blocked', 'unblock': 'active'}[command.operation],
                'signup_bonus_usd': current['signup_bonus_usd'] if command.operation == 'approve' else '0'}
    return {'operation': command.operation_payload(), 'current': current, 'proposed': proposed}


async def execute_partner(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError('not_found', 404)
    command = PartnerCommand.model_validate(request.model_dump(exclude={'step_up_id'}))
    operation = command.operation_payload()
    async with db.begin():
        if db.get_bind().dialect.name == 'postgresql':
            await db.execute(text("SET LOCAL lock_timeout = '5000'"))
            await db.execute(text("SET LOCAL statement_timeout = '8000'"))
        if not await consume_step_up_in_mutation(db, session_cookie=session_cookie, step_up_id=request.step_up_id,
                                                settings_obj=settings_obj, **operation):
            raise CommandError('admin_pwa_step_up_denied', 403)
        step = await db.get(AdminPwaStepUp, request.step_up_id)
        session = await db.get(AdminPwaSession, step.session_id)
        actor = await db.get(User, step.user_id)
        row, before, revision = await _state(db, command.partner_id, lock=True)
        if (not _enabled(settings_obj) or not _authorized_admin(actor, settings_obj) or session.revoked_at is not None
                or min(_utc(step.expires_at), _utc(session.expires_at)) <= datetime.now(timezone.utc)):
            raise CommandError('admin_pwa_step_up_denied', 403)
        if revision != command.expected_hash or row.status != _STATES[command.operation]:
            raise CommandError('confirmation_changed', 409)
        service = PartnerService(db)
        if command.operation == 'approve':
            await service.approve(row, actor.telegram_id)
        elif command.operation == 'reject':
            await service.repo.set_status(row, 'rejected', actor.telegram_id)
        elif command.operation == 'block':
            await service.block(row, actor.telegram_id)
        else:
            await service.unblock(row, actor.telegram_id)
        audit_id = str(uuid4())
        db.add(AdminPwaCommandAudit(id=audit_id, step_up_id=step.id, actor_user_id=actor.id, target_user_id=None,
            action=operation['action'], target=operation['target'], payload_hash=operation_digest(**operation),
            result_json=json.dumps({'operation': command.operation, 'status': row.status, 'before_hash': revision,
                'signup_bonus_usd': before['signup_bonus_usd'] if command.operation == 'approve' else '0'})))
        await db.flush()
        result = _public(row)
    # This command changes account state. Outbound partner notifications require
    # their own durable delivery contract; no network runs under these locks.
    return {'command_id': audit_id, 'partner': result}


def create_admin_pwa_partners_router(*, settings_obj, session_factory):
    router = APIRouter(tags=['admin-pwa-partners'])
    async def handle(request, task, schema):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, '')
        if not cookie:
            return _reply(401, 'admin_pwa_unauthorized')
        try:
            parsed = schema.model_validate(await _body(request, 4096))
        except ValidationError:
            return _reply(400, 'admin_pwa_invalid_payload')
        try:
            async with session_factory() as db:
                result = await task(db, session_cookie=cookie, request=parsed, settings_obj=settings_obj)
        except CommandError as exc:
            return _reply(exc.status, str(exc))
        except Exception:
            logger.error('Admin PWA partner command unavailable')
            return _reply(503, 'admin_pwa_command_unavailable')
        return JSONResponse({'ok': True, **result}, headers=_PRIVATE_HEADERS)
    @router.post('/api/admin/v1/partners/read')
    async def read(request: Request):
        return await handle(request, read_partners, PartnerRead)
    @router.post('/api/admin/v1/partners/prepare')
    async def prepare(request: Request):
        return await handle(request, prepare_partner, PreparePartner)
    @router.post('/api/admin/v1/partners/save')
    async def save(request: Request):
        return await handle(request, execute_partner, ExecutePartner)
    return router

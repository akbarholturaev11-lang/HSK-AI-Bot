"""Manual ledger entries with exact amounts, existing conversion and one-use proof."""
from datetime import datetime, timezone
import hashlib
import json
import logging
import math
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError, field_validator
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
from app.db.models.portfolio import PortfolioTransaction
from app.db.models.user import User
from app.services.portfolio_service import PortfolioService

logger=logging.getLogger(__name__)


class PortfolioRead(StrictModel):
    before_id: PositiveId | None = None


class PreparePortfolio(StrictModel):
    transaction_type: Literal['profit','expense']
    amount_minor: Annotated[int,Field(strict=True,ge=1,le=100_000_000)]
    currency: Literal['USD','TJS','CNY']
    note: Annotated[str,Field(min_length=2,max_length=300)]

    @field_validator('note')
    @classmethod
    def clean_note(cls,value):
        value=value.strip();value.encode('utf-8')
        if len(value)<2 or any(ord(c)<32 and c not in '\n\r\t' for c in value):
            raise ValueError('Invalid ledger note')
        return value


class PortfolioCommand(PreparePortfolio):
    expected_usd: Annotated[str,Field(max_length=40,pattern=r'^[0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?$')]

    def operation(self):
        return {'action':'portfolio.add','target':'manual','payload':self.model_dump()}


class ExecutePortfolio(PortfolioCommand):
    step_up_id: StepId


def _usd(db,request):
    value=PortfolioService(db).amount_to_usd(request.amount_minor/100,request.currency)
    if value is None or not math.isfinite(value) or value<=0:
        raise CommandError('admin_pwa_conversion_unavailable',503)
    return format(value,'.17g')


async def _authenticate(db,cookie,settings_obj):
    actor=await authenticate_admin_pwa_session(db,cookie,settings_obj)
    if actor is None or actor.auth_method!='webauthn':
        raise CommandError('admin_pwa_unauthorized',401)
    return actor


async def read_portfolio(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):
        raise CommandError('not_found',404)
    async with read_transaction(db):
        await _authenticate(db,session_cookie,settings_obj)
        # Existing summary/history helpers synchronize all approved payments.
        # This bounded manual-only projection deliberately performs no sync.
        query=select(PortfolioTransaction.id,PortfolioTransaction.transaction_type,
            PortfolioTransaction.original_amount,PortfolioTransaction.original_currency,
            PortfolioTransaction.amount_usd,func.substr(PortfolioTransaction.note,1,301).label('note_preview'),
            PortfolioTransaction.created_at).where(
                PortfolioTransaction.source.in_(PortfolioService.MANUAL_SOURCES))
        if request.before_id is not None:
            query=query.where(PortfolioTransaction.id<request.before_id)
        rows=(await db.execute(query.order_by(PortfolioTransaction.id.desc()).limit(31))).all()
        items=[{'id':r.id,'transaction_type':r.transaction_type,
                'amount':str(r.original_amount) if r.original_amount is not None and math.isfinite(r.original_amount) else None,
                'currency':r.original_currency,'amount_usd':format(r.amount_usd,'.17g') if math.isfinite(r.amount_usd) else None,
                'note':(r.note_preview or '')[:300],'note_truncated':len(r.note_preview or '')>300,
                'created_at':_utc(r.created_at).isoformat()} for r in rows[:30]]
    return {'items':items,'next_before_id':items[-1]['id'] if len(rows)>30 else None,
            'conversion_basis':'PortfolioService.amount_to_usd_internal_rates'}


async def prepare_portfolio(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):
        raise CommandError('not_found',404)
    async with read_transaction(db):
        await _authenticate(db,session_cookie,settings_obj)
        command=PortfolioCommand(**request.model_dump(),expected_usd=_usd(db,request))
    return {'operation':command.operation(),'current':{'new_entry':True}}


async def execute_portfolio(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):
        raise CommandError('not_found',404)
    command=PortfolioCommand.model_validate(request.model_dump(exclude={'step_up_id'}));operation=command.operation()
    async with db.begin():
        if db.get_bind().dialect.name=='postgresql':
            await db.execute(text("SET LOCAL lock_timeout = '5000'"))
            await db.execute(text("SET LOCAL statement_timeout = '8000'"))
        if not await consume_step_up_in_mutation(db,session_cookie=session_cookie,step_up_id=request.step_up_id,
                                                settings_obj=settings_obj,**operation):
            raise CommandError('admin_pwa_step_up_denied',403)
        step=await db.get(AdminPwaStepUp,request.step_up_id);session=await db.get(AdminPwaSession,step.session_id)
        actor=await db.get(User,step.user_id)
        if (not _enabled(settings_obj) or not _authorized_admin(actor,settings_obj) or session.revoked_at is not None
                or min(_utc(step.expires_at),_utc(session.expires_at))<=datetime.now(timezone.utc)):
            raise CommandError('admin_pwa_step_up_denied',403)
        if _usd(db,command)!=command.expected_usd:
            raise CommandError('confirmation_changed',409)
        row=await PortfolioService(db).add_manual_transaction(transaction_type=command.transaction_type,
            admin_telegram_id=actor.telegram_id,amount=command.amount_minor/100,currency=command.currency,note=command.note)
        if row is None or format(row.amount_usd,'.17g')!=command.expected_usd:
            raise CommandError('confirmation_changed',409)
        result={'id':row.id,'transaction_type':command.transaction_type,'amount_minor':command.amount_minor,
                'currency':command.currency,'amount_usd':command.expected_usd,'note':command.note}
        audit_id=str(uuid4())
        db.add(AdminPwaCommandAudit(id=audit_id,step_up_id=step.id,actor_user_id=actor.id,target_user_id=None,
            action=operation['action'],target=operation['target'],payload_hash=operation_digest(**operation),
            result_json=json.dumps({**{k:v for k,v in result.items() if k!='note'},
                'note_hash':hashlib.sha256(command.note.encode()).hexdigest()},sort_keys=True)))
        await db.flush()
    return {'command_id':audit_id,'transaction':result}


def create_admin_pwa_portfolio_router(*,settings_obj,session_factory):
    router=APIRouter(tags=['admin-pwa-portfolio'])
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
            logger.error('Admin PWA ledger command unavailable')
            return _reply(503,'admin_pwa_command_unavailable')
        return JSONResponse({'ok':True,**result},headers=_PRIVATE_HEADERS)
    @router.post('/api/admin/v1/portfolio/read')
    async def read(request:Request):
        return await handle(request,read_portfolio,PortfolioRead)
    @router.post('/api/admin/v1/portfolio/prepare')
    async def prepare(request:Request):
        return await handle(request,prepare_portfolio,PreparePortfolio)
    @router.post('/api/admin/v1/portfolio/save')
    async def save(request:Request):
        return await handle(request,execute_portfolio,ExecutePortfolio)
    return router

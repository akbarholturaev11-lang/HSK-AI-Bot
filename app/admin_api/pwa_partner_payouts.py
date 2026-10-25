"""Partner payout reservation, deadline and rejection through shared CAS owners."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError, field_validator, model_validator
from sqlalchemy import select, text

from app.admin_api.pwa_access_grants import CommandError, StepId
from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_partners import _authenticate
from app.admin_api.pwa_payment_review import PositiveId, StrictModel
from app.admin_api.pwa_read import read_transaction
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, _authorized_admin
from app.admin_api.pwa_step_up import _enabled, consume_step_up_in_mutation, operation_digest
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.partner import PartnerPayout
from app.db.models.user import User
from app.repositories.partner_repo import PAYOUT_EDITABLE_STATUSES, PartnerRepository

logger = logging.getLogger(__name__)


class PayoutRead(StrictModel):
    before_id: PositiveId | None = None
    payout_id: PositiveId | None = None
    status: Literal['pending', 'deadline_set', 'processing', 'paid', 'rejected'] | None = None

    @model_validator(mode='after')
    def distinct_read(self):
        if self.payout_id is not None and (self.before_id is not None or self.status is not None):
            raise ValueError('Choose detail or page')
        return self


class PreparePayout(StrictModel):
    payout_id: PositiveId
    operation: Literal['deadline', 'reject', 'claim', 'release']
    days: Annotated[int, Field(strict=True)] | None = None

    @field_validator('days')
    @classmethod
    def allowed_days(cls,value):
        if value is not None and value not in (1,3,7):raise ValueError('Unsupported deadline')
        return value

    @model_validator(mode='after')
    def deadline_days(self):
        if (self.operation == 'deadline') != (self.days is not None):
            raise ValueError('Days apply only to a deadline')
        return self


class PayoutCommand(PreparePayout):
    expected_hash: Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]
    deadline_at: Annotated[str, Field(max_length=40)] | None = None

    @model_validator(mode='after')
    def exact_deadline(self):
        if self.operation != 'deadline':
            if self.deadline_at is not None:
                raise ValueError('Unexpected deadline')
        else:
            value = datetime.fromisoformat(self.deadline_at or '')
            if value.tzinfo is None or value.utcoffset() != timedelta(0):
                raise ValueError('Explicit UTC deadline required')
        return self

    def operation_payload(self):
        return {'action':'partners.payout', 'target':str(self.payout_id), 'payload':self.model_dump()}


class ExecutePayout(PayoutCommand):
    step_up_id: StepId


def _public(row, actor):
    result = {key:getattr(row,key) for key in ('id','partner_id','status','payment_method','bank_name','local_currency')}
    result.update(amount_usd=str(row.amount_usd), local_amount=str(row.local_amount),
        exchange_rate=str(row.exchange_rate), account_details=row.account_details[:2000],
        holder_name=row.holder_name, note=(row.note or '')[:500],
        deadline_at=_utc(row.deadline_at).isoformat() if row.deadline_at else None,
        has_qr=bool(row.recipient_qr_code_file_id), has_proof=bool(row.proof_screenshot_file_id),
        owned_reservation=bool(row.status=='processing' and row.processing_by_telegram_id==actor.telegram_id))
    operations = ['deadline','reject','claim'] if row.status in PAYOUT_EDITABLE_STATUSES else (
        ['release'] if result['owned_reservation'] else [])
    result['operations']=operations
    return result


async def _target(db,payout_id,*,lock=False):
    query=select(PartnerPayout).where(PartnerPayout.id==payout_id).execution_options(populate_existing=True)
    row=await db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise CommandError('admin_pwa_payout_missing',404)
    raw={column.name:getattr(row,column.name) for column in PartnerPayout.__table__.columns}
    revision=hashlib.sha256(json.dumps(raw,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()
    return row,revision


async def read_payouts(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):raise CommandError('not_found',404)
    async with read_transaction(db):
        actor=await _authenticate(db,session_cookie,settings_obj)
        if request.payout_id is not None:
            row,revision=await _target(db,request.payout_id)
            return {'payout':_public(row,actor)|{'revision_hash':revision}}
        query=select(PartnerPayout.id,PartnerPayout.partner_id,PartnerPayout.status,
            PartnerPayout.amount_usd,PartnerPayout.local_amount,PartnerPayout.local_currency)
        if request.before_id is not None:query=query.where(PartnerPayout.id<request.before_id)
        if request.status is not None:query=query.where(PartnerPayout.status==request.status)
        rows=(await db.execute(query.order_by(PartnerPayout.id.desc()).limit(31))).all()
        items=[dict(id=r.id,partner_id=r.partner_id,status=r.status,amount_usd=str(r.amount_usd),
                    local_amount=str(r.local_amount),local_currency=r.local_currency) for r in rows[:30]]
    return {'items':items,'next_before_id':items[-1]['id'] if len(rows)>30 else None}


async def prepare_payout(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):raise CommandError('not_found',404)
    async with read_transaction(db):
        actor=await _authenticate(db,session_cookie,settings_obj)
        row,revision=await _target(db,request.payout_id);current=_public(row,actor)
        if request.operation not in current['operations']:raise CommandError('confirmation_changed',409)
        deadline=(datetime.now(timezone.utc)+timedelta(days=request.days)).isoformat() if request.days else None
        command=PayoutCommand(**request.model_dump(),expected_hash=revision,deadline_at=deadline)
    proposed={**current,'status':{'deadline':'deadline_set','reject':'rejected','claim':'processing',
        'release':'deadline_set' if row.deadline_at else 'pending'}[command.operation],
        'operation':command.operation,'deadline_at':deadline if command.operation=='deadline' else current['deadline_at']}
    return {'operation':command.operation_payload(),'current':current,'proposed':proposed}


async def execute_payout(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):raise CommandError('not_found',404)
    command=PayoutCommand.model_validate(request.model_dump(exclude={'step_up_id'}));operation=command.operation_payload()
    async with db.begin():
        if db.get_bind().dialect.name=='postgresql':
            await db.execute(text("SET LOCAL lock_timeout = '5000'"));await db.execute(text("SET LOCAL statement_timeout = '8000'"))
        if not await consume_step_up_in_mutation(db,session_cookie=session_cookie,step_up_id=request.step_up_id,
                                                settings_obj=settings_obj,**operation):
            raise CommandError('admin_pwa_step_up_denied',403)
        step=await db.get(AdminPwaStepUp,request.step_up_id);session=await db.get(AdminPwaSession,step.session_id)
        actor=await db.get(User,step.user_id);row,revision=await _target(db,command.payout_id,lock=True)
        now=datetime.now(timezone.utc)
        if (not _enabled(settings_obj) or not _authorized_admin(actor,settings_obj) or session.revoked_at is not None
                or min(_utc(step.expires_at),_utc(session.expires_at))<=now):
            raise CommandError('admin_pwa_step_up_denied',403)
        if revision!=command.expected_hash or command.operation not in _public(row,actor)['operations']:
            raise CommandError('confirmation_changed',409)
        repo=PartnerRepository(db)
        if command.operation=='deadline':
            deadline=datetime.fromisoformat(command.deadline_at)
            # The prepared date is signed, never silently shifted at save time.
            if not timedelta(days=command.days)-timedelta(minutes=5)<=deadline-now<=timedelta(days=command.days,seconds=5):
                raise CommandError('confirmation_changed',409)
            changed=await repo.set_payout_deadline(row.id,deadline,actor.telegram_id)
        elif command.operation=='reject':changed=await repo.reject_payout(row.id,actor.telegram_id)
        elif command.operation=='claim':changed=await repo.claim_payout_for_payment(row.id,actor.telegram_id)
        else:changed=await repo.release_payout_payment(row.id,actor.telegram_id)
        if not changed:raise CommandError('confirmation_changed',409)
        row,_=await _target(db,row.id);result=_public(row,actor);audit_id=str(uuid4())
        db.add(AdminPwaCommandAudit(id=audit_id,step_up_id=step.id,actor_user_id=actor.id,target_user_id=None,
            action=operation['action'],target=operation['target'],payload_hash=operation_digest(**operation),
            result_json=json.dumps({'operation':command.operation,'before_hash':revision,'status':row.status,
                'deadline_at':result['deadline_at'],'amount_usd':str(row.amount_usd),'local_amount':str(row.local_amount),
                'local_currency':row.local_currency},sort_keys=True)))
        await db.flush()
    return {'command_id':audit_id,'payout':result}


def create_admin_pwa_partner_payouts_router(*,settings_obj,session_factory):
    router=APIRouter(tags=['admin-pwa-partner-payouts'])
    async def handle(request,task,schema):
        failure=_guard_post(request,settings_obj)
        if failure is not None:return failure
        cookie=request.cookies.get(ADMIN_PWA_COOKIE_NAME,'')
        if not cookie:return _reply(401,'admin_pwa_unauthorized')
        try:parsed=schema.model_validate(await _body(request,4096))
        except ValidationError:return _reply(400,'admin_pwa_invalid_payload')
        try:
            async with session_factory() as db:
                result=await task(db,session_cookie=cookie,request=parsed,settings_obj=settings_obj)
        except CommandError as exc:return _reply(exc.status,str(exc))
        except Exception:
            logger.error('Admin PWA payout command unavailable');return _reply(503,'admin_pwa_command_unavailable')
        return JSONResponse({'ok':True,**result},headers=_PRIVATE_HEADERS)
    @router.post('/api/admin/v1/partner-payouts/read')
    async def read(request:Request):return await handle(request,read_payouts,PayoutRead)
    @router.post('/api/admin/v1/partner-payouts/prepare')
    async def prepare(request:Request):return await handle(request,prepare_payout,PreparePayout)
    @router.post('/api/admin/v1/partner-payouts/save')
    async def save(request:Request):return await handle(request,execute_payout,ExecutePayout)
    return router

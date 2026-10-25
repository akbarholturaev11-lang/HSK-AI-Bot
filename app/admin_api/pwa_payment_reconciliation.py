"""Human reconciliation evidence; never resend or rewrite financial decisions."""
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
from app.admin_api.pwa_payment_review import StrictModel
from app.admin_api.pwa_read import read_transaction
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, _authorized_admin
from app.admin_api.pwa_step_up import _enabled, consume_step_up_in_mutation, operation_digest
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_payment_review import AdminPwaPaymentOutbox, AdminPwaPaymentReview
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.user import User

logger=logging.getLogger(__name__)
ACTION='payments.delivery_reconcile'


class ReconciliationRead(StrictModel):
    review_id: StepId | None = None
    before_id: StepId | None = None

    @model_validator(mode='after')
    def distinct_read(self):
        if self.review_id and self.before_id:raise ValueError('Choose detail or page')
        return self


class PrepareReconciliation(StrictModel):
    review_id: StepId
    resolution: Literal['observed', 'no_retry']
    reason: Annotated[str,Field(min_length=5,max_length=300)]

    @field_validator('reason')
    @classmethod
    def clean_reason(cls,value):
        value=value.strip();value.encode('utf-8')
        if len(value)<5 or any(ord(c)<32 for c in value):raise ValueError('Invalid reconciliation reason')
        return value


class ReconciliationCommand(PrepareReconciliation):
    expected_hash: Annotated[str,Field(pattern=r'^[0-9a-f]{64}$')]

    def operation(self):
        return {'action':ACTION,'target':self.review_id,'payload':self.model_dump()}


class ExecuteReconciliation(ReconciliationCommand):
    step_up_id: StepId


def _eligible(outbox):
    return outbox.reconciled_at is None and (outbox.status=='uncertain' or (outbox.status=='attempting'
        and outbox.attempted_at is not None and _utc(outbox.attempted_at)<=datetime.now(timezone.utc)-timedelta(minutes=10)))


def _public(review,outbox):
    return {'review_id':review.id,'payment_id':review.payment_id,'decision':review.decision,
        'delivery_status':outbox.status,'created_at':_utc(review.created_at).isoformat(),
        'attempted_at':_utc(outbox.attempted_at).isoformat() if outbox.attempted_at else None,
        'finished_at':_utc(outbox.finished_at).isoformat() if outbox.finished_at else None,
        'reconciled_at':_utc(outbox.reconciled_at).isoformat() if outbox.reconciled_at else None,
        'eligible':_eligible(outbox)}


async def _snapshot(db,review_id,*,lock=False):
    query=select(AdminPwaPaymentReview,AdminPwaPaymentOutbox).join(
        AdminPwaPaymentOutbox,AdminPwaPaymentReview.id==AdminPwaPaymentOutbox.review_id).where(
        AdminPwaPaymentReview.id==review_id).execution_options(populate_existing=True)
    result=(await db.execute(query.with_for_update(of=AdminPwaPaymentOutbox) if lock else query)).one_or_none()
    if result is None:raise CommandError('admin_pwa_delivery_missing',404)
    review,outbox=result
    raw={'review_id':review.id,'payment_id':review.payment_id,'decision':review.decision,
        'payload_hash':review.payload_hash,'status':outbox.status,'attempted_at':outbox.attempted_at,
        'finished_at':outbox.finished_at,'reconciled_at':outbox.reconciled_at,
        'effects_hash':hashlib.sha256(outbox.effects_json.encode()).hexdigest()}
    revision=hashlib.sha256(json.dumps(raw,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()
    prior=await db.scalar(select(AdminPwaCommandAudit.result_json).where(
        AdminPwaCommandAudit.action==ACTION,AdminPwaCommandAudit.target==review_id).limit(1))
    return review,outbox,revision,json.loads(prior)['resolution'] if prior else None


async def read_reconciliation(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):raise CommandError('not_found',404)
    async with read_transaction(db):
        await _authenticate(db,session_cookie,settings_obj)
        if request.review_id:
            review,outbox,_,resolution=await _snapshot(db,request.review_id)
            return {'delivery':_public(review,outbox)|{'resolution':resolution}}
        # Both outbox status and action/target audit lookup are indexed. This
        # queue reads no effects JSON, review payload, destination or identity.
        query=select(AdminPwaPaymentOutbox.review_id,AdminPwaPaymentOutbox.status,
            AdminPwaPaymentOutbox.attempted_at,AdminPwaPaymentReview.payment_id,
            AdminPwaPaymentReview.decision,AdminPwaPaymentReview.created_at).join(
            AdminPwaPaymentReview,AdminPwaPaymentReview.id==AdminPwaPaymentOutbox.review_id).where(
            AdminPwaPaymentOutbox.reconciled_at.is_(None))
        if request.before_id:query=query.where(AdminPwaPaymentOutbox.review_id<request.before_id)
        rows=[]
        # Two exact-status index pages (at most 62 rows) avoid sorting/scanning
        # all unresolved deliveries just to render one mixed-status page.
        for status in ('attempting','uncertain'):
            rows.extend((await db.execute(query.where(AdminPwaPaymentOutbox.status==status)
                .order_by(AdminPwaPaymentOutbox.review_id.desc()).limit(31))).all())
        rows.sort(key=lambda row:row.review_id,reverse=True)
        items=[{'review_id':r.review_id,'payment_id':r.payment_id,'decision':r.decision,'delivery_status':r.status,
                'created_at':_utc(r.created_at).isoformat()} for r in rows[:30]]
    return {'items':items,'next_before_id':items[-1]['review_id'] if len(rows)>30 else None}


async def prepare_reconciliation(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):raise CommandError('not_found',404)
    async with read_transaction(db):
        await _authenticate(db,session_cookie,settings_obj)
        review,outbox,revision,prior=await _snapshot(db,request.review_id)
        if prior or not _eligible(outbox):raise CommandError('confirmation_changed',409)
        command=ReconciliationCommand(**request.model_dump(),expected_hash=revision)
        current=_public(review,outbox)
    return {'operation':command.operation(),'current':current,
            'proposed':current|{'resolution':command.resolution,'reason':command.reason}}


async def execute_reconciliation(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):raise CommandError('not_found',404)
    command=ReconciliationCommand.model_validate(request.model_dump(exclude={'step_up_id'}));operation=command.operation()
    async with db.begin():
        if db.get_bind().dialect.name=='postgresql':
            await db.execute(text("SET LOCAL lock_timeout = '5000'"));await db.execute(text("SET LOCAL statement_timeout = '8000'"))
        if not await consume_step_up_in_mutation(db,session_cookie=session_cookie,step_up_id=request.step_up_id,
                                                settings_obj=settings_obj,**operation):
            raise CommandError('admin_pwa_step_up_denied',403)
        step=await db.get(AdminPwaStepUp,request.step_up_id);session=await db.get(AdminPwaSession,step.session_id)
        actor=await db.get(User,step.user_id);review,outbox,revision,prior=await _snapshot(db,command.review_id,lock=True)
        if (not _enabled(settings_obj) or not _authorized_admin(actor,settings_obj) or session.revoked_at is not None
                or min(_utc(step.expires_at),_utc(session.expires_at))<=datetime.now(timezone.utc)):
            raise CommandError('admin_pwa_step_up_denied',403)
        if prior or revision!=command.expected_hash or not _eligible(outbox):raise CommandError('confirmation_changed',409)
        audit_id=str(uuid4())
        outbox.reconciled_at=datetime.now(timezone.utc)
        db.add(AdminPwaCommandAudit(id=audit_id,step_up_id=step.id,actor_user_id=actor.id,target_user_id=None,
            action=ACTION,target=review.id,payload_hash=operation_digest(**operation),result_json=json.dumps({
                'resolution':command.resolution,'before_hash':revision,
                'reason_hash':hashlib.sha256(command.reason.encode()).hexdigest()},sort_keys=True)))
        await db.flush();result=_public(review,outbox)|{'resolution':command.resolution}
    return {'command_id':audit_id,'delivery':result}


def create_admin_pwa_payment_reconciliation_router(*,settings_obj,session_factory):
    router=APIRouter(tags=['admin-pwa-payment-reconciliation'])
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
            logger.error('Admin PWA reconciliation unavailable');return _reply(503,'admin_pwa_command_unavailable')
        return JSONResponse({'ok':True,**result},headers=_PRIVATE_HEADERS)
    @router.post('/api/admin/v1/payment-deliveries/read')
    async def read(request:Request):return await handle(request,read_reconciliation,ReconciliationRead)
    @router.post('/api/admin/v1/payment-deliveries/prepare')
    async def prepare(request:Request):return await handle(request,prepare_reconciliation,PrepareReconciliation)
    @router.post('/api/admin/v1/payment-deliveries/save')
    async def save(request:Request):return await handle(request,execute_reconciliation,ExecuteReconciliation)
    return router

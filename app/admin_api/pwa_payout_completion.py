"""Owned raster proof upload and exact signed completion; no money transfer."""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse, Response
from pydantic import Field, ValidationError
from sqlalchemy import delete, select, text
from sqlalchemy.orm import load_only

from app.admin_api.pwa_access_grants import CommandError, StepId
from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _gate, _reply
from app.admin_api.pwa_inbox_attachments import _image_type
from app.admin_api.pwa_outbound import _deliverable, _hash, enqueue_reviewed_message, recipient_hash
from app.admin_api.pwa_partner_payouts import _public, _target
from app.admin_api.pwa_partners import _authenticate
from app.admin_api.pwa_payment_review import PositiveId, StrictModel
from app.admin_api.pwa_read import read_transaction
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, _authorized_admin
from app.admin_api.pwa_step_up import _enabled, _locked_session, consume_step_up_in_mutation, operation_digest
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.bot.utils.i18n import t
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_payout_proof import AdminPwaPayoutProof as Proof
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.partner import Partner
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.repositories.partner_repo import PartnerRepository

logger = logging.getLogger(__name__)
MAX_BYTES = 2 * 1024 * 1024


class PrepareCompletion(StrictModel):
    payout_id: PositiveId
    proof_id: StepId


class CompletionCommand(PrepareCompletion):
    expected_hash: Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]
    proof_hash: Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]
    notice_hash: Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]

    def operation_payload(self):
        return {'action':'partners.payout', 'target':str(self.payout_id),
                'payload':self.model_dump() | {'operation':'complete'}}


class ExecuteCompletion(CompletionCommand):
    step_up_id: StepId


@dataclass(frozen=True)
class UploadProof:
    actor_telegram_id: int
    raw: bytes
    media_type: str


def _authority(user, session, settings_obj, now, step=None):
    if (not _enabled(settings_obj) or not _authorized_admin(user,settings_obj)
            or session.revoked_at is not None or _utc(session.expires_at)<=now
            or step is not None and _utc(step.expires_at)<=now):
        raise CommandError('admin_pwa_step_up_denied',403)


def _reserved(row, actor):
    if row.status!='processing' or row.processing_by_telegram_id!=actor.telegram_id:
        raise CommandError('confirmation_changed',409)


async def _bound_waits(db):
    if db.get_bind().dialect.name=='postgresql':
        await db.execute(text("SET LOCAL lock_timeout = '5000'"))
        await db.execute(text("SET LOCAL statement_timeout = '8000'"))


async def _owned_proof(db, proof_id, payout_id, actor_id, session_id, *, lock=False, used=False):
    query=select(Proof).where(Proof.id==proof_id,Proof.payout_id==payout_id,
        Proof.actor_user_id==actor_id,Proof.session_id==session_id)
    row=await db.scalar(query.execution_options(populate_existing=True).with_for_update() if lock else query)
    if (row is None or row.status not in (('ready','used') if used else ('ready',))
            or not row.provider_file_id or _utc(row.expires_at)<=datetime.now(timezone.utc)):
        raise CommandError('admin_pwa_proof_unavailable',409)
    return row


def _proof_revision(row):
    return _hash([row.id,row.content_hash,row.byte_count,row.provider_file_id])


async def reserve_upload(db, *, session_cookie, payout_id, content_hash, byte_count, settings_obj):
    async with db.begin():
        await _bound_waits(db)
        pair=await _locked_session(db,session_cookie,settings_obj,datetime.now(timezone.utc))
        if pair is None:raise CommandError('admin_pwa_unauthorized',401)
        session,user=pair
        await BotSettingRepository(db).lock_key('pwa_payout_upload:'+str(user.id))
        row,_=await _target(db,payout_id,lock=True);_reserved(row,user)
        now=datetime.now(timezone.utc);_authority(user,session,settings_obj,now)
        recent=(await db.scalars(select(Proof.id).where(Proof.actor_user_id==user.id,
            Proof.created_at>now-timedelta(hours=1)).limit(20))).all()
        if len(recent)>=20:raise CommandError('admin_pwa_proof_rate_limited',429)
        proof=Proof(id=str(uuid4()),actor_user_id=user.id,session_id=session.id,payout_id=payout_id,
            content_hash=content_hash,byte_count=byte_count,status='uploading',created_at=now,
            expires_at=now+timedelta(minutes=15))
        db.add(proof);await db.flush()
        return proof.id,user.telegram_id


async def finish_upload(db, *, session_cookie, proof_id, file_id, settings_obj):
    async with db.begin():
        await _bound_waits(db)
        pair=await _locked_session(db,session_cookie,settings_obj,datetime.now(timezone.utc))
        if pair is None:raise CommandError('admin_pwa_unauthorized',401)
        session,user=pair
        proof=await db.scalar(select(Proof).where(Proof.id==proof_id,Proof.actor_user_id==user.id,
            Proof.session_id==session.id).with_for_update())
        if proof is None or proof.status!='uploading':raise CommandError('confirmation_changed',409)
        _authority(user,session,settings_obj,datetime.now(timezone.utc))
        if _utc(proof.expires_at)<=datetime.now(timezone.utc):raise CommandError('admin_pwa_proof_unavailable',409)
        if not isinstance(file_id,str) or not 1<=len(file_id)<=512 or any(c.isspace() for c in file_id):
            proof.status='failed';return None
        proof.provider_file_id=file_id;proof.status='ready'
        return {'proof_id':proof.id,'content_hash':proof.content_hash,'byte_count':proof.byte_count,
                'expires_at':_utc(proof.expires_at).isoformat()}


async def _notice(db, row, settings_obj, *, lock=False):
    # Partner ownership is canonicalized through the real optional TG identity;
    # absence/unreachability never blocks recording an already made payment.
    partner_query=select(Partner).where(Partner.id==row.partner_id).execution_options(populate_existing=True)
    partner=await db.scalar(partner_query.with_for_update() if lock else partner_query)
    query=select(User).where(User.telegram_id==partner.user_telegram_id).options(load_only(User.id,User.telegram_id,
        User.status,User.language,User.full_name,User.username,User.bot_blocked_at,User.bot_unblocked_at)) if partner else None
    user=await db.scalar(query.with_for_update() if lock else query) if query is not None else None
    texts={lang:t('partner_payout_paid_notification',lang,amount=f'${row.amount_usd:.2f}') for lang in ('uz','ru','tj')}
    snapshot=None
    if _deliverable(user,settings_obj):
        snapshot={'user_id':user.id,'snapshot_hash':recipient_hash(user),
                  'language':user.language if user.language in ('uz','ru','tj') else 'tj'}
    return texts,snapshot,_hash({'recipient':snapshot,'texts':texts})


async def prepare_completion(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):raise CommandError('not_found',404)
    async with read_transaction(db):
        actor=await _authenticate(db,session_cookie,settings_obj)
        session=await db.scalar(select(AdminPwaSession).where(
            AdminPwaSession.token_hash==hashlib.sha256(session_cookie.encode()).hexdigest()))
        row,revision=await _target(db,request.payout_id);_reserved(row,actor)
        proof=await _owned_proof(db,request.proof_id,row.id,actor.user_id,session.id)
        texts,recipient,notice_hash=await _notice(db,row,settings_obj)
        command=CompletionCommand(**request.model_dump(),expected_hash=revision,
            proof_hash=_proof_revision(proof),notice_hash=notice_hash)
        current=_public(row,actor)
    return {'operation':command.operation_payload(),'execute_payload':command.model_dump(),
        'current':current,'proposed':current|{'status':'paid','previous_status':current['status'],
        'proof_id':proof.id,'proof_hash':proof.content_hash,'notice_count':int(recipient is not None),
        'notice_user_id':recipient['user_id'] if recipient else None,'notice_texts':texts}}


async def execute_completion(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):raise CommandError('not_found',404)
    command=CompletionCommand.model_validate(request.model_dump(exclude={'step_up_id'}))
    operation=command.operation_payload()
    async with db.begin():
        if db.get_bind().dialect.name=='postgresql':
            await db.execute(text("SET LOCAL lock_timeout = '5000'"));await db.execute(text("SET LOCAL statement_timeout = '8000'"))
        if not await consume_step_up_in_mutation(db,session_cookie=session_cookie,step_up_id=request.step_up_id,
                                                settings_obj=settings_obj,**operation):
            raise CommandError('admin_pwa_step_up_denied',403)
        step=await db.get(AdminPwaStepUp,request.step_up_id);session=await db.get(AdminPwaSession,step.session_id)
        actor=await db.get(User,step.user_id);row,revision=await _target(db,command.payout_id,lock=True)
        _reserved(row,actor)
        proof=await _owned_proof(db,command.proof_id,row.id,actor.id,session.id,lock=True)
        texts,recipient,notice_hash=await _notice(db,row,settings_obj,lock=True)
        _authority(actor,session,settings_obj,datetime.now(timezone.utc),step)
        if (revision!=command.expected_hash or _proof_revision(proof)!=command.proof_hash
                or notice_hash!=command.notice_hash or _utc(proof.expires_at)<=datetime.now(timezone.utc)):
            raise CommandError('confirmation_changed',409)
        if not await PartnerRepository(db).mark_payout_paid(row.id,proof.provider_file_id,actor.telegram_id):
            raise CommandError('confirmation_changed',409)
        proof.status='used';audit_id=str(uuid4())
        db.add(AdminPwaCommandAudit(id=audit_id,step_up_id=step.id,actor_user_id=actor.id,
            target_user_id=recipient['user_id'] if recipient else None,action=operation['action'],
            target=operation['target'],payload_hash=operation_digest(**operation),result_json=json.dumps({
                'operation':'complete','before_hash':revision,'proof_hash':proof.content_hash,
                'status':'paid','notice_count':int(recipient is not None),'notice_hash':notice_hash})))
        await db.flush()
        if recipient:
            await enqueue_reviewed_message(db,command_id=audit_id,actor_user_id=actor.id,session_id=session.id,
                target_user_id=recipient['user_id'],kind='direct',texts=texts,filters={},snapshots=[recipient],
                digest=_hash([recipient]),photo_file_id=proof.provider_file_id)
        row,_=await _target(db,row.id)
        result=_public(row,actor)
    return {'command_id':audit_id,'payout':result,'job_id':audit_id if recipient else None}


async def purge_expired_proofs(db, *, limit=100, now=None):
    if type(limit) is not int or not 1<=limit<=1000:raise ValueError('Invalid bounded proof expiry page')
    keys=(await db.scalars(select(Proof.id).where(Proof.expires_at<=(now or datetime.now(timezone.utc)))
        .order_by(Proof.expires_at,Proof.id).limit(limit).with_for_update(skip_locked=True))).all()
    if keys:await db.execute(delete(Proof).where(Proof.id.in_(keys)))
    return len(keys)


def create_admin_pwa_payout_completion_router(*, settings_obj, session_factory, upload=None, loader=None, drainer=None):
    router=APIRouter(tags=['admin-pwa-payout-completion'])
    slots=asyncio.Semaphore(2)

    @router.post('/api/admin/v1/partner-payouts/{payout_id}/proof')
    async def upload_proof(request:Request,payout_id:str):
        failure=_gate(request,settings_obj)
        if failure is not None:return failure
        if request.headers.getlist('origin')!=[settings_obj.ADMIN_PWA_PUBLIC_ORIGIN] or request.headers.get('sec-fetch-site','same-origin')!='same-origin':
            return _reply(403,'admin_pwa_csrf')
        if request.headers.get('content-type','').split(';',1)[0] not in ('image/jpeg','image/png','image/webp'):
            return _reply(415,'unsupported_media_type')
        cookie=request.cookies.get(ADMIN_PWA_COOKIE_NAME,'')
        if not cookie:return _reply(401,'admin_pwa_unauthorized')
        if len(payout_id)>10 or not payout_id.isascii() or not payout_id.isdecimal() or not 0<int(payout_id)<=2147483647 or request.query_params:
            return _reply(400,'admin_pwa_invalid_payload')
        if upload is None:return _reply(503,'admin_pwa_proof_unavailable')
        try:
            async with slots:
                async with session_factory() as db:
                    async with read_transaction(db):await _authenticate(db,cookie,settings_obj)
                raw=bytearray()
                async for chunk in request.stream():
                    if len(raw)+len(chunk)>MAX_BYTES:return _reply(400,'admin_pwa_proof_invalid')
                    raw.extend(chunk)
                raw=bytes(raw);media=await asyncio.to_thread(_image_type,raw,MAX_BYTES)
                if media is None:return _reply(400,'admin_pwa_proof_invalid')
                async with session_factory() as db:
                    proof_id,admin=await reserve_upload(db,session_cookie=cookie,payout_id=int(payout_id),
                        content_hash=hashlib.sha256(raw).hexdigest(),byte_count=len(raw),settings_obj=settings_obj)
                file_id=None
                try:file_id=await asyncio.wait_for(upload(UploadProof(admin,raw,media)),8)
                except Exception:logger.warning('Admin PWA proof upload unavailable')
                async with session_factory() as db:
                    result=await finish_upload(db,session_cookie=cookie,proof_id=proof_id,file_id=file_id,settings_obj=settings_obj)
                if result is None:return _reply(503,'admin_pwa_proof_unavailable')
        except CommandError as exc:return _reply(exc.status,str(exc))
        except Exception:
            logger.error('Admin PWA proof upload unavailable');return _reply(503,'admin_pwa_proof_unavailable')
        return JSONResponse({'ok':True,**result},headers=_PRIVATE_HEADERS)

    @router.get('/api/admin/v1/payout-proofs/{proof_id}')
    async def preview(request:Request,proof_id:str):
        failure=_gate(request,settings_obj)
        if failure is not None:return failure
        if request.headers.get('sec-fetch-site','same-origin')!='same-origin' or (
            request.headers.get('origin') and request.headers['origin']!=settings_obj.ADMIN_PWA_PUBLIC_ORIGIN):
            return _reply(403,'admin_pwa_csrf')
        try:
            parsed=PrepareCompletion.model_validate({'payout_id':1,'proof_id':proof_id})
            if request.query_params:raise ValueError()
        except (ValueError,ValidationError):return _reply(400,'admin_pwa_invalid_payload')
        cookie=request.cookies.get(ADMIN_PWA_COOKIE_NAME,'')
        if not cookie:return _reply(401,'admin_pwa_unauthorized')
        async def reference():
            async with session_factory() as db:
                async with read_transaction(db):
                    actor=await _authenticate(db,cookie,settings_obj)
                    session=await db.scalar(select(AdminPwaSession.id).where(
                        AdminPwaSession.token_hash==hashlib.sha256(cookie.encode()).hexdigest()))
                    row=await db.scalar(select(Proof).where(Proof.id==parsed.proof_id))
                    if row is None:raise CommandError('admin_pwa_proof_unavailable',404)
                    row=await _owned_proof(db,row.id,row.payout_id,actor.user_id,session,used=True)
                    return row.provider_file_id,_proof_revision(row)
        try:
            file_id,revision=await reference()
            if loader is None:return _reply(503,'admin_pwa_proof_unavailable')
            async with slots:raw=await asyncio.wait_for(loader(file_id),10)
            media=await asyncio.to_thread(_image_type,raw,MAX_BYTES)
            if media is None:return _reply(404,'admin_pwa_proof_unavailable')
            if (await reference())!=(file_id,revision):return _reply(409,'confirmation_changed')
            return Response(raw,media_type=media,headers={**_PRIVATE_HEADERS,'Content-Disposition':'inline'})
        except CommandError as exc:return _reply(exc.status,str(exc))
        except Exception:return _reply(503,'admin_pwa_proof_unavailable')

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
            logger.error('Admin PWA payout completion unavailable');return _reply(503,'admin_pwa_command_unavailable')
        return result

    @router.post('/api/admin/v1/partner-payouts/prepare-completion')
    async def prepare(request:Request):
        result=await handle(request,prepare_completion,PrepareCompletion)
        return result if isinstance(result,JSONResponse) else JSONResponse({'ok':True,**result},headers=_PRIVATE_HEADERS)

    @router.post('/api/admin/v1/partner-payouts/complete')
    async def complete(request:Request,background:BackgroundTasks):
        result=await handle(request,execute_completion,ExecuteCompletion)
        if isinstance(result,JSONResponse):return result
        if result['job_id'] and drainer:background.add_task(drainer,result['job_id'])
        return JSONResponse({'ok':True,**result},headers=_PRIVATE_HEADERS)
    return router

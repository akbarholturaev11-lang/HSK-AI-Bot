"""Reviewed bounded audiences, one stored body, and at-most-once provider attempts."""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
from typing import Annotated, Literal
from types import SimpleNamespace
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError, field_validator, model_validator
from sqlalchemy import delete, func, insert, select, text, update
from sqlalchemy.orm import load_only

from app.admin_api.pwa_access_grants import CommandError, StepId
from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_partners import _authenticate
from app.admin_api.pwa_payment_review import PositiveId, StrictModel
from app.admin_api.pwa_read import read_transaction
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, _authorized_admin
from app.admin_api.pwa_step_up import _enabled, _locked_session, consume_step_up_in_mutation, operation_digest
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_outbound import (AdminPwaOutboundJob as Job,AdminPwaOutboundRecipient as Recipient,
    AdminPwaOutboundEvent)
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.bot_block_status_service import BotBlockStatusService

logger=logging.getLogger(__name__)
LANGS=('uz','ru','tj')
MAX_AUDIENCE=1000


def _hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


class MessageTexts(StrictModel):
    uz: Annotated[str,Field(min_length=2,max_length=3500)]
    ru: Annotated[str,Field(min_length=2,max_length=3500)]
    tj: Annotated[str,Field(min_length=2,max_length=3500)]

    @field_validator('uz','ru','tj')
    @classmethod
    def valid_copy(cls,value):
        value=value.strip();value.encode('utf-8')
        if len(value)<2 or len(value.encode('utf-16-le'))//2>3500 or any(ord(c)<32 and c not in '\n\r\t' for c in value):
            raise ValueError('Invalid bounded message copy')
        return value


class MessageFilters(StrictModel):
    languages: Annotated[list[Literal['uz','ru','tj']],Field(max_length=3)]=Field(default_factory=list)
    status: Literal['free','trial','active','expired']|None=None
    track: Literal['hsk20','hsk30']|None=None
    level: Literal['beginner','hsk1','hsk2','hsk3','hsk4','nhsk1','nhsk2','nhsk3']|None=None
    mode: Literal['qa','course']|None=None
    payment_status: Literal['none','pending','approved','rejected']|None=None
    payment_method: Literal['visa','alipay','wechat']|None=None
    plan: Literal['10_days','1_month','3_months']|None=None
    discount: Literal['eligible','used','none']|None=None
    course_promo: Literal['sent','not_sent']|None=None
    activity: Literal['active_7d','inactive_7d','new_7d']|None=None

    @field_validator('languages')
    @classmethod
    def unique_languages(cls,value):
        if len(value)!=len(set(value)):raise ValueError('Duplicate language')
        return sorted(value)


class PrepareMessage(StrictModel):
    kind: Literal['direct','broadcast','test']
    user_id: PositiveId|None=None
    texts: MessageTexts
    filters: MessageFilters=Field(default_factory=MessageFilters)

    @model_validator(mode='after')
    def exact_scope(self):
        if (self.kind=='direct')!=(self.user_id is not None):raise ValueError('Direct message requires canonical target')
        if self.kind!='broadcast' and self.filters!=MessageFilters():raise ValueError('Filters apply only to broadcast')
        return self


class MessageCommand(PrepareMessage):
    audience_hash: Annotated[str,Field(pattern=r'^[0-9a-f]{64}$')]
    audience_count: Annotated[int,Field(strict=True,ge=1,le=MAX_AUDIENCE)]

    def operation(self):
        scope=self.model_dump(exclude={'texts'})
        return {'action':'broadcast.send','target':'direct-'+str(self.user_id) if self.kind=='direct' else self.kind,
                'payload':scope|{'content_hash':_hash(self.texts.model_dump())}}


class ExecuteMessage(MessageCommand):
    step_up_id: StepId


class MessageRead(StrictModel):
    job_id: StepId|None=None
    before_id: StepId|None=None

    @model_validator(mode='after')
    def distinct_read(self):
        if self.job_id and self.before_id:raise ValueError('Choose job or page')
        return self


class RunMessage(StrictModel):
    job_id: StepId


class PrepareMessageControl(RunMessage):
    operation: Literal['resume','close']


class MessageControlCommand(PrepareMessageControl):
    expected_hash: Annotated[str,Field(pattern=r'^[0-9a-f]{64}$')]

    def operation_payload(self):
        return {'action':'broadcast.control','target':self.job_id,'payload':self.model_dump()}


class ExecuteMessageControl(MessageControlCommand):
    step_up_id: StepId


def recipient_hash(user):
    return _hash([user.id,user.telegram_id,user.status,user.language,user.full_name,user.username,
        _utc(user.bot_blocked_at).isoformat() if user.bot_blocked_at else None,
        _utc(user.bot_unblocked_at).isoformat() if user.bot_unblocked_at else None])


def _deliverable(user,settings_obj,*,test=False):
    return bool(user and user.telegram_id and user.telegram_id>0 and user.status!='blocked'
        and not BotBlockStatusService.is_bot_blocked(user)
        and (test or user.telegram_id not in settings_obj.admin_id_list))


async def _audience(db,request,actor,settings_obj,*,lock=False):
    if request.kind=='broadcast':
        names={'track':'course_track','mode':'learning_mode','plan':'selected_plan_type',
               'discount':'discount_filter','course_promo':'course_promo_filter','activity':'activity_filter'}
        args={names.get(key,key):value for key,value in request.filters.model_dump().items()}
        users=await UserRepository(db).get_filtered_users(**args,delivery_admin_ids=settings_obj.admin_id_list,
            limit=MAX_AUDIENCE+1,for_update=lock)
    else:
        target=actor.user_id if request.kind=='test' else request.user_id
        query=select(User).where(User.id==target).options(load_only(User.id,User.telegram_id,User.status,
            User.language,User.full_name,User.username,User.bot_blocked_at,User.bot_unblocked_at))
        query=query.execution_options(populate_existing=True)
        user=await db.scalar(query.with_for_update() if lock else query)
        users=[user] if _deliverable(user,settings_obj,test=request.kind=='test') else []
    if not users:raise CommandError('admin_pwa_message_no_targets',409)
    if len(users)>MAX_AUDIENCE:raise CommandError('admin_pwa_message_too_many_targets',400)
    snapshots=[{'user_id':user.id,'snapshot_hash':recipient_hash(user),
        'language':user.language if user.language in LANGS else 'tj'} for user in users]
    return snapshots,_hash(snapshots)


async def prepare_message(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):raise CommandError('not_found',404)
    async with read_transaction(db):
        actor=await _authenticate(db,session_cookie,settings_obj)
        snapshots,digest=await _audience(db,request,actor,settings_obj)
        command=MessageCommand(**request.model_dump(),audience_hash=digest,audience_count=len(snapshots))
    return {'operation':command.operation(),'execute_payload':command.model_dump(),
        'current':{'new_job':True},'proposed':{'kind':command.kind,'user_id':command.user_id,
            'audience_count':len(snapshots),'texts':command.texts.model_dump(),'filters':command.filters.model_dump()}}


async def _owned_job(db,job_id,actor,*,lock=False):
    query=select(Job).where(Job.id==job_id,Job.actor_user_id==actor.user_id,
        Job.expires_at>datetime.now(timezone.utc)).execution_options(populate_existing=True)
    job=await db.scalar(query.with_for_update() if lock else query)
    if job is None:raise CommandError('admin_pwa_message_missing',404)
    return job


async def _job_view(db,job):
    counts=dict((await db.execute(select(Recipient.status,func.count()).where(Recipient.job_id==job.id)
        .group_by(Recipient.status))).all())
    retained=sum(counts.values())
    if retained>job.audience_count:raise CommandError('admin_pwa_message_state_unavailable',503)
    counts['removed']=job.audience_count-retained
    body=json.loads(job.body_json)
    stale=bool(job.status=='running' and job.started_at is not None
        and _utc(job.started_at)<=datetime.now(timezone.utc)-timedelta(minutes=2))
    return {'job_id':job.id,'kind':job.kind,'user_id':job.target_user_id,'status':job.status,
        'audience_count':job.audience_count,'counts':counts,'expires_at':_utc(job.expires_at).isoformat(),
        'can_control':job.status=='ready' or stale or bool(job.status=='complete' and counts.get('uncertain')),
        'stale':stale,'can_stop':job.status in ('ready','running'),
        'texts':body['texts'],'filters':body['filters']}


async def read_messages(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):raise CommandError('not_found',404)
    async with read_transaction(db):
        actor=await _authenticate(db,session_cookie,settings_obj)
        if request.job_id:
            job=await _owned_job(db,request.job_id,actor);result=await _job_view(db,job)
            stored=await db.scalar(select(AdminPwaSession.token_hash).where(AdminPwaSession.id==job.session_id))
            result['session_current']=stored==hashlib.sha256(session_cookie.encode()).hexdigest()
            return {'job':result}
        query=select(Job.id,Job.kind,Job.status,Job.audience_count).where(Job.actor_user_id==actor.user_id,
            Job.expires_at>datetime.now(timezone.utc))
        if request.before_id:query=query.where(Job.id<request.before_id)
        rows=(await db.execute(query.order_by(Job.id.desc()).limit(31))).all()
        items=[{'job_id':r.id,'kind':r.kind,'status':r.status,'audience_count':r.audience_count} for r in rows[:30]]
    return {'items':items,'next_before_id':items[-1]['job_id'] if len(rows)>30 else None}


async def execute_message(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):raise CommandError('not_found',404)
    command=MessageCommand.model_validate(request.model_dump(exclude={'step_up_id'}));operation=command.operation()
    async with db.begin():
        if db.get_bind().dialect.name=='postgresql':
            await db.execute(text("SET LOCAL lock_timeout = '5000'"));await db.execute(text("SET LOCAL statement_timeout = '8000'"))
        if not await consume_step_up_in_mutation(db,session_cookie=session_cookie,step_up_id=request.step_up_id,
                                                settings_obj=settings_obj,**operation):
            raise CommandError('admin_pwa_step_up_denied',403)
        step=await db.get(AdminPwaStepUp,request.step_up_id);session=await db.get(AdminPwaSession,step.session_id)
        from app.admin_api.pwa_sessions import AdminPwaActor
        user=await db.get(User,step.user_id);actor=AdminPwaActor(user.id,user.telegram_id,'webauthn')
        snapshots,digest=await _audience(db,command,actor,settings_obj,lock=True)
        if (not _enabled(settings_obj) or not _authorized_admin(user,settings_obj) or session.revoked_at is not None
                or min(_utc(step.expires_at),_utc(session.expires_at))<=datetime.now(timezone.utc)):
            raise CommandError('admin_pwa_step_up_denied',403)
        if digest!=command.audience_hash or len(snapshots)!=command.audience_count:
            raise CommandError('confirmation_changed',409)
        job_id=str(uuid4());now=datetime.now(timezone.utc)
        db.add(AdminPwaCommandAudit(id=job_id,step_up_id=step.id,actor_user_id=user.id,target_user_id=command.user_id,
            action=operation['action'],target=operation['target'],payload_hash=operation_digest(**operation),
            result_json=json.dumps({'kind':command.kind,'audience_count':len(snapshots),'audience_hash':digest,
                                   'content_hash':operation['payload']['content_hash']})))
        await db.flush()
        job=await enqueue_reviewed_message(db,command_id=job_id,actor_user_id=user.id,session_id=session.id,
            target_user_id=command.user_id,kind=command.kind,texts=command.texts.model_dump(),
            filters=command.filters.model_dump(),snapshots=snapshots,digest=digest,now=now)
        result=await _job_view(db,job);result['session_current']=True
    return {'command_id':job_id,'job':result}


async def enqueue_reviewed_message(db,*,command_id,actor_user_id,session_id,target_user_id,kind,
                                   texts,filters,snapshots,digest,photo_file_id=None,now=None):
    """Internal only: caller atomically owns exact proof and command audit.

    A provider reference is accepted only from another server-validated
    command (currently owned payout proof), never from a browser payload.
    """
    if not 1<=len(snapshots)<=MAX_AUDIENCE:raise ValueError('Invalid reviewed audience')
    now=now or datetime.now(timezone.utc)
    body={'kind':kind,'user_id':target_user_id,'texts':texts,'filters':filters}
    if photo_file_id:body['photo_file_id']=photo_file_id
    job=Job(id=command_id,actor_user_id=actor_user_id,session_id=session_id,target_user_id=target_user_id,
        kind=kind,status='ready',body_json=json.dumps(body,ensure_ascii=False),audience_hash=digest,
        audience_count=len(snapshots),created_at=now,expires_at=now+timedelta(hours=1))
    db.add(job);await db.flush()
    await db.execute(insert(Recipient),[snapshot|{'job_id':command_id,'status':'pending'} for snapshot in snapshots])
    return job


@dataclass(frozen=True)
class OutboundMessage:
    user_id:int
    telegram_id:int
    language:str
    text:str
    photo_file_id:str|None=None


async def dispatch_message_batch(*,job_id,session_factory,settings_obj,emit,limit=10):
    """No database connection spans IO; attempting is never automatically retried."""
    if not _enabled(settings_obj) or emit is None:return False
    async with session_factory() as db:
        async with db.begin():
            job=await db.scalar(select(Job).where(Job.id==job_id).with_for_update())
            if job is None or job.status!='ready' or _utc(job.expires_at)<=datetime.now(timezone.utc):return False
            run_token=str(uuid4());job.status='running';job.run_token=run_token;job.started_at=datetime.now(timezone.utc)
            body=json.loads(job.body_json);copies=body['texts'];photo_file_id=body.get('photo_file_id')
    for _ in range(min(max(limit,1),10)):
        async with session_factory() as db:
            async with db.begin():
                state=(await db.execute(select(Job.status.label('job_status'),Job.run_token,Job.kind,Job.expires_at,
                    Job.actor_user_id,User.status.label('actor_status'),User.telegram_id.label('actor_telegram_id'),
                    AdminPwaSession.user_id.label('session_user_id'),AdminPwaSession.revoked_at,
                    AdminPwaSession.expires_at.label('session_expires'),AdminPwaSession.auth_method)
                    .join(User,User.id==Job.actor_user_id).join(AdminPwaSession,AdminPwaSession.id==Job.session_id)
                    .where(Job.id==job_id).with_for_update(of=Job))).one_or_none()
                if state is None or state.job_status!='running' or state.run_token!=run_token:return False
                now=datetime.now(timezone.utc)
                if (not _enabled(settings_obj) or not _authorized_admin(SimpleNamespace(
                        status=state.actor_status,telegram_id=state.actor_telegram_id),settings_obj)
                        or state.session_user_id!=state.actor_user_id or state.auth_method!='webauthn'
                        or state.revoked_at is not None or min(_utc(state.session_expires),_utc(state.expires_at))<=now):
                    await db.execute(update(Job).where(Job.id==job_id,Job.run_token==run_token).values(status='ready',run_token=None))
                    return False
                selected=(await db.execute(select(Recipient,User).join(User,User.id==Recipient.user_id).where(
                    Recipient.job_id==job_id,Recipient.status=='pending').order_by(Recipient.user_id).limit(1)
                    .options(load_only(User.id,User.telegram_id,User.status,User.language,User.full_name,
                        User.username,User.bot_blocked_at,User.bot_unblocked_at))
                    .with_for_update(of=Recipient,skip_locked=True))).one_or_none()
                if selected is None:break
                recipient,user=selected
                if (not _deliverable(user,settings_obj,test=state.kind=='test')
                        or recipient_hash(user)!=recipient.snapshot_hash):
                    recipient.status='skipped';recipient.finished_at=now;continue
                recipient.status='attempting';recipient.attempted_at=now
                message=OutboundMessage(user.id,user.telegram_id,recipient.language,copies[recipient.language],photo_file_id)
        status='uncertain'
        try:
            await asyncio.wait_for(emit(message),timeout=5)
            status='attempted'
        except Exception:
            logger.warning('Admin PWA outbound attempt requires operator review')
        async with session_factory() as db:
            async with db.begin():
                await db.execute(update(Recipient).where(Recipient.job_id==job_id,Recipient.user_id==message.user_id,
                    Recipient.status=='attempting').values(status=status,finished_at=datetime.now(timezone.utc)))
        await asyncio.sleep(.1)
    async with session_factory() as db:
        async with db.begin():
            pending=await db.scalar(select(Recipient.user_id).where(Recipient.job_id==job_id,Recipient.status=='pending').limit(1))
            await db.execute(update(Job).where(Job.id==job_id,Job.status=='running',Job.run_token==run_token)
                .values(status='ready' if pending else 'complete',run_token=None))
    return True


async def authorize_message_run(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):raise CommandError('not_found',404)
    async with read_transaction(db):
        actor=await _authenticate(db,session_cookie,settings_obj);job=await _owned_job(db,request.job_id,actor)
        session_hash=await db.scalar(select(AdminPwaSession.token_hash).where(AdminPwaSession.id==job.session_id))
        if session_hash!=hashlib.sha256(session_cookie.encode()).hexdigest():
            raise CommandError('admin_pwa_message_new_session',409)
        if job.status!='ready':raise CommandError('confirmation_changed',409)
    return {'job_id':job.id,'accepted':True}


async def stop_message(db,*,session_cookie,request,settings_obj):
    """Cancellation only reduces an existing grant; ordinary live cookie + audit.

    No new recipient, text or retry is authorized. One already claimed attempt
    may finish; the next claim observes the stopped/fenced job under its lock.
    """
    if not _enabled(settings_obj):raise CommandError('not_found',404)
    async with db.begin():
        if db.get_bind().dialect.name=='postgresql':
            await db.execute(text("SET LOCAL lock_timeout = '5000'"));await db.execute(text("SET LOCAL statement_timeout = '8000'"))
        pair=await _locked_session(db,session_cookie,settings_obj,datetime.now(timezone.utc))
        if pair is None:raise CommandError('admin_pwa_unauthorized',401)
        from app.admin_api.pwa_sessions import AdminPwaActor
        session,user=pair;actor=AdminPwaActor(user.id,user.telegram_id,'webauthn')
        job=await _owned_job(db,request.job_id,actor,lock=True)
        if (not _enabled(settings_obj) or not _authorized_admin(user,settings_obj) or session.revoked_at is not None
                or _utc(session.expires_at)<=datetime.now(timezone.utc)):
            raise CommandError('admin_pwa_unauthorized',401)
        if job.status in ('ready','running'):
            job.status='closed';job.run_token=None
            await db.execute(update(Recipient).where(Recipient.job_id==job.id,Recipient.status=='pending')
                .values(status='skipped',finished_at=datetime.now(timezone.utc)))
            db.add(AdminPwaOutboundEvent(id=str(uuid4()),job_id=job.id,actor_user_id=actor.user_id,
                operation='stop',created_at=datetime.now(timezone.utc)))
            await db.flush()
        result=await _job_view(db,job)
    return {'job':result}


async def _control_state(db,job):
    pending=(await db.execute(select(Recipient.user_id,Recipient.snapshot_hash).where(
        Recipient.job_id==job.id,Recipient.status=='pending').order_by(Recipient.user_id))).all()
    state=await _job_view(db,job)
    revision=_hash({'status':job.status,'run_token':job.run_token,'session_id':job.session_id,
        'body_hash':hashlib.sha256(job.body_json.encode()).hexdigest(),'counts':state['counts'],
        'pending':[(r.user_id,r.snapshot_hash) for r in pending]})
    return state,revision


async def prepare_message_control(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):raise CommandError('not_found',404)
    async with read_transaction(db):
        actor=await _authenticate(db,session_cookie,settings_obj);job=await _owned_job(db,request.job_id,actor)
        current,revision=await _control_state(db,job)
        if not current['can_control'] or not (current['counts'].get('pending',0) or request.operation=='close'
                and (current['counts'].get('attempting',0) or current['counts'].get('uncertain',0))):
            raise CommandError('confirmation_changed',409)
        command=MessageControlCommand(**request.model_dump(),expected_hash=revision)
    return {'operation':command.operation_payload(),'current':current,
        'proposed':current|{'operation':command.operation,'status':'ready' if command.operation=='resume' else 'closed','stale':False}}


async def execute_message_control(db,*,session_cookie,request,settings_obj):
    if not _enabled(settings_obj):raise CommandError('not_found',404)
    command=MessageControlCommand.model_validate(request.model_dump(exclude={'step_up_id'}));operation=command.operation_payload()
    async with db.begin():
        if db.get_bind().dialect.name=='postgresql':
            await db.execute(text("SET LOCAL lock_timeout = '5000'"));await db.execute(text("SET LOCAL statement_timeout = '8000'"))
        if not await consume_step_up_in_mutation(db,session_cookie=session_cookie,step_up_id=request.step_up_id,
                                                settings_obj=settings_obj,**operation):
            raise CommandError('admin_pwa_step_up_denied',403)
        step=await db.get(AdminPwaStepUp,request.step_up_id);session=await db.get(AdminPwaSession,step.session_id)
        from app.admin_api.pwa_sessions import AdminPwaActor
        user=await db.get(User,step.user_id);actor=AdminPwaActor(user.id,user.telegram_id,'webauthn')
        job=await _owned_job(db,command.job_id,actor,lock=True);current,revision=await _control_state(db,job)
        if (not _enabled(settings_obj) or not _authorized_admin(user,settings_obj) or session.revoked_at is not None
                or min(_utc(step.expires_at),_utc(session.expires_at))<=datetime.now(timezone.utc)):
            raise CommandError('admin_pwa_step_up_denied',403)
        if revision!=command.expected_hash or not current['can_control'] or not (current['counts'].get('pending',0)
                or command.operation=='close' and (current['counts'].get('attempting',0) or current['counts'].get('uncertain',0))):
            raise CommandError('confirmation_changed',409)
        job.session_id=session.id;job.run_token=None;job.status='ready' if command.operation=='resume' else 'closed'
        if command.operation=='close':
            await db.execute(update(Recipient).where(Recipient.job_id==job.id,Recipient.status=='pending')
                .values(status='skipped',finished_at=datetime.now(timezone.utc)))
            await db.execute(update(Recipient).where(Recipient.job_id==job.id,Recipient.status=='attempting')
                .values(status='uncertain',finished_at=datetime.now(timezone.utc)))
        audit_id=str(uuid4())
        db.add(AdminPwaCommandAudit(id=audit_id,step_up_id=step.id,actor_user_id=user.id,target_user_id=job.target_user_id,
            action=operation['action'],target=operation['target'],payload_hash=operation_digest(**operation),
            result_json=json.dumps({'operation':command.operation,'before_hash':revision,'pending':current['counts'].get('pending',0)})))
        await db.flush();result=await _job_view(db,job);result['session_current']=True
    return {'command_id':audit_id,'job':result}


async def purge_expired_message_jobs(db,*,limit=100,now=None):
    if type(limit) is not int or not 1<=limit<=1000:raise ValueError('Invalid retention page')
    keys=(await db.scalars(select(Job.id).where(Job.expires_at<=(now or datetime.now(timezone.utc)))
        .order_by(Job.expires_at,Job.id).limit(limit).with_for_update(skip_locked=True))).all()
    if not keys:return 0
    await db.execute(delete(Recipient).where(Recipient.job_id.in_(keys)))
    await db.execute(delete(Job).where(Job.id.in_(keys)))
    return len(keys)


def create_message_drainer(*,settings_obj,session_factory,emit,drain_batches=100):
    slots=asyncio.Semaphore(2)
    async def send_batch(job_id):
        async with slots:
            for _ in range(min(max(drain_batches,1),100)):
                processed=await dispatch_message_batch(job_id=job_id,session_factory=session_factory,settings_obj=settings_obj,emit=emit)
                if not processed:return
                async with session_factory() as db:
                    status=await db.scalar(select(Job.status).where(Job.id==job_id))
                if status!='ready':return
    return send_batch


def create_admin_pwa_outbound_router(*,settings_obj,session_factory,emit=None,drain_batches=100,drainer=None):
    router=APIRouter(tags=['admin-pwa-outbound'])
    send_batch=drainer or create_message_drainer(settings_obj=settings_obj,session_factory=session_factory,
        emit=emit,drain_batches=drain_batches)
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
            logger.error('Admin PWA outbound command unavailable');return _reply(503,'admin_pwa_command_unavailable')
        return result
    def reply(result):
        return result if isinstance(result,JSONResponse) else JSONResponse({'ok':True,**result},headers=_PRIVATE_HEADERS)
    @router.post('/api/admin/v1/messages/read')
    async def read(request:Request):return reply(await handle(request,read_messages,MessageRead))
    @router.post('/api/admin/v1/messages/prepare')
    async def prepare(request:Request):return reply(await handle(request,prepare_message,PrepareMessage))
    @router.post('/api/admin/v1/messages/save')
    async def save(request:Request,background:BackgroundTasks):
        result=await handle(request,execute_message,ExecuteMessage)
        if not isinstance(result,JSONResponse) and emit is not None:
            background.add_task(send_batch,result['job']['job_id'])
        return reply(result)
    @router.post('/api/admin/v1/messages/run')
    async def run(request:Request,background:BackgroundTasks):
        result=await handle(request,authorize_message_run,RunMessage)
        if not isinstance(result,JSONResponse) and emit is not None:
            background.add_task(send_batch,result['job_id'])
        return reply(result)
    @router.post('/api/admin/v1/messages/stop')
    async def stop(request:Request):return reply(await handle(request,stop_message,RunMessage))
    @router.post('/api/admin/v1/messages/prepare-control')
    async def prepare_control(request:Request):return reply(await handle(request,prepare_message_control,PrepareMessageControl))
    @router.post('/api/admin/v1/messages/control')
    async def control(request:Request,background:BackgroundTasks):
        result=await handle(request,execute_message_control,ExecuteMessageControl)
        if not isinstance(result,JSONResponse) and result['job']['status']=='ready' and emit is not None:
            background.add_task(send_batch,result['job']['job_id'])
        return reply(result)
    return router

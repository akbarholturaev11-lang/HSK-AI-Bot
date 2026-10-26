"""First-party bounded campaigns; exact signed audiences use the existing claimed queue.

No legacy scheduler is activated. Discount creation changes offer configuration
only: shared checkout remains authoritative and notification defaults stay off.
"""
from datetime import datetime, timedelta, timezone
import html
import json
import logging
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError, field_validator, model_validator
from sqlalchemy import func, insert, select, text, update

from app.admin_api.pwa_campaign_schedule import utc_send_time, validate_schedule
from app.admin_api.pwa_access_grants import CommandError, StepId
from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_marketing import CampaignTexts, reviewed_campaign_buttons
from app.admin_api.pwa_outbound import (
    LANGS, MAX_AUDIENCE, MessageFilters, _hash, enqueue_reviewed_message, recipient_hash,
)
from app.admin_api.pwa_partners import _authenticate
from app.admin_api.pwa_payment_review import PositiveId, StrictModel
from app.admin_api.pwa_read import read_transaction
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, _authorized_admin
from app.admin_api.pwa_step_up import _enabled, consume_step_up_in_mutation, operation_digest
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.bot.keyboards.release_feedback import release_feedback_rating_keyboard
from app.db.models.ad_campaign import AdCampaign, AdCampaignDelivery
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.discount_campaign import DiscountCampaign
from app.db.models.payment_qr_code import PaymentQrCode
from app.services.payment_qr_code_service import PaymentQrCodeService
from app.services.subscription_price_service import SubscriptionPriceService
from app.db.models.release_feedback import ReleaseFeedbackCampaign, ReleaseFeedbackDelivery
from app.db.models.user import User
from app.repositories.ad_campaign_repo import AdCampaignRepository, decode_languages
from app.repositories.discount_campaign_repo import DiscountCampaignRepository
from app.repositories.release_feedback_repo import ReleaseFeedbackRepository
from app.repositories.user_repo import UserRepository
from app.services.broadcast_translation_service import (
    decode_localized_broadcast_text, encode_localized_broadcast_text,
)
from app.services.release_feedback_service import release_feedback_prompt

logger = logging.getLogger(__name__)
Kind = Literal['ad', 'release', 'discount']
MODELS = {'ad': AdCampaign, 'release': ReleaseFeedbackCampaign, 'discount': DiscountCampaign}
Digest = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]


class CampaignRead(StrictModel):
    kind: Kind
    campaign_id: PositiveId | None = None
    before_id: PositiveId | None = None

    @model_validator(mode='after')
    def distinct(self):
        if self.campaign_id and self.before_id:
            raise ValueError('Select a campaign or a page')
        return self


class ScheduledSend(StrictModel):
    send_at: str | None = None

    @field_validator('send_at')
    @classmethod
    def utc_time(cls, value):
        return utc_send_time(value)


class AdSend(ScheduledSend):
    kind: Literal['ad_send']
    campaign_id: PositiveId


class ReleaseCreate(ScheduledSend):
    kind: Literal['release_create']
    title: Annotated[str, Field(min_length=1, max_length=120)]
    texts: CampaignTexts
    filters: MessageFilters = Field(default_factory=MessageFilters)
    asset_id: StepId | None = None
    asset_hash: Digest | None = None

    @model_validator(mode='after')
    def asset_pair(self):
        if (self.asset_id is None) != (self.asset_hash is None):
            raise ValueError('Exact asset reference required')
        return self

    feature_key: Literal['general', 'qa', 'image', 'course', 'profile', 'subscription', 'android_subscription'] = 'general'

    @field_validator('title')
    @classmethod
    def title_copy(cls, value):
        value = value.strip()
        value.encode('utf-8')
        if not value or any(ord(c) < 32 for c in value):
            raise ValueError('Invalid title')
        return value


class DiscountCopy(StrictModel):
    title: Annotated[str, Field(min_length=1, max_length=120)]
    reason: Annotated[str, Field(max_length=500)] = ''

    @field_validator('title', 'reason')
    @classmethod
    def valid_copy(cls, value, info):
        value = value.strip()
        value.encode('utf-8')
        if (info.field_name == 'title' and not value) or any(ord(c) < 32 and c not in '\n\r\t' for c in value):
            raise ValueError('Invalid copy')
        return value


class DiscountCopies(StrictModel):
    uz: DiscountCopy
    ru: DiscountCopy
    tj: DiscountCopy


class DiscountCreate(StrictModel):
    kind: Literal['discount_create']
    copies: DiscountCopies
    percent: Annotated[int, Field(strict=True, ge=1, le=90)]
    duration_hours: Annotated[int, Field(strict=True, ge=1, le=720)] = 24
    audience_status: Literal['free', 'trial', 'active', 'expired'] | None = None
    audience_language: Literal['uz', 'ru', 'tj'] | None = None
    audience_level: Literal['beginner', 'hsk1', 'hsk2', 'hsk3', 'hsk4', 'nhsk1', 'nhsk2', 'nhsk3'] | None = None
    target_user_id: PositiveId | None = None
    payment_method: Literal['visa', 'alipay', 'wechat'] | None = None
    plan_type: Literal['10_days', '1_month'] | None = None
    quota_total: Annotated[int, Field(strict=True, ge=1, le=100000)] | None = None
    repeat_interval_days: Annotated[int, Field(strict=True, ge=1, le=365)] | None = None
    is_active: bool = False

    @model_validator(mode='after')
    def exact_target(self):
        if self.target_user_id is not None and any(
                value is not None for value in (self.audience_status, self.audience_language, self.audience_level)):
            raise ValueError('A personal offer cannot also target a segment')
        return self


class DiscountSend(StrictModel):
    kind: Literal['discount_send']
    campaign_id: PositiveId


class DiscountState(StrictModel):
    kind: Literal['discount_state']
    campaign_id: PositiveId
    is_active: bool


Change = Annotated[AdSend | ReleaseCreate | DiscountCreate | DiscountState | DiscountSend, Field(discriminator='kind')]


class PrepareCampaign(StrictModel):
    change: Change


class CampaignCommand(PrepareCampaign):
    expected_hash: Digest
    audience_hash: Digest | None = None
    audience_count: Annotated[int, Field(strict=True, ge=1, le=MAX_AUDIENCE)] | None = None
    content_hash: Digest

    @model_validator(mode='after')
    def delivery_scope(self):
        sends = self.change.kind in ('ad_send', 'release_create', 'discount_send')
        if sends != (self.audience_hash is not None and self.audience_count is not None):
            raise ValueError('Exact delivery scope required')
        if not sends and (self.audience_hash is not None or self.audience_count is not None):
            raise ValueError('No delivery scope for offer configuration')
        return self

    def operation(self):
        change = self.change
        payload = self.model_dump()
        if change.kind == 'release_create':
            payload['change'] = change.model_dump(exclude={'texts'})
        elif change.kind == 'discount_create':
            payload['change'] = change.model_dump(exclude={'copies'})
        target = (f'ad-{change.campaign_id}' if change.kind == 'ad_send' else
                  f'discount-{change.campaign_id}' if change.kind in ('discount_state','discount_send') else change.kind)
        return {'action': 'marketing.update', 'target': target, 'payload': payload}


class ExecuteCampaign(CampaignCommand):
    step_up_id: StepId


def revision(row):
    return _hash({column.key: ( _utc(value).isoformat() if isinstance(value, datetime) else value)
                  for column in row.__table__.columns
                  if not isinstance(row,DiscountCampaign) or column.key not in ('notification_sent_count','notification_failed_count')
                  for value in [getattr(row, column.key)]})


async def _row(db, kind, campaign_id, *, lock=False):
    model = MODELS[kind]
    query = select(model).where(model.id == campaign_id).execution_options(populate_existing=True)
    row = await db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise CommandError('admin_pwa_campaign_missing', 404)
    return row


def _view(row, kind, *, detail=False):
    state = row.status if kind == 'release' else 'active' if row.is_active else 'paused'
    if kind == 'ad' and row.rounds_sent >= row.send_count_total:
        state = 'sent'
    result = {'id': row.id, 'kind': kind, 'title': row.title, 'status': state,
              'revision_hash': revision(row)}
    if not detail:
        return result
    if kind == 'discount':
        from app.admin_api.pwa_discount_notices import notice_available
        result.update(percent=row.percent, starts_at=_utc(row.starts_at).isoformat(),
                      ends_at=_utc(row.ends_at).isoformat(), is_active=row.is_active,
                      target_user_id=row.target_user_id, quota_total=row.quota_total,
                      repeat_interval_days=row.repeat_interval_days,
                      audience_status=row.audience_status, audience_language=row.audience_language,
                      audience_level=row.audience_level, payment_method=row.payment_method, plan_type=row.plan_type,
                      can_activate=not row.notify_enabled,
                      can_send=notice_available(row),
                      copies={lang: {'title': getattr(row, 'title_' + lang) or row.title,
                                     'reason': getattr(row, 'reason_' + lang) or row.reason or ''}
                              for lang in LANGS})
    else:
        copies = decode_localized_broadcast_text(row.message_text)
        result['texts'] = {lang: html.unescape((copies or {}).get(lang, '')) for lang in LANGS}
        if kind == 'ad':
            result.update(ends_at=_utc(row.ends_at).isoformat(), rounds_sent=row.rounds_sent,
                          media_type=row.content_type,
                          can_send=not row.is_active and row.next_send_at is None and row.rounds_sent == 0
                          and row.send_count_total == 1 and row.content_type in ('text', 'photo', 'video')
                          and (not row.media_file_id if row.content_type == 'text' else bool(row.media_file_id))
                          and bool(copies) and set(copies) == set(LANGS)
                          and _utc(row.starts_at) <= datetime.now(timezone.utc) < _utc(row.ends_at))
        else:
            result.update(sent_count=row.sent_count, failed_count=row.failed_count, feature_key=row.feature_key)
    return result


async def read_campaigns(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError('not_found', 404)
    async with read_transaction(db):
        await _authenticate(db, session_cookie, settings_obj)
        if request.campaign_id:
            row = await _row(db, request.kind, request.campaign_id)
            result = _view(row, request.kind, detail=True)
            if request.kind == 'ad':
                try:
                    button, rendered = await reviewed_campaign_buttons(db, row.button_config)
                    result.update(button=button, buttons=rendered)
                    if rendered:
                        result['revision_hash'] = _hash({'campaign': revision(row), 'buttons': rendered})
                except CommandError:
                    result['can_send'] = False
            return {'campaign': result}
        model = MODELS[request.kind]
        # Metadata-only keyset. No provider IDs or long copy in the list query.
        state = model.status if request.kind == 'release' else model.is_active
        extra = (model.rounds_sent, model.send_count_total) if request.kind == 'ad' else ()
        query = select(model.id, model.title, state.label('state'), *extra)
        if request.before_id:
            query = query.where(model.id < request.before_id)
        rows = (await db.execute(query.order_by(model.id.desc()).limit(31))).all()
        items = [{'id': row.id, 'kind': request.kind, 'title': row.title,
                  'status': (row.state if request.kind == 'release' else
                             'sent' if request.kind == 'ad' and row.rounds_sent >= row.send_count_total else
                             'active' if row.state else 'paused')}
                 for row in rows[:30]]
        return {'items': items, 'next_before_id': items[-1]['id'] if len(rows) > 30 else None}


async def _targets(db, filters, settings_obj, *, exclude_active=False, lock=False, user_ids=None):
    names = {'track': 'course_track', 'mode': 'learning_mode', 'plan': 'selected_plan_type',
             'discount': 'discount_filter', 'course_promo': 'course_promo_filter', 'activity': 'activity_filter'}
    args = {names.get(key, key): value for key, value in filters.items()}
    return await UserRepository(db).get_filtered_users(**args, delivery_admin_ids=settings_obj.admin_id_list,
        limit=MAX_AUDIENCE + 1, for_update=lock, delivery_user_ids=user_ids,
        exclude_active_subscribers=exclude_active)


async def _prepare_state(db, change, settings_obj, *, cookie, lock=False):
    """Repeat all commitments inside the final transaction; no provider/AI IO."""
    row, metadata, snapshots = None, {}, []
    if change.kind == 'ad_send':
        row = await _row(db, 'ad', change.campaign_id, lock=lock)
        if not _view(row, 'ad', detail=True)['can_send']:
            raise CommandError('confirmation_changed', 409)
        if await db.scalar(select(AdCampaignDelivery.id).where(AdCampaignDelivery.campaign_id == row.id).limit(1)):
            raise CommandError('confirmation_changed', 409)
        stored = decode_localized_broadcast_text(row.message_text)
        # Only explicit plain authored copies from the paused-draft contract.
        copies = CampaignTexts.model_validate({lang: html.unescape(stored.get(lang, '')) for lang in LANGS})
        texts = {lang: html.escape(value, quote=False) for lang, value in copies.model_dump().items()}
        if texts != stored:
            raise CommandError('admin_pwa_invalid_payload', 400)
        if row.content_type != 'text' and any(len(value.encode('utf-16-le')) // 2 > 1024 for value in texts.values()):
            raise CommandError('admin_pwa_campaign_caption_too_long', 400)
        filters = MessageFilters(languages=decode_languages(row.target_languages), track=row.target_track,
                                 level=row.target_level).model_dump()
        metadata = {'kind': 'ad', 'campaign_id': row.id, 'filters': filters,
                    'exclude_active': not row.include_active_subscribers,
                    'media_type': row.content_type, 'media_file_id': row.media_file_id}
        _, rendered = await reviewed_campaign_buttons(db, row.button_config, lock=lock)
        if rendered:
            metadata['buttons'] = rendered
        current_hash = _hash({'campaign': revision(row), 'buttons': rendered}) if rendered else revision(row)
        content = {'texts': texts, 'buttons': rendered,
                   'media_hash': _hash([row.content_type, row.media_file_id])}
    elif change.kind == 'release_create':
        texts = {lang: html.escape(value, quote=False) + release_feedback_prompt(lang)
                 for lang, value in change.texts.model_dump().items()}
        media_hash = None
        if change.asset_id:
            from app.admin_api.pwa_campaign_assets import owned_campaign_asset, asset_digest
            asset = await owned_campaign_asset(db, cookie=cookie, asset_id=change.asset_id,
                expected_hash=change.asset_hash, settings_obj=settings_obj, lock=lock)
            media_hash = asset_digest(asset)
        if any(len(value.encode('utf-16-le')) // 2 > (1024 if change.asset_id else 4096) for value in texts.values()):
            raise CommandError('admin_pwa_invalid_payload', 400)
        metadata = {'kind': 'release', 'filters': change.filters.model_dump(), 'exclude_active': False}
        if change.asset_id:
            metadata.update(media_type=asset.media_type, media_file_id=asset.provider_file_id)
        content = {'media_hash': media_hash, 'texts': texts, 'markup': {lang: release_feedback_rating_keyboard(0, lang).model_dump(mode='json')
                                            for lang in LANGS},
                   'discount_percent': 20, 'discount_hours': 24, 'trial_access_minutes': 30}
        current_hash = _hash({'release_create': 'new'})
    elif change.kind == 'discount_send':
        from app.admin_api.pwa_discount_notices import notice_available, notice_copy, notice_users, notice_recipient_hash
        row = await _row(db, 'discount', change.campaign_id, lock=lock)
        if not notice_available(row):
            raise CommandError('confirmation_changed', 409)
        texts, phone, buttons = await notice_copy(db, row)
        users = await notice_users(db, row, settings_obj, lock=lock)
        if not users:
            raise CommandError('admin_pwa_message_no_targets', 409)
        if len(users)>MAX_AUDIENCE:
            raise CommandError('admin_pwa_message_too_many_targets', 400)
        snapshots=[{'user_id':user.id,'snapshot_hash':notice_recipient_hash(user),
                    'language':user.language if user.language in LANGS else 'tj'} for user in users]
        metadata={'kind':'discount','campaign_id':row.id,'filters':{},'phone_texts':phone,'buttons':buttons}
        return row,revision(row),_hash({'texts':texts,'phone_texts':phone,'buttons':buttons}),snapshots,metadata,texts
    elif change.kind == 'discount_create':
        if change.target_user_id:
            query = select(User).where(User.id == change.target_user_id).execution_options(populate_existing=True)
            row = await db.scalar(query.with_for_update() if lock else query)
            if row is None or row.status == 'blocked' or row.telegram_id in settings_obj.admin_id_list:
                raise CommandError('admin_pwa_invalid_target', 400)
            current_hash = _hash([row.id, row.telegram_id, row.status])
        else:
            current_hash = _hash({'discount_create': 'new'})
        content = change.copies.model_dump()
        return row, current_hash, _hash(content), snapshots, metadata, None
    else:
        row = await _row(db, 'discount', change.campaign_id, lock=lock)
        if change.is_active and (row.notify_enabled or _utc(row.ends_at) <= datetime.now(timezone.utc)):
            raise CommandError('confirmation_changed', 409)
        return row, revision(row), _hash({'is_active': change.is_active}), snapshots, metadata, None
    metadata['not_before'] = await validate_schedule(db, cookie=cookie, send_at=change.send_at)
    if row is not None and change.kind == 'ad_send' and metadata['not_before'] and _utc(row.ends_at) <= metadata['not_before']:
        raise CommandError('admin_pwa_campaign_schedule_invalid', 409)
    users = await _targets(db, metadata['filters'], settings_obj,
                           exclude_active=metadata['exclude_active'], lock=lock)
    if not users:
        raise CommandError('admin_pwa_message_no_targets', 409)
    if len(users) > MAX_AUDIENCE:
        raise CommandError('admin_pwa_message_too_many_targets', 400)
    snapshots = [{'user_id': user.id, 'snapshot_hash': recipient_hash(user),
                  'language': user.language if user.language in LANGS else 'tj'} for user in users]
    return row, current_hash, _hash(content), snapshots, metadata, texts


async def prepare_campaign(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError('not_found', 404)
    async with read_transaction(db):
        await _authenticate(db, session_cookie, settings_obj)
        _, revision_hash, content_hash, snapshots, _, texts = await _prepare_state(db, request.change, settings_obj, cookie=session_cookie)
        command = CampaignCommand(change=request.change, expected_hash=revision_hash, content_hash=content_hash,
                                  audience_hash=_hash(snapshots) if snapshots else None,
                                  audience_count=len(snapshots) if snapshots else None)
        return {'operation': command.operation(), 'execute_payload': command.model_dump(),
                'current': {'revision_hash': revision_hash},
                'proposed': {'audience_count': len(snapshots), 'texts': texts}}


async def execute_campaign(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError('not_found', 404)
    command = CampaignCommand.model_validate(request.model_dump(exclude={'step_up_id'}))
    operation = command.operation()
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
        row, current_hash, content_hash, snapshots, metadata, texts = await _prepare_state(
            db, command.change, settings_obj, cookie=session_cookie, lock=True)
        now = datetime.now(timezone.utc)
        if (not _enabled(settings_obj) or not _authorized_admin(actor, settings_obj) or session.revoked_at is not None
                or min(_utc(step.expires_at), _utc(session.expires_at)) <= now):
            raise CommandError('admin_pwa_step_up_denied', 403)
        if (current_hash != command.expected_hash or content_hash != command.content_hash
                or snapshots and (_hash(snapshots) != command.audience_hash or len(snapshots) != command.audience_count)):
            raise CommandError('confirmation_changed', 409)
        change = command.change
        if change.kind == 'discount_create' and change.is_active and change.payment_method != 'visa':
            # The campaign ID is not known until creation. Create paused,
            # upload each exact campaign QR, then explicitly activate.
            raise CommandError('admin_pwa_payment_qr_required', 409)
        if change.kind == 'discount_state' and change.is_active:
            methods = ([row.payment_method] if row.payment_method in ('visa', 'alipay', 'wechat')
                       else ['alipay', 'wechat'])
            plans = [row.plan_type] if row.plan_type in ('10_days', '1_month') else ['10_days', '1_month']
            qr_service = PaymentQrCodeService(db)
            for method in methods:
                if method == 'visa':
                    continue
                for plan in plans:
                    price = await SubscriptionPriceService(db).get_price(method, plan)
                    if price is None:
                        raise CommandError('admin_pwa_payment_qr_required', 409)
                    final_amount = int(round(price.amount * (100 - row.percent) / 100))
                    if final_amount < 1 or not await qr_service.get_file_id(
                        scope=qr_service.admin_campaign_scope(row.id),
                        payment_method=method, plan_type=plan,
                        amount=final_amount, currency=price.currency):
                        raise CommandError('admin_pwa_payment_qr_required', 409)
        if change.kind == 'ad_send':
            # Reserve the single round atomically; never hand it to the legacy scheduler.
            await AdCampaignRepository(db).mark_round_finished(row, now=now)
            kind = 'ad'
        elif change.kind == 'release_create':
            filters = change.filters
            row = await ReleaseFeedbackRepository(db).create_campaign(
                title=change.title, message_text=encode_localized_broadcast_text(
                    {lang: html.escape(value, quote=False) for lang, value in change.texts.model_dump().items()}),
                content_type=metadata.get('media_type', 'text'), media_file_id=metadata.get('media_file_id'),
                send_at=metadata.get('not_before') or now, feature_key=change.feature_key,
                target_languages=filters.languages, status_filter=filters.status, level_filter=filters.level,
                mode_filter=filters.mode, payment_status_filter=filters.payment_status,
                payment_method_filter=filters.payment_method, plan_filter=filters.plan,
                discount_filter=filters.discount, course_promo_filter=filters.course_promo,
                activity_filter=filters.activity, created_by_telegram_id=actor.telegram_id)
            await ReleaseFeedbackRepository(db).mark_sending(row)
            metadata['campaign_id'] = row.id
            kind = 'release'
        elif change.kind == 'discount_send':
            row.notification_sent_at = now  # One signed round, even if the provider is uncertain.
            kind = 'discount'
        elif change.kind == 'discount_create':
            copies = change.copies.model_dump()
            row = await DiscountCampaignRepository(db).create(
                title=copies['tj']['title'],
                **{f'{key}_{lang}': copy[key]
                   for lang, copy in copies.items() for key in ('title', 'reason')},
                percent=change.percent, starts_at=now, ends_at=now + timedelta(hours=change.duration_hours),
                **change.model_dump(include={'audience_status', 'audience_language', 'audience_level',
                    'target_user_id', 'payment_method', 'plan_type', 'quota_total', 'repeat_interval_days'}),
                notify_enabled=False, created_by_telegram_id=actor.telegram_id)
            row.is_active = change.is_active
            kind = 'discount'
        else:
            if change.is_active:
                row.is_active = True
            else:
                await DiscountCampaignRepository(db).deactivate(row)
            kind = 'discount'
        await db.flush()
        audit_id = str(uuid4())
        db.add(AdminPwaCommandAudit(id=audit_id, step_up_id=step.id, actor_user_id=actor.id,
            target_user_id=change.target_user_id if change.kind == 'discount_create' else None,
            action=operation['action'], target=operation['target'], payload_hash=operation_digest(**operation),
            result_json=json.dumps({'kind': change.kind, 'campaign_id': row.id, 'before_hash': current_hash,
                                    'after_hash': revision(row), 'content_hash': content_hash,
                                    'audience_count': len(snapshots), 'audience_hash': command.audience_hash})))
        await db.flush()
        if change.kind == 'release_create' and change.asset_id:
            # Lock/recheck after every queue/campaign lock wait, within the same transaction.
            from app.admin_api.pwa_campaign_assets import owned_campaign_asset
            asset = await owned_campaign_asset(db, cookie=session_cookie, asset_id=change.asset_id,
                expected_hash=change.asset_hash, settings_obj=settings_obj, lock=True)
            if (not _authorized_admin(actor, settings_obj) or session.revoked_at is not None
                    or min(_utc(step.expires_at), _utc(session.expires_at)) <= datetime.now(timezone.utc)):
                raise CommandError('admin_pwa_step_up_denied', 403)
            asset.status, asset.command_id = 'used', audit_id
            await db.flush()
        job = None
        if snapshots:
            not_before = metadata.pop('not_before', None)
            metadata['job_id'] = audit_id
            # Final time check follows recipient/campaign lock waits.
            if not_before is not None:
                await validate_schedule(db, cookie=session_cookie, send_at=change.send_at)
            metadata['revision_hash'] = revision(row)
            users = (await db.execute(select(User.id, User.telegram_id).where(
                User.id.in_([snapshot['user_id'] for snapshot in snapshots])))).all()
            metadata['targets'] = {str(user.id): user.telegram_id for user in users}
            job = await enqueue_reviewed_message(db, command_id=audit_id, actor_user_id=actor.id,
                session_id=session.id, target_user_id=None, kind='broadcast', texts=texts,
                filters=metadata['filters'], snapshots=snapshots, digest=command.audience_hash,
                campaign=metadata, now=now, not_before=not_before,
                photo_file_id=metadata.get('media_file_id') if metadata.get('media_type') == 'photo' else None,
                video_file_id=metadata.get('media_file_id') if metadata.get('media_type') == 'video' else None)
            # Unique legacy evidence reserves every intended transport before provider IO.
            if kind != 'discount':
                delivery_model = AdCampaignDelivery if kind == 'ad' else ReleaseFeedbackDelivery
                await db.execute(insert(delivery_model), [dict(campaign_id=row.id,
                    user_telegram_id=user.telegram_id, status='pending',
                    **({'round_no': row.rounds_sent} if kind == 'ad' else {})) for user in users])
        result = _view(row, kind, detail=True)
    return {'command_id': audit_id, 'campaign': result, 'job_id': job.id if job else None}


async def campaign_recipient_allowed(db, metadata, user, settings_obj):
    try:
        row = await _row(db, metadata['kind'], metadata['campaign_id'])
    except CommandError as exc:
        if exc.status == 404:
            return False
        raise
    if revision(row) != metadata['revision_hash']:
        return False
    if metadata['kind'] == 'ad' and _utc(row.ends_at) <= datetime.now(timezone.utc):
        return False
    if metadata['kind'] == 'discount':
        from app.admin_api.pwa_discount_notices import notice_users
        return bool(row.is_active and _utc(row.starts_at)<=datetime.now(timezone.utc)<_utc(row.ends_at)
                    and await notice_users(db,row,settings_obj,user_ids=[user.id]))
    users = await _targets(db, metadata['filters'], settings_obj,
        exclude_active=metadata['exclude_active'], user_ids=[user.id])
    return bool(users)


async def record_campaign_attempt(db, metadata, telegram_id, status, message_id=None):
    if metadata['kind'] == 'discount':
        return  # Canonical recipient claims are the durable evidence, without invented TG IDs.
    model = AdCampaignDelivery if metadata['kind'] == 'ad' else ReleaseFeedbackDelivery
    values = {'status': status}
    if metadata['kind'] == 'release' and type(message_id) is int and message_id > 0:
        values['message_id'] = message_id
    allowed = ('pending', 'attempting', 'uncertain') if status == 'sent' else ('pending', 'attempting')
    query = update(model).where(model.campaign_id == metadata['campaign_id'], model.user_telegram_id == telegram_id,
                                model.status.in_(allowed))
    written = await db.execute(query.values(**values))
    if written.rowcount and metadata['kind'] == 'release' and status in ('sent', 'uncertain'):
        # One already claimed provider call can finish after Stop. Keep the
        # stopped campaign's counters consistent with that durable receipt.
        row = await _row(db, 'release', metadata['campaign_id'], lock=True)
        if row.status == 'stopped':
            counts = dict((await db.execute(select(ReleaseFeedbackDelivery.status, func.count()).where(
                ReleaseFeedbackDelivery.campaign_id == row.id).group_by(ReleaseFeedbackDelivery.status))).all())
            row.sent_count = counts.get('sent', 0)
            row.failed_count = sum(count for state, count in counts.items() if state != 'sent')


async def finish_campaign_job(db, metadata, *, closed=False):
    if metadata['kind'] == 'discount':
        from app.db.models.admin_pwa_outbound import AdminPwaOutboundRecipient as Recipient
        counts=dict((await db.execute(select(Recipient.status,func.count()).where(
            Recipient.job_id==metadata['job_id']).group_by(Recipient.status))).all())
        row=await _row(db,'discount',metadata['campaign_id'],lock=True)
        if revision(row)==metadata['revision_hash']:
            row.notification_sent_count=counts.get('attempted',0)
            row.notification_failed_count=sum(count for state,count in counts.items() if state!='attempted')
        return
    model = AdCampaignDelivery if metadata['kind'] == 'ad' else ReleaseFeedbackDelivery
    # A removed account or stopped job must not leave unclaimed legacy work.
    await db.execute(update(model).where(model.campaign_id == metadata['campaign_id'],
        model.status == 'pending').values(status='skipped'))
    if closed:
        await db.execute(update(model).where(model.campaign_id == metadata['campaign_id'],
            model.status == 'attempting').values(status='uncertain'))
    if metadata['kind'] != 'release':
        return
    try:
        row = await _row(db, 'release', metadata['campaign_id'], lock=True)
    except CommandError as exc:
        if exc.status == 404:
            return
        raise
    if row.status != 'sending':
        return
    counts = dict((await db.execute(select(ReleaseFeedbackDelivery.status, func.count()).where(
        ReleaseFeedbackDelivery.campaign_id == row.id).group_by(ReleaseFeedbackDelivery.status))).all())
    if closed:
        row.sent_count = counts.get('sent', 0)
        row.failed_count = sum(count for status, count in counts.items() if status != 'sent')
        await ReleaseFeedbackRepository(db).stop_campaign(row)
    else:
        await ReleaseFeedbackRepository(db).mark_sent(row, sent_count=counts.get('sent', 0),
            failed_count=sum(count for status, count in counts.items() if status != 'sent'))


def create_admin_pwa_campaigns_router(*, settings_obj, session_factory, drainer=None):
    router = APIRouter(tags=['admin-pwa-campaigns'])

    async def handle(request, task, schema):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, '')
        if not cookie:
            return _reply(401, 'admin_pwa_unauthorized')
        try:
            parsed = schema.model_validate(await _body(request, 64 * 1024))
        except ValidationError:
            return _reply(400, 'admin_pwa_invalid_payload')
        try:
            async with session_factory() as db:
                return await task(db, session_cookie=cookie, request=parsed, settings_obj=settings_obj)
        except CommandError as exc:
            return _reply(exc.status, str(exc))
        except Exception:
            logger.error('Admin PWA campaign command unavailable')
            return _reply(503, 'admin_pwa_command_unavailable')

    def reply(result):
        return result if isinstance(result, JSONResponse) else JSONResponse({'ok': True, **result}, headers=_PRIVATE_HEADERS)

    @router.post('/api/admin/v1/campaigns/read')
    async def read(request: Request):
        return reply(await handle(request, read_campaigns, CampaignRead))

    @router.post('/api/admin/v1/campaigns/prepare')
    async def prepare(request: Request):
        return reply(await handle(request, prepare_campaign, PrepareCampaign))

    @router.post('/api/admin/v1/campaigns/save')
    async def save(request: Request, background: BackgroundTasks):
        result = await handle(request, execute_campaign, ExecuteCampaign)
        if not isinstance(result, JSONResponse) and result['job_id'] and drainer is not None:
            background.add_task(drainer, result['job_id'])
        return reply(result)
    return router

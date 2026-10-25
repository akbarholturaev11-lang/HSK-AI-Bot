"""Bounded private campaign staging; binary data never enters SQL or browser storage."""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import logging
from pathlib import Path
import shutil
import subprocess
import tempfile
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import delete, select, text

from app.admin_api.pwa_access_grants import CommandError, StepId
from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _gate, _reply
from app.admin_api.pwa_marketing import (
    _PWA_COURSE_AD_VIDEO_SLOT, _PWA_COURSE_AD_VIDEO_TYPES, _PWA_PROMO_IMAGE_TYPES, _validate_promo_image,
)
from app.admin_api.pwa_outbound import _hash
from app.admin_api.pwa_partners import _authenticate
from app.admin_api.pwa_payment_review import StrictModel
from app.admin_api.pwa_read import read_transaction
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, _authorized_admin
from app.admin_api.pwa_step_up import _enabled, _locked_session
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_campaign_asset import AdminPwaCampaignAsset as Asset
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.course_ad_media import CourseAdVideoError, prepare_pwa_course_ad_video_file

logger = logging.getLogger(__name__)
PHOTO_MAX = 2 * 1024 * 1024
VIDEO_MAX = 25 * 1024 * 1024


class AssetReference(StrictModel):
    asset_id: StepId


@dataclass(frozen=True)
class CampaignMediaUpload:
    actor_telegram_id: int
    media_type: str
    path: str


def asset_digest(row):
    return _hash([row.id, row.media_type, row.content_hash, row.byte_count, row.provider_file_id,
                  _utc(row.expires_at).isoformat()])


def asset_public(row):
    return {'asset_id': row.id, 'asset_hash': asset_digest(row), 'media_type': row.media_type,
            'content_hash': row.content_hash, 'byte_count': row.byte_count,
            'expires_at': _utc(row.expires_at).isoformat()}


async def _waits(db):
    if db.get_bind().dialect.name == 'postgresql':
        await db.execute(text("SET LOCAL lock_timeout = '5000'"))
        await db.execute(text("SET LOCAL statement_timeout = '8000'"))


def _authority(user, session, settings_obj):
    if (not _enabled(settings_obj) or not _authorized_admin(user, settings_obj)
            or session.revoked_at is not None or _utc(session.expires_at) <= datetime.now(timezone.utc)):
        raise CommandError('admin_pwa_unauthorized', 401)


async def owned_campaign_asset(db, *, cookie, asset_id, settings_obj, lock=False, expected_hash=None):
    actor = await _authenticate(db, cookie, settings_obj)
    session_id = await db.scalar(select(AdminPwaSession.id).where(
        AdminPwaSession.token_hash == hashlib.sha256(cookie.encode()).hexdigest()))
    query = select(Asset).where(Asset.id == asset_id, Asset.actor_user_id == actor.user_id,
        Asset.session_id == session_id).execution_options(populate_existing=True)
    row = await db.scalar(query.with_for_update() if lock else query)
    if (row is None or row.status != 'ready' or not row.provider_file_id
            or _utc(row.expires_at) <= datetime.now(timezone.utc)):
        raise CommandError('admin_pwa_campaign_asset_unavailable', 409)
    if expected_hash is not None and not hmac.compare_digest(asset_digest(row), expected_hash):
        raise CommandError('confirmation_changed', 409)
    return row


async def reserve_campaign_upload(db, *, cookie, media_type, content_hash, byte_count, settings_obj):
    async with db.begin():
        await _waits(db)
        pair = await _locked_session(db, cookie, settings_obj, datetime.now(timezone.utc))
        if pair is None:
            raise CommandError('admin_pwa_unauthorized', 401)
        session, user = pair
        await BotSettingRepository(db).lock_key('pwa_campaign_upload:' + str(user.id))
        _authority(user, session, settings_obj)
        now = datetime.now(timezone.utc)
        recent = (await db.scalars(select(Asset.id).where(Asset.actor_user_id == user.id,
            Asset.created_at > now - timedelta(hours=1)).limit(20))).all()
        if len(recent) >= 20:
            raise CommandError('admin_pwa_campaign_asset_rate_limited', 429)
        row = Asset(id=str(uuid4()), actor_user_id=user.id, session_id=session.id, media_type=media_type,
            content_hash=content_hash, byte_count=byte_count, status='uploading', created_at=now,
            expires_at=now + timedelta(minutes=15))
        db.add(row)
        await db.flush()
        return row.id, user.telegram_id


async def finish_campaign_upload(db, *, cookie, asset_id, file_id, settings_obj):
    async with db.begin():
        await _waits(db)
        pair = await _locked_session(db, cookie, settings_obj, datetime.now(timezone.utc))
        if pair is None:
            raise CommandError('admin_pwa_unauthorized', 401)
        session, user = pair
        row = await db.scalar(select(Asset).where(Asset.id == asset_id, Asset.actor_user_id == user.id,
            Asset.session_id == session.id).with_for_update())
        _authority(user, session, settings_obj)
        if row is None or row.status != 'uploading' or _utc(row.expires_at) <= datetime.now(timezone.utc):
            raise CommandError('admin_pwa_campaign_asset_unavailable', 409)
        if (not isinstance(file_id, str) or not 1 <= len(file_id) <= 512 or not file_id.isascii()
                or any(ord(c) <= 32 for c in file_id)):
            row.status = 'failed'
            return None
        row.provider_file_id = file_id
        row.status = 'ready'
        return asset_public(row)


def prepare_campaign_video(raw, content_type, root):
    """The thread owns the encoder slot until the bounded child exits, even on disconnect."""
    if not _PWA_COURSE_AD_VIDEO_SLOT.acquire(blocking=False):
        raise CommandError('course_ad_video_busy', 429)
    try:
        source = Path(root) / ('source' + _PWA_COURSE_AD_VIDEO_TYPES[content_type])
        source.write_bytes(raw)
        probe = shutil.which('ffprobe')
        if not probe:
            raise CommandError('course_ad_video_unavailable', 503)
        container = 'matroska' if content_type == 'video/webm' else 'mov'
        result = subprocess.run([probe, '-v', 'error', '-max_alloc', '67108864', '-protocol_whitelist', 'file,pipe',
            '-f', container, '-select_streams', 'v:0', '-show_entries', 'stream=width,height:format=duration',
            '-of', 'json', str(source)], capture_output=True, check=True, timeout=8)
        info = json.loads(result.stdout)
        stream = info['streams'][0]
        duration = float(info['format']['duration'])
        width, height = int(stream['width']), int(stream['height'])
        if min(width, height) <= 0 or width * height > 4096 * 2160 or max(width, height) > 4096 or not 0 < duration <= 180:
            raise ValueError('Video bounds')
        name = prepare_pwa_course_ad_video_file(raw, raw_ext=_PWA_COURSE_AD_VIDEO_TYPES[content_type], media_root=root)
        path = Path(root) / name
        if not 0 < path.stat().st_size <= VIDEO_MAX:
            raise ValueError('Encoded video size')
        return str(path)
    except CommandError:
        raise
    except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError, CourseAdVideoError) as exc:
        raise CommandError('admin_pwa_campaign_asset_invalid', 422) from exc
    finally:
        _PWA_COURSE_AD_VIDEO_SLOT.release()


async def purge_expired_campaign_assets(db, *, limit=100, now=None):
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError('Invalid bounded expiry page')
    now = now or datetime.now(timezone.utc)
    keys = (await db.scalars(select(Asset.id).where(Asset.expires_at <= now,
        Asset.created_at <= now - timedelta(hours=1))
        .order_by(Asset.expires_at, Asset.id).limit(limit).with_for_update(skip_locked=True))).all()
    if keys:
        await db.execute(delete(Asset).where(Asset.id.in_(keys)))
    return len(keys)


def create_admin_pwa_campaign_assets_router(*, settings_obj, session_factory, upload=None):
    router = APIRouter(tags=['admin-pwa-campaign-assets'])
    slots = asyncio.Semaphore(2)

    @router.post('/api/admin/v1/campaign-assets')
    async def stage(request: Request):
        failure = _gate(request, settings_obj)
        if failure is not None:
            return failure
        if (request.headers.getlist('origin') != [settings_obj.ADMIN_PWA_PUBLIC_ORIGIN]
                or request.headers.get('sec-fetch-site', 'same-origin') != 'same-origin'):
            return _reply(403, 'admin_pwa_csrf')
        content_type = request.headers.get('content-type', '').split(';', 1)[0]
        photo = content_type in _PWA_PROMO_IMAGE_TYPES
        if not photo and content_type not in _PWA_COURSE_AD_VIDEO_TYPES:
            return _reply(415, 'unsupported_media_type')
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, '')
        if not cookie:
            return _reply(401, 'admin_pwa_unauthorized')
        if request.query_params:
            return _reply(400, 'admin_pwa_invalid_payload')
        if upload is None:
            return _reply(503, 'admin_pwa_campaign_asset_unavailable')
        asset_id = None
        acquired = False
        try:
            async with session_factory() as db:
                async with read_transaction(db):
                    await _authenticate(db, cookie, settings_obj)
            await asyncio.wait_for(slots.acquire(), .1)
            acquired = True
            raw = bytearray()
            bound = PHOTO_MAX if photo else VIDEO_MAX
            async for chunk in request.stream():
                if len(raw) + len(chunk) > bound:
                    return _reply(413, 'admin_pwa_media_too_large')
                raw.extend(chunk)
            if not raw:
                return _reply(400, 'admin_pwa_campaign_asset_invalid')
            raw = bytes(raw)
            async with session_factory() as db:
                asset_id, admin = await reserve_campaign_upload(db, cookie=cookie,
                    media_type='photo' if photo else 'video', content_hash=hashlib.sha256(raw).hexdigest(),
                    byte_count=len(raw), settings_obj=settings_obj)
            with tempfile.TemporaryDirectory(prefix='hsk-pwa-campaign-') as root:
                if photo:
                    extension = await asyncio.to_thread(_validate_promo_image, raw, content_type)
                    path = str(Path(root) / ('campaign' + extension))
                    await asyncio.to_thread(Path(path).write_bytes, raw)
                else:
                    path = await asyncio.to_thread(prepare_campaign_video, raw, content_type, root)
                file_id = None
                try:
                    file_id = await asyncio.wait_for(upload(CampaignMediaUpload(admin, 'photo' if photo else 'video', path)), 20)
                except Exception:
                    logger.warning('Admin PWA campaign upload outcome unavailable')
            async with session_factory() as db:
                result = await finish_campaign_upload(db, cookie=cookie, asset_id=asset_id,
                    file_id=file_id, settings_obj=settings_obj)
            if result is None:
                return _reply(503, 'admin_pwa_campaign_asset_unavailable')
            return JSONResponse({'ok': True, **result}, headers=_PRIVATE_HEADERS)
        except asyncio.TimeoutError:
            return _reply(429, 'admin_pwa_campaign_asset_busy')
        except CommandError as exc:
            if asset_id:
                try:
                    async with session_factory() as db:
                        await finish_campaign_upload(db, cookie=cookie, asset_id=asset_id, file_id=None, settings_obj=settings_obj)
                except Exception:
                    pass
            return _reply(exc.status, str(exc))
        except Exception:
            logger.error('Admin PWA campaign asset unavailable')
            return _reply(503, 'admin_pwa_campaign_asset_unavailable')
        finally:
            if acquired:
                slots.release()

    @router.get('/api/admin/v1/campaign-assets/{asset_id}')
    async def metadata(request: Request, asset_id: str):
        failure = _gate(request, settings_obj)
        if failure is not None:
            return failure
        if request.headers.get('sec-fetch-site', 'same-origin') != 'same-origin' or (
                request.headers.get('origin') and request.headers['origin'] != settings_obj.ADMIN_PWA_PUBLIC_ORIGIN):
            return _reply(403, 'admin_pwa_csrf')
        try:
            parsed = AssetReference(asset_id=asset_id)
            if request.query_params:
                raise ValueError('No query parameters')
        except (ValueError, ValidationError):
            return _reply(400, 'admin_pwa_invalid_payload')
        try:
            async with session_factory() as db:
                async with read_transaction(db):
                    row = await owned_campaign_asset(db, cookie=request.cookies.get(ADMIN_PWA_COOKIE_NAME, ''),
                        asset_id=parsed.asset_id, settings_obj=settings_obj)
                    return JSONResponse({'ok': True, **asset_public(row)}, headers=_PRIVATE_HEADERS)
        except CommandError as exc:
            return _reply(exc.status, str(exc))
        except Exception:
            return _reply(503, 'admin_pwa_campaign_asset_unavailable')
    return router

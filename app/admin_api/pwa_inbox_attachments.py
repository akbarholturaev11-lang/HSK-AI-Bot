"""Private Admin PWA image views; no MCP, Telegram URL, or file ID exposure.

Retained native JPEG screenshots and source-owned Bot/Release raster images
use bounded internal row IDs, never Telegram file IDs or user-provided URLs.
"""
import asyncio
import io
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError
from sqlalchemy import and_, select

from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _gate, _reply
from app.admin_api.pwa_read import read_transaction
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, authenticate_admin_pwa_session
from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
from app.db.models.bot_feedback import BotFeedback
from app.db.models.release_feedback import ReleaseFeedbackResponse
from app.db.models.user import User

_MAX_NATIVE_BYTES = 550 * 1024
_MAX_IMAGE_PIXELS = 20_000_000
_MAX_TELEGRAM_BYTES = 8 * 1024 * 1024
_DOWNLOAD_TIMEOUT = 10
_DOWNLOADS_PER_MINUTE = 30


@dataclass(frozen=True)
class _TelegramReference:
    actor_id: int
    owner_id: int
    file_id: str
    kind: str
    source_owner: tuple[int, ...]


def _image_type(raw, max_bytes):
    if not isinstance(raw, bytes) or not 4 <= len(raw) <= max_bytes:
        return None
    try:
        with Image.open(io.BytesIO(raw)) as img:
            media = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(img.format)
            if not media or img.width * img.height > _MAX_IMAGE_PIXELS:
                return None
            img.verify()
        return media
    except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError):
        return None


def _valid_jpeg(raw):
    # Native Android intake historically verified only JPEG magic. Fail closed
    # on corrupt or non-JPEG retained bytes instead of serving arbitrary data.
    return (isinstance(raw, bytes) and raw.startswith(b"\xff\xd8\xff")
            and _image_type(raw, _MAX_NATIVE_BYTES) == "image/jpeg")


def create_admin_pwa_inbox_attachment_router(*, settings_obj, session_factory, loader=None):
    router = APIRouter(tags=["admin-pwa-inbox-attachments"])
    # Bound provider IO per worker; this is not a distributed/global quota.
    downloads = asyncio.Semaphore(2)
    window_started, download_count = time.monotonic(), 0

    @router.get("/api/admin/v1/inbox/android/{report_id}/attachment")
    async def native_attachment(request: Request, report_id: str):
        failure = _gate(request, settings_obj)
        if failure is not None:
            return failure
        # Even browser GETs carrying the admin cookie cannot be embedded by a
        # sibling site or cross-site page. An Origin header must be canonical.
        if (request.headers.get("sec-fetch-site", "same-origin") != "same-origin"
                or (request.headers.get("origin")
                    and request.headers.get("origin") != settings_obj.ADMIN_PWA_PUBLIC_ORIGIN)):
            return _reply(403, "admin_pwa_csrf")
        # Parse AFTER the rollout guard: typed path validation would leak
        # HTTP 422 even when ADMIN_PWA_ENABLED is false. Every PWA entry must
        # return 404 before touching authentication or the database.
        if (len(report_id) > 10 or not report_id.isascii()
                or not report_id.isdecimal() or request.query_params):
            return _reply(400, "admin_pwa_invalid_payload")
        report_key = int(report_id)
        if not 0 < report_key <= 2_147_483_647:
            return _reply(400, "admin_pwa_invalid_payload")
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        try:
            async with session_factory() as db:
                async with read_transaction(db):
                    actor = await authenticate_admin_pwa_session(db, cookie, settings_obj)
                    if actor is None:
                        return _reply(401, "admin_pwa_unauthorized")
                    if actor.auth_method != "webauthn":
                        return _reply(403, "admin_pwa_attachment_denied")
                    raw = await db.scalar(select(AdminPwaNativeReport.attachment_bytes).where(
                        AdminPwaNativeReport.id == report_key,
                        AdminPwaNativeReport.expires_at > datetime.now(timezone.utc),
                    ))
                    if not _valid_jpeg(raw):
                        return _reply(404, "admin_pwa_attachment_unavailable")
            # No response body, filename or reference is logged or cached.
            return Response(content=raw, media_type="image/jpeg",
                            headers={**_PRIVATE_HEADERS, "Content-Disposition": "inline"})
        except Exception:
            # Deliberately do not log student images, SQL parameters or URLs.
            return _reply(503, "admin_pwa_attachment_unavailable")

    @router.get("/api/admin/v1/inbox/{source}/{item_id}/attachment")
    async def telegram_attachment(request: Request, source: str, item_id: str):
        nonlocal window_started, download_count
        failure = _gate(request, settings_obj)
        if failure is not None:
            return failure
        if (request.headers.get("sec-fetch-site", "same-origin") != "same-origin"
                or (request.headers.get("origin")
                    and request.headers.get("origin") != settings_obj.ADMIN_PWA_PUBLIC_ORIGIN)):
            return _reply(403, "admin_pwa_csrf")
        if source not in ("bot", "release"):
            return _reply(404, "admin_pwa_attachment_unavailable")
        # Keep parsing behind the gate, including unknown/malformed path values.
        if (len(item_id) > 10 or not item_id.isascii() or not item_id.isdecimal()
                or not 0 < int(item_id) <= 2_147_483_647 or request.query_params):
            return _reply(400, "admin_pwa_invalid_payload")
        key = int(item_id)
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")

        async def authorized_reference():
            async with session_factory() as db:
                async with read_transaction(db):
                    actor = await authenticate_admin_pwa_session(db, cookie, settings_obj)
                    if actor is None:
                        return None, 401
                    if actor.auth_method != "webauthn":
                        return None, 403
                    if source == "bot":
                        pair = (await db.execute(select(
                            BotFeedback.disliked_attachment_file_id, BotFeedback.disliked_attachment_type,
                            User.id, BotFeedback.user_id, BotFeedback.telegram_id
                        ).select_from(BotFeedback).join(
                            User, User.id == BotFeedback.user_id).where(BotFeedback.id == key))).first()
                        if pair is None:
                            return None, 404
                    else:
                        pair = (await db.execute(select(
                            ReleaseFeedbackResponse.attachment_file_id, ReleaseFeedbackResponse.attachment_type,
                            User.id, ReleaseFeedbackResponse.campaign_id, ReleaseFeedbackResponse.user_telegram_id
                        ).select_from(ReleaseFeedbackResponse).join(
                            User, and_(User.telegram_id > 0,
                                User.telegram_id == ReleaseFeedbackResponse.user_telegram_id)
                        ).where(ReleaseFeedbackResponse.id == key))).first()
                        if pair is None:
                            return None, 404
                    file_id, kind, owner_id, *binding = pair
                    if (kind not in ("photo", "document") or not isinstance(file_id, str)
                            or not 1 <= len(file_id) <= 256 or any(c.isspace() for c in file_id)):
                        return None, 404
                    return _TelegramReference(actor.user_id, owner_id, file_id, kind, tuple(binding)), 200

        try:
            reference, status = await authorized_reference()
            if status != 200:
                return _reply(status, "admin_pwa_attachment_unavailable")
            if loader is None:
                return _reply(503, "admin_pwa_attachment_unavailable")
            if downloads.locked():
                response = _reply(429, "admin_pwa_attachment_busy")
                response.headers["Retry-After"] = "1"
                return response
            current = time.monotonic()
            if current - window_started >= 60:
                window_started, download_count = current, 0
            if download_count >= _DOWNLOADS_PER_MINUTE:
                response = _reply(429, "admin_pwa_attachment_busy")
                response.headers["Retry-After"] = str(max(1, math.ceil(60 - (current - window_started))))
                return response
            download_count += 1
            # No DB session/connection remains held during provider IO or validation.
            async with downloads:
                async with asyncio.timeout(_DOWNLOAD_TIMEOUT):
                    raw, media_type = await loader(reference.file_id)
                validated_type = _image_type(raw, _MAX_TELEGRAM_BYTES)
                if validated_type is None or media_type != validated_type:
                    return _reply(404, "admin_pwa_attachment_unavailable")
                failure = _gate(request, settings_obj)
                if failure is not None:
                    return failure
                checked, status = await authorized_reference()
                if status != 200 or checked != reference:
                    return _reply(status if status != 200 else 409, "admin_pwa_attachment_unavailable")
                return Response(raw, media_type=media_type,
                    headers={**_PRIVATE_HEADERS, "Content-Disposition": "inline"})
        except ValueError:
            return _reply(404, "admin_pwa_attachment_unavailable")
        except Exception:
            # Provider paths/tokens, source identifiers and bytes stay out of logs.
            return _reply(503, "admin_pwa_attachment_unavailable")

    return router

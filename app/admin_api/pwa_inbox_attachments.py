"""Private Admin PWA Android attachment view; no MCP, Telegram URL, or file ID.

Only still-retained native JPEG screenshots can be served. The URL contains a
bounded internal row ID, not a Telegram file ID or a user-controlled path.
"""
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select

from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _gate, _reply
from app.admin_api.pwa_read import read_transaction
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, authenticate_admin_pwa_session
from app.db.models.admin_pwa_native_report import AdminPwaNativeReport

_MAX_NATIVE_BYTES = 550 * 1024
_MAX_IMAGE_PIXELS = 20_000_000


def _valid_jpeg(raw):
    # Native Android intake historically verified only JPEG magic. Fail closed
    # on corrupt or non-JPEG retained bytes instead of serving arbitrary data.
    if (not isinstance(raw, bytes) or not 4 <= len(raw) <= _MAX_NATIVE_BYTES
            or not raw.startswith(b"\xff\xd8\xff")):
        return False
    try:
        with Image.open(io.BytesIO(raw)) as img:
            if img.format != "JPEG" or img.width * img.height > _MAX_IMAGE_PIXELS:
                return False
            img.verify()
        return True
    except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError):
        return False


def create_admin_pwa_inbox_attachment_router(*, settings_obj, session_factory):
    router = APIRouter(tags=["admin-pwa-inbox-attachments"])

    @router.get("/api/admin/v1/inbox/android/{report_id}/attachment")
    async def native_attachment(request: Request, report_id: int):
        failure = _gate(request, settings_obj)
        if failure is not None:
            return failure
        # Even browser GETs carrying the admin cookie cannot be embedded by a
        # sibling site or cross-site page. An Origin header must be canonical.
        if (request.headers.get("sec-fetch-site", "same-origin") != "same-origin"
                or (request.headers.get("origin")
                    and request.headers.get("origin") != settings_obj.ADMIN_PWA_PUBLIC_ORIGIN)):
            return _reply(403, "admin_pwa_csrf")
        if (report_id <= 0 or report_id > 2_147_483_647
                or request.query_params):
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
                        AdminPwaNativeReport.id == report_id,
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

    return router

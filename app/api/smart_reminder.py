"""V1 Smart preference adapters. No cookie/query/body-selected ownership."""
import json
import logging
from datetime import datetime, timezone
from urllib.parse import parse_qsl

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import select

from app.api.desktop_auth import bearer_access_token, auth_error_response
from app.db.models.user import User
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.smart_reminder_preferences import (
    SmartReminderActor, SmartReminderError, SmartReminderPatch, SmartReminderPreferencesService,
)
from app.services.telegram_webapp_auth import extract_fresh_verified_webapp_user_id
from app.services.smart_reminder_capabilities import SmartCapabilityPatch, SmartReminderCapabilityService
from app.services.smart_reminder_android import AndroidStudyClaim, AndroidStudyReceipt, SmartReminderAndroidService

logger = logging.getLogger(__name__)
HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"}
MAX_BYTES = 4096


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate field")
        result[key] = value
    return result


async def _payload(request, model=SmartReminderPatch):
    if request.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
        raise SmartReminderError("smart_json_required", 415)
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > MAX_BYTES:
            raise SmartReminderError("smart_request_too_large", 413)
    try:
        return model.model_validate(json.loads(raw, object_pairs_hook=_unique))
    except (ValueError, TypeError, ValidationError):
        raise SmartReminderError("smart_request_invalid", 422) from None


def create_smart_reminder_router(*, session_factory, settings_obj, android_delivery_factory=None):
    router = APIRouter(tags=["smart-reminder"])

    async def actor(session, request, android):
        if any(len(request.headers.getlist(key)) > 1 for key in ("Authorization", "X-Telegram-Init-Data")):
            raise SmartReminderError("smart_auth_ambiguous", 401)
        if android:
            if request.headers.get("X-Telegram-Init-Data"):
                raise SmartReminderError("smart_auth_ambiguous", 401)
            current = await DesktopAuthService(session, settings_obj).authenticate(bearer_access_token(request))
            if current.device.platform != "android":
                raise SmartReminderError("android_device_required", 403)
            return SmartReminderActor(current.user.id, "android", device_id=current.device.id,
                session_id=current.session.id,
                access_expires_at=datetime.fromtimestamp(current.claims["exp"], timezone.utc))
        if request.headers.get("Authorization"):
            raise SmartReminderError("smart_auth_ambiguous", 401)
        raw = request.headers.get("X-Telegram-Init-Data", "")
        if not raw or len(raw.encode()) > MAX_BYTES:
            raise SmartReminderError("smart_auth_required", 401)
        try:
            params = _unique(parse_qsl(raw, keep_blank_values=True))
            user = json.loads(params.get("user", "{}"), object_pairs_hook=_unique)
            uid = user.get("id") if isinstance(user, dict) else None
            if type(uid) is not int or uid <= 0:
                raise ValueError("Invalid transport")
        except (ValueError, TypeError):
            raise SmartReminderError("smart_auth_required", 401) from None
        verified = extract_fresh_verified_webapp_user_id(raw, settings_obj.BOT_TOKEN, max_age_seconds=86400)
        if verified != uid:
            raise SmartReminderError("smart_auth_required", 401)
        user_id = await session.scalar(select(User.id).where(User.telegram_id == verified))
        if user_id is None:
            raise SmartReminderError("smart_account_not_found", 404)
        return SmartReminderActor(user_id, "telegram", telegram_id=verified)

    async def respond(request, *, android, write, capability=False, delivery=None, job_id=None):
        try:
            if request.query_params:
                raise SmartReminderError("smart_request_invalid", 422)
            # Authentication precedes payload interpretation; proof never comes
            # from a fallback body, query parameter or ambient browser cookie.
            async with session_factory() as session:
                async with session.begin():
                    current = await actor(session, request, android)
                    if delivery:
                        service = android_delivery_factory(session) if android_delivery_factory else SmartReminderAndroidService(session)
                        if delivery in {"due", "mode"}: result = await getattr(service, delivery)(current)
                        else:
                            model = AndroidStudyClaim if delivery == "claim" else AndroidStudyReceipt
                            result = await getattr(service, delivery)(current, job_id, await _payload(request, model))
                    else:
                        service = SmartReminderCapabilityService(session) if capability else SmartReminderPreferencesService(session)
                        model = SmartCapabilityPatch if capability else SmartReminderPatch
                        result = await service.patch(current, await _payload(request, model)) if write else await service.read(current)
            return JSONResponse(result, headers=HEADERS)
        except SmartReminderError as exc:
            body = {"ok": False, "error": exc.code}
            if exc.revision is not None:
                body["revision"] = exc.revision
            return JSONResponse(body, status_code=exc.status, headers=HEADERS)
        except DesktopAuthError as exc:
            response = auth_error_response(exc)
            response.headers.update(HEADERS)
            return response
        except Exception:
            # No exception/SQL/credential payloads in public output or logs.
            logger.error("Smart preference operation unavailable")
            return JSONResponse({"ok": False, "error": "smart_unavailable"}, status_code=503, headers=HEADERS)

    @router.get("/api/v3/smart-reminder/preferences")
    async def telegram_read(request: Request):
        return await respond(request, android=False, write=False)

    @router.patch("/api/v3/smart-reminder/preferences")
    async def telegram_patch(request: Request):
        return await respond(request, android=False, write=True)

    @router.get("/api/v3/android/smart-reminder/preferences")
    async def android_read(request: Request):
        return await respond(request, android=True, write=False)

    @router.patch("/api/v3/android/smart-reminder/preferences")
    async def android_patch(request: Request):
        return await respond(request, android=True, write=True)

    @router.get("/api/v3/android/smart-reminder/capability")
    async def android_capability_read(request: Request):
        return await respond(request, android=True, write=False, capability=True)

    @router.patch("/api/v3/android/smart-reminder/capability")
    async def android_capability_patch(request: Request):
        return await respond(request, android=True, write=True, capability=True)

    @router.get("/api/v3/android/smart-reminder/mode")
    async def android_study_mode(request: Request):
        return await respond(request, android=True, write=False, delivery="mode")

    @router.get("/api/v3/android/smart-reminder/due")
    async def android_study_due(request: Request):
        return await respond(request, android=True, write=False, delivery="due")

    @router.post("/api/v3/android/smart-reminder/jobs/{job_id}/claim")
    async def android_study_claim(job_id: str, request: Request):
        return await respond(request, android=True, write=True, delivery="claim", job_id=job_id)

    @router.post("/api/v3/android/smart-reminder/jobs/{job_id}/receipt")
    async def android_study_receipt(job_id: str, request: Request):
        return await respond(request, android=True, write=True, delivery="receipt", job_id=job_id)

    return router

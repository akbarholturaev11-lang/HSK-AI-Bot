"""Authenticated diagnostic intake for Android (bearer) and the learner PWA
(cookie + CSRF + same origin). Design D3.

The owner comes only from the verified session. In `off` mode the routes
answer `paused` without a database read, and clients pause for 24 hours.
"""
import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.desktop_auth import auth_error_response, bearer_access_token
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.monitoring import catalog
from app.services.monitoring.intake import (
    IntakeRejected, current_mode, ingest, is_owner_account, parse_batch,
)
from app.services.pwa_auth_service import (
    PWA_SESSION_COOKIE, PwaAuthError, PwaAuthService, require_pwa_enabled, require_same_origin,
)
from app.services.user_access_state_service import UserAccessState, UserAccessStateService

logger = logging.getLogger(__name__)
_NO_STORE = {"Cache-Control": "no-store"}
PAUSED = {"accepted": 0, "paused": True}


async def read_bounded_json(request: Request, limit=catalog.MAX_BODY_BYTES):
    """Size is checked from Content-Length and a capped read, before parsing."""
    if request.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
        raise IntakeRejected("invalid_body")
    declared = request.headers.get("Content-Length", "").strip()
    if declared and (not declared.isdigit() or int(declared) > limit):
        raise IntakeRejected("too_large")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > limit:
            raise IntakeRejected("too_large")
    try:
        return json.loads(bytes(body))
    except (ValueError, UnicodeDecodeError):
        raise IntakeRejected("invalid_body") from None


def _rejected(exc: IntakeRejected):
    return JSONResponse({"ok": False, "error": exc.code}, status_code=413 if exc.code == "too_large" else 422,
                        headers=_NO_STORE)


def create_monitoring_intake_router(*, session_factory, settings_obj) -> APIRouter:
    router = APIRouter(tags=["monitoring-intake"])

    @router.post("/api/v3/android/diagnostics")
    async def android_diagnostics(request: Request):
        mode = current_mode(settings_obj)
        if mode == "off":
            return JSONResponse(PAUSED, headers=_NO_STORE)
        try:
            body = await read_bounded_json(request)
            async with session_factory() as session:
                context = await DesktopAuthService(session, settings_obj).authenticate(
                    access_token=bearer_access_token(request))
                if context.device.platform != "android":
                    raise DesktopAuthError("android_device_required", status_code=403)
                # A bearer access token outlives a block until it expires; refuse here.
                if UserAccessStateService.classify(context.user) == UserAccessState.BLOCKED:
                    raise DesktopAuthError("user_blocked", status_code=403)
                events, rejected = parse_batch(body, platform="android")
                result = await ingest(session, owner_user_id=context.user.id, events=events, mode=mode,
                                      owner_admitted=is_owner_account(settings_obj, context.user.telegram_id))
                await session.commit()
            result.rejected += rejected
            return JSONResponse(result.response(), headers=_NO_STORE)
        except IntakeRejected as exc:
            return _rejected(exc)
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("Android diagnostic intake failed")
            return auth_error_response(DesktopAuthError("diagnostics_unavailable", status_code=503))

    @router.post("/api/v3/pwa/diagnostics")
    async def pwa_diagnostics(request: Request):
        mode = current_mode(settings_obj)
        if mode == "off":
            return JSONResponse(PAUSED, headers=_NO_STORE)
        try:
            require_pwa_enabled(settings_obj)
            require_same_origin(request, settings_obj)
            if request.query_params or request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            body = await read_bounded_json(request)
            async with session_factory() as session:
                user, _ = await PwaAuthService(session, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE), request.headers.get("X-HSK-PWA-CSRF"))
                events, rejected = parse_batch(body, platform="iphone_pwa")
                result = await ingest(session, owner_user_id=user.id, events=events, mode=mode,
                                      owner_admitted=is_owner_account(settings_obj, user.telegram_id))
                await session.commit()
            result.rejected += rejected
            return JSONResponse(result.response(), headers=_NO_STORE)
        except IntakeRejected as exc:
            return _rejected(exc)
        except PwaAuthError as exc:
            return JSONResponse({"ok": False, "error": exc.code}, status_code=exc.status_code, headers=_NO_STORE)
        except Exception:
            logger.exception("PWA diagnostic intake failed")
            return JSONResponse({"ok": False, "error": "diagnostics_unavailable"}, status_code=503,
                                headers=_NO_STORE)

    return router

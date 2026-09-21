"""iOS subscription/trial transport backed by the shared desktop subscription service."""

from __future__ import annotations
import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.desktop_subscription import _access_token
from app.services.desktop_auth_service import DesktopAuthError
from app.services.desktop_subscription_service import DesktopSubscriptionError, DesktopSubscriptionService

logger = logging.getLogger(__name__)


def create_ios_subscription_router(
    *,
    session_factory,
    settings_obj,
    bot,
    service_factory=DesktopSubscriptionService,
) -> APIRouter:
    router = APIRouter(tags=["ios-subscription"])

    def service(session):
        return service_factory(session, settings_obj, bot=bot)

    @router.get("/api/v3/ios/subscription/overview")
    async def ios_subscription_overview(request: Request):
        try:
            if request.query_params:
                raise DesktopSubscriptionError("ios_subscription_request_invalid", status_code=422)
            async with session_factory() as session:
                result = await service(session).overview(_access_token(request))
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopSubscriptionError) as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"ok": False, "error": exc.code},
                headers={"Cache-Control": "no-store"},
            )
        except Exception:
            logger.exception("iOS subscription overview failed")
            return JSONResponse(status_code=503, content={"ok": False, "error": "ios_subscription_unavailable"})

    @router.get("/api/v3/ios/subscription/trial")
    async def ios_trial_status(request: Request):
        try:
            if request.query_params:
                raise DesktopSubscriptionError("ios_subscription_request_invalid", status_code=422)
            async with session_factory() as session:
                result = await service(session).trial_status(_access_token(request))
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopSubscriptionError) as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"ok": False, "error": exc.code},
                headers={"Cache-Control": "no-store"},
            )
        except Exception:
            logger.exception("iOS trial status failed")
            return JSONResponse(status_code=503, content={"ok": False, "error": "ios_subscription_unavailable"})

    @router.post("/api/v3/ios/subscription/trial/start")
    async def ios_trial_start(request: Request):
        try:
            if request.query_params:
                raise DesktopSubscriptionError("ios_subscription_request_invalid", status_code=422)
            async with session_factory() as session:
                result = await service(session).trial_start(_access_token(request))
                if not result.get("ok"):
                    return JSONResponse(status_code=409, content=result, headers={"Cache-Control": "no-store"})
                await session.commit()
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopSubscriptionError) as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"ok": False, "error": exc.code},
                headers={"Cache-Control": "no-store"},
            )
        except Exception:
            logger.exception("iOS trial start failed")
            return JSONResponse(status_code=503, content={"ok": False, "error": "ios_subscription_unavailable"})

    return router

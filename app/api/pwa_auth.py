"""Browser-only learner PWA login/session transport; disabled until configured.

This router never authenticates a legacy Telegram course endpoint. Client PWA
routes must explicitly resolve the actor and enforce CSRF on state mutation.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.services.pwa_auth_service import (
    PWA_OAUTH_AGE_SECONDS,
    PWA_OAUTH_COOKIE,
    PWA_SESSION_COOKIE,
    PWA_SESSION_AGE_SECONDS,
    PwaAuthError,
    PwaAuthService,
    require_same_origin,
)

_NO_STORE = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


class PwaLoginStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["google", "apple"]
    language: Literal["uz", "ru", "tj"] | None = None


def _error(exc: PwaAuthError) -> JSONResponse:
    return JSONResponse(
        {"ok": False, "error": exc.code},
        status_code=exc.status_code, headers=_NO_STORE,
    )


def _session_cookie(response: JSONResponse, token: str) -> None:
    response.set_cookie(
        PWA_SESSION_COOKIE, token, max_age=PWA_SESSION_AGE_SECONDS,
        path="/", secure=True, httponly=True, samesite="lax",
    )


def _clear_cookie(response: JSONResponse, name: str) -> None:
    response.delete_cookie(name, path="/", secure=True, httponly=True, samesite="lax")


def create_pwa_auth_router(*, session_factory, settings_obj) -> APIRouter:
    router = APIRouter(tags=["pwa-auth"])

    @router.post("/api/v3/pwa-auth/start")
    async def start(request: Request):
        try:
            require_same_origin(request, settings_obj)
            raw = await request.body()
            if len(raw) > 1024 or request.headers.get("Content-Type", "").split(";")[0] != "application/json":
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            payload = PwaLoginStart.model_validate_json(raw)
            async with session_factory() as db:
                url, proof = await PwaAuthService(db, settings_obj).start(
                    provider=payload.provider, language=payload.language,
                )
            response = JSONResponse(
                {"ok": True, "authorize_url": url},
                headers=_NO_STORE,
            )
            response.set_cookie(
                PWA_OAUTH_COOKIE, proof, max_age=PWA_OAUTH_AGE_SECONDS,
                path="/", secure=True, httponly=True, samesite="none",
            )
            return response
        except PwaAuthError as exc:
            return _error(exc)
        except Exception as exc:
            # Never disclose provider configuration, cookie or server internals.
            if exc.__class__.__name__ in {"ValidationError", "DesktopAuthError", "NativeOAuthError", "IdentityLinkError"}:
                return _error(PwaAuthError("pwa_signin_unavailable", status_code=422))
            return _error(PwaAuthError("pwa_signin_unavailable", status_code=503))

    @router.get("/api/v3/pwa-auth/session")
    async def current(request: Request):
        try:
            cookie = request.cookies.get(PWA_SESSION_COOKIE)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).actor(cookie)
                csrf = PwaAuthService(db, settings_obj).csrf(cookie)
            return JSONResponse(
                {"ok": True, "user_id": actor.id, "language": actor.language,
                 "csrf": csrf, "telegram_linked": bool(actor.telegram_id)},
                headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa-auth/logout")
    async def logout(request: Request):
        try:
            require_same_origin(request, settings_obj)
            cookie = request.cookies.get(PWA_SESSION_COOKIE) or ""
            csrf = request.headers.get("X-HSK-PWA-CSRF", "")
            async with session_factory() as db:
                await PwaAuthService(db, settings_obj).logout(cookie, csrf)
            response = JSONResponse({"ok": True}, headers=_NO_STORE)
            _clear_cookie(response, PWA_SESSION_COOKIE)
            return response
        except PwaAuthError as exc:
            return _error(exc)

    return router

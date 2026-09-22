"""Transport adapter for Google / Apple sign-in and identity linking.

Like ``app/api/android_auth.py`` this module is transport only: every
cryptographic, resolution and rate-limiting decision lives in
``NativeOAuthService`` / ``IdentityLinkService`` / ``DesktopAuthService``.

Nothing here returns a session token. A sign-in flow ends by marking the shared
link row approved; the client then calls the existing, unchanged
``/api/v3/{android,desktop}-auth/link/status`` to receive its token pair.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Callable, Literal

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.api.desktop_auth import (
    AppVersion,
    InstallationKey,
    LinkRequestId,
    OpaqueSecret,
    auth_error_response,
    bearer_access_token,
    validated_auth_payload,
)
from app.services.desktop_auth_service import (
    LINK_INTENT,
    SIGNIN_INTENT,
    DesktopAuthError,
    DesktopAuthService,
)
from app.repositories.user_repo import UserRepository
from app.services.identity_link_service import IdentityLinkError, IdentityLinkService
from app.services.telegram_webapp_auth import extract_fresh_verified_webapp_user_id
from app.services.native_oauth_service import (
    BROWSER_REDIRECT_MODE,
    NATIVE_ID_TOKEN_MODE,
    NativeOAuthError,
    NativeOAuthService,
    available_providers,
)


logger = logging.getLogger(__name__)

# An OIDC ID token runs around a kilobyte, so these two endpoints need more than
# the 2 KiB default. Every other endpoint keeps it.
ASSERT_BODY_MAX_BYTES = 4096
APPLE_FORM_MAX_BYTES = 8192

Provider = Literal["google", "apple"]
MINIAPP_PLATFORM = "miniapp"
# The Mini App proves identity with fresh Telegram initData, exactly like every
# other Mini App endpoint. Same window the admin Mini App uses.
MINIAPP_INIT_DATA_MAX_AGE_SECONDS = 86400
MAX_INIT_DATA_CHARS = 4096
IdentityId = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=36)
]
IdToken = Annotated[str, Field(min_length=16, max_length=8192)]
OAuthState = Annotated[str, StringConstraints(min_length=8, max_length=256)]
OAuthCode = Annotated[str, StringConstraints(min_length=1, max_length=2048)]


class OAuthStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: Literal["android", "macos", "windows"]
    app_version: AppVersion
    installation_key: InstallationKey
    provider: Provider
    mode: Literal["native_id_token", "browser_redirect"]


class OAuthAssertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    link_request_id: LinkRequestId
    polling_secret: OpaqueSecret
    provider: Literal["google"]
    id_token: IdToken


class IdentityLinkStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: Literal["android", "macos", "windows", "miniapp"]
    app_version: AppVersion
    # The Mini App has no installation of its own; the server derives a stable
    # per-account value so the existing per-installation rate limit still
    # applies. Native clients must still send their real key.
    installation_key: InstallationKey | None = None
    provider: Provider
    mode: Literal["native_id_token", "browser_redirect"]


class IdentityLinkStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    link_request_id: LinkRequestId
    polling_secret: OpaqueSecret


class IdentityUnlinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identity_id: IdentityId


_NO_STORE = {"Cache-Control": "no-store"}
# The browser page is seen by whoever finished the provider flow. It carries no
# token, no user data and no prose — the app shows the translated message, so
# this never becomes a fourth translation surface.
_PAGE_HEADERS = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
    "X-Content-Type-Options": "nosniff",
}
_PAGE_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>HSK AI</title>
<style>
:root{{color-scheme:light dark}}
body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
background:#faf8f5;color:#1a1a1a}}
@media(prefers-color-scheme:dark){{body{{background:#14110f;color:#f2efe9}}}}
.card{{text-align:center;padding:32px 24px;max-width:320px}}
.mark{{font-size:44px;line-height:1}}
.code{{margin-top:12px;font:12px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;opacity:.55;
word-break:break-all}}
</style></head>
<body><div class="card"><div class="mark">{mark}</div><div class="code">{code}</div></div></body>
</html>"""


def _page(mark: str, code: str) -> HTMLResponse:
    safe = "".join(ch for ch in str(code or "") if ch.isalnum() or ch in "_-")[:64]
    return HTMLResponse(
        content=_PAGE_TEMPLATE.format(mark=mark, code=safe),
        status_code=200,
        headers=_PAGE_HEADERS,
    )


def _oauth_error(error: NativeOAuthError | IdentityLinkError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"ok": False, "error": error.code},
        headers=_NO_STORE,
    )


def _unavailable() -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"ok": False, "error": "oauth_unavailable"},
        headers=_NO_STORE,
    )


async def _apple_form(request: Request) -> dict[str, str]:
    """Parse Apple's bounded ``form_post`` callback body."""

    content_type = str(request.headers.get("Content-Type", "") or "")
    if (
        content_type.split(";", 1)[0].strip().lower()
        != "application/x-www-form-urlencoded"
    ):
        raise NativeOAuthError("oauth_state_invalid", status_code=400)
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > APPLE_FORM_MAX_BYTES:
            raise NativeOAuthError("oauth_state_invalid", status_code=413)
    from urllib.parse import parse_qsl

    try:
        return dict(parse_qsl(bytes(body).decode("utf-8"), keep_blank_values=True))
    except (UnicodeDecodeError, ValueError) as exc:
        raise NativeOAuthError("oauth_state_invalid", status_code=400) from exc


def create_native_oauth_router(
    *,
    session_factory,
    settings_obj: Any,
    service_factory: Callable[..., NativeOAuthService] = NativeOAuthService,
) -> APIRouter:
    router = APIRouter(tags=["native-oauth"])

    def _init_data(request: Request) -> str:
        return str(request.headers.get("X-Telegram-Init-Data", "") or "")[
            :MAX_INIT_DATA_CHARS
        ]

    async def _actor(session, request):
        """The signed-in user, proven by a bearer token or by Telegram initData.

        Two transports, one meaning: both identify an already authenticated
        account. Neither can create one, so allowing the Mini App here adds a
        client, not a new way in.
        """

        token = bearer_access_token(request)
        if token:
            context = await DesktopAuthService(session, settings_obj).authenticate(
                token
            )
            return context.user, context.session.id

        init_data = _init_data(request)
        telegram_id = (
            extract_fresh_verified_webapp_user_id(
                init_data,
                str(getattr(settings_obj, "BOT_TOKEN", "") or ""),
                max_age_seconds=MINIAPP_INIT_DATA_MAX_AGE_SECONDS,
            )
            if init_data
            else None
        )
        if not telegram_id:
            raise DesktopAuthError("desktop_access_invalid", status_code=401)
        user = await UserRepository(session).get_by_telegram_id(int(telegram_id))
        if not user:
            raise DesktopAuthError("desktop_user_not_found", status_code=404)
        # No desktop session to preserve: a Mini App unlink revokes every
        # native session, which is exactly what the user is asking for.
        return user, None

    @router.get("/api/v3/native-auth/providers")
    async def providers(platform: str | None = None):
        normalized = platform if platform in {"android", "macos", "windows"} else None
        return JSONResponse(
            content={
                "ok": True,
                "providers": available_providers(settings_obj, platform=normalized),
            },
            headers=_NO_STORE,
        )

    @router.post("/api/v3/native-auth/oauth/start")
    async def oauth_start(request: Request):
        try:
            payload = await validated_auth_payload(request, OAuthStartRequest)
            async with session_factory() as session:
                started = await service_factory(session, settings_obj).start(
                    provider=payload.provider,
                    mode=payload.mode,
                    platform=payload.platform,
                    app_version=payload.app_version,
                    installation_key=payload.installation_key.get_secret_value(),
                    intent=SIGNIN_INTENT,
                )
            content: dict[str, Any] = {
                "ok": True,
                "status": "pending",
                "link_request_id": started.link_request_id,
                "polling_secret": started.polling_secret,
                "expires_in": started.expires_in,
            }
            if payload.mode == NATIVE_ID_TOKEN_MODE:
                content["nonce"] = started.nonce
            if payload.mode == BROWSER_REDIRECT_MODE:
                content["authorize_url"] = started.authorize_url
            return JSONResponse(content=content, headers=_NO_STORE)
        except (NativeOAuthError, IdentityLinkError) as exc:
            return _oauth_error(exc)
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("OAuth start failed")
            return _unavailable()

    @router.post("/api/v3/native-auth/oauth/assert")
    async def oauth_assert(request: Request):
        try:
            payload = await validated_auth_payload(
                request, OAuthAssertRequest, max_bytes=ASSERT_BODY_MAX_BYTES
            )
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).assert_id_token(
                    link_request_id=payload.link_request_id,
                    polling_secret=payload.polling_secret.get_secret_value(),
                    provider=payload.provider,
                    id_token=payload.id_token,
                )
            return JSONResponse(content=result, headers=_NO_STORE)
        except (NativeOAuthError, IdentityLinkError) as exc:
            return _oauth_error(exc)
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("OAuth assert failed")
            return _unavailable()

    @router.get("/api/v3/native-auth/oauth/callback/google")
    async def google_callback(
        state: OAuthState | None = None,
        code: OAuthCode | None = None,
        error: str | None = None,
    ):
        if error or not state or not code:
            return _page("&#10005;", "oauth_cancelled")
        try:
            async with session_factory() as session:
                await service_factory(session, settings_obj).complete_callback(
                    provider="google", state=state, code=code
                )
            return _page("&#10003;", "ok")
        except (NativeOAuthError, IdentityLinkError, DesktopAuthError) as exc:
            return _page("&#10005;", exc.code)
        except Exception:
            logger.exception("Google OAuth callback failed")
            return _page("&#10005;", "oauth_unavailable")

    @router.post("/api/v3/native-auth/oauth/callback/apple")
    async def apple_callback(request: Request):
        try:
            form = await _apple_form(request)
        except NativeOAuthError as exc:
            return _page("&#10005;", exc.code)
        state = form.get("state") or ""
        code = form.get("code") or ""
        if form.get("error") or not state or not code:
            return _page("&#10005;", "oauth_cancelled")
        try:
            async with session_factory() as session:
                await service_factory(session, settings_obj).complete_callback(
                    provider="apple",
                    state=state,
                    code=code,
                    apple_user=form.get("user"),
                )
            return _page("&#10003;", "ok")
        except (NativeOAuthError, IdentityLinkError, DesktopAuthError) as exc:
            return _page("&#10005;", exc.code)
        except Exception:
            logger.exception("Apple OAuth callback failed")
            return _page("&#10005;", "oauth_unavailable")

    # --- bearer-authenticated identity management ------------------------

    @router.get("/api/v3/native-auth/identities")
    async def list_identities(request: Request):
        try:
            async with session_factory() as session:
                actor, _ = await _actor(session, request)
                items = await IdentityLinkService(
                    session, settings_obj
                ).list_identities(actor.id)
            return JSONResponse(
                content={
                    "ok": True,
                    "telegram_linked": bool(actor.telegram_id),
                    "identities": items,
                },
                headers=_NO_STORE,
            )
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("Identity list failed")
            return _unavailable()

    @router.post("/api/v3/native-auth/identities/link/start")
    async def identity_link_start(request: Request):
        try:
            payload = await validated_auth_payload(request, IdentityLinkStartRequest)
            async with session_factory() as session:
                actor, _ = await _actor(session, request)
                if payload.platform == MINIAPP_PLATFORM:
                    if payload.mode != BROWSER_REDIRECT_MODE:
                        raise NativeOAuthError(
                            "oauth_mode_unsupported", status_code=422
                        )
                    # Derived, not supplied: one stable value per account keeps
                    # the existing per-installation rate limit meaningful
                    # without inventing a client-side installation identity.
                    installation_key = DesktopAuthService(
                        session, settings_obj
                    )._hash("miniapp-install", str(actor.id))
                elif payload.installation_key is None:
                    raise NativeOAuthError(
                        "desktop_installation_key_invalid", status_code=422
                    )
                else:
                    installation_key = payload.installation_key.get_secret_value()
                started = await service_factory(session, settings_obj).start(
                    provider=payload.provider,
                    mode=payload.mode,
                    platform=payload.platform,
                    app_version=payload.app_version,
                    installation_key=installation_key,
                    intent=LINK_INTENT,
                    bind_user_id=int(actor.id),
                )
            content: dict[str, Any] = {
                "ok": True,
                "status": "pending",
                "link_request_id": started.link_request_id,
                "polling_secret": started.polling_secret,
                "expires_in": started.expires_in,
            }
            if payload.mode == NATIVE_ID_TOKEN_MODE:
                content["nonce"] = started.nonce
            if payload.mode == BROWSER_REDIRECT_MODE:
                content["authorize_url"] = started.authorize_url
            return JSONResponse(content=content, headers=_NO_STORE)
        except (NativeOAuthError, IdentityLinkError) as exc:
            return _oauth_error(exc)
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("Identity link start failed")
            return _unavailable()

    @router.post("/api/v3/native-auth/identities/link/status")
    async def identity_link_status(request: Request):
        try:
            payload = await validated_auth_payload(request, IdentityLinkStatusRequest)
            async with session_factory() as session:
                actor, _ = await _actor(session, request)
                result = await service_factory(session, settings_obj).link_status(
                    link_request_id=payload.link_request_id,
                    polling_secret=payload.polling_secret.get_secret_value(),
                    user_id=int(actor.id),
                )
            return JSONResponse(content=result, headers=_NO_STORE)
        except (NativeOAuthError, IdentityLinkError) as exc:
            return _oauth_error(exc)
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("Identity link status failed")
            return _unavailable()

    @router.post("/api/v3/native-auth/identities/unlink")
    async def identity_unlink(request: Request):
        try:
            payload = await validated_auth_payload(request, IdentityUnlinkRequest)
            async with session_factory() as session:
                actor, keep_session_id = await _actor(session, request)
                result = await IdentityLinkService(session, settings_obj).unlink(
                    payload.identity_id,
                    user_id=int(actor.id),
                    keep_session_id=keep_session_id,
                )
                await session.commit()
            return JSONResponse(content=result, headers=_NO_STORE)
        except IdentityLinkError as exc:
            return _oauth_error(exc)
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("Identity unlink failed")
            return _unavailable()

    return router

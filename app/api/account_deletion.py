"""Authenticated in-app requests and public ownership proof, without login."""
import logging
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.api.desktop_auth import LinkRequestId, OpaqueSecret, auth_error_response, bearer_access_token, validated_auth_payload
from app.repositories.user_repo import UserRepository
from app.services.account_deletion_service import AccountDeletionError, AccountDeletionService, BROWSER_COOKIE
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.telegram_webapp_auth import extract_fresh_verified_webapp_user_id

logger = logging.getLogger(__name__)
HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"}


class PrepareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StartRequest(PrepareRequest):
    provider: Literal["telegram", "google", "apple"]


class ProofRequest(PrepareRequest):
    request_id: LinkRequestId
    secret: OpaqueSecret


class ConfirmRequest(ProofRequest):
    confirmation: Literal["DELETE"]


def check_origin(request, settings_obj):
    # No cookie-authenticated state-changing GETs. Reject cross-origin JSON
    # requests even if a deployment later enables permissive CORS.
    origin = request.headers.get("Origin")
    expected = urlsplit(str(request.url))
    allowed = {f"{expected.scheme}://{expected.netloc}"}
    # Reverse proxies may terminate TLS before FastAPI. Use only explicitly
    # configured origins, never untrusted forwarded headers, as alternatives.
    for name in ("PUBLIC_SITE_URL", "OAUTH_REDIRECT_BASE_URL"):
        configured = urlsplit(str(getattr(settings_obj, name, "") or ""))
        if configured.scheme == "https" and configured.netloc:
            allowed.add(f"https://{configured.netloc}")
    if origin and origin.rstrip("/") not in allowed:
        raise AccountDeletionError("deletion_origin_invalid", status_code=403)


async def deletion_actor(session, settings_obj, request):
    token = bearer_access_token(request)
    if token:
        return (await DesktopAuthService(session, settings_obj).authenticate(token)).user
    raw = request.headers.get("X-Telegram-Init-Data", "")
    telegram_id = extract_fresh_verified_webapp_user_id(
        raw if len(raw) <= 4096 else "", settings_obj.BOT_TOKEN, max_age_seconds=86400)
    if not telegram_id:
        raise AccountDeletionError("deletion_auth_required", status_code=401)
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        raise AccountDeletionError("deletion_account_not_found", status_code=404)
    return user


async def notify_deletion_request(bot, settings_obj, result):
    """Best effort notification AFTER commit; the DB queue is authoritative."""
    for admin_id in set(getattr(settings_obj, "admin_id_list", [])):
        try:
            await bot.send_message(admin_id,
                f"HSK AI: hisobni o‘chirish so‘rovi\nRaqam: {result['request_id']}\n"
                f"Muddat: {result['due_at']}\nOperator queue: scripts/process_account_deletion.py list")
        except Exception:
            # Avoid exception details from transports that may echo tokens.
            logger.warning("Account deletion notification failed")


def create_account_deletion_router(*, session_factory, settings_obj, notifier=None):
    router = APIRouter(tags=["account-deletion"])

    async def respond(request, model, operation):
        try:
            check_origin(request, settings_obj)
            payload = await validated_auth_payload(request, model)
            async with session_factory() as session:
                result = await operation(session, payload)
            return JSONResponse(result, headers=HEADERS)
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.error("Account deletion operation failed")
            return JSONResponse({"ok": False, "error": "deletion_unavailable"}, status_code=503, headers=HEADERS)

    @router.get("/api/account-deletion/providers")
    async def providers():
        return JSONResponse({"ok": True, "providers": AccountDeletionService(None, settings_obj).providers()}, headers=HEADERS)

    @router.post("/api/account-deletion/prepare")
    async def prepare(request: Request):
        async def operation(session, payload):
            user = await deletion_actor(session, settings_obj, request)
            return await AccountDeletionService(session, settings_obj).start(
                provider="session", client=f"user:{user.id}", user=user)
        return await respond(request, PrepareRequest, operation)

    @router.post("/api/account-deletion/start")
    async def start(request: Request):
        import secrets
        browser = request.cookies.get(BROWSER_COOKIE) or secrets.token_urlsafe(32)
        async def operation(session, payload):
            return await AccountDeletionService(session, settings_obj).start(
                provider=payload.provider, browser=browser,
                # A proxy may present one peer IP for all learners. Bound the
                # initiating browser plus the cross-worker global quota.
                client=f"browser:{browser}")
        response = await respond(request, StartRequest, operation)
        if response.status_code == 200:
            configured = urlsplit(str(getattr(settings_obj, "OAUTH_REDIRECT_BASE_URL", "") or ""))
            secure = request.url.scheme == "https" or (
                configured.scheme == "https" and configured.netloc == request.url.netloc)
            # Apple returns form_post cross-site. None + Secure is required
            # for its callback to carry the initiating browser's cookie.
            response.set_cookie(BROWSER_COOKIE, browser, max_age=60 * 86400, httponly=True,
                secure=secure, samesite="none" if secure else "lax", path="/")
        return response

    @router.post("/api/account-deletion/status")
    async def status(request: Request):
        async def operation(session, payload):
            return await AccountDeletionService(session, settings_obj).status(
                request_id=payload.request_id, secret=payload.secret.get_secret_value(),
                browser=request.cookies.get(BROWSER_COOKIE))
        return await respond(request, ProofRequest, operation)

    @router.post("/api/account-deletion/confirm")
    async def confirm(request: Request):
        async def operation(session, payload):
            service = AccountDeletionService(session, settings_obj)
            previous = await service.status(request_id=payload.request_id,
                secret=payload.secret.get_secret_value(), browser=request.cookies.get(BROWSER_COOKIE))
            result = await service.confirm(request_id=payload.request_id,
                secret=payload.secret.get_secret_value(), browser=request.cookies.get(BROWSER_COOKIE))
            if notifier and previous["status"] != "submitted" and result["status"] == "submitted":
                try:
                    await notifier(result)
                except Exception:
                    logger.warning("Account deletion notification failed")
            return result
        return await respond(request, ConfirmRequest, operation)

    return router

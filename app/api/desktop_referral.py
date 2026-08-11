"""Bearer-authenticated desktop adapter for the referral programme.

``ReferralService`` already owns the invite code, the referral list and the
trial-activation counter for the Telegram product. This router binds it to the
user resolved from a verified desktop session, so an invite sent from the
desktop app counts exactly like one sent from the bot.

Telegram IDs and internal user IDs are dropped before the payload leaves the
server: the desktop UI shows a name and a status, nothing more.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.repositories.user_repo import UserRepository
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.referral_service import (
    REFERRAL_TRIAL_REQUIRED_ACTIVE,
    ReferralService,
)


logger = logging.getLogger(__name__)

MAX_REFERRAL_ITEMS = 30
MIN_TIMEZONE_OFFSET = -720
MAX_TIMEZONE_OFFSET = 840


class DesktopReferralError(RuntimeError):
    def __init__(self, code: str, *, status_code: int):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def _access_token(request: Request) -> str:
    value = str(request.headers.get("Authorization", "") or "")
    scheme, separator, token = value.partition(" ")
    if separator and scheme.lower() == "bearer":
        return token.strip()
    return ""


def _timezone_offset(request: Request) -> int | None:
    raw = request.query_params.get("tz")
    if raw is None:
        return None
    try:
        offset = int(raw)
    except (TypeError, ValueError) as exc:
        raise DesktopReferralError(
            "desktop_referral_request_invalid",
            status_code=422,
        ) from exc
    if offset < MIN_TIMEZONE_OFFSET or offset > MAX_TIMEZONE_OFFSET:
        raise DesktopReferralError("desktop_referral_request_invalid", status_code=422)
    return offset


def _public_item(entry: dict[str, Any]) -> dict[str, Any]:
    """Strip identifiers the desktop UI never renders."""

    return {
        "name": str(entry.get("name") or "").strip()[:40],
        "status": str(entry.get("status") or "pending"),
        "joined_at": str(entry.get("joined_at") or ""),
        "activated_at": str(entry.get("activated_at") or ""),
        "course_level": str(entry.get("course_level") or "").strip()[:32],
        "completed_lessons": int(entry.get("completed_lessons") or 0),
        "is_paid": bool(entry.get("is_paid")),
    }


def _invite_link(bot_username: str, code: str) -> str:
    """The same deep link the bot hands out, so attribution is identical."""

    handle = str(bot_username or "").strip().lstrip("@")
    if not handle or not code:
        return ""
    return f"https://t.me/{handle}?start=ref_{code}"


def _error_response(
    error: DesktopAuthError | DesktopReferralError,
) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"ok": False, "error": error.code},
        headers={"Cache-Control": "no-store"},
    )


def create_desktop_referral_router(
    *,
    session_factory,
    settings_obj,
    service_factory: Callable[..., ReferralService] = ReferralService,
) -> APIRouter:
    router = APIRouter(tags=["desktop-referral"])

    @router.get("/api/v3/desktop/referral/overview")
    async def desktop_referral_overview(request: Request):
        try:
            if set(request.query_params) - {"tz"}:
                raise DesktopReferralError(
                    "desktop_referral_request_invalid",
                    status_code=422,
                )
            timezone_offset = _timezone_offset(request)
            async with session_factory() as session:
                context = await DesktopAuthService(session, settings_obj).authenticate(
                    _access_token(request)
                )
                user = await UserRepository(session).get_by_telegram_id(
                    int(context.user.telegram_id)
                )
                if not user:
                    raise DesktopReferralError(
                        "desktop_referral_user_not_found",
                        status_code=404,
                    )
                service = service_factory(session)
                items = await service.list_miniapp_referrals(
                    user,
                    timezone_offset_minutes=timezone_offset,
                    limit=MAX_REFERRAL_ITEMS,
                )
                trial_progress = await service.get_trial_activation_progress(user)
                await session.commit()

            rows = [_public_item(item) for item in items if isinstance(item, dict)]
            activated = sum(1 for row in rows if row["status"] == "active")
            code = str(getattr(user, "referral_code", "") or "")
            return JSONResponse(
                content={
                    "code": code,
                    "link": _invite_link(
                        getattr(settings_obj, "BOT_USERNAME", ""), code
                    ),
                    "invited": len(rows),
                    "activated": activated,
                    "trial_progress": int(trial_progress or 0),
                    "trial_required": int(REFERRAL_TRIAL_REQUIRED_ACTIVE),
                    "items": rows,
                },
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, DesktopReferralError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop referral overview failed")
            return _error_response(
                DesktopReferralError(
                    "desktop_referral_unavailable",
                    status_code=503,
                )
            )

    return router

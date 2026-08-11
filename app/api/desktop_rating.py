"""Bearer-authenticated desktop adapter for the weekly league leaderboard.

``CourseGamificationService.leaderboard`` already powers the Telegram Mini App
rating screen. This router binds it to the user resolved from a verified desktop
session so both clients read the same league, the same weekly XP window and the
same ranking, with no second implementation.

Telegram IDs are dropped before the payload leaves the server: the desktop
webview never needs them and they are the one piece of personal data in the
response that the UI does not use.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.repositories.user_repo import UserRepository
from app.services.course_gamification_service import CourseGamificationService
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService


logger = logging.getLogger(__name__)

MAX_LEADERBOARD_ITEMS = 50
MIN_TIMEZONE_OFFSET = -720
MAX_TIMEZONE_OFFSET = 840


class DesktopRatingError(RuntimeError):
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
        raise DesktopRatingError(
            "desktop_rating_request_invalid",
            status_code=422,
        ) from exc
    if offset < MIN_TIMEZONE_OFFSET or offset > MAX_TIMEZONE_OFFSET:
        raise DesktopRatingError("desktop_rating_request_invalid", status_code=422)
    return offset


def _public_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Strip personal identifiers the desktop UI does not render."""

    return {
        "rank": int(entry.get("rank") or 0),
        "name": str(entry.get("name") or "").strip()[:40],
        "username": str(entry.get("username") or "").strip()[:32],
        "xp": int(entry.get("xp") or 0),
        "league_points": int(entry.get("league_points") or 0),
        "total_xp": int(entry.get("total_xp") or 0),
        "course_level": str(entry.get("course_level") or "").strip()[:32],
        "completed_lessons": int(entry.get("completed_lessons") or 0),
        "is_paid": bool(entry.get("is_paid")),
        "is_current_user": bool(entry.get("is_current_user")),
    }


def _public_payload(result: dict[str, Any]) -> dict[str, Any]:
    entries = result.get("leaderboard")
    rows = [_public_entry(item) for item in entries if isinstance(item, dict)] if isinstance(entries, list) else []
    return {
        "rank": int(result.get("rank") or 0),
        "league": str(result.get("league") or ""),
        "league_size": int(result.get("league_size") or 0),
        "xp": int(result.get("xp") or 0),
        "weekly_xp": int(result.get("weekly_xp") or 0),
        "daily_xp": int(result.get("daily_xp") or 0),
        "streak": int(result.get("streak") or 0),
        "longest_streak": int(result.get("longest_streak") or 0),
        "week_start": str(result.get("week_start") or ""),
        "week_activity_dates": list(result.get("week_activity_dates") or []),
        "weekly_reset_day": str(result.get("weekly_reset_day") or ""),
        "weekly_reset_seconds": int(result.get("weekly_reset_seconds") or 0),
        "leaderboard": rows,
    }


def _error_response(
    error: DesktopAuthError | DesktopRatingError,
) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"ok": False, "error": error.code},
        headers={"Cache-Control": "no-store"},
    )


def create_desktop_rating_router(
    *,
    session_factory,
    settings_obj,
    service_factory: Callable[..., CourseGamificationService] = CourseGamificationService,
) -> APIRouter:
    router = APIRouter(tags=["desktop-rating"])

    @router.get("/api/v3/desktop/rating/leaderboard")
    async def desktop_rating_leaderboard(request: Request):
        try:
            unexpected = set(request.query_params) - {"tz"}
            if unexpected:
                raise DesktopRatingError(
                    "desktop_rating_request_invalid",
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
                    raise DesktopRatingError(
                        "desktop_rating_user_not_found",
                        status_code=404,
                    )
                result = await service_factory(session).leaderboard(
                    user,
                    limit=MAX_LEADERBOARD_ITEMS,
                    timezone_offset_minutes=timezone_offset,
                )
                await session.commit()
            return JSONResponse(
                content=_public_payload(result),
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, DesktopRatingError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop rating leaderboard failed")
            return _error_response(
                DesktopRatingError(
                    "desktop_rating_unavailable",
                    status_code=503,
                )
            )

    return router

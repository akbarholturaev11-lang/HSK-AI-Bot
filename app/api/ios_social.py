"""Native iOS social/gamification adapters backed by shared services."""

from __future__ import annotations
import logging
from typing import Callable
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.desktop_referral import (
    MAX_REFERRAL_ITEMS,
    _invite_link,
    _public_item,
)
from app.api.desktop_rating import (
    MAX_LEADERBOARD_ITEMS,
    DesktopRatingError,
    _access_token,
    _public_payload,
    _timezone_offset,
)
from app.repositories.user_repo import UserRepository
from app.services.course_gamification_service import CourseGamificationService
from app.services.referral_service import REFERRAL_TRIAL_REQUIRED_ACTIVE, ReferralService
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService

logger = logging.getLogger(__name__)


def create_ios_social_router(
    *,
    session_factory,
    settings_obj,
    gamification_service_factory: Callable[..., CourseGamificationService] = CourseGamificationService,
    referral_service_factory: Callable[..., ReferralService] = ReferralService,
) -> APIRouter:
    router = APIRouter(tags=["ios-social"])

    @router.get("/api/v3/ios/rating/leaderboard")
    async def ios_rating_leaderboard(request: Request):
        try:
            if set(request.query_params) - {"tz"}:
                raise DesktopRatingError("ios_rating_request_invalid", status_code=422)
            timezone_offset = _timezone_offset(request)
            async with session_factory() as session:
                context = await DesktopAuthService(session, settings_obj).authenticate(
                    _access_token(request)
                )
                user = await UserRepository(session).get_by_telegram_id(
                    int(context.user.telegram_id)
                )
                if not user:
                    raise DesktopRatingError("ios_rating_user_not_found", status_code=404)
                result = await gamification_service_factory(session).leaderboard(
                    user,
                    limit=MAX_LEADERBOARD_ITEMS,
                    timezone_offset_minutes=timezone_offset,
                )
                await session.commit()
            return JSONResponse(
                content=_public_payload(
                    result,
                    secret=str(getattr(settings_obj, "DESKTOP_AUTH_SIGNING_SECRET", "") or ""),
                ),
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, DesktopRatingError) as exc:
            return JSONResponse(
                status_code=getattr(exc, "status_code", 400),
                content={"ok": False, "error": getattr(exc, "code", "ios_rating_unavailable")},
                headers={"Cache-Control": "no-store"},
            )
        except Exception:
            logger.exception("iOS rating leaderboard failed")
            return JSONResponse(
                status_code=503,
                content={"ok": False, "error": "ios_rating_unavailable"},
                headers={"Cache-Control": "no-store"},
            )


    @router.get("/api/v3/ios/referral/overview")
    async def ios_referral_overview(request: Request):
        try:
            if set(request.query_params) - {"tz"}:
                raise DesktopRatingError("ios_referral_request_invalid", status_code=422)
            timezone_offset = _timezone_offset(request)
            async with session_factory() as session:
                context = await DesktopAuthService(session, settings_obj).authenticate(
                    _access_token(request)
                )
                user = await UserRepository(session).get_by_telegram_id(
                    int(context.user.telegram_id)
                )
                if not user:
                    raise DesktopRatingError("ios_referral_user_not_found", status_code=404)
                service = referral_service_factory(session)
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
                    "ok": True,
                    "code": code,
                    "link": _invite_link(getattr(settings_obj, "BOT_USERNAME", ""), code),
                    "invited": len(rows),
                    "activated": activated,
                    "trial_progress": int(trial_progress or 0),
                    "trial_required": int(REFERRAL_TRIAL_REQUIRED_ACTIVE),
                    "items": rows,
                },
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, DesktopRatingError) as exc:
            return JSONResponse(
                status_code=getattr(exc, "status_code", 400),
                content={"ok": False, "error": getattr(exc, "code", "ios_referral_unavailable")},
                headers={"Cache-Control": "no-store"},
            )
        except Exception:
            logger.exception("iOS referral overview failed")
            return JSONResponse(
                status_code=503,
                content={"ok": False, "error": "ios_referral_unavailable"},
                headers={"Cache-Control": "no-store"},
            )

    return router

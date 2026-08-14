"""Bearer-authenticated feature adapters for the native Android client.

The Telegram Mini App already owns the canonical implementation for practice,
mistakes, gamification, referral and voice practice. Android has no Telegram
``initData`` inside the native app, so this module only resolves the user from
the shared native access token and delegates to those same services.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Callable, TypeVar

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from app.api.desktop_practice import (
    DesktopPracticeCompleteRequest,
    DesktopPracticeError,
    DesktopPracticeStartRequest,
    MAX_DESKTOP_PRACTICE_COMPLETE_BODY_BYTES,
    _validate_selection as _validate_practice_selection,
    _validated_payload as _validated_practice_payload,
)
from app.api.desktop_rating import (
    MAX_LEADERBOARD_ITEMS,
    _public_payload as _public_rating_payload,
)
from app.api.desktop_referral import (
    MAX_REFERRAL_ITEMS,
    _invite_link,
    _public_item as _public_referral_item,
)
from app.api.desktop_voice import (
    DesktopVoiceEndRequest,
    DesktopVoiceMessageRequest,
    DesktopVoiceStartRequest,
    MAX_DESKTOP_VOICE_AUDIO_BODY_BYTES,
    _decode_audio_data_url,
    _validated_payload as _validated_voice_payload,
)
from app.repositories.user_repo import UserRepository
from app.services.course_gamification_service import CourseGamificationService
from app.services.course_miniapp_practice_service import CourseMiniAppPracticeService
from app.services.course_mistake_service import CourseMistakeService
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.referral_service import (
    REFERRAL_TRIAL_REQUIRED_ACTIVE,
    ReferralService,
)
from app.services.study_miniapp_service import StudyMiniAppService
from app.services.user_access_state_service import UserAccessState, UserAccessStateService
from app.services.voice_practice_service import (
    LANGUAGE_NAMES,
    ROLE_PROMPTS,
    VoicePracticeError,
    VoicePracticeService,
)


logger = logging.getLogger(__name__)

PayloadModel = TypeVar("PayloadModel", bound=BaseModel)
MIN_TIMEZONE_OFFSET = -720
MAX_TIMEZONE_OFFSET = 840
MAX_ANDROID_JSON_BODY_BYTES = 16 * 1024


AndroidSessionId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=8, max_length=120),
]
AndroidQuestionId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=160),
]


class AndroidFeatureError(RuntimeError):
    def __init__(self, code: str, *, status_code: int):
        super().__init__(code)
        self.code = code
        self.status_code = status_code




class AndroidMistakeReviewStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ad_supported: bool = False
    access_ref: str = Field(default="", max_length=160)


class AndroidMistakeReviewAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: AndroidSessionId
    question_id: AndroidQuestionId
    selected_index: int = Field(ge=0, le=32)


class AndroidMistakeReviewCompleteAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: AndroidQuestionId
    selected_index: int = Field(ge=0, le=32)


class AndroidMistakeReviewCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: AndroidSessionId
    answers: list[AndroidMistakeReviewCompleteAnswer] = Field(default_factory=list)


def _access_token(request: Request) -> str:
    value = str(request.headers.get("Authorization", "") or "")
    scheme, separator, token = value.partition(" ")
    if separator and scheme.lower() == "bearer":
        return token.strip()
    return ""


async def _validated_payload(
    request: Request,
    model_type: type[PayloadModel],
    *,
    max_body_bytes: int = MAX_ANDROID_JSON_BODY_BYTES,
) -> PayloadModel:
    content_type = str(request.headers.get("Content-Type", "") or "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise AndroidFeatureError("android_request_invalid", status_code=415)

    content_length = str(request.headers.get("Content-Length", "") or "").strip()
    if content_length:
        try:
            parsed_length = int(content_length)
        except ValueError as exc:
            raise AndroidFeatureError("android_request_invalid", status_code=400) from exc
        if parsed_length < 0 or parsed_length > max_body_bytes:
            raise AndroidFeatureError("android_request_too_large", status_code=413)

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > max_body_bytes:
            raise AndroidFeatureError("android_request_too_large", status_code=413)
    try:
        return model_type.model_validate_json(bytes(body))
    except (ValidationError, ValueError, TypeError) as exc:
        raise AndroidFeatureError("android_request_invalid", status_code=422) from exc


def _timezone_offset(request: Request) -> int | None:
    raw = request.query_params.get("tz")
    if raw is None:
        return None
    try:
        offset = int(raw)
    except (TypeError, ValueError) as exc:
        raise AndroidFeatureError("android_request_invalid", status_code=422) from exc
    if offset < MIN_TIMEZONE_OFFSET or offset > MAX_TIMEZONE_OFFSET:
        raise AndroidFeatureError("android_request_invalid", status_code=422)
    return offset


def _error_response(
    error: AndroidFeatureError | DesktopAuthError | DesktopPracticeError | VoicePracticeError,
) -> JSONResponse:
    return JSONResponse(
        status_code=getattr(error, "status_code", 400),
        content={"ok": False, "error": getattr(error, "code", "android_unavailable")},
        headers={"Cache-Control": "no-store"},
    )


def _service_response(result: dict[str, Any]) -> JSONResponse:
    if result.get("ok") is True:
        return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
    code = str(result.get("error") or "android_unavailable")
    status = (
        403
        if code
        in {
            "free_feature_limit_reached",
            "access_start_first",
            "ad_authorization_required",
            "course_access_blocked",
        }
        else 404
        if code in {"mistake_review_empty"}
        else 409
    )
    return JSONResponse(
        status_code=status,
        content={"ok": False, "error": code, **({"ad": result["ad"]} if "ad" in result else {})},
        headers={"Cache-Control": "no-store"},
    )


def _subscription_payload(user, profile_payload: dict[str, Any]) -> dict[str, Any]:
    state = UserAccessStateService.classify(user)
    subscription = profile_payload.get("subscription") if isinstance(profile_payload, dict) else {}
    return {
        "ok": True,
        "source": "android_subscription",
        "mode": "subscription",
        "access": {
            "state": state,
            "is_paid": state == UserAccessState.PAID,
            "expires_at": subscription.get("until") if isinstance(subscription, dict) else None,
        },
        "checkout_allowed": False,
        "read_only_reason": "android_billing_not_configured",
        "billing": {
            "provider": "google_play",
            "configured": False,
            "required_external_config": [
                "Play Console product IDs",
                "Google Play service-account credentials",
                "release signing keystore",
            ],
        },
    }


def create_android_features_router(
    *,
    session_factory,
    settings_obj,
    practice_service_factory: Callable[..., CourseMiniAppPracticeService] = CourseMiniAppPracticeService,
    mistake_service_factory: Callable[..., CourseMistakeService] = CourseMistakeService,
    voice_service_factory: Callable[..., VoicePracticeService] = VoicePracticeService,
    gamification_service_factory: Callable[..., CourseGamificationService] = CourseGamificationService,
    referral_service_factory: Callable[..., ReferralService] = ReferralService,
) -> APIRouter:
    router = APIRouter(tags=["android-features"])

    async def _context(session, request: Request):
        return await DesktopAuthService(session, settings_obj).authenticate(
            _access_token(request)
        )

    async def _user(session, request: Request):
        context = await _context(session, request)
        user = await UserRepository(session).get_by_telegram_id(
            int(context.user.telegram_id)
        )
        if not user:
            raise AndroidFeatureError("android_user_not_found", status_code=404)
        return user

    async def _telegram_id(session, request: Request) -> int:
        context = await _context(session, request)
        return int(context.user.telegram_id)

    @router.get("/api/v3/android/profile")
    async def android_profile(request: Request):
        try:
            if request.query_params:
                raise AndroidFeatureError("android_request_invalid", status_code=422)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await StudyMiniAppService(session).get_profile_payload(
                    telegram_id
                )
                await session.commit()
            return _service_response(result)
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android profile failed")
            return _error_response(
                AndroidFeatureError("android_profile_unavailable", status_code=503)
            )

    @router.get("/api/v3/android/subscription/overview")
    async def android_subscription_overview(request: Request):
        try:
            if request.query_params:
                raise AndroidFeatureError("android_request_invalid", status_code=422)
            async with session_factory() as session:
                user = await _user(session, request)
                profile = await StudyMiniAppService(session).get_profile_payload(
                    int(user.telegram_id)
                )
                await session.commit()
            return JSONResponse(
                content=_subscription_payload(user, profile),
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android subscription overview failed")
            return _error_response(
                AndroidFeatureError("android_subscription_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/practice/start")
    async def android_practice_start(request: Request):
        try:
            payload = await _validated_practice_payload(
                request,
                DesktopPracticeStartRequest,
            )
            _validate_practice_selection(payload)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await practice_service_factory(session).start(
                    telegram_id,
                    mode=payload.mode,
                    level=payload.level,
                    lang=payload.language,
                    skill=payload.skill,
                )
            return _service_response(result)
        except (DesktopAuthError, DesktopPracticeError) as exc:
            return _error_response(exc)
        except ValueError:
            return _error_response(
                AndroidFeatureError("android_practice_request_invalid", status_code=422)
            )
        except Exception:
            logger.exception("Android practice start failed")
            return _error_response(
                AndroidFeatureError("android_practice_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/practice/complete")
    async def android_practice_complete(request: Request):
        try:
            payload = await _validated_practice_payload(
                request,
                DesktopPracticeCompleteRequest,
                max_body_bytes=MAX_DESKTOP_PRACTICE_COMPLETE_BODY_BYTES,
            )
            _validate_practice_selection(payload)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await practice_service_factory(session).complete(
                    telegram_id,
                    session_id=payload.session_id,
                    mode=payload.mode,
                    level=payload.level,
                    lang=payload.language,
                    skill=payload.skill,
                    answers=[
                        {
                            "question_id": item.question_id,
                            "selected_index": int(item.selected),
                        }
                        for item in payload.answers
                    ],
                )
            return _service_response(result)
        except (DesktopAuthError, DesktopPracticeError) as exc:
            return _error_response(exc)
        except ValueError:
            return _error_response(
                AndroidFeatureError("android_practice_request_invalid", status_code=422)
            )
        except Exception:
            logger.exception("Android practice complete failed")
            return _error_response(
                AndroidFeatureError("android_practice_unavailable", status_code=503)
            )

    @router.get("/api/v3/android/mistakes")
    async def android_mistakes(request: Request):
        try:
            unexpected = set(request.query_params) - {"category", "limit", "offset"}
            if unexpected:
                raise AndroidFeatureError("android_request_invalid", status_code=422)
            category = str(request.query_params.get("category") or "").strip().lower()
            if category == "all":
                category = ""
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await mistake_service_factory(session).overview(
                    telegram_id,
                    category=category or None,
                    limit=request.query_params.get("limit", "30"),
                    offset=request.query_params.get("offset", "0"),
                )
            return _service_response(result)
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android mistakes overview failed")
            return _error_response(
                AndroidFeatureError("android_mistakes_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/mistakes/review/start")
    async def android_mistake_review_start(request: Request):
        try:
            payload = await _validated_payload(request, AndroidMistakeReviewStartRequest)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await mistake_service_factory(session).start_review(
                    telegram_id,
                    ad_supported=payload.ad_supported,
                    access_ref=payload.access_ref,
                )
            return _service_response(result)
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android mistake review start failed")
            return _error_response(
                AndroidFeatureError("android_mistakes_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/mistakes/review/answer")
    async def android_mistake_review_answer(request: Request):
        try:
            payload = await _validated_payload(request, AndroidMistakeReviewAnswerRequest)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await mistake_service_factory(session).answer_review_question(
                    telegram_id,
                    session_id=payload.session_id,
                    question_id=payload.question_id,
                    selected_index=payload.selected_index,
                )
            return _service_response(result)
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android mistake review answer failed")
            return _error_response(
                AndroidFeatureError("android_mistakes_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/mistakes/review/complete")
    async def android_mistake_review_complete(request: Request):
        try:
            payload = await _validated_payload(
                request,
                AndroidMistakeReviewCompleteRequest,
            )
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await mistake_service_factory(session).complete_review(
                    telegram_id,
                    session_id=payload.session_id,
                    answers=[
                        {
                            "question_id": item.question_id,
                            "selected_index": int(item.selected_index),
                        }
                        for item in payload.answers
                    ],
                )
            return _service_response(result)
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android mistake review complete failed")
            return _error_response(
                AndroidFeatureError("android_mistakes_unavailable", status_code=503)
            )

    @router.get("/api/v3/android/rating/leaderboard")
    async def android_rating_leaderboard(request: Request):
        try:
            if set(request.query_params) - {"tz"}:
                raise AndroidFeatureError("android_request_invalid", status_code=422)
            timezone_offset = _timezone_offset(request)
            async with session_factory() as session:
                user = await _user(session, request)
                result = await gamification_service_factory(session).leaderboard(
                    user,
                    limit=MAX_LEADERBOARD_ITEMS,
                    timezone_offset_minutes=timezone_offset,
                )
                await session.commit()
            payload = {"ok": True, **_public_rating_payload(result)}
            return JSONResponse(content=payload, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android rating leaderboard failed")
            return _error_response(
                AndroidFeatureError("android_rating_unavailable", status_code=503)
            )

    @router.get("/api/v3/android/referral/overview")
    async def android_referral_overview(request: Request):
        try:
            if set(request.query_params) - {"tz"}:
                raise AndroidFeatureError("android_request_invalid", status_code=422)
            timezone_offset = _timezone_offset(request)
            async with session_factory() as session:
                user = await _user(session, request)
                service = referral_service_factory(session)
                items = await service.list_miniapp_referrals(
                    user,
                    timezone_offset_minutes=timezone_offset,
                    limit=MAX_REFERRAL_ITEMS,
                )
                trial_progress = await service.get_trial_activation_progress(user)
                await session.commit()

            rows = [_public_referral_item(item) for item in items if isinstance(item, dict)]
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
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android referral overview failed")
            return _error_response(
                AndroidFeatureError("android_referral_unavailable", status_code=503)
            )

    @router.get("/api/v3/android/voice/status")
    async def android_voice_status(request: Request):
        try:
            if request.query_params:
                raise VoicePracticeError(
                    "ANDROID_VOICE_REQUEST_INVALID",
                    "Unexpected query parameters.",
                    422,
                )
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await voice_service_factory(session).user_status(telegram_id)
            return JSONResponse(content={"ok": True, **result}, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, VoicePracticeError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android voice status failed")
            return _error_response(
                AndroidFeatureError("android_voice_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/voice/session/start")
    async def android_voice_start(request: Request):
        try:
            payload = await _validated_voice_payload(request, DesktopVoiceStartRequest)
            if payload.language not in LANGUAGE_NAMES:
                raise VoicePracticeError(
                    "ANDROID_VOICE_REQUEST_INVALID",
                    "Unsupported language.",
                    422,
                )
            if payload.role not in ROLE_PROMPTS:
                raise VoicePracticeError("INVALID_ROLE", "Unknown conversation role.", 422)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await voice_service_factory(session).start_session(
                    telegram_id,
                    role=payload.role,
                    level=payload.level,
                    language=payload.language,
                    voice=payload.voice,
                )
            return JSONResponse(content={"ok": True, **result}, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, VoicePracticeError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android voice session start failed")
            return _error_response(
                AndroidFeatureError("android_voice_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/voice/message")
    async def android_voice_message(request: Request):
        try:
            payload = await _validated_voice_payload(
                request,
                DesktopVoiceMessageRequest,
                max_body_bytes=MAX_DESKTOP_VOICE_AUDIO_BODY_BYTES,
            )
            audio_bytes, filename = _decode_audio_data_url(payload.audio_data_url)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await voice_service_factory(session).process_message(
                    telegram_id,
                    session_id=payload.session_id,
                    audio_bytes=audio_bytes,
                    filename=filename,
                )
            return JSONResponse(content={"ok": True, **result}, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, VoicePracticeError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android voice message failed")
            return _error_response(
                AndroidFeatureError("android_voice_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/voice/session/end")
    async def android_voice_end(request: Request):
        try:
            payload = await _validated_voice_payload(request, DesktopVoiceEndRequest)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await voice_service_factory(session).end_session(
                    telegram_id,
                    payload.session_id,
                )
            return JSONResponse(content={"ok": True, **result}, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, VoicePracticeError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android voice session end failed")
            return _error_response(
                AndroidFeatureError("android_voice_unavailable", status_code=503)
            )

    return router

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
from app.services.course_ad_service import CourseAdService
from app.services.course_gamification_service import CourseGamificationService
from app.services.course_miniapp_access_service import CourseMiniAppAccessService
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
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

# Reklama turlaridan Android nimani ko'rsatishi mumkin.
#
# `app` turi HECH QAYSI kanalda berilmaydi: u desktop ilovani yuklab olishga
# chaqiradigan promo, telefonda ma'nosi yo'q va platforma tugmalari Mini App
# maketiga qurilgan.
#
# `dars_yakuni` turi ostida OBUNA tugmasi bilan chiqadi, shuning uchun u faqat
# `direct` kanalda (APK / sayt / Telegram). Google Play build'i ilova ichida
# tashqi to'lovga chaqira olmaydi.
ANDROID_AD_TYPES_BY_CHANNEL = {
    "play": ("odiy", "hamkorlik", "bot"),
    "direct": ("odiy", "hamkorlik", "bot", "dars_yakuni"),
}
# Noma'lum qiymat kelsa cheklangan to'plam ishlaydi — xato tomonga emas.
ANDROID_DEFAULT_AD_CHANNEL = "play"
ANDROID_AD_SLOTS = ("practice", "lesson_end")
# Reklama qaysi bo'limni ochishi mumkin. Mini App bilan bir xil ro'yxat.
ANDROID_AD_GATE_FEATURES = {
    "recognition",
    "memorize",
    "pronunciation",
    "placement",
    "training_test",
    "mistake_review",
    "lesson",
}


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




class AndroidAdAttemptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ad_id: int = Field(ge=1)
    watched_seconds: int = Field(default=0, ge=0, le=3600)
    feature: str = Field(default="", max_length=40)
    lesson_order: int = Field(default=0, ge=0, le=10_000)
    placement: str = Field(default="start", max_length=24)
    access_ref: str = Field(default="", max_length=160)
    attempt_token: str = Field(default="", max_length=120)


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
    content: dict[str, Any] = {"ok": False, "error": code}
    if "ad" in result:
        content["ad"] = result["ad"]
    # Kunlik limit qachon ochilishi (UTC ISO) va u umuman ochiladimi. Klient
    # buni o'z vaqt mintaqasida ko'rsatadi; server formatlangan soat bermaydi.
    for key in ("reset_at", "lifetime"):
        if key in result:
            content[key] = result[key]
    return JSONResponse(
        status_code=status,
        content=content,
        headers={"Cache-Control": "no-store"},
    )


def _bot_url(settings_obj) -> str:
    """Deep link to the bot chat where the subscription Mini App is offered."""

    username = str(getattr(settings_obj, "BOT_USERNAME", "") or "").strip().lstrip("@")
    return f"https://t.me/{username}" if username else ""


def _subscription_payload(user, profile_payload: dict[str, Any], settings_obj) -> dict[str, Any]:
    """
    Subscription is never sold inside the Android app.

    The learner is handed off to the Telegram bot, which offers the existing
    subscription Mini App; payment, pricing and activation stay in that one
    canonical flow. The client therefore gets a handoff target, never a
    checkout of its own.
    """

    state = UserAccessStateService.classify(user)
    subscription = profile_payload.get("subscription") if isinstance(profile_payload, dict) else {}
    bot_url = _bot_url(settings_obj)
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
        "read_only_reason": "android_checkout_is_in_telegram",
        "billing": {
            "provider": "telegram_bot",
            "configured": bool(bot_url),
            "bot_url": bot_url,
            "required_external_config": [] if bot_url else ["BOT_USERNAME"],
        },
    }


def create_android_features_router(
    *,
    session_factory,
    settings_obj,
    bot=None,
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

    def _ad_channel(request: Request) -> str:
        raw = str(request.query_params.get("channel") or "").strip().lower()
        return raw if raw in ANDROID_AD_TYPES_BY_CHANNEL else ANDROID_DEFAULT_AD_CHANNEL

    @router.get("/api/v3/android/ad")
    async def android_ad(request: Request):
        """Reklama ro'yxati, o'rnatilgan kanalga ruxsat etilgan turlar bilan.

        Til hisobdan olinadi, so'rovdan emas — klient o'zini boshqa tilda
        ko'rsatib boshqa reklamalarni ola olmaydi.
        """
        try:
            slot = str(request.query_params.get("slot") or "").strip().lower()
            if slot not in ANDROID_AD_SLOTS:
                slot = ANDROID_AD_SLOTS[0]
            channel = _ad_channel(request)
            allowed_types = ANDROID_AD_TYPES_BY_CHANNEL[channel]
            async with session_factory() as session:
                user = await _user(session, request)
                # Dars yakuni bloki FAQAT bepul o'quvchiga. Obunachiga server
                # ham bermaydi, klient xato hisoblasa ham reklama chiqmaydi.
                if slot == "lesson_end" and CourseMiniAppAccessService.has_unlimited_course_access(
                    user
                ):
                    raise AndroidFeatureError("course_ad_not_found", status_code=404)
                service = CourseAdService(session)
                language = CourseAdService.normalize_language(
                    getattr(user, "language", None)
                )
                ads = await service.list_active_payloads(language=language, slot=slot)
                if service.media_backup_changed:
                    await session.commit()
            ads = [ad for ad in ads if ad.get("ad_type") in allowed_types]
            if not ads:
                raise AndroidFeatureError("course_ad_not_found", status_code=404)
            return JSONResponse(
                content={"ok": True, "ads": ads, "slot": slot, "channel": channel},
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android ad listing failed")
            return _error_response(
                AndroidFeatureError("android_ad_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/ad/attempt")
    async def android_ad_attempt(request: Request):
        """Ko'rilgan reklamani yozadi va kerak bo'lsa bo'limni ochadi.

        Ochish qarorini server beradi: klient "ko'rdim" deyishi yetarli emas,
        `CourseAdService.record_view` reklama davomiyligini tekshiradi.
        """
        try:
            payload = await _validated_payload(request, AndroidAdAttemptRequest)
            feature = payload.feature.strip().lower()
            if payload.lesson_order <= 0 and feature not in ANDROID_AD_GATE_FEATURES:
                raise AndroidFeatureError("android_request_invalid", status_code=422)
            placement = CourseAdService.normalize_placement(payload.placement)
            async with session_factory() as session:
                user = await _user(session, request)
                level = str(getattr(user, "level", None) or "hsk1").strip().lower()
                service = CourseAdService(session)
                result = await service.record_view(
                    user=user,
                    ad_id=payload.ad_id,
                    level=level,
                    lesson_order=payload.lesson_order,
                    placement=placement,
                    watched_seconds=payload.watched_seconds,
                )
                if not result.get("ok"):
                    raise AndroidFeatureError(
                        str(result.get("error") or "course_ad_not_found"),
                        status_code=404,
                    )
                access_ref = payload.access_ref.strip()
                should_authorize = bool(
                    access_ref
                    and (
                        (payload.lesson_order <= 0 and feature in (ANDROID_AD_GATE_FEATURES - {"lesson"}))
                        or (payload.lesson_order > 0 and feature == "lesson")
                    )
                )
                if should_authorize:
                    try:
                        authorization = await CourseMiniAppAccessService(
                            session
                        ).record_ad_authorization(
                            user,
                            feature_key=feature,
                            access_ref=access_ref,
                            ad_id=payload.ad_id,
                            placement=placement,
                            attempt_token=payload.attempt_token.strip(),
                            level=level if feature == "lesson" else None,
                            lesson_order=payload.lesson_order if feature == "lesson" else None,
                        )
                    except ValueError:
                        authorization = {"allowed": False, "error": "invalid_access_ref"}
                    if not authorization.get("allowed"):
                        await session.rollback()
                        code = str(authorization.get("error") or "invalid_ad_authorization")
                        raise AndroidFeatureError(
                            code,
                            status_code=403 if code == "course_access_blocked" else 400,
                        )
                    result["authorization"] = {
                        "recorded": bool(authorization.get("recorded")),
                        "idempotent": bool(authorization.get("idempotent")),
                    }
                await CourseMiniAppAnalyticsService(session).record_server_event(
                    event_name="course_ad_viewed",
                    telegram_id=int(user.telegram_id),
                    user_id=getattr(user, "id", None),
                    source="android_ad",
                    level=level,
                    lesson_order=payload.lesson_order,
                    payload={
                        "ad_id": payload.ad_id,
                        "placement": placement,
                        "watched_seconds": payload.watched_seconds,
                        "feature": feature or None,
                        "access_ref": access_ref or None,
                    },
                )
                await session.commit()
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android ad attempt failed")
            return _error_response(
                AndroidFeatureError("android_ad_unavailable", status_code=503)
            )

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
                content=_subscription_payload(user, profile, settings_obj),
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android subscription overview failed")
            return _error_response(
                AndroidFeatureError("android_subscription_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/subscription/open")
    async def android_subscription_open(request: Request):
        """
        Hand the learner off to the Telegram subscription flow.

        The bot posts the existing subscription Mini App button into the user's
        chat, so pricing, payment methods and activation all stay in the one
        canonical place. Nothing here grants access: the app only learns where
        to send the learner, and the limits lift on the next server refresh
        once the payment is approved.
        """
        try:
            if request.query_params:
                raise AndroidFeatureError("android_request_invalid", status_code=422)
            bot_url = _bot_url(settings_obj)
            if not bot_url:
                raise AndroidFeatureError(
                    "android_subscription_handoff_unavailable", status_code=503
                )
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                delivered = False
                if bot is not None:
                    delivered = bool(
                        await StudyMiniAppService(session).send_subscription_menu(
                            bot, telegram_id
                        )
                    )
                await session.commit()
            # A failed delivery is not a failed handoff: the learner can still
            # open the bot and reach the same subscription menu there, so the
            # button must not dead-end on a messaging hiccup.
            return JSONResponse(
                content={"ok": True, "bot_url": bot_url, "message_sent": delivered},
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android subscription handoff failed")
            return _error_response(
                AndroidFeatureError(
                    "android_subscription_handoff_unavailable", status_code=503
                )
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
                # Bot berilmagan bo'lsa chaqiruv shakli eskisicha qoladi.
                practice = (
                    practice_service_factory(session, bot=bot)
                    if bot is not None
                    else practice_service_factory(session)
                )
                result = await practice.start(
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
                # Bot berilmagan bo'lsa chaqiruv shakli eskisicha qoladi.
                practice = (
                    practice_service_factory(session, bot=bot)
                    if bot is not None
                    else practice_service_factory(session)
                )
                result = await practice.complete(
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

"""Bearer-authenticated feature adapters for the native Android client.

The Telegram Mini App already owns the canonical implementation for practice,
mistakes, gamification, referral and voice practice. Android has no Telegram
``initData`` inside the native app, so this module only resolves the user from
the shared native access token and delegates to those same services.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Callable, Literal, TypeVar

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)

from app.api.miniapp_practice import MASTERY_FEATURES
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
    challenge_ref,
    _public_payload as _public_rating_payload,
)
from app.api.desktop_referral import (
    MAX_REFERRAL_ITEMS,
    _invite_link,
    _public_item as _public_referral_item,
)
from app.api.desktop_voice import (
    DesktopSessionId,
    DesktopVoiceEndRequest,
    DesktopVoicePronounceRequest,
    DesktopVoiceStartRequest,
    MAX_DESKTOP_VOICE_AUDIO_BODY_BYTES,
    _decode_audio_data_url,
    _validated_payload as _validated_voice_payload,
)
from app.repositories.user_repo import UserRepository
from app.services.course_ad_service import CourseAdService
from app.services.course_challenge_service import CourseChallengeService
from app.services.course_drill_signal_service import CourseDrillSignalService
from app.services.course_gamification_service import CourseGamificationService
from app.services.course_word_mastery_service import CourseWordMasteryService
from app.services.course_hsk_exam_service import CourseHskExamService
from app.services.course_access_policy_service import CourseAccessPolicyService
from app.services.course_miniapp_access_service import CourseMiniAppAccessService
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.course_miniapp_practice_service import CourseMiniAppPracticeService
from app.services.course_mistake_service import CourseMistakeService
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.entitlements.state import has_full_access, resolve_state
from app.services.miniapp_hint_service import MiniAppHintService
from app.services.ad_placement_service import (
    AD_PLACEMENTS,
    AUDIENCE_FREE_ONLY,
    AdPlacementService,
    normalize_placement as normalize_ad_placement,
)
from app.services.entitlements.gate_shadow import shadow_compare_gate
from app.services.pro_trial_service import ProTrialService
from app.services.referral_service import (
    REFERRAL_TRIAL_REQUIRED_ACTIVE,
    ReferralService,
)
from app.services.study_miniapp_service import StudyMiniAppService
from app.services.user_access_state_service import UserAccessState, UserAccessStateService
from app.services.voice_practice_service import (
    LANGUAGE_NAMES,
    MAX_TEXT_CHARS as VOICE_MAX_TEXT_CHARS,
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




class AndroidAdViewRequest(BaseModel):
    """Reports a watched ad.

    `access_ref` va `attempt_token` OLIB TASHLANDI: ular reklama ko'rib kirish
    ochish uchun edi. Endi reklama hech narsani ochmaydi, shuning uchun
    ko'rsatish faqat kunlik chegara uchun hisoblanadi.

    Eski klientlar bu maydonlarni hali yuborishi mumkin, shuning uchun model
    `extra="ignore"` bilan ishlaydi — aks holda eski build 422 olardi.
    """

    model_config = ConfigDict(extra="ignore")

    ad_id: int = Field(ge=1)
    watched_seconds: int = Field(default=0, ge=0, le=3600)
    feature: str = Field(default="", max_length=40)
    lesson_order: int = Field(default=0, ge=0, le=10_000)
    placement: str = Field(default="screen_center", max_length=24)


class AndroidVoiceMessageRequest(BaseModel):
    """One turn of a conversation: spoken or typed.

    The Mini App's call screen has a keyboard next to the microphone — a
    learner on a bus, or one whose microphone is refused, still gets to answer.
    The service has always accepted typed text; only this adapter insisted on
    audio, so the Android client had no way to offer the keyboard.

    Exactly one of the two is expected. Both would leave it ambiguous which one
    the turn should be graded on.
    """

    model_config = ConfigDict(extra="forbid")

    session_id: DesktopSessionId
    audio_data_url: str = Field(default="", max_length=MAX_DESKTOP_VOICE_AUDIO_BODY_BYTES)
    text: str = Field(default="", max_length=VOICE_MAX_TEXT_CHARS)

    @model_validator(mode="after")
    def _exactly_one_input(self) -> "AndroidVoiceMessageRequest":
        spoken = bool(self.audio_data_url.strip())
        typed = bool(self.text.strip())
        if spoken == typed:
            raise ValueError("audio_data_url yoki text — bittasi kerak")
        return self


class AndroidDrillWordsRequest(BaseModel):
    """Which words to drill next — the server chooses, the client shows them.

    The answer carries the character and whether it is a review or a new word,
    nothing else: the visible text stays on the client, so switching language
    never changes what is being asked.
    """

    model_config = ConfigDict(extra="forbid")

    feature: Literal["recognition", "pronunciation"]
    limit: int = Field(default=10, ge=1, le=30)


class AndroidChallengeCreateRequest(BaseModel):
    """Challenge another learner to the same short quiz.

    The Mini App offers this from the leaderboard; Android could see the
    league but never take part in it.
    """

    model_config = ConfigDict(extra="forbid")

    opponent_ref: str = Field(min_length=8, max_length=64)
    level: str = Field(default="", max_length=16)
    language: str = Field(default="", max_length=8)


class AndroidChallengeRespondRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["accept", "decline"]


class AndroidChallengeAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1, max_length=80)
    selected_index: int = Field(ge=0, le=32)


class AndroidChallengeSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: list[AndroidChallengeAnswer] = Field(default_factory=list, max_length=40)
    duration_seconds: int = Field(default=0, ge=0, le=7200)


class AndroidHintDismissRequest(BaseModel):
    """Yopilgan blokchaning kaliti.

    Kalitdan boshqa hech nima yuborilmaydi: yozuv kuni serverda quriladi.
    """

    model_config = ConfigDict(extra="forbid")

    hint: str = Field(min_length=1, max_length=48)


class AndroidDrillGateRequest(BaseModel):
    """May this learner open the drill right now?

    The rule is the Mini App's, not a second one: a free learner gets the
    section once (`lifetime`), and an admin "free until" period opens it for
    everyone. The count is kept by the server, so the client cannot talk its
    way in.
    """

    model_config = ConfigDict(extra="forbid")

    feature: Literal["recognition", "pronunciation"]
    ref: str = Field(default="", max_length=48)
    #: E'TIBORGA OLINMAYDI. Reklama ko'rib bo'limni ochish olib tashlandi,
    #: lekin do'kondagi eski build hali bu maydonni yuboradi va model
    #: `extra="forbid"` — maydon olib tashlansa o'sha build 422 oladi.
    access_ref: str = Field(default="", max_length=160)


class AndroidDrillMistakeEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hanzi: str = Field(min_length=1, max_length=16)
    selected: str = Field(default="", max_length=64)


class AndroidDrillResultEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hanzi: str = Field(min_length=1, max_length=16)
    correct: bool = False


class AndroidDrillReportRequest(BaseModel):
    """What happened in a client-built drill.

    Only the character the learner got wrong is reported; the question and the
    right answer are rebuilt from the server's own dictionary, so a forged
    mistake cannot be written.
    """

    model_config = ConfigDict(extra="forbid")

    feature: Literal["recognition", "memorize", "pronunciation"]
    level: str = Field(default="", max_length=16)
    language: str = Field(default="", max_length=8)
    mistakes: list[AndroidDrillMistakeEntry] = Field(default_factory=list, max_length=50)
    results: list[AndroidDrillResultEntry] = Field(default_factory=list, max_length=50)


class AndroidExamStartRequest(BaseModel):
    """Opens one HSK exam — the same exam the Mini App's test centre opens."""

    model_config = ConfigDict(extra="forbid")

    level: str = Field(min_length=1, max_length=16)
    language: str = Field(default="", max_length=8)
    access_ref: str = Field(default="", max_length=160)
    ad_supported: bool = False


class AndroidExamAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: AndroidQuestionId
    selected_index: int = Field(ge=0, le=32)


class AndroidExamCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: AndroidSessionId
    level: str = Field(default="", max_length=16)
    language: str = Field(default="", max_length=8)
    answers: list[AndroidExamAnswer] = Field(default_factory=list)


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
            "invalid_ad_authorization",
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
    exam_service_factory: Callable[..., CourseHskExamService] = CourseHskExamService,
    referral_service_factory: Callable[..., ReferralService] = ReferralService,
    challenge_service_factory: Callable[..., CourseChallengeService] = (
        CourseChallengeService
    ),
    mastery_service_factory: Callable[..., CourseWordMasteryService] = (
        CourseWordMasteryService
    ),
    drill_service_factory: Callable[..., CourseDrillSignalService] = (
        CourseDrillSignalService
    ),
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
        """Shu joyda ko'rsatilishi mumkin bo'lgan reklamalar.

        Joylar Mini App'nikining o'zi va faqat ikkitasi: dars yakuni va ekran
        markazi. Mashq sessiyalaridagi reklama OLIB TASHLANDI, va u bilan
        birga "reklama ko'rib bo'limni ochish" ham.

        Do'kondagi eski build hali `slot=practice` so'raydi. Unga 404
        beriladi: o'sha build 404 ni "reklama yo'q" deb o'qiydi va obuna
        yo'liga o'tadi — ya'ni eski ilova ham xato ko'rsatmasdan ishlaydi.

        Bitta reklama emas, RO'YXAT qaytariladi va kanal filtri ro'yxatga
        qo'llanadi. Sababi aniq: serverda bitta reklama tanlanib, keyin kanal
        filtri unga tushsa, `play` build'i `dars_yakuni` tanlangan kunlarda
        oddiy reklamalar bor bo'la turib reklamasiz qolardi.

        Til hisobdan olinadi, so'rovdan emas — klient o'zini boshqa tilda
        ko'rsatib boshqa reklamalarni ola olmaydi.
        """
        try:
            slot = str(request.query_params.get("slot") or "").strip().lower()
            channel = _ad_channel(request)
            allowed_types = ANDROID_AD_TYPES_BY_CHANNEL[channel]

            async with session_factory() as session:
                # Autentifikatsiya HAR DOIM birinchi: imzosiz chaqiruv 404
                # emas, 401 olishi kerak — aks holda javob kodining o'zi
                # ma'lumot bo'lib qoladi.
                user = await _user(session, request)

                if slot not in AD_PLACEMENTS:
                    raise AndroidFeatureError("course_ad_not_found", status_code=404)

                # Joy sozlamasi, auditoriya va KUNLIK CHEGARA — hammasi
                # serverda, Mini App bilan bir xil qoida bo'yicha. Chegara
                # qurilmaga emas, Telegram akkauntga: telefonda ikkitasini
                # ko'rgan odamda desktopda nol qoladi.
                placements = AdPlacementService(session)
                status = await placements.status(user, placement=slot, client="android")
                if not status.get("enabled"):
                    raise AndroidFeatureError("course_ad_not_found", status_code=404)
                remaining = status.get("remaining")
                if remaining is not None and remaining <= 0:
                    raise AndroidFeatureError("course_ad_not_found", status_code=404)

                rule = (await placements.get_settings()).rule(slot)
                if rule.audience == AUDIENCE_FREE_ONLY and has_full_access(
                    resolve_state(user)
                ):
                    raise AndroidFeatureError("course_ad_not_found", status_code=404)

                service = placements.ads
                ads = []
                for ad in await placements.list_for_placement(
                    slot, language=getattr(user, "language", None)
                ):
                    payload = service.payload(ad)
                    payload["placement"] = slot
                    payload["skip_after_seconds"] = rule.skip_after_seconds
                    ads.append(payload)
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

    @router.post("/api/v3/android/ad/view")
    async def android_ad_view(request: Request):
        """Reklama ko'rilganini yozadi.

        Ilgari bu yerda `feature` MAJBURIY edi va u reklama qaysi bo'limni
        ochishini bildirardi. Reklama endi hech narsani ochmaydi, shuning
        uchun talab ham olib tashlandi: ko'rsatish faqat kunlik chegara uchun
        hisoblanadi va `feature` ixtiyoriy tashxis maydoni bo'lib qoldi.

        Yozuv `AdPlacementService` orqali ketadi, `CourseAdService` orqali
        EMAS: ikkinchisi joy nomini eski `start/middle/end` ro'yxati bo'yicha
        normalizatsiya qiladi va `screen_center` ni jimgina `start` ga
        aylantirib yuborardi — ya'ni Android ko'rsatishlari kunlik chegaraga
        umuman qo'shilmasdi.
        """
        try:
            payload = await _validated_payload(request, AndroidAdViewRequest)
            feature = payload.feature.strip().lower()
            placement = normalize_ad_placement(payload.placement)
            async with session_factory() as session:
                user = await _user(session, request)
                level = str(getattr(user, "level", None) or "hsk1").strip().lower()
                result = await AdPlacementService(session).record_view(
                    user,
                    placement=placement,
                    ad_id=payload.ad_id,
                    watched_seconds=payload.watched_seconds,
                    level=level,
                    lesson_order=payload.lesson_order,
                )
                # `record_view` withholds "ok" for two different reasons: the
                # ad is missing (an error) or it was not watched long enough
                # (not an error — the learner simply stopped). Keep them apart.
                if result.get("error"):
                    raise AndroidFeatureError(str(result["error"]), status_code=404)
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
                    },
                )
                await session.commit()
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android ad view failed")
            return _error_response(
                AndroidFeatureError("android_ad_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/trial/start")
    async def android_trial_start(request: Request):
        """7 kunlik bepul Pro — Android'da ham.

        Trial XARID EMAS, shuning uchun `play` build'ida ham taklif qilinadi:
        do'kon qoidasi ilova ichida tashqi TO'LOVni taqiqlaydi, bepul sinovni
        emas.
        """
        try:
            async with session_factory() as session:
                user = await _user(session, request)
                result = await ProTrialService(session).start(
                    user, source="android_trial", client="android"
                )
                if not result.get("ok"):
                    return JSONResponse(
                        status_code=409,
                        content=result,
                        headers={"Cache-Control": "no-store"},
                    )
                await session.commit()
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android trial start failed")
            return _error_response(
                AndroidFeatureError("android_trial_unavailable", status_code=503)
            )

    @router.get("/api/v3/android/trial/status")
    async def android_trial_status(request: Request):
        try:
            async with session_factory() as session:
                user = await _user(session, request)
                verdict = await ProTrialService(session).eligibility(user)
            return JSONResponse(
                content={"ok": True, "trial": verdict},
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android trial status failed")
            return _error_response(
                AndroidFeatureError("android_trial_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/hints/dismiss")
    async def android_hint_dismiss(request: Request):
        """Tushuntirish blokchasi yopildi — Android'da ham.

        Mini App bilan bir xil yozuv, bir xil jadval: telefonda yopilgan
        blokcha Mini App'da qayta chiqmaydi. "Bitta boshqaruv, bir nechta
        qurilma" aynan shu.
        """
        try:
            payload = await _validated_payload(request, AndroidHintDismissRequest)
            async with session_factory() as session:
                user = await _user(session, request)
                saved = await MiniAppHintService(session).dismiss(
                    user, payload.hint, client="android"
                )
                if saved:
                    await session.commit()
            return JSONResponse(
                content={"ok": True, "saved": saved},
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android hint dismiss failed")
            return _error_response(
                AndroidFeatureError("android_request_invalid", status_code=422)
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
                    access_ref=payload.access_ref,
                    ad_supported=payload.ad_supported,
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
                    access_ref=payload.access_ref,
                    ad_supported=payload.ad_supported,
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

    @router.post("/api/v3/android/exams/start")
    async def android_exam_start(request: Request):
        """One HSK exam, from the same service the Mini App's test centre uses.

        Android had only the ten-question level drill here, so the two clients
        handed out different tests under the same name. This delegates to
        `CourseHskExamService`, which owns the exam material, the shuffle seed
        and the daily allowance, so both clients sit the same exam.
        """
        try:
            payload = await _validated_payload(request, AndroidExamStartRequest)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await exam_service_factory(session).start(
                    telegram_id,
                    level=payload.level,
                    lang=payload.language,
                    access_ref=payload.access_ref,
                    ad_supported=payload.ad_supported,
                )
            return _service_response(result)
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except ValueError:
            return _error_response(
                AndroidFeatureError("android_exam_request_invalid", status_code=422)
            )
        except Exception:
            logger.exception("Android exam start failed")
            return _error_response(
                AndroidFeatureError("android_exam_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/exams/complete")
    async def android_exam_complete(request: Request):
        try:
            payload = await _validated_payload(
                request,
                AndroidExamCompleteRequest,
                max_body_bytes=MAX_DESKTOP_PRACTICE_COMPLETE_BODY_BYTES,
            )
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await exam_service_factory(session).complete(
                    telegram_id,
                    session_id=payload.session_id,
                    answers=[
                        {
                            "question_id": item.question_id,
                            "selected_index": int(item.selected_index),
                        }
                        for item in payload.answers
                    ],
                    # Empty means "whatever the session was started with": the
                    # service only uses these to catch a level or language that
                    # changed mid-exam.
                    level=payload.level or None,
                    lang=payload.language or None,
                )
            return _service_response(result)
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except ValueError:
            return _error_response(
                AndroidFeatureError("android_exam_request_invalid", status_code=422)
            )
        except Exception:
            logger.exception("Android exam complete failed")
            return _error_response(
                AndroidFeatureError("android_exam_unavailable", status_code=503)
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
            payload = {
                "ok": True,
                **_public_rating_payload(
                    result,
                    secret=str(
                        getattr(settings_obj, "DESKTOP_AUTH_SIGNING_SECRET", "") or ""
                    ),
                ),
            }
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
            payload = await _validated_payload(
                request,
                AndroidVoiceMessageRequest,
                max_body_bytes=MAX_DESKTOP_VOICE_AUDIO_BODY_BYTES,
            )
            typed = payload.text.strip()
            if typed:
                audio_bytes, filename = b"", ""
            else:
                audio_bytes, filename = _decode_audio_data_url(payload.audio_data_url)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await voice_service_factory(session).process_message(
                    telegram_id,
                    session_id=payload.session_id,
                    audio_bytes=audio_bytes,
                    filename=filename,
                    text=typed,
                )
            return JSONResponse(content={"ok": True, **result}, headers={"Cache-Control": "no-store"})
        # A malformed turn is the caller's mistake, not an outage: it must not
        # be reported as "voice unavailable".
        except (DesktopAuthError, AndroidFeatureError, VoicePracticeError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android voice message failed")
            return _error_response(
                AndroidFeatureError("android_voice_unavailable", status_code=503)
            )

    @router.get("/api/v3/android/challenges")
    async def android_challenges(request: Request):
        try:
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await challenge_service_factory(session).list_for_user(telegram_id)
            return _service_response(result)
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android challenge list failed")
            return _error_response(
                AndroidFeatureError("android_challenge_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/challenges")
    async def android_challenge_create(request: Request):
        try:
            payload = await _validated_payload(request, AndroidChallengeCreateRequest)
            async with session_factory() as session:
                user = await _user(session, request)
                telegram_id = int(user.telegram_id)
                # The reference only means something inside the caller's own
                # leaderboard, which is exactly who they are allowed to
                # challenge — the same reach the Mini App gives them.
                board = await gamification_service_factory(session).leaderboard(
                    user,
                    limit=MAX_LEADERBOARD_ITEMS,
                )
                secret = str(
                    getattr(settings_obj, "DESKTOP_AUTH_SIGNING_SECRET", "") or ""
                )
                opponent_id = 0
                for row in board.get("leaderboard") or []:
                    if not isinstance(row, dict):
                        continue
                    if challenge_ref(row.get("telegram_id"), secret) == payload.opponent_ref:
                        opponent_id = int(row.get("telegram_id") or 0)
                        break
                if opponent_id <= 0:
                    raise AndroidFeatureError(
                        "challenge_opponent_not_found", status_code=404
                    )
                result = await challenge_service_factory(session).create(
                    telegram_id,
                    opponent_telegram_id=opponent_id,
                    level=payload.level,
                    lang=payload.language,
                    bot=bot,
                )
                await session.commit()
            return _service_response(result)
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android challenge create failed")
            return _error_response(
                AndroidFeatureError("android_challenge_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/challenges/{challenge_id}/respond")
    async def android_challenge_respond(challenge_id: int, request: Request):
        try:
            payload = await _validated_payload(request, AndroidChallengeRespondRequest)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await challenge_service_factory(session).respond(
                    telegram_id,
                    int(challenge_id),
                    payload.action,
                    bot=bot,
                )
                await session.commit()
            return _service_response(result)
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android challenge respond failed")
            return _error_response(
                AndroidFeatureError("android_challenge_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/challenges/{challenge_id}/start")
    async def android_challenge_start(challenge_id: int, request: Request):
        try:
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await challenge_service_factory(session).start(
                    telegram_id,
                    int(challenge_id),
                )
                await session.commit()
            return _service_response(result)
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android challenge start failed")
            return _error_response(
                AndroidFeatureError("android_challenge_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/challenges/{challenge_id}/submit")
    async def android_challenge_submit(challenge_id: int, request: Request):
        try:
            payload = await _validated_payload(request, AndroidChallengeSubmitRequest)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await challenge_service_factory(session).submit(
                    telegram_id,
                    int(challenge_id),
                    [
                        {
                            "question_id": answer.question_id,
                            "selected_index": answer.selected_index,
                        }
                        for answer in payload.answers
                    ],
                    duration_seconds=payload.duration_seconds,
                    bot=bot,
                )
                await session.commit()
            return _service_response(result)
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android challenge submit failed")
            return _error_response(
                AndroidFeatureError("android_challenge_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/practice/gate")
    async def android_drill_gate(request: Request):
        """Mini App ochadigan AYNI eshik.

        Ilgari bu yerda ikkita qo'shimcha yo'l bor edi va ikkalasi ham endi
        noto'g'ri:

        * `access_ref` bilan "reklama ko'rdim, ochib yubor" — reklama endi
          hech narsani ochmaydi, u faqat ko'rsatiladi;
        * "ko'rsatadigan reklama yo'q ekan, bo'limni bepul ochamiz" — bu
          mashq reklamalari olib tashlangach bepul foydalanuvchiga Android'da
          cheksiz mashq berardi, Mini App'da esa o'sha odam paywall ko'rardi.

        Endi javob Mini App'nikining o'zi: bepul urinish sarflanadi, tugagan
        bo'lsa 403 va paywall. Trialni klient `trial/status` dan biladi.
        """
        try:
            payload = await _validated_payload(request, AndroidDrillGateRequest)
            feature = payload.feature
            async with session_factory() as session:
                user = await _user(session, request)
                access = CourseMiniAppAccessService(session)

                # "Free until" is a course-wide gift; it must not quietly cost
                # the learner their one free run of the section.
                policy = await CourseAccessPolicyService(session).get_policy()
                if getattr(user, "status", "") != "blocked" and policy.free_active:
                    return JSONResponse(
                        content={
                            "ok": True,
                            "allowed": True,
                            "is_paid": access.is_paid_user(user),
                            "policy_free": True,
                        },
                        headers={"Cache-Control": "no-store"},
                    )

                result = await access.consume_daily_use(
                    user,
                    feature_key=feature,
                    ref=payload.ref.strip() or None,
                    lifetime=True,
                    notify_bot=bot,
                )
                # The central engine answers the same question alongside, and
                # the difference is recorded. It decides nothing here yet.
                await shadow_compare_gate(
                    session, user=user, feature=feature, legacy=result, client="android"
                )
                if not result.get("allowed"):
                    await session.commit()
                    return JSONResponse(
                        status_code=403,
                        content={
                            "ok": False,
                            "error": result.get("error") or "free_feature_limit_reached",
                            "is_paid": bool(result.get("is_paid", False)),
                            **result,
                            "reset_at": result.get("reset_at"),
                            # Shakl SAQLANADI, javobi esa endi doim "yo'q":
                            # do'kondagi eski build shu kalitni o'qiydi va
                            # bo'lmagan reklamani kutib qolmasligi kerak.
                            "ad": {"available": False, "limited": False},
                        },
                        headers={"Cache-Control": "no-store"},
                    )
                await session.commit()
            return JSONResponse(
                content={
                    "ok": True,
                    "allowed": True,
                    "is_paid": bool(result.get("is_paid", False)),
                    "remaining": result.get("remaining"),
                },
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android drill gate failed")
            return _error_response(
                AndroidFeatureError("android_practice_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/practice/words")
    async def android_drill_words(request: Request):
        """The words the learner is due to drill, chosen by the server.

        Android used to build these sections from a different generator than
        the Mini App, so the same learner practised two different sets. This is
        the Mini App's own adviser; an empty list is not a failure — the client
        falls back to its dictionary and the drill still runs.
        """
        try:
            payload = await _validated_payload(request, AndroidDrillWordsRequest)
            async with session_factory() as session:
                user = await _user(session, request)
                plan = await mastery_service_factory(session).drill_words(
                    user,
                    skill=payload.feature,
                    limit=payload.limit,
                )
                await session.commit()
            return JSONResponse(
                content={"ok": True, **plan},
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android drill words failed")
            return _error_response(
                AndroidFeatureError("android_practice_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/practice/report")
    async def android_drill_report(request: Request):
        """What a client-built drill produced: mistakes and review outcomes."""
        try:
            payload = await _validated_payload(request, AndroidDrillReportRequest)
            async with session_factory() as session:
                user = await _user(session, request)
                recorded = 0
                if payload.mistakes:
                    recorded = await drill_service_factory(session).record(
                        user,
                        feature=payload.feature,
                        level=payload.level or str(getattr(user, "level", "") or ""),
                        language=payload.language
                        or str(getattr(user, "language", "") or ""),
                        entries=[
                            {"hanzi": entry.hanzi, "selected": entry.selected}
                            for entry in payload.mistakes
                        ],
                    )
                scheduled = 0
                if payload.results and payload.feature in MASTERY_FEATURES:
                    scheduled = await mastery_service_factory(session).record_drill(
                        user,
                        skill=payload.feature,
                        results=[
                            {"hanzi": entry.hanzi, "correct": entry.correct}
                            for entry in payload.results
                        ],
                    )
                await session.commit()
            return JSONResponse(
                content={"ok": True, "recorded": recorded, "scheduled": scheduled},
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, AndroidFeatureError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android drill report failed")
            return _error_response(
                AndroidFeatureError("android_practice_unavailable", status_code=503)
            )

    @router.post("/api/v3/android/voice/pronounce")
    async def android_voice_pronounce(request: Request):
        """Score one spoken phrase.

        Starter 0 asks the learner to repeat after the teacher, and the Mini
        App checks what they actually said before awarding the speaking bonus.
        Android had no way to ask, so the step was a button that believed
        anyone who pressed it.
        """
        try:
            payload = await _validated_voice_payload(
                request,
                DesktopVoicePronounceRequest,
                max_body_bytes=MAX_DESKTOP_VOICE_AUDIO_BODY_BYTES,
            )
            audio_bytes, filename = _decode_audio_data_url(payload.audio_data_url)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await voice_service_factory(session).score_pronunciation(
                    telegram_id,
                    target=payload.target,
                    target_pinyin=payload.target_pinyin,
                    audio_bytes=audio_bytes,
                    filename=filename,
                    language=payload.language,
                    level=payload.level,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, AndroidFeatureError, VoicePracticeError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Android voice pronounce failed")
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

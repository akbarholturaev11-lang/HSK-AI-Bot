"""Browser-only learner PWA login/session transport; disabled until configured.

This router never authenticates a legacy Telegram course endpoint. Client PWA
routes must explicitly resolve the actor and enforce CSRF on state mutation.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, ValidationError

from app.services.native_oauth_service import NativeOAuthError, available_providers
from app.services.identity_link_service import IdentityLinkError
from app.services.desktop_auth_service import DesktopAuthError
from app.services.pwa_auth_service import (
    PWA_OAUTH_AGE_SECONDS,
    PWA_OAUTH_COOKIE,
    PWA_TELEGRAM_COOKIE,
    PWA_SESSION_COOKIE,
    PWA_SESSION_AGE_SECONDS,
    PwaAuthError,
    PwaAuthService,
    require_same_origin,
    require_pwa_enabled,
)

_NO_STORE = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


class PwaLoginStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["google", "apple"]
    language: Literal["uz", "ru", "tj"] | None = None


class PwaTelegramStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Literal["uz", "ru", "tj"] | None = None


class PwaTelegramClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    link_request_id: UUID


class PwaMistakeStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ad_supported: Literal[False] = False
    access_ref: str
    category: Literal["all", "word", "grammar", "character", "pronunciation"] | None = None
    formats: list[str] | None = None
    language: Literal["uz", "ru", "tj"] | None = None


class PwaMistakeAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    question_id: str
    selected_index: int | list[str]


class PwaMistakeComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    answers: list[dict]


class PwaExamStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    level: str
    lang: Literal["uz", "ru", "tj"]
    access_ref: str
    ad_supported: Literal[False] = False


class PwaExamComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    answers: list[dict]


class PwaOnboardingFinish(BaseModel):
    model_config = ConfigDict(extra="forbid")
    level: str
    goal: str
    daily_minutes: int
    start_mode: str
    language: Literal["uz", "ru", "tj"]
    timezone_offset_minutes: int
    activation_variant: str | None = None


class PwaVoiceStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str
    voice: Literal["female", "male"] = "female"
    level: str | None = None
    language: Literal["uz", "ru", "tj"] | None = None


class PwaVoiceEnd(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str


class PwaLanguagePreference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Literal["uz", "ru", "tj"]


class PwaGamificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timezone_offset_minutes: int


class PwaCheckoutContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str | None = None
    mode: str | None = "subscription"
    plan: str | None = None
    method: str | None = None
    attempt_id: str | None = None
    campaign_id: int | None = None
    feedback_id: int | None = None


class PwaCheckoutQuote(PwaCheckoutContext):
    plan_type: str
    payment_method: str
    card_country: str | None = None
    card_bank: str | None = None


class PwaCheckoutSubmit(PwaCheckoutQuote):
    screenshot_data_url: str


class PwaCheckoutPaymentStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payment_id: int


class PwaCheckoutEvent(PwaCheckoutContext):
    stage: Literal["payment_instructions_viewed", "payment_receipt_selected"]
    plan_type: str | None = None
    payment_method: str | None = None

class PwaFeedbackPrepare(BaseModel):
    """No user, identity or campaign selector is supplied by the browser."""
    model_config = ConfigDict(extra="forbid")


class PwaReleaseFeedbackReply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    campaign_id: int
    rating: int
    comment_text: str | None = None


class PwaReleaseFeedbackComment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    campaign_id: int
    comment_text: str


class PwaOrdinaryFeedbackSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feedback_id: int
    liked_code: str | None = None
    liked_sub_code: str | None = None
    liked_other_text: str | None = None
    disliked_code: str | None = None
    disliked_detail_text: str | None = None
    paid_code: str | None = None
    paid_sub_code: str | None = None
    paid_other_text: str | None = None




def _pwa_feedback_choices(language: str, *, paid: bool) -> dict:
    """Expose Telegram's existing localized choice contract, not a second UI catalog.

    Read-only metadata; no callback payload, Telegram auth or reward authority.
    The server still validates all submitted codes against the same dictionaries.
    """
    from app.bot.keyboards.feedback import (
        LIKED_OPTIONS, DISLIKED_OPTIONS, LIKE_SUB_OPTIONS, PAID_OPTIONS,
        PAID_SUB_POSITIVE, PAID_SUB_NEGATIVE,
        feedback_like_label, feedback_dislike_label,
        feedback_sub_label, feedback_paid_label,
    )
    from app.bot.handlers.feedback import DISLIKE_DETAIL_REQUIRED_CODES

    lang = language if language in {"uz", "ru", "tj"} else "ru"

    def choices(codes, label):
        return [{"code":code, "label":label(code, lang)} for code in codes]

    if paid:
        return {
            "paid": choices(PAID_OPTIONS, feedback_paid_label),
            "paid_sub_positive": choices(PAID_SUB_POSITIVE, feedback_sub_label),
            "paid_sub_negative": choices(PAID_SUB_NEGATIVE, feedback_sub_label),
        }
    return {
        "liked": choices(LIKED_OPTIONS, feedback_like_label),
        "liked_sub": {
            code: choices(codes, feedback_sub_label)
            for code, codes in LIKE_SUB_OPTIONS.items()
        },
        "disliked": choices(DISLIKED_OPTIONS, feedback_dislike_label),
        "disliked_detail_required": sorted(DISLIKE_DETAIL_REQUIRED_CODES | {"other"}),
    }


def _pwa_feedback_prompt_eligible(user, service, now) -> bool:
    """Share the original bot's join/activity gates across PWA read and prepare.

    PWA deliberately does not require an active Telegram transport: a verified
    Google/Apple-only learner has the same canonical eligibility.
    """
    from app.services.bot_feedback_service import (
        FEEDBACK_ACTIVE_WINDOW, FEEDBACK_JOIN_DELAY,
    )

    joined = service._aware(user.created_at)
    active = service._aware(user.last_active_at)
    return bool(
        user.status != "blocked"
        and joined is not None and joined <= now - FEEDBACK_JOIN_DELAY
        and active is not None and active >= now - FEEDBACK_ACTIVE_WINDOW
    )


async def _small_json(request: Request, model, *, max_bytes: int = 1024):
    if request.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
        raise PwaAuthError("pwa_request_invalid", status_code=415)
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > max_bytes:
            raise PwaAuthError("pwa_request_invalid", status_code=413)
    try:
        return model.model_validate_json(bytes(body))
    except ValidationError:
        raise PwaAuthError("pwa_request_invalid", status_code=422)


def _error(exc: PwaAuthError) -> JSONResponse:
    return JSONResponse(
        {"ok": False, "error": exc.code},
        status_code=exc.status_code, headers=_NO_STORE,
    )


def _clear_cookie(response: JSONResponse, name: str) -> None:
    response.delete_cookie(name, path="/", secure=True, httponly=True, samesite="lax")


def create_pwa_auth_router(*, session_factory, settings_obj, bot=None) -> APIRouter:
    router = APIRouter(tags=["pwa-auth"])

    @router.get("/iphone-pwa/sw.js")
    async def iphone_pwa_service_worker():
        # The worker controls only the learner PWA's same-origin route subtree.
        return FileResponse(
            "app/static/iphone-pwa-sw.js", media_type="application/javascript",
            headers={**_NO_STORE, "Service-Worker-Allowed": "/iphone-pwa/",
                     "X-Content-Type-Options": "nosniff"},
        )

    # A login-only source-aligned shell; protected course routes are P2.
    # Do not serve it until a verified provider origin is configured.
    @router.get("/iphone-pwa")
    async def login_page():
        try:
            require_pwa_enabled(settings_obj)
            return FileResponse(
                "app/static/iphone-pwa-login.html", media_type="text/html",
                headers={**_NO_STORE,
                    "Content-Security-Policy": (
                        "default-src 'none'; script-src 'self'; "
                        "style-src 'self' 'unsafe-inline'; connect-src 'self'; "
                        "img-src 'self'; frame-ancestors 'none'; form-action 'none'; "
                        "base-uri 'none'"
                    ),
                    "X-Content-Type-Options": "nosniff",
                },
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.get("/iphone-pwa/course")
    async def learner_course_page(request: Request):
        """Reuse the original course HTML for browser learners, never a clone.

        The source course scripts retain Telegram-only mutations until each
        endpoint gets a dedicated canonical PWA adapter. A valid PWA session
        is mandatory even to render this browser-only course entry.
        """
        try:
            require_pwa_enabled(settings_obj)
            async with session_factory() as db:
                await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
            return FileResponse(
                "app/static/course-v3.html",
                media_type="text/html",
                headers={
                    **_NO_STORE,
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                },
            )
        except PwaAuthError as exc:
            if exc.code == "pwa_session_required":
                return RedirectResponse(
                    "/iphone-pwa", status_code=303, headers=_NO_STORE,
                )
            return _error(exc)

    @router.get("/iphone-pwa/practice/recognition")
    async def learner_recognition_page(request: Request):
        """Re-use the original recognition screen after canonical login."""
        try:
            require_pwa_enabled(settings_obj)
            async with session_factory() as db:
                await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
            return FileResponse(
                "app/static/course_v3_recognition.html",
                media_type="text/html",
                headers={
                    **_NO_STORE,
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                },
            )
        except PwaAuthError as exc:
            if exc.code == "pwa_session_required":
                return RedirectResponse(
                    "/iphone-pwa", status_code=303, headers=_NO_STORE,
                )
            return _error(exc)

    @router.get("/iphone-pwa/practice/memorize")
    async def learner_memorize_page(request: Request):
        """Serve the original memorization screen to one verified browser actor."""
        try:
            require_pwa_enabled(settings_obj)
            async with session_factory() as db:
                await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
            return FileResponse(
                "app/static/course_v3_memorize.html",
                media_type="text/html",
                headers={
                    **_NO_STORE,
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                },
            )
        except PwaAuthError as exc:
            if exc.code == "pwa_session_required":
                return RedirectResponse(
                    "/iphone-pwa", status_code=303, headers=_NO_STORE,
                )
            return _error(exc)

    @router.get("/iphone-pwa/practice/pronunciation")
    async def learner_pronunciation_page(request: Request):
        """Re-use the canonical pronunciation UI with browser-only identity."""
        try:
            require_pwa_enabled(settings_obj)
            async with session_factory() as db:
                await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
            return FileResponse(
                "app/static/course_v3_pronunciation.html",
                media_type="text/html",
                headers={**_NO_STORE,
                         "X-Content-Type-Options": "nosniff",
                         "X-Frame-Options": "DENY"},
            )
        except PwaAuthError as exc:
            if exc.code == "pwa_session_required":
                return RedirectResponse(
                    "/iphone-pwa", status_code=303, headers=_NO_STORE,
                )
            return _error(exc)

    @router.post("/api/v3/pwa/voice/pronounce")
    async def pwa_pronunciation_score(request: Request):
        """Canonical voice scoring for a verified PWA actor, never fake initData.

        MediaRecorder's Safari audio/mp4 and supported Telegram browser formats
        use the existing server VoicePracticeService and its real AI budget.
        """
        from app.services.voice_practice_service import (
            MAX_AUDIO_BYTES, VoicePracticeError, VoicePracticeService,
        )

        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            mime = request.headers.get("Content-Type", "").split(";", 1)[0].lower()
            if mime != "multipart/form-data":
                raise PwaAuthError("pwa_request_invalid", status_code=415)
            # Enforce an upload ceiling BEFORE running Starlette's form parser,
            # including requests with no explicit Content-Length.
            try:
                length = int(request.headers.get("Content-Length", ""))
            except (TypeError, ValueError):
                raise PwaAuthError("pwa_request_invalid", status_code=411)
            if length < 1 or length > MAX_AUDIO_BYTES + 16384:
                raise PwaAuthError("pwa_request_invalid", status_code=413)

            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                try:
                    form = await request.form(
                        max_files=1, max_fields=4, max_part_size=2048,
                    )
                except Exception as exc:
                    raise PwaAuthError("pwa_request_invalid", status_code=422) from exc
                if set(form.keys()) - {"target", "target_pinyin", "audio"}:
                    # Level and language are read from the verified account,
                    # never from an anonymous browser field.
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                if any(len(form.getlist(key)) != 1 for key in ("target", "audio")):
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                target = form.get("target")
                pinyin = form.get("target_pinyin", "")
                audio = form.get("audio")
                if (not isinstance(target, str) or not (1 <= len(target) <= 120)
                        or not isinstance(pinyin, str) or len(pinyin) > 240
                        or not audio or not hasattr(audio, "read")):
                    raise PwaAuthError("pwa_request_invalid", status_code=422)

                kind = (getattr(audio, "content_type", "") or "").split(";", 1)[0].lower()
                extensions = {
                    "audio/webm": "webm", "audio/mp4": "mp4",
                    "audio/ogg": "ogg", "audio/mpeg": "mp3",
                    "audio/wav": "wav",
                }
                ext = extensions.get(kind)
                if not ext:
                    raise PwaAuthError("pwa_request_invalid", status_code=415)
                audio_bytes = await audio.read(MAX_AUDIO_BYTES + 1)
                if not audio_bytes or len(audio_bytes) > MAX_AUDIO_BYTES:
                    raise PwaAuthError("pwa_request_invalid", status_code=413)
                signatures = {
                    "webm": audio_bytes.startswith(b"\x1a\x45\xdf\xa3"),
                    "mp4": len(audio_bytes) >= 12 and audio_bytes[4:8] == b"ftyp",
                    "ogg": audio_bytes.startswith(b"OggS"),
                    "mp3": audio_bytes.startswith(b"ID3") or audio_bytes[:2] in (
                        b"\xff\xfb", b"\xff\xf3", b"\xff\xf2",
                    ),
                    "wav": (len(audio_bytes) >= 12 and audio_bytes[:4] == b"RIFF"
                            and audio_bytes[8:12] == b"WAVE"),
                }
                if not signatures.get(ext):
                    raise PwaAuthError("pwa_request_invalid", status_code=422)

                result = await VoicePracticeService(db).score_pronunciation(
                    actor, target=target, target_pinyin=pinyin,
                    audio_bytes=audio_bytes, filename="voice." + ext,
                    language=str(actor.language or "ru"),
                    level=str(actor.level or "hsk1"),
                )
            return JSONResponse(result, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)
        except VoicePracticeError as exc:
            return JSONResponse(
                {"ok": False, "code": exc.code, "message": exc.message},
                status_code=exc.status_code, headers=_NO_STORE,
            )

    @router.get("/iphone-pwa/practice/mistakes")
    async def learner_mistakes_page(request: Request):
        """Render the original Mistake Engine UI, never a browser clone."""
        try:
            require_pwa_enabled(settings_obj)
            async with session_factory() as db:
                await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
            return FileResponse(
                "app/static/course_v3_mistakes.html", media_type="text/html",
                headers={**_NO_STORE,
                         "X-Content-Type-Options": "nosniff",
                         "X-Frame-Options": "DENY"},
            )
        except PwaAuthError as exc:
            if exc.code == "pwa_session_required":
                return RedirectResponse(
                    "/iphone-pwa", status_code=303, headers=_NO_STORE,
                )
            return _error(exc)

    @router.get("/api/v3/pwa/mistakes")
    async def pwa_mistakes_overview(request: Request):
        from app.services.course_mistake_service import CourseMistakeService
        try:
            allowed = {"view", "lang", "limit", "offset", "category"}
            if set(request.query_params.keys()) - allowed:
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            if request.query_params.get("view", "") not in {"", "targets"}:
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
                result = await CourseMistakeService(db).overview(
                    actor, view=request.query_params.get("view") or None,
                    category=request.query_params.get("category"),
                    limit=request.query_params.get("limit", "30"),
                    offset=request.query_params.get("offset", "0"),
                    language=request.query_params.get("lang"),
                )
            return JSONResponse(
                result, status_code=200 if result.get("ok") else 400,
                headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/mistakes/review/start")
    async def pwa_mistake_review_start(request: Request):
        from app.services.course_mistake_service import CourseMistakeService
        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            payload = await _small_json(request, PwaMistakeStart, max_bytes=4096)
            if (not payload.access_ref or len(payload.access_ref) > 100
                    or (payload.formats is not None and (
                        len(payload.formats) > 10
                        or any(not isinstance(v, str) or len(v) > 40
                               for v in payload.formats)
                    ))):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                result = await CourseMistakeService(db).start_review(
                    actor, ad_supported=False,
                    access_ref=payload.access_ref, category=payload.category,
                    formats=payload.formats, language=payload.language,
                )
            err = result.get("error")
            status = (200 if result.get("ok") else 403 if err in {
                "free_feature_limit_reached", "ad_authorization_required",
                "course_access_blocked",
            } else 400)
            return JSONResponse(result, status_code=status, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/mistakes/review/answer")
    async def pwa_mistake_review_answer(request: Request):
        from app.services.course_mistake_service import CourseMistakeService
        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            payload = await _small_json(request, PwaMistakeAnswer, max_bytes=4096)
            if (len(payload.session_id) > 160 or len(payload.question_id) > 160
                    or (isinstance(payload.selected_index, list) and (
                        len(payload.selected_index) > 40
                        or any(len(value) > 60 for value in payload.selected_index)
                    ))):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                result = await CourseMistakeService(db).answer_review_question(
                    actor, session_id=payload.session_id,
                    question_id=payload.question_id,
                    selected_index=payload.selected_index,
                )
            return JSONResponse(
                result, status_code=200 if result.get("ok") else 400,
                headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/mistakes/review/complete")
    async def pwa_mistake_review_complete(request: Request):
        from app.services.course_mistake_service import CourseMistakeService
        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            payload = await _small_json(request, PwaMistakeComplete, max_bytes=16384)
            if len(payload.session_id) > 160 or len(payload.answers) > 40:
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                result = await CourseMistakeService(db).complete_review(
                    actor, session_id=payload.session_id,
                    answers=payload.answers,
                )
            return JSONResponse(
                result, status_code=200 if result.get("ok") else 400,
                headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.get("/iphone-pwa/practice/test")
    async def learner_test_page(request: Request):
        """Use the existing test-centre page with PWA cookie authority."""
        try:
            require_pwa_enabled(settings_obj)
            async with session_factory() as db:
                await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
            return FileResponse(
                "app/static/course_v3_test.html", media_type="text/html",
                headers={**_NO_STORE,
                         "X-Content-Type-Options": "nosniff",
                         "X-Frame-Options": "DENY"},
            )
        except PwaAuthError as exc:
            if exc.code == "pwa_session_required":
                return RedirectResponse(
                    "/iphone-pwa", status_code=303, headers=_NO_STORE,
                )
            return _error(exc)

    @router.post("/api/v3/pwa/exams/start")
    async def pwa_exam_start(request: Request):
        from app.services.course_hsk_exam_service import CourseHskExamService
        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            payload = await _small_json(request, PwaExamStart, max_bytes=2048)
            if not (1 <= len(payload.level) <= 16) or not (1 <= len(payload.access_ref) <= 100):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                result = await CourseHskExamService(db).start(
                    actor,
                    level=payload.level, lang=payload.lang,
                    access_ref=payload.access_ref, ad_supported=False,
                )
            err = result.get("error")
            status = (200 if result.get("ok") else 403 if err in {
                "free_feature_limit_reached", "ad_authorization_required",
                "course_access_blocked",
            } else 400)
            return JSONResponse(result, status_code=status, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)
        except ValueError:
            return _error(PwaAuthError("pwa_request_invalid", status_code=422))

    @router.post("/api/v3/pwa/exams/complete")
    async def pwa_exam_complete(request: Request):
        from app.services.course_hsk_exam_service import CourseHskExamService
        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            payload = await _small_json(request, PwaExamComplete, max_bytes=32768)
            if not (1 <= len(payload.session_id) <= 160) or len(payload.answers) > 120:
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                result = await CourseHskExamService(db).complete(
                    actor, session_id=payload.session_id,
                    answers=payload.answers,
                )
            status = (200 if result.get("ok") else
                      409 if result.get("error") == "hsk_exam_material_changed" else 400)
            return JSONResponse(result, status_code=status, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)

    @router.get("/iphone-pwa/onboarding")
    async def learner_onboarding_page(request: Request):
        """The single original Mini App course onboarding UI."""
        try:
            require_pwa_enabled(settings_obj)
            async with session_factory() as db:
                await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
            return FileResponse(
                "app/static/course_v3_onboarding.html", media_type="text/html",
                headers={**_NO_STORE, "X-Content-Type-Options": "nosniff",
                         "X-Frame-Options": "DENY"},
            )
        except PwaAuthError as exc:
            if exc.code == "pwa_session_required":
                return RedirectResponse(
                    "/iphone-pwa", status_code=303, headers=_NO_STORE,
                )
            return _error(exc)

    @router.get("/api/v3/pwa/onboarding/status")
    async def pwa_onboarding_status(request: Request):
        from sqlalchemy import select
        from app.db.models.course_miniapp_profile import CourseMiniAppProfile
        from app.services.course_miniapp_profile_service import CourseMiniAppProfileService

        try:
            require_pwa_enabled(settings_obj)
            if set(request.query_params.keys()) - {"_"}:
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                user, _ = await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
                result = await db.execute(
                    select(CourseMiniAppProfile)
                    .where(CourseMiniAppProfile.user_id == user.id)
                )
                profile = result.scalar_one_or_none()
                completed = bool(profile and profile.onboarding_completed_at is not None)
                foundation_required = False
                if completed and str(user.level or "").strip().lower() == "beginner":
                    foundation = await CourseMiniAppProfileService(db).foundation_status(user)
                    foundation_required = bool(
                        foundation["required"] and not foundation["completed"]
                    )
                return JSONResponse({
                    "ok": True, "saved": completed,
                    "level": str(user.level or "").strip().lower(),
                    "profile": ({
                        "goal": profile.goal,
                        "daily_minutes": profile.daily_minutes,
                        "start_mode": profile.start_mode,
                    } if completed else None),
                    "foundation_required": foundation_required,
                }, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/onboarding")
    async def pwa_onboarding_finish(request: Request):
        from app.services.course_miniapp_onboarding_service import (
            CourseMiniAppOnboardingService,
        )

        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            payload = await _small_json(request, PwaOnboardingFinish, max_bytes=4096)
            if (not 1 <= len(payload.level) <= 16 or
                not 1 <= len(payload.goal) <= 40 or
                not 1 <= len(payload.start_mode) <= 32 or
                not 1 <= payload.daily_minutes <= 240 or
                not -840 <= payload.timezone_offset_minutes <= 840 or
                (payload.activation_variant is not None and
                 len(payload.activation_variant) > 32)):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                result = await CourseMiniAppOnboardingService(db).complete(
                    actor, level=payload.level, goal=payload.goal,
                    daily_minutes=payload.daily_minutes,
                    start_mode=payload.start_mode, language=payload.language,
                    timezone_offset_minutes=payload.timezone_offset_minutes,
                    activation_variant=payload.activation_variant,
                )
            status = (200 if result.get("ok") else
                      409 if result.get("error") == "course_level_change_requires_placement"
                      else 400)
            return JSONResponse(result, status_code=status, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)
        except ValueError:
            return _error(PwaAuthError("pwa_request_invalid", status_code=422))

    @router.get("/iphone-pwa/practice/voice")
    async def learner_voice_page(request: Request):
        """Original AI Voice Mini App page, protected by PWA session."""
        try:
            require_pwa_enabled(settings_obj)
            async with session_factory() as db:
                await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
            return FileResponse(
                "app/static/course_v3_voice.html", media_type="text/html",
                headers={**_NO_STORE, "X-Content-Type-Options": "nosniff",
                         "X-Frame-Options": "DENY"},
            )
        except PwaAuthError as exc:
            if exc.code == "pwa_session_required":
                return RedirectResponse(
                    "/iphone-pwa", status_code=303, headers=_NO_STORE,
                )
            return _error(exc)

    @router.get("/api/v3/pwa/voice/me")
    async def pwa_voice_status(request: Request):
        from app.services.voice_practice_service import VoicePracticeService, VoicePracticeError
        try:
            require_pwa_enabled(settings_obj)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
                result = await VoicePracticeService(db).user_status(actor)
            return JSONResponse(result, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)
        except VoicePracticeError as exc:
            return JSONResponse(
                {"ok": False, "code": exc.code, "message": exc.message},
                status_code=exc.status_code, headers=_NO_STORE,
            )

    @router.post("/api/v3/pwa/voice/session/start")
    async def pwa_voice_start(request: Request):
        from app.services.voice_practice_service import VoicePracticeService, VoicePracticeError
        from app.services.course_miniapp_analytics_service import (
            CourseMiniAppAnalyticsService,
        )
        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            payload = await _small_json(request, PwaVoiceStart, max_bytes=2048)
            if not 1 <= len(payload.role) <= 45:
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                result = await VoicePracticeService(db).start_session(
                    actor, role=payload.role, level=str(actor.level or "beginner"),
                    language=str(actor.language or "ru"), voice=payload.voice,
                    mode="turn",
                )
                result["live_available"] = False  # Browser PWA turn-based flow only.
                await CourseMiniAppAnalyticsService(db).record_server_event(
                    event_name="voice_started",
                    telegram_id=int(actor.telegram_id) if actor.telegram_id else None,
                    user_id=actor.id, source="course_voice",
                    level=str(actor.level or ""), session_id=result.get("session_id"),
                    dedupe_key=result.get("session_id"),
                    payload={
                        "role": payload.role,
                        "course_context": result.get("course_context"),
                        "scenario_id": (result.get("scenario") or {}).get("id"),
                        "transport": "iphone_pwa",
                    },
                )
                await db.commit()
            return JSONResponse(result, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)
        except VoicePracticeError as exc:
            return JSONResponse(
                {"ok": False, "code": exc.code, "message": exc.message},
                status_code=exc.status_code, headers=_NO_STORE,
            )

    @router.post("/api/v3/pwa/voice/message")
    async def pwa_voice_message(request: Request):
        from app.services.voice_practice_service import (
            MAX_AUDIO_BYTES, MAX_TEXT_CHARS, VoicePracticeError,
            VoicePracticeService,
        )
        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            if request.headers.get("Content-Type", "").split(";", 1)[0].lower() != "multipart/form-data":
                raise PwaAuthError("pwa_request_invalid", status_code=415)
            try:
                length = int(request.headers.get("Content-Length", ""))
            except (TypeError, ValueError):
                raise PwaAuthError("pwa_request_invalid", status_code=411)
            if length < 1 or length > MAX_AUDIO_BYTES + 16384:
                raise PwaAuthError("pwa_request_invalid", status_code=413)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                try:
                    form = await request.form(
                        max_files=1, max_fields=4, max_part_size=MAX_TEXT_CHARS + 1024,
                    )
                except Exception as exc:
                    raise PwaAuthError("pwa_request_invalid", status_code=422) from exc
                if set(form.keys()) - {"session_id", "text", "audio"}:
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                if len(form.getlist("session_id")) != 1 or len(form.getlist("text")) > 1 or len(form.getlist("audio")) > 1:
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                session_id = form.get("session_id")
                text_value = form.get("text", "")
                media = form.get("audio")
                if (not isinstance(session_id, str) or not (1 <= len(session_id) <= 160)
                    or not isinstance(text_value, str)
                    or len(text_value) > MAX_TEXT_CHARS):
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                audio_bytes = b""
                filename = "voice.webm"
                if media is not None:
                    if not hasattr(media, "read") or not hasattr(media, "content_type"):
                        raise PwaAuthError("pwa_request_invalid", status_code=422)
                    kind = (media.content_type or "").split(";", 1)[0].lower()
                    extension = {
                        "audio/webm": "webm", "audio/mp4": "mp4",
                        "audio/ogg": "ogg", "audio/mpeg": "mp3",
                        "audio/wav": "wav", "audio/x-m4a": "mp4",
                    }.get(kind)
                    if not extension:
                        raise PwaAuthError("pwa_request_invalid", status_code=415)
                    audio_bytes = await media.read(MAX_AUDIO_BYTES + 1)
                    if len(audio_bytes) > MAX_AUDIO_BYTES:
                        raise PwaAuthError("pwa_request_invalid", status_code=413)
                    valid = {
                        "webm": audio_bytes.startswith(b"\x1a\x45\xdf\xa3"),
                        "mp4": len(audio_bytes) >= 12 and audio_bytes[4:8] == b"ftyp",
                        "ogg": audio_bytes.startswith(b"OggS"),
                        "mp3": audio_bytes.startswith(b"ID3") or audio_bytes[:2] in (
                            b"\xff\xfb", b"\xff\xf3", b"\xff\xf2",
                        ),
                        "wav": len(audio_bytes) >= 12 and audio_bytes[:4] == b"RIFF"
                               and audio_bytes[8:12] == b"WAVE",
                    }.get(extension)
                    if not valid:
                        raise PwaAuthError("pwa_request_invalid", status_code=422)
                    filename = "voice." + extension
                if not audio_bytes and not text_value.strip():
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                result = await VoicePracticeService(db).process_message(
                    actor, session_id=session_id, audio_bytes=audio_bytes,
                    filename=filename, text=text_value.strip(),
                )
            return JSONResponse(result, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)
        except VoicePracticeError as exc:
            return JSONResponse(
                {"ok": False, "code": exc.code, "message": exc.message},
                status_code=exc.status_code, headers=_NO_STORE,
            )

    @router.post("/api/v3/pwa/voice/session/end")
    async def pwa_voice_end(request: Request):
        from app.services.voice_practice_service import VoicePracticeService, VoicePracticeError
        from app.services.course_miniapp_analytics_service import (
            CourseMiniAppAnalyticsService,
        )
        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            payload = await _small_json(request, PwaVoiceEnd, max_bytes=1024)
            if not (1 <= len(payload.session_id) <= 160):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                result = await VoicePracticeService(db).end_session(
                    actor, payload.session_id,
                )
                await CourseMiniAppAnalyticsService(db).record_server_event(
                    event_name="voice_completed",
                    telegram_id=int(actor.telegram_id) if actor.telegram_id else None,
                    user_id=actor.id, source="course_voice",
                    session_id=payload.session_id, dedupe_key=payload.session_id,
                    payload={
                        "duration_seconds": result.get("duration_seconds", 0),
                        "transport": "iphone_pwa",
                    },
                )
                await db.commit()
            return JSONResponse(result, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)
        except VoicePracticeError as exc:
            return JSONResponse(
                {"ok": False, "code": exc.code, "message": exc.message},
                status_code=exc.status_code, headers=_NO_STORE,
            )

    @router.get("/iphone-pwa/checkout")
    async def learner_checkout_page(request: Request):
        """The original subscription.html, not a second payments UI."""
        try:
            require_pwa_enabled(settings_obj)
            async with session_factory() as db:
                await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
            return FileResponse(
                "app/static/subscription.html", media_type="text/html",
                headers={
                    **_NO_STORE, "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                },
            )
        except PwaAuthError as exc:
            if exc.code == "pwa_session_required":
                return RedirectResponse(
                    "/iphone-pwa", status_code=303, headers=_NO_STORE,
                )
            return _error(exc)

    @router.post("/api/v3/pwa/subscription/overview")
    async def pwa_checkout_overview(request: Request):
        from app.services.subscription_miniapp_service import SubscriptionMiniAppService
        from app.services.subscription_entry_analytics_service import (
            SubscriptionEntryAnalyticsService,
        )
        from app.services.conversion_funnel_service import ConversionFunnelService

        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                data = await _small_json(request, PwaCheckoutContext, max_bytes=4096)
                if (data.source is not None and len(data.source) > 80
                    or data.mode is not None and len(data.mode) > 32
                    or data.attempt_id is not None and len(data.attempt_id) > 96):
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                result = await SubscriptionMiniAppService(db).overview(
                    actor, bot=bot, mode=data.mode,
                    campaign_id=data.campaign_id,
                    feedback_id=data.feedback_id,
                )
                if result.get("ok"):
                    await SubscriptionEntryAnalyticsService(db).record_entry(
                        user=actor, source=data.source or "iphone_pwa",
                        mode=data.mode, plan_type=data.plan,
                        payment_method=data.method,
                        campaign_id=data.campaign_id,
                        feedback_id=data.feedback_id,
                    )
                    # Retain the canonical funnel event. PWA users may have no
                    # Telegram provider, so the accountable key is users.id.
                    if not result.get("pending_payment") and data.attempt_id:
                        await ConversionFunnelService().record(
                            event_name="checkout_opened",
                            user=actor,
                            telegram_id=actor.telegram_id,
                            source=(data.source or "iphone_pwa")[:80],
                            payload={
                                "attempt_id": data.attempt_id,
                                "mode": data.mode or "",
                                "campaign_id": data.campaign_id,
                                "feedback_id": data.feedback_id,
                                "transport": "iphone_pwa",
                            },
                        )
            return JSONResponse(
                result, status_code=200 if result.get("ok") else 400,
                headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/subscription/quote")
    async def pwa_checkout_quote(request: Request):
        from app.services.subscription_miniapp_service import SubscriptionMiniAppService

        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                data = await _small_json(request, PwaCheckoutQuote, max_bytes=4096)
                if not (1 <= len(data.plan_type) <= 40 and 1 <= len(data.payment_method) <= 20):
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                result = await SubscriptionMiniAppService(db).quote(
                    telegram_id=actor,
                    plan_type=data.plan_type,
                    payment_method=data.payment_method,
                    card_country=data.card_country,
                    card_bank=data.card_bank,
                    bot=bot, mode=data.mode,
                    campaign_id=data.campaign_id,
                    feedback_id=data.feedback_id,
                )
            return JSONResponse(
                result, status_code=200 if result.get("ok") else 400,
                headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/subscription/payment-status")
    async def pwa_checkout_payment_status(request: Request):
        from app.repositories.payment_repo import PaymentRepository

        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                data = await _small_json(request, PwaCheckoutPaymentStatus)
                if not 1 <= data.payment_id <= 2147483647:
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                payment = await PaymentRepository(db).get_by_id(
                    data.payment_id, actor=actor,
                )
            if payment is None:
                return JSONResponse(
                    {"ok": False, "error": "payment_not_found"},
                    status_code=404, headers=_NO_STORE,
                )
            return JSONResponse({
                "ok": True, "payment_id": int(payment.id),
                "status": str(payment.payment_status or ""),
                "plan_type": str(payment.plan_type or ""),
            }, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/subscription/discount-start")
    async def pwa_checkout_discount(request: Request):
        from app.services.subscription_miniapp_service import SubscriptionMiniAppService

        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                await _small_json(request, PwaCheckoutContext, max_bytes=4096)
                result = await SubscriptionMiniAppService(db).start_discount(
                    actor, bot=bot,
                )
            return JSONResponse(
                result, status_code=200 if result.get("ok") else 400,
                headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/subscription/event")
    async def pwa_checkout_event(request: Request):
        """Only recorded checkout attempts can receive receipt-stage events."""
        from sqlalchemy import select
        from app.db.models.conversion_funnel_event import ConversionFunnelEvent
        from app.services.account_identity import owner_clause
        from app.services.conversion_funnel_service import ConversionFunnelService

        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                data = await _small_json(request, PwaCheckoutEvent, max_bytes=4096)
                attempt = str(data.attempt_id or "").strip()
                allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-:."
                if not (1 <= len(attempt) <= 80) or any(c not in allowed for c in attempt):
                    raise PwaAuthError("invalid_checkout_attempt", status_code=422)
                opened = (await db.execute(
                    select(ConversionFunnelEvent.id).where(
                        owner_clause(
                            ConversionFunnelEvent, actor,
                            telegram_column="telegram_id",
                        ),
                        ConversionFunnelEvent.event_name == "checkout_opened",
                        ConversionFunnelEvent.payload_json.like(
                            f'%"attempt_id": "{attempt}"%'
                        ),
                        ConversionFunnelEvent.payload_json.not_like('%"stage":%'),
                    ).limit(1)
                )).scalar_one_or_none()
                if not opened:
                    raise PwaAuthError("checkout_attempt_not_opened", status_code=409)
                recorded = await ConversionFunnelService().record(
                    event_name="checkout_opened", user=actor,
                    telegram_id=actor.telegram_id,
                    source=(data.source or "iphone_pwa")[:80],
                    payload={
                        "attempt_id": attempt,
                        "stage": data.stage,
                        "plan_type": (data.plan_type or "")[:32],
                        "payment_method": (data.payment_method or "")[:32],
                        "mode": (data.mode or "")[:32],
                        "transport": "iphone_pwa",
                    },
                )
            return JSONResponse(
                {"ok": bool(recorded)}, status_code=200 if recorded else 503,
                headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/subscription/submit")
    async def pwa_checkout_submit(request: Request):
        """Send the original checked receipt to admins before claiming pending."""
        from app.services.subscription_miniapp_service import SubscriptionMiniAppService

        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            if bot is None:
                raise PwaAuthError("checkout_delivery_unavailable", status_code=503)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                # The screenshot remains bounded by the canonical 8 MB decoded
                # image check in SubscriptionMiniAppService, plus this transport
                # bound for base64 JSON encoding.
                if int(request.headers.get("Content-Length") or "0") > 12 * 1024 * 1024:
                    raise PwaAuthError("pwa_request_invalid", status_code=413)
                data = await _small_json(
                    request, PwaCheckoutSubmit, max_bytes=12 * 1024 * 1024,
                )
                if (not 1 <= len(data.plan_type) <= 40
                    or not 1 <= len(data.payment_method) <= 20
                    or not data.screenshot_data_url.startswith("data:image/")
                    or len(data.screenshot_data_url) > 11_500_000):
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                try:
                    result = await SubscriptionMiniAppService(db).submit(
                        telegram_id=actor,
                        plan_type=data.plan_type,
                        payment_method=data.payment_method,
                        card_country=data.card_country,
                        card_bank=data.card_bank,
                        screenshot_data_url=data.screenshot_data_url,
                        bot=bot, mode=data.mode,
                        campaign_id=data.campaign_id,
                        feedback_id=data.feedback_id,
                        source="iphone_pwa",
                    )
                except Exception:
                    await db.rollback()
                    raise PwaAuthError("payment_submit_failed", status_code=503)
            return JSONResponse(
                result, status_code=200 if result.get("ok") else 400,
                headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)
        except ValueError:
            return _error(PwaAuthError("pwa_request_invalid", status_code=422))

    @router.post("/api/v3/pwa/language")
    async def pwa_set_language(request: Request):
        """Save the very same users.language consumed by Telegram course/QA."""
        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            data = await _small_json(request, PwaLanguagePreference)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                # No new PWA preferences table; write the canonical user.
                actor.language = data.language
                await db.commit()
            return JSONResponse(
                {"ok": True, "language": data.language}, headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.get("/iphone-pwa/manifest.webmanifest")
    async def learner_manifest():
        try:
            require_pwa_enabled(settings_obj)
            # Reuse the existing published app brand asset and Pomp paper
            # theme; no extra app identity or arbitrary install origin.
            return JSONResponse(
                {
                    "name": "HSK AI",
                    "short_name": "HSK AI",
                    "start_url": "/iphone-pwa",
                    "scope": "/iphone-pwa",
                    "display": "standalone",
                    "background_color": "#FDF9F0",
                    "theme_color": "#FDF9F0",
                    "icons": [{
                        "src": "/assets/hsk-ai-logo-256.png",
                        "sizes": "256x256",
                        "type": "image/png",
                        "purpose": "any",
                    }],
                },
                media_type="application/manifest+json",
                headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.get("/iphone-pwa-login.js")
    async def login_script():
        try:
            require_pwa_enabled(settings_obj)
            return FileResponse(
                "app/static/iphone-pwa-login.js", media_type="application/javascript",
                headers={**_NO_STORE, "X-Content-Type-Options": "nosniff"},
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.get("/api/v3/pwa-auth/providers")
    async def providers():
        try:
            require_pwa_enabled(settings_obj)
            return JSONResponse(
                {"ok": True, "providers": available_providers(settings_obj, platform="miniapp")},
                headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa-auth/telegram/start")
    async def telegram_start(request: Request):
        try:
            require_same_origin(request, settings_obj)
            payload = await _small_json(request, PwaTelegramStart)
            async with session_factory() as db:
                link_id, url, proof = await PwaAuthService(db, settings_obj).start_telegram(
                    language=payload.language,
                )
            response = JSONResponse(
                {"ok": True, "link_request_id": link_id, "authorize_url": url},
                headers=_NO_STORE,
            )
            response.set_cookie(
                PWA_TELEGRAM_COOKIE, proof, max_age=PWA_OAUTH_AGE_SECONDS,
                path="/", secure=True, httponly=True, samesite="lax",
            )
            return response
        except (PwaAuthError, DesktopAuthError) as exc:
            return _error(PwaAuthError(
                getattr(exc, "code", "pwa_telegram_unavailable"),
                status_code=getattr(exc, "status_code", 503),
            ))

    @router.post("/api/v3/pwa-auth/telegram/claim")
    async def telegram_claim(request: Request):
        try:
            require_same_origin(request, settings_obj)
            payload = await _small_json(request, PwaTelegramClaim)
            async with session_factory() as db:
                status, token = await PwaAuthService(db, settings_obj).claim_telegram(
                    request_id=str(payload.link_request_id),
                    proof=request.cookies.get(PWA_TELEGRAM_COOKIE),
                    replace_cookie=request.cookies.get(PWA_SESSION_COOKIE),
                )
            response = JSONResponse({"ok": True, "status": status}, headers=_NO_STORE)
            if status == "complete":
                response.set_cookie(
                    PWA_SESSION_COOKIE, token, max_age=PWA_SESSION_AGE_SECONDS,
                    path="/", secure=True, httponly=True, samesite="lax",
                )
                _clear_cookie(response, PWA_TELEGRAM_COOKIE)
                # The other unfinished login provider must not replace an
                # approved Telegram actor from a stale browser callback.
                response.delete_cookie(
                    PWA_OAUTH_COOKIE, path="/", secure=True,
                    httponly=True, samesite="none",
                )
            return response
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa-auth/start")
    async def start(request: Request):
        try:
            require_same_origin(request, settings_obj)
            payload = await _small_json(request, PwaLoginStart)
            async with session_factory() as db:
                url, proof = await PwaAuthService(db, settings_obj).start(
                    provider=payload.provider, language=payload.language,
                    replace_cookie=request.cookies.get(PWA_SESSION_COOKIE),
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
        except ValidationError:
            return _error(PwaAuthError("pwa_request_invalid", status_code=422))
        except (NativeOAuthError, IdentityLinkError, DesktopAuthError) as exc:
            return _error(PwaAuthError(
                "pwa_signin_unavailable",
                status_code=503 if getattr(exc, "status_code", 503) == 503 else 422,
            ))
        except Exception:
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

    # Read the existing canonical course inbox; a transactional Telegram/
    # Android delivery is NOT automatically a persisted inbox item.
    @router.get("/api/v3/pwa/notifications")
    async def course_notifications(request: Request):
        try:
            from app.services.course_notification_service import CourseNotificationService
            cookie = request.cookies.get(PWA_SESSION_COOKIE)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).actor(cookie)
                items = await CourseNotificationService(db).list_for_user(actor)
            return JSONResponse(
                {"ok": True, "notifications": items}, headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/gamification")
    async def pwa_gamification(request: Request):
        """Reuse the canonical course league for the verified browser account."""
        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            payload = await _small_json(request, PwaGamificationRequest)
            from app.services.course_gamification_service import CourseGamificationService

            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                result = await CourseGamificationService(db).leaderboard(
                    actor,
                    timezone_offset_minutes=payload.timezone_offset_minutes,
                )
                await db.commit()
            return JSONResponse({"ok": True, **result}, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)

    @router.get("/api/v3/pwa/push/status")
    async def pwa_push_status(request: Request):
        try:
            from app.services.learner_pwa_push import subscription_config, subscription_status
            async with session_factory() as db:
                actor, browser_session = await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
                configured = subscription_config(settings_obj)
                row = None
                if configured is not None:
                    row = await subscription_status(db, device_id=browser_session.device_id)
            return JSONResponse({
                "ok": True,
                "enabled": configured is not None,
                "public_key": configured[0] if configured is not None else None,
                "subscribed": row is not None,
                "subscription_id": row.id if row is not None else None,
                "user_id": actor.id,
            }, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/push/subscribe")
    async def pwa_push_subscribe(request: Request):
        try:
            from app.services.learner_pwa_push import SubscribeRequest, subscribe, subscription_config
            require_same_origin(request, settings_obj)
            async with session_factory() as db:
                actor, browser_session = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                configured = subscription_config(settings_obj)
                if configured is None:
                    return JSONResponse(
                        {"ok": False, "error": "push_unavailable"},
                        status_code=503, headers=_NO_STORE,
                    )
                try:
                    command = await _small_json(request, SubscribeRequest, max_bytes=4096)
                except (ValidationError, ValueError, TypeError):
                    return JSONResponse(
                        {"ok": False, "error": "invalid_subscription"},
                        status_code=422, headers=_NO_STORE,
                    )
                try:
                    result = await subscribe(
                        db, user_id=actor.id, device_id=browser_session.device_id,
                        command=command, fernet=configured[1],
                    )
                except ValueError:
                    return JSONResponse(
                        {"ok": False, "error": "invalid_subscription"},
                        status_code=422, headers=_NO_STORE,
                    )
                except OverflowError:
                    return JSONResponse(
                        {"ok": False, "error": "push_device_limit"},
                        status_code=409, headers=_NO_STORE,
                    )
                if result is None:
                    return JSONResponse(
                        {"ok": False, "error": "push_device_conflict"},
                        status_code=409, headers=_NO_STORE,
                    )
                await db.commit()
            return JSONResponse({"ok": True, "subscribed": True}, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/push/revoke")
    async def pwa_push_revoke(request: Request):
        try:
            from app.services.learner_pwa_push import RevokeRequest, revoke
            require_same_origin(request, settings_obj)
            async with session_factory() as db:
                _actor, browser_session = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                try:
                    command = await _small_json(request, RevokeRequest, max_bytes=512)
                except (ValidationError, ValueError, TypeError):
                    return JSONResponse(
                        {"ok": False, "error": "invalid_subscription"},
                        status_code=422, headers=_NO_STORE,
                    )
                found = await revoke(
                    db, device_id=browser_session.device_id,
                    subscription_id=command.subscription_id,
                )
                await db.commit()
            return JSONResponse({"ok": True, "subscribed": False, "found": found}, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)

    @router.get("/api/v3/pwa/account-notices")
    async def account_notices(request: Request):
        """Stored account/service notices, separate from course feed.

        Reading this route is never a push delivery acknowledgment and must
        not alter Android->Telegram fallback or Smart Reminder policy.
        """
        try:
            from sqlalchemy import select
            from app.db.models.account_notice_delivery import AccountNoticeDelivery
            from app.db.models.payment import Payment
            from app.services.account_identity import owner_clause
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
                rows = (await db.execute(
                    select(AccountNoticeDelivery)
                    .where(owner_clause(
                        AccountNoticeDelivery, actor, telegram_column="telegram_id",
                    ))
                    .order_by(
                        AccountNoticeDelivery.created_at.desc(),
                        AccountNoticeDelivery.id.desc(),
                    )
                    .limit(20)
                )).scalars().all()
                notices = [
                    {
                        "id": row.id,
                        "key": row.key,
                        "title": row.title,
                        "body": row.body,
                        "action": row.action if row.action in {"subscription", "course"} else "course",
                        "created_at": row.created_at.isoformat() if row.created_at else "",
                    }
                    for row in rows
                ]
                # Android/Telegram account notice rows are not a complete
                # record of browser checkout outcomes. Read the authoritative
                # reviewed payments separately, without changing delivery
                # acknowledgements, entitlements or exposing admin comments.
                reviews = (await db.execute(
                    select(
                        Payment.id, Payment.payment_status,
                        Payment.plan_type, Payment.reviewed_at,
                    )
                    .where(owner_clause(
                        Payment, actor, telegram_column="user_telegram_id",
                    ))
                    .where(Payment.payment_status.in_(("approved", "rejected")))
                    .where(Payment.reviewed_at.is_not(None))
                    .order_by(Payment.reviewed_at.desc(), Payment.id.desc())
                    .limit(10)
                )).all()
                payment_reviews = [
                    {
                        "payment_id": int(review.id),
                        "status": review.payment_status,
                        "plan_type": review.plan_type,
                        "reviewed_at": review.reviewed_at.isoformat(),
                    }
                    for review in reviews
                ]
                # A historical rejected receipt must not be presented as an
                # *active* failure after the learner submitted a new pending
                # receipt or an approval superseded it. Focus only the newest
                # submitted (not draft) transaction, scoped to this actor.
                latest = (await db.execute(
                    select(
                        Payment.id, Payment.payment_status,
                        Payment.plan_type, Payment.reviewed_at,
                    )
                    .where(owner_clause(
                        Payment, actor, telegram_column="user_telegram_id",
                    ))
                    .where(Payment.payment_status.in_((
                        "pending", "approved", "rejected",
                    )))
                    .order_by(Payment.submitted_at.desc(), Payment.id.desc())
                    .limit(1)
                )).one_or_none()
                payment_action = (
                    {
                        "payment_id": int(latest.id),
                        "status": "rejected",
                        "plan_type": latest.plan_type,
                        "reviewed_at": latest.reviewed_at.isoformat(),
                    }
                    if latest is not None
                    and latest.payment_status == "rejected"
                    and latest.reviewed_at is not None
                    else None
                )
            return JSONResponse(
                {"ok": True, "notices": notices,
                 "payment_reviews": payment_reviews,
                 "payment_action": payment_action}, headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.get("/api/v3/pwa/feedback/available")
    async def pwa_feedback_available(request: Request):
        """Read existing canonical prompts; reading creates no reward/delivery."""
        from datetime import datetime, timezone
        from sqlalchemy import select
        from app.db.models.release_feedback import (
            ReleaseFeedbackCampaign, ReleaseFeedbackDelivery,
        )
        from app.repositories.bot_feedback_repo import BotFeedbackRepository
        from app.repositories.release_feedback_repo import ReleaseFeedbackRepository
        from app.services.account_identity import owner_clause
        from app.services.bot_feedback_service import BotFeedbackService
        from app.services.user_access_state_service import UserAccessStateService

        try:
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
                service = BotFeedbackService(db)
                feedback = await BotFeedbackRepository(db).get_latest_pending_by_user(actor.id)
                now = datetime.now(timezone.utc)
                if (
                    not _pwa_feedback_prompt_eligible(actor, service, now)
                    or not feedback or not service._is_prompt_due(feedback, now)
                ):
                    feedback = None
                ordinary = ({
                    "feedback_id": feedback.id,
                    "paid": UserAccessStateService.is_paid(actor),
                    "liked_code": feedback.liked_code,
                    "disliked_code": feedback.disliked_code,
                    "choices": _pwa_feedback_choices(
                        actor.language, paid=UserAccessStateService.is_paid(actor),
                    ),
                } if feedback else None)

                deliveries = (await db.execute(
                    select(ReleaseFeedbackDelivery, ReleaseFeedbackCampaign)
                    .join(
                        ReleaseFeedbackCampaign,
                        ReleaseFeedbackDelivery.campaign_id == ReleaseFeedbackCampaign.id,
                    )
                    .where(owner_clause(
                        ReleaseFeedbackDelivery, actor,
                        telegram_column="user_telegram_id",
                    ))
                    .where(ReleaseFeedbackDelivery.status.in_(("sent", "clicked")))
                    .where(ReleaseFeedbackCampaign.status.in_(("sending", "sent")))
                    .order_by(
                        ReleaseFeedbackDelivery.delivered_at.desc(),
                        ReleaseFeedbackDelivery.id.desc(),
                    )
                    .limit(20)
                )).all()
                release_repo = ReleaseFeedbackRepository(db)
                release = []
                seen = set()
                for delivery, campaign in deliveries:
                    if campaign.id in seen:
                        continue
                    seen.add(campaign.id)
                    if await release_repo.get_response(campaign_id=campaign.id, user=actor):
                        continue
                    release.append({
                        "campaign_id": campaign.id,
                        "title": campaign.title,
                        "message_text": campaign.message_text,
                        "feature_key": campaign.feature_key,
                        "content_type": campaign.content_type,
                    })
                    if len(release) == 5:
                        break
            return JSONResponse(
                {"ok": True, "ordinary": ordinary, "release": release},
                headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/feedback/ordinary/prepare")
    async def pwa_prepare_ordinary_feedback(request: Request):
        """Reserve the existing bot feedback record for a verified learner.

        This does not send/ack a Telegram prompt or grant a reward. The UI
        will separately decide when to display a Figma-approved dialog.
        """
        from datetime import datetime, timezone
        from sqlalchemy import select
        from app.db.models.user import User
        from app.services.bot_feedback_service import BotFeedbackService
        from app.services.user_access_state_service import UserAccessStateService

        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                await _small_json(request, PwaFeedbackPrepare, max_bytes=256)
                # Serialize prompt creation per canonical learner, including
                # concurrent browser tabs or simultaneous provider sessions.
                learner = (await db.execute(
                    select(User).where(User.id == actor.id).with_for_update()
                )).scalar_one()
                now = datetime.now(timezone.utc)
                service = BotFeedbackService(db)
                feedback = None
                if _pwa_feedback_prompt_eligible(learner, service, now):
                    feedback = await service._get_or_create_due_feedback(learner, now)
                    if feedback and not service._is_prompt_due(feedback, now):
                        feedback = None
                await db.commit()
                payload = ({
                    "feedback_id": feedback.id,
                    "paid": UserAccessStateService.is_paid(learner),
                    "liked_code": feedback.liked_code,
                    "disliked_code": feedback.disliked_code,
                    "choices": _pwa_feedback_choices(
                        learner.language,
                        paid=UserAccessStateService.is_paid(learner),
                    ),
                } if feedback else None)
            return JSONResponse(
                {"ok": True, "ordinary": payload}, headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/feedback/ordinary/submit")
    async def pwa_ordinary_feedback_submit(request: Request):
        """Commit one existing ordinary bot feedback using its canonical rules."""
        from sqlalchemy import select
        from app.bot.keyboards.feedback import (
            LIKED_OPTIONS, DISLIKED_OPTIONS, LIKE_SUB_OPTIONS,
            PAID_OPTIONS, PAID_SUB_POSITIVE, PAID_SUB_NEGATIVE,
            feedback_like_label, feedback_dislike_label,
            feedback_sub_label, feedback_paid_label,
        )
        from app.bot.handlers.feedback import DISLIKE_DETAIL_REQUIRED_CODES
        from app.db.models.user import User
        from app.db.models.bot_feedback import BotFeedback
        from app.repositories.bot_feedback_repo import BotFeedbackRepository
        from app.services.bot_feedback_service import BotFeedbackService
        from app.services.user_access_state_service import UserAccessStateService

        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                data = await _small_json(
                    request, PwaOrdinaryFeedbackSubmit, max_bytes=8192,
                )
                if not 1 <= data.feedback_id <= 2147483647:
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                # A verified account row serializes browser tabs and repeated
                # submissions; existing bot records use the same users.id.
                learner = (await db.execute(
                    select(User).where(User.id == actor.id).with_for_update()
                )).scalar_one()
                feedback = (await db.execute(
                    select(BotFeedback).where(
                        BotFeedback.id == data.feedback_id,
                        BotFeedback.user_id == learner.id,
                    ).with_for_update()
                )).scalar_one_or_none()
                if feedback is None:
                    raise PwaAuthError("feedback_not_available", status_code=404)
                if feedback.status != "pending":
                    raise PwaAuthError("feedback_already_completed", status_code=409)
                repo = BotFeedbackRepository(db)
                lang = learner.language if learner.language in {"uz", "ru", "tj"} else "ru"
                if UserAccessStateService.is_paid(learner):
                    if (
                        data.paid_code not in PAID_OPTIONS
                        or any((
                            data.liked_code, data.liked_sub_code, data.liked_other_text,
                            data.disliked_code, data.disliked_detail_text,
                        ))
                    ):
                        raise PwaAuthError("pwa_request_invalid", status_code=422)
                    subs = (PAID_SUB_POSITIVE if data.paid_code in ("worth", "useful")
                            else PAID_SUB_NEGATIVE)
                    if data.paid_sub_code not in subs:
                        raise PwaAuthError("pwa_request_invalid", status_code=422)
                    detail = (data.paid_other_text or "").strip()
                    if (data.paid_sub_code == "other" and not detail) or len(detail) > 1000:
                        raise PwaAuthError("pwa_request_invalid", status_code=422)
                    if feedback.liked_code and feedback.liked_code != "paid_" + data.paid_code:
                        raise PwaAuthError("feedback_state_changed", status_code=409)
                    await repo.save_liked(
                        feedback, "paid_" + data.paid_code,
                        feedback_paid_label(data.paid_code, lang),
                    )
                    await repo.save_disliked(
                        feedback, "paid_" + data.paid_sub_code,
                        detail if data.paid_sub_code == "other"
                        else feedback_sub_label(data.paid_sub_code, lang),
                    )
                else:
                    if (
                        data.liked_code not in LIKED_OPTIONS
                        or data.disliked_code not in DISLIKED_OPTIONS
                        or data.paid_code is not None or data.paid_sub_code is not None
                        or data.paid_other_text is not None
                    ):
                        raise PwaAuthError("pwa_request_invalid", status_code=422)
                    like_detail = (data.liked_other_text or "").strip()
                    dislike_detail = (data.disliked_detail_text or "").strip()
                    if len(like_detail) > 1000 or len(dislike_detail) > 1000:
                        raise PwaAuthError("pwa_request_invalid", status_code=422)
                    if data.liked_code in LIKE_SUB_OPTIONS:
                        if data.liked_sub_code not in LIKE_SUB_OPTIONS[data.liked_code]:
                            raise PwaAuthError("pwa_request_invalid", status_code=422)
                        if data.liked_sub_code == "other" and not like_detail:
                            raise PwaAuthError("pwa_request_invalid", status_code=422)
                    elif data.liked_sub_code is not None:
                        raise PwaAuthError("pwa_request_invalid", status_code=422)
                    if data.liked_code == "other" and not like_detail:
                        raise PwaAuthError("pwa_request_invalid", status_code=422)
                    if data.disliked_code in DISLIKE_DETAIL_REQUIRED_CODES | {"other"}:
                        if not dislike_detail:
                            raise PwaAuthError("pwa_request_invalid", status_code=422)
                    if feedback.liked_code and feedback.liked_code != data.liked_code:
                        raise PwaAuthError("feedback_state_changed", status_code=409)
                    liked_text = (
                        like_detail if data.liked_code == "other"
                        else feedback_like_label(data.liked_code, lang)
                    )
                    if data.liked_sub_code:
                        liked_text = (
                            liked_text + " → " + (
                                like_detail if data.liked_sub_code == "other"
                                else feedback_sub_label(data.liked_sub_code, lang)
                            )
                        )[:1000]
                    await repo.save_liked(feedback, data.liked_code, liked_text)
                    await repo.save_disliked(
                        feedback, data.disliked_code,
                        dislike_detail if data.disliked_code in
                        DISLIKE_DETAIL_REQUIRED_CODES | {"other"}
                        else feedback_dislike_label(data.disliked_code, lang),
                    )
                await BotFeedbackService(db).finish_feedback(feedback, learner)
                await db.commit()
            if bot is not None:
                # Like the Telegram handler, notify only after commit. Admin
                # transport failure must never undo an accepted learner answer.
                try:
                    from app.services.admin_notify_service import AdminNotifyService
                    await AdminNotifyService().notify_bot_feedback(
                        bot=bot, feedback=feedback, user=learner,
                    )
                except Exception:
                    import logging
                    logging.getLogger(__name__).exception(
                        "PWA ordinary feedback admin notice failed"
                    )
            return JSONResponse(
                {"ok": True, "feedback_id": data.feedback_id, "completed": True},
                headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/feedback/release/comment")
    async def pwa_release_feedback_comment(request: Request):
        """Add a later comment to an already owned release rating.

        Telegram offers the same optional comment step. This path never
        creates a second rating, trial or discount. Identical retries do
        not emit another administrator notification.
        """
        from sqlalchemy import select
        from app.db.models.user import User
        from app.services.release_feedback_service import ReleaseFeedbackService

        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                data = await _small_json(
                    request, PwaReleaseFeedbackComment, max_bytes=4096,
                )
                if not 1 <= data.campaign_id <= 2147483647:
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                comment = data.comment_text.strip()
                if not comment or len(comment) > 1000:
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                learner = (await db.execute(
                    select(User).where(User.id == actor.id)
                    .with_for_update().execution_options(populate_existing=True)
                )).scalar_one()
                service = ReleaseFeedbackService(db)
                campaign = await service.repo.get_campaign(data.campaign_id)
                delivery = await service.repo.get_delivery(
                    campaign_id=data.campaign_id, user=learner,
                )
                if (
                    campaign is None or campaign.status not in {"sending", "sent"}
                    or delivery is None
                    or delivery.status not in {"sent", "clicked"}
                ):
                    raise PwaAuthError("feedback_not_available", status_code=404)
                response = await service.repo.get_response(
                    campaign_id=data.campaign_id, user=learner,
                )
                if response is None:
                    raise PwaAuthError("feedback_rating_required", status_code=409)
                changed = (response.comment_text or "").strip() != comment
                if changed:
                    await service.repo.update_response_comment(
                        response, comment_text=comment,
                        # The PWA currently has no attachment editor. Preserve
                        # a historical Telegram photo/document when adding text.
                        attachment_file_id=response.attachment_file_id,
                        attachment_type=response.attachment_type,
                    )
                    await db.commit()
                response_id = response.id
            if changed and bot is not None:
                try:
                    from app.services.admin_notify_service import AdminNotifyService
                    await AdminNotifyService().notify_release_feedback_response(
                        bot, campaign=campaign, response=response,
                        user=learner, event="comment",
                    )
                except Exception:
                    import logging
                    logging.getLogger(__name__).exception(
                        "PWA release feedback comment notice failed"
                    )
            return JSONResponse({
                "ok": True, "response_id": response_id,
                "updated": changed,
            }, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/feedback/release/respond")
    async def pwa_release_feedback_respond(request: Request):
        """Answer only a campaign previously delivered to this canonical owner.

        Shared release feedback response/discount/trial services, with one
        per-account campaign decision regardless of Telegram/PWA transport.
        """
        from sqlalchemy import select
        from app.db.models.user import User
        from app.repositories.release_feedback_repo import ReleaseFeedbackRepository
        from app.services.release_feedback_service import ReleaseFeedbackService

        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                data = await _small_json(
                    request, PwaReleaseFeedbackReply, max_bytes=4096,
                )
                if not 1 <= data.campaign_id <= 2147483647 or not 1 <= data.rating <= 5:
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                comment = (data.comment_text or "").strip()
                if len(comment) > 1000 or (data.rating <= 2 and not comment):
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                learner = (await db.execute(
                    select(User).where(User.id == actor.id).with_for_update()
                )).scalar_one()
                service = ReleaseFeedbackService(db)
                campaign = await service.repo.get_campaign(data.campaign_id)
                delivery = await service.repo.get_delivery(
                    campaign_id=data.campaign_id, user=learner,
                )
                if (
                    campaign is None or campaign.status not in {"sending", "sent"}
                    or delivery is None or delivery.status not in {"sent", "clicked"}
                ):
                    raise PwaAuthError("feedback_not_available", status_code=404)
                if await service.repo.get_response(
                    campaign_id=campaign.id, user=learner,
                ):
                    raise PwaAuthError("feedback_already_completed", status_code=409)
                response = await service.repo.create_response(
                    campaign_id=campaign.id,
                    user=learner,
                    rating=data.rating,
                    comment_text=comment or None,
                )
                discount_id = await service.create_discount_for_response(
                    campaign=campaign, response=response, user=learner,
                )
                _, trial_until = await service.grant_trial_access(
                    campaign=campaign, user=learner,
                )
                response_id = response.id
                await db.commit()
            if bot is not None:
                try:
                    from app.services.admin_notify_service import AdminNotifyService
                    await AdminNotifyService().notify_release_feedback_response(
                        bot, campaign=campaign, response=response,
                        user=learner, event="rating",
                    )
                except Exception:
                    import logging
                    logging.getLogger(__name__).exception(
                        "PWA release feedback admin notice failed"
                    )
            return JSONResponse({
                "ok": True, "response_id": response_id,
                "discount_campaign_id": discount_id,
                "trial_until": trial_until.isoformat() if trial_until else None,
            }, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)

    return router

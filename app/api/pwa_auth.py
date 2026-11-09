"""Browser-only learner PWA login/session transport; disabled until configured.

This router never authenticates a legacy Telegram course endpoint. Client PWA
routes must explicitly resolve the actor and enforce CSRF on state mutation.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError

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
    pwa_origin,
    require_same_origin,
    require_pwa_enabled,
)

_NO_STORE = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
# A short-lived, HttpOnly navigation hint, not authentication or course access.
_PWA_LI_RESUME_COOKIE = "__Host-hskai-li-resume"
_PWA_LI_RESUME_SECONDS = 900


def _embeddable_pwa_page_headers(request: Request) -> dict[str, str]:
    embedded = request.query_params.getlist("embedded") == ["1"]
    return {
        **_NO_STORE,
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "SAMEORIGIN" if embedded else "DENY",
        "Content-Security-Policy": (
            "frame-ancestors 'self'" if embedded else "frame-ancestors 'none'"
        ),
    }


_PWA_HTML_ETAGS: dict[tuple[str, int, int], str] = {}


def _pwa_html(request: Request, path: str, headers: dict[str, str]) -> Response:
    """Serve an already-authorized learner HTML shell with revalidation.

    Every caller verifies the browser session before calling this, so a 304
    never skips authentication. ``private, no-cache`` keeps shared caches out
    and makes the browser revalidate on each launch; an unchanged course shell
    (~760 KB) then costs one round trip instead of a full download on a slow
    connection. The ETag is derived from the file bytes, so a deploy that does
    not change this page keeps the learner's cached copy valid.
    """
    stat = os.stat(path)
    key = (path, stat.st_mtime_ns, stat.st_size)
    etag = _PWA_HTML_ETAGS.get(key)
    if etag is None:
        with open(path, "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()[:32]
        etag = f'W/"{digest}"'
        _PWA_HTML_ETAGS[key] = etag
    response_headers = {
        **headers, "Cache-Control": "private, no-cache", "ETag": etag,
    }
    candidates = {
        tag.strip().removeprefix("W/")
        for tag in request.headers.get("if-none-match", "").split(",")
    }
    if etag.removeprefix("W/") in candidates:
        return Response(status_code=304, headers=response_headers)
    return FileResponse(path, media_type="text/html", headers=response_headers)


# The reviewed shared HTML bytes MUST remain unchanged for source/translation
# audit anchors. Inject PWA-only assets only after an authenticated route check.
# The injected HTML is separately ETagged by its FULL bytes, not by file SHA.
_PWA_INLINE_PRO_HTML = "\n<link rel=\"stylesheet\" href=\"/course_v3_data/iphone-pwa-inline-pro.css?v=20261108-e8010ea28fdc\">\n<script src=\"/course_v3_data/iphone-pwa-inline-pro.js?v=20261108-8d96888d601f\"></script>\n<script src=\"/course_v3_data/iphone-pwa-inline-pro-bridge.js?v=20261108-afd4f9d80534\"></script>\n".encode("utf-8")

# Scope only to the verified browser PWA. The native first-paint skeleton
# stays in course-v3.html; these are ONLY independent secondary section states.
_PWA_PROGRESSIVE_SECTIONS_CSS = b'''<style id="hsk-pwa-progressive-sections">
html.hsk-pwa-browser .hsk-pwa-section-loading{display:block;padding:12px 0 24px;min-height:220px}
html.hsk-pwa-browser .hsk-pwa-section-loading .hsk-pwa-load-card{border-radius:18px;background:var(--card,#f1f0ee);border:1px solid var(--line,rgba(0,0,0,.08));min-height:78px;margin:12px 0;padding:16px}
html.hsk-pwa-browser .hsk-pwa-section-loading .hsk-pwa-load-card:first-child{min-height:110px}
html.hsk-pwa-browser .hsk-pwa-section-loading .hsk-pwa-load-line{width:56%;height:13px;margin:9px 0;border-radius:9px;background:var(--hsk-divider,#dedddc);animation:hsk-pwa-section-pulse 1.5s ease-in-out infinite alternate}
html.hsk-pwa-browser .hsk-pwa-section-loading .hsk-pwa-load-line.short{width:34%}
html.hsk-pwa-browser .hsk-pwa-profile-accuracy-loading{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px;min-height:138px;margin:14px 0}
html.hsk-pwa-browser .hsk-pwa-profile-accuracy-loading .hsk-pwa-load-ring{width:76px;height:76px;border-radius:50%;border:10px solid var(--hsk-divider,#dedddc);margin:0 auto 10px;opacity:.75;animation:hsk-pwa-section-pulse 1.5s ease-in-out infinite alternate}
html.hsk-pwa-browser .hsk-pwa-profile-accuracy-loading .hsk-pwa-load-line{height:12px;width:55%;border-radius:8px;background:var(--hsk-divider,#dedddc);margin:auto;opacity:.75}
@keyframes hsk-pwa-section-pulse{from{opacity:.5}to{opacity:.95}}
@media(prefers-reduced-motion:reduce){html.hsk-pwa-browser .hsk-pwa-section-loading .hsk-pwa-load-line,html.hsk-pwa-browser .hsk-pwa-profile-accuracy-loading .hsk-pwa-load-ring{animation:none}}
</style>'''
_PWA_TELEGRAM_SDK_SCRIPT = b'<script src="/assets/telegram-web-app.js?v=20261019-1"></script>'


_PWA_INLINE_CACHE: dict[tuple[str, int, int], tuple[bytes, str]] = {}


def _pwa_inline_html(request: Request, path: str, headers: dict[str, str],
                     *, revalidate: bool = True) -> Response:
    stat = os.stat(path)
    key = (path, stat.st_mtime_ns, stat.st_size)
    cached = _PWA_INLINE_CACHE.get(key)
    if cached is None:
        with open(path, "rb") as handle:
            source = handle.read()
        if source.count(b"</body>") != 1:
            raise RuntimeError("pwa_inline_html_invalid")
        if path == "app/static/course-v3.html":
            # Safari does not use Telegram WebApp. Remove its blocking SDK
            # from the authenticated PWA response only, never shared source.
            if source.count(_PWA_TELEGRAM_SDK_SCRIPT) == 1:
                source = source.replace(_PWA_TELEGRAM_SDK_SCRIPT, b"", 1)
            else:
                logging.getLogger(__name__).warning("pwa_telegram_sdk_tag_changed")
            # The new upstream shell is already in shared HTML. Inject CSS
            # only for independent Rating/Friends/Profile loading boundaries.
            source = source.replace(b"</head>", _PWA_PROGRESSIVE_SECTIONS_CSS + b"</head>", 1)
        document = source.replace(b"</body>", _PWA_INLINE_PRO_HTML + b"</body>", 1)
        etag = 'W/"' + hashlib.sha256(document).hexdigest()[:32] + '"'
        cached = document, etag
        if len(_PWA_INLINE_CACHE) >= 12:
            _PWA_INLINE_CACHE.clear()
        _PWA_INLINE_CACHE[key] = cached
    document, etag = cached
    output_headers = {**headers}
    output_headers["Cache-Control"] = "private, no-cache" if revalidate else "no-store"
    if revalidate:
        output_headers["ETag"] = etag
        candidates = {tag.strip().removeprefix("W/")
                      for tag in request.headers.get("if-none-match", "").split(",")}
        if etag.removeprefix("W/") in candidates:
            return Response(status_code=304, headers=output_headers)
    return Response(content=document, media_type="text/html", headers=output_headers)


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


class PwaProfileUpdate(BaseModel):
    """Same editable app-profile fields as Android; provider identity stays read-only."""
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(default="", max_length=80)
    avatar_key: Literal["", "panda_cheer", "panda_streak", "panda_worried"] = ""


class PwaNotifyToggle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: StrictBool


class PwaHintDismiss(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hint: str = Field(min_length=1, max_length=48)


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
    goals: list[str] | None = Field(default=None, min_length=1, max_length=5)
    streak_target_days: Literal[7, 14, 30, 50] | None = None
    preferred_focus: Literal["speaking", "listening", "vocabulary", "grammar", "none"] | None = None
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


class PwaVoiceMode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    mode: Literal["turn", "live"]


class PwaVoiceEnd(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str


class PwaLanguagePreference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Literal["uz", "ru", "tj"]


class PwaGamificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timezone_offset_minutes: int


class PwaExitOfferAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["view", "claim"]
    source: str | None = Field(default=None, max_length=80)


class PwaProUiEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Billing events are exclusively recorded after real provider actions.
    event: Literal[
        "pwa_pro_opened", "pwa_pro_plan_selected", "pwa_pro_more_opened",
        "pwa_pro_method_selected", "pwa_pro_exit_offered",
        "pwa_pro_exit_claimed", "pwa_pro_exit_declined", "pwa_pro_dismissed",
        "pwa_pro_checkout_failed",
    ]
    source: Literal[
        "v3_locked_lesson", "v3_pronunciation_limit", "v3_recognition_limit",
        "v3_memorize_limit", "v3_test_limit", "v3_mistake_review",
        "v3_voice_limit", "v3_qa_limit",
    ]
    attempt_id: str = Field(min_length=5, max_length=80, pattern=r"^[A-Za-z0-9:.-]+$")
    event_id: str = Field(min_length=5, max_length=80, pattern=r"^[A-Za-z0-9:.-]+$")
    plan_type: Literal["1_month", "3_months", "6_months", "12_months"] | None = None
    method: Literal["lava", "manual"] | None = None


class PwaCheckoutContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str | None = None
    mode: str | None = "subscription"
    plan: str | None = None
    method: str | None = None
    attempt_id: str | None = None
    campaign_id: int | None = None
    feedback_id: int | None = None
    # Declared by checkout builds that implement the lava.top path.
    supports_lava: bool | None = None
    # Inline UI only requests prices; it has NOT opened checkout.
    inline_preview: bool = False


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

class PwaBugReport(BaseModel):
    """Authenticated learner PWA bug report; no caller-supplied owner ID."""
    model_config = ConfigDict(extra="forbid")
    description: str
    screenshot_data_url: str = ""
    app_version: str = ""
    screen: str = ""


class PwaFeedbackPrepare(BaseModel):
    """No user, identity or campaign selector is supplied by the browser."""
    model_config = ConfigDict(extra="forbid")


class PwaLessonFeedbackPrepare(BaseModel):
    """Context for an existing feedback prompt after a server-saved lesson."""
    model_config = ConfigDict(extra="forbid")
    lesson_id: int
    level: Literal["hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3"]


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




def _pwa_feedback_choices(language: str, *, paid: bool, current: str | None = None) -> dict:
    """Expose Telegram's existing localized choice contract, not a second UI catalog.

    Read-only metadata; no callback payload, Telegram auth or reward authority.
    The server still validates all submitted codes against the same dictionaries.
    """
    from app.bot.keyboards.feedback import (
        APP_LIKED_OPTIONS, APP_PAID_SUB_POSITIVE, ACCEPTED_LIKED_OPTIONS,
        DISLIKED_OPTIONS, LIKE_SUB_OPTIONS, PAID_OPTIONS, PAID_SUB_NEGATIVE,
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
            "paid_sub_positive": choices(APP_PAID_SUB_POSITIVE, feedback_sub_label),
            "paid_sub_negative": choices(PAID_SUB_NEGATIVE, feedback_sub_label),
        }
    liked = list(APP_LIKED_OPTIONS)
    # A first answer already recorded in the bot stays selectable in the app.
    if current in ACCEPTED_LIKED_OPTIONS and current not in liked:
        liked.insert(-1, current)
    return {
        "liked": choices(liked, feedback_like_label),
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


def create_pwa_auth_router(*, session_factory, settings_obj, bot=None, lava_runtime_getter=None) -> APIRouter:
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
    async def login_page(request: Request):
        try:
            require_pwa_enabled(settings_obj)
            # A returning learner already has an authenticated browser session.
            # Redirect on the server so the login welcome screen never flashes
            # before its JavaScript notices the valid HttpOnly cookie.
            cookie = request.cookies.get(PWA_SESSION_COOKIE)
            if cookie:
                try:
                    async with session_factory() as db:
                        await PwaAuthService(db, settings_obj).actor(cookie)
                except PwaAuthError:
                    # Expired/revoked sessions still see the real login page;
                    # never treat an unverified cookie as a signed-in learner.
                    pass
                else:
                    # The Li onboarding guest can resume their same-tab draft
                    # after provider callback, but the server still verifies
                    # session actor and onboarding status before any save.
                    resuming_li = request.cookies.get(_PWA_LI_RESUME_COOKIE) == "1"
                    response = RedirectResponse(
                        "/iphone-pwa/onboarding/li" if resuming_li else "/iphone-pwa/course",
                        status_code=303, headers=_NO_STORE,
                    )
                    if resuming_li:
                        response.delete_cookie(
                            _PWA_LI_RESUME_COOKIE, path="/", secure=True,
                            httponly=True, samesite="lax",
                        )
                    return response
            # Gradual opt-in cutover: the Li panda entry is a public visual
            # shell, not a login or an entitlement. Returning verified actors
            # still use the normal authenticated course route above.
            # The flag defaults OFF in production until release QA is complete.
            # Telegram login started from Li must show the canonical browser
            # approval/polling page, not bounce back into Li again. This is
            # only a presentation escape hatch; session/CSRF rules are unchanged.
            explicit_login = request.query_params.get("login") == "1"
            if (not explicit_login and
                    bool(getattr(settings_obj, "PWA_LI_ONBOARDING_ENTRY_ENABLED", False))):
                return RedirectResponse(
                    "/iphone-pwa/onboarding/li", status_code=303,
                    headers={**_NO_STORE, "Referrer-Policy": "no-referrer"},
                )
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
            return _pwa_inline_html(request, "app/static/course-v3.html", {
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
            })
        except PwaAuthError as exc:
            if exc.code == "pwa_session_required":
                return RedirectResponse(
                    "/iphone-pwa", status_code=303, headers=_NO_STORE,
                )
            return _error(exc)

    @router.get("/iphone-pwa/dictionary")
    async def learner_dictionary_page(request: Request):
        """Public dictionary shell inside the learner PWA service-worker scope.

        Same bytes as /hsk-lugat.html (no learner data). Serving it under
        /iphone-pwa/ lets the worker reuse versioned dictionary assets.
        """
        try:
            require_pwa_enabled(settings_obj)
            return _pwa_html(request, "app/static/hsk-lugat.html",
                             _embeddable_pwa_page_headers(request))
        except PwaAuthError as exc:
            return _error(exc)

    @router.get("/iphone-pwa/phrases")
    async def learner_phrases_page(request: Request):
        """Public ready-phrases shell inside the learner PWA worker scope."""
        try:
            require_pwa_enabled(settings_obj)
            return _pwa_html(request, "app/static/hsk-gaplar.html",
                             _embeddable_pwa_page_headers(request))
        except PwaAuthError as exc:
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
            return _pwa_inline_html(request, "app/static/course_v3_recognition.html", _embeddable_pwa_page_headers(request))
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
            return _pwa_inline_html(request, "app/static/course_v3_memorize.html", _embeddable_pwa_page_headers(request))
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
            return _pwa_inline_html(request, "app/static/course_v3_pronunciation.html", _embeddable_pwa_page_headers(request))
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
            return _pwa_inline_html(request, "app/static/course_v3_mistakes.html", _embeddable_pwa_page_headers(request))
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
            return _pwa_inline_html(request, "app/static/course_v3_test.html", _embeddable_pwa_page_headers(request))
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

    @router.get("/api/v3/pwa/invite")
    async def pwa_invite(request: Request):
        """Read canonical referrals for this verified PWA account only.

        The legacy Mini App includes Telegram IDs and usernames; the browser
        UI needs neither. Do not export either identifier or trust client
        language/level as an identity claim.
        """
        from app.services.referral_service import (
            ReferralService, REFERRAL_TRIAL_REQUIRED_ACTIVE, public_apps_url,
        )

        try:
            require_pwa_enabled(settings_obj)
            if set(request.query_params) - {"lang", "tz"}:
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            lang = str(request.query_params.get("lang") or "uz").lower()
            if lang not in {"uz", "ru", "tj"}:
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            tz_str = request.query_params.get("tz")
            tz = 0 if tz_str is None else int(tz_str)
            if not -720 <= tz <= 840:
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
                service = ReferralService(db)
                await service.user_repo.ensure_referral_code(actor)
                joined = await service.referral_repo.count_by_referrer(actor)
                active = await service.get_trial_activation_progress(actor)
                source = await service.list_miniapp_referrals(
                    actor, timezone_offset_minutes=tz, limit=30,
                )
                code = str(actor.referral_code or "")
                await db.commit()
            public = [{
                "rank": int(item.get("rank") or 0),
                "name": str(item.get("name") or "").strip()[:40],
                "status": str(item.get("status") or "pending")[:20],
                "xp": int(item.get("xp") or 0),
                "total_xp": int(item.get("total_xp") or 0),
                "course_level": str(item.get("course_level") or "")[:32],
                "completed_lessons": int(item.get("completed_lessons") or 0),
                "is_paid": bool(item.get("is_paid")),
                "is_current_user": False,
            } for item in source if isinstance(item, dict)]
            return JSONResponse({
                "ok": True,
                "link": public_apps_url(settings_obj, code, trial=True),
                "joined_count": int(joined),
                "active_count": int(active),
                "required": int(REFERRAL_TRIAL_REQUIRED_ACTIVE),
                "referrals": public,
            }, headers={**_NO_STORE, "X-HSK-PWA-User-ID": str(actor.id)})
        except PwaAuthError as exc:
            return _error(exc)
        except (TypeError, ValueError):
            return _error(PwaAuthError("pwa_request_invalid", status_code=422))

    @router.get("/api/v3/pwa/profile")
    async def pwa_profile(request: Request):
        """Account-owned profile analytics without a Telegram client identity."""
        from app.services.study_miniapp_service import StudyMiniAppService

        try:
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                )
                result = await StudyMiniAppService(db).get_profile_payload(actor)
                if result.get("ok"):
                    # Provider usernames are not PWA profile identities.
                    if isinstance(result.get("user"), dict):
                        result["user"].pop("telegram_username", None)
                    await db.commit()
            return JSONResponse(result, status_code=200 if result.get("ok") else 404,
                                headers={**_NO_STORE, "X-HSK-PWA-User-ID": str(actor.id)})
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

    @router.get("/iphone-pwa/onboarding/li")
    async def learner_li_onboarding_page(request: Request):
        """Public visual shell only; never a public account or course API.

        The panda-first entry can display before registration. Every actual
        account state, track entitlement, trial and course write remains under
        the existing verified PWA cookie/CSRF routes. No public HTML response
        contains user profile data, a session token or an entitlement grant.
        """
        try:
            require_pwa_enabled(settings_obj)
            return FileResponse(
                "app/static/course_v3_li_onboarding.html",
                media_type="text/html",
                headers={
                    **_NO_STORE, "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                    "Content-Security-Policy": (
                        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                        "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; "
                        "form-action 'none'"
                    ),
                },
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/onboarding/li/resume")
    async def learner_li_resume_after_provider_login(request: Request):
        """Same-origin explicit navigation only, never an anonymous login."""
        try:
            require_pwa_enabled(settings_obj)
            require_same_origin(request, settings_obj)
            response = JSONResponse({"ok": True}, headers=_NO_STORE)
            response.set_cookie(
                _PWA_LI_RESUME_COOKIE, "1", max_age=_PWA_LI_RESUME_SECONDS,
                path="/", secure=True, httponly=True, samesite="lax",
            )
            return response
        except PwaAuthError as exc:
            return _error(exc)

    @router.get("/api/v3/pwa/onboarding/public-tracks")
    async def learner_li_public_track_preview(request: Request):
        """Expose only read-only HSK feature metadata, not user entitlement.

        Anonymous visitors may view available standards but cannot claim
        HSK 3.0 access or write profile/lesson/trial information.
        """
        try:
            require_pwa_enabled(settings_obj)
            from app.services.hsk30_feature_service import Hsk30FeatureService
            async with session_factory() as db:
                feature = Hsk30FeatureService(db)
                enabled = bool(await feature.is_enabled())
                live_levels = await feature.live_levels() if enabled else []
            return JSONResponse({
                "ok": True,
                "tracks": {
                    "hsk20": {"track": "hsk20"},
                    "hsk30": {"track": "hsk30",
                              "access": {"feature_enabled": enabled, "allowed": False},
                              "live_levels": list(live_levels)},
                },
                "hsk30_unlock": {},
            }, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)

    @router.get("/api/v3/pwa/onboarding/status")
    async def pwa_onboarding_status(request: Request):
        from sqlalchemy import select
        from app.db.models.course_miniapp_profile import CourseMiniAppProfile
        from app.services.course_miniapp_profile_service import CourseMiniAppProfileService
        from app.services.onboarding_goal_selection import read_onboarding_goals

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
                        "goals": read_onboarding_goals(getattr(profile, "goals_json", None), primary_goal=profile.goal),
                        "streak_target_days": getattr(profile, "streak_target_days", None),
                        "preferred_focus": getattr(profile, "preferred_focus", None),
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
            # Validate the ordered primary/goal invariant *before* any course write.
            from app.services.onboarding_goal_selection import normalize_onboarding_goals
            try:
                normalize_onboarding_goals(payload.goals, primary_goal=payload.goal)
            except ValueError:
                raise PwaAuthError("pwa_request_invalid", status_code=422) from None
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
                    goals=payload.goals,
                    streak_target_days=payload.streak_target_days,
                    preferred_focus=payload.preferred_focus,
                )
            status = (200 if result.get("ok") else
                      409 if result.get("error") == "course_level_change_requires_placement"
                      else 400)
            return JSONResponse(result, status_code=status, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)
        except ValueError:
            return _error(PwaAuthError("pwa_request_invalid", status_code=422))

    @router.get("/api/v3/pwa/trial/status")
    async def pwa_onboarding_trial_status(request: Request):
        """Read-only eligibility for the verified browser account, never a grant."""
        from app.services.pro_trial_service import ProTrialService, REASON_NOT_APPLICABLE
        from app.services.trial_risk_service import TrialRiskService
        from app.services.entitlements.state import EntitlementState, access_expires_at, resolve_state
        try:
            require_pwa_enabled(settings_obj)
            # Browser cookie owns this read; no Telegram initData is trusted.
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
                verdict = await ProTrialService(db).eligibility(actor)
                if verdict.get("eligible"):
                    risk = TrialRiskService(db, settings_obj)
                    snapshot = await risk.analyze(
                        actor, client="iphone_pwa", source="pwa_onboarding_status",
                        remote_ip=request.headers.get("X-Real-IP"),
                    )
                    if risk.evaluate(snapshot).denied:
                        verdict = {**verdict, "eligible": False,
                                   "reason": REASON_NOT_APPLICABLE}
                # A lost /trial/start HTTP response must be recoverable by
                # reading this *verified actor's* current entitlement. A
                # used trial flag alone is not proof that Pro is now active.
                active = resolve_state(actor) == EntitlementState.TRIAL_ACTIVE
                expires = access_expires_at(actor, EntitlementState.TRIAL_ACTIVE) if active else None
                verdict = {**verdict, "active": active,
                           "ends_at": expires.isoformat() if expires else None}
            return JSONResponse({"ok": True, "trial": verdict}, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/trial/start")
    async def pwa_onboarding_trial_start(request: Request):
        """One-time trial via canonical service; same-origin cookie+CSRF only."""
        from app.services.pro_trial_service import ProTrialService, REASON_NOT_APPLICABLE
        from app.services.trial_risk_service import TrialRiskService
        try:
            require_pwa_enabled(settings_obj)
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                risk = TrialRiskService(db, settings_obj)
                snapshot = await risk.analyze(
                    actor, client="iphone_pwa", source="pwa_onboarding",
                    remote_ip=request.headers.get("X-Real-IP"),
                )
                if risk.evaluate(snapshot).denied:
                    return JSONResponse(
                        {"ok": False, "error": REASON_NOT_APPLICABLE},
                        status_code=409, headers=_NO_STORE,
                    )
                result = await ProTrialService(db).start(
                    actor, source="pwa_onboarding", client="iphone_pwa",
                )
                if not result.get("ok"):
                    return JSONResponse(result, status_code=409, headers=_NO_STORE)
                await risk.record_started(actor, snapshot)
                await db.commit()
            return JSONResponse(result, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)

    @router.get("/iphone-pwa/practice/voice")
    async def learner_voice_page(request: Request):
        """Original AI Voice Mini App page, protected by PWA session."""
        try:
            require_pwa_enabled(settings_obj)
            async with session_factory() as db:
                await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
            return _pwa_inline_html(
                request, "app/static/course_v3_voice.html",
                {**_NO_STORE, "X-Content-Type-Options": "nosniff",
                 "X-Frame-Options": "DENY"},
                revalidate=False,
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
            return JSONResponse(result, headers={**_NO_STORE, "X-HSK-PWA-User-ID": str(actor.id)})
        except PwaAuthError as exc:
            return _error(exc)
        except VoicePracticeError as exc:
            return JSONResponse(
                {"ok": False, "code": exc.code, "message": exc.message},
                status_code=exc.status_code, headers=_NO_STORE,
            )

    @router.post("/api/v3/pwa/voice/session/start")
    async def pwa_voice_start(request: Request):
        from app.services.android_live_voice_service import pwa_live_voice_available
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
                result["live_available"] = pwa_live_voice_available(settings_obj, actor)
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

    @router.post("/api/v3/pwa/voice/session/mode")
    async def pwa_voice_mode(request: Request):
        from app.services.android_live_voice_service import pwa_live_voice_available
        from app.services.voice_practice_service import VoicePracticeError, VoicePracticeService

        try:
            # Same origin set as every other PWA mutation (session/start too).
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            payload = await _small_json(request, PwaVoiceMode, max_bytes=1024)
            if not 8 <= len(payload.session_id) <= 120:
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                if payload.mode == "live" and not pwa_live_voice_available(settings_obj, actor):
                    raise VoicePracticeError("live_voice_unavailable", "Live voice is unavailable.", 403)
                result = await VoicePracticeService(db).set_session_mode(
                    actor, session_id=payload.session_id, mode=payload.mode,
                )
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
            # The course shell can host the existing checkout after the same
            # actor check. Direct checkout links remain unframeable.
            return _pwa_inline_html(request, "app/static/subscription.html", _embeddable_pwa_page_headers(request))
        except PwaAuthError as exc:
            if exc.code == "pwa_session_required":
                return RedirectResponse(
                    "/iphone-pwa", status_code=303, headers=_NO_STORE,
                )
            return _error(exc)

    @router.post("/api/v3/pwa/subscription/inline-event")
    async def pwa_inline_pro_event(request: Request):
        """CSRF-protected, account-bound, idempotent PWA UI funnel stages.

        The canonical account row serializes concurrent browser-tab writes.
        UI clients CANNOT record a provider checkout or completed payment.
        """
        import json
        from sqlalchemy import select
        from app.db.models.user import User
        from app.db.models.conversion_funnel_event import ConversionFunnelEvent
        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            data = await _small_json(request, PwaProUiEvent, max_bytes=1024)
            if not data.event_id.startswith(data.attempt_id + ":"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                # SELECT FOR UPDATE avoids double counting the same stage
                # when a tab/network retries the same event ID.
                await db.get(User, actor.id, with_for_update=True)
                existed = (await db.execute(
                    select(ConversionFunnelEvent.id).where(
                        ConversionFunnelEvent.user_id == actor.id,
                        ConversionFunnelEvent.event_name == data.event,
                        ConversionFunnelEvent.payload_json.like(
                            '%"event_id": "' + data.event_id + '"%'
                        ),
                    ).limit(1)
                )).scalar_one_or_none()
                if existed is None:
                    db.add(ConversionFunnelEvent(
                        user_id=actor.id, telegram_id=actor.telegram_id,
                        event_name=data.event, source=data.source,
                        payload_json=json.dumps({
                            "event_id": data.event_id,
                            "attempt_id": data.attempt_id,
                            "plan_type": data.plan_type or "",
                            "payment_method": data.method or "",
                            "transport": "iphone_pwa",
                        }, ensure_ascii=False),
                    ))
                await db.commit()
            return JSONResponse(
                {"ok": True, "recorded": existed is None}, headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/subscription/exit-offer")
    async def pwa_exit_offer(request: Request):
        """Allow a one-time real 20% promo only after a verified PWA X action."""
        from app.services.pwa_exit_offer_service import PwaExitOfferService
        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            payload = await _small_json(request, PwaExitOfferAction, max_bytes=512)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                result = await PwaExitOfferService(db, settings_obj).action(
                    actor, action=payload.action,
                )
                await db.commit()
            return JSONResponse(result, headers=_NO_STORE)
        except PwaAuthError as exc:
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
                if result.get("ok") and not data.inline_preview:
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
                if result.get("ok") and lava_runtime_getter is not None:
                    from app.api.lava_checkout import attach_lava_block
                    result = await attach_lava_block(
                        db, lava_runtime_getter(), actor, result, mode=data.mode,
                        supports_lava=data.supports_lava is True,
                        campaign_id=data.campaign_id, feedback_id=data.feedback_id,
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

    @router.post("/api/v3/pwa/profile")
    async def pwa_profile_update(request: Request):
        """Edit the account display name and preset avatar (Android parity)."""
        from app.services.course_miniapp_profile_service import CourseMiniAppProfileService

        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            payload = await _small_json(request, PwaProfileUpdate, max_bytes=1024)
            # Collapse whitespace/control separators like the Android endpoint.
            display_name = " ".join(payload.display_name.split()).strip()[:80]
            if not display_name:
                raise PwaAuthError("pwa_profile_name_required", status_code=422)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                profile = await CourseMiniAppProfileService(db).get_or_create(actor.id)
                profile.display_name = display_name
                profile.avatar_key = payload.avatar_key
                await db.commit()
            return JSONResponse(
                {"ok": True, "display_name": display_name, "avatar_key": payload.avatar_key},
                headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/notify")
    async def pwa_notify_toggle(request: Request):
        """Study reminder switch: the same profile flag as Mini App /api/v3/notify."""
        from app.services.course_miniapp_profile_service import CourseMiniAppProfileService

        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            payload = await _small_json(request, PwaNotifyToggle, max_bytes=256)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                profile = await CourseMiniAppProfileService(db).get_or_create(actor.id)
                profile.notifications_enabled = payload.enabled
                await db.commit()
            return JSONResponse({"ok": True, "notifications": payload.enabled}, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/hints/dismiss")
    async def pwa_hint_dismiss(request: Request):
        """Remember a closed section hint for the verified PWA account.

        Without this the browser could never record the dismissal, so every
        introduction block came back on each open.
        """
        from app.services.miniapp_hint_service import MiniAppHintService

        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            payload = await _small_json(request, PwaHintDismiss, max_bytes=512)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                saved = await MiniAppHintService(db).dismiss(
                    actor, payload.hint.strip(), client="course_v3_pwa",
                )
                if saved:
                    await db.commit()
            return JSONResponse({"ok": True, "saved": saved}, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/preferences")
    async def pwa_set_preferences(request: Request):
        from app.api.miniapp_preferences import (
            CoursePreferencesUpdate, PreferencesError, apply_course_preferences,
            course_preferences_payload, validated_preferences_payload,
        )
        from app.services.course_miniapp_profile_service import CourseMiniAppProfileService

        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            payload = await validated_preferences_payload(request, CoursePreferencesUpdate)
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                profile = await apply_course_preferences(CourseMiniAppProfileService(db), actor.id, payload)
                await db.commit()
                return JSONResponse(
                    {"ok": True, "profile": course_preferences_payload(profile)}, headers=_NO_STORE,
                )
        except PwaAuthError as exc:
            return _error(exc)
        except PreferencesError as exc:
            return _error(PwaAuthError(exc.code, status_code=exc.status_code))
        except ValueError:
            return _error(PwaAuthError("preferences_request_invalid", status_code=422))

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
                    # Signed-in learners open the course directly; the course
                    # route sends anyone without a session to sign-in.
                    "start_url": "/iphone-pwa/course",
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
            for member in result["leaderboard"]:
                member.pop("telegram_id", None)
                member.pop("username", None)
                member["league"] = CourseGamificationService.league_for_xp(member["total_xp"])
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
            from app.services.learner_pwa_push import ACCOUNT_RESTRICTION_KEY
            from app.services.payment_notify_service import learner_rejection_reason
            from app.services.subscription_currency_service import normalize_visa_price
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).actor(
                    request.cookies.get(PWA_SESSION_COOKIE)
                )
                rows = (await db.execute(
                    select(AccountNoticeDelivery)
                    .where(owner_clause(
                        AccountNoticeDelivery, actor, telegram_column="telegram_id",
                    ))
                    .where(AccountNoticeDelivery.key != ACCOUNT_RESTRICTION_KEY)
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
                        Payment.payment_method, Payment.amount, Payment.currency,
                        Payment.local_amount, Payment.local_currency,
                        Payment.admin_comment, Payment.card_country,
                    )
                    .where(owner_clause(
                        Payment, actor, telegram_column="user_telegram_id",
                    ))
                    .where(Payment.payment_status.in_(("approved", "rejected")))
                    .where(Payment.reviewed_at.is_not(None))
                    .order_by(Payment.reviewed_at.desc(), Payment.id.desc())
                    .limit(10)
                )).all()
                language = str(actor.language or "ru")

                def review_view(row, status):
                    # Read-only receipt summary. Free-text admin comments
                    # stay hidden; only fixed coded reasons are localized.
                    local = bool(row.local_amount and row.local_currency)
                    _, currency = normalize_visa_price(
                        0, str(row.local_currency if local else row.currency or ""),
                    )
                    return {
                        "payment_id": int(row.id),
                        "status": status,
                        "plan_type": row.plan_type,
                        "reviewed_at": row.reviewed_at.isoformat(),
                        "payment_method": (
                            row.payment_method
                            if row.payment_method in {"visa", "alipay", "wechat"} else None
                        ),
                        "card_country": (
                            row.card_country
                            if row.payment_method == "visa"
                            and row.card_country in {"tj", "uz", "ru", "other"} else None
                        ),
                        "amount": str(row.local_amount if local else row.amount),
                        "currency": currency,
                        "reason": (
                            learner_rejection_reason(row.admin_comment, language)
                            if status == "rejected" else None
                        ),
                    }

                payment_reviews = [
                    review_view(review, review.payment_status) for review in reviews
                ]
                # A historical rejected receipt must not be presented as an
                # *active* failure after the learner submitted a new pending
                # receipt or an approval superseded it. Focus only the newest
                # submitted (not draft) transaction, scoped to this actor.
                latest = (await db.execute(
                    select(
                        Payment.id, Payment.payment_status,
                        Payment.plan_type, Payment.reviewed_at,
                        Payment.payment_method, Payment.amount, Payment.currency,
                        Payment.local_amount, Payment.local_currency,
                        Payment.admin_comment, Payment.card_country,
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
                    review_view(latest, "rejected")
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

    @router.post("/api/v3/pwa/bug-report")
    async def pwa_bug_report(request: Request):
        """PWA session/CSRF-specific transport to the existing native report inbox.

        Images are strictly opt-in at Send; shakes never create network writes.
        """
        import base64
        import binascii
        import logging
        from html import escape

        from aiogram.types import BufferedInputFile
        from app.services.admin_notify_service import AdminNotifyService
        from app.services.admin_pwa_native_reports import (
            NativeReportRateLimited, finish_native_report, reserve_native_report,
        )

        admission = None
        try:
            require_pwa_enabled(settings_obj)
            require_same_origin(request, settings_obj)
            if request.query_params or request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            # This learner report uses the authenticated PWA session and
            # Telegram admin recipients; it must not depend on enabling the
            # separate browser Admin PWA (which defaults to disabled).
            async with session_factory() as db:
                actor, _ = await PwaAuthService(db, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE),
                    request.headers.get("X-HSK-PWA-CSRF"),
                )
                report = await _small_json(request, PwaBugReport, max_bytes=800 * 1024)
            description = report.description.strip()
            if not 5 <= len(description) <= 2000 or len(report.app_version) > 40 or len(report.screen) > 80:
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            screenshot = None
            if report.screenshot_data_url:
                prefix = "data:image/jpeg;base64,"
                if not report.screenshot_data_url.startswith(prefix) or len(report.screenshot_data_url) > 750_000:
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                try:
                    screenshot = base64.b64decode(
                        report.screenshot_data_url[len(prefix):], validate=True,
                    )
                except (ValueError, binascii.Error):
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                if len(screenshot) > 550 * 1024 or not screenshot.startswith(b"\xff\xd8\xff"):
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
            try:
                admission = await reserve_native_report(
                    session_factory, user_id=actor.id, description=description,
                    app_version=report.app_version, screen=report.screen,
                    screenshot=screenshot,
                )
            except NativeReportRateLimited:
                raise PwaAuthError("pwa_report_rate_limited", status_code=429)
            if admission.already_sent:
                return JSONResponse({"ok": True}, headers=_NO_STORE)
            if bot is None:
                raise PwaAuthError("pwa_report_unavailable", status_code=503)
            recipients = AdminNotifyService()._feedback_recipient_ids()
            if not recipients:
                raise PwaAuthError("pwa_report_unavailable", status_code=503)
            title = "🐞 HSK AI iPhone PWA — muammo xabari"
            message = (
                f"{title}\n🆔 User ID: {actor.id}\n"
                f"📱 Versiya: {escape(report.app_version)}\n"
                f"📍 Ekran: {escape(report.screen)}\n\n"
                f"📝 {escape(description)}"
            )
            delivered = 0
            for recipient in recipients:
                try:
                    if screenshot is not None:
                        await bot.send_photo(
                            chat_id=recipient,
                            photo=BufferedInputFile(screenshot, filename="iphone-pwa-report.jpg"),
                            caption=title,
                        )
                    await bot.send_message(chat_id=recipient, text=message)
                    delivered += 1
                except Exception as exc:
                    logging.getLogger(__name__).error(
                        "PWA report delivery failed (%s)", type(exc).__name__,
                    )
            if not delivered:
                raise PwaAuthError("pwa_report_unavailable", status_code=503)
            await finish_native_report(session_factory, admission.report_id, delivered=True)
            return JSONResponse({"ok": True}, headers=_NO_STORE)
        except PwaAuthError as exc:
            failure = exc
        except Exception as exc:
            # Never log report text, image bytes, cookies or CSRF.
            logging.getLogger(__name__).error(
                "PWA bug report failed (%s)", type(exc).__name__,
            )
            failure = PwaAuthError("pwa_report_unavailable", status_code=503)
        if admission is not None:
            try:
                await finish_native_report(session_factory, admission.report_id, delivered=False)
            except Exception as exc:
                logging.getLogger(__name__).error(
                    "PWA report outcome failed (%s)", type(exc).__name__,
                )
        return _error(failure)

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
                        current=feedback.liked_code,
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
                        current=feedback.liked_code,
                    ),
                } if feedback else None)
            return JSONResponse(
                {"ok": True, "ordinary": payload}, headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/feedback/lesson/prepare")
    async def pwa_prepare_lesson_feedback(request: Request):
        """Prepare the existing learner feedback only for saved course lessons."""
        from datetime import datetime, timezone
        from sqlalchemy import select
        from app.db.models.user import User
        from app.repositories.course_progress_repo import CourseProgressRepository
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
                payload = await _small_json(
                    request, PwaLessonFeedbackPrepare, max_bytes=256,
                )
                if not 1 <= payload.lesson_id <= 500:
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                learner = (await db.execute(
                    select(User).where(User.id == actor.id).with_for_update()
                )).scalar_one()
                progress = await CourseProgressRepository(db).get_by_user_id(learner.id)
                if (not progress or str(progress.level or "").lower() != payload.level
                        or int(progress.completed_lessons_count or 0) < payload.lesson_id):
                    raise PwaAuthError("lesson_not_completed", status_code=409)

                now = datetime.now(timezone.utc)
                service = BotFeedbackService(db)
                feedback = None
                if _pwa_feedback_prompt_eligible(learner, service, now):
                    feedback = await service._get_or_create_due_feedback(learner, now)
                    if feedback and not service._is_prompt_due(feedback, now):
                        feedback = None
                await db.commit()
                ordinary = ({
                    "feedback_id": feedback.id,
                    "paid": UserAccessStateService.is_paid(learner),
                    "liked_code": feedback.liked_code,
                    "disliked_code": feedback.disliked_code,
                    "choices": _pwa_feedback_choices(
                        learner.language,
                        paid=UserAccessStateService.is_paid(learner),
                        current=feedback.liked_code,
                    ),
                } if feedback else None)
            return JSONResponse({"ok": True, "ordinary": ordinary}, headers=_NO_STORE)
        except PwaAuthError as exc:
            return _error(exc)

    @router.post("/api/v3/pwa/feedback/ordinary/submit")
    async def pwa_ordinary_feedback_submit(request: Request):
        """Commit one existing ordinary bot feedback using its canonical rules."""
        from sqlalchemy import select
        from app.bot.keyboards.feedback import (
            ACCEPTED_LIKED_OPTIONS, ACCEPTED_PAID_SUB_POSITIVE,
            DISLIKED_OPTIONS, LIKE_SUB_OPTIONS,
            PAID_OPTIONS, PAID_SUB_NEGATIVE,
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
                    subs = (ACCEPTED_PAID_SUB_POSITIVE if data.paid_code in ("worth", "useful")
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
                        data.liked_code not in ACCEPTED_LIKED_OPTIONS
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

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


async def _small_json(request: Request, model):
    if request.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
        raise PwaAuthError("pwa_request_invalid", status_code=415)
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 1024:
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


def create_pwa_auth_router(*, session_factory, settings_obj) -> APIRouter:
    router = APIRouter(tags=["pwa-auth"])

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

    @router.get("/api/v3/pwa/account-notices")
    async def account_notices(request: Request):
        """Stored account/service notices, separate from course feed.

        Reading this route is never a push delivery acknowledgment and must
        not alter Android->Telegram fallback or Smart Reminder policy.
        """
        try:
            from sqlalchemy import select
            from app.db.models.account_notice_delivery import AccountNoticeDelivery
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
            return JSONResponse(
                {"ok": True, "notices": notices}, headers=_NO_STORE,
            )
        except PwaAuthError as exc:
            return _error(exc)

    return router

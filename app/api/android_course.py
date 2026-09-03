"""Bearer-authenticated Course v3 transport for the native Android client.

Like the auth adapter, this is transport only. Access rules, XP, streak,
mistakes and completion idempotency all live in the shared course service; the
Android client cannot reach a different code path or a different decision.

The request models are reused from the desktop adapter so both clients are
validated by exactly the same constraints. The completion event id is expected
to look like ``android:<uuid>``, which already fits the shared pattern.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from pathlib import Path
import re
import tempfile
from typing import Callable

from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse, JSONResponse

from app.api.desktop_course import (
    DesktopCourseCompleteRequest,
    DesktopCourseLanguageRequest,
    DesktopCourseNotificationsRequest,
    bearer_access_token,
    course_error_response,
    validated_course_payload,
)
from app.repositories.user_repo import UserRepository
from app.services.android_course_service import AndroidCourseService
from app.services.course_v3_dictionary import (
    dictionary_for_language,
    dictionary_version,
)
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.desktop_course_service import DesktopCourseError


logger = logging.getLogger(__name__)

MIN_LESSON_ORDER = 1
MAX_LESSON_ORDER = 500
MIN_TZ_OFFSET_MINUTES = -720
MAX_TZ_OFFSET_MINUTES = 840
ANDROID_TTS_VOICE = "zh-CN-XiaoxiaoNeural"
ANDROID_TTS_RATE = "-10%"
# Keep generated speech outside `app/static`: the only download path must be
# the bearer-authenticated endpoint above, never a guessable public asset URL.
ANDROID_TTS_CACHE_DIR = Path(tempfile.gettempdir()) / "pomp-hsk-ai-android-tts"
ANDROID_TTS_HEADERS = {
    "Cache-Control": "private, max-age=31536000, immutable",
    "X-Content-Type-Options": "nosniff",
}
_ANDROID_TTS_GENERATION_LOCK = asyncio.Lock()


def _unavailable() -> JSONResponse:
    return course_error_response(
        DesktopCourseError("android_course_unavailable", status_code=503)
    )


def _timezone_offset(request: Request) -> int | None:
    """Device timezone offset in minutes, bounded. Absent means 'unchanged'."""

    raw = request.query_params.get("tz")
    if raw is None:
        return None
    try:
        offset = int(raw)
    except (TypeError, ValueError) as exc:
        raise DesktopCourseError(
            "desktop_course_request_invalid",
            status_code=422,
        ) from exc
    # Note the explicit None check above: UTC+0 is a real offset and must not
    # be swallowed by a falsy test.
    if not MIN_TZ_OFFSET_MINUTES <= offset <= MAX_TZ_OFFSET_MINUTES:
        raise DesktopCourseError(
            "desktop_course_request_invalid",
            status_code=422,
        )
    return offset


def _android_tts_text(value: str | None) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 240 or not re.search(r"[\u4e00-\u9fff]", text):
        raise DesktopCourseError("android_tts_bad_text", status_code=400)
    return text


async def _android_tts_file(text: str) -> Path:
    """Create/reuse one deterministic MP3 without exposing arbitrary paths."""

    key = hashlib.sha256(
        f"{ANDROID_TTS_VOICE}|{ANDROID_TTS_RATE}|{text}".encode("utf-8")
    ).hexdigest()
    ANDROID_TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = ANDROID_TTS_CACHE_DIR / f"android-{key}.mp3"
    if path.is_file() and path.stat().st_size > 0:
        return path

    # A single generator lock bounds external TTS work even when an account
    # taps several audio buttons quickly. Cached reads never take this lock.
    async with _ANDROID_TTS_GENERATION_LOCK:
        if path.is_file() and path.stat().st_size > 0:
            return path
        tmp = path.with_suffix(".mp3.tmp")
        try:
            import edge_tts

            await edge_tts.Communicate(
                text,
                ANDROID_TTS_VOICE,
                rate=ANDROID_TTS_RATE,
            ).save(str(tmp))
            if not tmp.is_file() or tmp.stat().st_size <= 0:
                raise RuntimeError("empty Android TTS output")
            os.replace(tmp, path)
        except Exception as exc:
            logger.warning("Android TTS generation failed: %s", exc)
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise DesktopCourseError("android_tts_failed", status_code=502) from exc
    return path


def create_android_course_router(
    *,
    session_factory,
    settings_obj,
    service_factory: Callable[..., AndroidCourseService] = AndroidCourseService,
    bot=None,
) -> APIRouter:
    router = APIRouter(tags=["android-course"])

    @router.get("/api/v3/android/course/map")
    async def android_course_map(request: Request):
        try:
            offset = _timezone_offset(request)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).course_map(
                    bearer_access_token(request),
                    timezone_offset_minutes=offset,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("Android course map failed")
            return _unavailable()

    @router.get("/api/v3/android/course/lesson/{lesson_order}")
    async def android_course_lesson(request: Request, lesson_order: int):
        try:
            if not MIN_LESSON_ORDER <= lesson_order <= MAX_LESSON_ORDER:
                raise DesktopCourseError("invalid_lesson_order", status_code=422)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).lesson(
                    bearer_access_token(request),
                    lesson_order=lesson_order,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("Android course lesson failed")
            return _unavailable()

    @router.get("/api/v3/android/tts")
    async def android_tts(request: Request, text: str = ""):
        try:
            async with session_factory() as session:
                await DesktopAuthService(session, settings_obj).authenticate(
                    bearer_access_token(request)
                )
            phrase = _android_tts_text(text)
            path = await _android_tts_file(phrase)
            return FileResponse(
                path,
                media_type="audio/mpeg",
                headers=ANDROID_TTS_HEADERS,
            )
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("Android TTS failed")
            return _unavailable()

    @router.post("/api/v3/android/course/complete")
    async def android_course_complete(request: Request):
        try:
            payload = await validated_course_payload(
                request,
                DesktopCourseCompleteRequest,
            )
            async with session_factory() as session:
                # Bot berilmagan bo'lsa chaqiruv shakli aynan eskisicha
                # qoladi — mavjud testlar va fabrikalar buzilmaydi.
                service = (
                    service_factory(session, settings_obj, bot=bot)
                    if bot is not None
                    else service_factory(session, settings_obj)
                )
                result = await service.complete(
                    bearer_access_token(request),
                    lesson_order=payload.lesson_order,
                    event_id=payload.event_id,
                    mistakes=[
                        mistake.model_dump(exclude_none=True)
                        for mistake in payload.mistakes
                    ],
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("Android course completion failed")
            return _unavailable()

    @router.post("/api/v3/android/preferences/language")
    async def android_course_language(request: Request):
        try:
            payload = await validated_course_payload(
                request,
                DesktopCourseLanguageRequest,
            )
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).set_language(
                    bearer_access_token(request),
                    language=payload.language,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("Android course language update failed")
            return _unavailable()

    @router.get("/api/v3/android/dictionary")
    async def android_dictionary(request: Request):
        """
        The character dictionary, in the learner's own language.

        It is the same word list the Mini App's Lug'at shows — read from the
        one source rather than copied into the app, so the two can never drift
        apart. The payload carries a version; an unchanged version answers 304
        so the ~90 KB list is downloaded once, not on every open.
        """
        try:
            if request.query_params:
                raise DesktopCourseError("android_request_invalid", status_code=422)
            async with session_factory() as session:
                context = await DesktopAuthService(session, settings_obj).authenticate(
                    bearer_access_token(request),
                )
                user = await UserRepository(session).get_by_telegram_id(
                    int(context.user.telegram_id),
                )
                language = getattr(user, "language", None)

            version = dictionary_version()
            etag = f'W/"dictionary-{version}"'
            # The list only changes with a deploy, so a matching ETag means the
            # client's copy is still correct.
            if version and request.headers.get("If-None-Match") == etag:
                return Response(
                    status_code=304,
                    headers={"ETag": etag, "Cache-Control": "private, max-age=0"},
                )

            words = dictionary_for_language(language)
            return JSONResponse(
                content={
                    "ok": True,
                    "version": version,
                    "language": str(language or "ru"),
                    "words": words,
                },
                headers={
                    "ETag": etag,
                    "Cache-Control": "private, max-age=0",
                },
            )
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("Android dictionary failed")
            return _unavailable()

    @router.post("/api/v3/android/preferences/notifications")
    async def android_course_notifications(request: Request):
        """
        Reminder opt-in, sharing the canonical course preference.

        The bot, the Mini App, desktop and Android all read and write the same
        flag, so turning reminders off on one client turns them off everywhere.
        """
        try:
            payload = await validated_course_payload(
                request,
                DesktopCourseNotificationsRequest,
            )
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).set_notifications(
                    bearer_access_token(request),
                    enabled=payload.enabled,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("Android course notifications update failed")
            return _unavailable()

    return router

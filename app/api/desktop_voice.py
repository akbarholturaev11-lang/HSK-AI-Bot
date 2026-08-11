"""Bearer-authenticated desktop adapter around the canonical Voice Practice.

The Telegram Mini App reaches ``VoicePracticeService`` through
``/api/voice-practice/*`` with Telegram ``initData``. The desktop client has no
``initData``: it holds a short-lived desktop access token instead. This router
binds the very same service to the user resolved from a verified desktop
session, so limits, budget control, paid gating, corrections, mistakes and XP
stay owned by ``VoicePracticeService``.

Audio arrives as a base64 data URL instead of ``multipart/form-data`` because
the desktop webview cannot reach the network: the Rust side forwards a JSON
body over IPC, mirroring the existing subscription receipt transport.
"""

from __future__ import annotations

import base64
import logging
from typing import Annotated, Callable, Literal, TypeVar

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError

from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.voice_practice_service import (
    LANGUAGE_NAMES,
    MAX_AUDIO_BYTES,
    ROLE_PROMPTS,
    VoicePracticeError,
    VoicePracticeService,
)


logger = logging.getLogger(__name__)

MAX_DESKTOP_VOICE_BODY_BYTES = 32 * 1024
MAX_AUDIO_BASE64_CHARS = ((MAX_AUDIO_BYTES + 2) // 3) * 4
MAX_AUDIO_DATA_URL_CHARS = MAX_AUDIO_BASE64_CHARS + 40
MAX_DESKTOP_VOICE_AUDIO_BODY_BYTES = MAX_AUDIO_DATA_URL_CHARS + 16 * 1024

PayloadModel = TypeVar("PayloadModel", bound=BaseModel)

# macOS WKWebView records `audio/mp4`, Windows WebView2 records
# `audio/webm;codecs=opus`. Both platforms must be accepted or the desktop
# apps lose parity. The extension decides the filename handed to the STT
# provider, which uses it to pick a decoder.
AUDIO_KINDS: dict[str, tuple[str, str]] = {
    "data:audio/webm;base64": ("webm", "webm"),
    "data:audio/ogg;base64": ("ogg", "ogg"),
    "data:audio/mp4;base64": ("mp4", "mp4"),
    "data:audio/mpeg;base64": ("mp3", "mp3"),
    "data:audio/wav;base64": ("wav", "wav"),
}

# The canonical role list lives in ``ROLE_PROMPTS``. Membership is checked at
# request time so a new role never needs a second declaration here.
DesktopVoiceRole = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=40,
        pattern=r"^[a-z][a-z0-9_]*$",
    ),
]
DesktopVoiceLevel = Literal[
    "beginner", "hsk1", "hsk2", "hsk3", "hsk4", "hsk1_2", "hsk3_4"
]
DesktopVoiceLanguage = Literal["uz", "ru", "tj"]
DesktopVoiceVoice = Literal["female", "male"]
DesktopSessionId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9-]+$",
    ),
]
DesktopAudioDataUrl = Annotated[
    str,
    StringConstraints(min_length=32, max_length=MAX_DESKTOP_VOICE_AUDIO_BODY_BYTES),
]
DesktopPronounceTarget = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
DesktopPronouncePinyin = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=240)
]


class DesktopVoiceStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: DesktopVoiceRole
    level: DesktopVoiceLevel
    language: DesktopVoiceLanguage
    voice: DesktopVoiceVoice = "female"


class DesktopVoiceMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: DesktopSessionId
    audio_data_url: DesktopAudioDataUrl


class DesktopVoicePronounceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: DesktopPronounceTarget
    target_pinyin: DesktopPronouncePinyin = ""
    language: DesktopVoiceLanguage
    level: DesktopVoiceLevel
    audio_data_url: DesktopAudioDataUrl


class DesktopVoiceEndRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: DesktopSessionId


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
    max_body_bytes: int = MAX_DESKTOP_VOICE_BODY_BYTES,
) -> PayloadModel:
    content_type = str(request.headers.get("Content-Type", "") or "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise VoicePracticeError(
            "DESKTOP_VOICE_REQUEST_INVALID",
            "Unsupported content type.",
            415,
        )

    content_length = str(request.headers.get("Content-Length", "") or "").strip()
    if content_length:
        try:
            parsed_length = int(content_length)
        except ValueError as exc:
            raise VoicePracticeError(
                "DESKTOP_VOICE_REQUEST_INVALID",
                "Invalid content length.",
                400,
            ) from exc
        if parsed_length < 0:
            raise VoicePracticeError(
                "DESKTOP_VOICE_REQUEST_INVALID",
                "Invalid content length.",
                400,
            )
        if parsed_length > max_body_bytes:
            raise VoicePracticeError(
                "AUDIO_TOO_LARGE",
                "Audio hajmi juda katta.",
                413,
            )

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > max_body_bytes:
            raise VoicePracticeError(
                "AUDIO_TOO_LARGE",
                "Audio hajmi juda katta.",
                413,
            )
    try:
        return model_type.model_validate_json(bytes(body))
    except (ValidationError, ValueError, TypeError) as exc:
        raise VoicePracticeError(
            "DESKTOP_VOICE_REQUEST_INVALID",
            "Invalid request payload.",
            422,
        ) from exc


def _decode_audio_data_url(value: str) -> tuple[bytes, str]:
    """Return ``(audio_bytes, filename)`` for a validated audio data URL."""

    prefix, separator, raw_base64 = str(value or "").partition(",")
    kind = AUDIO_KINDS.get(prefix)
    if not separator or not kind or not raw_base64:
        raise VoicePracticeError(
            "INVALID_AUDIO_FORMAT",
            "Audio format is not supported.",
            422,
        )
    audio_kind, extension = kind
    if len(raw_base64) > MAX_AUDIO_BASE64_CHARS:
        raise VoicePracticeError("AUDIO_TOO_LARGE", "Audio hajmi juda katta.", 413)
    try:
        decoded = base64.b64decode(raw_base64, validate=True)
    except Exception as exc:
        raise VoicePracticeError(
            "INVALID_AUDIO_FORMAT",
            "Audio could not be decoded.",
            422,
        ) from exc
    if not decoded:
        raise VoicePracticeError("EMPTY_AUDIO", "Audio bo'sh.", 400)
    if len(decoded) > MAX_AUDIO_BYTES:
        raise VoicePracticeError("AUDIO_TOO_LARGE", "Audio hajmi juda katta.", 413)

    # Container signature check. A wrong prefix would otherwise reach the STT
    # provider as a paid request that can only fail.
    signature_matches = {
        "webm": decoded.startswith(b"\x1a\x45\xdf\xa3"),
        "ogg": decoded.startswith(b"OggS"),
        "mp4": len(decoded) >= 12 and decoded[4:8] == b"ftyp",
        "mp3": decoded.startswith(b"ID3") or decoded[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"),
        "wav": (
            len(decoded) >= 12
            and decoded.startswith(b"RIFF")
            and decoded[8:12] == b"WAVE"
        ),
    }
    if not signature_matches[audio_kind]:
        raise VoicePracticeError(
            "INVALID_AUDIO_FORMAT",
            "Audio content does not match its declared format.",
            422,
        )
    return decoded, f"voice.{extension}"


def _error_response(error: DesktopAuthError | VoicePracticeError) -> JSONResponse:
    code = getattr(error, "code", "DESKTOP_VOICE_UNAVAILABLE")
    return JSONResponse(
        status_code=getattr(error, "status_code", 400),
        content={"ok": False, "error": code},
        headers={"Cache-Control": "no-store"},
    )


def create_desktop_voice_router(
    *,
    session_factory,
    settings_obj,
    service_factory: Callable[..., VoicePracticeService] = VoicePracticeService,
) -> APIRouter:
    router = APIRouter(tags=["desktop-voice"])

    async def _telegram_id(session, request: Request) -> int:
        context = await DesktopAuthService(session, settings_obj).authenticate(
            _access_token(request)
        )
        return int(context.user.telegram_id)

    @router.get("/api/v3/desktop/voice/status")
    async def desktop_voice_status(request: Request):
        try:
            if request.query_params:
                raise VoicePracticeError(
                    "DESKTOP_VOICE_REQUEST_INVALID",
                    "Unexpected query parameters.",
                    422,
                )
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await service_factory(session).user_status(telegram_id)
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, VoicePracticeError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop voice status failed")
            return _error_response(
                VoicePracticeError(
                    "DESKTOP_VOICE_UNAVAILABLE",
                    "Voice practice unavailable.",
                    503,
                )
            )

    @router.post("/api/v3/desktop/voice/session/start")
    async def desktop_voice_start(request: Request):
        try:
            payload = await _validated_payload(request, DesktopVoiceStartRequest)
            if payload.language not in LANGUAGE_NAMES:
                raise VoicePracticeError(
                    "DESKTOP_VOICE_REQUEST_INVALID",
                    "Unsupported language.",
                    422,
                )
            if payload.role not in ROLE_PROMPTS:
                raise VoicePracticeError(
                    "INVALID_ROLE",
                    "Unknown conversation role.",
                    422,
                )
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await service_factory(session).start_session(
                    telegram_id,
                    role=payload.role,
                    level=payload.level,
                    language=payload.language,
                    voice=payload.voice,
                )
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, VoicePracticeError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop voice session start failed")
            return _error_response(
                VoicePracticeError(
                    "DESKTOP_VOICE_UNAVAILABLE",
                    "Voice practice unavailable.",
                    503,
                )
            )

    @router.post("/api/v3/desktop/voice/message")
    async def desktop_voice_message(request: Request):
        try:
            payload = await _validated_payload(
                request,
                DesktopVoiceMessageRequest,
                max_body_bytes=MAX_DESKTOP_VOICE_AUDIO_BODY_BYTES,
            )
            audio_bytes, filename = _decode_audio_data_url(payload.audio_data_url)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await service_factory(session).process_message(
                    telegram_id,
                    session_id=payload.session_id,
                    audio_bytes=audio_bytes,
                    filename=filename,
                )
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, VoicePracticeError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop voice message failed")
            return _error_response(
                VoicePracticeError(
                    "DESKTOP_VOICE_UNAVAILABLE",
                    "Voice practice unavailable.",
                    503,
                )
            )

    @router.post("/api/v3/desktop/voice/pronounce")
    async def desktop_voice_pronounce(request: Request):
        try:
            payload = await _validated_payload(
                request,
                DesktopVoicePronounceRequest,
                max_body_bytes=MAX_DESKTOP_VOICE_AUDIO_BODY_BYTES,
            )
            audio_bytes, filename = _decode_audio_data_url(payload.audio_data_url)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await service_factory(session).score_pronunciation(
                    telegram_id,
                    target=payload.target,
                    target_pinyin=payload.target_pinyin,
                    audio_bytes=audio_bytes,
                    filename=filename,
                    language=payload.language,
                    level=payload.level,
                )
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, VoicePracticeError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop voice pronounce failed")
            return _error_response(
                VoicePracticeError(
                    "DESKTOP_VOICE_UNAVAILABLE",
                    "Voice practice unavailable.",
                    503,
                )
            )

    @router.post("/api/v3/desktop/voice/session/end")
    async def desktop_voice_end(request: Request):
        try:
            payload = await _validated_payload(request, DesktopVoiceEndRequest)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await service_factory(session).end_session(
                    telegram_id,
                    payload.session_id,
                )
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, VoicePracticeError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop voice session end failed")
            return _error_response(
                VoicePracticeError(
                    "DESKTOP_VOICE_UNAVAILABLE",
                    "Voice practice unavailable.",
                    503,
                )
            )

    return router

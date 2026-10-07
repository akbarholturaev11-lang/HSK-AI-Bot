"""Authenticated WebSocket relay for Android real-time voice practice."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from sqlalchemy import or_, select, update

from app.db.models.voice_practice_session import VoicePracticeSession
from app.services.android_live_voice_service import (
    connect_gemini_live,
    live_voice_available,
)
from app.services.ai_service import AIUsageResult
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.voice_practice_service import (
    MAX_DIALOGS_PER_SESSION,
    VoicePracticeError,
    VoicePracticeService,
)


logger = logging.getLogger(__name__)
MAX_AUDIO_CHUNK_BYTES = 16_000
PCM_INPUT_BYTES_PER_SECOND = 16_000 * 2
PCM_OUTPUT_BYTES_PER_SECOND = 24_000 * 2


@dataclass(frozen=True)
class LiveSessionContext:
    id: str
    user_telegram_id: int
    mode: str
    role: str
    level: str
    language: str
    voice: str
    target_words: list
    plan_json: dict
    history: list
    live_resumption_handle: str | None
    live_started_at: datetime | None


def _bearer_token(value: str | None) -> str:
    scheme, separator, token = str(value or "").partition(" ")
    return token.strip() if separator and scheme.lower() == "bearer" else ""


def _append_transcript(current: str, chunk: str) -> str:
    next_text = str(chunk or "").strip()
    if not next_text:
        return current
    if not current:
        return next_text
    if next_text.startswith(current):
        return next_text
    overlap = min(len(current), len(next_text))
    while overlap and current[-overlap:] != next_text[:overlap]:
        overlap -= 1
    return (current + next_text[overlap:]).strip()


def _usage_result(metadata, model: str) -> AIUsageResult | None:
    if not metadata:
        return None
    prompt_tokens = int(
        getattr(metadata, "prompt_token_count", 0)
        or getattr(metadata, "input_token_count", 0)
        or 0
    )
    completion_tokens = int(
        getattr(metadata, "response_token_count", 0)
        or getattr(metadata, "candidate_token_count", 0)
        or getattr(metadata, "output_token_count", 0)
        or 0
    )
    total_tokens = int(getattr(metadata, "total_token_count", 0) or prompt_tokens + completion_tokens)
    if not prompt_tokens and not completion_tokens:
        return None
    return AIUsageResult(
        content="",
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )


async def _receive_live_responses(provider_session):
    """The SDK receive iterator ends after each turn, not after the session."""
    while True:
        received = False
        async for response in provider_session.receive():
            received = True
            yield response
        if not received:
            return


def create_android_live_voice_router(
    *,
    session_factory,
    settings_obj,
    voice_service_factory: Callable[..., VoicePracticeService] = VoicePracticeService,
    provider_connector=connect_gemini_live,
) -> APIRouter:
    router = APIRouter(tags=["android-live-voice"])

    @router.websocket("/api/v3/android/voice/live")
    async def android_live_voice(websocket: WebSocket):
        await websocket.accept()
        token = _bearer_token(websocket.headers.get("Authorization"))
        session_id = str(websocket.query_params.get("session_id") or "").strip()
        if not token or not 8 <= len(session_id) <= 120:
            await websocket.send_json({"type": "error", "code": "android_request_invalid"})
            await websocket.close(code=1008)
            return

        connection_token = str(uuid.uuid4())
        telegram_id = 0
        live_item = None
        configured_max_seconds = max(
            30,
            min(180, int(getattr(settings_obj, "ANDROID_VOICE_LIVE_MAX_SECONDS", 180))),
        )
        max_seconds = configured_max_seconds
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=max_seconds + 20)
        try:
            async with session_factory() as session:
                context = await DesktopAuthService(session, settings_obj).authenticate(token)
                telegram_id = int(context.user.telegram_id)
                if not live_voice_available(settings_obj, telegram_id):
                    raise DesktopAuthError("live_voice_unavailable", status_code=403)
                claimed = await session.execute(
                    update(VoicePracticeSession)
                    .where(
                        VoicePracticeSession.id == session_id,
                        VoicePracticeSession.user_telegram_id == telegram_id,
                        VoicePracticeSession.mode == "live",
                        VoicePracticeSession.status == "active",
                        or_(
                            VoicePracticeSession.live_connection_expires_at.is_(None),
                            VoicePracticeSession.live_connection_expires_at < datetime.now(timezone.utc),
                        ),
                    )
                    .values(
                        live_connection_token=connection_token,
                        live_connection_expires_at=expires_at,
                    )
                )
                if claimed.rowcount != 1:
                    raise VoicePracticeError("LIVE_SESSION_BUSY", "Live session is not available.", 409)
                await session.commit()
                result = await session.execute(
                    select(VoicePracticeSession).where(
                        VoicePracticeSession.id == session_id,
                        VoicePracticeSession.user_telegram_id == telegram_id,
                        VoicePracticeSession.live_connection_token == connection_token,
                    )
                )
                row = result.scalar_one_or_none()
                if row is None:
                    raise VoicePracticeError("SESSION_NOT_FOUND", "Voice session not found.", 404)
                live_item = LiveSessionContext(
                    id=row.id,
                    user_telegram_id=telegram_id,
                    mode=row.mode,
                    role=row.role,
                    level=row.level,
                    language=row.language,
                    voice=row.voice,
                    target_words=list(row.target_words or []),
                    plan_json=dict(row.plan_json or {}),
                    history=list(row.history or []),
                    live_resumption_handle=row.live_resumption_handle,
                    live_started_at=row.live_started_at,
                )
                started_at = live_item.live_started_at or datetime.now(timezone.utc)
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)
                max_seconds = max(
                    0,
                    int(
                        (
                            started_at
                            + timedelta(seconds=configured_max_seconds)
                            - datetime.now(timezone.utc)
                        ).total_seconds()
                    ),
                )

            if max_seconds <= 0:
                await websocket.send_json({"type": "error", "code": "live_session_expired"})
                await websocket.close(code=1008)
                return

            async with provider_connector(settings_obj, live_item) as provider_session:
                from google.genai import types

                await websocket.send_json(
                    {
                        "type": "ready",
                        "input_sample_rate": 16000,
                        "output_sample_rate": 24000,
                        "max_dialogs": MAX_DIALOGS_PER_SESSION,
                        "max_seconds": max_seconds,
                    }
                )

                send_lock = asyncio.Lock()

                async def send_event(payload: dict) -> None:
                    async with send_lock:
                        await websocket.send_json(payload)

                audio_stats = {"input_bytes": 0}
                typed_inputs: asyncio.Queue[str] = asyncio.Queue()

                async def receive_from_android():
                    input_bytes = 0
                    started_at = time.monotonic()
                    while True:
                        message = await websocket.receive()
                        if message.get("type") == "websocket.disconnect":
                            return
                        text = message.get("text")
                        if text is not None:
                            if len(text) > 1000:
                                await send_event({"type": "error", "code": "android_request_invalid"})
                                return
                            try:
                                command = json.loads(text)
                            except json.JSONDecodeError:
                                await send_event({"type": "error", "code": "android_request_invalid"})
                                return
                            if command.get("type") == "stop":
                                return
                            if command.get("type") == "text":
                                typed_text = str(command.get("text") or "").strip()[:200]
                                if typed_text:
                                    await provider_session.send_realtime_input(text=typed_text)
                                    await typed_inputs.put(typed_text)
                                continue
                            if command.get("type") == "ping":
                                await send_event({"type": "pong"})
                            continue
                        audio = message.get("bytes")
                        if not audio:
                            continue
                        if len(audio) > MAX_AUDIO_CHUNK_BYTES:
                            await send_event({"type": "error", "code": "live_audio_chunk_too_large"})
                            return
                        input_bytes += len(audio)
                        audio_stats["input_bytes"] += len(audio)
                        elapsed = max(0.0, time.monotonic() - started_at)
                        # A small lead tolerates network batching while preventing
                        # clients from replaying minutes of audio in a short burst.
                        if input_bytes / PCM_INPUT_BYTES_PER_SECOND > elapsed + 5:
                            await send_event({"type": "error", "code": "live_audio_rate_exceeded"})
                            return
                        await provider_session.send_realtime_input(
                            audio=types.Blob(
                                data=audio,
                                mime_type="audio/pcm;rate=16000",
                            )
                        )

                async def send_to_android():
                    user_text = ""
                    assistant_text = ""
                    latest_usage = None
                    total_output_bytes = 0
                    session_output_bytes = 0
                    session_cost_usd = 0.0
                    completed_turns = 0
                    budget_cap = max(
                        0.01,
                        float(getattr(settings_obj, "ANDROID_VOICE_LIVE_SESSION_BUDGET_USD", 0.15) or 0.15),
                    )
                    model = str(getattr(settings_obj, "ANDROID_VOICE_LIVE_MODEL", "gemini-3.8-live"))
                    async for response in _receive_live_responses(provider_session):
                        resumption = getattr(response, "session_resumption_update", None)
                        resumption_handle = str(getattr(resumption, "new_handle", "") or "")
                        if resumption_handle:
                            async with session_factory() as session:
                                await session.execute(
                                    update(VoicePracticeSession)
                                    .where(
                                        VoicePracticeSession.id == session_id,
                                        VoicePracticeSession.user_telegram_id == telegram_id,
                                        VoicePracticeSession.live_connection_token == connection_token,
                                    )
                                    .values(live_resumption_handle=resumption_handle)
                                )
                                await session.commit()
                        usage = _usage_result(getattr(response, "usage_metadata", None), model)
                        if usage is not None:
                            latest_usage = usage
                        content = getattr(response, "server_content", None)
                        if content is None:
                            continue
                        input_transcription = getattr(content, "input_transcription", None)
                        if input_transcription:
                            user_text = _append_transcript(user_text, getattr(input_transcription, "text", ""))
                        if getattr(content, "interrupted", False):
                            assistant_text = ""
                            await send_event({"type": "interrupted"})
                            continue
                        output_transcription = getattr(content, "output_transcription", None)
                        if output_transcription:
                            assistant_text = _append_transcript(
                                assistant_text,
                                getattr(output_transcription, "text", ""),
                            )
                        model_turn = getattr(content, "model_turn", None)
                        for part in getattr(model_turn, "parts", []) if model_turn else []:
                            inline = getattr(part, "inline_data", None)
                            if not inline:
                                continue
                            audio_data = getattr(inline, "data", b"")
                            if isinstance(audio_data, str):
                                try:
                                    audio_bytes = base64.b64decode(audio_data, validate=True)
                                except ValueError:
                                    audio_bytes = b""
                            else:
                                audio_bytes = bytes(audio_data or b"")
                            if audio_bytes:
                                total_output_bytes += len(audio_bytes)
                                session_output_bytes += len(audio_bytes)
                                await send_event(
                                    {"type": "audio", "data": base64.b64encode(audio_bytes).decode("ascii")}
                                )

                        if getattr(content, "turn_complete", False):
                            while not typed_inputs.empty():
                                user_text = _append_transcript(user_text, typed_inputs.get_nowait())
                            if user_text and assistant_text:
                                if latest_usage is None:
                                    # Conservative fallback: streamed audio is
                                    # charged once for each completed model turn.
                                    prompt_tokens = int(
                                        (
                                            (audio_stats["input_bytes"] / PCM_INPUT_BYTES_PER_SECOND)
                                            + (session_output_bytes / PCM_OUTPUT_BYTES_PER_SECOND)
                                        )
                                        * max(1, completed_turns + 1)
                                        * 25
                                    ) + 1000
                                    output_tokens = int(
                                        (total_output_bytes / PCM_OUTPUT_BYTES_PER_SECOND) * 25
                                    )
                                    latest_usage = AIUsageResult(
                                        content="",
                                        model=model,
                                        prompt_tokens=prompt_tokens,
                                        completion_tokens=output_tokens,
                                        total_tokens=prompt_tokens + output_tokens,
                                    )
                                async with session_factory() as session:
                                    turn = await voice_service_factory(session).process_live_turn(
                                        telegram_id,
                                        session_id=session_id,
                                        transcription=user_text,
                                        assistant_text=assistant_text,
                                        provider_usage=latest_usage,
                                    )
                                session_cost_usd = float(turn.get("session_cost_usd") or session_cost_usd)
                                completed_turns = int(turn.get("turn_count") or completed_turns + 1)
                                await send_event({"type": "turn_complete", **turn})
                                user_text = ""
                                assistant_text = ""
                                latest_usage = None
                                total_output_bytes = 0
                                if turn.get("session_should_end"):
                                    await send_event({"type": "session_limit"})
                                    return
                                if session_cost_usd >= budget_cap:
                                    await send_event({"type": "budget_limit"})
                                    return
                            else:
                                # Do not charge or count an incomplete transcript.
                                user_text = ""
                                assistant_text = ""
                                latest_usage = None
                                total_output_bytes = 0

                client_task = asyncio.create_task(receive_from_android())
                provider_task = asyncio.create_task(send_to_android())
                done, pending = await asyncio.wait(
                    {client_task, provider_task},
                    timeout=max_seconds,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if not done:
                    await websocket.send_json({"type": "time_limit"})
                for task in pending:
                    task.cancel()
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)
                for task in done:
                    if task.cancelled():
                        continue
                    error = task.exception()
                    if error:
                        raise error
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.close(code=1000)
        except (DesktopAuthError, VoicePracticeError) as exc:
            code = getattr(exc, "code", "live_voice_unavailable")
            logger.info("Android Live Voice refused: %s", code)
            try:
                await websocket.send_json({"type": "error", "code": code})
                await websocket.close(code=1008)
            except Exception:  # noqa: BLE001
                pass
        except WebSocketDisconnect:
            pass
        except Exception:  # noqa: BLE001
            logger.exception("Android Live Voice relay failed for user %s", telegram_id or "unknown")
            try:
                await websocket.send_json({"type": "error", "code": "live_voice_unavailable"})
                await websocket.close(code=1011)
            except Exception:  # noqa: BLE001
                pass
        finally:
            if connection_token and telegram_id:
                try:
                    async with session_factory() as session:
                        await session.execute(
                            update(VoicePracticeSession)
                            .where(
                                VoicePracticeSession.id == session_id,
                                VoicePracticeSession.user_telegram_id == telegram_id,
                                VoicePracticeSession.live_connection_token == connection_token,
                            )
                            .values(
                                live_connection_token=None,
                                live_connection_expires_at=None,
                            )
                        )
                        await session.commit()
                except Exception:  # noqa: BLE001 — expiry is the fallback release
                    logger.exception("Android Live Voice lock release failed")

    return router

"""Mandarin lesson audio shared by Mini App and Android.

Prefer Edge neural speech; if Microsoft's endpoint rejects synthesis, generate
server-side audio with Gemini TTS. Edge uses MP3; Gemini PCM is wrapped in WAV.
The caller must set the MIME type from the returned file suffix.
"""
from __future__ import annotations

import asyncio
import base64
from collections import deque
import hashlib
from io import BytesIO
import logging
import os
from pathlib import Path
import re
import time
from uuid import uuid4
import wave

import httpx

VOICE = "zh-CN-XiaoxiaoNeural"
RATE = "-10%"
GEMINI_MODEL = "gemini-2.5-flash-preview-tts"
GEMINI_VOICE = "Kore"
log = logging.getLogger(__name__)
_edge_retry_at = 0.0
_locks: dict[str, asyncio.Lock] = {}
_edge_gate = asyncio.Semaphore(2)
_paid_gate = asyncio.Semaphore(3)
_paid_times: deque[float] = deque()


class TTSUnavailable(Exception):
    """No configured provider generated a valid audio file."""


def _cache_dir() -> Path:
    return Path(os.getenv("HSK_TTS_CACHE_DIR") or "app/static/audio/tts_cache")


def _cache_key(text: str, rate: str) -> str:
    # Keep existing Edge MP3 filenames valid across this migration.
    return hashlib.sha1(f"{VOICE}|{rate}|{text}".encode("utf-8")).hexdigest()


def _bundled_word_audio(text: str, rate: str) -> Path | None:
    """Reuse the Android APK's 1,247 existing Edge MP3s for the Mini App too.

    These files were synthesized with the same Mandarin voice and -10% rate.
    Using them directly avoids Edge websocket and Gemini generation latency,
    including for a phrase that is being heard for the first time.
    """
    if rate != RATE or len(text) > 80:
        return None
    audio_dir = Path(__file__).resolve().parents[2] / (
        "android/app/src/main/assets/audio/words"
    )
    name = "_".join(str(ord(char)) for char in text) + ".mp3"
    path = audio_dir / name
    if path.is_file() and path.stat().st_size > 128:
        return path
    return None


def _cached_audio(folder: Path, key: str) -> Path | None:
    for suffix in (".mp3", ".wav"):
        path = folder / (key + suffix)
        if path.is_file() and path.stat().st_size > 128:
            return path
    return None


def _wav_from_pcm(pcm: bytes, sample_rate: int = 24000) -> bytes:
    if len(pcm) < 128 or len(pcm) % 2:
        raise TTSUnavailable("gemini_invalid_pcm")
    if sample_rate not in (8000, 16000, 22050, 24000, 32000, 44100, 48000):
        raise TTSUnavailable("gemini_invalid_sample_rate")
    output = BytesIO()
    with wave.open(output, "wb") as audio_file:
        audio_file.setnchannels(1)
        audio_file.setsampwidth(2)
        audio_file.setframerate(sample_rate)
        audio_file.writeframes(pcm)
    return output.getvalue()


async def _edge(text: str, rate: str, destination: Path) -> None:
    global _edge_retry_at
    async with _edge_gate:
        if time.monotonic() < _edge_retry_at:
            raise TTSUnavailable("edge_paused")
        try:
            import edge_tts

            await asyncio.wait_for(
                edge_tts.Communicate(text, VOICE, rate=rate).save(str(destination)),
                timeout=9,
            )
            if not destination.is_file() or destination.stat().st_size < 128:
                raise TTSUnavailable("edge_empty")
            _edge_retry_at = 0.0
        except Exception as exc:
            # A 403 storm would otherwise trigger a fresh websocket per card.
            _edge_retry_at = time.monotonic() + (600 if "403" in str(exc) else 45)
            log.warning("Mandarin Edge TTS unavailable: %s", type(exc).__name__)
            raise


async def _reserve_gemini_budget() -> None:
    now = time.monotonic()
    while _paid_times and _paid_times[0] <= now - 3600:
        _paid_times.popleft()
    try:
        limit = max(0, int(os.getenv("HSK_TTS_GEMINI_MAX_HOURLY", "300")))
    except ValueError:
        limit = 300
    if len(_paid_times) >= limit:
        raise TTSUnavailable("gemini_hourly_cap")
    _paid_times.append(now)


async def _fallback(text: str, rate: str) -> bytes:
    """Return playable RIFF/WAV bytes from Gemini's 24 kHz 16-bit PCM."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or os.getenv("HSK_TTS_GEMINI_ENABLED", "1").lower() in ("0", "false", "no"):
        raise TTSUnavailable("gemini_disabled_or_no_key")

    model = os.getenv("HSK_TTS_GEMINI_MODEL") or GEMINI_MODEL
    if not re.fullmatch(r"gemini-[a-zA-Z0-9._-]+", model):
        raise TTSUnavailable("gemini_invalid_model")

    async with _paid_gate:
        await _reserve_gemini_budget()
        pace = max(60, min(140, 100 + int(rate[:-1])))
        payload = {
            "contents": [{"parts": [{"text":
                "Read ONLY the text between the Chinese brackets aloud in clear "
                "Standard Mandarin (Putonghua), with correct tones and no "
                f"extra words or translation. Speak at about {pace}% of normal "
                f"speed: 【{text}】"
            }]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": GEMINI_VOICE}}
                },
            },
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(35.0, connect=5.0)) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts") or []
        inline = next((part.get("inlineData") or part.get("inline_data")
                       for part in parts if part.get("inlineData") or part.get("inline_data")), None)
        if not inline:
            raise TTSUnavailable("gemini_missing_audio")
        pcm = base64.b64decode(inline.get("data", ""), validate=True)
        mime = str(inline.get("mimeType") or inline.get("mime_type") or "")
        if pcm.startswith(b"RIFF") and pcm[8:12] == b"WAVE":
            return pcm
        if "audio/" not in mime.lower():
            raise TTSUnavailable("gemini_unexpected_mime")
        match = re.search(r"rate=(\d+)", mime)
        return _wav_from_pcm(pcm, int(match.group(1)) if match else 24000)


async def synthesize_chinese_mp3(text: str, rate: str = RATE) -> Path:
    """Compatibility name: returns cached MP3 from Edge OR WAV from Gemini."""
    text = str(text or "").strip()
    if not text or len(text) > 240 or not re.search(r"[一-鿿]", text):
        raise ValueError("invalid_mandarin_text")
    if not re.fullmatch(r"[+-]\d{1,3}%", rate):
        rate = RATE

    bundled = _bundled_word_audio(text, rate)
    if bundled is not None:
        return bundled

    folder = _cache_dir()
    folder.mkdir(parents=True, exist_ok=True)
    key = _cache_key(text, rate)
    cached = _cached_audio(folder, key)
    if cached is not None:
        return cached

    async with _locks.setdefault(key, asyncio.Lock()):
        cached = _cached_audio(folder, key)
        if cached is not None:
            return cached

        temporary = folder / (key + "." + uuid4().hex + ".tmp")
        try:
            try:
                await _edge(text, rate, temporary)
                destination = folder / (key + ".mp3")
                provider = "edge"
            except Exception:
                temporary.unlink(missing_ok=True)
                try:
                    temporary.write_bytes(await _fallback(text, rate))
                except Exception as exc:
                    log.warning("Mandarin Gemini backup unavailable: %s status=%s",
                                type(exc).__name__,
                                getattr(getattr(exc, "response", None), "status_code", None))
                    raise TTSUnavailable("all_providers_failed") from exc
                destination = folder / (key + ".wav")
                provider = "gemini"

            if not temporary.is_file() or temporary.stat().st_size < 128:
                raise TTSUnavailable("tts_empty_audio")
            os.replace(temporary, destination)
            log.info("Mandarin TTS generated: provider=%s characters=%d", provider, len(text))
            return destination
        finally:
            temporary.unlink(missing_ok=True)

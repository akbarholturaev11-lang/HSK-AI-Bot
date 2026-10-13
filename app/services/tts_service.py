"""Mandarin lesson audio shared by Mini App and Android.

Prefer Edge neural speech; if Microsoft's endpoint rejects synthesis, generate
server-side audio with Gemini TTS. Edge uses MP3; Gemini PCM is wrapped in WAV.
The caller must set the MIME type from the returned file suffix.
"""
from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from collections import deque
import hashlib
from io import BytesIO
import logging
import os
from pathlib import Path
import re
import time
from urllib.parse import quote
from uuid import uuid4
import wave

import httpx

VOICE = "zh-CN-XiaoxiaoNeural"
RATE = "-10%"
GEMINI_MODEL = "gemini-2.5-flash-preview-tts"
GEMINI_VOICE = "Kore"
log = logging.getLogger(__name__)
_edge_retry_at = 0.0
_gemini_retry_at = 0.0
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

    # HSK 3.0 greeting is absent from the bundled Xiaoxiao word MP3s.
    # Use the local CC BY-SA pronunciation (ni2 + hao3 with tone sandhi).
    # This avoids Edge/Gemini network failures; attribution in THIRD_PARTY_AUDIO.md.
    if text == "你好":
        emergency = Path(__file__).resolve().parents[2] / (
            "app/static/audio/tts_fallback/nihao-cc-by-sa.mp3"
        )
        if emergency.is_file() and emergency.stat().st_size > 128:
            return emergency
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
            import edge_tts.communicate as edge_communicate
            from edge_tts.constants import TRUSTED_CLIENT_TOKEN

            # Microsoft started rejecting edge-tts 7.2.8's legacy Bing
            # WebSocket endpoint with HTTP 403 in October 2026. Preserve
            # the same neural voice, rate and authentication token; only
            # use the working Edge Read Aloud synthesis endpoint.
            edge_communicate.WSS_URL = (
                "wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1"
                f"?Ocp-Apim-Subscription-Key={TRUSTED_CLIENT_TOKEN}"
            )

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
            log.warning(
                "Mandarin Edge TTS unavailable: type=%s status=%s reason=%s",
                type(exc).__name__,
                getattr(exc, "status_code", None) or getattr(exc, "status", None),
                re.sub(r"(?i)(https?://|wss?://)[^\\s]+", "[redacted-url]", str(getattr(exc, "message", "") or ""))[:120],
            )
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


def _gemini_retry_delay(response: httpx.Response) -> float:
    """Respect provider Retry-After while bounding an in-process circuit break."""
    value = str(response.headers.get("Retry-After") or "").strip()
    try:
        seconds = float(value)
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            seconds = (date - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError, IndexError):
            seconds = 120.0
    if not 0 <= seconds <= 86400:
        seconds = 120.0
    return min(900.0, max(30.0, seconds))


async def _fallback(text: str, rate: str) -> bytes:
    """Return playable RIFF/WAV bytes from Gemini's 24 kHz 16-bit PCM."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or os.getenv("HSK_TTS_GEMINI_ENABLED", "1").lower() in ("0", "false", "no"):
        raise TTSUnavailable("gemini_disabled_or_no_key")

    model = os.getenv("HSK_TTS_GEMINI_MODEL") or GEMINI_MODEL
    if not re.fullmatch(r"gemini-[a-zA-Z0-9._-]+", model):
        raise TTSUnavailable("gemini_invalid_model")

    global _gemini_retry_at
    async with _paid_gate:
        if time.monotonic() < _gemini_retry_at:
            raise TTSUnavailable("gemini_cooling_down")
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
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (429, 503):
                    _gemini_retry_at = max(
                        _gemini_retry_at,
                        time.monotonic() + _gemini_retry_delay(exc.response),
                    )
                raise
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


def _public_mp3_urls(text: str, rate: str) -> tuple[str, ...]:
    """Public, credited Mandarin word recordings. Never send personal data."""
    if rate != RATE:
        return ()
    # This emergency source is for isolated words, not AI conversations or
    # long lesson sentences; trimming end punctuation does not change speech.
    word = text.strip().rstrip("。！？!?.,，")
    if not re.fullmatch(r"[\u3400-\u9fff]{1,12}", word):
        return ()
    urls: list[str] = []
    if word == "你好":
        # Sjors Provoost, CC BY-SA 3.0. Wikimedia Commons' MP3 transcode
        # preserves compatibility with Android 1.7.10's MP3-only playback.
        urls.append(
            "https://upload.wikimedia.org/wikipedia/commons/transcoded/"
            "7/7d/Zh_n%C7%90_h%C7%8Eo.ogg/Zh_n%C7%90_h%C7%8Eo.ogg.mp3"
        )
    # SWAC human recordings assembled by hugolpz/audio-cmn (CC BY-SA).
    # This is a best-effort network fallback, not an always-on dependency.
    urls.append(
        "https://raw.githubusercontent.com/hugolpz/audio-cmn/master/64k/hsk/"
        "cmn-" + quote(word, safe="") + ".mp3"
    )
    return tuple(urls)


def _valid_mp3(data: bytes) -> bool:
    return 128 <= len(data) <= 1024 * 1024 and (
        data.startswith(b"ID3") or
        (len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0)
    )


async def _public_mp3_fallback(text: str, rate: str) -> bytes:
    """Last resort: return real human speech in MP3 for older APKs.

    The URL list is controlled by the server and contains public word
    content only. Bad responses are never cached or served as audio.
    """
    urls = _public_mp3_urls(text, rate)
    if not urls:
        raise TTSUnavailable("no_licensed_word_recording")
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(5.0, connect=3.0), follow_redirects=True
    ) as client:
        for url in urls:
            try:
                response = await client.get(url, headers={"Accept": "audio/mpeg"})
                if response.status_code != 200:
                    continue
                if _valid_mp3(response.content):
                    log.info("Mandarin licensed recording fallback succeeded")
                    return response.content
            except (httpx.HTTPError, TimeoutError):
                continue
    raise TTSUnavailable("licensed_word_recording_unavailable")



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
                    try:
                        temporary.write_bytes(await _public_mp3_fallback(text, rate))
                    except Exception as backup_exc:
                        raise TTSUnavailable("all_providers_failed") from backup_exc
                    destination = folder / (key + ".mp3")
                    provider = "licensed_word_recording"
                else:
                    destination = folder / (key + ".wav")
                    provider = "gemini"

            if not temporary.is_file() or temporary.stat().st_size < 128:
                raise TTSUnavailable("tts_empty_audio")
            os.replace(temporary, destination)
            log.info("Mandarin TTS generated: provider=%s characters=%d", provider, len(text))
            return destination
        finally:
            temporary.unlink(missing_ok=True)

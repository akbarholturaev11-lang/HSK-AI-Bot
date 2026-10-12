"""Shared Mandarin lesson speech with an MP3 cache and provider failover."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from pathlib import Path
import re
import time

from openai import AsyncOpenAI

VOICE = "zh-CN-XiaoxiaoNeural"
RATE = "-10%"
log = logging.getLogger(__name__)
_edge_retry_at = 0.0
_locks: dict[str, asyncio.Lock] = {}
_edge_gate = asyncio.Semaphore(2)
_paid_gate = asyncio.Semaphore(3)
_paid_times: list[float] = []


class TTSUnavailable(Exception):
    pass


async def _edge(text: str, rate: str, path: Path) -> None:
    global _edge_retry_at
    async with _edge_gate:
        if time.monotonic() < _edge_retry_at:
            raise TTSUnavailable("edge_paused")
        try:
            import edge_tts
            await asyncio.wait_for(edge_tts.Communicate(text, VOICE, rate=rate).save(str(path)), 9)
            if not path.is_file() or path.stat().st_size < 100:
                raise TTSUnavailable("edge_empty")
            _edge_retry_at = 0
        except Exception as exc:
            _edge_retry_at = time.monotonic() + (600 if "403" in str(exc) else 45)
            log.warning("Mandarin Edge TTS unavailable: %s", type(exc).__name__)
            raise


async def _fallback(text: str, rate: str) -> bytes:
    if not os.getenv("OPENAI_API_KEY") or os.getenv("HSK_TTS_OPENAI_ENABLED", "1") == "0":
        raise TTSUnavailable("backup_disabled")
    async with _paid_gate:
        now = time.monotonic()
        _paid_times[:] = [at for at in _paid_times if at > now - 3600]
        if len(_paid_times) >= int(os.getenv("HSK_TTS_OPENAI_MAX_HOURLY", "300")):
            raise TTSUnavailable("backup_hourly_cap")
        _paid_times.append(now)
        model = os.getenv("HSK_TTS_OPENAI_MODEL", "gpt-4o-mini-tts")
        options = dict(model=model, voice="coral", input=text, response_format="mp3",
                       speed=max(.25, min(4.0, 1 + int(rate[:-1]) / 100)))
        if model.startswith("gpt-4o"):
            options["instructions"] = (
                "Speak only the provided Chinese text in natural Standard Mandarin. "
                "Use accurate tones and a patient teacher's voice. Do not translate."
            )
        async with AsyncOpenAI(timeout=20, max_retries=0) as client:
            response = await client.audio.speech.create(**options)
            audio = response.content
            if len(audio) < 100 or not (audio.startswith(b"ID3") or
                    (audio[0] == 255 and audio[1] & 224 == 224)):
                raise TTSUnavailable("invalid_audio")
            return audio


async def synthesize_chinese_mp3(text: str, rate: str = RATE) -> Path:
    text = str(text or "").strip()
    if len(text) > 240 or not re.search(r"[一-鿿]", text):
        raise ValueError("invalid_mandarin_text")
    if not re.fullmatch(r"[+-]\d{1,3}%", rate):
        rate = RATE
    folder = Path(os.getenv("HSK_TTS_CACHE_DIR", "app/static/audio/tts_cache"))
    folder.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f"{VOICE}|{rate}|{text}".encode()).hexdigest()
    path = folder / f"{key}.mp3"
    if path.is_file() and path.stat().st_size > 0:
        return path
    async with _locks.setdefault(key, asyncio.Lock()):
        if path.is_file() and path.stat().st_size > 0:
            return path
        tmp = folder / f"{key}.tmp"
        try:
            try:
                await _edge(text, rate, tmp)
                provider = "edge"
            except Exception:
                tmp.unlink(missing_ok=True)
                try:
                    tmp.write_bytes(await _fallback(text, rate))
                    provider = "openai"
                except Exception as exc:
                    log.warning("Mandarin backup TTS failed: %s", type(exc).__name__)
                    raise TTSUnavailable("all_providers_failed") from exc
            os.replace(tmp, path)
            log.info("Mandarin TTS generated: provider=%s length=%d", provider, len(text))
            return path
        finally:
            tmp.unlink(missing_ok=True)

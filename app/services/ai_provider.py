"""AI provayder zanjiri: Gemini asosiy, OpenAI zaxira.

Ish mantig'i (foydalanuvchi so'rovi bo'yicha):
- `GEMINI_API_KEY` sozlangan bo'lsa Gemini asosiy provayder bo'ladi.
- Gemini yo'q bo'lsa yoki ish vaqtida xato bersa, so'rov avtomatik OpenAI'ga o'tadi.
- Matn / vision / JSON javoblar Gemini'ning OpenAI-mos endpointi orqali ketadi
  (xuddi shu `AsyncOpenAI` mijozi, faqat `base_url` + kalit boshqa) — shuning uchun
  mavjud so'rov/javob kodi qayta ishlatiladi.
- STT (ovoz -> matn) Gemini'da alohida endpoint bo'lmagani uchun native `google-genai`
  SDK orqali (audio -> matn) amalga oshadi, OpenAI transkripsiyasi zaxira bo'lib qoladi.

Qaysi Gemini modeli ishlashini admin panel belgilaydi (`bot_settings` dagi
`active_gemini_model`), qiymat qisqa muddatli keshda saqlanadi.
"""

import logging
import time
from typing import Optional

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

GEMINI_OPENAI_COMPAT_DEFAULT = "https://generativelanguage.googleapis.com/v1beta/openai/"

# Admin panelda tanlanadigan Gemini modellari.
GEMINI_MODEL_OPTIONS = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]

# AI Voice suhbatida kechikishni kamaytirish uchun eng tez model
# (admin global tanlovidan qat'i nazar shu ishlatiladi).
GEMINI_FAST_MODEL = "gemini-2.5-flash-lite"

# bot_settings jadvalidagi kalit.
ACTIVE_GEMINI_MODEL_KEY = "active_gemini_model"

_MODEL_CACHE_TTL_SECONDS = 60.0
_model_cache = {"value": None, "ts": 0.0}


def _default_gemini_model() -> str:
    model = (settings.GEMINI_MODEL or "").strip()
    return model if model in GEMINI_MODEL_OPTIONS else "gemini-2.5-flash"


def set_active_gemini_model_cache(value: str) -> None:
    """Admin modelni saqlaganda keshni darhol yangilash uchun."""
    _model_cache["value"] = value
    _model_cache["ts"] = time.monotonic()


async def get_active_gemini_model() -> str:
    """Admin tanlagan faol Gemini modeli (qisqa keshli).

    Har AI chaqiruvda bazaga bormaslik uchun qiymat modul ichida ~60s keshlanadi.
    Baza o'qishi uchun qisqa mustaqil sessiya ochiladi; xato bo'lsa standartga qaytadi.
    """
    now = time.monotonic()
    cached = _model_cache.get("value")
    if cached and (now - _model_cache.get("ts", 0.0)) < _MODEL_CACHE_TTL_SECONDS:
        return cached

    value = _default_gemini_model()
    try:
        from app.db.session import async_session_maker
        from app.repositories.bot_setting_repo import BotSettingRepository

        async with async_session_maker() as session:
            stored = await BotSettingRepository(session).get(ACTIVE_GEMINI_MODEL_KEY)
        if stored and stored.strip() in GEMINI_MODEL_OPTIONS:
            value = stored.strip()
    except Exception:
        logger.exception("Faol Gemini modelini o'qishda xato; standart model ishlatiladi")

    _model_cache["value"] = value
    _model_cache["ts"] = now
    return value


def _usage_int(usage, *names: str) -> int:
    if not usage:
        return 0
    for name in names:
        value = getattr(usage, name, None)
        if value is None and isinstance(usage, dict):
            value = usage.get(name)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0
    return 0


class AIProviderChain:
    """Gemini (asosiy) -> OpenAI (zaxira) tartibida AI chaqiruvlarini bajaradi."""

    def __init__(self):
        self._gemini_compat: Optional[AsyncOpenAI] = None
        self._openai: Optional[AsyncOpenAI] = None
        self._gemini_native = None

        if settings.GEMINI_API_KEY:
            self._gemini_compat = AsyncOpenAI(
                api_key=settings.GEMINI_API_KEY,
                base_url=(settings.GEMINI_BASE_URL or GEMINI_OPENAI_COMPAT_DEFAULT),
                timeout=settings.AI_PRIMARY_TIMEOUT_SECONDS,
            )
        if settings.OPENAI_API_KEY:
            self._openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    @property
    def available(self) -> bool:
        return bool(self._gemini_compat or self._openai)

    def _chat_providers(self):
        """(kind, client) juftliklari: Gemini avval, OpenAI keyin."""
        providers = []
        if self._gemini_compat is not None:
            providers.append(("gemini", self._gemini_compat))
        if self._openai is not None:
            providers.append(("openai", self._openai))
        return providers

    @staticmethod
    def _build_chat_request(
        *,
        kind: str,
        model: str,
        messages,
        max_completion_tokens,
        temperature,
        frequency_penalty,
        presence_penalty,
        response_format,
    ) -> dict:
        request = {"model": model, "messages": messages}
        if response_format is not None:
            request["response_format"] = response_format

        if kind == "gemini":
            # Gemini OpenAI-mos endpointi `max_tokens` ishlatadi (`max_completion_tokens` emas).
            if max_completion_tokens is not None:
                request["max_tokens"] = max_completion_tokens
            if temperature is not None:
                request["temperature"] = temperature
            # frequency_penalty / presence_penalty himoya uchun uzatilmaydi
            # (compat endpoint ularni qo'llamasa so'rov yiqilib, keraksiz fallbackka sabab bo'lardi).
        else:  # openai — mavjud xatti-harakat aynan saqlanadi
            if max_completion_tokens is not None:
                request["max_completion_tokens"] = max_completion_tokens
            if temperature is not None:
                request["temperature"] = temperature
            if frequency_penalty is not None:
                request["frequency_penalty"] = frequency_penalty
            if presence_penalty is not None:
                request["presence_penalty"] = presence_penalty
        return request

    async def chat_completion(
        self,
        *,
        openai_model: str,
        messages,
        max_completion_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        response_format=None,
        gemini_model: Optional[str] = None,
    ):
        """Chat javobini oladi. Qaytaradi: (response, model_used).

        `openai_model` — OpenAI ishlatilsa qaysi model (asl xatti-harakat).
        `gemini_model` — berilsa, admin global tanlovi o'rniga shu Gemini modeli
        ishlatiladi (masalan AI Voice tezligi uchun flash-lite).
        """
        providers = self._chat_providers()
        if not providers:
            raise RuntimeError("AI provayder sozlanmagan (GEMINI_API_KEY yoki OPENAI_API_KEY yo'q)")

        resolved_gemini = None
        if self._gemini_compat is not None:
            resolved_gemini = gemini_model or await get_active_gemini_model()

        last_error = None
        for index, (kind, client) in enumerate(providers):
            is_last = index == len(providers) - 1
            model_used = resolved_gemini if kind == "gemini" else openai_model
            try:
                request = self._build_chat_request(
                    kind=kind,
                    model=model_used,
                    messages=messages,
                    max_completion_tokens=max_completion_tokens,
                    temperature=temperature,
                    frequency_penalty=frequency_penalty,
                    presence_penalty=presence_penalty,
                    response_format=response_format,
                )
                response = await client.chat.completions.create(**request)
                return response, model_used
            except Exception as error:  # noqa: BLE001 — har qanday xatoda zaxiraga o'tamiz
                last_error = error
                if is_last:
                    raise
                logger.warning(
                    "AI provayder '%s' (model=%s) xato berdi, zaxiraga o'tilyapti: %s",
                    kind,
                    model_used,
                    error,
                )
        raise last_error  # pragma: no cover — providers bo'sh bo'lmagani uchun yetmaydi

    # ------------------------------------------------------------------ STT

    def _native_gemini_client(self):
        if self._gemini_native is None:
            from google import genai  # lazy import: paket bo'lmasa shu yerda xato

            self._gemini_native = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._gemini_native

    async def _gemini_transcribe(self, *, audio_bytes: bytes, mime_type: str, prompt: str, model: str):
        from google.genai import types

        client = self._native_gemini_client()
        response = await client.aio.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                prompt,
            ],
            config=types.GenerateContentConfig(temperature=0),
        )
        text = (getattr(response, "text", "") or "").strip()
        usage = getattr(response, "usage_metadata", None)
        usage_dict = {
            "prompt_tokens": _usage_int(usage, "prompt_token_count"),
            "completion_tokens": _usage_int(usage, "candidates_token_count"),
            "total_tokens": _usage_int(usage, "total_token_count"),
        }
        return text, usage_dict, model

    async def _openai_transcribe(self, *, audio_bytes: bytes, filename: str, mime_type: str, prompt: str):
        model = "gpt-4o-mini-transcribe"
        response = await self._openai.audio.transcriptions.create(
            model=model,
            chunking_strategy="auto",
            file=(filename, audio_bytes, mime_type),
            prompt=prompt,
            temperature=0,
        )
        if isinstance(response, str):
            return response.strip(), {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, model
        text = (getattr(response, "text", "") or "").strip()
        usage = getattr(response, "usage", None)
        usage_dict = {
            "prompt_tokens": _usage_int(usage, "prompt_tokens", "input_tokens"),
            "completion_tokens": _usage_int(usage, "completion_tokens", "output_tokens"),
            "total_tokens": _usage_int(usage, "total_tokens"),
        }
        return text, usage_dict, model

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        filename: str,
        mime_type: str,
        prompt: str,
        gemini_model: Optional[str] = None,
    ):
        """Ovozni matnga o'giradi. Qaytaradi: (text, usage_dict, model_used).

        Gemini asosiy (native SDK), OpenAI zaxira. Gemini paketi/format qo'llab-quvvatlanmasa
        yoki xato bersa OpenAI transkripsiyasiga o'tiladi.
        """
        gemini_error = None
        if settings.GEMINI_API_KEY:
            resolved = gemini_model or await get_active_gemini_model()
            try:
                return await self._gemini_transcribe(
                    audio_bytes=audio_bytes, mime_type=mime_type, prompt=prompt, model=resolved
                )
            except Exception as error:  # noqa: BLE001
                gemini_error = error
                logger.warning("Gemini STT xato berdi, OpenAI zaxiraga o'tilyapti: %s", error)

        if self._openai is not None:
            return await self._openai_transcribe(
                audio_bytes=audio_bytes, filename=filename, mime_type=mime_type, prompt=prompt
            )

        if gemini_error is not None:
            raise gemini_error
        raise RuntimeError("STT uchun AI provayder sozlanmagan")

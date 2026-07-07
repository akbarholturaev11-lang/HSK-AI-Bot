import json
from dataclasses import dataclass
from typing import Iterable, Optional

from openai import AsyncOpenAI

from app.config import settings


SUPPORTED_BROADCAST_LANGUAGES = ("tj", "uz", "ru")
_PAYLOAD_MARKER = "_localized_broadcast_v1"


@dataclass(frozen=True)
class LocalizedBroadcastText:
    texts: dict[str, str]
    translated: bool = False


def normalize_broadcast_languages(languages: Optional[Iterable[str]]) -> list[str]:
    selected = {item for item in (languages or []) if item in SUPPORTED_BROADCAST_LANGUAGES}
    return [item for item in SUPPORTED_BROADCAST_LANGUAGES if item in selected]


def broadcast_languages_or_all(languages: Optional[Iterable[str]]) -> list[str]:
    selected = normalize_broadcast_languages(languages)
    return selected or list(SUPPORTED_BROADCAST_LANGUAGES)


def encode_localized_broadcast_text(texts: dict[str, str]) -> str:
    clean = {
        lang: str(texts.get(lang) or "")
        for lang in SUPPORTED_BROADCAST_LANGUAGES
        if str(texts.get(lang) or "")
    }
    return json.dumps({_PAYLOAD_MARKER: True, "texts": clean}, ensure_ascii=False)


def decode_localized_broadcast_text(value: Optional[str]) -> Optional[dict[str, str]]:
    if not value:
        return None
    try:
        payload = json.loads(value)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get(_PAYLOAD_MARKER) is not True:
        return None
    texts = payload.get("texts")
    if not isinstance(texts, dict):
        return None
    clean = {
        lang: str(texts.get(lang) or "")
        for lang in SUPPORTED_BROADCAST_LANGUAGES
        if str(texts.get(lang) or "")
    }
    return clean or None


def localized_broadcast_text_for_language(value: Optional[str], language: Optional[str]) -> str:
    texts = decode_localized_broadcast_text(value)
    if not texts:
        return value or ""
    lang = language if language in SUPPORTED_BROADCAST_LANGUAGES else "tj"
    return texts.get(lang) or texts.get("tj") or next(iter(texts.values()), "")


def localized_broadcast_preview(value: Optional[str], *, language: str = "tj", limit: int = 180) -> str:
    text = localized_broadcast_text_for_language(value, language)
    return text[:limit] + ("..." if len(text) > limit else "")


class BroadcastTranslationService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    def _fallback(self, text: str, target_languages: Iterable[str], max_length: int) -> LocalizedBroadcastText:
        source = text[:max_length]
        return LocalizedBroadcastText(
            texts={lang: source for lang in broadcast_languages_or_all(target_languages)},
            translated=False,
        )

    async def translate_from_tajik(
        self,
        text: str,
        target_languages: Optional[Iterable[str]],
        *,
        max_length: int = 4096,
    ) -> LocalizedBroadcastText:
        targets = broadcast_languages_or_all(target_languages)
        source = (text or "")[:max_length]
        if not source:
            return LocalizedBroadcastText(texts={}, translated=False)

        texts = {lang: source for lang in targets}
        translation_targets = [lang for lang in targets if lang in {"uz", "ru"}]
        if not settings.OPENAI_API_KEY or not translation_targets:
            return LocalizedBroadcastText(texts=texts, translated=False)

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You translate Telegram admin broadcast copy from Tajik Cyrillic. "
                            "Return only valid JSON with exactly the requested language keys. "
                            "Language keys: uz = Uzbek Latin, ru = Russian. "
                            "Preserve emojis, line breaks, URLs, promo codes, numbers, prices, "
                            "hashtags, and product names. Do not add explanations, labels, "
                            "markdown wrappers, or quotation marks around the whole message. "
                            f"Each translated value must be at most {max_length} characters."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "source_language": "tj",
                                "target_languages": translation_targets,
                                "text": source,
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                temperature=0,
            )
            raw = response.choices[0].message.content or ""
            start = raw.find("{")
            end = raw.rfind("}")
            payload = json.loads(raw[start : end + 1] if start >= 0 and end >= 0 else raw)
        except Exception:
            return self._fallback(source, targets, max_length)

        translated = False
        for lang in translation_targets:
            value = str(payload.get(lang) or "").strip()
            if value:
                texts[lang] = value[:max_length]
                translated = True

        return LocalizedBroadcastText(texts=texts, translated=translated)

    async def translate_generic(
        self,
        text: str,
        source_language: str,
        *,
        max_length: int = 1024,
    ) -> LocalizedBroadcastText:
        """Matnni ixtiyoriy manba tildan (uz/ru/tj) qolgan ikki tilga o'giradi.

        `translate_from_tajik` faqat tojikchadan tarjima qiladi; bu metod esa
        admin qaysi tilda yozgan bo'lsa, o'shani manba sifatida oladi (promo
        bo'limlar uchun). Xatolik/kalit yo'q bo'lsa — barcha tillarga manba
        matn nusxalanadi (fallback)."""
        _NAMES = {"uz": "Uzbek (Latin script)", "ru": "Russian", "tj": "Tajik (Cyrillic script)"}
        src = source_language if source_language in SUPPORTED_BROADCAST_LANGUAGES else "uz"
        source = (text or "")[:max_length]
        if not source:
            return LocalizedBroadcastText(texts={}, translated=False)

        targets = list(SUPPORTED_BROADCAST_LANGUAGES)
        texts = {lang: source for lang in targets}
        translation_targets = [lang for lang in targets if lang != src]
        if not settings.OPENAI_API_KEY or not translation_targets:
            return LocalizedBroadcastText(texts=texts, translated=False)

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You translate short Telegram mini app promo copy. "
                            f"The source text is written in {_NAMES.get(src, src)}. "
                            "Return only valid JSON with exactly the requested language keys. "
                            "Language keys: uz = Uzbek Latin, ru = Russian, tj = Tajik Cyrillic. "
                            "Preserve emojis, line breaks, URLs, @usernames, promo codes, numbers, "
                            "prices, hashtags, and product/brand names. Do not add explanations, "
                            "labels, markdown wrappers, or quotation marks around the whole message. "
                            f"Each translated value must be at most {max_length} characters."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "source_language": src,
                                "target_languages": translation_targets,
                                "text": source,
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                temperature=0,
            )
            raw = response.choices[0].message.content or ""
            start = raw.find("{")
            end = raw.rfind("}")
            payload = json.loads(raw[start : end + 1] if start >= 0 and end >= 0 else raw)
        except Exception:
            return LocalizedBroadcastText(texts=texts, translated=False)

        translated = False
        for lang in translation_targets:
            value = str(payload.get(lang) or "").strip()
            if value:
                texts[lang] = value[:max_length]
                translated = True

        return LocalizedBroadcastText(texts=texts, translated=translated)

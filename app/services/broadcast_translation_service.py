import json
from dataclasses import dataclass
from typing import Iterable, Optional

from app.config import settings
from app.services.ai_service import AIService


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
        self.ai_service = AIService()

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
        if not settings.ai_enabled or not translation_targets:
            return LocalizedBroadcastText(texts=texts, translated=False)

        try:
            result = await self.ai_service.complete_messages_with_usage(
                openai_model="gpt-4o-mini",
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
            raw = result.content or ""
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

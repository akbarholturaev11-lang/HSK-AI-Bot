"""Localized course-ad headlines and buttons.

An "all" creative uses Tajik Cyrillic as its source. One AI request
generates the Uzbek (Latin) and Russian alternatives when uploaded.
Runtime clients never call AI; the persisted text is selected by the
learner's UI/account language.
"""

import json

from app.config import settings
from app.services.ai_service import AIService


LANGUAGES = ("tj", "uz", "ru")


class CourseAdTranslationError(Exception):
    """The ad must not be marked multilingual without actual translations."""


def localize_ad_copy(
    stored: str | None, *, title: str, button_text: str | None, language: str | None,
) -> tuple[str, str | None]:
    """Resolve text for the learner; old ads safely use their original copy."""
    original = (title or "").strip()
    fallback_button = (button_text or "").strip() or None
    chosen = (language or "tj").lower().split("-", 1)[0]
    if chosen not in LANGUAGES:
        chosen = "tj"
    try:
        values = json.loads(stored) if stored else {}
        copy = values.get(chosen) if isinstance(values, dict) else None
        if not isinstance(copy, dict):
            return original, fallback_button
        localized_title = copy.get("title")
        localized_button = copy.get("button_text")
        if not isinstance(localized_title, str) or not localized_title.strip():
            return original, fallback_button
        if fallback_button is not None and (
            not isinstance(localized_button, str) or not localized_button.strip()
        ):
            return original, fallback_button
        return localized_title.strip()[:120], (
            localized_button.strip()[:64] if fallback_button is not None else None
        )
    except (TypeError, ValueError, AttributeError):
        return original, fallback_button


class CourseAdTranslationService:
    def __init__(self, ai_service: AIService | None = None):
        self.ai_service = ai_service or AIService()

    async def translate_from_tajik(
        self, *, title: str, button_text: str | None,
    ) -> str:
        title = (title or "").strip()
        button = (button_text or "").strip()
        if not title or len(title) > 120 or len(button) > 64:
            raise CourseAdTranslationError("invalid_ad_copy")
        if not settings.ai_enabled:
            raise CourseAdTranslationError("ad_translation_unavailable")

        try:
            result = await self.ai_service.complete_messages_with_usage(
                openai_model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Translate a short advertisement from Tajik Cyrillic to "
                            "Uzbek LATIN script and Russian. Return ONLY a JSON object "
                            "with exactly two keys: uz and ru. Each value is an object "
                            'with keys "title" and "button_text". '
                            "Preserve brand names, numbers, emojis, URLs and the "
                            "intended call to action. Do not invent promises. "
                            "Write natural marketing copy, not word-for-word calques. "
                            "title must be non-empty and at most 120 characters; "
                            "button_text must be at most 64 characters. "
                            "If the source button_text is empty, return empty strings "
                            "for button_text in both languages. No markdown fences."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {"source_language": "tj", "title": title, "button_text": button},
                            ensure_ascii=False,
                        ),
                    },
                ],
                temperature=0,
            )
            raw = str(result.content or "")
            start, end = raw.find("{"), raw.rfind("}")
            if start == -1 or end < start:
                raise ValueError("missing JSON")
            parsed = json.loads(raw[start : end + 1])
            if not isinstance(parsed, dict):
                raise ValueError("invalid JSON root")
            localized = {"tj": {"title": title, "button_text": button}}
            for target in ("uz", "ru"):
                item = parsed.get(target)
                if not isinstance(item, dict):
                    raise ValueError("missing language")
                tr_title, tr_button = item.get("title"), item.get("button_text")
                if (not isinstance(tr_title, str) or not tr_title.strip()
                    or len(tr_title.strip()) > 120
                    or not isinstance(tr_button, str)
                    or len(tr_button.strip()) > 64
                    or (button and not tr_button.strip())
                    or (not button and tr_button.strip())):
                    raise ValueError("invalid localized text")
                localized[target] = {
                    "title": tr_title.strip(), "button_text": tr_button.strip(),
                }
            return json.dumps(localized, ensure_ascii=False, separators=(",", ":"))
        except Exception as exc:
            raise CourseAdTranslationError("ad_translation_unavailable") from exc

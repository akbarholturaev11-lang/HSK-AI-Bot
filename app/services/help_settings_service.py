from __future__ import annotations
from app.bot.generated.bot_i18n import bot_locale_map

from dataclasses import dataclass
from html import escape

from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.support_contact_service import get_admin_contact_html


HELP_LANGS = ("tj", "ru", "uz")


@dataclass(frozen=True)
class HelpVideoField:
    key: str
    label: str
    icon: str

    def setting_key(self, lang: str) -> str:
        return f"help_video_{self.key}_{lang}"


HELP_VIDEO_FIELDS = (
    HelpVideoField("course_hsk", "HSK kurs video linki", "📚"),
    HelpVideoField("qa_mode", "Oddiy rejim video link", "💬"),
    HelpVideoField("voice_translator", "Ovoz / tarjimon video linki", "🎙"),
    HelpVideoField("subscription", "Obuna imkoniyatlari video link", "💳"),
)
HELP_VIDEO_FIELD_BY_KEY = {field.key: field for field in HELP_VIDEO_FIELDS}

HELP_TEXT = bot_locale_map('inline.services.help_settings_service.module.copy1')


def normalize_help_lang(lang: str | None) -> str:
    return lang if lang in HELP_LANGS else "ru"


def normalize_help_url(value: str | None) -> str:
    url = (value or "").strip()
    lowered = url.lower()
    if not url:
        return ""
    if lowered.startswith(("https://", "http://", "tg://")):
        return url
    if lowered.startswith("t.me/"):
        return f"https://{url}"
    return ""


async def get_help_video_url(session, field: HelpVideoField, lang: str) -> str:
    stored = await BotSettingRepository(session).get(field.setting_key(normalize_help_lang(lang)))
    return normalize_help_url(stored)


async def build_help_text(session, lang: str) -> str:
    lang = normalize_help_lang(lang)
    text = HELP_TEXT[lang]
    lines = [text["title"], ""]

    for field in HELP_VIDEO_FIELDS:
        url = await get_help_video_url(session, field, lang)
        if not url:
            continue
        href = escape(url, quote=True)
        click = escape(text["click"])
        label = escape(text[field.key])
        lines.append(f"{field.icon} {label} — <a href=\"{href}\">{click}</a>")
        lines.append("")

    admin_link = await get_admin_contact_html(session, text["admin"])
    lines.append(text["admin_line"].format(admin=admin_link))
    return "\n".join(lines).strip()

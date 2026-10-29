"""Dormant Smart content adapter; transport is injected only after authorization."""
from dataclasses import dataclass
from pathlib import Path
from string import Formatter
from urllib.parse import parse_qs, urlsplit

from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy import select

from app.bot.utils.course_miniapp import course_study_miniapp_url
from app.db.models.user import User
from app.services.notification_i18n import notification_message
from app.services.notification_template_service import (
    CAPTION_MAX, TEXT_MAX, KEY_SMART_STUDY, NotificationTemplateService,
)
from app.services.smart_reminder_preferences import SmartReminderError


MEDIA_ROOT = Path("app/static/uploads/notifications")


@dataclass(frozen=True)
class TelegramContent:
    language: str
    text: str
    lesson_order: int
    markup: InlineKeyboardMarkup
    media_type: str = "none"
    media_path: str | None = None


async def render_telegram_content(session, actor, job):
    """Called after current target/access policy under the canonical User lock."""
    user = (await session.execute(select(User.language).where(
        User.id == actor.user_id, User.telegram_id == actor.telegram_id))).one_or_none()
    if user is None:
        raise SmartReminderError("telegram_content_owner_changed", 409)
    lang = user.language if user.language in ("uz", "ru", "tj") else "ru"
    lesson = job["lesson_order"]
    if type(lesson) is not int or lesson < 1:
        raise SmartReminderError("telegram_content_target_invalid", 409)
    resolved = await NotificationTemplateService(session).resolve(KEY_SMART_STUDY, lang)
    if resolved is None:
        raise SmartReminderError("telegram_template_disabled", 409)
    try:
        for _, field, spec, conversion in Formatter().parse(resolved["text"]):
            if field is not None and (field != "lesson" or spec or conversion):
                raise ValueError("Unsafe template field")
        text = resolved["text"].format(lesson=lesson)
    except (KeyError, IndexError, ValueError):
        raise SmartReminderError("telegram_template_invalid", 409) from None
    media_type = resolved.get("media_type") or "none"
    media_path = resolved.get("media_path")
    if media_type not in {"none", "photo", "video"}:
        raise SmartReminderError("telegram_template_invalid", 409)
    if media_type != "none" and media_path:
        # A DB template never authorizes arbitrary filesystem reads. Missing
        # owned media uses text in the transport, with the same text cap here.
        candidate = Path(media_path)
        if candidate.name != media_path or media_path in {".", ".."}:
            raise SmartReminderError("telegram_template_invalid", 409)
    maximum = CAPTION_MAX if media_type != "none" and media_path else TEXT_MAX
    if not text.strip() or len(text.encode("utf-16-le")) // 2 > maximum:
        raise SmartReminderError("telegram_template_invalid", 409)
    url = course_study_miniapp_url(lang=lang, level=job["course_key"], lesson=lesson,
                                 tab="course", source=KEY_SMART_STUDY, autostart=False)
    parsed = urlsplit(url)
    query = parse_qs(parsed.query)
    expected = {"lang": lang, "level": job["course_key"], "lesson": str(lesson),
                "tab": "course", "source": KEY_SMART_STUDY}
    if (parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or
            parsed.fragment or set(query) != {*expected, "v"} or
            any(query.get(k) != [v] for k, v in expected.items())):
        raise SmartReminderError("telegram_content_target_invalid", 409)
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text=notification_message("reminder.continueLessonNumber", lang, lesson=lesson),
        web_app=WebAppInfo(url=url))]])
    return TelegramContent(lang, text, lesson, markup, media_type, media_path)


async def send_telegram_content(bot, envelope):
    """No SQL/eligibility/retries here. The caller must hold committed authority.

    This helper is not registered with a runtime producer or scheduler. Tests
    inject a fake Bot through the same authorized dispatch callback.
    """
    content = envelope.content
    if content is None:
        raise ValueError("Authorized rendered content required")
    if content.media_type in {"photo", "video"} and content.media_path:
        root = MEDIA_ROOT.resolve()
        path = (root / content.media_path).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Unowned template media")
        if path.is_file():
            sender = bot.send_photo if content.media_type == "photo" else bot.send_video
            return await sender(envelope.telegram_id, FSInputFile(path), caption=content.text,
                                reply_markup=content.markup, parse_mode="HTML")
    return await bot.send_message(chat_id=envelope.telegram_id, text=content.text,
                                 reply_markup=content.markup, parse_mode="HTML")

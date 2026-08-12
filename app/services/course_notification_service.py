from __future__ import annotations

import html
import re
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.course_user_notification import CourseUserNotification
from app.db.models.user import User
from app.services.notification_template_service import (
    KEY_DAILY_GOAL,
    KEY_D1_RECOVERY,
    KEY_LESSON_UNFINISHED,
    KEY_OVERTAKEN,
    KEY_STREAK,
)


MAX_FEED_ITEMS = 8
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"[ \t\r\f\v]+")


TITLE_BY_KEY: dict[str, dict[str, str]] = {
    "subscription_expiring": {
        "uz": "Obuna tugayapti",
        "ru": "Подписка скоро закончится",
        "tj": "Обуна ба охир мерасад",
    },
    "subscription_offer": {
        "uz": "Obunani davom ettiring",
        "ru": "Продлите подписку",
        "tj": "Обунаатонро идома диҳед",
    },
    "lesson_time": {
        "uz": "Dars vaqti keldi",
        "ru": "Время урока",
        "tj": "Вақти дарс расид",
    },
    KEY_OVERTAKEN: {
        "uz": "Reytingda o'zib ketishdi",
        "ru": "В рейтинге вас обошли",
        "tj": "Дар рейтинг аз шумо гузаштанд",
    },
    KEY_LESSON_UNFINISHED: {
        "uz": "Dars tugallanmagan",
        "ru": "Урок не завершён",
        "tj": "Дарс анҷом нашудааст",
    },
    KEY_D1_RECOVERY: {
        "uz": "Darsga qaytish",
        "ru": "Вернуться к уроку",
        "tj": "Ба дарс баргаштан",
    },
    KEY_DAILY_GOAL: {
        "uz": "Bugungi maqsad",
        "ru": "Цель на сегодня",
        "tj": "Ҳадафи имрӯз",
    },
    KEY_STREAK: {
        "uz": "Seriya xavf ostida",
        "ru": "Серия под угрозой",
        "tj": "Силсила дар хатар аст",
    },
}

ACTION_BY_KEY = {
    "subscription_expiring": "subscription",
    "subscription_offer": "subscription",
    KEY_OVERTAKEN: "rating",
    KEY_LESSON_UNFINISHED: "course",
    KEY_D1_RECOVERY: "course",
    KEY_DAILY_GOAL: "course",
    KEY_STREAK: "course",
    "lesson_time": "course",
}
GLYPH_BY_KEY = {
    "subscription_expiring": "会",
    "subscription_offer": "会",
    KEY_OVERTAKEN: "榜",
    KEY_LESSON_UNFINISHED: "课",
    KEY_D1_RECOVERY: "课",
    KEY_DAILY_GOAL: "今",
    KEY_STREAK: "火",
    "lesson_time": "时",
}
ALLOWED_ACTIONS = {"course", "rating", "subscription", "profile"}


def notification_title(key: str, lang: str) -> str:
    texts = TITLE_BY_KEY.get(key, {})
    return texts.get(lang) or texts.get("ru") or key.replace("_", " ").title()


def clean_notification_text(value: str, limit: int = 420) -> str:
    text = html.unescape(_TAG_RE.sub("", str(value or "")))
    lines = [_SPACE_RE.sub(" ", line).strip() for line in text.splitlines()]
    normalized = "\n".join(line for line in lines if line)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def notification_copy(key: str, lang: str, text: str) -> tuple[str, str]:
    title = notification_title(key, lang)
    body = clean_notification_text(text)
    if body.startswith(title):
        body = body[len(title):].lstrip(" \n:-—")
    if not body:
        body = title
    return title, body


def _localized_copy(
    row: CourseUserNotification,
    lang: str | None,
) -> tuple[str, str]:
    """Render a stored notification in the language the reader is using now.

    The row keeps the text as it was sent, which is the wrong language as soon
    as the learner switches the app. When `params` carries the template and its
    arguments the whole item is rebuilt; otherwise only the title can be
    recovered from `TITLE_BY_KEY`, and the body stays as written. Rows created
    before `params` existed therefore keep working, just partly translated.
    """
    reader = lang if lang in ("uz", "ru", "tj") else None
    if not reader or reader == row.language:
        return row.title, row.body

    params = row.params if isinstance(row.params, dict) else {}
    if params.get("template_service"):
        # Needs a database session, so `list_for_user` resolves these before
        # calling here and passes the result in as `_rendered`.
        rendered = params.get("_rendered")
        if rendered:
            return notification_copy(row.key, reader, str(rendered))
        return notification_title(row.key, reader), row.body
    template = str(params.get("template") or "").strip()
    if template:
        arguments = {k: v for k, v in params.items() if k != "template"}
        try:
            from app.bot.utils.i18n import t

            return notification_copy(row.key, reader, t(template, reader, **arguments))
        except Exception:  # noqa: BLE001 - a broken template must not empty the feed
            pass
    return notification_title(row.key, reader), row.body


def local_day_dedupe(key: str, local_day: date | None) -> str:
    day = local_day or datetime.now(timezone.utc).date()
    return f"{key}:{day.isoformat()}"


class CourseNotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def payload(row: CourseUserNotification, lang: str | None = None) -> dict[str, Any]:
        created_at = row.created_at
        if created_at and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        title, body = _localized_copy(row, lang)
        return {
            "id": int(row.id),
            "key": row.key,
            "glyph": GLYPH_BY_KEY.get(row.key, "铃"),
            "title": title,
            "body": body,
            "action": row.action if row.action in ALLOWED_ACTIONS else "course",
            "level": row.level,
            "lesson_order": row.lesson_order,
            "created_at": created_at.isoformat() if created_at else "",
        }

    async def list_for_user(self, user: User, *, limit: int = MAX_FEED_ITEMS) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(CourseUserNotification)
            .where(CourseUserNotification.telegram_id == int(user.telegram_id))
            .order_by(CourseUserNotification.created_at.desc(), CourseUserNotification.id.desc())
            .limit(max(1, min(20, int(limit or MAX_FEED_ITEMS))))
        )
        reader_language = getattr(user, "language", None)
        rows = list(result.scalars().all())
        await self._resolve_admin_templates(rows, reader_language)
        return [self.payload(row, reader_language) for row in rows]

    async def _resolve_admin_templates(
        self,
        rows: list[CourseUserNotification],
        lang: str | None,
    ) -> None:
        """Re-render motivation reminders, whose templates live in the database.

        These cannot be rebuilt inside `payload` because looking them up needs a
        session. Rendering happens here, once per row, and the result rides
        along in `params["_rendered"]` — an in-memory field only, never written
        back, so the stored row keeps the text that was actually sent.
        """
        if lang not in ("uz", "ru", "tj"):
            return
        pending = [
            row
            for row in rows
            if isinstance(row.params, dict)
            and row.params.get("template_service")
            and row.language != lang
        ]
        if not pending:
            return
        from app.services.notification_template_service import NotificationTemplateService

        templates = NotificationTemplateService(self.session)
        cache: dict[str, str] = {}
        for row in pending:
            key = str(row.params.get("template_service") or "")
            try:
                if key not in cache:
                    resolved = await templates.resolve(key, lang)
                    cache[key] = str((resolved or {}).get("text") or "")
                text = cache[key]
                if not text:
                    continue
                fields = {
                    name: value
                    for name, value in row.params.items()
                    if name != "template_service" and not name.startswith("_")
                }
                # A missing placeholder must leave the row alone, not blank it.
                row.params = {**row.params, "_rendered": text.format(**fields)}
            except Exception:  # noqa: BLE001 - the stored copy is the fallback
                continue

    async def record(
        self,
        user: User,
        *,
        key: str,
        lang: str,
        title: str,
        body: str,
        action: str | None = None,
        source: str = "telegram_reminder",
        level: str | None = None,
        lesson_order: int | None = None,
        dedupe_key: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> bool:
        key = str(key or "").strip()[:64]
        if not key:
            return False
        lang = lang if lang in ("uz", "ru", "tj") else "ru"
        action = action if action in ALLOWED_ACTIONS else ACTION_BY_KEY.get(key, "course")
        normalized_title = clean_notification_text(title, 160) or notification_title(key, lang)
        normalized_body = clean_notification_text(body, 420) or normalized_title
        try:
            normalized_lesson = int(lesson_order) if lesson_order else None
        except (TypeError, ValueError):
            normalized_lesson = None

        row = CourseUserNotification(
            user_id=getattr(user, "id", None),
            telegram_id=int(user.telegram_id),
            key=key,
            source=str(source or "telegram_reminder")[:40],
            language=lang,
            title=normalized_title[:160],
            body=normalized_body,
            params=params if isinstance(params, dict) and params.get("template") else None,
            action=action,
            level=str(level or "").strip().lower()[:32] or None,
            lesson_order=normalized_lesson,
            dedupe_key=str(dedupe_key or "")[:160] or None,
            created_at=datetime.now(timezone.utc),
        )
        try:
            async with self.session.begin_nested():
                self.session.add(row)
                await self.session.flush()
            return True
        except IntegrityError:
            return False

    async def record_from_text(
        self,
        user: User,
        *,
        key: str,
        lang: str,
        text: str,
        action: str | None = None,
        source: str = "telegram_reminder",
        level: str | None = None,
        lesson_order: int | None = None,
        dedupe_key: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> bool:
        title, body = notification_copy(key, lang, text)
        return await self.record(
            user,
            key=key,
            lang=lang,
            title=title,
            body=body,
            action=action,
            source=source,
            level=level,
            lesson_order=lesson_order,
            dedupe_key=dedupe_key,
            params=params,
        )

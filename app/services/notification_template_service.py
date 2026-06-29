from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notification_template import NotificationTemplate


# Reminder keys handled by MotivationReminderService.
KEY_OVERTAKEN = "rating_overtaken"
KEY_PASSED = "rating_passed"
KEY_DAILY_GOAL = "daily_goal"
KEY_STREAK = "streak_risk"

MOTIVATION_KEYS = (KEY_OVERTAKEN, KEY_PASSED, KEY_DAILY_GOAL, KEY_STREAK)

# Human-facing metadata for the admin Mini App editor: title, short note and the
# placeholders available for each reminder. Placeholders are filled per-user when
# the reminder is actually sent.
TEMPLATE_META: dict[str, dict] = {
    KEY_OVERTAKEN: {
        "title": "🥇 Reytingda o'tib ketishdi",
        "note": "Mini App reytingida foydalanuvchini kimdir ortda qoldirsa yuboriladi.",
        "placeholders": ["{name}", "{league}", "{rank}", "{xp_gap}"],
    },
    KEY_PASSED: {
        "title": "🚀 Reytingda oldinga o'tdi",
        "note": "Mini App reytingida foydalanuvchi kimnidir ortda qoldirsa yuboriladi.",
        "placeholders": ["{name}", "{league}", "{rank}", "{xp_gap}"],
    },
    KEY_DAILY_GOAL: {
        "title": "⏳ Kunlik maqsad bajarilmadi",
        "note": "Kun oxirida foydalanuvchi bugun hali shug'ullanmagan bo'lsa yuboriladi.",
        "placeholders": ["{minutes}"],
    },
    KEY_STREAK: {
        "title": "🔥 Streak uzilmoqda",
        "note": "Kun oxirida bugun kirmagan, lekin streaki bor foydalanuvchiga yuboriladi.",
        "placeholders": ["{streak}"],
    },
}

# Built-in default texts (the approved samples). Used when the admin has not set
# a custom text for a language, so a misconfiguration can never silence a reminder.
DEFAULT_TEXTS: dict[str, dict[str, str]] = {
    KEY_OVERTAKEN: {
        "uz": (
            "🥇 <b>{name} sizni ortda qoldirdi!</b>\n"
            "Siz <b>{league} ligasida {rank}-o'ringa</b> tushdingiz.\n"
            "Farq atigi <b>{xp_gap} XP</b>. Bitta dars bilan o'rningizni qaytaring 💪"
        ),
        "ru": (
            "🥇 <b>{name} обошёл вас!</b>\n"
            "Вы опустились на <b>{rank}-е место в лиге {league}</b>.\n"
            "Разница всего <b>{xp_gap} XP</b>. Один урок — и вы снова впереди 💪"
        ),
        "tj": (
            "🥇 <b>{name} аз шумо пеш гузашт!</b>\n"
            "Шумо ба <b>ҷои {rank} дар лигаи {league}</b> фаромадед.\n"
            "Фарқ ҳамагӣ <b>{xp_gap} XP</b>. Бо як дарс ҷои худро баргардонед 💪"
        ),
    },
    KEY_PASSED: {
        "uz": (
            "🚀 <b>Siz {name}ni ortda qoldirdingiz!</b>\n"
            "Endi <b>{league} ligasida {rank}-o'rindasiz</b>.\n"
            "Farq <b>{xp_gap} XP</b>. Tempni tushirmang 💪"
        ),
        "ru": (
            "🚀 <b>Вы обошли {name}!</b>\n"
            "Теперь вы на <b>{rank}-м месте в лиге {league}</b>.\n"
            "Разница <b>{xp_gap} XP</b>. Держите темп 💪"
        ),
        "tj": (
            "🚀 <b>Шумо аз {name} пеш гузаштед!</b>\n"
            "Ҳоло шумо дар <b>ҷои {rank} дар лигаи {league}</b> ҳастед.\n"
            "Фарқ <b>{xp_gap} XP</b>. Ҳамин суръатро нигоҳ доред 💪"
        ),
    },
    KEY_DAILY_GOAL: {
        "uz": (
            "⏳ <b>Bugungi maqsad hali bajarilmadi</b>\n"
            "Kun tugashiga oz qoldi, siz bugun hali shug'ullanmadingiz.\n"
            "Atigi <b>{minutes} daqiqa</b> — kunlik maqsadingizni yoping 🎯"
        ),
        "ru": (
            "⏳ <b>Сегодняшняя цель ещё не выполнена</b>\n"
            "День заканчивается, а вы ещё не занимались.\n"
            "Всего <b>{minutes} минут</b> — закройте дневную цель 🎯"
        ),
        "tj": (
            "⏳ <b>Ҳадафи имрӯза ҳанӯз иҷро нашуд</b>\n"
            "Рӯз ба охир мерасад, шумо имрӯз ҳанӯз машғул нашудед.\n"
            "Ҳамагӣ <b>{minutes} дақиқа</b> — ҳадафи рӯзонаатонро пӯшонед 🎯"
        ),
    },
    KEY_STREAK: {
        "uz": (
            "🔥 <b>{streak} kunlik streak xavf ostida!</b>\n"
            "Bugun kirmasangiz, streak uziladi va kalendarda kun yo'qoladi.\n"
            "Bitta kichik dars — streak saqlanadi 🔥"
        ),
        "ru": (
            "🔥 <b>Серия из {streak} дней под угрозой!</b>\n"
            "Если не зайдёте сегодня, серия прервётся и день пропадёт в календаре.\n"
            "Один маленький урок — и серия сохранится 🔥"
        ),
        "tj": (
            "🔥 <b>Силсилаи {streak}-рӯза дар хатар аст!</b>\n"
            "Агар имрӯз надароед, силсила канда мешавад ва рӯз дар тақвим гум мешавад.\n"
            "Як дарси хурд — силсила нигоҳ дошта мешавад 🔥"
        ),
    },
}

# Telegram limits: caption (with media) max 1024, plain message max 4096.
CAPTION_MAX = 1024
TEXT_MAX = 4096


def default_text(key: str, lang: str) -> str:
    texts = DEFAULT_TEXTS.get(key, {})
    return texts.get(lang) or texts.get("ru") or ""


class NotificationTemplateService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_row(self, key: str) -> NotificationTemplate | None:
        return (
            await self.session.execute(
                select(NotificationTemplate).where(NotificationTemplate.key == key)
            )
        ).scalar_one_or_none()

    async def _get_or_create(self, key: str) -> NotificationTemplate:
        row = await self._get_row(key)
        if row is None:
            row = NotificationTemplate(key=key, enabled=True, media_type="none")
            self.session.add(row)
            await self.session.flush()
        return row

    async def list_for_admin(self) -> list[dict]:
        """Return the motivation templates merged with defaults for the admin editor."""
        rows = {
            row.key: row
            for row in (
                await self.session.execute(select(NotificationTemplate))
            ).scalars()
        }
        result = []
        for key in MOTIVATION_KEYS:
            row = rows.get(key)
            meta = TEMPLATE_META[key]
            result.append(
                {
                    "key": key,
                    "title": meta["title"],
                    "note": meta["note"],
                    "placeholders": meta["placeholders"],
                    "enabled": bool(row.enabled) if row else True,
                    "text_uz": (row.text_uz if row else "") or "",
                    "text_ru": (row.text_ru if row else "") or "",
                    "text_tj": (row.text_tj if row else "") or "",
                    "default_uz": default_text(key, "uz"),
                    "default_ru": default_text(key, "ru"),
                    "default_tj": default_text(key, "tj"),
                    "media_type": (row.media_type if row else "none") or "none",
                    "media_url": (
                        f"/uploads/notifications/{row.media_path}"
                        if row and row.media_path
                        else None
                    ),
                    "caption_max": CAPTION_MAX,
                    "text_max": TEXT_MAX,
                }
            )
        return result

    async def resolve(self, key: str, lang: str) -> dict | None:
        """Resolve text + media for sending. Returns None when disabled."""
        row = await self._get_row(key)
        if row is not None and not row.enabled:
            return None
        lang = lang if lang in ("uz", "ru", "tj") else "ru"
        custom = ""
        media_type = "none"
        media_path = None
        if row is not None:
            custom = getattr(row, f"text_{lang}", "") or ""
            media_type = row.media_type or "none"
            media_path = row.media_path
        text = custom.strip() or default_text(key, lang)
        return {"text": text, "media_type": media_type, "media_path": media_path}

    async def update_text(
        self,
        key: str,
        *,
        text_uz: str,
        text_ru: str,
        text_tj: str,
        enabled: bool,
        updated_by: int | None,
    ) -> NotificationTemplate:
        row = await self._get_or_create(key)
        row.text_uz = (text_uz or "").strip() or None
        row.text_ru = (text_ru or "").strip() or None
        row.text_tj = (text_tj or "").strip() or None
        row.enabled = bool(enabled)
        row.updated_by = updated_by
        row.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return row

    async def set_media(self, key: str, *, media_type: str, media_path: str | None) -> NotificationTemplate:
        row = await self._get_or_create(key)
        row.media_type = media_type if media_type in ("photo", "video") else "none"
        row.media_path = media_path
        row.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return row

    async def clear_media(self, key: str) -> NotificationTemplate:
        return await self.set_media(key, media_type="none", media_path=None)

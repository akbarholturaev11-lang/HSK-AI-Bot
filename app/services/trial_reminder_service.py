"""7 kunlik Pro trial tugashi haqida ogohlantirish.

Jami IKKI xabar: 2 kun qolganda va oxirgi kuni. Ko'proq emas — loyihada
allaqachon oltita bildirishnoma servisi bor va odam kuniga to'rt xabar olsa
botni bloklaydi (bu KPI ro'yxatidagi ko'rsatkich).

Takrorlanmasligi `course_user_notifications` dagi `dedupe_key` bilan
ta'minlanadi: `users` ga yangi ustun qo'shilmaydi, chunki trial ustunlariga
har qanday qo'shimcha yozuv referral byudjeti bilan bog'liq xavfni oshiradi.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from sqlalchemy import select

from app.bot.utils.i18n import t
from app.db.models.user import User
from app.services.bot_block_status_service import BotBlockStatusService
from app.services.course_notification_service import CourseNotificationService


logger = logging.getLogger(__name__)


#: Qaysi kunlarda xabar yuboriladi (trial tugashiga necha kun qolganda).
REMINDER_DAYS = (2, 0)

MAX_BATCH = 200


def _as_utc(value: datetime | None) -> datetime | None:
    if not value:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class TrialReminderService:
    def __init__(self, session):
        self.session = session

    async def send_due_reminders(self, bot: Bot, *, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        horizon = now + timedelta(days=max(REMINDER_DAYS) + 1)

        result = await self.session.execute(
            select(User)
            .where(
                User.pro_trial_ends_at.is_not(None),
                User.pro_trial_ends_at > now,
                User.pro_trial_ends_at <= horizon,
                User.pro_trial_revoked_at.is_(None),
            )
            .limit(MAX_BATCH)
        )
        users = list(result.scalars().all())

        notifications = CourseNotificationService(self.session)
        blocks = BotBlockStatusService(self.session)
        sent = 0

        for user in users:
            ends_at = _as_utc(user.pro_trial_ends_at)
            if not ends_at:
                continue
            # Qolgan kun yuqoriga yaxlitlanadi: 1.5 kun qolgan bo'lsa "2 kun".
            days_left = max(0, (ends_at - now).days)
            if days_left not in REMINDER_DAYS:
                continue

            lang = user.language or "ru"
            key = "trial_expiring_soon" if days_left else "trial_expired_notice"
            text = (
                t(key, lang, days=days_left) if days_left else t(key, lang)
            )
            dedupe = f"trial_reminder:{ends_at.date().isoformat()}:{days_left}"

            # AVVAL yoziladi, KEYIN yuboriladi. Tartib muhim: yozuv unique
            # kalit bilan dedupe qiladi, ya'ni takror chaqiruvda `False`
            # qaytadi. Teskari tartibda xabar yuborilib, keyin dedupe
            # aniqlanardi — foydalanuvchi ikkinchi xabarni allaqachon olgan
            # bo'lardi.
            if not await notifications.record_from_text(
                user,
                key="trial_expiring",
                lang=lang,
                text=text,
                action="subscription",
                source="trial_reminder",
                dedupe_key=dedupe,
                params={"days_left": days_left},
            ):
                continue

            try:
                await bot.send_message(
                    chat_id=user.telegram_id, text=text, parse_mode="HTML"
                )
            except Exception as exc:  # noqa: BLE001 — blok holati alohida yuriladi
                await blocks.handle_send_exception(
                    user.telegram_id, exc, reason="trial_reminder"
                )
                continue
            sent += 1

        await self.session.commit()
        return sent

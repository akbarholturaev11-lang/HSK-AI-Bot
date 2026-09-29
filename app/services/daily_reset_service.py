from datetime import datetime, timezone

from aiogram import Bot
from sqlalchemy import select

from app.db.models.user import User
from app.bot.utils.i18n import t
from app.services.notification_delivery_service import (
    DELIVERED,
    NotificationDeliveryService,
    TelegramNotice,
)


class DailyResetService:
    def __init__(self, session):
        self.session = session

    async def send_daily_reset_notifications(self, bot: Bot) -> int:
        today = datetime.now(timezone.utc).date()
        now = datetime.now(timezone.utc)
        delivery = NotificationDeliveryService(self.session)

        result = await self.session.execute(
            select(User).where(User.status == "trial")
        )
        users = list(result.scalars().all())

        sent_count = 0

        for user in users:
            needs_reset = (
                user.last_limit_reset_at is None
                or user.last_limit_reset_at.date() < today
            )
            if not needs_reset:
                continue

            should_notify = user.questions_used > 0

            user.questions_used = 0
            user.last_limit_reset_at = now

            if should_notify and await delivery.reachable(user):
                lang = user.language if user.language else "ru"
                # Android app first; Telegram when the phone cannot show it.
                outcome = await delivery.deliver(
                    bot,
                    user,
                    key="daily_limit_renewed",
                    lang=lang,
                    telegram=TelegramNotice(text=t("daily_limit_renewed", lang)),
                    reason="daily_reset",
                    action="course",
                )
                if outcome in DELIVERED:
                    sent_count += 1

        await self.session.commit()
        return sent_count

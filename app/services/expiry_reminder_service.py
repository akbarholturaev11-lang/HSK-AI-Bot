from datetime import datetime, timezone, timedelta

from aiogram import Bot

from app.repositories.user_repo import UserRepository
from app.bot.utils.i18n import t
from app.services.course_notification_service import CourseNotificationService
from app.services.notification_delivery_service import (
    DELIVERED,
    NotificationDeliveryService,
    TelegramNotice,
)


class ExpiryReminderService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)

    async def send_expiry_reminders(self, bot: Bot) -> int:
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date()
        users = await self.user_repo.list_active_users_expiring_on(tomorrow)
        delivery = NotificationDeliveryService(self.session)

        sent_count = 0

        for user in users:
            if user.expiry_reminder_sent_at is not None:
                continue
            if not await delivery.reachable(user):
                continue

            lang = user.language if user.language else "ru"
            text = t("subscription_expires_tomorrow", lang)

            # Android app first; Telegram when the phone cannot show it.
            outcome = await delivery.deliver(
                bot,
                user,
                key="subscription_expiring",
                lang=lang,
                telegram=TelegramNotice(text=text),
                reason="expiry_reminder",
            )
            if outcome not in DELIVERED:
                continue
            await CourseNotificationService(self.session).record_from_text(
                user,
                key="subscription_expiring",
                lang=lang,
                text=text,
                action="subscription",
                source="expiry_reminder",
                dedupe_key=f"subscription_expiring:{tomorrow.isoformat()}",
                params={"template": "subscription_expires_tomorrow"},
            )
            user.expiry_reminder_sent_at = datetime.now(timezone.utc)
            sent_count += 1

        await self.session.commit()
        return sent_count

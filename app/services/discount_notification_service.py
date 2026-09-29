import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from aiogram import Bot

from app.config import settings
from app.bot.keyboards.subscription import admin_discount_entry_keyboard
from app.db.models.discount_campaign import DiscountCampaign
from app.repositories.discount_campaign_repo import DiscountCampaignRepository
from app.repositories.user_repo import UserRepository
from app.services.course_notification_service import CourseNotificationService
from app.services.notification_delivery_service import (
    DELIVERED,
    NotificationDeliveryService,
    TelegramNotice,
)
from app.services.user_access_state_service import UserAccessStateService


@dataclass
class DiscountNotificationResult:
    campaign_id: int
    total: int
    sent: int
    failed: int


class DiscountNotificationService:
    def __init__(self, session):
        self.session = session
        self.repo = DiscountCampaignRepository(session)
        self.user_repo = UserRepository(session)

    async def send_due_notifications(self, bot: Bot) -> list[DiscountNotificationResult]:
        campaigns = await self.repo.list_due_notifications(datetime.now(timezone.utc))
        results = []
        for campaign in campaigns:
            results.append(await self.send_campaign_notification(bot, campaign))
        if campaigns:
            await self.session.commit()
        return results

    async def send_campaign_notification(
        self,
        bot: Bot,
        campaign: DiscountCampaign,
    ) -> DiscountNotificationResult:
        users = await self._target_users(campaign)
        admin_ids = set(settings.admin_id_list)
        delivery = NotificationDeliveryService(self.session)
        # A learner who blocked the bot can still get it in the Android app.
        target_users = [
            user for user in users
            if user.telegram_id not in admin_ids
            and await delivery.reachable(user)
        ]

        sent_count = 0
        failed_count = 0

        for user in target_users:
            lang = user.language or "uz"
            text = await self._notification_text(campaign, lang, user.payment_method)
            media_type = (
                campaign.notify_media_type
                if campaign.notify_media_type in ("photo", "video") and campaign.notify_media_file_id
                else None
            )
            # Android app first; Telegram (with the campaign media) as fallback.
            # The phone copy leaves out the "opens in the Mini App" line.
            outcome = await delivery.deliver(
                bot,
                user,
                key="discount_offer",
                lang=lang,
                telegram=TelegramNotice(
                    text=text,
                    reply_markup=admin_discount_entry_keyboard(lang, campaign_id=campaign.id),
                    parse_mode="HTML",
                    media_type=media_type,
                    media_file_id=campaign.notify_media_file_id if media_type else None,
                    disable_web_page_preview=None if media_type else True,
                ),
                reason="discount_notification",
                body=await self._notification_text(
                    campaign, lang, user.payment_method, for_phone=True
                ),
            )
            if outcome in DELIVERED:
                await CourseNotificationService(self.session).record_from_text(
                    user,
                    key="subscription_offer",
                    lang=lang,
                    text=text,
                    action="subscription",
                    source="discount_notification",
                    dedupe_key=f"discount_campaign:{campaign.id}",
                )
                sent_count += 1
            else:
                failed_count += 1
            await asyncio.sleep(0.05)

        await self.repo.mark_notification_sent(
            campaign,
            sent_count=sent_count,
            failed_count=failed_count,
        )
        return DiscountNotificationResult(
            campaign_id=campaign.id,
            total=len(target_users),
            sent=sent_count,
            failed=failed_count,
        )

    async def _target_users(self, campaign: DiscountCampaign):
        if campaign.target_telegram_id:
            user = await self.user_repo.get_by_telegram_id(campaign.target_telegram_id)
            return [user] if user else []
        users = await self.user_repo.get_filtered_users(
            language=campaign.audience_language,
            status=campaign.audience_status,
            level=campaign.audience_level,
        )
        # Faol pullik obunachi chegirma e'lonini olmaydi — u "obunam tugadimi?"
        # degan noto'g'ri xabar beradi. `status="active"` filtri ularni ham
        # qamrab olgani uchun bu yerda alohida chiqarib tashlanadi.
        return [user for user in users if not UserAccessStateService.is_paid(user)]

    async def _notification_text(
        self,
        campaign: DiscountCampaign,
        lang: str,
        user_payment_method: Optional[str],
        *,
        for_phone: bool = False,
    ) -> str:
        """Telegram text; ``for_phone`` is the Android body under the headline.

        The phone shows the headline as the notification title and opens the
        app's own subscription screen, so it drops both the headline and the
        "opens in the Mini App" line.
        """
        title = (
            getattr(campaign, f"title_{lang}", None)
            or campaign.title
            or {
                "tj": "Тахфифи махсус",
                "ru": "Специальная скидка",
                "uz": "Maxsus chegirma",
            }.get(lang, "Maxsus chegirma")
        )
        reason = (
            getattr(campaign, f"reason_{lang}", None)
            or campaign.reason
            or ""
        )
        labels = {
            "tj": {
                "title": "🎁 <b>Тахфифи махсус омода аст</b>",
                "discount": "Тахфиф",
                "open": "Тариф ва пардохт дар Mini App кушода мешавад.",
            },
            "ru": {
                "title": "🎁 <b>Специальная скидка готова</b>",
                "discount": "Скидка",
                "open": "Тариф и оплата откроются в Mini App.",
            },
            "uz": {
                "title": "🎁 <b>Maxsus chegirma tayyor</b>",
                "discount": "Chegirma",
                "open": "Tarif va to'lov Mini App ichida ochiladi.",
            },
        }.get(lang, {})
        lines = [
            f"<b>{title}</b>",
            f"{labels.get('discount', 'Chegirma')}: <b>{campaign.percent}%</b>",
        ]
        if reason:
            lines.extend(["", reason])
        if for_phone:
            return "\n".join(lines)
        lines = [labels.get("title", "🎁 <b>Maxsus chegirma tayyor</b>"), "", *lines]
        lines.extend(["", labels.get("open", "Tarif va to'lov Mini App ichida ochiladi.")])
        return "\n".join(lines)

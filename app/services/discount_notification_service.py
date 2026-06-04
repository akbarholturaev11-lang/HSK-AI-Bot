import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from aiogram import Bot

from app.config import settings
from app.bot.keyboards.subscription import admin_discount_entry_keyboard
from app.bot.utils.discount_formatter import build_admin_discount_block, build_discount_plan_line
from app.db.models.discount_campaign import DiscountCampaign
from app.repositories.discount_campaign_repo import DiscountCampaignRepository
from app.repositories.user_repo import UserRepository
from app.services.subscription_currency_service import SubscriptionCurrencyService
from app.services.subscription_price_service import SubscriptionPriceService


PLANS = ("10_days", "1_month")


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
        target_users = [user for user in users if user.telegram_id not in admin_ids]

        sent_count = 0
        failed_count = 0

        for user in target_users:
            lang = user.language or "uz"
            text = await self._notification_text(campaign, lang, user.payment_method)
            try:
                if campaign.notify_media_type == "photo" and campaign.notify_media_file_id:
                    await bot.send_photo(
                        chat_id=user.telegram_id,
                        photo=campaign.notify_media_file_id,
                        caption=text,
                        reply_markup=admin_discount_entry_keyboard(lang, campaign_id=campaign.id),
                        parse_mode="HTML",
                    )
                elif campaign.notify_media_type == "video" and campaign.notify_media_file_id:
                    await bot.send_video(
                        chat_id=user.telegram_id,
                        video=campaign.notify_media_file_id,
                        caption=text,
                        reply_markup=admin_discount_entry_keyboard(lang, campaign_id=campaign.id),
                        parse_mode="HTML",
                    )
                else:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=text,
                        reply_markup=admin_discount_entry_keyboard(lang, campaign_id=campaign.id),
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
                sent_count += 1
            except Exception:
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
        return await self.user_repo.get_filtered_users(
            language=campaign.audience_language,
            status=campaign.audience_status,
            level=campaign.audience_level,
        )

    async def _plan_price(self, plan_type: str, payment_method: Optional[str]) -> tuple[int, str]:
        price = await SubscriptionPriceService(self.session).get_price(payment_method, plan_type)
        if price:
            return price.amount, price.currency
        if payment_method in ("alipay", "wechat"):
            return (66 if plan_type == "1_month" else 29), "¥"
        return (89 if plan_type == "1_month" else 29), "TJS"

    async def _notification_text(
        self,
        campaign: DiscountCampaign,
        lang: str,
        user_payment_method: Optional[str],
    ) -> str:
        payment_method = campaign.payment_method or user_payment_method
        plans = [campaign.plan_type] if campaign.plan_type else list(PLANS)
        lines = []
        for plan in plans:
            base, currency = await self._plan_price(plan, payment_method)
            final = int(round(base * (100 - campaign.percent) / 100))
            local_equivalents = ""
            if (currency or "").strip().lower() in {"usd", "$"}:
                local_equivalents = await SubscriptionCurrencyService(
                    self.session
                ).format_local_equivalents(final)
            lines.append(
                build_discount_plan_line(
                    lang=lang,
                    plan=plan,
                    base=base,
                    currency=currency,
                    percent=campaign.percent,
                    local_equivalents=local_equivalents,
                )
            )

        return build_admin_discount_block(
            lang=lang,
            discount=campaign,
            percent=campaign.percent,
            starts_at=campaign.starts_at,
            ends_at=campaign.ends_at,
            quota_total=campaign.quota_total,
            repeat_interval_days=campaign.repeat_interval_days,
            plan_lines="\n".join(lines),
            now=datetime.now(timezone.utc),
        )

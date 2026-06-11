from aiogram import Bot

from app.bot.handlers.subscription import build_subscription_discount_progress_text, _referral_link
from app.bot.keyboards.subscription import (
    subscription_discount_progress_keyboard,
    subscription_discount_ready_keyboard,
)
from app.services.discount_service import DiscountService


class SubscriptionProgressService:
    def __init__(self, session):
        self.session = session

    async def update_discount_progress_message(
        self,
        bot: Bot,
        referrer_user,
    ) -> None:
        if not referrer_user:
            return

        if not referrer_user.discount_progress_chat_id or not referrer_user.discount_progress_message_id:
            return

        lang = referrer_user.language if referrer_user.language else "ru"
        count, discount_eligible = await DiscountService(self.session).sync_referral_discount_progress(referrer_user)

        try:
            referral_link = await _referral_link(bot, referrer_user.referral_code)
            text = await build_subscription_discount_progress_text(
                self.session,
                lang,
                referral_link,
                count,
                discount_eligible=discount_eligible,
                discount_used=referrer_user.discount_used,
                payment_method=referrer_user.payment_method,
            )
            keyboard = (
                subscription_discount_ready_keyboard(lang)
                if discount_eligible and not referrer_user.discount_used
                else subscription_discount_progress_keyboard(lang)
            )
            await bot.edit_message_text(
                chat_id=referrer_user.discount_progress_chat_id,
                message_id=referrer_user.discount_progress_message_id,
                text=text,
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
        except Exception:
            pass

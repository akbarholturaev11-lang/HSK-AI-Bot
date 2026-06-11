from aiogram import Bot

from app.bot.keyboards.subscription import subscription_miniapp_keyboard
from app.bot.utils.i18n import t
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
            text = t("subscription_miniapp_entry_text", lang)
            keyboard = subscription_miniapp_keyboard(
                lang,
                source="referral_progress_update",
                mode="referral_discount",
                text=t(
                    "subscription_referral_discount_button"
                    if discount_eligible and not referrer_user.discount_used
                    else "subscription_miniapp_open_button",
                    lang,
                ),
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

from aiogram import Bot

from app.bot.utils.i18n import t


class ReferralNotifyService:
    async def notify_bonus_received(
        self,
        bot: Bot,
        referrer_user,
        count: int,
        required: int,
    ) -> None:
        if not referrer_user:
            return

        lang = referrer_user.language if referrer_user.language else "ru"
        text = t("referral_bonus_received", lang, count=count, required=required)

        try:
            await bot.send_message(
                chat_id=referrer_user.telegram_id,
                text=text,
            )
        except Exception:
            pass

    async def notify_trial_access_unlocked(
        self,
        bot: Bot,
        referrer_user,
        days: int,
    ) -> None:
        if not referrer_user:
            return

        lang = referrer_user.language if referrer_user.language else "ru"
        text = t("referral_trial_access_unlocked", lang, days=days)

        try:
            await bot.send_message(
                chat_id=referrer_user.telegram_id,
                text=text,
                parse_mode="HTML",
            )
        except Exception:
            pass

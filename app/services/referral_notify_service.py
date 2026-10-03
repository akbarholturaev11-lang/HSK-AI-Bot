from aiogram import Bot

from app.bot.keyboards.course_miniapp import course_study_miniapp_keyboard
from app.bot.utils.i18n import t
from app.services.bot_block_status_service import BotBlockStatusService


COURSE_START_BUTTON = {
    "uz": "▶️ Darsni boshlash",
    "tj": "▶️ Оғози дарс",
    "ru": "▶️ Начать урок",
}


class ReferralNotifyService:
    def __init__(self, session=None):
        self.session = session

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

        if self.session is not None and BotBlockStatusService.is_bot_blocked(referrer_user):
            return
        blocks = BotBlockStatusService(self.session) if self.session is not None else None
        try:
            await bot.send_message(
                chat_id=referrer_user.telegram_id,
                text=text,
            )
            if blocks is not None:
                await blocks.handle_send_success(referrer_user, reason="referral_bonus")
        except Exception as exc:
            if blocks is not None:
                await blocks.handle_send_exception(
                    referrer_user.telegram_id,
                    exc,
                    reason="referral_bonus",
                )

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

        if self.session is not None and BotBlockStatusService.is_bot_blocked(referrer_user):
            return
        blocks = BotBlockStatusService(self.session) if self.session is not None else None
        try:
            await bot.send_message(
                chat_id=referrer_user.telegram_id,
                text=text,
                parse_mode="HTML",
                reply_markup=course_study_miniapp_keyboard(
                    lang,
                    tab="course",
                    text=COURSE_START_BUTTON.get(lang, COURSE_START_BUTTON["ru"]),
                ),
            )
            if blocks is not None:
                await blocks.handle_send_success(referrer_user, reason="referral_trial_unlocked")
        except Exception as exc:
            if blocks is not None:
                await blocks.handle_send_exception(
                    referrer_user.telegram_id,
                    exc,
                    reason="referral_trial_unlocked",
                )

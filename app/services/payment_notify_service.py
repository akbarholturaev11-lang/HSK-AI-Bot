from aiogram import Bot

from app.bot.keyboards.subscription import subscription_miniapp_keyboard
from app.bot.utils.i18n import t
from app.services.bot_block_status_service import BotBlockStatusService

REASON_TRANSLATIONS = {
    "wrong_amount":       {"uz": "Summa noto'g'ri",    "tj": "Маблағ нодуруст",     "ru": "Неверная сумма"},
    "unclear_screenshot": {"uz": "Screenshot noaniq",  "tj": "Скриншот норавшан",   "ru": "Скриншот нечёткий"},
    "fake_suspected":     {"uz": "Shubhali to'lov",    "tj": "Пардохти шубҳанок",   "ru": "Подозрительный платёж"},
    "old_payment":        {"uz": "Eski to'lov",        "tj": "Пардохти кӯҳна",      "ru": "Старый платёж"},
    "other":              {"uz": "Boshqa sabab",        "tj": "Сабаби дигар",        "ru": "Другая причина"},
}


def _translate_reason(reason_code: str, lang: str) -> str:
    return REASON_TRANSLATIONS.get(reason_code, {}).get(lang, reason_code)


class PaymentNotifyService:
    def __init__(self, session=None):
        self.session = session

    async def _success(self, user, source: str) -> None:
        if self.session is not None:
            await BotBlockStatusService(self.session).handle_send_success(user, reason=source)

    async def _failure(self, user, exc: Exception, source: str) -> None:
        if self.session is not None:
            await BotBlockStatusService(self.session).handle_send_exception(user.telegram_id, exc, reason=source)

    async def notify_payment_approved(self, bot: Bot, user) -> None:
        if not user:
            return
        lang = user.language if user.language else "ru"
        if self.session is not None and BotBlockStatusService.is_bot_blocked(user):
            return
        try:
            await bot.send_message(chat_id=user.telegram_id, text=t("user_payment_approved", lang))
            await self._success(user, "payment_approved")
        except Exception as exc:
            await self._failure(user, exc, "payment_approved")

    async def notify_payment_rejected(self, bot: Bot, user, reason: str = None, plan_type: str = None, payment=None) -> None:
        if not user:
            return
        lang = user.language if user.language else "ru"
        text = t("user_payment_rejected", lang)
        if reason:
            translated = _translate_reason(reason, lang)
            prefix = {"uz": "Sabab", "tj": "Сабаб", "ru": "Причина"}.get(lang, "Sabab")
            text += f"\n\n{prefix}: {translated}"
        mode = "subscription"
        campaign_id = None
        if payment and getattr(payment, "discount_source", None) == "admin_campaign":
            mode = "admin_discount"
            campaign_id = getattr(payment, "discount_campaign_id", None)
        elif payment and getattr(payment, "discount_source", None) == "feedback_price_offer":
            mode = "feedback_discount"
        elif payment and getattr(payment, "discount_source", None) == "referral":
            mode = "referral_discount"

        if self.session is not None and BotBlockStatusService.is_bot_blocked(user):
            return
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                reply_markup=subscription_miniapp_keyboard(
                    lang,
                    source="payment_rejected",
                    mode=mode,
                    campaign_id=campaign_id,
                    plan=plan_type,
                    method=getattr(payment, "payment_method", None) if payment else None,
                ),
            )
            await self._success(user, "payment_rejected")
        except Exception as exc:
            await self._failure(user, exc, "payment_rejected")

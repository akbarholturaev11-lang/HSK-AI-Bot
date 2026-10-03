from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.bot.keyboards.course_miniapp import course_study_miniapp_keyboard
from app.bot.keyboards.subscription import subscription_miniapp_keyboard
from app.bot.utils.course_miniapp import course_study_miniapp_url
from app.bot.utils.i18n import t
from app.services.bot_block_status_service import BotBlockStatusService
from app.services.android_payment_push_service import AndroidPaymentPushService

HSK30_UNLOCK_APPROVED_TEXT = {
    "uz": "To'lov qabul qilindi ✅\n\nHSK 3.0 ga to'liq kirish siz uchun ochildi. Quyidagi tugmadan boshlang 👇🏽",
    "tj": "Пардохт қабул шуд ✅\n\nДастрасии пурра ба HSK 3.0 барои шумо кушода шуд. Аз тугмаи поён оғоз кунед 👇🏽",
    "ru": "Платёж принят ✅\n\nПолный доступ к HSK 3.0 открыт для вас. Начните с кнопки ниже 👇🏽",
}

HSK30_UNLOCK_COURSE_BUTTON = {
    "uz": "▶️ HSK 3.0 ni boshlash",
    "tj": "▶️ HSK 3.0-ро оғоз кардан",
    "ru": "▶️ Начать HSK 3.0",
}

COURSE_START_BUTTON = {
    "uz": "▶️ Darsni boshlash",
    "tj": "▶️ Оғози дарс",
    "ru": "▶️ Начать урок",
}

HSK30_UNLOCK_REJECTED_TEXT = {
    "uz": "❌ HSK 3.0 ni ochish to'lovi tasdiqlanmadi.",
    "tj": "❌ Пардохти кушодани HSK 3.0 тасдиқ нашуд.",
    "ru": "❌ Платёж за открытие HSK 3.0 не подтверждён.",
}

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

    async def _android_push(self, payment, status: str) -> None:
        if self.session is None or payment is None:
            return
        try:
            await AndroidPaymentPushService(self.session).notify(
                telegram_id=payment.user_telegram_id,
                payment_id=payment.id,
                status=status,
            )
        except Exception:
            # Bot delivery and the committed subscription decision must keep
            # working even if the optional Android transport is unavailable.
            import logging

            logging.getLogger(__name__).exception("Android payment notification failed")

    async def notify_payment_approved(self, bot: Bot, user, payment=None) -> None:
        try:
            if not user:
                return
            lang = user.language if user.language else "ru"
            if self.session is not None and BotBlockStatusService.is_bot_blocked(user):
                return
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=t("user_payment_approved", lang),
                    reply_markup=course_study_miniapp_keyboard(
                        lang,
                        tab="course",
                        text=COURSE_START_BUTTON.get(lang, COURSE_START_BUTTON["ru"]),
                    ),
                )
                await self._success(user, "payment_approved")
            except Exception as exc:
                await self._failure(user, exc, "payment_approved")
        finally:
            await self._android_push(payment, "approved")

    async def notify_hsk30_unlock_approved(self, bot: Bot, user, payment=None) -> None:
        try:
            if not user:
                return
            lang = user.language if user.language in {"uz", "tj", "ru"} else "ru"
            if self.session is not None and BotBlockStatusService.is_bot_blocked(user):
                return
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=HSK30_UNLOCK_APPROVED_TEXT[lang],
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text=HSK30_UNLOCK_COURSE_BUTTON[lang],
                                    web_app=WebAppInfo(
                                        url=course_study_miniapp_url(
                                            lang=lang,
                                            level="nhsk1",
                                            tab="course",
                                            source="hsk30_unlock_approved",
                                        )
                                    ),
                                )
                            ]
                        ]
                    ),
                )
                await self._success(user, "hsk30_unlock_approved")
            except Exception as exc:
                await self._failure(user, exc, "hsk30_unlock_approved")
        finally:
            await self._android_push(payment, "approved")

    async def notify_hsk30_unlock_rejected(
        self,
        bot: Bot,
        user,
        *,
        reason: str | None = None,
        payment=None,
    ) -> None:
        try:
            if not user:
                return
            lang = user.language if user.language in {"uz", "tj", "ru"} else "ru"
            message = HSK30_UNLOCK_REJECTED_TEXT[lang]
            if reason:
                translated = _translate_reason(reason, lang)
                prefix = {"uz": "Sabab", "tj": "Сабаб", "ru": "Причина"}.get(lang, "Sabab")
                message += f"\n\n{prefix}: {translated}"
            if self.session is not None and BotBlockStatusService.is_bot_blocked(user):
                return
            try:
                await bot.send_message(chat_id=user.telegram_id, text=message)
                await self._success(user, "hsk30_unlock_rejected")
            except Exception as exc:
                await self._failure(user, exc, "hsk30_unlock_rejected")
        finally:
            await self._android_push(payment, "rejected")

    async def notify_payment_rejected(self, bot: Bot, user, reason: str = None, plan_type: str = None, payment=None) -> None:
        try:
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
        finally:
            await self._android_push(payment, "rejected")

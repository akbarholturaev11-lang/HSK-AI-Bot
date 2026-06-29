from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.keyboards.feedback import feedback_price_offer_keyboard
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.subscription_churn import (
    CHURN_REASON_CODES,
    subscription_churn_reason_keyboard,
)
from app.bot.utils.i18n import t
from app.repositories.user_repo import UserRepository
from app.services.admin_notify_service import AdminNotifyService
from app.services.subscription_churn_service import SubscriptionChurnService


router = Router()


async def _edit_or_answer(callback: CallbackQuery, text: str, reply_markup=None) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
        return
    except Exception:
        pass

    await callback.message.answer(text, reply_markup=reply_markup, parse_mode="HTML")


async def _open_reason_prompt(callback: CallbackQuery, session) -> None:
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "ru"
    if not user:
        await callback.answer(t("access_start_first", lang), show_alert=True)
        return

    await SubscriptionChurnService(session).mark_responded(user)
    await session.commit()
    await callback.answer()
    await _edit_or_answer(
        callback,
        t("subscription_churn_reason_prompt", lang),
        subscription_churn_reason_keyboard(lang),
    )


@router.callback_query(F.data.in_({"sub_churn:later", "sub_churn:feedback"}))
async def subscription_churn_later_handler(callback: CallbackQuery, session):
    await _open_reason_prompt(callback, session)


@router.callback_query(F.data.startswith("sub_churn:reason:"))
async def subscription_churn_reason_handler(callback: CallbackQuery, session):
    reason = (callback.data or "").split(":")[-1]
    if reason not in CHURN_REASON_CODES:
        reason = "other"

    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "ru"
    if not user:
        await callback.answer(t("access_start_first", lang), show_alert=True)
        return

    feedback, discount_available = await SubscriptionChurnService(session).record_reason(user, reason)
    await session.commit()

    await AdminNotifyService().notify_bot_feedback(
        bot=callback.bot,
        feedback=feedback,
        user=user,
    )

    await callback.answer()
    if discount_available:
        await _edit_or_answer(
            callback,
            t("subscription_churn_discount_ready_text", lang),
            feedback_price_offer_keyboard(feedback.id, lang),
        )
        return

    await _edit_or_answer(callback, t("subscription_churn_feedback_thanks", lang))
    if reason == "trial_more":
        await callback.message.answer(
            t("subscription_churn_trial_more_text", lang),
            reply_markup=main_menu_keyboard(lang),
            parse_mode="HTML",
        )

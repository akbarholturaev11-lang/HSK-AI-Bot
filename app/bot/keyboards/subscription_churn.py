from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.subscription import subscription_miniapp_button
from app.bot.utils.i18n import t


CHURN_REASON_CODES = ("budget", "price", "ai_quality", "course_fit", "trial_more", "other")


def subscription_expired_offer_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                subscription_miniapp_button(
                    lang,
                    source="subscription_expired",
                    mode="subscription",
                    text=t("subscription_expired_continue_button", lang),
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("subscription_expired_later_button", lang),
                    callback_data="sub_churn:later",
                )
            ],
        ]
    )


def subscription_churn_followup_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                subscription_miniapp_button(
                    lang,
                    source="subscription_churn_followup",
                    mode="subscription",
                    text=t("subscription_expired_continue_button", lang),
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("subscription_churn_feedback_button", lang),
                    callback_data="sub_churn:feedback",
                )
            ],
        ]
    )


def subscription_churn_reason_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(f"subscription_churn_reason_{code}", lang),
                    callback_data=f"sub_churn:reason:{code}",
                )
            ]
            for code in CHURN_REASON_CODES
        ]
    )

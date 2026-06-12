from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.bot.keyboards.subscription import subscription_miniapp_button
from app.bot.utils.i18n import t


def referral_daily_limit_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("referral_bonus_question_button", lang),
                    callback_data="referral:invite",
                )
            ],
            [
                subscription_miniapp_button(
                    lang,
                    source="daily_limit",
                    mode="subscription",
                    text=t("menu_subscription", lang),
                )
            ],
        ]
    )


def photo_limit_subscription_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("referral_bonus_question_button", lang),
                    callback_data="referral:invite",
                )
            ],
            [
                subscription_miniapp_button(
                    lang,
                    source="photo_limit",
                    mode="subscription",
                    text=t("menu_subscription", lang),
                )
            ],
        ]
    )

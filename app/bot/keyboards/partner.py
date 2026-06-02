from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.utils.i18n import t


def partner_close_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("partner_back_button", lang), callback_data="partner:close")],
        ]
    )


def partner_apply_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("partner_apply_button", lang), callback_data="partner:apply")],
            [InlineKeyboardButton(text=t("partner_back_button", lang), callback_data="partner:close")],
        ]
    )


def partner_active_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("partner_get_link_button", lang), callback_data="partner:link")],
            [InlineKeyboardButton(text=t("partner_payout_button", lang), callback_data="partner:payout")],
            [InlineKeyboardButton(text=t("partner_back_button", lang), callback_data="partner:close")],
        ]
    )


def partner_dashboard_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("partner_back_button", lang), callback_data="partner:dashboard")],
        ]
    )


def partner_payout_methods_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("partner_payout_bank_button", lang), callback_data="partner:payout_method:bank_card")],
            [InlineKeyboardButton(text=t("partner_payout_alipay_button", lang), callback_data="partner:payout_method:alipay")],
            [InlineKeyboardButton(text=t("partner_payout_wechat_button", lang), callback_data="partner:payout_method:wechat")],
            [InlineKeyboardButton(text=t("partner_payout_other_button", lang), callback_data="partner:payout_method:other")],
            [InlineKeyboardButton(text=t("partner_back_button", lang), callback_data="partner:dashboard")],
        ]
    )

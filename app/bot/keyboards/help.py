from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.utils.i18n import t


def help_contact_keyboard(lang: str, contact_url: str) -> InlineKeyboardMarkup | None:
    if not contact_url:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("help_contact_button", lang), url=contact_url)]
        ]
    )

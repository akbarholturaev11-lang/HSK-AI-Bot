from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from app.bot.utils.i18n import t


def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("menu_profile", lang)),
                KeyboardButton(text=t("menu_subscription", lang)),
            ],
            [
                KeyboardButton(text=t("menu_course_mode", lang)),
                KeyboardButton(text=t("course_reminder_set_button", lang)),
            ],
            [
                KeyboardButton(text=t("menu_partner", lang)),
                KeyboardButton(text=t("menu_help", lang)),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="...",
    )



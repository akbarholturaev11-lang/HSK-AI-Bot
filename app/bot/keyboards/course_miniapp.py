from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.bot.utils.course_miniapp import course_miniapp_url, course_stroke_order_url
from app.bot.utils.i18n import t


def course_quiz_miniapp_keyboard(lang: str, lesson, block_no: int | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("course_miniapp_quiz_button", lang),
                    web_app=WebAppInfo(url=course_miniapp_url(lesson, "quiz", lang, block_no=block_no)),
                )
            ],
        ]
    )


def course_homework_miniapp_keyboard(lang: str, lesson) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("course_miniapp_homework_button", lang),
                    web_app=WebAppInfo(url=course_miniapp_url(lesson, "homework", lang)),
                )
            ],
        ]
    )


def course_vocab_stroke_order_keyboard(
    lang: str,
    lesson,
    *,
    block_no: int | None = None,
    vocab_page: int | None = None,
    next_callback: str = "course:go_next_step",
) -> InlineKeyboardMarkup:
    labels = {
        "uz": "✍️ Ieroglif yozilishini ko'rish",
        "ru": "✍️ Посмотреть написание иероглифов",
        "tj": "✍️ Тарзи навишти иероглифҳо",
    }
    next_labels = {
        "uz": "▶️ Davom etamiz",
        "ru": "▶️ Продолжаем",
        "tj": "▶️ Идома медиҳем",
    }
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=labels.get(lang, labels["ru"]),
                    web_app=WebAppInfo(
                        url=course_stroke_order_url(
                            lesson,
                            lang,
                            block_no=block_no,
                            vocab_page=vocab_page,
                        )
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=next_labels.get(lang, next_labels["ru"]),
                    callback_data=next_callback,
                )
            ],
        ]
    )


def course_miniapp_understood_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("course_miniapp_yes_button", lang),
                    callback_data="course:satisfied_yes",
                ),
                InlineKeyboardButton(
                    text=t("course_miniapp_no_button", lang),
                    callback_data="course:satisfied_no",
                ),
            ],
        ]
    )


def course_miniapp_continue_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("course_next_step", lang),
                    callback_data="course:repeat_step",
                )
            ],
        ]
    )


def course_homework_done_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("course_miniapp_next_lesson_button", lang),
                    callback_data="course:start_next_lesson",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("course_miniapp_repeat_lesson_button", lang),
                    callback_data="course:homework_reread",
                )
            ],
        ]
    )

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.bot.keyboards.course_miniapp import course_study_miniapp_button
from app.bot.utils.i18n import t


# Step → callback for "I understood, continue" button
_STEP_NEXT_CALLBACK = {
    "intro":    "course:go_vocab",
    "vocab":    "course:go_dialogue",
    "dialogue": "course:go_grammar",
    "grammar":  "course:go_exercise",
}

def _with_miniapp(rows: list[list[InlineKeyboardButton]], lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *rows,
            [course_study_miniapp_button(lang, text=t("course_miniapp_open", lang))],
        ]
    )


def course_understood_keyboard(lang: str, step: str) -> InlineKeyboardMarkup | None:
    callback = _STEP_NEXT_CALLBACK.get(step)
    if not callback:
        return None
    locale = lang if lang in ("uz", "ru", "tj") else "ru"
    label = t("bot.courseKeyboard.understood", locale)
    return _with_miniapp(
        [[InlineKeyboardButton(text=label, callback_data=callback)]],
        lang,
    )




def course_satisfaction_keyboard(lang: str) -> InlineKeyboardMarkup:
    return _with_miniapp(
        [
            [
                InlineKeyboardButton(
                    text=t("course_lesson_satisfied_yes", lang),
                    callback_data="course:satisfied_yes",
                ),
                InlineKeyboardButton(
                    text=t("course_lesson_satisfied_no", lang),
                    callback_data="course:satisfied_no",
                ),
            ],
        ],
        lang,
    )


def course_homework_keyboard(lang: str) -> InlineKeyboardMarkup:
    return _with_miniapp(
        [
            [
                InlineKeyboardButton(
                    text=t("course_start_homework", lang),
                    callback_data="course:show_homework",
                )
            ],
        ],
        lang,
    )


def course_next_lesson_keyboard(lang: str) -> InlineKeyboardMarkup:
    return _with_miniapp(
        [
            [
                InlineKeyboardButton(
                    text=t("course_start_next_lesson", lang),
                    callback_data="course:start_next_lesson",
                )
            ],
        ],
        lang,
    )


def course_level_upgrade_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("course_next_level_yes", lang),
                    callback_data="course:level_upgrade_yes",
                ),
                InlineKeyboardButton(
                    text=t("course_next_level_no", lang),
                    callback_data="course:level_upgrade_no",
                ),
            ],
        ]
    )

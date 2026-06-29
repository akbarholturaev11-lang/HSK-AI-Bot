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

_UNDERSTOOD_LABELS = {
    "uz": "✅ Tushundim, davom etamiz",
    "ru": "✅ Понял(а), продолжаем",
    "tj": "✅ Фаҳмидам, давом медиҳем",
}
_MINIAPP_LABELS = {
    "uz": "📚 Mini Appda ochish",
    "ru": "📚 Открыть в Mini App",
    "tj": "📚 Дар Mini App кушодан",
}


def _with_miniapp(rows: list[list[InlineKeyboardButton]], lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *rows,
            [course_study_miniapp_button(lang, text=_MINIAPP_LABELS.get(lang, _MINIAPP_LABELS["ru"]))],
        ]
    )


def course_understood_keyboard(lang: str, step: str) -> InlineKeyboardMarkup | None:
    callback = _STEP_NEXT_CALLBACK.get(step)
    if not callback:
        return None
    label = _UNDERSTOOD_LABELS.get(lang, _UNDERSTOOD_LABELS["ru"])
    return _with_miniapp(
        [[InlineKeyboardButton(text=label, callback_data=callback)]],
        lang,
    )


# Barcha content step lari uchun universal "Tushundim" tugmasi (AI javob ostida)
_TUSHUNDIM_LABELS = {
    "uz": "✅ Tushundim",
    "ru": "✅ Понял(а)",
    "tj": "✅ Фаҳмидам",
}

def course_tushundim_keyboard(lang: str) -> InlineKeyboardMarkup:
    """AI tutor javobidan keyin: 'Tushundim' → keyingi bo'limga o'tish."""
    return _with_miniapp(
        [[
            InlineKeyboardButton(
                text=_TUSHUNDIM_LABELS.get(lang, _TUSHUNDIM_LABELS["ru"]),
                callback_data="course:go_next_step",
            )
        ]],
        lang,
    )


def course_review_offer_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("course_review_yesterday", lang),
                    callback_data="course:review_last",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("course_skip_review", lang),
                    callback_data="course:continue",
                )
            ],
        ]
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

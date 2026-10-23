import json

from app.bot.utils.i18n import t
from app.bot.keyboards.course_miniapp import course_study_miniapp_button
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


HSK4_UPPER_MAX_ORDER = 10
HSK4_PART_UPPER = "upper"
HSK4_PART_LOWER = "lower"


def _with_miniapp(rows: list[list[InlineKeyboardButton]], lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *rows,
            [course_study_miniapp_button(lang, text=t("course_miniapp_open", lang))],
        ]
    )


def _parse_title(raw: str) -> str:
    """lesson.title oddiy string yoki JSON bo'lishi mumkin — xitoycha qismini qaytaradi."""
    if not raw:
        return ""
    if raw.strip().startswith("{"):
        try:
            d = json.loads(raw)
            if isinstance(d, dict):
                return d.get("zh") or d.get("uz") or raw
        except Exception:
            pass
    return raw


def normalize_hsk4_part(part: str | None) -> str | None:
    if part in {HSK4_PART_UPPER, HSK4_PART_LOWER}:
        return part
    return None


def filter_hsk4_lessons_by_part(lessons: list, part: str | None) -> list:
    normalized_part = normalize_hsk4_part(part)
    if normalized_part == HSK4_PART_UPPER:
        return [lesson for lesson in lessons if lesson.lesson_order <= HSK4_UPPER_MAX_ORDER]
    if normalized_part == HSK4_PART_LOWER:
        return [lesson for lesson in lessons if lesson.lesson_order > HSK4_UPPER_MAX_ORDER]
    return lessons


def hsk4_part_selection_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="上", callback_data=f"course:hsk4_part:{HSK4_PART_UPPER}"),
        InlineKeyboardButton(text="下", callback_data=f"course:hsk4_part:{HSK4_PART_LOWER}"),
    ]])


# ─── STEP KEYBOARDS (inline) ────────────────────────────────────────────────

def course_intro_keyboard(lang: str) -> InlineKeyboardMarkup:
    return _with_miniapp(
        [[InlineKeyboardButton(text=t("course_intro_vocab", lang), callback_data="course:go_vocab")]],
        lang,
    )




def course_dialogue_keyboard(lang: str) -> InlineKeyboardMarkup:
    audio_label = "🔉"
    return _with_miniapp(
        [
            [
                InlineKeyboardButton(text=audio_label, callback_data="course:audio_dialogue"),
                InlineKeyboardButton(text=t("course_dialogue_grammar", lang), callback_data="course:go_grammar"),
            ]
        ],
        lang,
    )


def course_grammar_keyboard(lang: str) -> InlineKeyboardMarkup:
    return _with_miniapp(
        [[InlineKeyboardButton(text=t("course_grammar_exercises", lang), callback_data="course:go_exercise")]],
        lang,
    )




def course_homework_keyboard(lang: str) -> InlineKeyboardMarkup:
    return _with_miniapp(
        [[InlineKeyboardButton(text=t("course_homework_next_lesson", lang), callback_data="course:start_next_lesson")]],
        lang,
    )


def homework_retry_keyboard(lang: str) -> InlineKeyboardMarkup:
    return _with_miniapp(
        [
            [
                InlineKeyboardButton(
                    text=t("course_reread_button", lang),
                    callback_data="course:homework_reread",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("course_start_next_lesson", lang),
                    callback_data="course:start_next_lesson",
                ),
            ],
        ],
        lang,
    )


def course_next_step_keyboard(lang: str) -> InlineKeyboardMarkup:
    """V2 darslar uchun universal 'Davom etamiz' tugmasi (audiosiz)."""
    return _with_miniapp(
        [[InlineKeyboardButton(text=t("course_continue", lang), callback_data="course:go_next_step")]],
        lang,
    )




def course_dialogue_n_keyboard(lang: str, n: int) -> InlineKeyboardMarkup:
    """V2 dialogue_N step: [🔉]  [▶️ Davom etamiz]."""
    return _with_miniapp(
        [[
            InlineKeyboardButton(text="🔉", callback_data=f"course:audio_dialogue:{n}"),
            InlineKeyboardButton(
                text=t("course_continue", lang),
                callback_data="course:go_next_step",
            ),
        ]],
        lang,
    )


def review_choice_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("course_review_yes", lang), callback_data="course:review_yes"),
        InlineKeyboardButton(text=t("course_review_no", lang),  callback_data="course:review_no"),
    ]])


def lesson_selection_keyboard(
    lessons: list,
    page: int = 0,
    lang: str = "ru",
    hsk4_part: str | None = None,
) -> InlineKeyboardMarkup:
    if not lessons:
        return InlineKeyboardMarkup(inline_keyboard=[])

    level = lessons[0].level if lessons else "hsk1"
    if level == "hsk4" and hsk4_part:
        lessons = filter_hsk4_lessons_by_part(lessons, hsk4_part)
        if not lessons:
            return InlineKeyboardMarkup(inline_keyboard=[])

    page_size = 10 if level == "hsk4" else 7

    start = page * page_size
    end = start + page_size
    page_lessons = lessons[start:end]
    total = len(lessons)

    buttons = []
    for lesson in page_lessons:
        buttons.append([
            InlineKeyboardButton(
                text=f"{lesson.lesson_order}. {_parse_title(lesson.title or '')}",
                callback_data=f"course:pick_lesson:{lesson.id}",
            )
        ])

    nav = []
    page_callback_suffix = f":{hsk4_part}" if level == "hsk4" and hsk4_part else ""
    if page > 0:
        nav.append(InlineKeyboardButton(
            text=(t("trial_lesson_previous", lang)
                  if lang in ("uz", "ru", "tj") else "⬅️"),
            callback_data=f"course:lessons_page:{page-1}{page_callback_suffix}",
        ))
    if end < total:
        nav.append(InlineKeyboardButton(
            text=(t("trial_lesson_next", lang)
                  if lang in ("uz", "ru", "tj") else "➡️"),
            callback_data=f"course:lessons_page:{page+1}{page_callback_suffix}",
        ))
    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=buttons)




def reminder_time_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="08:00", callback_data="course:reminder_time:08:00"),
                InlineKeyboardButton(text="14:00", callback_data="course:reminder_time:14:00"),
                InlineKeyboardButton(text="20:00", callback_data="course:reminder_time:20:00"),
            ],
            [
                InlineKeyboardButton(
                    text=t("course_reminder_cancel", lang),
                    callback_data="course:reminder_cancel",
                ),
            ],
        ],
    )

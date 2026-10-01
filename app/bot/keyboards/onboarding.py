import json

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.bot.utils.i18n import t


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇹🇯 Тоҷикӣ", callback_data="lang:tj"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
                InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang:uz"),
            ]
        ]
    )


def course_mode_entry_keyboard(lang: str) -> InlineKeyboardMarkup:
    labels = {
        "uz": ("🚀 Kursni boshlash", "🤖 Oddiy rejim (chatda savol-javob)"),
        "ru": ("🚀 Начать курс", "🤖 Обычный режим (вопрос-ответ в чате)"),
        "tj": ("🚀 Оғози курс", "🤖 Реҷаи оддӣ (савол-ҷавоб дар чат)"),
    }
    course_label, qa_label = labels.get(lang, labels["ru"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=course_label,
                    callback_data="mode:course",
                )
            ],
            [InlineKeyboardButton(text=qa_label, callback_data="mode:free_qa")],
        ]
    )


def level_keyboard(
    lang: str,
    levels: list[str] | tuple[str, ...] | None = None,
) -> InlineKeyboardMarkup:
    keys = list(levels or ("beginner", "hsk1", "hsk2", "hsk3", "hsk4"))

    def label(level: str) -> str:
        if level == "beginner":
            return t("level_beginner", lang)
        if level.startswith("nhsk") and level[-1:].isdigit():
            return f"HSK 3.0 · N{level[-1]}"
        if level.startswith("hsk") and level[3:].isdigit():
            return f"HSK {level[3:]}"
        return level.upper()

    buttons = [
        InlineKeyboardButton(
            text=label(level),
            callback_data=f"level:{level}",
        )
        for level in keys
    ]
    rows = [buttons[index : index + 2] for index in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=rows)




def daily_practice_finish_keyboard(lang: str) -> InlineKeyboardMarkup:
    labels = {
        "uz": ("📚 Kursni boshlash", "💬 Bepul savol-javobga o'tish"),
        "ru": ("📚 Начать курс", "💬 Перейти в бесплатный вопрос-ответ"),
        "tj": ("📚 Оғози курс", "💬 Ба савол-ҷавоби ройгон гузаштан"),
    }
    course_label, qa_label = labels.get(lang, labels["ru"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=course_label, callback_data="daily_practice:course")],
            [InlineKeyboardButton(text=qa_label, callback_data="mode:free_qa")],
        ]
    )


def daily_practice_check_keyboard(lang: str) -> InlineKeyboardMarkup:
    labels = {
        "uz": "✅ Javoblarni ko'rish",
        "ru": "✅ Посмотреть ответы",
        "tj": "✅ Дидани ҷавобҳо",
    }
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=labels.get(lang, labels["ru"]), callback_data="daily_practice:complete")],
        ]
    )


def _parse_lesson_title(raw: str, lang: str) -> str:
    if not raw:
        return ""
    try:
        data = json.loads(raw)
    except Exception:
        return raw
    if isinstance(data, dict):
        return str(data.get("zh") or data.get(lang) or data.get("uz") or data.get("ru") or raw)
    return raw


def trial_lesson_selection_keyboard(
    lessons: list,
    page: int = 0,
    lang: str = "ru",
) -> InlineKeyboardMarkup:
    page_size = 7
    start = page * page_size
    end = start + page_size
    buttons = []
    for lesson in lessons[start:end]:
        title = _parse_lesson_title(str(getattr(lesson, "title", "") or ""), lang).strip()
        buttons.append([
            InlineKeyboardButton(
                text=f"{lesson.lesson_order}. {title[:48]}",
                callback_data=f"trial_lesson:pick:{lesson.id}",
            )
        ])

    nav = []
    prev_labels = {"tj": "⬅️ Қабл", "uz": "⬅️ Oldingi", "ru": "⬅️ Назад"}
    next_labels = {"tj": "Баъд ➡️", "uz": "Keyingi ➡️", "ru": "Далее ➡️"}
    if page > 0:
        nav.append(InlineKeyboardButton(
            text=prev_labels.get(lang, "⬅️"),
            callback_data=f"trial_lesson:page:{page - 1}",
        ))
    if end < len(lessons):
        nav.append(InlineKeyboardButton(
            text=next_labels.get(lang, "➡️"),
            callback_data=f"trial_lesson:page:{page + 1}",
        ))
    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

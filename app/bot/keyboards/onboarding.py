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


def level_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("level_beginner", lang), callback_data="level:beginner")],
            [
                InlineKeyboardButton(text="HSK 1", callback_data="level:hsk1"),
                InlineKeyboardButton(text="HSK 2", callback_data="level:hsk2"),
            ],
            [
                InlineKeyboardButton(text="HSK 3", callback_data="level:hsk3"),
                InlineKeyboardButton(text="HSK 4", callback_data="level:hsk4"),
            ],
        ]
    )


def trial_lesson_choice_keyboard(lang: str) -> InlineKeyboardMarkup:
    labels = {
        "uz": ("🚀 Tavsiya: 1-darsdan boshlash", "📚 Boshqa dars tanlash"),
        "ru": ("🚀 Рекомендация: начать с 1-го урока", "📚 Выбрать другой урок"),
        "tj": ("🚀 Тавсия: аз дарси 1 оғоз кардан", "📚 Интихоби дарси дигар"),
    }
    first_label, choose_label = labels.get(lang, labels["ru"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=first_label, callback_data="trial_lesson:first")],
            [InlineKeyboardButton(text=choose_label, callback_data="trial_lesson:choose")],
        ]
    )


def daily_practice_entry_keyboard(lang: str) -> InlineKeyboardMarkup:
    labels = {
        "uz": ("🚀 Bugungi 3 daqiqalik mashq", "📚 Kursni boshlash"),
        "ru": ("🚀 Сегодняшняя практика на 3 минуты", "📚 Начать курс"),
        "tj": ("🚀 Машқи 3-дақиқаи имрӯз", "📚 Оғози курс"),
    }
    practice_label, course_label = labels.get(lang, labels["ru"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=practice_label, callback_data="daily_practice:start")],
            [InlineKeyboardButton(text=course_label, callback_data="daily_practice:course")],
        ]
    )


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

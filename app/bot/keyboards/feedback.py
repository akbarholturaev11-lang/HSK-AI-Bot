from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.subscription import subscription_miniapp_button
from app.bot.utils.i18n import t


LIKED_OPTIONS = ("course", "answers", "photo", "practice", "other")
DISLIKED_OPTIONS = ("price", "limits", "unclear", "pace", "other")

# Har bir "yoqdi" javobidan keyin aniqlashtiruvchi 2-qadam. Maqsad — "kurs yoqdi"
# degan umumiy javob o'rniga aynan qaysi qism ishlayotganini bilish.
LIKE_SUB_OPTIONS = {
    "course": ("lessons", "exercises", "voice", "other"),
    "answers": ("speed", "clarity", "examples", "other"),
    "photo": ("hanzi", "translate", "homework", "other"),
    "practice": ("daily", "memorize", "quiz", "other"),
}

# Obunachilar uchun alohida oqim: chegirma emas, "obuna arzidimi?" savoli.
PAID_OPTIONS = ("worth", "useful", "unsure", "regret")
PAID_POSITIVE_OPTIONS = ("worth", "useful")
PAID_SUB_POSITIVE = ("lessons", "voice", "speed", "daily", "other")
PAID_SUB_NEGATIVE = ("content", "slow", "tech", "time", "other")


def feedback_like_label(code: str, lang: str) -> str:
    return t(f"feedback_like_{code}", lang)


def feedback_dislike_label(code: str, lang: str) -> str:
    return t(f"feedback_dislike_{code}", lang)


def feedback_sub_label(code: str, lang: str) -> str:
    return t(f"feedback_sub_{code}", lang)


def feedback_paid_label(code: str, lang: str) -> str:
    return t(f"feedback_paid_{code}", lang)


def is_paid_positive(code: str) -> bool:
    return code in PAID_POSITIVE_OPTIONS


def _column_keyboard(rows: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=data)] for text, data in rows
        ]
    )


def feedback_like_keyboard(feedback_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=feedback_like_label(code, lang),
                    callback_data=f"fb:{feedback_id}:like:{code}",
                )
            ]
            for code in LIKED_OPTIONS
        ]
    )


def feedback_dislike_keyboard(feedback_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=feedback_dislike_label(code, lang),
                    callback_data=f"fb:{feedback_id}:dislike:{code}",
                )
            ]
            for code in DISLIKED_OPTIONS
        ]
    )


def feedback_like_sub_keyboard(feedback_id: int, parent: str, lang: str) -> InlineKeyboardMarkup:
    codes = LIKE_SUB_OPTIONS.get(parent, ("other",))
    return _column_keyboard(
        [
            (feedback_sub_label(code, lang), f"fb:{feedback_id}:lsub:{parent}:{code}")
            for code in codes
        ]
    )


def feedback_paid_keyboard(feedback_id: int, lang: str) -> InlineKeyboardMarkup:
    return _column_keyboard(
        [
            (feedback_paid_label(code, lang), f"fb:{feedback_id}:paid:{code}")
            for code in PAID_OPTIONS
        ]
    )


def feedback_paid_sub_keyboard(feedback_id: int, parent: str, lang: str) -> InlineKeyboardMarkup:
    codes = PAID_SUB_POSITIVE if is_paid_positive(parent) else PAID_SUB_NEGATIVE
    return _column_keyboard(
        [
            (feedback_sub_label(code, lang), f"fb:{feedback_id}:psub:{parent}:{code}")
            for code in codes
        ]
    )


def feedback_cancel_keyboard(feedback_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("feedback_cancel_button", lang),
                    callback_data=f"fb:{feedback_id}:cancel_other",
                )
            ]
        ]
    )


def feedback_price_offer_keyboard(feedback_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                subscription_miniapp_button(
                    lang,
                    source="feedback_price_offer",
                    mode="feedback_discount",
                    feedback_id=feedback_id,
                    text=t("feedback_price_offer_button", lang),
                )
            ]
        ]
    )


def admin_bot_feedback_keyboard(feedback_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="↩️ Javob yozish",
                    callback_data=f"admin_feedback:reply:{feedback_id}",
                )
            ]
        ]
    )


def admin_feedback_reply_cancel_keyboard(feedback_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data=f"admin_feedback:cancel:{feedback_id}",
                )
            ]
        ]
    )

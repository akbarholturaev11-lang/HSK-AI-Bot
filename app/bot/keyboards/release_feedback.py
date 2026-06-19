from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.subscription import subscription_miniapp_button


def release_feedback_rating_keyboard(campaign_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Sinab ko'rish",
                    callback_data=f"relfb:{campaign_id}:try",
                )
            ],
            [
                InlineKeyboardButton(
                    text=str(rating),
                    callback_data=f"relfb:{campaign_id}:rate:{rating}",
                )
                for rating in range(1, 6)
            ]
        ]
    )


def release_feedback_test_rating_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Sinab ko'rish", callback_data="relfb:test")],
            [InlineKeyboardButton(text=str(rating), callback_data="relfb:test") for rating in range(1, 6)],
        ]
    )


def release_feedback_optional_comment_keyboard(campaign_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Izoh yozish", callback_data=f"relfb:{campaign_id}:comment")],
            [InlineKeyboardButton(text="➡️ O'tkazib yuborish", callback_data=f"relfb:{campaign_id}:skip")],
        ]
    )


def release_feedback_discount_keyboard(campaign_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                subscription_miniapp_button(
                    lang,
                    source="release_feedback_discount",
                    mode="admin_discount",
                    campaign_id=campaign_id,
                    text={
                        "uz": "🎁 20% chegirmani olish",
                        "ru": "🎁 Получить скидку 20%",
                        "tj": "🎁 20% тахфифро гирифтан",
                    }.get(lang, "🎁 Получить скидку 20%"),
                )
            ]
        ]
    )


def release_feedback_after_rating_keyboard(
    release_campaign_id: int,
    *,
    discount_campaign_id: int | None,
    lang: str,
) -> InlineKeyboardMarkup:
    rows = []
    if discount_campaign_id:
        rows.append([
            subscription_miniapp_button(
                lang,
                source="release_feedback_discount",
                mode="admin_discount",
                campaign_id=discount_campaign_id,
                text={
                    "uz": "🎁 20% chegirmani olish",
                    "ru": "🎁 Получить скидку 20%",
                    "tj": "🎁 20% тахфифро гирифтан",
                }.get(lang, "🎁 Получить скидку 20%"),
            )
        ])
    rows.extend([
        [InlineKeyboardButton(text="✍️ Izoh yozish", callback_data=f"relfb:{release_campaign_id}:comment")],
        [InlineKeyboardButton(text="➡️ O'tkazib yuborish", callback_data=f"relfb:{release_campaign_id}:skip")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def release_feedback_feature_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💬 Oddiy AI savol", callback_data="rf:feature:qa"),
                InlineKeyboardButton(text="🖼 Foto tahlil", callback_data="rf:feature:image"),
            ],
            [
                InlineKeyboardButton(text="📚 Kurs rejimi", callback_data="rf:feature:course"),
                InlineKeyboardButton(text="👤 Profil", callback_data="rf:feature:profile"),
            ],
            [
                InlineKeyboardButton(text="💳 Obuna/Chegirma", callback_data="rf:feature:subscription"),
                InlineKeyboardButton(text="🧭 Umumiy", callback_data="rf:feature:general"),
            ],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="rf:cancel")],
        ]
    )


def release_feedback_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yangi yangilik", callback_data="rf:new")],
            [InlineKeyboardButton(text="⚡ Course Mini App update", callback_data="rf:template:course_miniapp_v2")],
            [InlineKeyboardButton(text="📋 Rejadagi va oxirgilar", callback_data="rf:list")],
            [InlineKeyboardButton(text="🎯 Kimlarga yuborish", callback_data="rf:filters")],
            [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:menu")],
        ]
    )


def release_feedback_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="rf:cancel")],
        ]
    )


def release_feedback_send_time_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Hozir", callback_data="rf:send_at:now"),
                InlineKeyboardButton(text="Belgilangan vaqt", callback_data="rf:send_at:scheduled"),
            ],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="rf:cancel")],
        ]
    )


def release_feedback_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👁 Test yuborish", callback_data="rf:test")],
            [
                InlineKeyboardButton(text="✅ Saqlash", callback_data="rf:confirm"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="rf:cancel"),
            ],
        ]
    )


def release_feedback_list_keyboard(campaigns) -> InlineKeyboardMarkup:
    rows = []
    for campaign in campaigns:
        rows.append([
            InlineKeyboardButton(
                text=f"📊 #{campaign.id} statistika",
                callback_data=f"rf:stats:{campaign.id}",
            )
        ])
        if campaign.status in {"scheduled", "sending"}:
            rows.append([
                InlineKeyboardButton(
                    text=f"⛔ #{campaign.id} to'xtatish",
                    callback_data=f"rf:stop:{campaign.id}",
                )
            ])
    rows.extend([
        [InlineKeyboardButton(text="➕ Yangi yangilik", callback_data="rf:new")],
        [InlineKeyboardButton(text="⬅️ Yangilik otzivi", callback_data="rf:panel")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def release_feedback_stats_keyboard(campaign_id: int, can_stop: bool) -> InlineKeyboardMarkup:
    rows = []
    if can_stop:
        rows.append([
            InlineKeyboardButton(text="⛔ To'xtatish", callback_data=f"rf:stop:{campaign_id}")
        ])
    rows.extend([
        [InlineKeyboardButton(text="📋 Ro'yxat", callback_data="rf:list")],
        [InlineKeyboardButton(text="⬅️ Yangilik otzivi", callback_data="rf:panel")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

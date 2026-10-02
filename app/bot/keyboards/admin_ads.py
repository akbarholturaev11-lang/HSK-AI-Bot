from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def ad_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yangi reklama", callback_data="ads:new")],
            [InlineKeyboardButton(text="📋 Reklamalar", callback_data="ads:list")],
            [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:menu")],
        ]
    )


def ad_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="ads:cancel")],
        ]
    )


def ad_duration_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1 kun", callback_data="ads:duration:24"),
                InlineKeyboardButton(text="3 kun", callback_data="ads:duration:72"),
                InlineKeyboardButton(text="7 kun", callback_data="ads:duration:168"),
            ],
            [InlineKeyboardButton(text="✍️ Boshqa muddat", callback_data="ads:duration:custom")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="ads:cancel")],
        ]
    )


def ad_send_count_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1 marta", callback_data="ads:count:1"),
                InlineKeyboardButton(text="2 marta", callback_data="ads:count:2"),
                InlineKeyboardButton(text="3 marta", callback_data="ads:count:3"),
            ],
            [
                InlineKeyboardButton(text="5 marta", callback_data="ads:count:5"),
                InlineKeyboardButton(text="✍️ Boshqa", callback_data="ads:count:custom"),
            ],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="ads:cancel")],
        ]
    )


def ad_language_keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    selected_set = set(selected)

    def label(code: str, text: str) -> str:
        return f"✅ {text}" if code in selected_set else text

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=label("uz", "UZ"), callback_data="ads:lang:uz"),
                InlineKeyboardButton(text=label("ru", "RU"), callback_data="ads:lang:ru"),
                InlineKeyboardButton(text=label("tj", "TJ"), callback_data="ads:lang:tj"),
            ],
            [InlineKeyboardButton(text="🌐 Hammasi", callback_data="ads:lang:all")],
            [InlineKeyboardButton(text="✅ Davom etish", callback_data="ads:lang_done")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="ads:cancel")],
        ]
    )


def ad_track_keyboard(selected: str | None = None) -> InlineKeyboardMarkup:
    def label(key: str, text: str) -> str:
        return f"✅ {text}" if selected == key else text

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=label("hsk20", "HSK 2.0"), callback_data="ads:track:hsk20"),
                InlineKeyboardButton(text=label("hsk30", "HSK 3.0"), callback_data="ads:track:hsk30"),
            ],
            [InlineKeyboardButton(text="🌐 Hammasi", callback_data="ads:track:all")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="ads:cancel")],
        ]
    )


def ad_level_keyboard(track: str | None = None, selected: str | None = None) -> InlineKeyboardMarkup:
    if track == "hsk30":
        levels = [("nhsk1", "HSK 3.0 · N1"), ("nhsk2", "HSK 3.0 · N2"), ("nhsk3", "HSK 3.0 · N3")]
    elif track == "hsk20":
        levels = [("beginner", "Boshlang'ich"), ("hsk1", "HSK1"), ("hsk2", "HSK2"), ("hsk3", "HSK3"), ("hsk4", "HSK4")]
    else:
        levels = [
            ("hsk1", "HSK1"), ("hsk2", "HSK2"), ("hsk3", "HSK3"), ("hsk4", "HSK4"),
            ("nhsk1", "3.0 · N1"), ("nhsk2", "3.0 · N2"), ("nhsk3", "3.0 · N3"),
        ]

    rows = []
    for index in range(0, len(levels), 2):
        rows.append([
            InlineKeyboardButton(
                text=("✅ " if selected == key else "") + text,
                callback_data=f"ads:level:{key}",
            )
            for key, text in levels[index:index + 2]
        ])
    rows.append([InlineKeyboardButton(text="🌐 Hammasi", callback_data="ads:level:all")])
    rows.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="ads:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ad_active_policy_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Faol obunachilarga yubormaslik", callback_data="ads:active:no")],
            [InlineKeyboardButton(text="✅ Faol obunachilarga ham yuborish", callback_data="ads:active:yes")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="ads:cancel")],
        ]
    )


def ad_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Hozir", callback_data="ads:start:now"),
                InlineKeyboardButton(text="Belgilangan vaqt", callback_data="ads:start:scheduled"),
            ],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="ads:cancel")],
        ]
    )


def ad_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👁 Admin test", callback_data="ads:test")],
            [
                InlineKeyboardButton(text="✅ Ishga tushirish", callback_data="ads:confirm"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="ads:cancel"),
            ],
        ]
    )


def ad_list_keyboard(campaigns) -> InlineKeyboardMarkup:
    rows = []
    for campaign in campaigns:
        if campaign.is_active:
            rows.append([
                InlineKeyboardButton(
                    text=f"⛔ #{campaign.id} to'xtatish",
                    callback_data=f"ads:disable:{campaign.id}",
                )
            ])
    rows.extend([
        [InlineKeyboardButton(text="➕ Yangi reklama", callback_data="ads:new")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:menu")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

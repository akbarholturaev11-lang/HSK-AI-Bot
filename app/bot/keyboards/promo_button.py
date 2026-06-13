import json
from urllib.parse import urlparse

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.subscription import subscription_miniapp_button
from app.services.support_contact_service import get_admin_contact_url


PROMO_BUTTON_ACTIONS = {
    "subscription",
    "partner",
    "course",
    "reminder",
    "help",
    "contact",
    "profile",
    "url",
}

PROMO_BUTTON_ADMIN_LABELS = {
    "subscription": "Obuna",
    "partner": "Partnyor",
    "course": "Kurs rejimi",
    "reminder": "Eslatma vaqti",
    "help": "Yordam",
    "contact": "Admin kontakti",
    "profile": "Profil",
    "url": "Tashqi link",
}

_DEFAULT_TEXTS = {
    "subscription": {"uz": "💎 Obuna", "ru": "💎 Подписка", "tj": "💎 Обуна"},
    "partner": {"uz": "🤝 Partnyor", "ru": "🤝 Партнёрство", "tj": "🤝 Ҳамкорӣ"},
    "course": {"uz": "📚 Kurs rejimi", "ru": "📚 Режим курса", "tj": "📚 Реҷаи курс"},
    "reminder": {"uz": "⏰ Eslatma vaqti", "ru": "⏰ Напоминание", "tj": "⏰ Вақти ёдраскунак"},
    "help": {"uz": "❓ Yordam", "ru": "❓ Помощь", "tj": "❓ Ёрдам"},
    "contact": {"uz": "👤 Admin bilan aloqa", "ru": "👤 Связаться с админом", "tj": "👤 Тамос бо админ"},
    "profile": {"uz": "👤 Profil", "ru": "👤 Профиль", "tj": "👤 Профил"},
    "url": {"uz": "🔗 Ochish", "ru": "🔗 Открыть", "tj": "🔗 Кушодан"},
}


def default_promo_button_text(action: str, lang: str | None) -> str:
    texts = _DEFAULT_TEXTS.get(action) or _DEFAULT_TEXTS["url"]
    if lang not in {"uz", "ru", "tj"}:
        lang = "ru"
    return texts.get(lang, texts["ru"])


def promo_button_choice_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💎 Obuna", callback_data=f"{prefix}:button:subscription"),
                InlineKeyboardButton(text="🤝 Partnyor", callback_data=f"{prefix}:button:partner"),
            ],
            [
                InlineKeyboardButton(text="📚 Kurs rejimi", callback_data=f"{prefix}:button:course"),
                InlineKeyboardButton(text="⏰ Eslatma vaqti", callback_data=f"{prefix}:button:reminder"),
            ],
            [
                InlineKeyboardButton(text="❓ Yordam", callback_data=f"{prefix}:button:help"),
                InlineKeyboardButton(text="👤 Admin kontakti", callback_data=f"{prefix}:button:contact"),
            ],
            [
                InlineKeyboardButton(text="👤 Profil", callback_data=f"{prefix}:button:profile"),
                InlineKeyboardButton(text="🔗 Tashqi link", callback_data=f"{prefix}:button:url"),
            ],
            [InlineKeyboardButton(text="➡️ Knopkasiz davom etish", callback_data=f"{prefix}:button:none")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"{prefix}:cancel")],
        ]
    )


def promo_button_text_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Default nom", callback_data=f"{prefix}:button_text_default")],
            [InlineKeyboardButton(text="➡️ Knopkasiz davom etish", callback_data=f"{prefix}:button:none")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"{prefix}:cancel")],
        ]
    )


def promo_button_url_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Knopkasiz davom etish", callback_data=f"{prefix}:button:none")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"{prefix}:cancel")],
        ]
    )


def normalize_promo_button_url(value: str | None) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    if raw.startswith("@"):
        raw = f"https://t.me/{raw[1:]}"
    elif raw.startswith("t.me/"):
        raw = f"https://{raw}"
    elif "://" not in raw:
        raw = f"https://{raw}"

    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https", "tg"}:
        return None
    if parsed.scheme in {"http", "https"} and not parsed.netloc:
        return None
    return raw


def normalize_promo_button_config(
    action: str | None,
    *,
    text: str | None = None,
    url: str | None = None,
) -> dict | None:
    if action not in PROMO_BUTTON_ACTIONS:
        return None

    clean_text = (text or "").strip()[:64] or None
    config = {"action": action}
    if clean_text:
        config["text"] = clean_text

    if action == "url":
        clean_url = normalize_promo_button_url(url)
        if not clean_url:
            return None
        config["url"] = clean_url
    return config


def decode_promo_button_config(value) -> dict | None:
    if not value:
        return None
    if isinstance(value, dict):
        data = value
    else:
        try:
            data = json.loads(value)
        except (TypeError, ValueError):
            return None
    if not isinstance(data, dict):
        return None
    return normalize_promo_button_config(
        data.get("action"),
        text=data.get("text"),
        url=data.get("url"),
    )


def encode_promo_button_config(value) -> str | None:
    config = decode_promo_button_config(value)
    if not config:
        return None
    return json.dumps(config, ensure_ascii=False, separators=(",", ":"))


def promo_button_summary(value) -> str:
    config = decode_promo_button_config(value)
    if not config:
        return "Yo'q"
    action = config["action"]
    label = config.get("text") or default_promo_button_text(action, "uz")
    action_label = PROMO_BUTTON_ADMIN_LABELS.get(action, action)
    if action == "url":
        return f"{action_label}: {label} -> {config.get('url')}"
    return f"{action_label}: {label}"


async def build_promo_button_markup(
    session,
    value,
    *,
    lang: str | None,
    source: str,
    contact_url: str | None = None,
) -> InlineKeyboardMarkup | None:
    config = decode_promo_button_config(value)
    if not config:
        return None

    action = config["action"]
    text = config.get("text") or default_promo_button_text(action, lang)

    if action == "subscription":
        button = subscription_miniapp_button(
            lang or "ru",
            source=source,
            mode="subscription",
            text=text,
        )
    elif action == "contact":
        contact_url = contact_url if contact_url is not None else await get_admin_contact_url(session)
        if contact_url:
            button = InlineKeyboardButton(text=text, url=contact_url)
        else:
            button = InlineKeyboardButton(text=text, callback_data="promo:action:help")
    elif action == "url":
        button = InlineKeyboardButton(text=text, url=config["url"])
    else:
        button = InlineKeyboardButton(text=text, callback_data=f"promo:action:{action}")

    return InlineKeyboardMarkup(inline_keyboard=[[button]])

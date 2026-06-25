from aiogram import Router, F
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from html import escape
from math import isfinite
from zoneinfo import ZoneInfo

from app.bot.fsm.admin_portfolio import AdminPortfolioStates
from app.bot.fsm.admin_management import AdminHelpStates, AdminPriceStates, AdminRequiredChannelStates, AdminUserStates
from app.config import settings
from app.repositories.bot_setting_repo import BotSettingRepository
from app.repositories.user_repo import UserRepository
from app.repositories.course_audio_repo import CourseAudioRepository
from app.db.models.user import User
from app.db.models.payment import Payment
from app.db.models.course_progress import CourseProgress
from app.db.models.referral import Referral
from app.db.models.bot_feedback import BotFeedback
from app.services.ai_usage_budget_service import USD_TO_SOMONI, USD_TO_YUAN
from app.services.admin_stats_service import miniapp_course_stats
from app.services.course_miniapp_admin_analytics_service import CourseMiniAppAdminAnalyticsService
from app.services.portfolio_service import PortfolioService
from app.services.payment_qr_code_service import (
    PaymentQrCodeService,
    SUBSCRIPTION_DISCOUNT_20_QR_SCOPE,
    SUBSCRIPTION_QR_SCOPE,
)
from app.services.required_channel_service import (
    MAIN_CHANNEL_USERNAME,
    RequiredChannelService,
    is_main_channel,
    normalize_channel_username,
)
from app.services.subscription_currency_service import (
    SUBSCRIPTION_USD_RATE_KEYS,
    SubscriptionCurrencyService,
    format_subscription_price,
)
from app.services.subscription_price_service import PAYMENT_METHODS, PLANS, SubscriptionPriceService
from app.services.subscription_miniapp_service import PAYMENT_DETAILS_KEY
from app.services.support_contact_service import (
    ADMIN_CONTACT_KEY,
    admin_contact_url,
    get_admin_contact,
    normalize_admin_contact,
)
from app.services.help_settings_service import (
    HELP_LANGS,
    HELP_VIDEO_FIELD_BY_KEY,
    HELP_VIDEO_FIELDS,
    normalize_help_url,
)
from app.bot.handlers.admin_broadcast import open_broadcast_panel_for_callback
from app.bot.utils.workflow_message import (
    delete_message_safely,
    edit_callback_workflow_message,
    edit_stored_workflow_message,
)

router = Router()

ADMIN_MENU_TEXT = "<b>🛠 Admin panel</b>\n\nQuyidagi amallardan birini tanlang:"
_ADMIN_FLOW_CHAT_ID = "admin_flow_chat_id"
_ADMIN_FLOW_MSG_ID = "admin_flow_msg_id"
ADMIN_STATS_TZ = ZoneInfo("Asia/Shanghai")


def _is_admin(user_id: int) -> bool:
    admin_ids = [int(x.strip()) for x in settings.ADMIN_IDS.split(",") if x.strip()]
    return user_id in admin_ids


def _pct(part: int, total: int) -> float:
    return round(part / total * 100, 1) if total > 0 else 0.0


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="adm:stats")],
        [InlineKeyboardButton(text="🔎 Foydalanuvchi qidirish", callback_data="adm:user_search_info")],
        [InlineKeyboardButton(text="💼 Portfel", callback_data="adm:portfolio")],
        [InlineKeyboardButton(text="💳 Obuna narxlari", callback_data="adm:prices")],
        [InlineKeyboardButton(text="📣 Majburiy kanal obunasi", callback_data="adm:channels")],
        [InlineKeyboardButton(text="🗑 Foydalanuvchini o'chirish", callback_data="adm:deleteuser_info")],
        [InlineKeyboardButton(text="📢 Ommaviy xabar", callback_data="adm:broadcast_info")],
        [InlineKeyboardButton(text="📣 Reklama kampaniyasi", callback_data="adm:ads_panel")],
        [InlineKeyboardButton(text="🆕 Yangilik otzivi", callback_data="adm:release_feedback")],
        [InlineKeyboardButton(text="🎁 Chegirma boshqaruv", callback_data="adm:discount_panel")],
        [InlineKeyboardButton(text="🤝 Hamkorlar", callback_data="adm:partners")],
        [InlineKeyboardButton(text="🆘 Yordam sozlamalari", callback_data="adm:help_settings")],
        [InlineKeyboardButton(text="✅ Obuna berish", callback_data="adm:giveaccess_info")],
        [InlineKeyboardButton(text="🎵 Audio boshqaruv", callback_data="adm:audio_panel")],
    ])


def admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:menu")],
    ])


def admin_stats_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Otziv statistikasi", callback_data="adm:feedback_stats")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:menu")],
    ])


def help_settings_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Yordam sozlamalari", callback_data="adm:help_settings")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:menu")],
    ])


def help_settings_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for field in HELP_VIDEO_FIELDS:
        rows.extend([
            [
                InlineKeyboardButton(
                    text=f"{field.icon} {field.label} · TJ",
                    callback_data=f"adm:help_link:{field.key}:tj",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{field.icon} {field.label} · RU",
                    callback_data=f"adm:help_link:{field.key}:ru",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{field.icon} {field.label} · UZ",
                    callback_data=f"adm:help_link:{field.key}:uz",
                )
            ],
        ])
    rows.append([InlineKeyboardButton(text="🆘 Admin aloqa linki", callback_data="adm:help_link:admin_contact")])
    rows.append([InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _help_lang_label(lang: str | None) -> str:
    return {"tj": "TJ", "ru": "RU", "uz": "UZ"}.get(lang or "", "—")


async def help_settings_text(session) -> str:
    repo = BotSettingRepository(session)
    lines = [
        "🆘 <b>Yordam sozlamalari</b>",
        "",
        "Video linklar 3 tilda alohida boshqariladi. Bo'sh link yordam matnida ko'rsatilmaydi.",
        "",
    ]
    for field in HELP_VIDEO_FIELDS:
        lines.append(f"{field.icon} <b>{escape(field.label)}</b>")
        for lang in HELP_LANGS:
            current = normalize_help_url(await repo.get(field.setting_key(lang)))
            lines.append(f"{_help_lang_label(lang)}: <code>{escape(current or '—')}</code>")
        lines.append("")

    contact = await get_admin_contact(session)
    contact_url = admin_contact_url(contact)
    lines.extend([
        "🆘 <b>Admin aloqa linki</b>",
        f"<code>{escape(contact_url or contact or '—')}</code>",
        "",
        "Tahrirlashda linkni tozalash uchun <code>-</code> yuboring.",
    ])
    return "\n".join(lines).strip()


def portfolio_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 Tarix", callback_data="adm:portfolio_history")],
        [
            InlineKeyboardButton(text="➕ Foyda qo'shish", callback_data="adm:portfolio_profit_info"),
            InlineKeyboardButton(text="➖ Rasxod qo'shish", callback_data="adm:portfolio_expense_info"),
        ],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:menu")],
    ])


def portfolio_history_keyboard(rows) -> InlineKeyboardMarkup:
    buttons = []
    for row in rows:
        if row.source not in PortfolioService.MANUAL_SOURCES:
            continue
        icon = _portfolio_type_icon(row.transaction_type)
        buttons.append([
            InlineKeyboardButton(
                text=f"✏️ #{row.id} {icon} {_usd(row.amount_usd)}",
                callback_data=f"adm:portfolio_edit:{row.id}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Portfel", callback_data="adm:portfolio")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def portfolio_edit_type_keyboard(transaction_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➕ Foyda",
                callback_data=f"adm:portfolio_edit_type:{transaction_id}:profit",
            ),
            InlineKeyboardButton(
                text="➖ Rasxod",
                callback_data=f"adm:portfolio_edit_type:{transaction_id}:expense",
            ),
        ],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="adm:portfolio_cancel")],
        [InlineKeyboardButton(text="⬅️ Portfel", callback_data="adm:portfolio")],
    ])


def portfolio_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="adm:portfolio_cancel")],
        [InlineKeyboardButton(text="⬅️ Portfel", callback_data="adm:portfolio")],
    ])


async def _edit_callback_message(
    callback: CallbackQuery,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
) -> Message | None:
    if not callback.message:
        return None
    try:
        edited = await callback.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        return edited if isinstance(edited, Message) else callback.message
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return callback.message
        return await callback.message.answer(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )


async def _edit_message_by_id(
    message: Message,
    *,
    chat_id: int | None,
    message_id: int | None,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
) -> bool:
    if not chat_id or not message_id:
        return False
    try:
        await message.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        return True
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return True
        return False


async def _edit_admin_flow_callback(
    callback: CallbackQuery,
    state: FSMContext,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    await edit_callback_workflow_message(
        callback,
        state,
        text,
        chat_id_key=_ADMIN_FLOW_CHAT_ID,
        message_id_key=_ADMIN_FLOW_MSG_ID,
        reply_markup=reply_markup,
    )


async def _edit_admin_flow_message(
    message: Message,
    state: FSMContext,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    await edit_stored_workflow_message(
        message,
        state,
        text,
        chat_id_key=_ADMIN_FLOW_CHAT_ID,
        message_id_key=_ADMIN_FLOW_MSG_ID,
        reply_markup=reply_markup,
    )


async def _send_or_edit_portfolio_prompt(
    *,
    state: FSMContext,
    message: Message,
    text: str,
) -> None:
    data = await state.get_data()
    chat_id = data.get("portfolio_prompt_chat_id")
    message_id = data.get("portfolio_prompt_message_id")
    edited = await _edit_message_by_id(
        message,
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        reply_markup=portfolio_cancel_keyboard(),
    )
    if edited:
        return

    sent = await message.answer(
        text,
        reply_markup=portfolio_cancel_keyboard(),
        parse_mode="HTML",
    )
    await state.update_data(
        portfolio_prompt_chat_id=sent.chat.id,
        portfolio_prompt_message_id=sent.message_id,
    )


def _usd(value: float) -> str:
    return f"${value:,.2f}"


def _signed_usd(value: float) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}${abs(value):,.2f}"


def _portfolio_type_label(transaction_type: str) -> str:
    return "foyda" if transaction_type == "profit" else "rasxod"


def _portfolio_type_icon(transaction_type: str) -> str:
    return "➕" if transaction_type == "profit" else "➖"


def _parse_amount_currency(text: str) -> tuple[float, str] | None:
    parts = (text or "").strip().split(maxsplit=2)
    if len(parts) < 2:
        return None
    try:
        amount = float(parts[0].replace(",", "."))
    except ValueError:
        return None
    if not isfinite(amount) or amount <= 0:
        return None
    return amount, parts[1]


def _method_label(method: str) -> str:
    return {
        "visa": "Visa/Card TJS",
        "alipay": "Alipay/¥",
        "wechat": "WeChat/¥",
    }.get(method, method)


def _plan_label_admin(plan: str) -> str:
    return {"10_days": "10 kun", "1_month": "1 oy"}.get(plan, plan)


def _price_qr_items(method: str, plan: str, amount: int) -> list[dict]:
    discount_amount = int(round(amount * 0.8))
    return [
        {
            "scope": SUBSCRIPTION_QR_SCOPE,
            "payment_method": method,
            "plan_type": plan,
            "amount": amount,
            "currency": "¥",
            "label": "asosiy narx",
        },
        {
            "scope": SUBSCRIPTION_DISCOUNT_20_QR_SCOPE,
            "payment_method": method,
            "plan_type": plan,
            "amount": discount_amount,
            "currency": "¥",
            "label": "20% chegirma narxi",
        },
    ]


def _qr_item_prompt(item: dict, index: int, total: int) -> str:
    return (
        f"📱 <b>QR kod yuklash</b> ({index + 1}/{total})\n\n"
        f"Usul: <b>{PaymentQrCodeService.method_label(item['payment_method'])}</b>\n"
        f"Tarif: <b>{_plan_label_admin(item['plan_type'])}</b>\n"
        f"Narx: <b>{format_subscription_price(int(item['amount']), item['currency'])}</b>\n"
        f"Turi: <b>{escape(str(item['label']))}</b>\n\n"
        "Shu narxga mos QR kod rasmini yuboring."
    )


async def _edit_price_qr_prompt(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    items = data.get("price_qr_items") or []
    index = int(data.get("price_qr_index") or 0)
    if not items or index >= len(items):
        await _edit_admin_flow_message(message, state, "❌ QR navbati topilmadi.", reply_markup=prices_keyboard())
        return
    await _edit_admin_flow_message(
        message,
        state,
        _qr_item_prompt(items[index], index, len(items)),
        reply_markup=admin_back_keyboard(),
    )


async def _prices_text(session) -> str:
    prices = await SubscriptionPriceService(session).all_prices()
    currency_service = SubscriptionCurrencyService(session)
    auto_rates = await currency_service.is_auto_rate_enabled()
    rates, rate_source = await currency_service.effective_rates()
    rate_mode = "Avto real kurs" if auto_rates and rate_source == "auto" else "Avto fallback: qo'lbola kurs" if auto_rates else "Qo'lbola admin kurs"
    lines = ["💳 <b>Obuna narxlari</b>", ""]
    for price in prices:
        lines.append(
            f"{_method_label(price.payment_method)} · {_plan_label_admin(price.plan_type)}: "
            f"<b>{format_subscription_price(price.amount, price.currency)}</b>"
        )
    lines.extend(
        [
            "",
            "💱 <b>Obuna fallback kurslari</b>",
            f"Rejim: <b>{rate_mode}</b>",
            f"1 USD = <code>{SubscriptionCurrencyService.format_rate('tjs', rates['tjs'])}</code> TJS",
            f"1 USD = <code>{SubscriptionCurrencyService.format_rate('uzs', rates['uzs'])}</code> UZS",
            f"1 USD = <code>{SubscriptionCurrencyService.format_rate('rub', rates['rub'])}</code> RUB",
            f"1 USD = <code>{SubscriptionCurrencyService.format_rate('cny', rates['cny'])}</code> CNY",
        ]
    )
    details = await BotSettingRepository(session).get(PAYMENT_DETAILS_KEY)
    details = (details or settings.PAYMENT_DETAILS or "").strip()
    short = (details[:60] + "…") if len(details) > 60 else (details or "—")
    lines.extend([
        "",
        "💳 <b>Karta rekviziti (mini app)</b>",
        f"<code>{escape(short)}</code>",
        "",
        "<i>Visa/Card obuna narxi faqat TJSda yuradi. Alipay/WeChat narxlari ¥ bo'lib qoladi.</i>",
        "",
        "Narxni o'zgartirish uchun pastdagi tugmani tanlang.",
    ])
    return "\n".join(lines)


def prices_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for method in PAYMENT_METHODS:
        rows.append([
            InlineKeyboardButton(
                text=f"{_method_label(method)} · 10 kun",
                callback_data=f"adm:price_set:{method}:10_days",
            ),
            InlineKeyboardButton(
                text=f"{_method_label(method)} · 1 oy",
                callback_data=f"adm:price_set:{method}:1_month",
            ),
        ])
    rows.append([
        InlineKeyboardButton(text="💱 TJS kurs", callback_data="adm:visa_rate_set:tjs"),
        InlineKeyboardButton(text="💱 UZS kurs", callback_data="adm:visa_rate_set:uzs"),
        InlineKeyboardButton(text="💱 RUB kurs", callback_data="adm:visa_rate_set:rub"),
    ])
    rows.append([
        InlineKeyboardButton(text="💴 CNY kurs", callback_data="adm:visa_rate_set:cny"),
    ])
    rows.append([
        InlineKeyboardButton(text="🔄 Avto kursni yoqish", callback_data="adm:visa_rate_auto:on"),
        InlineKeyboardButton(text="✋ Avto kursni o'chirish", callback_data="adm:visa_rate_auto:off"),
    ])
    rows.append([InlineKeyboardButton(text="💳 Karta rekviziti", callback_data="adm:payment_details")])
    rows.append([InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def channel_panel_keyboard(enabled: bool, channels) -> InlineKeyboardMarkup:
    rows = [[
        InlineKeyboardButton(
            text="🟢 Yoqilgan" if enabled else "⚪ Yoqish",
            callback_data="adm:channels_mode:on",
        ),
        InlineKeyboardButton(
            text="🔴 O'chirilgan" if not enabled else "⚪ O'chirish",
            callback_data="adm:channels_mode:off",
        ),
    ]]
    rows.append([InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="adm:channel_add")])
    for channel in channels[:20]:
        label = "✅" if channel.is_active else "⛔"
        rows.append([
            InlineKeyboardButton(
                text=f"{label} #{channel.id} {channel.title[:28]}",
                callback_data=f"adm:channel_toggle:{channel.id}",
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"adm:channel_delete:{channel.id}",
            ),
        ])
    rows.append([InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _channel_panel_text(session) -> tuple[str, InlineKeyboardMarkup]:
    service = RequiredChannelService(session)
    enabled = await service.is_enabled()
    channels = await service.list_channels()
    active_count = len([item for item in channels if item.is_active])
    lines = [
        "📣 <b>Majburiy kanal obunasi</b>",
        "",
        f"Rejim: <b>{_enabled_label(enabled)}</b>",
        f"Aktiv kanallar: <b>{active_count}</b>",
        "Ishlash joyi: <b>course 2-qism yangi so'zlar checkpointidan keyin</b>",
        "",
        "Kanal qo'shish oson:",
        "1) Kanaldan bitta postni forward qiling",
        "2) yoki <code>@channel</code> / <code>t.me/channel</code> yuboring",
    ]
    if channels:
        lines.extend(["", "<b>Kanallar:</b>"])
        for channel in channels[:20]:
            status = "Yoqilgan" if channel.is_active else "O'chirilgan"
            lines.append(
                f"#{channel.id} [{status}] <code>{escape(channel.chat_id)}</code> — {escape(channel.title)}"
            )
    return "\n".join(lines), channel_panel_keyboard(enabled, channels)


def _username_from_tme_link(value: str) -> str | None:
    value = (value or "").strip()
    prefixes = ("https://t.me/", "http://t.me/", "t.me/")
    for prefix in prefixes:
        if value.startswith(prefix):
            tail = value[len(prefix):].strip("/")
            if tail and not tail.startswith("+"):
                username = tail.split("/")[0]
                return username if username else None
    return None


def _parse_channel_input(text: str) -> tuple[str, str | None, str] | None:
    parts = (text or "").strip().split()
    if not parts:
        return None

    first = parts[0]
    invite_link = None
    title_parts = parts[1:]
    username = _username_from_tme_link(first)

    if username:
        chat_id = f"@{username}"
        invite_link = f"https://t.me/{username}"
        title = " ".join(title_parts) if title_parts else username
        return chat_id, invite_link, title[:180]

    if first.startswith("@"):
        chat_id = first
        invite_link = f"https://t.me/{first.lstrip('@')}"
        title = " ".join(title_parts) if title_parts else first.lstrip("@")
        return chat_id, invite_link, title[:180]

    if first.startswith("-100"):
        chat_id = first
        if title_parts and title_parts[0].startswith(("http://", "https://")):
            invite_link = title_parts[0]
            title_parts = title_parts[1:]
        title = " ".join(title_parts) if title_parts else first
        return chat_id, invite_link, title[:180]

    return None


async def _extract_channel_input(message: Message) -> tuple[str, str | None, str] | None:
    origin = getattr(message, "forward_origin", None)
    chat = getattr(origin, "chat", None) if origin else None
    if not chat:
        chat = getattr(message, "forward_from_chat", None)

    if chat:
        username = getattr(chat, "username", None)
        chat_id = f"@{username}" if username else str(chat.id)
        invite_link = f"https://t.me/{username}" if username else None
        title = getattr(chat, "title", None) or username or str(chat.id)
        return chat_id, invite_link, title[:180]

    return _parse_channel_input(message.text or "")


async def _fill_channel_invite_link(message: Message, chat_id: str, invite_link: str | None) -> str | None:
    if invite_link:
        return invite_link
    try:
        link = await message.bot.create_chat_invite_link(chat_id=chat_id, name="HSK AI required subscription")
        return link.invite_link
    except Exception:
        return None


async def _resolve_channel_title(message: Message, chat_id: str, fallback_title: str) -> str:
    try:
        chat = await message.bot.get_chat(chat_id)
        title = getattr(chat, "title", None) or getattr(chat, "username", None)
        if title:
            return str(title)[:180]
    except Exception:
        pass
    if is_main_channel(chat_id):
        return MAIN_CHANNEL_USERNAME
    username = normalize_channel_username(chat_id)
    return (fallback_title or username or chat_id)[:180]


def _fmt_dt(value) -> str:
    if not value:
        return "—"
    try:
        return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return str(value)


def _admin_label(value, labels: dict[str, str]) -> str:
    raw = str(value or "—")
    return labels.get(raw, raw.replace("_", " "))


def _yes_no(value) -> str:
    return "Ha" if value else "Yo'q"


def _enabled_label(value) -> str:
    return "Yoqilgan" if value else "O'chirilgan"


def _payment_total_text(rows) -> str:
    totals = [
        format_subscription_price(int(row.total_sum or 0), row.currency)
        for row in rows
        if row.total_sum
    ]
    return " · ".join(totals) if totals else "—"


def _course_step_label(value: str | None) -> str:
    step = str(value or "—")
    exact_labels = {
        "intro": "Kirish",
        "vocab": "So'zlar",
        "dialogue": "Dialog",
        "grammar": "Grammatika",
        "exercise": "Test",
        "satisfaction_check": "Dars bahosi",
        "homework": "Uyga vazifa",
        "completed": "Tugatilgan",
    }
    if step in exact_labels:
        return exact_labels[step]

    prefix_labels = {
        "block_vocab_": "blok: so'zlar",
        "block_grammar_": "blok: grammatika",
        "block_quiz_": "blok: test",
        "vocab_": "qism: so'zlar",
        "dialogue_": "dialog",
    }
    for prefix, label in prefix_labels.items():
        if step.startswith(prefix):
            return f"{step.removeprefix(prefix)}-{label}"
    return step.replace("_", " ")


def _homework_status_label(value: str | None) -> str:
    return _admin_label(
        value,
        {
            "none": "Boshlanmagan",
            "assigned": "Berilgan",
            "completed": "Tugatilgan",
        },
    )


async def _admin_user_info_text(session, user: User) -> str:
    payment_rows = await session.execute(
        select(Payment)
        .where(Payment.user_telegram_id == user.telegram_id)
        .order_by(Payment.submitted_at.desc())
        .limit(5)
    )
    payments = list(payment_rows.scalars().all())
    payment_count = (await session.execute(
        select(func.count()).select_from(Payment).where(Payment.user_telegram_id == user.telegram_id)
    )).scalar() or 0
    approved_totals = (await session.execute(
        select(Payment.currency, func.sum(Payment.amount).label("total_sum")).where(
            Payment.user_telegram_id == user.telegram_id,
            Payment.payment_status == "approved",
        ).group_by(Payment.currency)
    )).fetchall()

    referral_rows = await session.execute(
        select(Referral.status, func.count().label("cnt"))
        .where(Referral.referrer_telegram_id == user.telegram_id)
        .group_by(Referral.status)
    )
    referral_counts = {row.status: row.cnt for row in referral_rows.fetchall()}
    referral_total = sum(referral_counts.values())
    invited_by = await session.execute(
        select(Referral).where(Referral.invited_user_telegram_id == user.telegram_id).limit(1)
    )
    invited_ref = invited_by.scalar_one_or_none()

    progress_result = await session.execute(
        select(CourseProgress).where(CourseProgress.user_id == user.id).limit(1)
    )
    progress = progress_result.scalar_one_or_none()

    status_labels = {
        "active": "Faol",
        "trial": "Sinov rejimi",
        "expired": "Muddati tugagan",
        "blocked": "Bloklangan",
        "free": "Bepul",
    }
    payment_status_labels = {
        "none": "To'lov qilinmagan",
        "draft": "Tarif tanlangan",
        "pending": "Tekshiruv kutilmoqda",
        "approved": "Tasdiqlangan",
        "rejected": "Rad etilgan",
    }
    learning_mode_labels = {"qa": "Savol-javob", "course": "Kurs"}
    language_labels = {"tj": "Tojikcha", "uz": "O'zbekcha", "ru": "Ruscha"}
    plan_labels = {"10_days": "10 kunlik", "1_month": "1 oylik"}
    bonus_balance = max((user.bonus_questions or 0) - (user.bonus_questions_used or 0), 0)

    lines = [
        "🔎 <b>Foydalanuvchi ma'lumoti</b>",
        "",
        "👤 <b>Asosiy ma'lumotlar</b>",
        f"Ism: <b>{escape(user.full_name or '—')}</b>",
        f"Telegram ID: <code>{user.telegram_id}</code>",
        f"Username: <b>@{escape(user.username)}</b>" if user.username else "Username: —",
        f"Til: <b>{_admin_label(user.language, language_labels)}</b>",
        f"Daraja: <b>{escape(user.level or '—')}</b>",
        f"Ro'yxatdan o'tgan: <code>{_fmt_dt(user.created_at)}</code>",
        f"Oxirgi faollik: <code>{_fmt_dt(user.last_active_at)}</code>",
        "",
        "🔐 <b>Kirish va obuna</b>",
        f"Holat: <b>{_admin_label(user.status, status_labels)}</b>",
        f"O'qish rejimi: <b>{_admin_label(user.learning_mode, learning_mode_labels)}</b>",
        f"To'lov holati: <b>{_admin_label(user.payment_status, payment_status_labels)}</b>",
        f"To'lov usuli: <b>{escape(_method_label(user.payment_method)) if user.payment_method else '—'}</b>",
        f"Tanlangan tarif: <b>{_admin_label(user.selected_plan_type, plan_labels)}</b>",
        f"Obuna boshlangan: <code>{_fmt_dt(user.start_date)}</code>",
        f"Obuna tugaydi: <code>{_fmt_dt(user.end_date)}</code>",
        f"Savollar: <b>{user.questions_used}/{user.question_limit}</b>",
        f"Bonus savollar qoldig'i: <b>{bonus_balance}</b>",
        f"Daily practice boshlandi: <code>{_fmt_dt(user.daily_practice_started_at)}</code>",
        f"Daily practice tugadi: <code>{_fmt_dt(user.daily_practice_completed_at)}</code>",
        f"Daily streak: <b>{user.daily_practice_streak or 0}</b>",
        f"Daily oxirgi kun: <code>{user.daily_practice_last_day or '—'}</code>",
        f"Sinov darsi ID: <b>{user.trial_course_lesson_id or '—'}</b>",
        f"Sinov darsi boshlandi: <code>{_fmt_dt(user.trial_course_started_at)}</code>",
        f"Sinov darsi tugadi: <code>{_fmt_dt(user.trial_course_completed_at)}</code>",
        f"Sinov AI xato tahlili: <code>{_fmt_dt(user.trial_quiz_explanation_used_at)}</code>",
        f"Kanal checkpoint: <code>{_fmt_dt(user.force_sub_required_at)}</code>",
        "",
        "🎁 <b>Referallar va chegirma</b>",
        f"Chaqirganlari jami: <b>{referral_total}</b>",
        f"Faollashgan: <b>{referral_counts.get('active', 0)}</b>",
        f"Kutilmoqda: <b>{referral_counts.get('pending', 0)}</b>",
        f"Chegirma hisobi: <b>{user.discount_referral_count}/3</b>",
        f"Chegirmaga tayyor: <b>{_yes_no(user.discount_eligible)}</b>",
        f"Chegirma ishlatilgan: <b>{_yes_no(user.discount_used)}</b>",
        f"Taklif qilgan foydalanuvchi: <code>{invited_ref.referrer_telegram_id if invited_ref else '—'}</code>",
        "",
        "💳 <b>To'lovlar</b>",
        f"Jami arizalar: <b>{payment_count}</b>",
        f"Tasdiqlangan tushum: <b>{_payment_total_text(approved_totals)}</b>",
    ]
    if payments:
        lines.append("<b>Oxirgi 5 ta ariza:</b>")
        for payment in payments:
            lines.append(
                f"#{payment.id} · {_admin_label(payment.payment_status, payment_status_labels)}\n"
                f"  {_admin_label(payment.plan_type, plan_labels)} · "
                f"{escape(_method_label(payment.payment_method)) if payment.payment_method else '—'} · "
                f"{format_subscription_price(payment.amount, payment.currency)}\n"
                f"  <code>{_fmt_dt(payment.submitted_at)}</code>"
            )
    else:
        lines.append("Hali to'lov arizasi yo'q.")

    lines.extend(["", "📚 <b>Kurs natijalari</b>"])
    if progress:
        lines.extend([
            f"Daraja: <b>{escape((progress.level or '—').upper())}</b>",
            f"Joriy dars ID: <code>{progress.current_lesson_id or '—'}</code>",
            f"Joriy bosqich: <b>{escape(_course_step_label(progress.current_step))}</b>",
            f"Tugatilgan darslar: <b>{progress.completed_lessons_count}</b>",
            f"Uyga vazifa: <b>{escape(_homework_status_label(progress.homework_status))}</b>",
            f"Eslatma: <b>{_enabled_label(progress.reminder_enabled)}</b> · {progress.reminder_time or '—'}",
            f"Oxirgi ochilgan: <code>{_fmt_dt(progress.last_opened_at)}</code>",
            f"Oxirgi tugatilgan: <code>{_fmt_dt(progress.last_completed_at)}</code>",
        ])
    else:
        lines.append("Kurs hali boshlanmagan.")

    return "\n".join(lines)


async def _start_portfolio_flow(
    *,
    state: FSMContext,
    callback: CallbackQuery,
    transaction_type: str,
) -> None:
    await state.clear()
    await state.update_data(portfolio_transaction_type=transaction_type)
    await state.set_state(AdminPortfolioStates.waiting_amount)
    icon = _portfolio_type_icon(transaction_type)
    label = _portfolio_type_label(transaction_type)
    edited = await _edit_callback_message(
        callback,
        f"{icon} <b>{label.capitalize()} qo'shish</b>\n\n"
        "Avval summa va currency yuboring:\n"
        "<code>50 usd</code>\n"
        "<code>120 somoni</code>\n"
        "<code>200 ¥</code>\n\n"
        "Keyingi xabarda bot sababini so'raydi.",
        reply_markup=portfolio_cancel_keyboard(),
        parse_mode="HTML",
    )
    if edited:
        await state.update_data(
            portfolio_prompt_chat_id=edited.chat.id,
            portfolio_prompt_message_id=edited.message_id,
        )


async def _ask_portfolio_reason(
    *,
    state: FSMContext,
    message: Message,
    transaction_type: str,
    amount: float,
    currency: str,
) -> None:
    if PortfolioService(None).amount_to_usd(amount, currency) is None:
        await _send_or_edit_portfolio_prompt(
            state=state,
            message=message,
            text="❌ Currency noto'g'ri. Faqat usd, somoni yoki ¥ ishlat.",
        )
        return

    await state.update_data(
        portfolio_transaction_type=transaction_type,
        portfolio_amount=amount,
        portfolio_currency=currency,
    )
    await state.set_state(AdminPortfolioStates.waiting_reason)
    icon = _portfolio_type_icon(transaction_type)
    label = _portfolio_type_label(transaction_type)
    await _send_or_edit_portfolio_prompt(
        state=state,
        message=message,
        text=(
            f"{icon} <b>{amount:g} {escape(currency)}</b> {label} uchun sababini yozing.\n\n"
            "Masalan:\n"
            "<code>OpenAI to'lov</code>\n"
            "<code>Reklama tushumi</code>\n"
            "<code>Railway oylik to'lov</code>"
        ),
    )


async def _start_portfolio_command_flow(
    *,
    message: Message,
    state: FSMContext,
    transaction_type: str,
) -> None:
    parts = message.text.strip().split(maxsplit=3)
    if len(parts) < 3:
        command = "/portfolio_profit" if transaction_type == "profit" else "/portfolio_expense"
        await message.answer(
            f"Foydalanish: <code>{command} 50 usd</code>\n\n"
            "Sababini keyingi xabarda bot o'zi so'raydi.",
            parse_mode="HTML",
        )
        return

    parsed = _parse_amount_currency(" ".join(parts[1:3]))
    if not parsed:
        await message.answer("❌ Summa formati noto'g'ri. Masalan: <code>50 usd</code>", parse_mode="HTML")
        return

    amount, currency = parsed
    await _ask_portfolio_reason(
        state=state,
        message=message,
        transaction_type=transaction_type,
        amount=amount,
        currency=currency,
    )


def _portfolio_summary_text(summary) -> str:
    status = "🟢 PLUS" if summary.net_usd >= 0 else "🔴 MINUS"
    return (
        f"💼 <b>Portfel</b>\n"
        f"{'─' * 30}\n\n"
        f"<b>💳 Obunalar</b>\n"
        f"  Tasdiqlangan: <b>{summary.approved_payments}</b>\n"
        f"  Brutto tushum: <b>{_usd(summary.gross_revenue_usd)}</b>\n"
        f"  Kurs: <code>1$ = {USD_TO_SOMONI} somoni</code>, <code>1$ = {USD_TO_YUAN} ¥</code>\n\n"
        f"<b>📈 Foyda</b>\n"
        f"  Obunalardan auto tushum: <b>{_usd(summary.subscription_profit_usd)}</b>\n"
        f"  Qo'lda qo'shilgan foyda: <b>{_usd(summary.manual_profit_usd)}</b>\n"
        f"  Jami foyda: <b>{_usd(summary.total_profit_usd)}</b>\n\n"
        f"<b>📉 Rasxod</b>\n"
        f"  Qo'lda qo'shilgan rasxod: <b>{_usd(summary.manual_expense_usd)}</b>\n"
        f"  Jami rasxod: <b>{_usd(summary.total_expense_usd)}</b>\n\n"
        f"<b>📊 Holat</b>\n"
        f"  Net: <b>{_signed_usd(summary.net_usd)}</b>\n"
        f"  Holat: <b>{status}</b>\n\n"
        f"<i>OpenAI, Railway, reklama va boshqa tushum/rasxodlar tokenlardan avtomatik olinmaydi. Ularni o'zingiz +/- qilib kiritasiz.</i>"
    )


def _portfolio_history_text(rows) -> str:
    if not rows:
        return "📜 <b>Portfel history</b>\n\nHali transaction yo'q."

    lines = ["📜 <b>Portfel history</b>", ""]
    for row in rows:
        created = row.created_at
        if created and created.tzinfo:
            created = created.astimezone(timezone.utc)
        date_text = created.strftime("%d.%m %H:%M") if created else "-"
        icon = "📈" if row.transaction_type == "profit" else "📉"
        sign = "+" if row.transaction_type == "profit" else "-"
        source = escape(row.source.replace("_", " "))
        note = escape(row.note or "")
        original = ""
        if row.original_amount is not None and row.original_currency:
            original = f" · {row.original_amount:g} {escape(row.original_currency)}"
        lines.append(
            f"{icon} <code>#{row.id}</code> · <code>{date_text}</code> {sign}{_usd(row.amount_usd)}"
            f"{original}\n"
            f"  <b>{source}</b>{f' — {note}' if note else ''}"
        )
    return "\n\n".join(lines)


@router.message(Command("admin"))
async def admin_menu_handler(message: Message, session):
    if not _is_admin(message.from_user.id):
        return
    await message.answer(
        ADMIN_MENU_TEXT,
        reply_markup=admin_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adm:menu")
async def admin_menu_callback(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.answer()
    await _edit_callback_message(
        callback,
        ADMIN_MENU_TEXT,
        reply_markup=admin_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adm:portfolio")
async def admin_portfolio_callback(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    await state.clear()
    summary = await PortfolioService(session).get_summary()
    await session.commit()
    await callback.answer()
    await _edit_callback_message(
        callback,
        _portfolio_summary_text(summary),
        reply_markup=portfolio_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adm:user_search_info")
async def admin_user_search_info(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.answer()
    await _edit_callback_message(
        callback,
        "🔎 <b>Foydalanuvchi qidirish</b>\n\n"
        "Buyruq: <code>/user TELEGRAM_ID</code> yoki <code>/user @username</code>\n\n"
        "Natijada asosiy ma'lumotlar, obuna, referallar, to'lovlar va kurs natijalari tartibli ko'rinadi.",
        reply_markup=admin_back_keyboard(),
        parse_mode="HTML",
    )


@router.message(Command("user"))
async def admin_user_search_command(message: Message, session):
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "Foydalanish: <code>/user TELEGRAM_ID</code> yoki <code>/user @username</code>",
            parse_mode="HTML",
        )
        return

    repo = UserRepository(session)
    users = await repo.search_by_identifier(parts[1], limit=5)
    if not users:
        await message.answer("❌ User topilmadi.")
        return

    if len(users) > 1:
        lines = ["Bir nechta foydalanuvchi topildi. Aniq ID bilan qayta qidiring:", ""]
        for item in users:
            username = f"@{item.username}" if item.username else "—"
            lines.append(f"<code>{item.telegram_id}</code> · {escape(item.full_name or '—')} · {escape(username)}")
        await message.answer("\n".join(lines), parse_mode="HTML")
        return

    await message.answer(await _admin_user_info_text(session, users[0]), parse_mode="HTML")


@router.callback_query(F.data == "adm:prices")
async def admin_prices_callback(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.answer()
    await _edit_callback_message(
        callback,
        await _prices_text(session),
        reply_markup=prices_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("adm:price_set:"))
async def admin_price_set_callback(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    parts = callback.data.split(":")
    method = parts[2]
    plan = parts[3]
    if method not in PAYMENT_METHODS or plan not in PLANS:
        await callback.answer("Noto'g'ri tarif", show_alert=True)
        return
    await state.update_data(price_method=method, price_plan=plan)
    await state.set_state(AdminPriceStates.waiting_amount)
    await callback.answer()
    currency_label = "TJS" if method == "visa" else "¥"
    example_amount = 89 if method == "visa" and plan == "1_month" else 29
    if method in {"alipay", "wechat"} and plan == "1_month":
        example_amount = 66
    await _edit_admin_flow_callback(
        callback,
        state,
        f"💳 <b>Narx o'zgartirish</b>\n\n"
        f"Usul: <b>{_method_label(method)}</b>\n"
        f"Tarif: <b>{_plan_label_admin(plan)}</b>\n\n"
        f"Yangi narxni <b>{currency_label}</b> bo'yicha raqam bilan yuboring. "
        f"Masalan: <code>{example_amount}</code>",
        reply_markup=admin_back_keyboard(),
    )


@router.message(StateFilter(AdminPriceStates.waiting_amount))
async def admin_price_amount_handler(message: Message, state: FSMContext, session):
    if not _is_admin(message.from_user.id):
        return
    try:
        amount = int((message.text or "").strip())
    except ValueError:
        await delete_message_safely(message)
        await _edit_admin_flow_message(
            message,
            state,
            "❌ Narx raqam bo'lishi kerak. Masalan: <code>99</code>",
        )
        return
    if amount <= 0 or amount > 1_000_000:
        await delete_message_safely(message)
        await _edit_admin_flow_message(message, state, "❌ Narx 1 dan 1 000 000 gacha bo'lsin.")
        return

    data = await state.get_data()
    method = data.get("price_method")
    plan = data.get("price_plan")
    if PaymentQrCodeService.is_qr_method(method) and not PaymentQrCodeService.is_default_subscription_amount(
        payment_method=method,
        plan_type=plan,
        amount=amount,
        currency="¥",
    ):
        items = _price_qr_items(method, plan, amount)
        await state.update_data(
            price_amount=amount,
            price_qr_items=items,
            price_qr_index=0,
        )
        await state.set_state(AdminPriceStates.waiting_qr_code)
        await delete_message_safely(message)
        await _edit_admin_flow_message(
            message,
            state,
            _qr_item_prompt(items[0], 0, len(items)),
            reply_markup=admin_back_keyboard(),
        )
        return

    price = await SubscriptionPriceService(session).set_price(
        payment_method=method,
        plan_type=plan,
        amount=amount,
        updated_by_telegram_id=message.from_user.id,
    )
    if not price:
        await delete_message_safely(message)
        await _edit_admin_flow_message(message, state, "❌ Narx saqlanmadi. Tarif noto'g'ri.")
        return
    await session.commit()
    await delete_message_safely(message)
    await _edit_admin_flow_message(
        message,
        state,
        f"✅ Narx yangilandi: <b>{_method_label(price.payment_method)} · "
        f"{_plan_label_admin(price.plan_type)} = "
        f"{format_subscription_price(price.amount, price.currency)}</b>",
        reply_markup=prices_keyboard(),
    )
    await state.clear()


@router.message(StateFilter(AdminPriceStates.waiting_qr_code), F.photo)
async def admin_price_qr_photo_handler(message: Message, state: FSMContext, session):
    if not _is_admin(message.from_user.id):
        return

    data = await state.get_data()
    items = data.get("price_qr_items") or []
    index = int(data.get("price_qr_index") or 0)
    if not items or index >= len(items):
        await delete_message_safely(message)
        await _edit_admin_flow_message(message, state, "❌ QR navbati topilmadi.", reply_markup=prices_keyboard())
        await state.clear()
        return

    items[index]["file_id"] = message.photo[-1].file_id
    index += 1
    await delete_message_safely(message)

    if index < len(items):
        await state.update_data(price_qr_items=items, price_qr_index=index)
        await _edit_price_qr_prompt(message, state)
        return

    method = data.get("price_method")
    plan = data.get("price_plan")
    amount = int(data.get("price_amount") or 0)
    price = await SubscriptionPriceService(session).set_price(
        payment_method=method,
        plan_type=plan,
        amount=amount,
        updated_by_telegram_id=message.from_user.id,
    )
    if not price:
        await _edit_admin_flow_message(message, state, "❌ Narx saqlanmadi. Tarif noto'g'ri.")
        await state.clear()
        return

    await PaymentQrCodeService(session).save_qr_codes(
        items,
        created_by_telegram_id=message.from_user.id,
    )
    await session.commit()
    await _edit_admin_flow_message(
        message,
        state,
        f"✅ Narx va QR kodlar yangilandi: <b>{_method_label(price.payment_method)} · "
        f"{_plan_label_admin(price.plan_type)} = "
        f"{format_subscription_price(price.amount, price.currency)}</b>",
        reply_markup=prices_keyboard(),
    )
    await state.clear()


@router.message(StateFilter(AdminPriceStates.waiting_qr_code))
async def admin_price_qr_only_handler(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await delete_message_safely(message)
    await _edit_price_qr_prompt(message, state)


@router.callback_query(F.data.startswith("adm:visa_rate_auto:"))
async def admin_visa_rate_auto_callback(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    enabled = callback.data.split(":")[-1] == "on"
    await SubscriptionCurrencyService(session).set_auto_rate_enabled(enabled)
    await session.commit()
    await state.clear()
    await callback.answer("Avto kurs yoqildi" if enabled else "Avto kurs o'chirildi", show_alert=True)
    await _edit_callback_message(
        callback,
        await _prices_text(session),
        reply_markup=prices_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("adm:visa_rate_set:"))
async def admin_visa_rate_set_callback(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    currency_code = callback.data.split(":")[-1]
    if currency_code not in SUBSCRIPTION_USD_RATE_KEYS:
        await callback.answer("Noto'g'ri valyuta", show_alert=True)
        return
    await state.update_data(visa_rate_currency=currency_code)
    await state.set_state(AdminPriceStates.waiting_rate)
    label = SubscriptionCurrencyService.rate_label(currency_code)
    current_rate = await SubscriptionCurrencyService(session).get_rate(currency_code)
    formatted_rate = SubscriptionCurrencyService.format_rate(currency_code, current_rate)
    await callback.answer()
    await _edit_admin_flow_callback(
        callback,
        state,
        f"💱 <b>Obuna fallback kursini o'zgartirish</b>\n\n"
        f"Valyuta: <b>{label}</b>\n\n"
        f"Joriy kurs: <code>1 USD = {formatted_rate} {label}</code>\n\n"
        f"1 USD uchun yangi {label} kursini yuboring.\n"
        f"Masalan: <code>{formatted_rate}</code>",
        reply_markup=admin_back_keyboard(),
    )


@router.message(StateFilter(AdminPriceStates.waiting_rate))
async def admin_visa_rate_amount_handler(message: Message, state: FSMContext, session):
    if not _is_admin(message.from_user.id):
        return
    try:
        value = Decimal((message.text or "").strip().replace(",", "."))
    except InvalidOperation:
        await delete_message_safely(message)
        await _edit_admin_flow_message(
            message,
            state,
            "❌ Kurs raqam bo'lishi kerak. Masalan: <code>9.2464</code>",
        )
        return
    if not value.is_finite() or value <= 0 or value > Decimal("1000000000"):
        await delete_message_safely(message)
        await _edit_admin_flow_message(message, state, "❌ Kurs 0 dan katta bo'lishi kerak.")
        return

    data = await state.get_data()
    currency_code = data.get("visa_rate_currency")
    service = SubscriptionCurrencyService(session)
    if not await service.set_rate(currency_code, value):
        await delete_message_safely(message)
        await _edit_admin_flow_message(message, state, "❌ Kurs saqlanmadi. Valyuta noto'g'ri.")
        return
    await session.commit()

    label = service.rate_label(currency_code)
    formatted = service.format_rate(currency_code, value)
    await delete_message_safely(message)
    await _edit_admin_flow_message(
        message,
        state,
        f"✅ Obuna fallback kursi yangilandi: <b>1 USD = {formatted} {label}</b>",
        reply_markup=prices_keyboard(),
    )
    await state.clear()


@router.callback_query(F.data == "adm:payment_details")
async def admin_payment_details_callback(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    current = await BotSettingRepository(session).get(PAYMENT_DETAILS_KEY)
    current = (current or settings.PAYMENT_DETAILS or "").strip()
    await state.set_state(AdminPriceStates.waiting_payment_details)
    await callback.answer()
    await _edit_admin_flow_callback(
        callback,
        state,
        "💳 <b>Bank karta rekviziti</b>\n\n"
        "Bu matn mini appda VISA/karta to'lovida foydalanuvchiga ko'rsatiladi.\n\n"
        f"Joriy:\n<code>{escape(current or '—')}</code>\n\n"
        "Yangi rekvizit matnini yuboring (ism, karta raqami va boshqalar).",
        reply_markup=admin_back_keyboard(),
    )


@router.message(StateFilter(AdminPriceStates.waiting_payment_details))
async def admin_payment_details_handler(message: Message, state: FSMContext, session):
    if not _is_admin(message.from_user.id):
        return
    text_value = (message.text or "").strip()
    if not text_value:
        await delete_message_safely(message)
        await _edit_admin_flow_message(message, state, "❌ Rekvizit matni bo'sh bo'lmasin.")
        return
    if len(text_value) > 1500:
        await delete_message_safely(message)
        await _edit_admin_flow_message(message, state, "❌ Matn juda uzun (1500 belgidan kam bo'lsin).")
        return
    await BotSettingRepository(session).set(PAYMENT_DETAILS_KEY, text_value)
    await session.commit()
    await delete_message_safely(message)
    await _edit_admin_flow_message(
        message,
        state,
        "✅ Karta rekviziti yangilandi. Mini appda darhol ko'rinadi.",
        reply_markup=prices_keyboard(),
    )
    await state.clear()


@router.callback_query(F.data.in_({"adm:help_settings", "adm:support_contact"}))
async def admin_help_settings_callback(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.answer()
    await _edit_admin_flow_callback(
        callback,
        state,
        await help_settings_text(session),
        reply_markup=help_settings_keyboard(),
    )


@router.callback_query(F.data.startswith("adm:help_link:"))
async def admin_help_link_prompt(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    parts = (callback.data or "").split(":")
    target = parts[2] if len(parts) >= 3 else ""
    lang = parts[3] if len(parts) >= 4 else None

    if target == "admin_contact":
        current = await get_admin_contact(session)
        title = "Admin aloqa linki"
        current_display = admin_contact_url(current) or current
    else:
        field = HELP_VIDEO_FIELD_BY_KEY.get(target)
        if not field or lang not in HELP_LANGS:
            await callback.answer("Noto'g'ri sozlama.", show_alert=True)
            return
        current = await BotSettingRepository(session).get(field.setting_key(lang))
        title = f"{field.label} · {_help_lang_label(lang)}"
        current_display = normalize_help_url(current)

    await state.update_data(admin_help_target=target, admin_help_lang=lang)
    await state.set_state(AdminHelpStates.waiting_link)
    await callback.answer()
    await _edit_admin_flow_callback(
        callback,
        state,
        "🆘 <b>Yordam linki tahriri</b>\n\n"
        f"Maydon: <b>{escape(title)}</b>\n\n"
        f"Joriy:\n<code>{escape(current_display or '—')}</code>\n\n"
        "Yangi link yuboring.\n"
        "Qabul qilinadi: <code>https://...</code>, <code>http://...</code>, "
        "<code>tg://...</code>, <code>t.me/...</code>"
        "\n\nBo'sh qilish uchun <code>-</code> yuboring.",
        reply_markup=help_settings_back_keyboard(),
    )


@router.message(StateFilter(AdminHelpStates.waiting_link))
async def admin_help_link_handler(message: Message, state: FSMContext, session):
    if not _is_admin(message.from_user.id):
        return

    data = await state.get_data()
    target = data.get("admin_help_target")
    lang = data.get("admin_help_lang")
    raw_value = (message.text or "").strip()
    should_clear = raw_value.lower() in {"-", "—", "clear", "tozalash", "очистить"}

    if target == "admin_contact":
        value = "" if should_clear else normalize_admin_contact(raw_value)
        if value and not admin_contact_url(value):
            await delete_message_safely(message)
            await _edit_admin_flow_message(
                message,
                state,
                "❌ Kontakt noto'g'ri. <code>@username</code>, <code>t.me/username</code> "
                "yoki <code>https://t.me/username</code> formatida yuboring.",
                reply_markup=help_settings_back_keyboard(),
            )
            return
        setting_key = ADMIN_CONTACT_KEY
    else:
        field = HELP_VIDEO_FIELD_BY_KEY.get(str(target or ""))
        if not field or lang not in HELP_LANGS:
            await delete_message_safely(message)
            await _edit_admin_flow_message(
                message,
                state,
                "❌ Sozlama topilmadi. Yordam sozlamalaridan qayta tanlang.",
                reply_markup=help_settings_keyboard(),
            )
            await state.clear()
            return
        value = "" if should_clear else normalize_help_url(raw_value)
        if raw_value and not should_clear and not value:
            await delete_message_safely(message)
            await _edit_admin_flow_message(
                message,
                state,
                "❌ Link noto'g'ri. <code>https://...</code>, <code>http://...</code>, "
                "<code>tg://...</code> yoki <code>t.me/...</code> yuboring.",
                reply_markup=help_settings_back_keyboard(),
            )
            return
        setting_key = field.setting_key(lang)

    if len(value) > 500:
        await delete_message_safely(message)
        await _edit_admin_flow_message(
            message,
            state,
            "❌ Link 500 belgidan oshmasin.",
            reply_markup=help_settings_back_keyboard(),
        )
        return

    await BotSettingRepository(session).set(setting_key, value)
    await session.commit()
    await delete_message_safely(message)
    await _edit_admin_flow_message(
        message,
        state,
        f"✅ Saqlandi.\n\n{await help_settings_text(session)}",
        reply_markup=help_settings_keyboard(),
    )
    await state.clear()


@router.callback_query(F.data == "adm:channels")
async def admin_channels_callback(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.answer()
    text, keyboard = await _channel_panel_text(session)
    await _edit_callback_message(callback, text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("adm:channels_mode:"))
async def admin_channels_mode_callback(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    enabled = callback.data.split(":")[2] == "on"
    service = RequiredChannelService(session)
    await service.set_enabled(enabled)
    await session.commit()
    await callback.answer("Saqlandi", show_alert=True)
    text, keyboard = await _channel_panel_text(session)
    await _edit_callback_message(callback, text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "adm:channel_add")
async def admin_channel_add_callback(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.set_state(AdminRequiredChannelStates.waiting_channel)
    await callback.answer()
    await _edit_admin_flow_callback(
        callback,
        state,
        "➕ <b>Kanal qo'shish</b>\n\n"
        "Eng oson yo'l: kanaldan bitta postni shu yerga forward qiling.\n\n"
        "Yoki public kanal uchun shunchaki yuboring:\n"
        "<code>@channel</code>\n"
        "<code>https://t.me/channel</code>\n\n"
        "Private kanal bo'lsa, botni kanalga admin qilib qo'ying va post forward qiling.",
        reply_markup=admin_back_keyboard(),
    )


@router.message(StateFilter(AdminRequiredChannelStates.waiting_channel))
async def admin_channel_add_message(message: Message, state: FSMContext, session):
    if not _is_admin(message.from_user.id):
        return
    parsed = await _extract_channel_input(message)
    if not parsed:
        await delete_message_safely(message)
        await _edit_admin_flow_message(
            message,
            state,
            "❌ Kanalni aniqlay olmadim.\n\n"
            "Kanaldan post forward qiling yoki <code>@channel</code> / <code>t.me/channel</code> yuboring.",
        )
        return
    chat_id, invite_link, title = parsed
    title = await _resolve_channel_title(message, chat_id, title)
    invite_link = await _fill_channel_invite_link(message, chat_id, invite_link)
    await RequiredChannelService(session).add_channel(
        chat_id=chat_id,
        invite_link=invite_link,
        title=title,
        created_by_telegram_id=message.from_user.id,
    )
    await session.commit()
    text, keyboard = await _channel_panel_text(session)
    await delete_message_safely(message)
    await _edit_admin_flow_message(message, state, f"✅ Kanal saqlandi.\n\n{text}", reply_markup=keyboard)
    await state.clear()


@router.callback_query(F.data.startswith("adm:channel_toggle:"))
async def admin_channel_toggle_callback(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    channel_id = int(callback.data.split(":")[2])
    service = RequiredChannelService(session)
    channels = await service.list_channels()
    channel = next((item for item in channels if item.id == channel_id), None)
    if not channel:
        await callback.answer("Kanal topilmadi", show_alert=True)
        return
    await service.set_channel_active(channel_id, not channel.is_active)
    await session.commit()
    await callback.answer("Saqlandi", show_alert=True)
    text, keyboard = await _channel_panel_text(session)
    await _edit_callback_message(callback, text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("adm:channel_delete:"))
async def admin_channel_delete_callback(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    channel_id = int(callback.data.split(":")[2])
    deleted = await RequiredChannelService(session).delete_channel(channel_id)
    if not deleted:
        await callback.answer("Kanal topilmadi", show_alert=True)
        return
    await session.commit()
    await callback.answer("Kanal o'chirildi", show_alert=True)
    text, keyboard = await _channel_panel_text(session)
    await _edit_callback_message(callback, text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "adm:portfolio_history")
async def admin_portfolio_history_callback(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    rows = await PortfolioService(session).list_history(limit=20)
    await session.commit()
    await callback.answer()
    await _edit_callback_message(
        callback,
        _portfolio_history_text(rows),
        reply_markup=portfolio_history_keyboard(rows),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("adm:portfolio_edit:"))
async def admin_portfolio_edit_callback(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    try:
        transaction_id = int(callback.data.split(":")[2])
    except (AttributeError, IndexError, ValueError):
        await callback.answer("Transaction noto'g'ri", show_alert=True)
        return

    transaction = await PortfolioService(session).get_manual_transaction(transaction_id)
    if not transaction:
        await callback.answer("Faqat qo'lda qo'shilgan transaction edit qilinadi", show_alert=True)
        return

    await state.clear()
    await state.update_data(portfolio_edit_transaction_id=transaction.id)
    await callback.answer()
    edited = await _edit_callback_message(
        callback,
        f"✏️ <b>Portfel yozuvini edit qilish</b>\n\n"
        f"Transaction: <code>#{transaction.id}</code>\n"
        f"Joriy tur: <b>{_portfolio_type_label(transaction.transaction_type)}</b>\n"
        f"Joriy summa: <b>{_usd(transaction.amount_usd)}</b>\n"
        f"Sabab: <b>{escape(transaction.note or '—')}</b>\n\n"
        "To'g'ri turini tanlang:",
        reply_markup=portfolio_edit_type_keyboard(transaction.id),
        parse_mode="HTML",
    )
    if edited:
        await state.update_data(
            portfolio_prompt_chat_id=edited.chat.id,
            portfolio_prompt_message_id=edited.message_id,
        )


@router.callback_query(F.data.startswith("adm:portfolio_edit_type:"))
async def admin_portfolio_edit_type_callback(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    try:
        _, _, transaction_id_text, transaction_type = callback.data.split(":")
        transaction_id = int(transaction_id_text)
    except (AttributeError, ValueError):
        await callback.answer("Transaction noto'g'ri", show_alert=True)
        return
    if transaction_type not in {"profit", "expense"}:
        await callback.answer("Transaction turi noto'g'ri", show_alert=True)
        return

    transaction = await PortfolioService(session).get_manual_transaction(transaction_id)
    if not transaction:
        await callback.answer("Transaction topilmadi", show_alert=True)
        return

    await state.update_data(
        portfolio_edit_transaction_id=transaction.id,
        portfolio_transaction_type=transaction_type,
    )
    await state.set_state(AdminPortfolioStates.waiting_amount)
    await callback.answer()
    icon = _portfolio_type_icon(transaction_type)
    label = _portfolio_type_label(transaction_type)
    edited = await _edit_callback_message(
        callback,
        f"{icon} <b>#{transaction.id} {label} summasini edit qilish</b>\n\n"
        "Yangi summa va currency yuboring:\n"
        "<code>50 usd</code>\n"
        "<code>120 somoni</code>\n"
        "<code>200 ¥</code>",
        reply_markup=portfolio_cancel_keyboard(),
        parse_mode="HTML",
    )
    if edited:
        await state.update_data(
            portfolio_prompt_chat_id=edited.chat.id,
            portfolio_prompt_message_id=edited.message_id,
        )


@router.callback_query(F.data == "adm:portfolio_expense_info")
async def admin_portfolio_expense_info(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.answer()
    await _start_portfolio_flow(
        state=state,
        callback=callback,
        transaction_type="expense",
    )


@router.callback_query(F.data == "adm:portfolio_profit_info")
async def admin_portfolio_profit_info(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.answer()
    await _start_portfolio_flow(
        state=state,
        callback=callback,
        transaction_type="profit",
    )


@router.callback_query(F.data == "adm:portfolio_cancel")
async def admin_portfolio_cancel(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    await state.clear()
    summary = await PortfolioService(session).get_summary()
    await session.commit()
    await callback.answer("Bekor qilindi")
    await _edit_callback_message(
        callback,
        _portfolio_summary_text(summary),
        reply_markup=portfolio_keyboard(),
        parse_mode="HTML",
    )


@router.message(Command("portfolio_expense"))
async def admin_portfolio_expense_handler(message: Message, state: FSMContext, session):
    if not _is_admin(message.from_user.id):
        return

    await _start_portfolio_command_flow(
        message=message,
        state=state,
        transaction_type="expense",
    )


@router.message(Command("portfolio_profit"))
async def admin_portfolio_profit_handler(message: Message, state: FSMContext, session):
    if not _is_admin(message.from_user.id):
        return

    await _start_portfolio_command_flow(
        message=message,
        state=state,
        transaction_type="profit",
    )


@router.message(StateFilter(AdminPortfolioStates.waiting_amount))
async def admin_portfolio_amount_handler(message: Message, state: FSMContext, session):
    if not _is_admin(message.from_user.id):
        return

    data = await state.get_data()
    transaction_type = data.get("portfolio_transaction_type")
    if transaction_type not in {"profit", "expense"}:
        await delete_message_safely(message)
        await _send_or_edit_portfolio_prompt(
            state=state,
            message=message,
            text="❌ Portfel flow buzildi. Qaytadan boshlang.",
        )
        await state.clear()
        return

    parsed = _parse_amount_currency(message.text or "")
    if not parsed:
        await delete_message_safely(message)
        await _send_or_edit_portfolio_prompt(
            state=state,
            message=message,
            text=(
                "❌ Summa formati noto'g'ri.\n\n"
                "Summa va currency yuboring. Masalan:\n"
                "<code>50 usd</code>"
            ),
        )
        return

    amount, currency = parsed
    await delete_message_safely(message)
    await _ask_portfolio_reason(
        state=state,
        message=message,
        transaction_type=transaction_type,
        amount=amount,
        currency=currency,
    )


@router.message(StateFilter(AdminPortfolioStates.waiting_reason))
async def admin_portfolio_reason_handler(message: Message, state: FSMContext, session):
    if not _is_admin(message.from_user.id):
        return

    note = (message.text or "").strip()
    await delete_message_safely(message)
    if len(note) < 2:
        await _send_or_edit_portfolio_prompt(
            state=state,
            message=message,
            text=(
                "❌ Sabab juda qisqa.\n\n"
                "Sababini aniqroq yozing. Masalan:\n"
                "<code>OpenAI to'lov</code>"
            ),
        )
        return

    data = await state.get_data()
    transaction_type = data.get("portfolio_transaction_type")
    amount = data.get("portfolio_amount")
    currency = data.get("portfolio_currency")
    if transaction_type not in {"profit", "expense"} or amount is None or not currency:
        await _send_or_edit_portfolio_prompt(
            state=state,
            message=message,
            text="❌ Portfel flow buzildi. Qaytadan boshlang.",
        )
        await state.clear()
        return

    portfolio_service = PortfolioService(session)
    edit_transaction_id = data.get("portfolio_edit_transaction_id")
    if edit_transaction_id:
        transaction = await portfolio_service.update_manual_transaction(
            transaction_id=int(edit_transaction_id),
            transaction_type=transaction_type,
            amount=float(amount),
            currency=str(currency),
            note=note,
        )
    else:
        transaction = await portfolio_service.add_manual_transaction(
            transaction_type=transaction_type,
            admin_telegram_id=message.from_user.id,
            amount=float(amount),
            currency=str(currency),
            note=note,
        )
    if not transaction:
        await _send_or_edit_portfolio_prompt(
            state=state,
            message=message,
            text="❌ Transaction saqlanmadi. Qaytadan boshlang.",
        )
        await state.clear()
        return

    await session.commit()
    summary = await PortfolioService(session).get_summary()
    await session.commit()
    await state.clear()
    label = "Foyda" if transaction_type == "profit" else "Rasxod"
    action = "yangilandi" if edit_transaction_id else "qo'shildi"
    edited = await _edit_message_by_id(
        message,
        chat_id=data.get("portfolio_prompt_chat_id"),
        message_id=data.get("portfolio_prompt_message_id"),
        text=(
            f"✅ {label} {action}: <b>{_usd(transaction.amount_usd)}</b>\n"
            f"📝 Sabab: {escape(note)}\n\n"
            f"{_portfolio_summary_text(summary)}"
        ),
        reply_markup=portfolio_keyboard(),
    )
    if not edited:
        await message.answer(
            f"✅ {label} {action}: <b>{_usd(transaction.amount_usd)}</b>\n"
            f"📝 Sabab: {escape(note)}\n\n"
            f"{_portfolio_summary_text(summary)}",
            reply_markup=portfolio_keyboard(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "adm:stats")
async def admin_stats_callback(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    now = datetime.now(timezone.utc)
    today_start = now.astimezone(ADMIN_STATS_TZ).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    last_24h = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # --- Foydalanuvchilar ---
    total = (await session.execute(select(func.count()).select_from(User))).scalar() or 0

    status_counts = {
        r.status: r.cnt
        for r in (await session.execute(
            select(User.status, func.count().label("cnt")).group_by(User.status)
        )).fetchall()
    }
    lang_counts = {
        r.language: r.cnt
        for r in (await session.execute(
            select(User.language, func.count().label("cnt")).group_by(User.language)
        )).fetchall()
    }
    level_counts = {
        r.level: r.cnt
        for r in (await session.execute(
            select(User.level, func.count().label("cnt")).group_by(User.level)
        )).fetchall()
    }
    # --- Faollik ---
    new_today = (await session.execute(
        select(func.count()).select_from(User).where(User.created_at >= today_start)
    )).scalar() or 0
    new_week = (await session.execute(
        select(func.count()).select_from(User).where(User.created_at >= week_ago)
    )).scalar() or 0
    new_month = (await session.execute(
        select(func.count()).select_from(User).where(User.created_at >= month_ago)
    )).scalar() or 0
    active_today = (await session.execute(
        select(func.count()).select_from(User).where(User.last_active_at >= today_start)
    )).scalar() or 0
    active_24h = (await session.execute(
        select(func.count()).select_from(User).where(User.last_active_at >= last_24h)
    )).scalar() or 0
    active_week = (await session.execute(
        select(func.count()).select_from(User).where(User.last_active_at >= week_ago)
    )).scalar() or 0

    # --- To'lovlar ---
    pay_rows = (await session.execute(
        select(
            Payment.payment_status,
            func.count().label("cnt"),
            func.sum(Payment.amount).label("total_sum"),
        ).group_by(Payment.payment_status)
    )).fetchall()
    pay_by_status = {r.payment_status: (r.cnt, int(r.total_sum or 0)) for r in pay_rows}

    pay_plan_rows = (await session.execute(
        select(Payment.plan_type, func.count().label("cnt"))
        .where(Payment.payment_status == "approved")
        .group_by(Payment.plan_type)
    )).fetchall()
    pay_by_plan = {r.plan_type: r.cnt for r in pay_plan_rows}

    # --- Kurs Mini App ---
    miniapp_course = await miniapp_course_stats(session)

    # --- Referallar ---
    ref_total = (await session.execute(
        select(func.count()).select_from(Referral)
    )).scalar() or 0
    ref_activated = (await session.execute(
        select(func.count()).select_from(Referral).where(Referral.status == "active")
    )).scalar() or 0
    ref_bonus = (await session.execute(
        select(func.count()).select_from(Referral).where(Referral.bonus_granted == True)  # noqa: E712
    )).scalar() or 0
    discount_eligible = (await session.execute(
        select(func.count()).select_from(User).where(User.discount_eligible == True)  # noqa: E712
    )).scalar() or 0
    discount_used_cnt = (await session.execute(
        select(func.count()).select_from(User).where(User.discount_used == True)  # noqa: E712
    )).scalar() or 0

    # --- Hisob ---
    free_cnt    = status_counts.get("free", 0)
    trial_cnt   = status_counts.get("trial", 0)
    active_cnt  = status_counts.get("active", 0)
    expired_cnt = status_counts.get("expired", 0)
    blocked_cnt = status_counts.get("blocked", 0)

    pending_cnt,  _            = pay_by_status.get("pending",  (0, 0))
    approved_cnt, approved_sum = pay_by_status.get("approved", (0, 0))
    rejected_cnt, _            = pay_by_status.get("rejected", (0, 0))
    paid_user_cnt = (await session.execute(
        select(func.count()).select_from(User).where(
            User.payment_status == "approved",
            User.status == "active",
            User.end_date.is_not(None),
            User.end_date > now,
        )
    )).scalar() or 0
    historical_approved_users = (await session.execute(
        select(func.count()).select_from(User).where(User.payment_status == "approved")
    )).scalar() or 0
    course_miniapp_text = await CourseMiniAppAdminAnalyticsService(session).admin_text(week_ago=week_ago)

    conversion  = _pct(paid_user_cnt, total)
    qa_users    = (await session.execute(
        select(func.count()).select_from(User).where(User.questions_used > 0)
    )).scalar() or 0
    engagement  = _pct(qa_users, total)
    avg_lessons = (
        round(miniapp_course.completed_sections / miniapp_course.completed_users, 1)
        if miniapp_course.completed_users > 0
        else 0
    )
    level_order = ["beginner", "hsk1", "hsk2", "hsk3", "hsk4"]
    level_str   = "  " + "   ".join(
        f"{l.upper()}: {level_counts.get(l, 0)}" for l in level_order
    )
    lang_str = "  " + " | ".join(f"{k}: {v}" for k, v in sorted(lang_counts.items()))
    now_str  = now.astimezone(ADMIN_STATS_TZ).strftime("%d.%m.%Y %H:%M Asia/Shanghai")

    text = (
        f"📊 <b>Statistika</b>  <i>{now_str}</i>\n"
        f"{'─' * 32}\n\n"

        f"<b>👥 FOYDALANUVCHILAR  [{total}]</b>\n"
        f"  Bepul: <b>{free_cnt}</b>   Sinov: <b>{trial_cnt}</b>\n"
        f"  Faol status: <b>{active_cnt}</b>   To'lovli: <b>{paid_user_cnt}</b>\n"
        f"  Tarixiy tasdiqlangan: <b>{historical_approved_users}</b>\n"
        f"  Tugagan: <b>{expired_cnt}</b>   Bloklangan: <b>{blocked_cnt}</b>\n\n"

        f"<b>📅 FAOLLIK</b>\n"
        f"  Yangi:  bugun <b>+{new_today}</b>  |  hafta <b>+{new_week}</b>  |  oy <b>+{new_month}</b>\n"
        f"  Aktiv:  bugun <b>{active_today}</b>  |  24 soat <b>{active_24h}</b>  |  hafta <b>{active_week}</b>\n\n"

        f"<b>📊 DARAJALAR</b>\n"
        f"{level_str}\n\n"

        f"<b>🌐 TIL</b>\n"
        f"{lang_str}\n\n"

        f"<b>💳 TO'LOVLAR</b>\n"
        f"  Kutilmoqda: <b>{pending_cnt}</b>   Tasdiqlangan: <b>{approved_cnt}</b>   Rad: <b>{rejected_cnt}</b>\n"
        f"  10 kun: <b>{pay_by_plan.get('10_days', 0)}</b>   1 oy: <b>{pay_by_plan.get('1_month', 0)}</b>\n"
        f"  Jami daromad: <b>{approved_sum:,}</b> so'm\n\n"

        f"<b>📚 KURS</b>\n"
        f"  Mini App ochgan: <b>{miniapp_course.opened_users}</b>   Dars boshlaganlar: <b>{miniapp_course.lesson_users}</b>\n"
        f"  Dars tugatganlar: <b>{miniapp_course.completed_users}</b>   Tugatilgan qismlar: <b>{miniapp_course.completed_sections}</b>\n"
        f"  Tugatilgan kitob darslari: <b>{miniapp_course.completed_book_lessons}</b>   O'rtacha qism: <b>{avg_lessons}</b>\n\n"

        f"{course_miniapp_text}\n\n"

        f"<b>🎁 REFERALLAR</b>\n"
        f"  Jami: <b>{ref_total}</b>   Faollashgan: <b>{ref_activated}</b>   Bonus: <b>{ref_bonus}</b>\n"
        f"  Chegirma eligible: <b>{discount_eligible}</b>   Ishlatilgan: <b>{discount_used_cnt}</b>\n\n"

        f"<b>📈 KONVERSIYA</b>\n"
        f"  User → Paid: <b>{conversion}%</b>\n"
        f"  Savol berganlar: <b>{qa_users}</b> (<b>{engagement}%</b>)"
    )

    await callback.answer()
    await _edit_callback_message(
        callback,
        text,
        reply_markup=admin_stats_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adm:feedback_stats")
async def admin_feedback_stats_callback(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    completed = (await session.execute(
        select(func.count()).select_from(BotFeedback).where(BotFeedback.status == "completed")
    )).scalar() or 0
    completed_week = (await session.execute(
        select(func.count()).select_from(BotFeedback).where(
            BotFeedback.status == "completed",
            BotFeedback.completed_at >= week_ago,
        )
    )).scalar() or 0
    completed_month = (await session.execute(
        select(func.count()).select_from(BotFeedback).where(
            BotFeedback.status == "completed",
            BotFeedback.completed_at >= month_ago,
        )
    )).scalar() or 0
    price_high = (await session.execute(
        select(func.count()).select_from(BotFeedback).where(
            BotFeedback.status == "completed",
            BotFeedback.disliked_code == "price",
        )
    )).scalar() or 0
    limit_unhappy = (await session.execute(
        select(func.count()).select_from(BotFeedback).where(
            BotFeedback.status == "completed",
            BotFeedback.disliked_code == "limits",
        )
    )).scalar() or 0
    unclear = (await session.execute(
        select(func.count()).select_from(BotFeedback).where(
            BotFeedback.status == "completed",
            BotFeedback.disliked_code == "unclear",
        )
    )).scalar() or 0
    pace = (await session.execute(
        select(func.count()).select_from(BotFeedback).where(
            BotFeedback.status == "completed",
            BotFeedback.disliked_code == "pace",
        )
    )).scalar() or 0
    other = (await session.execute(
        select(func.count()).select_from(BotFeedback).where(
            BotFeedback.status == "completed",
            BotFeedback.disliked_code == "other",
        )
    )).scalar() or 0
    disliked_total = (await session.execute(
        select(func.count()).select_from(BotFeedback).where(
            BotFeedback.status == "completed",
            BotFeedback.disliked_code.is_not(None),
        )
    )).scalar() or 0
    text_comments = (await session.execute(
        select(func.count()).select_from(BotFeedback).where(
            BotFeedback.status == "completed",
            BotFeedback.disliked_text.is_not(None),
        )
    )).scalar() or 0
    screenshots = (await session.execute(
        select(func.count()).select_from(BotFeedback).where(
            BotFeedback.status == "completed",
            BotFeedback.disliked_attachment_file_id.is_not(None),
        )
    )).scalar() or 0
    discount_offers_sent = (await session.execute(
        select(func.count()).select_from(BotFeedback).where(BotFeedback.price_offer_sent_at.is_not(None))
    )).scalar() or 0
    discount_offers_used = (await session.execute(
        select(func.count()).select_from(BotFeedback).where(BotFeedback.price_offer_used_at.is_not(None))
    )).scalar() or 0

    now_str = now.strftime("%d.%m.%Y %H:%M UTC")
    text = (
        f"📝 <b>Otziv statistikasi</b>  <i>{now_str}</i>\n"
        f"{'─' * 32}\n\n"
        f"Jami yakunlangan: <b>{completed}</b>\n"
        f"7 kun: <b>+{completed_week}</b>   30 kun: <b>+{completed_month}</b>\n\n"
        f"<b>Asosiy noroziliklar</b>\n"
        f"Obuna narxi baland: <b>{price_high}</b>\n"
        f"Limitdan norozi: <b>{limit_unhappy}</b>\n"
        f"Tushunarsiz javob: <b>{unclear}</b>\n"
        f"Tezlik/pace muammo: <b>{pace}</b>\n"
        f"Boshqa: <b>{other}</b>\n"
        f"Kamchilik yozgan jami: <b>{disliked_total}</b>\n\n"
        f"<b>Dalil/izoh</b>\n"
        f"Matnli izoh: <b>{text_comments}</b>\n"
        f"Screenshot: <b>{screenshots}</b>\n\n"
        f"<b>Chegirma offer</b>\n"
        f"Yuborilgan: <b>{discount_offers_sent}</b>\n"
        f"Ishlatilgan: <b>{discount_offers_used}</b>"
    )

    await callback.answer()
    await _edit_callback_message(
        callback,
        text,
        reply_markup=admin_back_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adm:deleteuser_info")
async def admin_deleteuser_info(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.set_state(AdminUserStates.waiting_delete_user_id)
    await callback.answer()
    await _edit_admin_flow_callback(
        callback,
        state,
        "🗑 <b>Foydalanuvchini o'chirish</b>\n\n"
        "Telegram ID yuboring. Masalan:\n"
        "<code>123456789</code>",
        reply_markup=admin_back_keyboard(),
    )


def _parse_delete_user_id(text: str | None) -> int | None:
    value = (text or "").strip()
    if not value:
        return None
    if value.startswith("/deleteuser"):
        parts = value.split(maxsplit=1)
        value = parts[1].strip() if len(parts) == 2 else ""
    if not value.isdigit():
        return None
    return int(value)


async def _delete_user_by_telegram_id(session, target_id: int) -> bool:
    user_repo = UserRepository(session)
    deleted = await user_repo.delete_by_telegram_id(target_id)
    await session.commit()
    return deleted


@router.message(StateFilter(AdminUserStates.waiting_delete_user_id))
async def admin_deleteuser_waiting_id_handler(message: Message, state: FSMContext, session):
    if not _is_admin(message.from_user.id):
        return

    target_id = _parse_delete_user_id(message.text)
    await delete_message_safely(message)
    if target_id is None:
        await _edit_admin_flow_message(
            message,
            state,
            "❌ Telegram ID faqat raqam bo'lishi kerak.\n\n"
            "Masalan: <code>123456789</code>",
            reply_markup=admin_back_keyboard(),
        )
        return

    try:
        deleted = await _delete_user_by_telegram_id(session, target_id)
    except Exception:
        await session.rollback()
        await _edit_admin_flow_message(
            message,
            state,
            "❌ User o'chirishda DB xato chiqdi. IDni tekshirib qayta yuboring.",
            reply_markup=admin_back_keyboard(),
        )
        return

    if not deleted:
        await _edit_admin_flow_message(
            message,
            state,
            f"❌ User <code>{target_id}</code> topilmadi.\n\n"
            "Boshqa Telegram ID yuboring.",
            reply_markup=admin_back_keyboard(),
        )
        return

    await _edit_admin_flow_message(
        message,
        state,
        f"✅ User <code>{target_id}</code> o'chirildi.",
        reply_markup=admin_back_keyboard(),
    )
    await state.clear()


@router.message(Command("deleteuser"))
async def admin_deleteuser_handler(message: Message, session):
    if not _is_admin(message.from_user.id):
        return

    target_id = _parse_delete_user_id(message.text)
    if target_id is None:
        await message.answer("Foydalanish: <code>/deleteuser TELEGRAM_ID</code>", parse_mode="HTML")
        return

    try:
        deleted = await _delete_user_by_telegram_id(session, target_id)
    except Exception:
        await session.rollback()
        await message.answer("❌ User o'chirishda DB xato chiqdi.")
        return
    if deleted:
        await message.answer(f"✅ User <code>{target_id}</code> o'chirildi.", parse_mode="HTML")
    else:
        await message.answer(f"❌ User <code>{target_id}</code> topilmadi.", parse_mode="HTML")


@router.callback_query(F.data == "adm:broadcast_info")
async def admin_broadcast_info(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.answer()
    await open_broadcast_panel_for_callback(callback, state)


@router.message(Command("broadcast_all"))
async def admin_broadcast_handler(message: Message, session):
    if not _is_admin(message.from_user.id):
        return

    text = message.text.strip()[len("/broadcast_all"):].strip()
    if not text:
        await message.answer("Foydalanish: <code>/broadcast_all Xabar matni</code>", parse_mode="HTML")
        return

    result = await session.execute(select(User.telegram_id))
    all_ids = [row.telegram_id for row in result.fetchall()]

    sent = 0
    failed = 0
    for uid in all_ids:
        try:
            await message.bot.send_message(chat_id=uid, text=text)
            sent += 1
        except Exception:
            failed += 1

    await message.answer(f"✅ Yuborildi: {sent}\n❌ Xato: {failed}")


@router.callback_query(F.data == "adm:giveaccess_info")
async def admin_giveaccess_info(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.answer()
    await _edit_callback_message(
        callback,
        "✅ <b>Obuna berish</b>\n\n"
        "Buyruq: <code>/giveaccess TELEGRAM_ID PLAN</code>\n\n"
        "Planlar: <code>10_days</code> | <code>1_month</code>\n\n"
        "Misol: <code>/giveaccess 123456789 1_month</code>",
        reply_markup=admin_back_keyboard(),
        parse_mode="HTML",
    )


@router.message(Command("audio_list"))
async def admin_audio_list_handler(message: Message, session):
    """Yuklangan audio fayllar ro'yxati: /audio_list hsk1 1"""
    if not _is_admin(message.from_user.id):
        return

    parts = message.text.strip().split()
    if len(parts) < 3:
        await message.answer(
            "Foydalanish: <code>/audio_list hsk1 1</code>\n"
            "(level va lesson_order)",
            parse_mode="HTML",
        )
        return

    level = parts[1].lower()
    try:
        lesson_order = int(parts[2])
    except ValueError:
        await message.answer("❌ lesson_order raqam bo'lishi kerak")
        return

    repo = CourseAudioRepository(session)
    rows = await repo.list_for_lesson(level, lesson_order)

    if not rows:
        await message.answer(f"🔇 {level} / lesson_{lesson_order:02d} uchun audio yo'q")
        return

    lines = [f"🎵 <b>{level} — Dars {lesson_order}</b>\n"]
    for row in rows:
        lines.append(f"  <code>{row.audio_type}</code> → <code>{row.file_id[:30]}…</code>")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.voice | F.audio | F.document)
async def admin_upload_audio_handler(message: Message, session):
    """Audio yuklash — voice, audio yoki mp3/ogg fayl sifatida yuboring.

    Caption (podpis) ga yozing:  hsk1 1 dialogue_1
    Format:  {level} {lesson_order} {audio_type}
    audio_type:  vocab | dialogue_1 | dialogue_2 | ...

    Misol caption:
      hsk1 1 vocab
      hsk1 1 dialogue_1
      hsk2 3 dialogue_2
    """
    if not _is_admin(message.from_user.id):
        raise SkipHandler()

    caption = (message.caption or "").strip().lower()
    import re
    m = re.match(r"^(hsk\d+)\s+(\d+)\s+(vocab|dialogue_\d+)$", caption)
    if not m:
        # Caption yo'q yoki noto'g'ri — yordam ko'rsat
        await message.answer(
            "📎 Fayl qabul qilindi, lekin <b>caption (podpis) noto'g'ri</b>.\n\n"
            "Faylni qaytadan yuboring, caption qatoriga quyidagi formatda yozing:\n"
            "<code>hsk1 1 dialogue_1</code>\n\n"
            "Misollар:\n"
            "<code>hsk1 1 vocab</code> — 1-dars so'zlar\n"
            "<code>hsk1 1 dialogue_1</code> — 1-dars 1-dialog\n"
            "<code>hsk1 1 dialogue_2</code> — 1-dars 2-dialog\n"
            "<code>hsk2 3 dialogue_1</code> — HSK2 3-dars 1-dialog",
            parse_mode="HTML",
        )
        return

    level = m.group(1)
    lesson_order = int(m.group(2))
    audio_type = m.group(3)

    # file_id olish — voice, audio yoki document (mp3 fayl)
    if message.voice:
        file_id = message.voice.file_id
    elif message.audio:
        file_id = message.audio.file_id
    elif message.document:
        file_id = message.document.file_id
    else:
        await message.answer("❌ Audio, voice yoki fayl yuboring")
        return

    repo = CourseAudioRepository(session)
    await repo.upsert(level=level, lesson_order=lesson_order, audio_type=audio_type, file_id=file_id)

    await message.answer(
        f"✅ Saqlandi!\n"
        f"📍 <b>{level}</b> · Dars <b>{lesson_order}</b> · <code>{audio_type}</code>\n"
        f"🔑 <code>{file_id[:50]}…</code>",
        parse_mode="HTML",
    )


@router.message(Command("giveaccess"))
async def admin_giveaccess_handler(message: Message, session):
    if not _is_admin(message.from_user.id):
        return

    parts = message.text.strip().split()
    if len(parts) < 3:
        await message.answer("Foydalanish: <code>/giveaccess TELEGRAM_ID PLAN</code>", parse_mode="HTML")
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Noto'g'ri ID")
        return

    plan = parts[2]
    if plan not in ("10_days", "1_month"):
        await message.answer("❌ Plan: 10_days yoki 1_month")
        return

    from app.services.subscription_service import SubscriptionService
    sub_service = SubscriptionService(session)
    await sub_service.activate_plan(telegram_id=target_id, plan_type=plan)
    await session.commit()
    await message.answer(f"✅ {target_id} ga {plan} obuna berildi")

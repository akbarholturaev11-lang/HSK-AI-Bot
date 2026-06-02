from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.fsm.partner import AdminPartnerStates
from app.bot.utils.i18n import t
from app.config import settings
from app.db.models.partner import Partner, PartnerPayout
from app.repositories.partner_repo import PAYOUT_EDITABLE_STATUSES, PAYOUT_PROCESSING_STATUS
from app.repositories.user_repo import UserRepository
from app.services.partner_service import PartnerService
from app.bot.utils.workflow_message import (
    delete_message_safely,
    edit_callback_workflow_message,
    edit_stored_workflow_message,
)


router = Router()
_PARTNER_PANEL_CHAT_ID = "admin_partner_panel_chat_id"
_PARTNER_PANEL_MSG_ID = "admin_partner_panel_msg_id"


def _is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.admin_id_list


def _fmt_number(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _status_label(status: str) -> str:
    return {
        "pending": "Kutilmoqda",
        "active": "Faol",
        "blocked": "Bloklangan",
    }.get(status, status)


def _payout_status_label(status: str) -> str:
    return {
        "pending": "Kutilmoqda",
        "deadline_set": "Muddat belgilangan",
        "processing": "Admin to'lov qilmoqda",
        "paid": "To'langan",
        "rejected": "Rad qilingan",
    }.get(status, status)


async def _edit_callback(
    callback: CallbackQuery,
    text: str,
    keyboard: InlineKeyboardMarkup,
) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


async def _edit_callback_flow(
    callback: CallbackQuery,
    state: FSMContext,
    text: str,
    keyboard: InlineKeyboardMarkup,
) -> None:
    await edit_callback_workflow_message(
        callback,
        state,
        text,
        chat_id_key=_PARTNER_PANEL_CHAT_ID,
        message_id_key=_PARTNER_PANEL_MSG_ID,
        reply_markup=keyboard,
    )


async def _edit_state_flow(
    message: Message,
    state: FSMContext,
    text: str,
    keyboard: InlineKeyboardMarkup,
) -> None:
    await edit_stored_workflow_message(
        message,
        state,
        text,
        chat_id_key=_PARTNER_PANEL_CHAT_ID,
        message_id_key=_PARTNER_PANEL_MSG_ID,
        reply_markup=keyboard,
    )


def admin_partners_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏳ Kutilayotgan arizalar", callback_data="adm:partners:pending")],
            [InlineKeyboardButton(text="✅ Faol hamkorlar", callback_data="adm:partners:active")],
            [InlineKeyboardButton(text="💸 Pul yechish so'rovlari", callback_data="adm:partners:payouts")],
            [InlineKeyboardButton(text="⚙️ Hamkorlik sozlamalari", callback_data="adm:partners:settings")],
            [InlineKeyboardButton(text="📊 Umumiy statistika", callback_data="adm:partners:stats")],
            [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:menu")],
        ]
    )


def admin_partner_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Hamkorlar", callback_data="adm:partners")],
        ]
    )


def admin_partner_detail_keyboard(partner: Partner) -> InlineKeyboardMarkup:
    rows = []
    if partner.status == "pending":
        rows.append([InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"adm:partner_approve:{partner.id}")])
    if partner.status == "active":
        rows.append([InlineKeyboardButton(text="⛔ Bloklash", callback_data=f"adm:partner_block:{partner.id}")])
    if partner.status == "blocked":
        rows.append([InlineKeyboardButton(text="✅ Blokdan chiqarish", callback_data=f"adm:partner_unblock:{partner.id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Hamkorlar", callback_data="adm:partners")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_payout_keyboard(
    payout_id: int,
    *,
    has_qr_code: bool = False,
    status: str = "pending",
) -> InlineKeyboardMarkup:
    rows = []
    if has_qr_code:
        rows.append([InlineKeyboardButton(text="📱 QR kodni ko'rish", callback_data=f"adm:payout_qr:{payout_id}")])
    if status == PAYOUT_PROCESSING_STATUS:
        rows.extend(
            [
                [InlineKeyboardButton(text="🔄 To'lovni davom ettirish", callback_data=f"adm:payout_pay:{payout_id}")],
                [
                    InlineKeyboardButton(
                        text="🔓 To'lov jarayonini bekor qilish",
                        callback_data=f"adm:payout_payment_cancel:{payout_id}",
                    )
                ],
            ]
        )
    else:
        rows.extend(
            [
                [InlineKeyboardButton(text="✅ To'lash", callback_data=f"adm:payout_pay:{payout_id}")],
                [InlineKeyboardButton(text="✉️ Xabar yuborish", callback_data=f"adm:payout_message:{payout_id}")],
                [InlineKeyboardButton(text="⏰ Muddat belgilash", callback_data=f"adm:payout_deadline:{payout_id}")],
                [InlineKeyboardButton(text="❌ Rad qilish", callback_data=f"adm:payout_reject:{payout_id}")],
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Hamkorlar", callback_data="adm:partners")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_payout_payment_cancel_keyboard(payout_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔓 To'lov jarayonini bekor qilish",
                    callback_data=f"adm:payout_payment_cancel:{payout_id}",
                )
            ],
        ]
    )


def admin_deadline_keyboard(payout_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1 kun", callback_data=f"adm:payout_due:{payout_id}:1"),
                InlineKeyboardButton(text="3 kun", callback_data=f"adm:payout_due:{payout_id}:3"),
                InlineKeyboardButton(text="7 kun", callback_data=f"adm:payout_due:{payout_id}:7"),
            ],
            [InlineKeyboardButton(text="⬅️ Hamkorlar", callback_data="adm:partners")],
        ]
    )


def admin_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💱 USD/TJS kursini o'zgartirish", callback_data="adm:partners:set_rate")],
            [InlineKeyboardButton(text="💴 CNY kursini o'zgartirish", callback_data="adm:partners:set_cny_rate")],
            [InlineKeyboardButton(text="🧮 Hisoblash turini tanlash", callback_data="adm:partners:commission_mode")],
            [InlineKeyboardButton(text="📈 Foizni o'zgartirish", callback_data="adm:partners:set_percent")],
            [InlineKeyboardButton(text="💵 Belgilangan summani o'zgartirish", callback_data="adm:partners:set_fixed")],
            [InlineKeyboardButton(text="🎁 Bonusni o'zgartirish", callback_data="adm:partners:set_bonus")],
            [InlineKeyboardButton(text="💸 Minimal yechishni o'zgartirish", callback_data="adm:partners:set_minimum")],
            [InlineKeyboardButton(text="⬅️ Hamkorlar", callback_data="adm:partners")],
        ]
    )


def admin_commission_mode_keyboard(commission_mode: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'✅' if commission_mode == 'percent' else '▫️'} Foizda hisoblash",
                    callback_data="adm:partners:mode:percent",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{'✅' if commission_mode == 'fixed' else '▫️'} Aniq summada hisoblash",
                    callback_data="adm:partners:mode:fixed",
                )
            ],
            [InlineKeyboardButton(text="⬅️ Sozlamalar", callback_data="adm:partners:settings")],
        ]
    )


def admin_settings_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Sozlamalar", callback_data="adm:partners:settings")],
        ]
    )


async def _partner_detail_text(session, partner: Partner) -> str:
    service = PartnerService(session)
    user = await UserRepository(session).get_by_telegram_id(partner.user_telegram_id)
    balance = await service.get_balance(partner)
    username = f"@{escape(user.username)}" if user and user.username else "—"
    return (
        f"🤝 <b>Hamkor #{partner.id}</b>\n\n"
        f"Holat: <b>{escape(_status_label(partner.status))}</b>\n"
        f"Username: <b>{username}</b>\n"
        f"Telegram ID: <code>{partner.user_telegram_id}</code>\n"
        f"Reklama joyi: {escape(partner.promotion_channel)}\n"
        f"Auditoriya: {escape(partner.audience_size)}\n"
        f"Aloqa: {escape(partner.contact_username)}\n\n"
        f"Balans: <b>${balance.balance_usd:.2f}</b>\n"
        f"Jarayonda: <b>${balance.in_progress_usd:.2f}</b>\n"
        f"Yechilgan jami: <b>${balance.withdrawn_usd:.2f}</b>\n"
        f"Kelganlar: <b>{balance.referrals}</b>\n"
        f"To'lov qilganlar: <b>{balance.paid_referrals}</b>"
    )


async def _settings_text(session) -> str:
    service = PartnerService(session)
    commission_mode = await service.get_commission_mode()
    mode_label = "Foizda hisoblash" if commission_mode == "percent" else "Aniq summada hisoblash"
    active_value = (
        f"{_fmt_number(await service.get_commission_percent())}%"
        if commission_mode == "percent"
        else f"${await service.get_commission_usd():.2f}"
    )
    return (
        "⚙️ <b>Hamkorlik sozlamalari</b>\n\n"
        f"1 USD = <b>{await service.get_usdt_tjs_rate():.4f} TJS</b>\n"
        f"1 USD = <b>{await service.get_usd_cny_rate():.4f} CNY</b>\n"
        f"Hisoblash turi: <b>{mode_label}</b>\n"
        f"Faol komissiya: <b>{active_value}</b>\n\n"
        f"Saqlangan foiz: <b>{_fmt_number(await service.get_commission_percent())}%</b>\n"
        f"Saqlangan summa: <b>${await service.get_commission_usd():.2f}</b>\n"
        f"Hamkor bonusi: <b>${await service.get_signup_bonus_usd():.2f} locked</b>\n"
        f"Minimal payout: <b>${await service.get_min_payout_usd():.2f}</b>"
    )


@router.callback_query(F.data == "adm:partners")
async def admin_partners_panel(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.answer()
    await _edit_callback(
        callback,
        "🤝 <b>Hamkorlar</b>\n\nKerakli bo'limni tanlang.",
        admin_partners_keyboard(),
    )


@router.callback_query(F.data.in_({"adm:partners:pending", "adm:partners:active"}))
async def admin_partner_list(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    status = callback.data.split(":")[2]
    partners = await PartnerService(session).repo.list_by_status(status)
    rows = [
        [InlineKeyboardButton(text=f"#{partner.id} · {partner.user_telegram_id}", callback_data=f"adm:partner:{partner.id}")]
        for partner in partners
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Hamkorlar", callback_data="adm:partners")])
    await callback.answer()
    await _edit_callback(
        callback,
        f"🤝 <b>{'Kutilayotgan arizalar' if status == 'pending' else 'Faol hamkorlar'}</b>\n\n"
        f"Jami: <b>{len(partners)}</b>",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("adm:partner:"))
async def admin_partner_detail(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    partner = await PartnerService(session).repo.get_by_id(int(callback.data.split(":")[2]))
    if not partner:
        await callback.answer("Partner topilmadi", show_alert=True)
        return
    await callback.answer()
    await _edit_callback(callback, await _partner_detail_text(session, partner), admin_partner_detail_keyboard(partner))


async def _change_partner_status(callback: CallbackQuery, session, target_status: str) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    partner_id = int(callback.data.split(":")[2])
    service = PartnerService(session)
    partner = await service.repo.get_by_id(partner_id)
    if not partner:
        await callback.answer("Partner topilmadi", show_alert=True)
        return
    if target_status == "active" and partner.status == "pending":
        await service.approve(partner, callback.from_user.id)
        notify_key = "partner_approved_notification"
    elif target_status == "active":
        await service.unblock(partner, callback.from_user.id)
        notify_key = "partner_unblocked_notification"
    else:
        await service.block(partner, callback.from_user.id)
        notify_key = "partner_blocked_notification"
    await session.commit()
    await service.notify_partner(callback.bot, partner, notify_key)
    await callback.answer("Saqlandi", show_alert=True)
    await _edit_callback(callback, await _partner_detail_text(session, partner), admin_partner_detail_keyboard(partner))


@router.callback_query(F.data.startswith("adm:partner_approve:"))
async def admin_partner_approve(callback: CallbackQuery, session):
    await _change_partner_status(callback, session, "active")


@router.callback_query(F.data.startswith("adm:partner_block:"))
async def admin_partner_block(callback: CallbackQuery, session):
    await _change_partner_status(callback, session, "blocked")


@router.callback_query(F.data.startswith("adm:partner_unblock:"))
async def admin_partner_unblock(callback: CallbackQuery, session):
    await _change_partner_status(callback, session, "active")


@router.callback_query(F.data == "adm:partners:payouts")
async def admin_payout_list(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    payouts = await PartnerService(session).repo.list_open_payouts()
    rows = [
        [
            InlineKeyboardButton(
                text=f"#{payout.id} · ${payout.amount_usd:.2f} · {_payout_status_label(payout.status)}",
                callback_data=f"adm:payout:{payout.id}",
            )
        ]
        for payout in payouts
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Hamkorlar", callback_data="adm:partners")])
    await callback.answer()
    await _edit_callback(
        callback,
        f"💸 <b>Pul yechish so'rovlari</b>\n\nJami: <b>{len(payouts)}</b>",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("adm:payout:"))
async def admin_payout_detail(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    payout = await PartnerService(session).repo.get_payout(int(callback.data.split(":")[2]))
    if not payout:
        await callback.answer("Payout topilmadi", show_alert=True)
        return
    await callback.answer()
    await _edit_callback(
        callback,
        await PartnerService(session).build_admin_payout_text(payout),
        admin_payout_keyboard(
            payout.id,
            has_qr_code=bool(payout.recipient_qr_code_file_id),
            status=payout.status,
        ),
    )


@router.callback_query(F.data.startswith("adm:payout_qr:"))
async def admin_payout_qr_code(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    payout = await PartnerService(session).repo.get_payout(int(callback.data.split(":")[2]))
    if not payout or not payout.recipient_qr_code_file_id:
        await callback.answer("QR kod topilmadi", show_alert=True)
        return
    await callback.answer()
    try:
        await callback.bot.send_photo(
            chat_id=callback.from_user.id,
            photo=payout.recipient_qr_code_file_id,
            caption=(
                f"📱 Partner payout #{payout.id} QR kodi\n\n"
                "Partnerga pulni shu QR kod orqali to'lang."
            ),
        )
    except Exception:
        await callback.message.answer("❌ QR kodni yuborib bo'lmadi.")


async def _get_open_payout(callback: CallbackQuery, session) -> PartnerPayout | None:
    payout = await PartnerService(session).repo.get_payout(int(callback.data.split(":")[2]))
    if not payout or payout.status not in PAYOUT_EDITABLE_STATUSES:
        await callback.answer("Payout yopilgan yoki topilmadi", show_alert=True)
        return None
    return payout


@router.callback_query(F.data.startswith("adm:payout_pay:"))
async def admin_payout_pay(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    service = PartnerService(session)
    payout_id = int(callback.data.split(":")[2])
    payout = await service.repo.claim_payout_for_payment(payout_id, callback.from_user.id)
    if not payout:
        await callback.answer("Payout boshqa admin tomonidan band qilingan yoki yopilgan", show_alert=True)
        return
    await session.commit()
    await state.clear()
    await state.update_data(admin_partner_payout_id=payout.id)
    await state.set_state(AdminPartnerStates.waiting_payout_screenshot)
    await callback.answer()
    await _edit_callback_flow(
        callback,
        state,
        f"✅ <b>Payout #{payout.id}</b>\n\n"
        f"To'lang: <b>{payout.local_amount:.2f} {escape(payout.local_currency)}</b>\n"
        "To'lov tugagach screenshot yuboring.",
        admin_payout_payment_cancel_keyboard(payout.id),
    )


@router.callback_query(F.data.startswith("adm:payout_payment_cancel:"))
async def admin_payout_payment_cancel(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    service = PartnerService(session)
    payout_id = int(callback.data.split(":")[2])
    if not await service.repo.release_payout_payment(payout_id, callback.from_user.id):
        await callback.answer("Bu payout siz tomonidan band qilinmagan", show_alert=True)
        return
    await session.commit()
    payout = await service.repo.get_payout(payout_id)
    await state.clear()
    await callback.answer("To'lov jarayoni bekor qilindi", show_alert=True)
    if payout:
        await _edit_callback(
            callback,
            await service.build_admin_payout_text(payout),
            admin_payout_keyboard(
                payout.id,
                has_qr_code=bool(payout.recipient_qr_code_file_id),
                status=payout.status,
            ),
        )


@router.message(StateFilter(AdminPartnerStates.waiting_payout_screenshot), F.photo)
async def admin_payout_screenshot(message: Message, state: FSMContext, session):
    if not _is_admin(message.from_user.id):
        return
    data = await state.get_data()
    service = PartnerService(session)
    payout = await service.repo.get_payout(int(data.get("admin_partner_payout_id") or 0))
    if not payout or payout.status != PAYOUT_PROCESSING_STATUS:
        await _edit_state_flow(message, state, "❌ Payout yopilgan yoki topilmadi.", admin_partner_back_keyboard())
        await state.clear()
        return
    partner = await service.repo.get_by_id(payout.partner_id)
    screenshot_file_id = message.photo[-1].file_id
    if not await service.repo.mark_payout_paid(payout.id, screenshot_file_id, message.from_user.id):
        await _edit_state_flow(
            message,
            state,
            "❌ Payout boshqa admin tomonidan band qilingan yoki yopilgan.",
            admin_partner_back_keyboard(),
        )
        await state.clear()
        return
    await session.commit()
    user = await UserRepository(session).get_by_telegram_id(partner.user_telegram_id) if partner else None
    if user:
        try:
            await message.bot.send_photo(
                chat_id=user.telegram_id,
                photo=screenshot_file_id,
                caption=t("partner_payout_paid_notification", user.language or "ru", amount=f"${payout.amount_usd:.2f}"),
            )
        except Exception:
            pass
    await _edit_state_flow(
        message,
        state,
        f"✅ Payout #{payout.id} paid qilindi.",
        admin_partners_keyboard(),
    )
    await state.clear()


@router.message(StateFilter(AdminPartnerStates.waiting_payout_screenshot))
async def admin_payout_screenshot_only(message: Message, state: FSMContext):
    if _is_admin(message.from_user.id):
        await delete_message_safely(message)
        data = await state.get_data()
        payout_id = int(data.get("admin_partner_payout_id") or 0)
        await _edit_state_flow(
            message,
            state,
            "Screenshotni photo ko'rinishida yuboring.",
            admin_payout_payment_cancel_keyboard(payout_id),
        )


@router.callback_query(F.data.startswith("adm:payout_message:"))
async def admin_payout_message(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    payout = await _get_open_payout(callback, session)
    if not payout:
        return
    await state.clear()
    await state.update_data(admin_partner_payout_id=payout.id)
    await state.set_state(AdminPartnerStates.waiting_partner_message)
    await callback.answer()
    await _edit_callback_flow(
        callback,
        state,
        f"✉️ <b>Payout #{payout.id}</b>\n\nPartnerga yuboriladigan xabarni yozing.",
        admin_partner_back_keyboard(),
    )


@router.message(StateFilter(AdminPartnerStates.waiting_partner_message))
async def admin_partner_message_text(message: Message, state: FSMContext, session):
    if not _is_admin(message.from_user.id):
        return
    text = (message.text or "").strip()
    if not text:
        await delete_message_safely(message)
        await _edit_state_flow(message, state, "Xabar matnini yuboring.", admin_partner_back_keyboard())
        return
    data = await state.get_data()
    service = PartnerService(session)
    payout = await service.repo.get_payout(int(data.get("admin_partner_payout_id") or 0))
    partner = await service.repo.get_by_id(payout.partner_id) if payout else None
    if not payout or not partner:
        await delete_message_safely(message)
        await _edit_state_flow(message, state, "❌ Payout topilmadi.", admin_partner_back_keyboard())
        await state.clear()
        return
    await service.notify_partner(message.bot, partner, "partner_admin_message", text=escape(text))
    await delete_message_safely(message)
    await _edit_state_flow(message, state, "✅ Xabar yuborildi.", admin_partners_keyboard())
    await state.clear()


@router.callback_query(F.data.startswith("adm:payout_deadline:"))
async def admin_payout_deadline(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    payout = await _get_open_payout(callback, session)
    if not payout:
        return
    await callback.answer()
    await _edit_callback(
        callback,
        f"⏰ <b>Payout #{payout.id}</b>\n\nMuddatni tanlang.",
        admin_deadline_keyboard(payout.id),
    )


@router.callback_query(F.data.startswith("adm:payout_due:"))
async def admin_payout_due(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    parts = callback.data.split(":")
    payout = await PartnerService(session).repo.get_payout(int(parts[2]))
    days = int(parts[3])
    if not payout or payout.status not in PAYOUT_EDITABLE_STATUSES or days not in {1, 3, 7}:
        await callback.answer("Payout yopilgan yoki muddat noto'g'ri", show_alert=True)
        return
    service = PartnerService(session)
    deadline = datetime.now(timezone.utc) + timedelta(days=days)
    if not await service.repo.set_payout_deadline(payout.id, deadline, callback.from_user.id):
        await callback.answer("Payout boshqa admin tomonidan band qilingan yoki yopilgan", show_alert=True)
        return
    partner = await service.repo.get_by_id(payout.partner_id)
    await session.commit()
    if partner:
        await service.notify_partner(callback.bot, partner, "partner_payout_deadline_notification", days=days)
    await callback.answer("Muddat saqlandi", show_alert=True)
    await _edit_callback(
        callback,
        await service.build_admin_payout_text(payout),
        admin_payout_keyboard(
            payout.id,
            has_qr_code=bool(payout.recipient_qr_code_file_id),
            status=payout.status,
        ),
    )


@router.callback_query(F.data.startswith("adm:payout_reject:"))
async def admin_payout_reject(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    payout = await _get_open_payout(callback, session)
    if not payout:
        return
    service = PartnerService(session)
    partner = await service.repo.get_by_id(payout.partner_id)
    if not await service.repo.reject_payout(payout.id, callback.from_user.id):
        await callback.answer("Payout boshqa admin tomonidan band qilingan yoki yopilgan", show_alert=True)
        return
    await session.commit()
    if partner:
        await service.notify_partner(callback.bot, partner, "partner_payout_rejected_notification", amount=f"${payout.amount_usd:.2f}")
    await callback.answer("Rad qilindi", show_alert=True)
    await _edit_callback(callback, f"❌ Payout #{payout.id} rad qilindi.", admin_partner_back_keyboard())


@router.callback_query(F.data == "adm:partners:settings")
async def admin_partner_settings(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.answer()
    await _edit_callback(callback, await _settings_text(session), admin_settings_keyboard())


@router.callback_query(F.data == "adm:partners:commission_mode")
async def admin_partner_commission_mode(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    service = PartnerService(session)
    commission_mode = await service.get_commission_mode()
    mode_label = "Foizda hisoblash" if commission_mode == "percent" else "Aniq summada hisoblash"
    await callback.answer()
    await _edit_callback(
        callback,
        "🧮 <b>Komissiya hisoblash turi</b>\n\n"
        "Faqat bitta tur faol bo'ladi.\n"
        f"Hozirgi tanlov: <b>{mode_label}</b>",
        admin_commission_mode_keyboard(commission_mode),
    )


@router.callback_query(F.data.startswith("adm:partners:mode:"))
async def admin_partner_commission_mode_select(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    commission_mode = callback.data.split(":")[3]
    if commission_mode not in {"percent", "fixed"}:
        await callback.answer("Hisoblash turi noto'g'ri", show_alert=True)
        return
    await state.clear()
    service = PartnerService(session)
    await service.set_commission_mode(commission_mode)
    await session.commit()
    await callback.answer("Hisoblash turi saqlandi", show_alert=True)
    await _edit_callback(callback, await _settings_text(session), admin_settings_keyboard())


@router.callback_query(
    F.data.in_(
        {
            "adm:partners:set_rate",
            "adm:partners:set_cny_rate",
            "adm:partners:set_percent",
            "adm:partners:set_fixed",
            "adm:partners:set_bonus",
            "adm:partners:set_minimum",
        }
    )
)
async def admin_partner_setting_prompt(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    setting_type = callback.data.split(":")[2]
    prompts = {
        "set_rate": "💱 Yangi USD kursini TJS'da yuboring. Masalan: <code>10.90</code>",
        "set_cny_rate": "💴 Yangi USD kursini CNY'da yuboring. Masalan: <code>6.80</code>",
        "set_percent": "📈 Referral to'lovidan beriladigan foizni yuboring. Masalan: <code>20</code>",
        "set_fixed": "💵 Har bir paid referral uchun aniq summani USD'da yuboring. Masalan: <code>1.00</code>",
        "set_bonus": "🎁 Yangi partner bonusini USD'da yuboring. Masalan: <code>1.00</code>",
        "set_minimum": "💸 Minimal yechish summasini USD'da yuboring. Masalan: <code>5.00</code>",
    }
    states = {
        "set_rate": AdminPartnerStates.waiting_usdt_tjs_rate,
        "set_cny_rate": AdminPartnerStates.waiting_usd_cny_rate,
        "set_percent": AdminPartnerStates.waiting_commission_percent,
        "set_fixed": AdminPartnerStates.waiting_commission_fixed,
        "set_bonus": AdminPartnerStates.waiting_signup_bonus,
        "set_minimum": AdminPartnerStates.waiting_min_payout,
    }
    await state.clear()
    await state.update_data(admin_partner_setting_type=setting_type)
    await state.set_state(states[setting_type])
    await callback.answer()
    await _edit_callback_flow(
        callback,
        state,
        prompts[setting_type],
        admin_settings_back_keyboard(),
    )


async def _save_decimal_setting(message: Message, state: FSMContext, session, setting_type: str) -> None:
    if not _is_admin(message.from_user.id):
        return
    try:
        value = Decimal((message.text or "").strip().replace(",", "."))
    except InvalidOperation:
        await delete_message_safely(message)
        await _edit_state_flow(
            message,
            state,
            "Musbat raqam yuboring. Masalan: <code>10.90</code>",
            admin_settings_back_keyboard(),
        )
        return
    if not value.is_finite():
        await delete_message_safely(message)
        await _edit_state_flow(message, state, "Real qiymat yuboring.", admin_settings_back_keyboard())
        return
    allow_zero = setting_type in {"set_percent", "set_fixed", "set_bonus"}
    max_value = Decimal("100") if setting_type == "set_percent" else Decimal("100000")
    if value < 0 or (not allow_zero and value == 0) or value > max_value:
        await delete_message_safely(message)
        await _edit_state_flow(message, state, "Real qiymat yuboring.", admin_settings_back_keyboard())
        return
    service = PartnerService(session)
    if setting_type == "set_rate":
        await service.set_usdt_tjs_rate(value)
    elif setting_type == "set_cny_rate":
        await service.set_usd_cny_rate(value)
    elif setting_type == "set_percent":
        await service.set_commission_percent(value)
    elif setting_type == "set_fixed":
        await service.set_commission_usd(value)
    elif setting_type == "set_bonus":
        await service.set_signup_bonus_usd(value)
    else:
        await service.set_min_payout_usd(value)
    await session.commit()
    await delete_message_safely(message)
    await _edit_state_flow(message, state, f"✅ Saqlandi.\n\n{await _settings_text(session)}", admin_settings_keyboard())
    await state.clear()


@router.message(StateFilter(AdminPartnerStates.waiting_usdt_tjs_rate))
async def admin_partner_rate_value(message: Message, state: FSMContext, session):
    await _save_decimal_setting(message, state, session, "set_rate")


@router.message(StateFilter(AdminPartnerStates.waiting_usd_cny_rate))
async def admin_partner_cny_rate_value(message: Message, state: FSMContext, session):
    await _save_decimal_setting(message, state, session, "set_cny_rate")


@router.message(StateFilter(AdminPartnerStates.waiting_commission_percent))
async def admin_partner_commission_percent_value(message: Message, state: FSMContext, session):
    await _save_decimal_setting(message, state, session, "set_percent")


@router.message(StateFilter(AdminPartnerStates.waiting_commission_fixed))
async def admin_partner_commission_fixed_value(message: Message, state: FSMContext, session):
    await _save_decimal_setting(message, state, session, "set_fixed")


@router.message(StateFilter(AdminPartnerStates.waiting_signup_bonus))
async def admin_partner_bonus_value(message: Message, state: FSMContext, session):
    await _save_decimal_setting(message, state, session, "set_bonus")


@router.message(StateFilter(AdminPartnerStates.waiting_min_payout))
async def admin_partner_minimum_value(message: Message, state: FSMContext, session):
    await _save_decimal_setting(message, state, session, "set_minimum")


@router.callback_query(F.data == "adm:partners:stats")
async def admin_partner_stats(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    stats = await PartnerService(session).overall_stats()
    conversion = round(stats["paid_referrals"] / stats["referrals"] * 100, 1) if stats["referrals"] else 0
    await callback.answer()
    await _edit_callback(
        callback,
        "📊 <b>Hamkorlik statistikasi</b>\n\n"
        f"Kutilayotgan arizalar: <b>{stats['pending']}</b>\n"
        f"Faol hamkorlar: <b>{stats['active']}</b>\n"
        f"Bloklanganlar: <b>{stats['blocked']}</b>\n\n"
        f"Kelgan userlar: <b>{stats['referrals']}</b>\n"
        f"Trial / non-paid: <b>{stats['trial_users']}</b>\n"
        f"To'lov qilganlar: <b>{stats['paid_referrals']}</b>\n"
        f"Savol berganlar: <b>{stats['question_users']}</b>\n"
        f"Kursga kirganlar: <b>{stats['course_users']}</b>\n"
        f"To'lov konversiyasi: <b>{conversion}%</b>\n\n"
        f"Credit yozilgan: <b>${stats['credited_usd']:.2f}</b>\n"
        f"Band qilingan payout: <b>${stats['reserved_usd']:.2f}</b>\n"
        f"To'langan payout: <b>${stats['withdrawn_usd']:.2f}</b>",
        admin_partner_back_keyboard(),
    )

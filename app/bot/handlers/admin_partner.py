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
from app.repositories.user_repo import UserRepository
from app.services.partner_service import PartnerService


router = Router()


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


def admin_payout_keyboard(payout_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ To'lash", callback_data=f"adm:payout_pay:{payout_id}")],
            [InlineKeyboardButton(text="✉️ Xabar yuborish", callback_data=f"adm:payout_message:{payout_id}")],
            [InlineKeyboardButton(text="⏰ Muddat belgilash", callback_data=f"adm:payout_deadline:{payout_id}")],
            [InlineKeyboardButton(text="❌ Rad qilish", callback_data=f"adm:payout_reject:{payout_id}")],
            [InlineKeyboardButton(text="⬅️ Hamkorlar", callback_data="adm:partners")],
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
            [InlineKeyboardButton(text="💱 USDT kursini o'zgartirish", callback_data="adm:partners:set_rate")],
            [InlineKeyboardButton(text="📈 Foizli komissiyani belgilash", callback_data="adm:partners:set_percent")],
            [InlineKeyboardButton(text="💵 Aniq summa komissiyasini belgilash", callback_data="adm:partners:set_fixed")],
            [InlineKeyboardButton(text="🎁 Bonusni o'zgartirish", callback_data="adm:partners:set_bonus")],
            [InlineKeyboardButton(text="💸 Minimal yechishni o'zgartirish", callback_data="adm:partners:set_minimum")],
            [InlineKeyboardButton(text="⬅️ Hamkorlar", callback_data="adm:partners")],
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
    mode_label = "Foizli" if commission_mode == "percent" else "Aniq summa"
    return (
        "⚙️ <b>Hamkorlik sozlamalari</b>\n\n"
        f"1 USDT = <b>{await service.get_usdt_tjs_rate():.4f} TJS</b>\n"
        f"Faol komissiya turi: <b>{mode_label}</b>\n"
        f"Foizli komissiya: <b>{_fmt_number(await service.get_commission_percent())}%</b>\n"
        f"Aniq summa komissiyasi: <b>${await service.get_commission_usd():.2f}</b>\n"
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
        [InlineKeyboardButton(text=f"#{payout.id} · ${payout.amount_usd:.2f}", callback_data=f"adm:payout:{payout.id}")]
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
    await _edit_callback(callback, await PartnerService(session).build_admin_payout_text(payout), admin_payout_keyboard(payout.id))


async def _get_open_payout(callback: CallbackQuery, session) -> PartnerPayout | None:
    payout = await PartnerService(session).repo.get_payout(int(callback.data.split(":")[2]))
    if not payout or payout.status not in {"pending", "deadline_set"}:
        await callback.answer("Payout yopilgan yoki topilmadi", show_alert=True)
        return None
    return payout


@router.callback_query(F.data.startswith("adm:payout_pay:"))
async def admin_payout_pay(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    payout = await _get_open_payout(callback, session)
    if not payout:
        return
    await state.clear()
    await state.update_data(admin_partner_payout_id=payout.id)
    await state.set_state(AdminPartnerStates.waiting_payout_screenshot)
    await callback.answer()
    await _edit_callback(
        callback,
        f"✅ <b>Payout #{payout.id}</b>\n\nTo'lovni bajaring va screenshot yuboring.",
        admin_partner_back_keyboard(),
    )


@router.message(StateFilter(AdminPartnerStates.waiting_payout_screenshot), F.photo)
async def admin_payout_screenshot(message: Message, state: FSMContext, session):
    if not _is_admin(message.from_user.id):
        return
    data = await state.get_data()
    service = PartnerService(session)
    payout = await service.repo.get_payout(int(data.get("admin_partner_payout_id") or 0))
    if not payout or payout.status not in {"pending", "deadline_set"}:
        await state.clear()
        await message.answer("❌ Payout yopilgan yoki topilmadi.")
        return
    partner = await service.repo.get_by_id(payout.partner_id)
    screenshot_file_id = message.photo[-1].file_id
    await service.repo.mark_payout_paid(payout, screenshot_file_id, message.from_user.id)
    await session.commit()
    await state.clear()
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
    await message.answer(
        f"✅ Payout #{payout.id} paid qilindi.",
        reply_markup=admin_partners_keyboard(),
    )


@router.message(StateFilter(AdminPartnerStates.waiting_payout_screenshot))
async def admin_payout_screenshot_only(message: Message):
    if _is_admin(message.from_user.id):
        await message.answer("Screenshotni photo ko'rinishida yuboring.")


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
    await _edit_callback(
        callback,
        f"✉️ <b>Payout #{payout.id}</b>\n\nPartnerga yuboriladigan xabarni yozing.",
        admin_partner_back_keyboard(),
    )


@router.message(StateFilter(AdminPartnerStates.waiting_partner_message))
async def admin_partner_message_text(message: Message, state: FSMContext, session):
    if not _is_admin(message.from_user.id):
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer("Xabar matnini yuboring.")
        return
    data = await state.get_data()
    service = PartnerService(session)
    payout = await service.repo.get_payout(int(data.get("admin_partner_payout_id") or 0))
    partner = await service.repo.get_by_id(payout.partner_id) if payout else None
    if not payout or not partner:
        await state.clear()
        await message.answer("❌ Payout topilmadi.")
        return
    await service.notify_partner(message.bot, partner, "partner_admin_message", text=escape(text))
    await state.clear()
    await message.answer("✅ Xabar yuborildi.", reply_markup=admin_partners_keyboard())


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
    if not payout or payout.status not in {"pending", "deadline_set"} or days not in {1, 3, 7}:
        await callback.answer("Payout yopilgan yoki muddat noto'g'ri", show_alert=True)
        return
    service = PartnerService(session)
    deadline = datetime.now(timezone.utc) + timedelta(days=days)
    await service.repo.set_payout_deadline(payout, deadline, callback.from_user.id)
    partner = await service.repo.get_by_id(payout.partner_id)
    await session.commit()
    if partner:
        await service.notify_partner(callback.bot, partner, "partner_payout_deadline_notification", days=days)
    await callback.answer("Muddat saqlandi", show_alert=True)
    await _edit_callback(callback, await service.build_admin_payout_text(payout), admin_payout_keyboard(payout.id))


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
    await service.repo.reject_payout(payout, callback.from_user.id)
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


@router.callback_query(
    F.data.in_(
        {
            "adm:partners:set_rate",
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
        "set_rate": "💱 Yangi USDT kursini TJS'da yuboring. Masalan: <code>10.90</code>",
        "set_percent": "📈 Referral to'lovidan beriladigan foizni yuboring. Masalan: <code>20</code>",
        "set_fixed": "💵 Har bir paid referral uchun aniq summani USD'da yuboring. Masalan: <code>1.00</code>",
        "set_bonus": "🎁 Yangi partner bonusini USD'da yuboring. Masalan: <code>1.00</code>",
        "set_minimum": "💸 Minimal yechish summasini USD'da yuboring. Masalan: <code>5.00</code>",
    }
    states = {
        "set_rate": AdminPartnerStates.waiting_usdt_tjs_rate,
        "set_percent": AdminPartnerStates.waiting_commission_percent,
        "set_fixed": AdminPartnerStates.waiting_commission_fixed,
        "set_bonus": AdminPartnerStates.waiting_signup_bonus,
        "set_minimum": AdminPartnerStates.waiting_min_payout,
    }
    await state.clear()
    await state.update_data(admin_partner_setting_type=setting_type)
    await state.set_state(states[setting_type])
    await callback.answer()
    await _edit_callback(
        callback,
        prompts[setting_type],
        admin_partner_back_keyboard(),
    )


async def _save_decimal_setting(message: Message, state: FSMContext, session, setting_type: str) -> None:
    if not _is_admin(message.from_user.id):
        return
    try:
        value = Decimal((message.text or "").strip().replace(",", "."))
    except InvalidOperation:
        await message.answer("Musbat raqam yuboring. Masalan: <code>10.90</code>", parse_mode="HTML")
        return
    if not value.is_finite():
        await message.answer("Real qiymat yuboring.")
        return
    allow_zero = setting_type in {"set_percent", "set_fixed", "set_bonus"}
    max_value = Decimal("100") if setting_type == "set_percent" else Decimal("100000")
    if value < 0 or (not allow_zero and value == 0) or value > max_value:
        await message.answer("Real qiymat yuboring.")
        return
    service = PartnerService(session)
    if setting_type == "set_rate":
        await service.set_usdt_tjs_rate(value)
    elif setting_type == "set_percent":
        await service.set_commission_percent(value)
        await service.set_commission_mode("percent")
    elif setting_type == "set_fixed":
        await service.set_commission_usd(value)
        await service.set_commission_mode("fixed")
    elif setting_type == "set_bonus":
        await service.set_signup_bonus_usd(value)
    else:
        await service.set_min_payout_usd(value)
    await session.commit()
    await state.clear()
    await message.answer(f"✅ Saqlandi.\n\n{await _settings_text(session)}", reply_markup=admin_settings_keyboard())


@router.message(StateFilter(AdminPartnerStates.waiting_usdt_tjs_rate))
async def admin_partner_rate_value(message: Message, state: FSMContext, session):
    await _save_decimal_setting(message, state, session, "set_rate")


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

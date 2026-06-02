from decimal import Decimal
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.bot.fsm.partner import PartnerApplicationStates, PartnerPayoutStates
from app.bot.keyboards.partner import (
    partner_active_keyboard,
    partner_apply_keyboard,
    partner_close_keyboard,
    partner_dashboard_keyboard,
    partner_payout_methods_keyboard,
)
from app.bot.utils.i18n import t
from app.repositories.user_repo import UserRepository
from app.services.partner_service import PartnerService


router = Router()
_QR_PAYOUT_METHODS = {"alipay", "wechat"}


def _fmt_usd(value: Decimal) -> str:
    return f"${value:.2f}"


def _lang(user) -> str:
    return user.language if user and user.language else "ru"


async def _remember_block(state: FSMContext, message: Message) -> None:
    await state.update_data(
        partner_block_chat_id=message.chat.id,
        partner_block_message_id=message.message_id,
    )


async def _edit_callback_block(
    callback: CallbackQuery,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup,
) -> Message:
    try:
        edited = await callback.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        message = edited if isinstance(edited, Message) else callback.message
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            message = callback.message
        else:
            message = await callback.message.answer(
                text,
                reply_markup=reply_markup,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
    await _remember_block(state, message)
    return message


async def _edit_state_block(
    message: Message,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup,
) -> None:
    data = await state.get_data()
    try:
        await message.bot.edit_message_text(
            chat_id=data.get("partner_block_chat_id"),
            message_id=data.get("partner_block_message_id"),
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return
    except Exception:
        pass
    sent = await message.answer(
        text,
        reply_markup=reply_markup,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await _remember_block(state, sent)


async def _delete_answer(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        pass


async def _render_partner_text(session, telegram_id: int) -> tuple[str, InlineKeyboardMarkup]:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    lang = _lang(user)
    service = PartnerService(session)
    partner = await service.repo.get_by_telegram_id(telegram_id)

    if not partner:
        return (
            t(
                "partner_not_partner_text",
                lang,
                commission_offer=await service.get_commission_offer(),
                bonus=_fmt_usd(await service.get_signup_bonus_usd()),
                minimum=_fmt_usd(await service.get_min_payout_usd()),
            ),
            partner_apply_keyboard(lang),
        )
    if partner.status == "pending":
        return t("partner_pending_text", lang), partner_close_keyboard(lang)
    if partner.status == "blocked":
        return t("partner_blocked_text", lang), partner_close_keyboard(lang)

    link = await service.build_partner_link(partner) or "—"
    balance = await service.get_balance(partner)
    return (
        t(
            "partner_active_text",
            lang,
            link=escape(link),
            balance=_fmt_usd(balance.balance_usd),
            in_progress=_fmt_usd(balance.in_progress_usd),
            withdrawn=_fmt_usd(balance.withdrawn_usd),
            referrals=balance.referrals,
            paid_referrals=balance.paid_referrals,
        ),
        partner_active_keyboard(lang),
    )


async def open_partner_for_message(message: Message, state: FSMContext, session) -> None:
    await state.clear()
    text, keyboard = await _render_partner_text(session, message.from_user.id)
    await session.commit()
    sent = await message.answer(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await _remember_block(state, sent)


@router.message(Command("partner"))
async def partner_command(message: Message, state: FSMContext, session):
    if not await UserRepository(session).get_by_telegram_id(message.from_user.id):
        return
    await open_partner_for_message(message, state, session)


@router.callback_query(F.data == "partner:open")
async def partner_open_callback(callback: CallbackQuery, state: FSMContext, session):
    await state.clear()
    text, keyboard = await _render_partner_text(session, callback.from_user.id)
    await session.commit()
    await callback.answer()
    await _edit_callback_block(callback, state, text, keyboard)


@router.callback_query(F.data == "partner:dashboard")
async def partner_dashboard_callback(callback: CallbackQuery, state: FSMContext, session):
    await state.clear()
    text, keyboard = await _render_partner_text(session, callback.from_user.id)
    await session.commit()
    await callback.answer()
    await _edit_callback_block(callback, state, text, keyboard)


@router.callback_query(F.data == "partner:close")
async def partner_close_callback(callback: CallbackQuery, state: FSMContext, session):
    from app.bot.handlers.commands import (
        _profile_referral_count,
        _profile_reminder_text,
        _profile_text,
        profile_menu_keyboard,
    )

    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return
    await state.clear()
    lang = _lang(user)
    referral_total = await _profile_referral_count(session, user)
    reminder_text = await _profile_reminder_text(session, user, lang)
    await callback.answer()
    await _edit_callback_block(
        callback,
        state,
        _profile_text(user, lang, referral_total, reminder_text),
        profile_menu_keyboard(lang, user),
    )


@router.callback_query(F.data == "partner:apply")
async def partner_apply_callback(callback: CallbackQuery, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = _lang(user)
    partner = await PartnerService(session).repo.get_by_telegram_id(callback.from_user.id)
    if partner:
        await callback.answer()
        text, keyboard = await _render_partner_text(session, callback.from_user.id)
        await _edit_callback_block(callback, state, text, keyboard)
        return
    await state.clear()
    await state.set_state(PartnerApplicationStates.waiting_promotion_channel)
    await callback.answer()
    await _edit_callback_block(
        callback,
        state,
        t("partner_application_channel_prompt", lang),
        partner_close_keyboard(lang),
    )


@router.message(StateFilter(PartnerApplicationStates.waiting_promotion_channel))
async def partner_application_channel(message: Message, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    lang = _lang(user)
    value = (message.text or "").strip()
    if len(value) < 2:
        await _delete_answer(message)
        await _edit_state_block(message, state, t("partner_application_invalid", lang), partner_close_keyboard(lang))
        return
    await state.update_data(partner_promotion_channel=value)
    await state.set_state(PartnerApplicationStates.waiting_audience_size)
    await _delete_answer(message)
    await _edit_state_block(message, state, t("partner_application_audience_prompt", lang), partner_close_keyboard(lang))


@router.message(StateFilter(PartnerApplicationStates.waiting_audience_size))
async def partner_application_audience(message: Message, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    lang = _lang(user)
    value = (message.text or "").strip()
    if len(value) < 1:
        await _delete_answer(message)
        await _edit_state_block(message, state, t("partner_application_invalid", lang), partner_close_keyboard(lang))
        return
    await state.update_data(partner_audience_size=value)
    await state.set_state(PartnerApplicationStates.waiting_contact_username)
    await _delete_answer(message)
    await _edit_state_block(message, state, t("partner_application_contact_prompt", lang), partner_close_keyboard(lang))


@router.message(StateFilter(PartnerApplicationStates.waiting_contact_username))
async def partner_application_contact(message: Message, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    lang = _lang(user)
    value = (message.text or "").strip()
    if len(value) < 2:
        await _delete_answer(message)
        await _edit_state_block(message, state, t("partner_application_invalid", lang), partner_close_keyboard(lang))
        return
    data = await state.get_data()
    partner = await PartnerService(session).submit_application(
        telegram_id=message.from_user.id,
        promotion_channel=str(data.get("partner_promotion_channel") or ""),
        audience_size=str(data.get("partner_audience_size") or ""),
        contact_username=value,
    )
    await session.commit()
    await PartnerService(session).notify_application(message.bot, partner)
    await _delete_answer(message)
    await _edit_state_block(message, state, t("partner_pending_text", lang), partner_close_keyboard(lang))
    await state.clear()


@router.callback_query(F.data == "partner:link")
async def partner_link_callback(callback: CallbackQuery, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = _lang(user)
    service = PartnerService(session)
    partner = await service.repo.get_by_telegram_id(callback.from_user.id)
    if not partner or partner.status != "active":
        await callback.answer()
        text, keyboard = await _render_partner_text(session, callback.from_user.id)
        await _edit_callback_block(callback, state, text, keyboard)
        return
    link = await service.build_partner_link(partner) or "—"
    await session.commit()
    await callback.answer()
    await _edit_callback_block(
        callback,
        state,
        t("partner_link_text", lang, link=escape(link)),
        partner_dashboard_keyboard(lang),
    )


@router.callback_query(F.data == "partner:payout")
async def partner_payout_callback(callback: CallbackQuery, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = _lang(user)
    service = PartnerService(session)
    partner = await service.repo.get_by_telegram_id(callback.from_user.id)
    if not partner or partner.status != "active":
        await callback.answer()
        return
    balance = await service.get_balance(partner)
    minimum = await service.get_min_payout_usd()
    await callback.answer()
    if await service.repo.has_open_payout(partner.id):
        await _edit_callback_block(
            callback,
            state,
            t("partner_payout_already_open_text", lang),
            partner_dashboard_keyboard(lang),
        )
        return
    if balance.balance_usd < minimum:
        await _edit_callback_block(
            callback,
            state,
            t(
                "partner_payout_unavailable_text",
                lang,
                balance=_fmt_usd(balance.balance_usd),
                minimum=_fmt_usd(minimum),
            ),
            partner_dashboard_keyboard(lang),
        )
        return
    await _edit_callback_block(
        callback,
        state,
        t("partner_payout_choose_method", lang, balance=_fmt_usd(balance.balance_usd)),
        partner_payout_methods_keyboard(lang),
    )


@router.callback_query(F.data.startswith("partner:payout_method:"))
async def partner_payout_method_callback(callback: CallbackQuery, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = _lang(user)
    method = callback.data.split(":")[2]
    if method not in {"bank_card", "alipay", "wechat", "other"}:
        await callback.answer()
        return
    await state.clear()
    await state.update_data(partner_payout_method=method)
    await callback.answer()
    if method == "bank_card":
        await state.set_state(PartnerPayoutStates.waiting_bank_name)
        text = t("partner_payout_bank_name_prompt", lang)
    elif method in _QR_PAYOUT_METHODS:
        await state.update_data(
            partner_payout_bank_name=None,
            partner_payout_account_details="QR code attached",
            partner_payout_holder_name=None,
        )
        await state.set_state(PartnerPayoutStates.waiting_qr_code)
        text = t("partner_payout_qr_prompt", lang)
    else:
        await state.update_data(partner_payout_bank_name=None)
        await state.set_state(PartnerPayoutStates.waiting_account_details)
        text = t("partner_payout_account_prompt", lang)
    await _edit_callback_block(callback, state, text, partner_dashboard_keyboard(lang))


async def _submit_payout_request(
    message: Message,
    state: FSMContext,
    session,
    *,
    delete_answer: bool,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    lang = _lang(user)
    data = await state.get_data()
    service = PartnerService(session)
    partner = await service.repo.get_by_telegram_id(message.from_user.id)
    if not partner or partner.status != "active":
        if delete_answer:
            await _delete_answer(message)
        await state.clear()
        return
    payout = await service.create_payout_request(
        partner=partner,
        payment_method=str(data.get("partner_payout_method") or ""),
        bank_name=data.get("partner_payout_bank_name"),
        account_details=str(data.get("partner_payout_account_details") or ""),
        holder_name=str(data.get("partner_payout_holder_name") or "") or None,
        note=str(data.get("partner_payout_note") or "") or None,
        recipient_qr_code_file_id=str(data.get("partner_payout_qr_code_file_id") or "") or None,
    )
    if delete_answer:
        await _delete_answer(message)
    if not payout:
        if await service.repo.has_open_payout(partner.id):
            await _edit_state_block(
                message,
                state,
                t("partner_payout_already_open_text", lang),
                partner_dashboard_keyboard(lang),
            )
            await state.clear()
            return
        balance = await service.get_balance(partner)
        minimum = await service.get_min_payout_usd()
        await _edit_state_block(
            message,
            state,
            t(
                "partner_payout_unavailable_text",
                lang,
                balance=_fmt_usd(balance.balance_usd),
                minimum=_fmt_usd(minimum),
            ),
            partner_dashboard_keyboard(lang),
        )
        await state.clear()
        return
    await session.commit()
    await service.notify_payout_request(message.bot, payout)
    await _edit_state_block(
        message,
        state,
        t("partner_payout_created_text", lang, amount=_fmt_usd(payout.amount_usd)),
        partner_dashboard_keyboard(lang),
    )
    await state.clear()


@router.message(StateFilter(PartnerPayoutStates.waiting_qr_code), F.photo)
async def partner_payout_qr_code(message: Message, state: FSMContext, session):
    await state.update_data(partner_payout_qr_code_file_id=message.photo[-1].file_id)
    await _submit_payout_request(message, state, session, delete_answer=False)


@router.message(StateFilter(PartnerPayoutStates.waiting_qr_code))
async def partner_payout_qr_code_only(message: Message, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    await _delete_answer(message)
    await _edit_state_block(
        message,
        state,
        t("partner_payout_qr_photo_only", _lang(user)),
        partner_dashboard_keyboard(_lang(user)),
    )


@router.message(StateFilter(PartnerPayoutStates.waiting_bank_name))
async def partner_payout_bank_name(message: Message, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    lang = _lang(user)
    value = (message.text or "").strip()
    if len(value) < 2:
        await _delete_answer(message)
        await _edit_state_block(message, state, t("partner_payout_invalid", lang), partner_dashboard_keyboard(lang))
        return
    await state.update_data(partner_payout_bank_name=value)
    await state.set_state(PartnerPayoutStates.waiting_account_details)
    await _delete_answer(message)
    await _edit_state_block(message, state, t("partner_payout_account_prompt", lang), partner_dashboard_keyboard(lang))


@router.message(StateFilter(PartnerPayoutStates.waiting_account_details))
async def partner_payout_account(message: Message, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    lang = _lang(user)
    value = (message.text or "").strip()
    if len(value) < 3:
        await _delete_answer(message)
        await _edit_state_block(message, state, t("partner_payout_invalid", lang), partner_dashboard_keyboard(lang))
        return
    await state.update_data(partner_payout_account_details=value)
    await state.set_state(PartnerPayoutStates.waiting_holder_name)
    await _delete_answer(message)
    await _edit_state_block(message, state, t("partner_payout_holder_prompt", lang), partner_dashboard_keyboard(lang))


@router.message(StateFilter(PartnerPayoutStates.waiting_holder_name))
async def partner_payout_holder(message: Message, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    lang = _lang(user)
    value = (message.text or "").strip()
    if len(value) < 2:
        await _delete_answer(message)
        await _edit_state_block(message, state, t("partner_payout_invalid", lang), partner_dashboard_keyboard(lang))
        return
    await state.update_data(partner_payout_holder_name=value)
    await state.set_state(PartnerPayoutStates.waiting_note)
    await _delete_answer(message)
    await _edit_state_block(message, state, t("partner_payout_note_prompt", lang), partner_dashboard_keyboard(lang))


@router.message(StateFilter(PartnerPayoutStates.waiting_note))
async def partner_payout_note(message: Message, state: FSMContext, session):
    note = (message.text or "").strip()
    await state.update_data(partner_payout_note=note or None)
    await _submit_payout_request(message, state, session, delete_answer=True)

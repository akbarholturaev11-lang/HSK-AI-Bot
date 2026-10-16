"""Receive a verified account-deletion request without deleting shared data in chat."""

import logging
import re
import uuid

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config import settings
from app.api.account_deletion import notify_deletion_request
from app.services.account_deletion_service import AccountDeletionService
from app.services.desktop_auth_service import DesktopAuthError

router = Router()
logger = logging.getLogger(__name__)
CONFIRM = "account_deletion:confirm"
VERIFY = "account_deletion:verify:"


def is_account_deletion_event(event):
    """Only private, ownership-checked deletion handlers bypass learning blocks."""
    message = event.message if isinstance(event, CallbackQuery) else event
    actor = getattr(event, "from_user", None)
    chat = getattr(message, "chat", None)
    if not actor or not chat or chat.type != "private" or chat.id != actor.id:
        return False
    if isinstance(event, CallbackQuery):
        return event.data == CONFIRM or bool(re.fullmatch(
            r"account_deletion:verify:[0-9a-f-]{36}", event.data or ""))
    return bool(re.fullmatch(r"/start(?:@\w+)?\s+(?:account_deletion|delete_[0-9a-f]{32})\s*", event.text or ""))


@router.message(F.text.regexp(r"^/start(?:@\w+)?\s+delete_[0-9a-f]{32}\s*$"))
async def begin_web_verification(message: Message):
    if not message.from_user or message.chat.type != "private" or message.chat.id != message.from_user.id:
        return
    request_id = str(uuid.UUID(message.text.strip().rsplit("delete_", 1)[1]))
    await message.answer(
        "HSK AI web sahifasida hisobni o‘chirish so‘rovi boshlandi. "
        "Faqat o‘zingiz boshlagan bo‘lsangiz tasdiqlang. Tasdiqdan keyin brauzerda "
        "shu hisobni o‘chirish so‘rovini yuborish mumkin bo‘ladi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Bu mening hisobim", callback_data=VERIFY + request_id),
        ]]),
    )


@router.callback_query(F.data.startswith(VERIFY))
async def verify_web_account(callback: CallbackQuery, session):
    if not is_account_deletion_event(callback):
        await callback.answer("So‘rovni shaxsiy chatdan yuboring.", show_alert=True)
        return
    try:
        await AccountDeletionService(session, settings).verify_telegram(
            request_id=callback.data[len(VERIFY):], telegram_id=callback.from_user.id)
    except DesktopAuthError:
        await callback.answer("So‘rov eskirgan yoki topilmadi. Web sahifada qayta boshlang.", show_alert=True)
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Hisob tasdiqlandi.")
    await callback.message.answer("Hisob tasdiqlandi. Brauzerdagi HSK AI sahifasiga qaytib yakuniy so‘rovni tasdiqlang.")


@router.message(F.text.regexp(r"^/start(?:@\w+)?\s+account_deletion\s*$"))
async def begin_account_deletion(message: Message):
    if not message.from_user or message.chat.type != "private":
        return
    await message.answer(
        "HSK AI hisobingizni va unga bog‘liq ma’lumotlarni o‘chirishni so‘ramoqchimisiz? "
        "Bu Android, Telegram Mini App va desktop hisobingizga ham ta’sir qiladi. "
        "Tasdiqlasangiz, so‘rovingiz saqlanib 30 kun ichida ko‘rib chiqiladi; ma’lumotlar hozir o‘chirilmaydi. "
        "Tasdiqlangan to‘lovlar va qonuniy hisob-kitob yozuvlari saqlanishi mumkin.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="O‘chirishni so‘rash", callback_data=CONFIRM),
        ]]),
    )


@router.callback_query(F.data == CONFIRM)
async def confirm_account_deletion(callback: CallbackQuery, session):
    user = callback.from_user
    if not user or not callback.message or callback.message.chat.type != "private" \
            or callback.message.chat.id != user.id:
        await callback.answer("So‘rovni shaxsiy chatdan yuboring.", show_alert=True)
        return

    try:
        result = await AccountDeletionService(session, settings).submit_telegram(user.id)
    except Exception:
        logger.error("Failed to persist account deletion request")
        await callback.answer("So‘rov yuborilmadi. Keyinroq qayta urinib ko‘ring.", show_alert=True)
        return
    await notify_deletion_request(callback.bot, settings, result)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("So‘rov qabul qilindi.")
    await callback.message.answer(
        f"Hisobni o‘chirish so‘rovingiz saqlandi. Raqam: {result['request_id']}. "
        "So‘rov 30 kun ichida ko‘rib chiqiladi. Tasdiqlangan to‘lovlar va qonuniy "
        "hisob-kitob yozuvlari mavjud saqlash qoidalariga muvofiq qolishi mumkin."
    )

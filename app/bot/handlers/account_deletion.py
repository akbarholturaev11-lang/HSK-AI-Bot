"""Receive a verified account-deletion request without deleting shared data in chat."""

import logging
from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config import settings

router = Router()
logger = logging.getLogger(__name__)
CONFIRM = "account_deletion:confirm"


@router.message(F.text.regexp(r"^/start(?:@\w+)?\s+account_deletion\s*$"))
async def begin_account_deletion(message: Message):
    if not message.from_user or message.chat.type != "private":
        return
    await message.answer(
        "HSK AI hisobingizni va unga bog‘liq ma’lumotlarni o‘chirishni so‘ramoqchimisiz? "
        "Bu Android, Telegram Mini App va desktop hisobingizga ham ta’sir qiladi. "
        "Tasdiqlasangiz, so‘rovingiz administratorga yuboriladi; ma’lumotlar hozir o‘chirilmaydi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="O‘chirishni so‘rash", callback_data=CONFIRM),
        ]]),
    )


@router.callback_query(F.data == CONFIRM)
async def confirm_account_deletion(callback: CallbackQuery):
    user = callback.from_user
    if not user or not callback.message or callback.message.chat.type != "private" \
            or callback.message.chat.id != user.id:
        await callback.answer("So‘rovni shaxsiy chatdan yuboring.", show_alert=True)
        return

    admin_ids = settings.admin_id_list
    if not admin_ids:
        await callback.answer("Hozir so‘rov yuborilmadi. Keyinroq qayta urinib ko‘ring.", show_alert=True)
        return

    username = f"@{escape(user.username)}" if user.username else "—"
    notice = (
        "🗑 HSK AI hisobini o‘chirish so‘rovi\n"
        f"Telegram ID: <code>{user.id}</code>\n"
        f"Ism: {escape(user.full_name)}\nUsername: {username}\n\n"
        "Shaxsni va obuna/saqlanish majburiyatlarini tekshiring; "
        "tasdiqsiz ma’lumotlarni o‘chirmang."
    )
    delivered = False
    for admin_id in set(admin_ids):
        try:
            await callback.bot.send_message(admin_id, notice, parse_mode="HTML")
            delivered = True
        except Exception:
            logger.exception("Failed to deliver account deletion request to admin")

    if not delivered:
        await callback.answer("So‘rov yuborilmadi. Keyinroq qayta urinib ko‘ring.", show_alert=True)
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("So‘rov qabul qilindi.")
    await callback.message.answer(
        "Hisobni o‘chirish so‘rovingiz administratorga yetkazildi. "
        "Shaxsingiz tekshirilgandan keyin so‘rov ko‘rib chiqiladi."
    )

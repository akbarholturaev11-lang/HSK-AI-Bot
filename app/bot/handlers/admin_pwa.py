"""Telegram private-chat confirmation for standalone HSK AI Admin PWA.

Register before generic /start. This handler does not authenticate browsers:
it can only approve/deny an existing Google-verified DB challenge. Never use
callback data, text or forwarded messages as a source of Telegram identity.
"""

from __future__ import annotations

import logging
import re
from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.exceptions import TelegramBadRequest

from app.admin_api.pwa_bot_approval import (
    preview_admin_pwa_bot_request,
    decide_admin_pwa_bot_request,
)
from app.bot.utils.i18n import t
from app.config import settings
from app.repositories.user_repo import UserRepository

router = Router()
logger = logging.getLogger(__name__)

DEEP_LINK_PREFIX = "admin_pwa_"
_CALLBACK_PREFIX = "admin_pwa:"
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_START_PATTERN = re.compile(rf"^/start(?:@\w+)?\s+{DEEP_LINK_PREFIX}({_UUID})\s*$")
_CALLBACK_PATTERN = re.compile(rf"^{_CALLBACK_PREFIX}(approve|deny):({_UUID})$")


def _private_chat(event: Message | CallbackQuery) -> bool:
    actor = getattr(event, "from_user", None)
    message = event.message if isinstance(event, CallbackQuery) else event
    chat = getattr(message, "chat", None)
    if (getattr(message, "forward_origin", None) is not None
            or getattr(message, "forward_from", None) is not None
            or getattr(message, "forward_sender_name", None) is not None):
        return False
    return bool(actor and chat and not actor.is_bot
                and chat.type == "private" and int(chat.id) == int(actor.id))


def _normalise_locale(raw: str | None) -> str:
    code = str(raw or "").lower().split("-", 1)[0]
    return "tj" if code == "tg" else code if code in ("uz", "ru", "tj") else "ru"


async def _language(db, event: Message | CallbackQuery) -> str:
    fallback = _normalise_locale(getattr(event.from_user, "language_code", None))
    user = await UserRepository(db).get_by_telegram_id(int(event.from_user.id))
    return _normalise_locale(getattr(user, "language", None) or fallback)


def _keyboard(request_id: str, language: str) -> InlineKeyboardMarkup:
    approve = f"{_CALLBACK_PREFIX}approve:{request_id}"
    deny = f"{_CALLBACK_PREFIX}deny:{request_id}"
    # Telegram imposes a 64-byte callback_data limit.
    assert len(approve.encode("ascii")) <= 64 and len(deny.encode("ascii")) <= 64
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("bot.adminPwa.approve", language), callback_data=approve)],
        [InlineKeyboardButton(text=t("bot.adminPwa.deny", language), callback_data=deny)],
    ])


@router.message(F.text.regexp(_START_PATTERN.pattern))
async def begin_admin_pwa_approval(message: Message, session) -> None:
    if not bool(getattr(settings, "ADMIN_PWA_ENABLED", False)) or not _private_chat(message):
        return
    match = _START_PATTERN.fullmatch(message.text or "")
    if match is None:
        return
    request_id = match.group(1)
    try:
        preview = await preview_admin_pwa_bot_request(
            session, bot_event=message, request_id=request_id,
            settings_obj=settings,
        )
        language = await _language(session, message)
    except Exception:
        logger.exception("Admin PWA Telegram preview unavailable")
        await message.answer(t("bot.adminPwa.unavailable", _normalise_locale(
            getattr(message.from_user, "language_code", None))))
        return
    if preview is None:
        await message.answer(t("bot.adminPwa.invalid", language))
        return
    # Code is an 8-digit deterministic comparison value, not a bearer secret.
    # The Google/browser proof never enters the Telegram message.
    await message.answer(
        t("bot.adminPwa.confirm", language, code=escape(preview.pairing_code)),
        parse_mode="HTML",
        reply_markup=_keyboard(preview.request_id, language),
    )


@router.callback_query(F.data.regexp(_CALLBACK_PATTERN.pattern))
async def decide_admin_pwa_approval(callback: CallbackQuery, session) -> None:
    if not bool(getattr(settings, "ADMIN_PWA_ENABLED", False)):
        await callback.answer()
        return
    if not _private_chat(callback):
        await callback.answer(t(
            "bot.adminPwa.privateOnly",
            _normalise_locale(getattr(callback.from_user, "language_code", None)),
        ), show_alert=True)
        return
    match = _CALLBACK_PATTERN.fullmatch(callback.data or "")
    if match is None:
        await callback.answer()
        return
    action, request_id = match.groups()
    try:
        language = await _language(session, callback)
        accepted = await decide_admin_pwa_bot_request(
            session, bot_event=callback, request_id=request_id,
            approve=(action == "approve"), settings_obj=settings,
        )
    except Exception:
        logger.exception("Admin PWA Telegram decision unavailable")
        await callback.answer(t("bot.adminPwa.unavailable", _normalise_locale(
            getattr(callback.from_user, "language_code", None))), show_alert=True)
        return
    key = "approved" if action == "approve" else "denied"
    if not accepted:
        await callback.answer(t("bot.adminPwa.invalid", language), show_alert=True)
        return
    text = t("bot.adminPwa." + key, language)
    await callback.answer(text)
    # Decision is committed before the reply. Telegram Bot API cannot force the
    # phone's default browser to open after an inline callback. Provide a
    # same-origin return link; the existing browser observes status on return.
    if isinstance(callback.message, Message):
        try:
            return_keyboard = (InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text=t("bot.adminPwa.openBrowser", language),
                    url="https://hskai.app/admin/",
                ),
            ]]) if action == "approve" else None)
            await callback.message.edit_text(
                text, parse_mode="HTML", reply_markup=return_keyboard,
            )
        except TelegramBadRequest:
            logger.info("Admin PWA Bot approval message cannot be edited")

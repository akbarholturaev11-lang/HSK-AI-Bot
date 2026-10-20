"""Receive a verified account-deletion request without deleting shared data in chat."""

import logging
import re
import uuid

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config import settings
from app.api.account_deletion import notify_deletion_request
from app.repositories.user_repo import UserRepository
from app.services.account_deletion_service import AccountDeletionService
from app.services.desktop_auth_service import DesktopAuthError
from app.bot.utils.i18n import t

router = Router()
logger = logging.getLogger(__name__)
CONFIRM = "account_deletion:confirm"
VERIFY = "account_deletion:verify:"


def _normalize_language(value):
    if not isinstance(value, str):
        return "ru"
    language = value.lower().split("-", 1)[0]
    if language == "tg":
        language = "tj"
    return language if language in {"uz", "ru", "tj"} else "ru"


async def _account_deletion_language(session, telegram_id, fallback=None):
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    return _normalize_language(getattr(user, "language", None) or fallback)


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
async def begin_web_verification(message: Message, session):
    if not message.from_user or message.chat.type != "private" or message.chat.id != message.from_user.id:
        return
    request_id = str(uuid.UUID(message.text.strip().rsplit("delete_", 1)[1]))
    lang = await _account_deletion_language(
        session, message.from_user.id, getattr(message.from_user, "language_code", None))
    await message.answer(
        t("common.bot.accountDeletion.webStarted", lang),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=t("common.bot.accountDeletion.webConfirmButton", lang),
                callback_data=VERIFY + request_id,
            ),
        ]]),
    )


@router.callback_query(F.data.startswith(VERIFY))
async def verify_web_account(callback: CallbackQuery, session):
    if not is_account_deletion_event(callback):
        lang = _normalize_language(getattr(callback.from_user, "language_code", None))
        await callback.answer(t("common.bot.accountDeletion.privateChatOnly", lang), show_alert=True)
        return
    lang = await _account_deletion_language(
        session, callback.from_user.id, getattr(callback.from_user, "language_code", None))
    try:
        await AccountDeletionService(session, settings).verify_telegram(
            request_id=callback.data[len(VERIFY):], telegram_id=callback.from_user.id)
    except DesktopAuthError:
        await callback.answer(t("common.bot.accountDeletion.expired", lang), show_alert=True)
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer(t("common.bot.accountDeletion.accountVerified", lang))
    await callback.message.answer(t("common.bot.accountDeletion.returnToWeb", lang))


@router.message(F.text.regexp(r"^/start(?:@\w+)?\s+account_deletion\s*$"))
async def begin_account_deletion(message: Message, session):
    if not message.from_user or message.chat.type != "private":
        return
    lang = await _account_deletion_language(
        session, message.from_user.id, getattr(message.from_user, "language_code", None))
    await message.answer(
        t("common.bot.accountDeletion.prompt", lang),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=t("common.bot.accountDeletion.submitButton", lang), callback_data=CONFIRM),
        ]]),
    )


@router.callback_query(F.data == CONFIRM)
async def confirm_account_deletion(callback: CallbackQuery, session):
    user = callback.from_user
    if not user or not callback.message or callback.message.chat.type != "private" \
            or callback.message.chat.id != user.id:
        lang = _normalize_language(getattr(user, "language_code", None))
        await callback.answer(t("common.bot.accountDeletion.privateChatOnly", lang), show_alert=True)
        return

    lang = await _account_deletion_language(
        session, user.id, getattr(user, "language_code", None))

    try:
        result = await AccountDeletionService(session, settings).submit_telegram(user.id)
    except Exception:
        logger.error("Failed to persist account deletion request")
        await callback.answer(t("common.bot.accountDeletion.submitFailed", lang), show_alert=True)
        return
    await notify_deletion_request(callback.bot, settings, result)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer(t("common.bot.accountDeletion.requestAccepted", lang))
    await callback.message.answer(t(
        "common.bot.accountDeletion.requestSaved", lang,
        requestId=result["request_id"],
    ))

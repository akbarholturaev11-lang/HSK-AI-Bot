"""Handing the Android APK to a learner, inside the chat they already have.

There is no Play listing and no download page yet, so this chat is the whole
distribution channel. The bot re-sends one stored `file_id`: Telegram already
holds the bytes, so the learner gets the file at CDN speed, we serve nothing,
and the same upload can be handed out to everyone without a second copy
drifting out of sync with the first.
"""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.utils.i18n import t
from app.repositories.user_repo import UserRepository
from app.services.android_release_service import AndroidReleaseService
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService


logger = logging.getLogger(__name__)
router = Router()

ANDROID_APP_CALLBACK = "android_app:get"


async def send_android_app(
    bot: Bot,
    chat_id: int,
    telegram_id: int,
    session,
    *,
    source: str,
    track: bool = True,
) -> bool:
    """Send the published APK, or explain why there is nothing to send.

    Returns whether the file actually reached the chat, so that a caller
    answering a callback query can say something truthful about it.

    `track=False` is for the admin checking their own upload. These two events
    are the only measurement this channel has — nothing of ours serves the
    file — so an admin testing a release must not show up in it as demand.
    """

    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    lang = getattr(user, "language", None) or "ru"

    analytics = CourseMiniAppAnalyticsService(session)
    if track:
        await analytics.record_server_event(
            event_name="android_apk_requested",
            telegram_id=telegram_id,
            user_id=getattr(user, "id", None),
            source=source,
        )

    release = await AndroidReleaseService(session).current()
    if not release:
        await session.commit()
        await bot.send_message(
            chat_id,
            t("android_app_unavailable", lang),
            parse_mode="HTML",
        )
        return False

    await bot.send_message(
        chat_id,
        t(
            "android_app_intro",
            lang,
            version=release.version_text,
            size=release.size_text,
        ),
        parse_mode="HTML",
    )

    try:
        await bot.send_document(
            chat_id,
            release.file_id,
            caption=t("android_app_caption", lang),
            parse_mode="HTML",
        )
    except Exception:
        # A stored file_id can stop resolving — the upload was deleted, or the
        # bot token changed. The learner must not be left staring at an intro
        # with no file under it.
        logger.exception("Failed to send the Android APK to %s", telegram_id)
        await session.commit()
        await bot.send_message(chat_id, t("android_app_failed", lang))
        return False

    if track:
        await analytics.record_server_event(
            event_name="android_apk_sent",
            telegram_id=telegram_id,
            user_id=getattr(user, "id", None),
            source=source,
            payload={
                "version_name": release.version_name,
                "version_code": release.version_code,
                "file_size": release.file_size,
            },
        )
    await session.commit()
    return True


@router.message(Command("android"))
async def android_command(message: Message, session):
    await send_android_app(
        message.bot,
        message.chat.id,
        message.from_user.id,
        session,
        source="bot_command",
    )


@router.callback_query(F.data == ANDROID_APP_CALLBACK)
async def android_from_button(callback: CallbackQuery, session):
    await callback.answer()
    await send_android_app(
        callback.bot,
        reply_chat_id(callback),
        callback.from_user.id,
        session,
        source="bot_profile",
    )


def reply_chat_id(callback: CallbackQuery) -> int:
    """Where the file should land.

    Telegram stops attaching the message to a callback once it is old enough,
    and the profile keyboard is exactly the kind of message a learner scrolls
    back to weeks later. Falling back to their own id keeps the button working
    instead of failing on an attribute that is simply no longer there.
    """

    message = callback.message
    chat = getattr(message, "chat", None) if message is not None else None
    return getattr(chat, "id", None) or callback.from_user.id

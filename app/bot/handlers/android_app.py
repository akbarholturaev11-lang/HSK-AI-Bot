"""Handing the Android APK to a learner, inside the chat they already have.

There is no Play listing and no download page yet, so this chat is the whole
distribution channel. The bot re-sends one stored `file_id`: Telegram already
holds the bytes, so the learner gets the file at CDN speed, we serve nothing,
and the same upload can be handed out to everyone without a second copy
drifting out of sync with the first.
"""

import logging

import httpx
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from app.bot.utils.i18n import t
from app.repositories.user_repo import UserRepository
from app.services.android_release_service import AndroidReleaseService
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService


logger = logging.getLogger(__name__)
router = Router()

ANDROID_APP_CALLBACK = "android_app:get"

#: Telegram refuses documents larger than this from a bot, so there is no point
#: pulling more than this into memory either.
MAX_APK_BYTES = 50 * 1024 * 1024
APK_FETCH_TIMEOUT_SECONDS = 60.0


async def _fetch_apk(url: str, expected_size: int) -> bytes | None:
    """Read the APK ourselves rather than asking Telegram to fetch it.

    Telegram will download a URL given to `sendDocument`, and that is one more
    party that has to be able to reach object storage — behind Cloudflare, from
    their network, with their client. When it cannot, the learner sees only
    "the file could not be sent" and the reason lives in a log that has already
    rotated. Reading it here costs one download per release, after which the
    file_id is cached and nobody fetches anything again.
    """

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(APK_FETCH_TIMEOUT_SECONDS),
            follow_redirects=True,
        ) as client:
            async with client.stream("GET", url) as response:
                if response.status_code != 200:
                    logger.warning(
                        "APK fetch returned HTTP %s for %s",
                        response.status_code,
                        url,
                    )
                    return None
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_APK_BYTES:
                        logger.warning("APK at %s is larger than we will send", url)
                        return None
    except Exception:
        logger.exception("APK could not be fetched from %s", url)
        return None

    if not body:
        return None
    if expected_size and len(body) != expected_size:
        # The published release and the stored one disagree. Sending it anyway
        # would hand out a build nobody measured.
        logger.warning(
            "APK at %s is %s bytes, the release says %s",
            url,
            len(body),
            expected_size,
        )
        return None
    return bytes(body)


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

    releases = AndroidReleaseService(session)
    release = await releases.serve()
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

    # A file_id when Telegram already holds this build; otherwise the bytes,
    # read here. That second case happens exactly once per release — what
    # Telegram gives back is cached below, so the release workflow never has to
    # know this chat exists.
    if release.file_id:
        document = release.file_id
    elif release.download_url:
        # Logged at INFO on purpose: this should happen once per release. If
        # it appears for every learner, the file_id is not being cached and
        # each of them is costing an upload.
        logger.info(
            "Reading the Android APK once for version %s", release.version_text
        )
        blob = await _fetch_apk(release.download_url, release.size)
        if blob is None:
            await session.commit()
            await bot.send_message(chat_id, t("android_app_failed", lang))
            return False
        document = BufferedInputFile(blob, filename=release.file_name)
    else:
        await session.commit()
        await bot.send_message(chat_id, t("android_app_failed", lang))
        return False

    try:
        sent = await bot.send_document(
            chat_id,
            document,
            caption=t("android_app_caption", lang),
            parse_mode="HTML",
        )
    except Exception:
        # A stored file_id can stop resolving. The learner must not be left
        # staring at an intro with no file under it.
        logger.exception("Failed to send the Android APK to %s", telegram_id)
        await session.commit()
        await bot.send_message(chat_id, t("android_app_failed", lang))
        return False

    if not release.file_id and release.version_code is not None:
        new_file_id = getattr(getattr(sent, "document", None), "file_id", None)
        if new_file_id:
            try:
                await releases.remember_file_id(
                    version_code=release.version_code,
                    file_id=str(new_file_id),
                )
            except Exception:
                # The learner has their file; only the next one pays for this.
                logger.exception("Telegram's copy of the APK could not be cached")

    if track:
        await analytics.record_server_event(
            event_name="android_apk_sent",
            telegram_id=telegram_id,
            user_id=getattr(user, "id", None),
            source=source,
            payload={
                "version_name": release.version_name,
                "version_code": release.version_code,
                "file_size": release.size,
                "release_source": release.source,
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

import logging
import time
from dataclasses import dataclass

import aiohttp

from app.config import settings


logger = logging.getLogger(__name__)

_DRAFT_METHOD = "sendMessageDraft"
_DRAFT_TEXT_LIMIT = 512
_HTTP_TIMEOUT_SECONDS = 8
_MIN_UPDATE_INTERVAL_SECONDS = 1.2
_MAX_UPDATES_PER_REPLY = 4
_ACTIVE_DRAFTS: dict[int, "MessageDraftState"] = {}


@dataclass
class MessageDraftState:
    chat_id: int
    using_draft: bool = False
    last_update_at: float = 0.0
    update_count: int = 0
    max_updates: int = _MAX_UPDATES_PER_REPLY
    min_update_interval: float = _MIN_UPDATE_INTERVAL_SECONDS


def is_message_draft_enabled() -> bool:
    return bool(getattr(settings, "ENABLE_MESSAGE_DRAFTS", False))


def _preview_text(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return "AI is preparing a reply..."
    return text[:_DRAFT_TEXT_LIMIT]


async def _send_library_draft(bot, chat_id: int, preview_text: str) -> bool:
    method = getattr(bot, "send_message_draft", None) or getattr(bot, "sendMessageDraft", None)
    if not callable(method):
        return False
    await method(chat_id=chat_id, text=preview_text)
    return True


async def _send_raw_draft(bot, chat_id: int, preview_text: str) -> None:
    token = getattr(bot, "token", "")
    if not token:
        raise RuntimeError("Bot token is not available for raw sendMessageDraft")

    timeout = aiohttp.ClientTimeout(total=_HTTP_TIMEOUT_SECONDS)
    async with aiohttp.ClientSession(timeout=timeout) as http:
        async with http.post(
            f"https://api.telegram.org/bot{token}/{_DRAFT_METHOD}",
            json={"chat_id": chat_id, "text": preview_text},
        ) as response:
            try:
                payload = await response.json(content_type=None)
            except Exception:
                payload = {"ok": False, "description": await response.text()}

            if response.status >= 400 or not payload.get("ok"):
                description = str(payload.get("description") or response.status)
                raise RuntimeError(f"sendMessageDraft failed: {description[:160]}")


async def _send_message_draft(bot, chat_id: int, preview_text: str) -> None:
    text = _preview_text(preview_text)
    if await _send_library_draft(bot, chat_id, text):
        return
    await _send_raw_draft(bot, chat_id, text)


async def _use_typing_fallback(bot, chat_id: int) -> None:
    if bot is None:
        logger.warning("typing_fallback_used_failed", extra={"chat_id": chat_id})
        return

    try:
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        logger.info("typing_fallback_used", extra={"chat_id": chat_id})
    except Exception:
        logger.exception("typing_fallback_used_failed", extra={"chat_id": chat_id})


async def send_draft_or_fallback(
    bot,
    chat_id: int,
    preview_text: str,
    *,
    source_message=None,
    fallback_mode: str = "qa",
    seed: int | None = None,
    max_updates: int = _MAX_UPDATES_PER_REPLY,
    min_update_interval: float = _MIN_UPDATE_INTERVAL_SECONDS,
) -> MessageDraftState:
    state = MessageDraftState(
        chat_id=chat_id,
        max_updates=max_updates,
        min_update_interval=min_update_interval,
    )
    _ACTIVE_DRAFTS[chat_id] = state

    if is_message_draft_enabled():
        try:
            await _send_message_draft(bot, chat_id, preview_text)
            state.using_draft = True
            state.last_update_at = time.monotonic()
            logger.info("message_draft_sent", extra={"chat_id": chat_id})
            return state
        except Exception:
            logger.exception("message_draft_failed", extra={"chat_id": chat_id})

    await _use_typing_fallback(bot, chat_id)
    return state


async def update_draft_or_fallback(bot, chat_id: int, preview_text: str) -> bool:
    state = _ACTIVE_DRAFTS.get(chat_id)
    if not state:
        return False

    now = time.monotonic()
    if state.update_count >= state.max_updates:
        return False
    if state.last_update_at and now - state.last_update_at < state.min_update_interval:
        return False

    if state.using_draft and is_message_draft_enabled():
        try:
            await _send_message_draft(bot, chat_id, preview_text)
            state.update_count += 1
            state.last_update_at = now
            logger.info("message_draft_updated", extra={"chat_id": chat_id})
            return True
        except Exception:
            logger.exception("message_draft_failed", extra={"chat_id": chat_id})
            state.using_draft = False
            await _use_typing_fallback(bot, chat_id)
            return False

    await _use_typing_fallback(bot, chat_id)
    state.update_count += 1
    state.last_update_at = now
    return True


async def finish_draft_if_needed(bot=None, chat_id: int | None = None) -> None:
    if chat_id is None:
        return
    _ACTIVE_DRAFTS.pop(chat_id, None)

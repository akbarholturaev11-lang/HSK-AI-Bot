from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.enums import ChatType
from aiogram.types import Message

from app.bot.utils.i18n import t
from app.bot.utils.workflow_message import delete_message_safely


MENU_BUTTON_TEXT_KEYS = (
    "menu_start_lesson",
    "menu_profile",
    "menu_subscription",
    "menu_invite",
    "menu_partner",
    "menu_help",
    "menu_course_mode",
    "course_settings_button",
    "course_progress",
    "course_reread_button",
    "course_reminder_set_button",
    "course_back_to_qa_button",
)
MENU_BUTTON_TEXTS = {
    t(key, lang)
    for lang in ("tj", "ru", "uz")
    for key in MENU_BUTTON_TEXT_KEYS
}


def _is_cleanup_message(message: Message) -> bool:
    if message.chat.type != ChatType.PRIVATE:
        return False

    text = (message.text or "").strip()
    if not text:
        return False

    return text.startswith("/") or text in MENU_BUTTON_TEXTS


class CommandCleanupMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        result = await handler(event, data)

        should_delete = (
            isinstance(event, Message)
            and result is not UNHANDLED
            and _is_cleanup_message(event)
        )
        if should_delete:
            await delete_message_safely(event)

        return result

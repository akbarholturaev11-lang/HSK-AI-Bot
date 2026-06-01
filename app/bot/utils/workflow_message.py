from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message


REMINDER_PANEL_CHAT_ID = "reminder_panel_chat_id"
REMINDER_PANEL_MSG_ID = "reminder_panel_msg_id"


async def delete_message_safely(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        pass


async def remember_workflow_message(
    state: FSMContext,
    message: Message,
    *,
    chat_id_key: str,
    message_id_key: str,
) -> None:
    await state.update_data(
        **{
            chat_id_key: message.chat.id,
            message_id_key: message.message_id,
        }
    )


async def edit_callback_workflow_message(
    callback: CallbackQuery,
    state: FSMContext,
    text: str,
    *,
    chat_id_key: str,
    message_id_key: str,
    reply_markup=None,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = False,
) -> Message | None:
    if not callback.message:
        return None

    try:
        edited = await callback.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
        )
        panel = edited if isinstance(edited, Message) else callback.message
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            panel = callback.message
        else:
            panel = await callback.message.answer(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
    except Exception:
        panel = await callback.message.answer(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
        )

    await remember_workflow_message(
        state,
        panel,
        chat_id_key=chat_id_key,
        message_id_key=message_id_key,
    )
    return panel


async def edit_stored_workflow_message(
    message: Message,
    state: FSMContext,
    text: str,
    *,
    chat_id_key: str,
    message_id_key: str,
    reply_markup=None,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = False,
) -> None:
    data = await state.get_data()
    chat_id = data.get(chat_id_key)
    message_id = data.get(message_id_key)
    if chat_id and message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
            return
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc).lower():
                return
        except Exception:
            pass

    panel = await message.answer(
        text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
        disable_web_page_preview=disable_web_page_preview,
    )
    await remember_workflow_message(
        state,
        panel,
        chat_id_key=chat_id_key,
        message_id_key=message_id_key,
    )

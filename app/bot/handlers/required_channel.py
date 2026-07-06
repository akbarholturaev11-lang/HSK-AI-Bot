from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.utils.i18n import t
from app.bot.middlewares.required_channel import (
    FORCE_SUB_ACTION_OPEN_COURSE,
    FORCE_SUB_ACTION_OPEN_FREE_QA,
    PENDING_FORCE_SUB_ACTION,
    PENDING_FORCE_SUB_MESSAGE_ID,
    PENDING_FORCE_SUB_PAYLOAD,
    PENDING_FORCE_SUB_TEXT,
)
from app.repositories.user_repo import UserRepository
from app.services.required_channel_service import RequiredChannelService


router = Router()


class _MessageEditResponder:
    def __init__(self, message):
        self._message = message
        self._used_edit = False

    async def __call__(self, text: str, **kwargs):
        if self._message and not self._used_edit:
            self._used_edit = True
            try:
                return await self._message.edit_text(text, **kwargs)
            except Exception:
                pass
        return await self._message.answer(text, **kwargs)


class _ForceSubTextProxy:
    def __init__(self, callback: CallbackQuery, text: str, message_id: int | None):
        self._message = callback.message
        self.text = text
        self.from_user = callback.from_user
        self.message_id = message_id or callback.message.message_id

    def __getattr__(self, name):
        return getattr(self._message, name)


@router.callback_query(F.data == "force_sub:check")
async def force_sub_check(callback: CallbackQuery, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "ru"
    service = RequiredChannelService(session)
    missing = await service.missing_channels(callback.bot, callback.from_user.id)
    if missing:
        await callback.answer(t("force_sub_still_missing", lang), show_alert=True)
        if callback.message:
            await callback.message.edit_text(
                service.build_required_text(missing, lang),
                reply_markup=service.build_required_keyboard(missing, lang),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        return

    await callback.answer(t("force_sub_unlocked_alert", lang), show_alert=True)
    if user:
        user.last_active_at = datetime.now(timezone.utc)
        await session.flush()

    data = await state.get_data()
    pending_text = (data.get(PENDING_FORCE_SUB_TEXT) or "").strip()
    pending_message_id = data.get(PENDING_FORCE_SUB_MESSAGE_ID)
    pending_action = data.get(PENDING_FORCE_SUB_ACTION)
    pending_payload = data.get(PENDING_FORCE_SUB_PAYLOAD) or {}
    if not isinstance(pending_payload, dict):
        pending_payload = {}
    await state.update_data(
        **{
            PENDING_FORCE_SUB_TEXT: None,
            PENDING_FORCE_SUB_MESSAGE_ID: None,
            PENDING_FORCE_SUB_ACTION: None,
            PENDING_FORCE_SUB_PAYLOAD: None,
        }
    )

    if pending_text and callback.message:
        try:
            await callback.message.delete()
        except Exception:
            pass

        from app.bot.handlers.messages import handle_text_message

        await handle_text_message(
            _ForceSubTextProxy(callback, pending_text, pending_message_id),
            state,
            session,
        )
        return

    if pending_action and callback.message:
        respond = _MessageEditResponder(callback.message)
        if pending_action == FORCE_SUB_ACTION_OPEN_COURSE:
            from app.bot.handlers.course import show_course_level_choice

            # Kanalga a'zo bo'lgach kurs rejimi davom etadi: avval HSK darajasi
            # so'raladi, keyin process_level 1-darsga olib o'tadi (izchil oqim).
            await show_course_level_choice(
                respond=respond,
                state=state,
                lang=lang,
            )
            return

        if pending_action == FORCE_SUB_ACTION_OPEN_FREE_QA:
            from app.bot.handlers.course import show_free_qa_level_choice

            await show_free_qa_level_choice(
                respond=respond,
                state=state,
                lang=lang,
            )
            return

    if user and getattr(user, "learning_mode", "qa") == "course" and callback.message:
        from app.bot.handlers.course import send_course_miniapp_entry

        await send_course_miniapp_entry(
            session=session,
            telegram_id=callback.from_user.id,
            respond=_MessageEditResponder(callback.message),
            state=state,
            source="required_channel_course",
        )
        return

    if callback.message:
        await callback.message.edit_text(t("force_sub_unlocked_text", lang), parse_mode="HTML")

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import COURSE_MODE_ENABLED
from app.repositories.user_repo import UserRepository
from app.services.course_engine_service import CourseEngineService
from app.bot.keyboards.subscription import subscription_miniapp_keyboard
from app.bot.keyboards.course import reminder_time_keyboard
from app.bot.keyboards.help import help_contact_keyboard
from app.bot.utils.i18n import t
from app.services.help_settings_service import build_help_text
from app.services.support_contact_service import get_admin_contact_url
from app.bot.utils.workflow_message import (
    REMINDER_PANEL_CHAT_ID,
    REMINDER_PANEL_MSG_ID,
    delete_message_safely,
    edit_stored_workflow_message,
)


router = Router()


async def _clear_voice_mode(user, session, state: FSMContext | None = None) -> None:
    if state:
        await state.update_data(pending_voice_transcript=None, pending_voice_message_id=None)
    if user and (getattr(user, "voice_mode", "none") or "none") != "none":
        user.voice_mode = "none"
        await session.commit()


@router.callback_query(F.data.startswith("promo:action:"))
async def handle_promo_action_callback(callback: CallbackQuery, state: FSMContext, session):
    action = callback.data.split(":")[-1]
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "ru"

    if not user:
        await callback.answer()
        await callback.message.answer(t("access_start_first", lang))
        return

    await state.clear()
    await _clear_voice_mode(user, session, state)

    if action == "profile":
        from app.bot.handlers.commands import (
            _profile_referral_count,
            _profile_reminder_text,
            _profile_text,
            profile_menu_keyboard,
        )

        referral_total = await _profile_referral_count(session, user)
        reminder_text = await _profile_reminder_text(session, user, lang)
        await callback.answer()
        await callback.message.answer(
            _profile_text(user, lang, referral_total, reminder_text),
            parse_mode="HTML",
            reply_markup=profile_menu_keyboard(lang, user),
        )
        return

    if action == "partner":
        from app.bot.handlers.partner import _render_partner_text

        text, keyboard = await _render_partner_text(session, callback.from_user.id)
        await session.commit()
        await callback.answer()
        await callback.message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    if action == "course":
        from app.bot.handlers.course import run_course_entry_flow

        await callback.answer()
        if not COURSE_MODE_ENABLED:
            msg_map = {
                "uz": "🚧 Kurs rejimi hozircha ishlab chiqilmoqda.",
                "ru": "🚧 Режим курса сейчас в разработке.",
                "tj": "🚧 Реҷаи курс ҳоло дар навсози аст.",
            }
            await callback.message.answer(msg_map.get(lang, msg_map["ru"]))
            return
        await run_course_entry_flow(
            session=session,
            telegram_id=callback.from_user.id,
            respond=callback.message.answer,
            show_menu=True,
        )
        return

    if action == "reminder":
        engine = CourseEngineService(session)
        _, progress, error_key = await engine.get_or_create_progress(callback.from_user.id)
        await callback.answer()
        if error_key or not progress:
            await callback.message.answer(t(error_key or "course_no_lesson_found", lang))
            return

        await engine.progress_repo.set_waiting_for(progress, "reminder_setup")
        await session.commit()
        sent = await callback.message.answer(
            t("course_reminder_setup_msg", lang),
            reply_markup=reminder_time_keyboard(lang),
        )
        await state.update_data(
            **{
                REMINDER_PANEL_CHAT_ID: sent.chat.id,
                REMINDER_PANEL_MSG_ID: sent.message_id,
            }
        )
        return

    if action == "help":
        contact_url = await get_admin_contact_url(session)
        await callback.answer()
        await callback.message.answer(
            await build_help_text(session, lang),
            reply_markup=help_contact_keyboard(lang, contact_url),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    await callback.answer("Button eskirgan yoki noto'g'ri.", show_alert=True)

# ──────────────────────────────────────────────
# QA rejim menyusi — barcha tugmalar handleri
# ──────────────────────────────────────────────

@router.message(F.text.in_([
    "💳 Обуна",
    "💳 Подписка",
    "💳 Obuna",
]))
async def handle_subscription_button(message: Message, state: FSMContext, session):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user:
        return

    lang = user.language if user.language else "ru"
    await _clear_voice_mode(user, session, state)

    await message.answer(
        t("subscription_miniapp_entry_text", lang),
        reply_markup=subscription_miniapp_keyboard(lang, source="menu_subscription", mode="subscription"),
        parse_mode="HTML",
    )


@router.message(F.text.in_([
    "👤 Профил",
    "👤 Профиль",
    "👤 Profil",
]))
async def handle_profile_button(message: Message, state: FSMContext, session):
    from app.bot.handlers.commands import (
        _profile_referral_count,
        _profile_reminder_text,
        _profile_text,
        profile_menu_keyboard,
    )
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        return
    lang = user.language if user.language else "ru"
    await _clear_voice_mode(user, session, state)
    referral_total = await _profile_referral_count(session, user)
    reminder_text = await _profile_reminder_text(session, user, lang)
    await message.answer(
        _profile_text(user, lang, referral_total, reminder_text),
        parse_mode="HTML",
        reply_markup=profile_menu_keyboard(lang, user),
    )


@router.message(F.text.in_([
    "🤝 Ҳамкорӣ",
    "🤝 Партнёрство",
    "🤝 Hamkorlik",
]))
async def handle_partner_button(message: Message, state: FSMContext, session):
    from app.bot.handlers.partner import open_partner_for_message

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        return
    await _clear_voice_mode(user, session, state)
    await open_partner_for_message(message, state, session)


@router.message(F.text.in_([
    "❓ Ёрдам",
    "❓ Помощь",
    "❓ Yordam",
]))
async def handle_help_button(message: Message, state: FSMContext, session):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    lang = user.language if user and user.language else "ru"
    await _clear_voice_mode(user, session, state)
    contact_url = await get_admin_contact_url(session)
    await message.answer(
        await build_help_text(session, lang),
        reply_markup=help_contact_keyboard(lang, contact_url),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@router.message(F.text.in_([
    "⏰ Вақти ёдраскунак",
    "⏰ Напоминание",
    "⏰ Eslatma vaqti",
]))
async def handle_reminder_time_button(message: Message, state: FSMContext, session):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        return

    lang = user.language if user.language else "ru"
    await _clear_voice_mode(user, session, state)
    engine = CourseEngineService(session)
    _, progress, error_key = await engine.get_or_create_progress(message.from_user.id)
    if error_key or not progress:
        await delete_message_safely(message)
        await edit_stored_workflow_message(
            message,
            state,
            t(error_key or "course_no_lesson_found", lang),
            chat_id_key=REMINDER_PANEL_CHAT_ID,
            message_id_key=REMINDER_PANEL_MSG_ID,
        )
        return

    await engine.progress_repo.set_waiting_for(progress, "reminder_setup")
    await session.commit()
    await delete_message_safely(message)
    await edit_stored_workflow_message(
        message,
        state,
        t("course_reminder_setup_msg", lang),
        chat_id_key=REMINDER_PANEL_CHAT_ID,
        message_id_key=REMINDER_PANEL_MSG_ID,
        reply_markup=reminder_time_keyboard(lang),
    )


@router.message(F.text.in_([
    "📚 Режими курс",
    "📚 Режим курса",
    "📚 Kurs rejimi",
]))
async def handle_course_mode_button(message: Message, state: FSMContext, session):
    from app.bot.handlers.course import run_course_entry_flow
    from app.config import COURSE_MODE_ENABLED
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    lang = user.language if user and user.language else "ru"
    await _clear_voice_mode(user, session, state)

    if not COURSE_MODE_ENABLED:
        msg_map = {
            "uz": "🚧 Kurs rejimi hozircha ishlab chiqilmoqda.",
            "ru": "🚧 Режим курса сейчас в разработке.",
            "tj": "🚧 Реҷаи курс ҳоло дар навсози аст.",
        }
        await message.answer(msg_map.get(lang, msg_map["ru"]))
        return

    await run_course_entry_flow(
        session=session,
        telegram_id=message.from_user.id,
        respond=message.answer,
        show_menu=True,
    )

import asyncio
import time
from html import escape
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.config import settings
from app.repositories.user_repo import UserRepository
from app.bot.fsm.admin_broadcast import BroadcastStates
from app.bot.keyboards.admin_broadcast import broadcast_panel_keyboard, broadcast_confirm_keyboard
from app.services.broadcast_translation_service import (
    BroadcastTranslationService,
    SUPPORTED_BROADCAST_LANGUAGES,
    broadcast_languages_or_all,
    encode_localized_broadcast_text,
    localized_broadcast_text_for_language,
    normalize_broadcast_languages,
)
from app.bot.utils.workflow_message import (
    delete_message_safely,
    edit_callback_workflow_message,
    edit_stored_workflow_message,
)

router = Router()
_PANEL_CHAT_ID = "panel_chat_id"
_PANEL_MSG_ID = "panel_msg_id"
_LANG_LABELS = {"tj": "TJ", "uz": "UZ", "ru": "RU"}


def _is_admin(user_id: int) -> bool:
    admin_ids = [int(x.strip()) for x in settings.ADMIN_IDS.split(",") if x.strip()]
    return user_id in admin_ids


def _panel_text(
    target_languages: Optional[list[str]],
    status_filter: Optional[str],
    level_filter: Optional[str],
    mode_filter: Optional[str] = None,
    payment_status_filter: Optional[str] = None,
    payment_method_filter: Optional[str] = None,
    plan_filter: Optional[str] = None,
    discount_filter: Optional[str] = None,
    course_promo_filter: Optional[str] = None,
    activity_filter: Optional[str] = None,
) -> str:
    labels = {
        "status": {
            "free": "Bepul",
            "trial": "Sinov",
            "active": "Faol",
            "expired": "Tugagan",
            "blocked": "Blok",
        },
        "level": {"beginner": "Boshlang'ich", "hsk1": "HSK1", "hsk2": "HSK2", "hsk3": "HSK3", "hsk4": "HSK4"},
        "mode": {"qa": "Savol-javob", "course": "Kurs"},
        "payment_status": {"none": "Yo'q", "pending": "Kutilmoqda", "approved": "Tasdiqlangan", "rejected": "Rad etilgan"},
        "payment_method": {"visa": "Visa", "alipay": "Alipay", "wechat": "WeChat"},
        "plan": {"10_days": "10 kun", "1_month": "1 oy"},
        "discount": {"eligible": "Chegirma bor", "used": "Chegirma ishlatilgan", "none": "Chegirma yo'q"},
        "promo": {"sent": "Promo yuborilgan", "not_sent": "Promo yuborilmagan"},
        "activity": {"active_7d": "7 kunda aktiv", "inactive_7d": "7 kunda sovuq", "new_7d": "7 kunda yangi"},
    }

    def label(group: str, value: Optional[str]) -> str:
        if not value:
            return "Hammasi"
        return labels[group].get(value, value)

    def languages_label(values: Optional[list[str]]) -> str:
        selected = normalize_broadcast_languages(values)
        if not selected:
            return "Hammasi"
        return ", ".join(_LANG_LABELS[item] for item in selected)

    return (
        "📢 <b>Broadcast paneli</b>\n\n"
        "<blockquote>"
        f"🌐 Til: <b>{languages_label(target_languages)}</b>\n"
        f"👤 Status: <b>{label('status', status_filter)}</b>\n"
        f"📚 Daraja: <b>{label('level', level_filter)}</b>\n"
        f"🎯 Rejim: <b>{label('mode', mode_filter)}</b>\n"
        f"💳 To'lov statusi: <b>{label('payment_status', payment_status_filter)}</b>\n"
        f"🏦 To'lov usuli: <b>{label('payment_method', payment_method_filter)}</b>\n"
        f"📦 Tarif tanlovi: <b>{label('plan', plan_filter)}</b>\n"
        f"🎁 Chegirma: <b>{label('discount', discount_filter)}</b>\n"
        f"📣 Kurs promo: <b>{label('promo', course_promo_filter)}</b>\n"
        f"⚡ Aktivlik: <b>{label('activity', activity_filter)}</b>"
        "</blockquote>\n\n"
        "Kerakli segmentni tanlang, keyin ✏️ Matn kiritish tugmasini bosing."
    )


def _initial_broadcast_state() -> dict:
    return {
        "target_languages": [],
        "status_filter": None,
        "level_filter": None,
        "mode_filter": None,
        "payment_status_filter": None,
        "payment_method_filter": None,
        "plan_filter": None,
        "discount_filter": None,
        "course_promo_filter": None,
        "activity_filter": None,
        "target_user_id": None,
        "target_label": None,
        "bc_section": "main",
    }


def _selected_languages(data: dict) -> list[str]:
    return normalize_broadcast_languages(data.get("target_languages") or [])


def _actual_user_languages(users) -> list[str]:
    selected = {
        user.language if getattr(user, "language", None) in SUPPORTED_BROADCAST_LANGUAGES else "tj"
        for user in users
    }
    return [lang for lang in SUPPORTED_BROADCAST_LANGUAGES if lang in selected]


async def _prepare_localized_text(text: str, users, content_type: str) -> str:
    if not text:
        return ""
    max_length = 1024 if content_type in {"photo", "video"} else 4096
    target_languages = _actual_user_languages(users) or list(SUPPORTED_BROADCAST_LANGUAGES)
    localized = await BroadcastTranslationService().translate_from_tajik(
        text,
        target_languages,
        max_length=max_length,
    )
    return encode_localized_broadcast_text(localized.texts)


async def _get_target_users(session, data: dict) -> list:
    user_repo = UserRepository(session)
    target_user_id = data.get("target_user_id")
    if target_user_id:
        target_user = await user_repo.get_by_telegram_id(int(target_user_id))
        return [target_user] if target_user else []
    return await user_repo.get_filtered_users(
        languages=_selected_languages(data) or None,
        status=data.get("status_filter"),
        level=data.get("level_filter"),
        learning_mode=data.get("mode_filter"),
        payment_status=data.get("payment_status_filter"),
        payment_method=data.get("payment_method_filter"),
        selected_plan_type=data.get("plan_filter"),
        discount_filter=data.get("discount_filter"),
        course_promo_filter=data.get("course_promo_filter"),
        activity_filter=data.get("activity_filter"),
    )


async def _send_broadcast_payload(
    bot,
    *,
    chat_id: int,
    text: str,
    content_type: str,
    media_file_id: str | None,
) -> None:
    if content_type == "photo" and media_file_id:
        await bot.send_photo(chat_id, media_file_id, caption=text or None)
    elif content_type == "video" and media_file_id:
        await bot.send_video(chat_id, media_file_id, caption=text or None)
    else:
        await bot.send_message(chat_id, text)


async def _edit_callback_panel(callback: CallbackQuery, state: FSMContext, text: str, reply_markup=None) -> None:
    await edit_callback_workflow_message(
        callback,
        state,
        text,
        chat_id_key=_PANEL_CHAT_ID,
        message_id_key=_PANEL_MSG_ID,
        reply_markup=reply_markup,
    )


async def _edit_stored_panel(message: Message, state: FSMContext, text: str, reply_markup=None) -> None:
    await edit_stored_workflow_message(
        message,
        state,
        text,
        chat_id_key=_PANEL_CHAT_ID,
        message_id_key=_PANEL_MSG_ID,
        reply_markup=reply_markup,
    )


async def open_broadcast_panel_for_message(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.update_data(**_initial_broadcast_state())
    sent = await message.answer(
        _panel_text([], None, None),
        reply_markup=broadcast_panel_keyboard([], None, None, section="main"),
        parse_mode="HTML",
    )
    await state.update_data(**{_PANEL_MSG_ID: sent.message_id, _PANEL_CHAT_ID: sent.chat.id})


async def open_broadcast_panel_for_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.update_data(**_initial_broadcast_state())
    sent = await callback.message.edit_text(
        _panel_text([], None, None),
        reply_markup=broadcast_panel_keyboard([], None, None, section="main"),
        parse_mode="HTML",
    )
    await state.update_data(**{_PANEL_MSG_ID: sent.message_id, _PANEL_CHAT_ID: sent.chat.id})


async def _redraw_panel(callback: CallbackQuery, data: dict) -> None:
    target_languages = _selected_languages(data)
    status_filter = data.get("status_filter")
    level_filter = data.get("level_filter")
    mode_filter = data.get("mode_filter")
    payment_status_filter = data.get("payment_status_filter")
    payment_method_filter = data.get("payment_method_filter")
    plan_filter = data.get("plan_filter")
    discount_filter = data.get("discount_filter")
    course_promo_filter = data.get("course_promo_filter")
    activity_filter = data.get("activity_filter")
    section = data.get("bc_section", "main")
    try:
        await callback.message.edit_text(
            _panel_text(
                target_languages,
                status_filter,
                level_filter,
                mode_filter,
                payment_status_filter,
                payment_method_filter,
                plan_filter,
                discount_filter,
                course_promo_filter,
                activity_filter,
            ),
            reply_markup=broadcast_panel_keyboard(
                target_languages,
                status_filter,
                level_filter,
                mode_filter,
                payment_status_filter,
                payment_method_filter,
                plan_filter,
                discount_filter,
                course_promo_filter,
                activity_filter,
                section,
            ),
            parse_mode="HTML",
        )
    except Exception:
        pass


# ── /broadcast ──────────────────────────────────────────────────────────────

@router.message(Command("broadcast"))
async def broadcast_command(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return

    await open_broadcast_panel_for_message(message, state)


# ── Filter toggles ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("bc:section:"))
async def bc_section(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    section = callback.data.split(":")[2]
    data = await state.get_data()
    data["bc_section"] = section
    await state.update_data(bc_section=section)
    await _redraw_panel(callback, data)
    await callback.answer()

@router.callback_query(F.data.startswith("bc:lang:"))
async def bc_lang_filter(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    val = callback.data.split(":")[2]
    data = await state.get_data()
    selected = set(_selected_languages(data))
    if val == "all":
        selected.clear()
    elif val in SUPPORTED_BROADCAST_LANGUAGES:
        if val in selected:
            selected.remove(val)
        else:
            selected.add(val)
    data["target_languages"] = normalize_broadcast_languages(selected)
    await state.update_data(target_languages=data["target_languages"])
    await _redraw_panel(callback, data)
    await callback.answer()


@router.callback_query(F.data.startswith("bc:status:"))
async def bc_status_filter(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    val = callback.data.split(":")[2]
    data = await state.get_data()
    data["status_filter"] = None if val == "all" else val
    await state.update_data(status_filter=data["status_filter"])
    await _redraw_panel(callback, data)
    await callback.answer()


@router.callback_query(F.data.startswith("bc:level:"))
async def bc_level_filter(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    val = callback.data.split(":")[2]
    data = await state.get_data()
    data["level_filter"] = None if val == "all" else val
    await state.update_data(level_filter=data["level_filter"])
    await _redraw_panel(callback, data)
    await callback.answer()


async def _set_filter(callback: CallbackQuery, state: FSMContext, key: str) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    val = callback.data.split(":")[2]
    data = await state.get_data()
    data[key] = None if val == "all" else val
    await state.update_data(**{key: data[key]})
    await _redraw_panel(callback, data)
    await callback.answer()


@router.callback_query(F.data.startswith("bc:mode:"))
async def bc_mode_filter(callback: CallbackQuery, state: FSMContext):
    await _set_filter(callback, state, "mode_filter")


@router.callback_query(F.data.startswith("bc:paystatus:"))
async def bc_payment_status_filter(callback: CallbackQuery, state: FSMContext):
    await _set_filter(callback, state, "payment_status_filter")


@router.callback_query(F.data.startswith("bc:paymethod:"))
async def bc_payment_method_filter(callback: CallbackQuery, state: FSMContext):
    await _set_filter(callback, state, "payment_method_filter")


@router.callback_query(F.data.startswith("bc:plan:"))
async def bc_plan_filter(callback: CallbackQuery, state: FSMContext):
    await _set_filter(callback, state, "plan_filter")


@router.callback_query(F.data.startswith("bc:discount:"))
async def bc_discount_filter(callback: CallbackQuery, state: FSMContext):
    await _set_filter(callback, state, "discount_filter")


@router.callback_query(F.data.startswith("bc:promo:"))
async def bc_promo_filter(callback: CallbackQuery, state: FSMContext):
    await _set_filter(callback, state, "course_promo_filter")


@router.callback_query(F.data.startswith("bc:activity:"))
async def bc_activity_filter(callback: CallbackQuery, state: FSMContext):
    await _set_filter(callback, state, "activity_filter")


# ── Text entry ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "bc:enter_text")
async def bc_enter_text(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    await state.update_data(target_user_id=None, target_label=None)
    await state.set_state(BroadcastStates.waiting_for_text)
    await callback.answer()
    await _edit_callback_panel(
        callback,
        state,
        "✏️ Xabarni yuboring:\n"
        "• faqat matn\n"
        "• foto + caption\n"
        "• video + caption"
    )


@router.callback_query(F.data == "bc:target_user")
async def bc_target_user(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    await state.update_data(target_user_id=None, target_label=None)
    await state.set_state(BroadcastStates.waiting_for_target)
    await callback.answer()
    await _edit_callback_panel(
        callback,
        state,
        "🎯 Bitta userga xabar\n\n"
        "Telegram ID yoki username yuboring.\n"
        "Misol: <code>123456789</code> yoki <code>@username</code>",
    )


@router.message(StateFilter(BroadcastStates.waiting_for_target))
async def bc_receive_target(message: Message, state: FSMContext, session):
    if not _is_admin(message.from_user.id):
        return

    identifier = (message.text or "").strip()
    user = await UserRepository(session).find_by_identifier(identifier)
    await delete_message_safely(message)
    if not user:
        await _edit_stored_panel(message, state, "❌ User topilmadi. Telegram ID yoki @username ni tekshiring.")
        return

    target_label = f"{user.full_name or '-'}"
    if user.username:
        target_label += f" (@{user.username})"
    await state.update_data(
        target_user_id=user.telegram_id,
        target_label=target_label,
    )
    await state.set_state(BroadcastStates.waiting_for_text)
    await _edit_stored_panel(
        message,
        state,
        f"✅ Target: <b>{escape(target_label)}</b>\n"
        f"ID: <code>{user.telegram_id}</code>\n\n"
        "Endi xabarni yuboring: matn, foto yoki video + caption.",
    )


@router.message(StateFilter(BroadcastStates.waiting_for_text))
async def bc_receive_text(message: Message, state: FSMContext, session):
    if not _is_admin(message.from_user.id):
        return

    text = message.text or message.caption or ""
    content_type = "text"
    media_file_id = None
    if message.photo:
        content_type = "photo"
        media_file_id = message.photo[-1].file_id
    elif message.video:
        content_type = "video"
        media_file_id = message.video.file_id

    if not text and not media_file_id:
        await delete_message_safely(message)
        await _edit_stored_panel(message, state, "Matn, foto yoki video yuboring.")
        return
    if content_type == "text" and len(text) > 4096:
        await delete_message_safely(message)
        await _edit_stored_panel(message, state, "Matn 4096 belgidan oshmasin.")
        return
    if content_type in ("photo", "video") and len(text) > 1024:
        await delete_message_safely(message)
        await _edit_stored_panel(message, state, "Foto/video caption 1024 belgidan oshmasin.")
        return

    await state.set_state(None)
    await state.update_data(
        broadcast_text=text,
        broadcast_content_type=content_type,
        broadcast_media_file_id=media_file_id,
    )

    data = await state.get_data()
    users = await _get_target_users(session, data)
    count = len(users)

    media_label = {"text": "Matn", "photo": "Foto", "video": "Video"}[content_type]
    preview_source = text if text else f"[{media_label}]"
    preview = escape(preview_source[:200] + ("..." if len(preview_source) > 200 else ""))
    selected_languages = broadcast_languages_or_all(_selected_languages(data))
    language_preview = ", ".join(_LANG_LABELS[item] for item in selected_languages)
    confirm_text = (
        "📢 <b>Broadcast tasdiqlash</b>\n\n"
        f"Tur: <b>{media_label}</b>\n"
        f"<blockquote>{preview}</blockquote>\n\n"
        f"👥 Target: <b>{escape(data.get('target_label') or f'{count} ta user')}</b>\n"
        f"🌐 Tillarga moslash: <b>{language_preview}</b>\n"
        "Source matn tojikcha deb olinadi; UZ/RU kerak bo'lsa AI tarjima qiladi.\n"
        "⚠️ Xabar faqat tanlangan user yoki filter segmentiga yuboriladi.\n\n"
        "Tasdiqlaysizmi?"
    )

    panel_msg_id = data.get("panel_msg_id")
    panel_chat_id = data.get("panel_chat_id")
    await delete_message_safely(message)

    if panel_msg_id and panel_chat_id:
        try:
            await message.bot.edit_message_text(
                text=confirm_text,
                chat_id=panel_chat_id,
                message_id=panel_msg_id,
                reply_markup=broadcast_confirm_keyboard(),
                parse_mode="HTML",
            )
            return
        except Exception:
            pass

    sent = await message.answer(
        confirm_text,
        reply_markup=broadcast_confirm_keyboard(),
        parse_mode="HTML",
    )
    await state.update_data(**{_PANEL_MSG_ID: sent.message_id, _PANEL_CHAT_ID: sent.chat.id})


# ── Confirm / Cancel ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "bc:test")
async def bc_test(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    data = await state.get_data()
    broadcast_text = data.get("broadcast_text", "")
    content_type = data.get("broadcast_content_type", "text")
    media_file_id = data.get("broadcast_media_file_id")
    if not broadcast_text and not media_file_id:
        await callback.answer("Xabar topilmadi", show_alert=True)
        return

    users = await _get_target_users(session, data)
    localized_text = data.get("broadcast_localized_text")
    if broadcast_text and not localized_text:
        localized_text = await _prepare_localized_text(broadcast_text, users, content_type)
        await state.update_data(broadcast_localized_text=localized_text)

    languages = _actual_user_languages(users) or broadcast_languages_or_all(_selected_languages(data))
    if not languages:
        languages = list(SUPPORTED_BROADCAST_LANGUAGES)

    try:
        for lang in languages:
            await callback.bot.send_message(callback.from_user.id, f"👁 Test {_LANG_LABELS[lang]}")
            await _send_broadcast_payload(
                callback.bot,
                chat_id=callback.from_user.id,
                text=localized_broadcast_text_for_language(localized_text or broadcast_text, lang),
                content_type=content_type,
                media_file_id=media_file_id,
            )
            await asyncio.sleep(0.05)
        await callback.answer("Test yuborildi", show_alert=True)
    except Exception as exc:
        await callback.answer(f"Test xato: {str(exc)[:80]}", show_alert=True)


@router.callback_query(F.data == "bc:confirm")
async def bc_confirm(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    await callback.answer()

    data = await state.get_data()
    broadcast_text = data.get("broadcast_text", "")
    content_type = data.get("broadcast_content_type", "text")
    media_file_id = data.get("broadcast_media_file_id")
    await state.clear()

    if not broadcast_text and not media_file_id:
        await callback.message.edit_text("❌ Xabar topilmadi.")
        return

    users = await _get_target_users(session, data)
    total = len(users)

    localized_text = data.get("broadcast_localized_text")
    if broadcast_text and not localized_text:
        await callback.message.edit_text("🌐 AI tarjima tayyorlanmoqda...")
        localized_text = await _prepare_localized_text(broadcast_text, users, content_type)
    elif not localized_text:
        localized_text = broadcast_text

    await callback.message.edit_text(f"⏳ Yuborilmoqda... (0/{total})")

    sent_count = 0
    failed_count = 0
    last_update = time.monotonic()

    for i, user in enumerate(users, start=1):
        try:
            if content_type == "photo" and media_file_id:
                text = localized_broadcast_text_for_language(localized_text, user.language)
                await _send_broadcast_payload(
                    callback.bot,
                    chat_id=user.telegram_id,
                    text=text,
                    content_type=content_type,
                    media_file_id=media_file_id,
                )
            elif content_type == "video" and media_file_id:
                text = localized_broadcast_text_for_language(localized_text, user.language)
                await _send_broadcast_payload(
                    callback.bot,
                    chat_id=user.telegram_id,
                    text=text,
                    content_type=content_type,
                    media_file_id=media_file_id,
                )
            else:
                await _send_broadcast_payload(
                    callback.bot,
                    chat_id=user.telegram_id,
                    text=localized_broadcast_text_for_language(localized_text, user.language),
                    content_type=content_type,
                    media_file_id=media_file_id,
                )
            sent_count += 1
        except Exception:
            failed_count += 1
        await asyncio.sleep(0.05)

        now = time.monotonic()
        if now - last_update >= 2 or i == total:
            try:
                await callback.message.edit_text(f"⏳ Yuborilmoqda... ({i}/{total})")
                last_update = now
            except Exception:
                pass

    await callback.message.edit_text(
        f"✅ Yuborildi: {sent_count}, ❌ Xato: {failed_count}"
    )


@router.callback_query(F.data == "bc:cancel")
async def bc_cancel(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    await state.clear()
    await callback.answer()
    await callback.message.edit_text("❌ Broadcast bekor qilindi.")


from datetime import datetime, timezone
from html import escape
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.fsm.release_feedback import ReleaseFeedbackAdminStates, ReleaseFeedbackUserStates
from app.bot.keyboards.release_feedback import (
    release_feedback_after_rating_keyboard,
    release_feedback_cancel_keyboard,
    release_feedback_confirm_keyboard,
    release_feedback_discount_keyboard,
    release_feedback_feature_keyboard,
    release_feedback_list_keyboard,
    release_feedback_panel_keyboard,
    release_feedback_rating_keyboard,
    release_feedback_send_time_keyboard,
    release_feedback_stats_keyboard,
    release_feedback_test_rating_keyboard,
)
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.subscription import subscription_miniapp_keyboard
from app.bot.utils.workflow_message import delete_message_safely
from app.config import settings
from app.repositories.release_feedback_repo import (
    ReleaseFeedbackRepository,
    decode_languages,
    encode_languages,
)
from app.repositories.user_repo import UserRepository
from app.services.broadcast_translation_service import (
    BroadcastTranslationService,
    SUPPORTED_BROADCAST_LANGUAGES,
    broadcast_languages_or_all,
    encode_localized_broadcast_text,
    localized_broadcast_preview,
)
from app.services.release_feedback_service import (
    ReleaseFeedbackService,
    release_feedback_discount_text,
    release_feedback_low_rating_comment_text,
    release_feedback_optional_comment_text,
    release_feedback_thanks_text,
    release_feedback_try_already_text,
    release_feedback_try_granted_text,
    send_release_feedback_payload,
)


router = Router()
ADMIN_TZ = ZoneInfo("Asia/Shanghai")
_PANEL_CHAT_ID = "rf_panel_chat_id"
_PANEL_MSG_ID = "rf_panel_msg_id"
_LANG_LABELS = {"tj": "TJ", "uz": "UZ", "ru": "RU"}
_MEDIA_LABELS = {"text": "Matn", "photo": "Foto", "video": "Video"}
_FEATURE_LABELS = {
    "general": "Umumiy",
    "qa": "Oddiy AI savol",
    "image": "Foto tahlil",
    "course": "Kurs rejimi",
    "profile": "Profil",
    "subscription": "Obuna/Chegirma",
}
_MAX_COMMENT_TEXT = 1000
_COURSE_MINIAPP_V2_RELEASE_TITLE = "Course Mini App v2: quiz va mustahkamlash"
_COURSE_MINIAPP_V2_RELEASE_TEXTS = {
    "uz": (
        "⚡ Course mode yangilandi!\n\n"
        "Quiz endi yengil interaktiv formatda: 5 ta tez savol, speaker, chiplar, progress va darhol feedback.\n\n"
        "Uyga vazifa o'rniga Mustahkamlash qo'shildi: so'z tartiblash, mos juftlik, eshitib tanlash va iyeroglifni ko'rish.\n\n"
        "Kursga kiring va keyingi darsda sinab ko'ring."
    ),
    "ru": (
        "⚡ Course mode обновился!\n\n"
        "Quiz теперь в лёгком интерактивном формате: 5 быстрых вопросов, speaker, chips, progress и мгновенный feedback.\n\n"
        "Вместо домашнего задания добавлено Закрепление: порядок слов, пары, выбор на слух и просмотр иероглифа.\n\n"
        "Зайдите в курс и попробуйте на следующем уроке."
    ),
    "tj": (
        "⚡ Course mode нав шуд!\n\n"
        "Quiz ҳоло дар формати сабуки интерактивӣ аст: 5 саволи тез, speaker, chip-ҳо, progress ва feedback-и фаврӣ.\n\n"
        "Ба ҷои вазифаи хонагӣ Мустаҳкамкунӣ илова шуд: тартиби калимаҳо, ҷуфтҳо, интихоб аз рӯи шунидан ва дидани иероглиф.\n\n"
        "Ба курс дароед ва дар дарси навбатӣ санҷед."
    ),
}


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_id_list


def _mark(active: bool) -> str:
    return "✅ " if active else ""


def _initial_state() -> dict:
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
        "feature_key": "general",
        "rf_section": "main",
    }


def _course_miniapp_v2_template_state(current: dict | None = None) -> dict:
    current = current or {}
    data = _initial_state()
    for key in data:
        if key in current:
            data[key] = current[key]
    data.update(
        {
            "title": _COURSE_MINIAPP_V2_RELEASE_TITLE,
            "message_text": _COURSE_MINIAPP_V2_RELEASE_TEXTS["tj"],
            "content_type": "text",
            "media_file_id": None,
            "localized_message_text": encode_localized_broadcast_text(_COURSE_MINIAPP_V2_RELEASE_TEXTS),
            "mode_filter": current.get("mode_filter") or "course",
        }
    )
    return data


def _selected_languages(data: dict) -> list[str]:
    selected = {item for item in (data.get("target_languages") or []) if item in SUPPORTED_BROADCAST_LANGUAGES}
    return [lang for lang in SUPPORTED_BROADCAST_LANGUAGES if lang in selected]


def _languages_label(values: list[str]) -> str:
    return ", ".join(_LANG_LABELS[item] for item in values) if values else "Hammasi"


def _fmt_time(value) -> str:
    if not value:
        return "—"
    return value.astimezone(ADMIN_TZ).strftime("%Y-%m-%d %H:%M")


def _status_label(campaign) -> str:
    return {
        "scheduled": "kutmoqda",
        "sending": "yuborilmoqda",
        "sent": "yuborilgan",
        "stopped": "to'xtatilgan",
    }.get(campaign.status, campaign.status)


def _panel_text(data: dict) -> str:
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
        "payment_status": {"none": "Yo'q", "pending": "Kutilmoqda", "approved": "Tasdiqlangan", "rejected": "Rad"},
        "payment_method": {"visa": "Visa", "alipay": "Alipay", "wechat": "WeChat"},
        "plan": {"10_days": "10 kun", "1_month": "1 oy"},
        "discount": {"eligible": "Chegirma bor", "used": "Ishlatilgan", "none": "Yo'q"},
        "promo": {"sent": "Promo yuborilgan", "not_sent": "Promo yo'q"},
        "activity": {"active_7d": "7 kunda aktiv", "inactive_7d": "7 kunda sovuq", "new_7d": "7 kunda yangi"},
    }

    def label(group: str, value) -> str:
        return labels[group].get(value, value) if value else "Hammasi"

    selected = _selected_languages(data)
    return (
        "🆕 <b>Yangilik otzivi</b>\n\n"
        "<blockquote>"
        f"Til: <b>{_languages_label(selected)}</b>\n"
        f"Status: <b>{label('status', data.get('status_filter'))}</b>\n"
        f"Daraja: <b>{label('level', data.get('level_filter'))}</b>\n"
        f"Rejim: <b>{label('mode', data.get('mode_filter'))}</b>\n"
        f"To'lov statusi: <b>{label('payment_status', data.get('payment_status_filter'))}</b>\n"
        f"To'lov usuli: <b>{label('payment_method', data.get('payment_method_filter'))}</b>\n"
        f"Tarif: <b>{label('plan', data.get('plan_filter'))}</b>\n"
        f"Chegirma: <b>{label('discount', data.get('discount_filter'))}</b>\n"
        f"Kurs promo: <b>{label('promo', data.get('course_promo_filter'))}</b>\n"
        f"Aktivlik: <b>{label('activity', data.get('activity_filter'))}</b>"
        "</blockquote>\n\n"
        "Targetni tanlang, keyin yangi release yarating."
    )


def _filter_keyboard(data: dict) -> InlineKeyboardMarkup:
    section = data.get("rf_section", "main")
    selected_languages = set(_selected_languages(data))

    def section_btn(key: str, label: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(text=label, callback_data=f"rf:section:{key}")

    def back_btn() -> InlineKeyboardButton:
        return InlineKeyboardButton(text="⬅️ Filterlarga qaytish", callback_data="rf:section:main")

    def lang_btn(value: str, label: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(text=f"{_mark(value in selected_languages)}{label}", callback_data=f"rf:lang:{value}")

    def option(prefix: str, current, value, label: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text=f"{_mark(current == value)}{label}",
            callback_data=f"rf:{prefix}:{value or 'all'}",
        )

    if section == "lang":
        rows = [
            [lang_btn("tj", "TJ"), lang_btn("uz", "UZ"), lang_btn("ru", "RU")],
            [InlineKeyboardButton(text=f"{_mark(not selected_languages)}Hammasi", callback_data="rf:lang:all")],
        ]
    elif section == "status":
        current = data.get("status_filter")
        rows = [
            [option("status", current, None, "Hammasi"), option("status", current, "active", "Faol"), option("status", current, "trial", "Sinov")],
            [option("status", current, "free", "Bepul"), option("status", current, "expired", "Tugagan"), option("status", current, "blocked", "Blok")],
        ]
    elif section == "level":
        current = data.get("level_filter")
        rows = [
            [option("level", current, None, "Hammasi"), option("level", current, "beginner", "Boshlang'ich"), option("level", current, "hsk1", "HSK1")],
            [option("level", current, "hsk2", "HSK2"), option("level", current, "hsk3", "HSK3"), option("level", current, "hsk4", "HSK4")],
        ]
    elif section == "mode":
        current = data.get("mode_filter")
        rows = [[option("mode", current, None, "Hammasi"), option("mode", current, "qa", "QA"), option("mode", current, "course", "Kurs")]]
    elif section == "payment":
        pay_status = data.get("payment_status_filter")
        method = data.get("payment_method_filter")
        plan = data.get("plan_filter")
        rows = [
            [option("paystatus", pay_status, None, "Status: Hammasi"), option("paystatus", pay_status, "none", "Yo'q"), option("paystatus", pay_status, "pending", "Kutilmoqda")],
            [option("paystatus", pay_status, "approved", "Tasdiqlangan"), option("paystatus", pay_status, "rejected", "Rad")],
            [option("paymethod", method, None, "Usul: Hammasi"), option("paymethod", method, "visa", "Visa")],
            [option("paymethod", method, "alipay", "Alipay"), option("paymethod", method, "wechat", "WeChat")],
            [option("plan", plan, None, "Tarif: Hammasi"), option("plan", plan, "10_days", "10 kun"), option("plan", plan, "1_month", "1 oy")],
        ]
    elif section == "discount":
        discount = data.get("discount_filter")
        promo = data.get("course_promo_filter")
        rows = [
            [option("discount", discount, None, "Hammasi"), option("discount", discount, "eligible", "Chegirma bor"), option("discount", discount, "used", "Ishlatilgan")],
            [option("discount", discount, "none", "Chegirma yo'q")],
            [option("promo", promo, None, "Promo: Hammasi"), option("promo", promo, "sent", "Yuborilgan"), option("promo", promo, "not_sent", "Yuborilmagan")],
        ]
    elif section == "activity":
        current = data.get("activity_filter")
        rows = [
            [option("activity", current, None, "Hammasi"), option("activity", current, "active_7d", "7 kun faol")],
            [option("activity", current, "inactive_7d", "7 kun sovuq"), option("activity", current, "new_7d", "7 kun yangi")],
        ]
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [section_btn("lang", "🌐 Til"), section_btn("status", "👤 Status")],
            [section_btn("level", "📚 Daraja"), section_btn("mode", "🎯 Rejim")],
            [section_btn("payment", "💳 To'lov"), section_btn("discount", "🎁 Chegirma")],
            [section_btn("activity", "⚡ Aktivlik")],
            [InlineKeyboardButton(text="➕ Yangi release", callback_data="rf:new")],
            [InlineKeyboardButton(text="⚡ Course Mini App update", callback_data="rf:template:course_miniapp_v2")],
            [InlineKeyboardButton(text="📋 Scheduled/Recent", callback_data="rf:list")],
            [InlineKeyboardButton(text="⬅️ Release panel", callback_data="rf:panel")],
        ])
    rows.append([back_btn(), InlineKeyboardButton(text="➕ Yangi yangilik", callback_data="rf:new")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _remember_panel(state: FSMContext, callback: CallbackQuery) -> None:
    if callback.message:
        await state.update_data(**{_PANEL_CHAT_ID: callback.message.chat.id, _PANEL_MSG_ID: callback.message.message_id})


async def _edit_callback_panel(callback: CallbackQuery, state: FSMContext, text: str, reply_markup=None) -> None:
    await _remember_panel(state, callback)
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        pass


async def _edit_stored_panel(message: Message, state: FSMContext, text: str, reply_markup=None) -> None:
    data = await state.get_data()
    chat_id = data.get(_PANEL_CHAT_ID)
    message_id = data.get(_PANEL_MSG_ID)
    if chat_id and message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
            return
        except Exception:
            pass
    sent = await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")
    await state.update_data(**{_PANEL_CHAT_ID: sent.chat.id, _PANEL_MSG_ID: sent.message_id})


async def _show_main_panel(target, state: FSMContext, *, edit: bool = True) -> None:
    await state.clear()
    await state.update_data(**_initial_state())
    text = "🆕 <b>Yangilik otzivi</b>\n\nYangilik yuboring, userlardan 1-5 ball va izoh oling."
    if isinstance(target, CallbackQuery):
        await target.answer()
        if edit:
            await _edit_callback_panel(target, state, text, release_feedback_panel_keyboard())
        else:
            sent = await target.message.answer(text, reply_markup=release_feedback_panel_keyboard(), parse_mode="HTML")
            await state.update_data(**{_PANEL_CHAT_ID: sent.chat.id, _PANEL_MSG_ID: sent.message_id})
    else:
        sent = await target.answer(text, reply_markup=release_feedback_panel_keyboard(), parse_mode="HTML")
        await state.update_data(**{_PANEL_CHAT_ID: sent.chat.id, _PANEL_MSG_ID: sent.message_id})


async def _target_users_for_data(session, data: dict) -> list:
    users = await UserRepository(session).get_filtered_users(
        languages=_selected_languages(data),
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
    admin_ids = set(settings.admin_id_list)
    return [user for user in users if user.status != "blocked" and user.telegram_id not in admin_ids]


def _actual_user_languages(users) -> list[str]:
    selected = {
        user.language if getattr(user, "language", None) in SUPPORTED_BROADCAST_LANGUAGES else "tj"
        for user in users
    }
    return [lang for lang in SUPPORTED_BROADCAST_LANGUAGES if lang in selected]


async def _prepare_localized_text(session, data: dict) -> str | None:
    text = data.get("message_text") or ""
    if not text:
        return None
    existing = data.get("localized_message_text")
    if existing:
        return existing
    max_length = 1024 if data.get("content_type") in {"photo", "video"} else 4096
    users = await _target_users_for_data(session, data)
    target_languages = _actual_user_languages(users) or broadcast_languages_or_all(_selected_languages(data))
    localized = await BroadcastTranslationService().translate_from_tajik(
        text,
        target_languages,
        max_length=max_length,
    )
    return encode_localized_broadcast_text(localized.texts)


async def _target_count(session, data: dict) -> int:
    return len(await _target_users_for_data(session, data))


def _content_preview(data: dict, limit: int = 180) -> str:
    content_type = data.get("content_type") or "text"
    text = data.get("localized_message_text") or data.get("message_text") or ""
    if not text:
        return f"[{_MEDIA_LABELS.get(content_type, content_type)}]"
    return localized_broadcast_preview(text, limit=limit)


async def _confirm_text(session, data: dict) -> str:
    count = await _target_count(session, data)
    preview = escape(_content_preview(data))
    send_at = data.get("send_at")
    return (
        "🆕 <b>Yangilik otzivini tasdiqlash</b>\n\n"
        f"Nomi: <b>{escape(str(data.get('title') or '—'))}</b>\n"
        f"Tur: <b>{_MEDIA_LABELS.get(data.get('content_type'), '—')}</b>\n"
        f"<blockquote>{preview}</blockquote>\n\n"
        f"Target: <b>{count} ta user</b>\n"
        f"Sinash joyi: <b>{escape(_FEATURE_LABELS.get(data.get('feature_key') or 'general', 'Umumiy'))}</b>\n"
        f"Yuborish vaqti: <b>{_fmt_time(send_at)}</b>\n"
        "Feedback: <b>1-5 ball</b>, 1-2 uchun izoh majburiy.\n"
        "Sinab ko'rish: <b>non-paid userlarga 30 minut limitsiz test access</b>.\n"
        "Chegirma: <b>non-paid userlarga oldindan aytilgan 20% / 24 soat</b>.\n\n"
        "Saqlaysizmi?"
    )


async def _show_confirm_callback(callback: CallbackQuery, state: FSMContext, session) -> None:
    await _edit_callback_panel(callback, state, await _confirm_text(session, await state.get_data()), release_feedback_confirm_keyboard())


async def _show_confirm_message(message: Message, state: FSMContext, session) -> None:
    await _edit_stored_panel(message, state, await _confirm_text(session, await state.get_data()), release_feedback_confirm_keyboard())


def _extract_comment(message: Message):
    if message.text:
        text = (message.text or "").strip()
        if text and not text.startswith("/"):
            return text[:_MAX_COMMENT_TEXT], None, None
    if message.photo:
        return (message.caption or "Screenshot").strip()[:_MAX_COMMENT_TEXT], message.photo[-1].file_id, "photo"
    if message.document and (message.document.mime_type or "").startswith("image/"):
        return (message.caption or "Screenshot").strip()[:_MAX_COMMENT_TEXT], message.document.file_id, "document"
    return None, None, None


async def _edit_user_feedback_message(target, text: str, reply_markup=None) -> None:
    try:
        await target.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
        return
    except Exception:
        pass
    try:
        await target.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="HTML")
        return
    except Exception:
        pass
    await target.answer(text, reply_markup=reply_markup, parse_mode="HTML")


async def _edit_stored_user_message(
    message: Message,
    message_id: int,
    text: str,
    reply_markup=None,
    *,
    delete_input: bool = True,
) -> None:
    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    except Exception:
        try:
            await message.bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=message_id,
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        except Exception:
            await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")
    if delete_input:
        await delete_message_safely(message)


async def _complete_response(
    *,
    session,
    user,
    campaign,
    rating: int,
    comment_text: str | None = None,
    attachment_file_id: str | None = None,
    attachment_type: str | None = None,
):
    service = ReleaseFeedbackService(session)
    repo = service.repo
    existing = await repo.get_response(campaign_id=campaign.id, user_telegram_id=user.telegram_id)
    if existing:
        if comment_text or attachment_file_id:
            await repo.update_response_comment(
                existing,
                comment_text=comment_text,
                attachment_file_id=attachment_file_id,
                attachment_type=attachment_type,
            )
        response = existing
    else:
        response = await repo.create_response(
            campaign_id=campaign.id,
            user_telegram_id=user.telegram_id,
            rating=rating,
            comment_text=comment_text,
            attachment_file_id=attachment_file_id,
            attachment_type=attachment_type,
        )
    discount_campaign_id = await service.create_discount_for_response(
        campaign=campaign,
        response=response,
        user=user,
    )
    return response, discount_campaign_id


async def _route_try_feature(callback: CallbackQuery, state: FSMContext, session, user, campaign) -> None:
    lang = user.language if user and user.language else "ru"
    feature_key = getattr(campaign, "feature_key", None) or "general"

    if feature_key == "course":
        from app.bot.handlers.course import send_course_miniapp_entry

        await send_course_miniapp_entry(
            session=session,
            telegram_id=callback.from_user.id,
            respond=callback.message.answer,
            state=state,
            source="release_feedback_course",
        )
        return

    if feature_key == "profile":
        from app.bot.handlers.commands import _profile_referral_count, _profile_reminder_text, _profile_text, profile_menu_keyboard

        referral_total = await _profile_referral_count(session, user)
        reminder_text = await _profile_reminder_text(session, user, lang)
        await callback.message.answer(
            _profile_text(user, lang, referral_total, reminder_text),
            reply_markup=profile_menu_keyboard(lang, user),
            parse_mode="HTML",
        )
        return

    if feature_key == "subscription":
        from app.bot.handlers.subscription import build_subscription_main_text_for_user

        await callback.message.answer(
            await build_subscription_main_text_for_user(session, user, lang),
            reply_markup=subscription_miniapp_keyboard(lang, source="release_feedback_try", mode="subscription"),
            parse_mode="HTML",
        )
        return

    if feature_key == "qa":
        user.learning_mode = "qa"
        user.voice_mode = "none"
        await state.update_data(pending_voice_transcript=None, pending_voice_message_id=None)
        await session.flush()
        await callback.message.answer(
            {
                "uz": "Oddiy AI savol rejimi ochildi. Endi yangilangan joyni sinash uchun savolingizni yozing.",
                "ru": "Открыт обычный режим AI-вопросов. Напишите вопрос, чтобы попробовать обновление.",
                "tj": "Реҷаи одии саволи AI кушода шуд. Барои санҷидани навигарӣ саволи худро нависед.",
            }.get(lang, "Напишите вопрос, чтобы попробовать обновление."),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    if feature_key == "image":
        await callback.message.answer(
            {
                "uz": "Foto tahlilni sinash uchun rasm yuboring.",
                "ru": "Чтобы попробовать анализ фото, отправьте изображение.",
                "tj": "Барои санҷидани таҳлили фото, расм фиристед.",
            }.get(lang, "Отправьте изображение, чтобы попробовать обновление."),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    await callback.message.answer(
        {
            "uz": "Yangilangan joyni sinash uchun menyudan kerakli bo'limni tanlang.",
            "ru": "Чтобы попробовать обновление, выберите нужный раздел в меню.",
            "tj": "Барои санҷидани навигарӣ, аз меню қисми лозимиро интихоб кунед.",
        }.get(lang, "Выберите нужный раздел в меню."),
        reply_markup=main_menu_keyboard(lang),
    )


@router.message(Command("release_feedback"))
async def release_feedback_command(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await _show_main_panel(message, state)


@router.callback_query(F.data == "adm:release_feedback")
async def release_feedback_from_admin(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await _show_main_panel(callback, state)


@router.callback_query(F.data == "rf:panel")
async def rf_panel(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await _show_main_panel(callback, state)


@router.callback_query(F.data == "rf:filters")
async def rf_filters(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    data = await state.get_data()
    if not data:
        data = _initial_state()
        await state.update_data(**data)
    await callback.answer()
    await _edit_callback_panel(callback, state, _panel_text(data), _filter_keyboard(data))


@router.callback_query(F.data.startswith("rf:section:"))
async def rf_section(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    section = callback.data.split(":")[2]
    await state.update_data(rf_section=section)
    data = await state.get_data()
    await callback.answer()
    await _edit_callback_panel(callback, state, _panel_text(data), _filter_keyboard(data))


@router.callback_query(F.data.startswith("rf:lang:"))
async def rf_lang(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    value = callback.data.split(":")[2]
    data = await state.get_data()
    selected = set(_selected_languages(data))
    if value == "all":
        selected.clear()
    elif value in SUPPORTED_BROADCAST_LANGUAGES:
        if value in selected:
            selected.remove(value)
        else:
            selected.add(value)
    await state.update_data(target_languages=list(selected))
    data = await state.get_data()
    await callback.answer()
    await _edit_callback_panel(callback, state, _panel_text(data), _filter_keyboard(data))


async def _set_filter(callback: CallbackQuery, state: FSMContext, key: str) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    value = callback.data.split(":")[2]
    await state.update_data(**{key: None if value == "all" else value})
    data = await state.get_data()
    await callback.answer()
    await _edit_callback_panel(callback, state, _panel_text(data), _filter_keyboard(data))


@router.callback_query(F.data.startswith("rf:status:"))
async def rf_status(callback: CallbackQuery, state: FSMContext):
    await _set_filter(callback, state, "status_filter")


@router.callback_query(F.data.startswith("rf:level:"))
async def rf_level(callback: CallbackQuery, state: FSMContext):
    await _set_filter(callback, state, "level_filter")


@router.callback_query(F.data.startswith("rf:mode:"))
async def rf_mode(callback: CallbackQuery, state: FSMContext):
    await _set_filter(callback, state, "mode_filter")


@router.callback_query(F.data.startswith("rf:paystatus:"))
async def rf_paystatus(callback: CallbackQuery, state: FSMContext):
    await _set_filter(callback, state, "payment_status_filter")


@router.callback_query(F.data.startswith("rf:paymethod:"))
async def rf_paymethod(callback: CallbackQuery, state: FSMContext):
    await _set_filter(callback, state, "payment_method_filter")


@router.callback_query(F.data.startswith("rf:plan:"))
async def rf_plan(callback: CallbackQuery, state: FSMContext):
    await _set_filter(callback, state, "plan_filter")


@router.callback_query(F.data.startswith("rf:discount:"))
async def rf_discount(callback: CallbackQuery, state: FSMContext):
    await _set_filter(callback, state, "discount_filter")


@router.callback_query(F.data.startswith("rf:promo:"))
async def rf_promo(callback: CallbackQuery, state: FSMContext):
    await _set_filter(callback, state, "course_promo_filter")


@router.callback_query(F.data.startswith("rf:activity:"))
async def rf_activity(callback: CallbackQuery, state: FSMContext):
    await _set_filter(callback, state, "activity_filter")


@router.callback_query(F.data == "rf:new")
async def rf_new(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    data = await state.get_data()
    if not data:
        await state.update_data(**_initial_state())
    await state.set_state(ReleaseFeedbackAdminStates.waiting_title)
    await callback.answer()
    await _edit_callback_panel(
        callback,
        state,
        "🆕 <b>Yangi yangilik otzivi</b>\n\nYangilik nomini yozing.",
        release_feedback_cancel_keyboard(),
    )


@router.callback_query(F.data == "rf:template:course_miniapp_v2")
async def rf_course_miniapp_v2_template(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    current = await state.get_data()
    await state.clear()
    await state.update_data(**_course_miniapp_v2_template_state(current))
    await callback.answer("Course update template tayyor", show_alert=True)
    await _edit_callback_panel(
        callback,
        state,
        "⚡ <b>Course Mini App update</b>\n\n"
        "Tayyor 3 tilli release matni qo'yildi.\n"
        "Target default: <b>Kurs rejimi</b>.\n\n"
        "Qachon yuborilsin?",
        release_feedback_send_time_keyboard(),
    )


@router.message(StateFilter(ReleaseFeedbackAdminStates.waiting_title))
async def rf_title(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    title = (message.text or "").strip()
    await delete_message_safely(message)
    if len(title) < 2:
        await _edit_stored_panel(message, state, "Nom juda qisqa. Yangilik nomini yozing.", release_feedback_cancel_keyboard())
        return
    await state.update_data(title=title[:120])
    await state.set_state(ReleaseFeedbackAdminStates.waiting_content)
    await _edit_stored_panel(
        message,
        state,
        "Yangilik e'lonini yuboring:\n"
        "• matn\n"
        "• foto + caption\n"
        "• video + caption\n\n"
        "Source matn Tajik deb olinadi; UZ/RU AI tarjima qilinadi.",
        release_feedback_cancel_keyboard(),
    )


@router.message(StateFilter(ReleaseFeedbackAdminStates.waiting_content))
async def rf_content(message: Message, state: FSMContext):
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

    await delete_message_safely(message)
    if not text and not media_file_id:
        await _edit_stored_panel(message, state, "Matn, foto yoki video yuboring.", release_feedback_cancel_keyboard())
        return
    if content_type == "text" and len(text) > 4096:
        await _edit_stored_panel(message, state, "Matn 4096 belgidan oshmasin.", release_feedback_cancel_keyboard())
        return
    if content_type in {"photo", "video"} and len(text) > 1024:
        await _edit_stored_panel(message, state, "Foto/video caption 1024 belgidan oshmasin.", release_feedback_cancel_keyboard())
        return

    await state.update_data(
        message_text=text,
        content_type=content_type,
        media_file_id=media_file_id,
        localized_message_text=None,
    )
    await state.set_state(ReleaseFeedbackAdminStates.waiting_feature)
    await _edit_stored_panel(
        message,
        state,
        "Yangilik botning qaysi joyida sinab ko'riladi?",
        release_feedback_feature_keyboard(),
    )


@router.callback_query(F.data.startswith("rf:feature:"))
async def rf_feature(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    feature_key = callback.data.split(":")[2]
    if feature_key not in _FEATURE_LABELS:
        feature_key = "general"
    await state.update_data(feature_key=feature_key)
    await state.set_state(None)
    await callback.answer()
    await _edit_callback_panel(
        callback,
        state,
        f"Sinash joyi: <b>{escape(_FEATURE_LABELS[feature_key])}</b>\n\nQachon yuborilsin?",
        release_feedback_send_time_keyboard(),
    )


@router.callback_query(F.data.startswith("rf:send_at:"))
async def rf_send_at(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    value = callback.data.split(":")[2]
    await callback.answer()
    if value == "scheduled":
        await state.set_state(ReleaseFeedbackAdminStates.waiting_send_at)
        await _edit_callback_panel(
            callback,
            state,
            "Boshlanish vaqtini yozing: <code>YYYY-MM-DD HH:MM</code>\nVaqt zonasi: Asia/Shanghai",
            release_feedback_cancel_keyboard(),
        )
        return
    await state.update_data(send_at=datetime.now(timezone.utc))
    await _show_confirm_callback(callback, state, session)


@router.message(StateFilter(ReleaseFeedbackAdminStates.waiting_send_at))
async def rf_send_at_message(message: Message, state: FSMContext, session):
    if not _is_admin(message.from_user.id):
        return
    raw = (message.text or "").strip()
    await delete_message_safely(message)
    try:
        local_dt = datetime.strptime(raw, "%Y-%m-%d %H:%M").replace(tzinfo=ADMIN_TZ)
    except ValueError:
        await _edit_stored_panel(
            message,
            state,
            "Format noto'g'ri. Masalan: <code>2026-06-14 21:30</code>",
            release_feedback_cancel_keyboard(),
        )
        return
    send_at = local_dt.astimezone(timezone.utc)
    if send_at < datetime.now(timezone.utc):
        await _edit_stored_panel(message, state, "Kelajakdagi vaqtni yozing.", release_feedback_cancel_keyboard())
        return
    await state.update_data(send_at=send_at)
    await state.set_state(None)
    await _show_confirm_message(message, state, session)


@router.callback_query(F.data == "rf:test")
async def rf_test(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    data = await state.get_data()
    if not data.get("content_type"):
        await callback.answer("Xabar topilmadi", show_alert=True)
        return
    try:
        localized = await _prepare_localized_text(session, data)
        if localized:
            await state.update_data(localized_message_text=localized)
        languages = broadcast_languages_or_all(_selected_languages(data))
        for lang in languages:
            await callback.bot.send_message(callback.from_user.id, f"👁 Yangilik testi {_LANG_LABELS[lang]}")
            await send_release_feedback_payload(
                callback.bot,
                chat_id=callback.from_user.id,
                text=localized or data.get("message_text"),
                content_type=data.get("content_type"),
                media_file_id=data.get("media_file_id"),
                language=lang,
                rating_markup=release_feedback_test_rating_keyboard(),
            )
        await callback.answer("Test yuborildi", show_alert=True)
    except Exception as exc:
        await callback.answer(f"Test xato: {str(exc)[:80]}", show_alert=True)


@router.callback_query(F.data == "rf:confirm")
async def rf_confirm(callback: CallbackQuery, state: FSMContext, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    data = await state.get_data()
    required = ["title", "content_type", "send_at"]
    if any(key not in data for key in required):
        await callback.answer("Ma'lumot yetishmayapti", show_alert=True)
        return
    localized = await _prepare_localized_text(session, data)
    target_count = await _target_count(session, data)
    campaign = await ReleaseFeedbackRepository(session).create_campaign(
        title=data["title"],
        message_text=localized or data.get("message_text") or None,
        content_type=data["content_type"],
        media_file_id=data.get("media_file_id"),
        send_at=data["send_at"],
        feature_key=data.get("feature_key") or "general",
        target_languages=_selected_languages(data),
        status_filter=data.get("status_filter"),
        level_filter=data.get("level_filter"),
        mode_filter=data.get("mode_filter"),
        payment_status_filter=data.get("payment_status_filter"),
        payment_method_filter=data.get("payment_method_filter"),
        plan_filter=data.get("plan_filter"),
        discount_filter=data.get("discount_filter"),
        course_promo_filter=data.get("course_promo_filter"),
        activity_filter=data.get("activity_filter"),
        created_by_telegram_id=callback.from_user.id,
    )
    campaign_id = campaign.id
    await session.commit()
    await state.clear()
    await callback.answer("Yangilik saqlandi", show_alert=True)
    await callback.message.edit_text(
        f"✅ Yangilik otzivi #{campaign_id} saqlandi.\n"
        f"Target: {target_count} ta user\n"
        f"Yuborish vaqti: {_fmt_time(data['send_at'])}\n\n"
        "Scheduler yuborish vaqti kelgan yangiliklarni 1 daqiqa ichida yuboradi.",
        reply_markup=release_feedback_panel_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "rf:list")
async def rf_list(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    repo = ReleaseFeedbackRepository(session)
    campaigns = await repo.list_recent_campaigns(10)
    await callback.answer()
    if not campaigns:
        await callback.message.edit_text(
            "Hozircha yangilik otzivi yo'q.",
            reply_markup=release_feedback_panel_keyboard(),
            parse_mode="HTML",
        )
        return
    lines = ["📋 <b>Yangilik otzivi kampaniyalari</b>", ""]
    for item in campaigns:
        stats = await repo.stats(item.id)
        langs = _languages_label(decode_languages(item.target_languages))
        lines.append(
            f"#{item.id} <b>{escape(item.title)}</b> — {_status_label(item)}\n"
            f"  Yuborish: {_fmt_time(item.send_at)} · Til: {langs}\n"
            f"  Yetdi: {stats.delivered}, xato: {stats.failed}, javob: {stats.responses}, o'rtacha: {stats.average_rating}"
        )
    await callback.message.edit_text(
        "\n\n".join(lines),
        reply_markup=release_feedback_list_keyboard(campaigns),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("rf:stats:"))
async def rf_stats(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    campaign_id = int(callback.data.split(":")[2])
    repo = ReleaseFeedbackRepository(session)
    campaign = await repo.get_campaign(campaign_id)
    if not campaign:
        await callback.answer("Topilmadi", show_alert=True)
        return
    stats = await repo.stats(campaign_id)
    comments = await repo.recent_comments(campaign_id, 5)
    comment_lines = []
    for item in comments:
        body = escape((item.comment_text or "[attachment]").strip()[:180])
        comment_lines.append(f"  {item.rating}/5 · <code>{item.user_telegram_id}</code>: {body}")
    if not comment_lines:
        comment_lines.append("  Izoh yo'q")
    text = (
        f"📊 <b>Yangilik otzivi #{campaign.id}</b>\n"
        f"<b>{escape(campaign.title)}</b>\n\n"
        f"Status: <b>{_status_label(campaign)}</b>\n"
        f"Yuborish: <b>{_fmt_time(campaign.send_at)}</b>\n\n"
        f"Yetib bordi: <b>{stats.delivered}</b> · Xato: <b>{stats.failed}</b>\n"
        f"Javoblar: <b>{stats.responses}</b> · O'rtacha: <b>{stats.average_rating}</b>\n"
        f"1: <b>{stats.rating_1}</b>  2: <b>{stats.rating_2}</b>  3: <b>{stats.rating_3}</b>  "
        f"4: <b>{stats.rating_4}</b>  5: <b>{stats.rating_5}</b>\n"
        f"Izoh/screenshot: <b>{stats.comments}</b>\n"
        f"Sinab ko'rish bosildi: <b>{stats.try_clicked}</b> · Test access: <b>{stats.trial_granted}</b>\n"
        f"Chegirma berildi: <b>{stats.discount_offered}</b> · ishlatilgan/kutilmoqda: <b>{stats.discount_used}</b>\n\n"
        "<b>Oxirgi izohlar:</b>\n"
        + "\n".join(comment_lines)
    )
    await callback.answer()
    await callback.message.edit_text(
        text,
        reply_markup=release_feedback_stats_keyboard(campaign.id, campaign.status in {"scheduled", "sending"}),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("rf:stop:"))
async def rf_stop(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    campaign_id = int(callback.data.split(":")[2])
    repo = ReleaseFeedbackRepository(session)
    campaign = await repo.get_campaign(campaign_id)
    if not campaign:
        await callback.answer("Topilmadi", show_alert=True)
        return
    await repo.stop_campaign(campaign)
    await session.commit()
    await callback.answer("To'xtatildi", show_alert=True)
    await callback.message.edit_text(
        f"⛔ Yangilik otzivi #{campaign_id} to'xtatildi.",
        reply_markup=release_feedback_panel_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "rf:cancel")
async def rf_cancel(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "❌ Yangilik otzivi bekor qilindi.",
        reply_markup=release_feedback_panel_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "relfb:test")
async def release_feedback_test_callback(callback: CallbackQuery):
    await callback.answer("Bu admin test xabari.", show_alert=True)


@router.callback_query(F.data.startswith("relfb:"))
async def release_feedback_user_callback(callback: CallbackQuery, state: FSMContext, session):
    parts = (callback.data or "").split(":")
    if len(parts) < 3:
        await callback.answer()
        return
    try:
        campaign_id = int(parts[1])
    except ValueError:
        await callback.answer()
        return
    action = parts[2]
    value = parts[3] if len(parts) > 3 else None

    repo = ReleaseFeedbackRepository(session)
    campaign = await repo.get_campaign(campaign_id)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "ru"
    if not campaign or not user:
        await callback.answer("Feedback topilmadi.", show_alert=True)
        return

    existing = await repo.get_response(campaign_id=campaign.id, user_telegram_id=user.telegram_id)
    if action == "try":
        granted, until = await ReleaseFeedbackService(session).grant_trial_access(
            campaign=campaign,
            user=user,
        )
        if granted:
            await callback.answer(release_feedback_try_granted_text(lang), show_alert=True)
        else:
            await callback.answer(release_feedback_try_already_text(lang), show_alert=True)
        await _route_try_feature(callback, state, session, user, campaign)
        await session.commit()
        return

    if action == "rate" and value:
        if existing:
            await callback.answer("Siz allaqachon baho bergansiz.", show_alert=True)
            return
        try:
            rating = int(value)
        except ValueError:
            await callback.answer()
            return
        if rating < 1 or rating > 5:
            await callback.answer()
            return
        if rating <= 2:
            await state.set_state(ReleaseFeedbackUserStates.waiting_required_comment)
            await state.update_data(
                release_feedback_campaign_id=campaign.id,
                release_feedback_rating=rating,
                release_feedback_message_id=callback.message.message_id,
            )
            await callback.answer()
            await _edit_user_feedback_message(
                callback.message,
                release_feedback_low_rating_comment_text(lang),
            )
            return

        response, discount_campaign_id = await _complete_response(
            session=session,
            user=user,
            campaign=campaign,
            rating=rating,
        )
        await session.commit()
        text = release_feedback_discount_text(lang) if discount_campaign_id else release_feedback_optional_comment_text(lang)
        await callback.answer()
        await _edit_user_feedback_message(
            callback.message,
            text,
            release_feedback_after_rating_keyboard(
                campaign.id,
                discount_campaign_id=response.discount_campaign_id,
                lang=lang,
            ),
        )
        return

    if action == "comment":
        if not existing:
            await callback.answer("Avval 1-5 ball tanlang.", show_alert=True)
            return
        await state.set_state(ReleaseFeedbackUserStates.waiting_optional_comment)
        await state.update_data(
            release_feedback_campaign_id=campaign.id,
            release_feedback_message_id=callback.message.message_id,
        )
        await callback.answer()
        await _edit_user_feedback_message(
            callback.message,
            release_feedback_optional_comment_text(lang),
        )
        return

    if action == "skip":
        await state.clear()
        await callback.answer()
        await _edit_user_feedback_message(callback.message, release_feedback_thanks_text(lang))
        return

    await callback.answer()


@router.message(StateFilter(ReleaseFeedbackUserStates.waiting_required_comment))
async def release_feedback_required_comment(message: Message, state: FSMContext, session):
    data = await state.get_data()
    campaign_id = int(data.get("release_feedback_campaign_id") or 0)
    rating = int(data.get("release_feedback_rating") or 0)
    message_id = int(data.get("release_feedback_message_id") or message.message_id)
    repo = ReleaseFeedbackRepository(session)
    campaign = await repo.get_campaign(campaign_id)
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    lang = user.language if user and user.language else "ru"
    comment_text, attachment_file_id, attachment_type = _extract_comment(message)
    if not campaign or not user or rating not in {1, 2}:
        await _edit_stored_user_message(message, message_id, "Feedback topilmadi.")
        await state.clear()
        return
    if not comment_text and not attachment_file_id:
        await _edit_stored_user_message(
            message,
            message_id,
            release_feedback_low_rating_comment_text(lang),
            delete_input=False,
        )
        return
    response, discount_campaign_id = await _complete_response(
        session=session,
        user=user,
        campaign=campaign,
        rating=rating,
        comment_text=comment_text,
        attachment_file_id=attachment_file_id,
        attachment_type=attachment_type,
    )
    await session.commit()
    await state.clear()
    text = release_feedback_discount_text(lang) if discount_campaign_id else release_feedback_thanks_text(lang)
    keyboard = (
        release_feedback_discount_keyboard(response.discount_campaign_id, lang)
        if response.discount_campaign_id
        else None
    )
    await _edit_stored_user_message(
        message,
        message_id,
        text,
        keyboard,
        delete_input=attachment_file_id is None,
    )


@router.message(StateFilter(ReleaseFeedbackUserStates.waiting_optional_comment))
async def release_feedback_optional_comment(message: Message, state: FSMContext, session):
    data = await state.get_data()
    campaign_id = int(data.get("release_feedback_campaign_id") or 0)
    message_id = int(data.get("release_feedback_message_id") or message.message_id)
    repo = ReleaseFeedbackRepository(session)
    response = await repo.get_response(campaign_id=campaign_id, user_telegram_id=message.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    lang = user.language if user and user.language else "ru"
    comment_text, attachment_file_id, attachment_type = _extract_comment(message)
    if not response:
        await _edit_stored_user_message(message, message_id, "Feedback topilmadi.")
        await state.clear()
        return
    if not comment_text and not attachment_file_id:
        await _edit_stored_user_message(
            message,
            message_id,
            "Izohni matn yoki screenshot qilib yuboring.",
            delete_input=False,
        )
        return
    await repo.update_response_comment(
        response,
        comment_text=comment_text,
        attachment_file_id=attachment_file_id,
        attachment_type=attachment_type,
    )
    await session.commit()
    await state.clear()
    keyboard = (
        release_feedback_discount_keyboard(response.discount_campaign_id, lang)
        if response.discount_campaign_id
        else None
    )
    await _edit_stored_user_message(
        message,
        message_id,
        release_feedback_thanks_text(lang),
        keyboard,
        delete_input=attachment_file_id is None,
    )

from app.bot.keyboards.onboarding import level_keyboard
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from sqlalchemy import select, func
from app.db.models.user import User

from app.repositories.user_repo import UserRepository
from app.services.referral_service import ReferralService
from app.bot.handlers.subscription import build_subscription_main_text_for_user
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.subscription import subscription_main_keyboard, payment_method_keyboard
from app.bot.keyboards.referral import photo_limit_subscription_keyboard
from app.bot.utils.i18n import t


router = Router()


def _lang(user) -> str:
    return user.language if user and user.language else "ru"


async def _clear_voice_mode(user, session, state: FSMContext | None = None) -> None:
    if state:
        await state.update_data(pending_voice_transcript=None, pending_voice_message_id=None)
    if user and (getattr(user, "voice_mode", "none") or "none") != "none":
        user.voice_mode = "none"
        await session.commit()


def _fmt_date(dt) -> str:
    if not dt:
        return "-"
    try:
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return str(dt)


def _status_label(status: str, lang: str) -> str:
    return {
        "free": "Free",
        "trial": "Free",
        "active": "Active",
        "expired": "Free",
        "blocked": {
            "tj": "Баста",
            "uz": "Bloklangan",
            "ru": "Заблокирован",
        }.get(lang, "Заблокирован"),
    }.get(status, "Free")


def _profile_status_label(user, lang: str) -> str:
    status = str(getattr(user, "status", "") or "")
    is_paid = getattr(user, "payment_status", "") == "approved"

    if status == "active" and is_paid:
        return "Active"

    if status == "active":
        return {
            "tj": "Мӯҳлати санҷишӣ",
            "uz": "Sinov muddati",
            "ru": "Пробный срок",
        }.get(lang, "Sinov muddati")

    return _status_label(status, lang)


def _language_label(value: str, lang: str) -> str:
    labels = {
        "tj": {"tj": "Тоҷикӣ", "uz": "O'zbek", "ru": "Русский"},
        "uz": {"tj": "Tojik", "uz": "O'zbek", "ru": "Rus"},
        "ru": {"tj": "Таджикский", "uz": "Узбекский", "ru": "Русский"},
    }
    unknown = {"tj": "Номаълум", "uz": "Noma'lum", "ru": "Неизвестно"}
    return labels.get(lang, labels["ru"]).get(value, unknown.get(lang, unknown["ru"]))


def _level_label(value: str, lang: str) -> str:
    if not value:
        return "—"
    if value.startswith("hsk"):
        return value.upper()
    beginner = {
        "tj": "Оғозӣ",
        "uz": "Boshlang'ich",
        "ru": "Начальный",
    }
    return beginner.get(lang, beginner["ru"]) if value == "beginner" else value


def _learning_mode_label(value: str, lang: str) -> str:
    labels = {
        "tj": {"qa": "Саволу ҷавоб", "course": "Курс"},
        "uz": {"qa": "Savol-javob", "course": "Kurs"},
        "ru": {"qa": "Вопрос-ответ", "course": "Курс"},
    }
    unknown = {"tj": "Номаълум", "uz": "Noma'lum", "ru": "Неизвестно"}
    return labels.get(lang, labels["ru"]).get(value, unknown.get(lang, unknown["ru"]))


def _days_label(days: int, lang: str) -> str:
    if lang == "tj":
        return f"{days} рӯз"
    if lang == "ru":
        return f"{days} дн."
    return f"{days} kun"


def _remaining_days(value) -> int | None:
    if not value:
        return None
    try:
        from datetime import datetime, timezone
        from math import ceil

        end_dt = value
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        seconds = (end_dt.astimezone(timezone.utc) - datetime.now(timezone.utc)).total_seconds()
        if seconds <= 0:
            return 0
        return max(1, ceil(seconds / 86400))
    except Exception:
        return None


def _referral_count_label(total: int, lang: str) -> str:
    if lang == "tj":
        return f"👥 <b>Даъватҳо:</b> {total} нафар"
    if lang == "ru":
        return f"👥 <b>Приглашения:</b> {total}"
    return f"👥 <b>Chaqirganlar:</b> {total} ta"


def _profile_reminder_line(progress, lang: str) -> str | None:
    from html import escape

    if (
        not progress
        or not getattr(progress, "reminder_enabled", False)
        or not getattr(progress, "reminder_time", None)
    ):
        return None

    reminder_time = getattr(progress, "reminder_time", None)
    try:
        time_text = reminder_time.strftime("%H:%M")
    except Exception:
        time_text = str(reminder_time)[:5]

    try:
        tz_offset = int(getattr(progress, "reminder_tz_offset", 5) or 5)
    except Exception:
        tz_offset = 5
    tz_text = f"UTC+{tz_offset}" if tz_offset >= 0 else f"UTC{tz_offset}"

    label = {
        "tj": "Ёдраскунак",
        "uz": "Eslatma",
        "ru": "Напоминание",
    }.get(lang, "Напоминание")
    return f"⏰ <b>{label}:</b> {escape(time_text)} ({escape(tz_text)})"


async def _profile_reminder_text(session, user, lang: str) -> str | None:
    from app.repositories.course_progress_repo import CourseProgressRepository

    if not user:
        return None
    progress = await CourseProgressRepository(session).get_by_user_id(user.id)
    return _profile_reminder_line(progress, lang)


def _profile_text(
    user,
    lang: str,
    referral_total: int = 0,
    reminder_text: str | None = None,
) -> str:
    from html import escape

    full_name = escape(str(getattr(user, "full_name", "—") or "—"))
    language = escape(_language_label(str(getattr(user, "language", "") or ""), lang))
    level = escape(_level_label(str(getattr(user, "level", "") or ""), lang))
    status_raw = str(getattr(user, "status", "—") or "—")
    learning_mode = escape(_learning_mode_label(str(getattr(user, "learning_mode", "") or ""), lang))

    started = (
        getattr(user, "start_date", None)
        or getattr(user, "created_at", None)
    )
    ends = getattr(user, "end_date", None)

    plan_raw = getattr(user, "selected_plan_type", None)
    is_paid = getattr(user, "payment_status", "") == "approved"
    is_temporary_active = status_raw == "active" and not is_paid

    duration_days = None
    try:
        if started and ends:
            duration_days = (ends.date() - started.date()).days
    except Exception:
        duration_days = None

    plan_label = ""
    if is_paid and plan_raw:
        plan_key = str(plan_raw)
        if lang == "tj":
            plan_map = {
                "10_days": "10 рӯз",
                "1_month": "1 моҳ",
                "monthly": "1 моҳ",
            }
        elif lang == "uz":
            plan_map = {
                "10_days": "10 kun",
                "1_month": "1 oy",
                "monthly": "1 oy",
            }
        else:
            plan_map = {
                "10_days": "10 дней",
                "1_month": "1 месяц",
                "monthly": "1 месяц",
            }
        plan_label = plan_map.get(plan_key, "")
    elif is_paid:
        if duration_days is not None and 9 <= duration_days <= 11:
            plan_label = "10 рӯз" if lang == "tj" else ("10 kun" if lang == "uz" else "10 дней")
        elif duration_days is not None and 28 <= duration_days <= 31:
            plan_label = "1 моҳ" if lang == "tj" else ("1 oy" if lang == "uz" else "1 месяц")
        else:
            plan_label = "Обунаи фаъол" if lang == "tj" else ("Faol obuna" if lang == "uz" else "Активная подписка")

    status = escape(_profile_status_label(user, lang))
    plan = escape(str(plan_label or ""))
    temporary_days = _remaining_days(ends) if is_temporary_active else None

    def fmt_date(value):
        if not value:
            return "—"
        try:
            return str(value)[:10]
        except Exception:
            return "—"

    ends_str = escape(fmt_date(ends))
    referral_count = _referral_count_label(referral_total, lang)

    if lang == "tj":
        details = [
            f"🙍 <b>Ном:</b> {full_name}",
            f"🈯 <b>Забон:</b> {language}",
            f"📖 <b>Дараҷа:</b> {level}",
            f"🎯 <b>Режими ҷорӣ:</b> {learning_mode}",
            f"⭐ <b>Ҳолат:</b> {status}",
            referral_count,
        ]
        if reminder_text:
            details.append(reminder_text)
        if is_paid and plan:
            details.append(f"💳 <b>Обуна:</b> {plan}")
            details.append(f"⌛ <b>Анҷом:</b> {ends_str}")
        elif is_temporary_active and temporary_days is not None:
            details.append(f"⏳ <b>Мӯҳлати санҷишӣ:</b> {_days_label(temporary_days, lang)}")
            details.append(f"⌛ <b>Анҷом:</b> {ends_str}")
        text = (
            f"<b>👤 Профили шумо</b>\n\n"
            f"<blockquote>{chr(10).join(details)}</blockquote>"
        )
        return text

    if lang == "uz":
        details = [
            f"🙍 <b>Ism:</b> {full_name}",
            f"🈯 <b>Til:</b> {language}",
            f"📖 <b>Daraja:</b> {level}",
            f"🎯 <b>Joriy rejim:</b> {learning_mode}",
            f"⭐ <b>Holat:</b> {status}",
            referral_count,
        ]
        if reminder_text:
            details.append(reminder_text)
        if is_paid and plan:
            details.append(f"💳 <b>Obuna:</b> {plan}")
            details.append(f"⌛ <b>Tugash:</b> {ends_str}")
        elif is_temporary_active and temporary_days is not None:
            details.append(f"⏳ <b>Sinov muddati:</b> {_days_label(temporary_days, lang)}")
            details.append(f"⌛ <b>Tugash:</b> {ends_str}")
        text = (
            f"<b>👤 Profilingiz</b>\n\n"
            f"<blockquote>{chr(10).join(details)}</blockquote>"
        )
        return text

    details = [
        f"🙍 <b>Имя:</b> {full_name}",
        f"🈯 <b>Язык:</b> {language}",
        f"📖 <b>Уровень:</b> {level}",
        f"🎯 <b>Текущий режим:</b> {learning_mode}",
        f"⭐ <b>Статус:</b> {status}",
        referral_count,
    ]
    if reminder_text:
        details.append(reminder_text)
    if is_paid and plan:
        details.append(f"💳 <b>Подписка:</b> {plan}")
        details.append(f"⌛ <b>Окончание:</b> {ends_str}")
    elif is_temporary_active and temporary_days is not None:
        details.append(f"⏳ <b>Пробный срок:</b> {_days_label(temporary_days, lang)}")
        details.append(f"⌛ <b>Окончание:</b> {ends_str}")
    text = (
        f"<b>👤 Ваш профиль</b>\n\n"
        f"<blockquote>{chr(10).join(details)}</blockquote>"
    )
    return text


async def _profile_referral_count(session, user) -> int:
    from app.repositories.referral_repo import ReferralRepository

    referral_repo = ReferralRepository(session)
    return await referral_repo.count_by_referrer(user.telegram_id)


def profile_menu_keyboard(lang: str, user=None) -> InlineKeyboardMarkup:
    labels = {
        "tj": {
            "subscription": "💎 Обуна",
            "language": "🌐 Забон",
            "level": "📊 Дараҷа",
        },
        "uz": {
            "subscription": "💎 Obuna",
            "language": "🌐 Til",
            "level": "📊 Daraja",
        },
        "ru": {
            "subscription": "💎 Подписка",
            "language": "🌐 Язык",
            "level": "📊 Уровень",
        },
    }
    l = labels.get(lang, labels["ru"])
    rows = [
            [
                InlineKeyboardButton(text=l["subscription"], callback_data="subscription:open"),
                InlineKeyboardButton(text=l["language"], callback_data="profile_menu:language"),
            ],
            [
                InlineKeyboardButton(text=l["level"], callback_data="profile_menu:level"),
            ],
    ]
    mode_button = (
        InlineKeyboardButton(text=t("profile_to_qa_button", lang), callback_data="profile_menu:qa")
        if getattr(user, "learning_mode", "qa") == "course"
        else InlineKeyboardButton(text=t("profile_to_course_button", lang), callback_data="profile_menu:course")
    )
    rows.append([
        InlineKeyboardButton(text=t("menu_partner", lang), callback_data="partner:open"),
        mode_button,
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("profile"))
async def profile_command(message: Message, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    lang = _lang(user)

    if not user:
        await message.answer(t("user_not_found", lang))
        return

    await _clear_voice_mode(user, session, state)
    referral_total = await _profile_referral_count(session, user)
    reminder_text = await _profile_reminder_text(session, user, lang)
    text = _profile_text(user, lang, referral_total, reminder_text)
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=profile_menu_keyboard(lang, user),
    )


@router.message(Command("subscription"))
async def subscription_command_handler(message: Message, state: FSMContext, session):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user:
        return

    lang = user.language if user.language else "ru"
    await _clear_voice_mode(user, session, state)

    await message.answer(
        t("payment_method_choose", lang),
        reply_markup=payment_method_keyboard(lang),
        parse_mode="HTML",
    )



def command_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇹🇯 Тоҷикӣ", callback_data="cmdlang:tj"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="cmdlang:ru"),
                InlineKeyboardButton(text="🇺🇿 O‘zbek", callback_data="cmdlang:uz"),
            ]
        ]
    )


@router.message(Command("language"))
async def language_command_handler(message: Message, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    lang = getattr(user, "language", None) or "ru"
    await _clear_voice_mode(user, session, state)

    await message.answer(
        t("choose_language", lang),
        reply_markup=command_language_keyboard(),
    )


@router.callback_query(F.data.startswith("cmdlang:"))
async def command_language_callback_handler(callback: CallbackQuery, session):
    lang = callback.data.split(":")[1]

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    user.language = lang
    await session.commit()

    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(t("language_selected", lang))



def command_level_keyboard(lang: str):
    kb = level_keyboard(lang)
    for row in kb.inline_keyboard:
        for btn in row:
            if btn.callback_data and btn.callback_data.startswith("level:"):
                btn.callback_data = btn.callback_data.replace("level:", "cmdlevel:", 1)
    return kb


@router.message(Command("level"))
async def level_command_handler(message: Message, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    lang = getattr(user, "language", None) or "ru"
    await _clear_voice_mode(user, session, state)

    await message.answer(
        t("choose_level", lang),
        reply_markup=command_level_keyboard(lang),
    )


@router.callback_query(F.data.startswith("cmdlevel:"))
async def command_level_callback_handler(callback: CallbackQuery, session):
    level = callback.data.split(":", 1)[1]

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    user.level = level
    await session.commit()

    lang = getattr(user, "language", None) or "ru"

    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    level_label = level.upper() if level.startswith("hsk") else level

    if lang == "tj":
        msg = f"✅ Дараҷа нав шуд: {level_label}"
    elif lang == "uz":
        msg = f"✅ Daraja yangilandi: {level_label}"
    else:
        msg = f"✅ Уровень обновлён: {level_label}"

    await callback.message.answer(msg)



@router.message(Command("invite"))
async def invite_command_handler(message: Message, state: FSMContext, session):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        return

    await _clear_voice_mode(user, session, state)
    referral_service = ReferralService(session)
    lang, text = await referral_service.build_trial_progress_text(user)
    await session.commit()

    sent = await message.answer(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await referral_service.remember_trial_progress_message(
        user,
        chat_id=sent.chat.id,
        message_id=sent.message_id,
    )



@router.message(Command("help"))
async def help_command_handler(message: Message, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    lang = getattr(user, "language", None) or "ru"
    await _clear_voice_mode(user, session, state)

    await message.answer(
        t("help_section_text", lang),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@router.message(Command("admin_stats"))
async def admin_stats_handler(message: Message, session):
    from app.config import settings

    admin_ids = [int(x.strip()) for x in settings.ADMIN_IDS.split(",") if x.strip()]
    if message.from_user.id not in admin_ids:
        return

    # Count users by status
    result = await session.execute(
        select(User.status, func.count().label("cnt")).group_by(User.status)
    )
    status_counts = {row.status: row.cnt for row in result.fetchall()}

    # Count users by language
    result = await session.execute(
        select(User.language, func.count().label("cnt")).group_by(User.language)
    )
    lang_counts = {row.language: row.cnt for row in result.fetchall()}

    # Total users
    result = await session.execute(select(func.count()).select_from(User))
    total = result.scalar() or 0

    # Users who asked at least 1 question
    result = await session.execute(
        select(func.count()).select_from(User).where(User.questions_used > 0)
    )
    active_users = result.scalar() or 0

    # Users registered in last 7 days
    from datetime import datetime, timezone, timedelta
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    result = await session.execute(
        select(func.count()).select_from(User).where(User.created_at >= week_ago)
    )
    new_this_week = result.scalar() or 0

    # Pending payments
    from app.db.models.payment import Payment
    result = await session.execute(
        select(func.count()).select_from(Payment).where(Payment.payment_status == "pending")
    )
    pending_payments = result.scalar() or 0

    # Approved payments total
    result = await session.execute(
        select(func.count()).select_from(Payment).where(Payment.payment_status == "approved")
    )
    total_paid = result.scalar() or 0

    trial = status_counts.get("trial", 0)
    active = status_counts.get("active", 0)
    expired = status_counts.get("expired", 0)
    blocked = status_counts.get("blocked", 0)

    conversion = round(active / total * 100, 1) if total > 0 else 0
    engagement = round(active_users / total * 100, 1) if total > 0 else 0

    lang_str = " | ".join(f"{k}: {v}" for k, v in sorted(lang_counts.items()))

    text = (
        f"📊 <b>Admin statistika</b>\n\n"
        f"<b>👥 Foydalanuvchilar:</b>\n"
        f"  Jami: {total}\n"
        f"  Trial: {trial}\n"
        f"  Aktiv obuna: {active}\n"
        f"  Tugagan: {expired}\n"
        f"  Bloklangan: {blocked}\n\n"
        f"<b>📈 Konversiya:</b>\n"
        f"  Trial → Obuna: {conversion}%\n"
        f"  Savol berganlar: {active_users} ({engagement}%)\n"
        f"  Bu hafta yangilar: +{new_this_week}\n\n"
        f"<b>💳 To'lovlar:</b>\n"
        f"  Kutilmoqda: {pending_payments}\n"
        f"  Jami tasdiqlangan: {total_paid}\n\n"
        f"<b>🌐 Tillar:</b>\n"
        f"  {lang_str}"
    )

    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "profile_menu:language")
async def profile_menu_language(callback: CallbackQuery, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "ru"
    await _clear_voice_mode(user, session, state)
    await callback.answer()
    await callback.message.answer(
        t("choose_language", lang),
        reply_markup=command_language_keyboard(),
    )

@router.callback_query(F.data == "profile_menu:level")
async def profile_menu_level(callback: CallbackQuery, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "ru"
    await _clear_voice_mode(user, session, state)
    await callback.answer()
    await callback.message.answer(
        t("choose_level", lang),
        reply_markup=command_level_keyboard(lang),
    )

@router.callback_query(F.data == "profile_menu:course")
async def profile_menu_course(callback: CallbackQuery, state: FSMContext, session):
    from app.bot.handlers.course import run_course_entry_flow
    await state.update_data(pending_voice_transcript=None, pending_voice_message_id=None)
    await callback.answer()
    await run_course_entry_flow(
        session=session,
        telegram_id=callback.from_user.id,
        respond=callback.message.answer,
    )

@router.callback_query(F.data == "profile_menu:qa")
async def profile_menu_qa(callback: CallbackQuery, state: FSMContext, session):
    from app.repositories.user_repo import UserRepository as UR
    user_repo = UR(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return
    user.learning_mode = "qa"
    user.voice_mode = "none"
    await state.update_data(pending_voice_transcript=None, pending_voice_message_id=None)
    await session.commit()
    lang = user.language if user.language else "ru"
    await callback.answer()
    await callback.message.answer(
        t("send_first_message", lang),
        reply_markup=main_menu_keyboard(lang),
    )

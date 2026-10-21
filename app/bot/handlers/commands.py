import asyncio

from app.bot.keyboards.onboarding import level_keyboard
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from sqlalchemy import and_, or_, select, func
from app.db.models.user import User

from app.repositories.user_repo import UserRepository
from app.services.conversion_funnel_service import ConversionFunnelService
from app.services.course_miniapp_admin_analytics_service import CourseMiniAppAdminAnalyticsService
from app.services.course_levels import TRACK_HSK30, level_spec
from app.services.course_track_service import CourseTrackError, CourseTrackService
from app.services.hsk30_feature_service import Hsk30FeatureService
from app.services.referral_service import ReferralService
from app.bot.keyboards.subscription import (
    subscription_miniapp_button,
    subscription_miniapp_keyboard,
)
from app.bot.handlers.android_app import reply_chat_id
from app.bot.utils.course_miniapp import course_v3_miniapp_url
from app.bot.keyboards.help import help_contact_keyboard
from app.bot.utils.i18n import bot_locale_map, t
from app.bot.utils.qa_entry import send_qa_entry
from app.services.course_reminder_service import reminder_tz_label
from app.services.help_settings_service import build_help_text
from app.services.message_draft_service import (
    finish_draft_if_needed,
    send_draft_or_fallback,
    update_draft_or_fallback,
)
from app.services.support_contact_service import get_admin_contact_url
from app.services.rich_message_service import RichMessageService
from app.config import settings


router = Router()


def _lang(user) -> str:
    return user.language if user and user.language else "ru"


async def _clear_voice_mode(user, session, state: FSMContext | None = None) -> None:
    if state:
        await state.update_data(pending_voice_transcript=None, pending_voice_message_id=None)
    if user and (getattr(user, "voice_mode", "none") or "none") != "none":
        user.voice_mode = "none"
        await session.commit()




def _pct(part: int, total: int) -> float:
    return round(part / total * 100, 1) if total > 0 else 0.0


def _status_label(status: str, lang: str) -> str:
    return {
        "free": bot_locale_map('inline.handlers.commands.helper_status_label.copy1').get(lang, "Bepul"),
        "trial": bot_locale_map('inline.handlers.commands.helper_status_label.copy2').get(lang, "Sinov rejimi"),
        "active": bot_locale_map('inline.handlers.commands.helper_status_label.copy3').get(lang, "Faol"),
        "expired": bot_locale_map('inline.handlers.commands.helper_status_label.copy4').get(lang, "Muddati tugagan"),
        "blocked": bot_locale_map('inline.handlers.commands.helper_status_label.copy5').get(lang, "Заблокирован"),
    }.get(status, bot_locale_map('inline.handlers.commands.helper_status_label.copy6').get(lang, "Bepul"))


def _profile_status_label(user, lang: str) -> str:
    status = str(getattr(user, "status", "") or "")
    is_paid = getattr(user, "payment_status", "") == "approved"

    if status == "active" and is_paid:
        return bot_locale_map('inline.handlers.commands.helper_profile_status_label.copy1').get(lang, "To'lov faol")

    if status == "active":
        return bot_locale_map('inline.handlers.commands.helper_profile_status_label.copy2').get(lang, "Bepul test ruxsati")

    return _status_label(status, lang)


def _language_label(value: str, lang: str) -> str:
    labels = bot_locale_map('inline.handlers.commands.helper_language_label.copy1')
    unknown = bot_locale_map('inline.handlers.commands.helper_language_label.copy2')
    return labels.get(lang, labels["ru"]).get(value, unknown.get(lang, unknown["ru"]))


def _level_label(value: str, lang: str) -> str:
    if not value:
        return "—"
    if value.startswith("hsk"):
        return value.upper()
    beginner = bot_locale_map('inline.handlers.commands.helper_level_label.copy1')
    return beginner.get(lang, beginner["ru"]) if value == "beginner" else value




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


def _profile_copy(key: str, lang: str, **values) -> str:
    # Existing Bot profile paths use Russian for unsupported language codes.
    locale = lang if lang in ("uz", "ru", "tj") else "ru"
    return t("bot.profile." + key, locale, **values)


def _referral_count_label(total: int, lang: str) -> str:
    if lang == "tj":
        return _profile_copy('referralCount', 'tj', total=total)
    if lang == "ru":
        return _profile_copy('referralCount', 'ru', total=total)
    return _profile_copy('referralCount', 'uz', total=total)


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

    tz_text = reminder_tz_label(progress)

    label = bot_locale_map('inline.handlers.commands.helper_profile_reminder_line.copy1').get(lang, "Напоминание")
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
                "10_days": _profile_copy('plan10Days', lang),
                "1_month": _profile_copy('plan1Month', lang),
                "monthly": _profile_copy('plan1Month', lang),
            }
        elif lang == "uz":
            plan_map = {
                "10_days": _profile_copy('plan10Days', lang),
                "1_month": _profile_copy('plan1Month', lang),
                "monthly": _profile_copy('plan1Month', lang),
            }
        else:
            plan_map = {
                "10_days": _profile_copy('plan10Days', lang),
                "1_month": _profile_copy('plan1Month', lang),
                "monthly": _profile_copy('plan1Month', lang),
            }
        plan_label = plan_map.get(plan_key, "")
    elif is_paid:
        if duration_days is not None and 9 <= duration_days <= 11:
            plan_label = _profile_copy('plan10Days', lang) if lang == "tj" else (_profile_copy('plan10Days', lang) if lang == "uz" else _profile_copy('plan10Days', lang))
        elif duration_days is not None and 28 <= duration_days <= 31:
            plan_label = _profile_copy('plan1Month', lang) if lang == "tj" else (_profile_copy('plan1Month', lang) if lang == "uz" else _profile_copy('plan1Month', lang))
        else:
            plan_label = _profile_copy('activePlan', lang) if lang == "tj" else (_profile_copy('activePlan', lang) if lang == "uz" else _profile_copy('activePlan', lang))

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
            _profile_copy('name', lang, full_name=full_name),
            _profile_copy('language', lang, language=language),
            _profile_copy('level', lang, level=level),
            _profile_copy('status', lang, status=status),
            referral_count,
        ]
        if reminder_text:
            details.append(reminder_text)
        if is_paid and plan:
            details.append(_profile_copy('subscription', lang, plan=plan))
            details.append(_profile_copy('end', lang, ends_str=ends_str))
        elif is_temporary_active and temporary_days is not None:
            details.append(_profile_copy('trial', lang))
            details.append(_profile_copy('end', lang, ends_str=ends_str))
        text = (
            _profile_copy('header', lang) +
            f"<blockquote>{chr(10).join(details)}</blockquote>"
        )
        return text

    if lang == "uz":
        details = [
            _profile_copy('name', lang, full_name=full_name),
            _profile_copy('language', lang, language=language),
            _profile_copy('level', lang, level=level),
            _profile_copy('status', lang, status=status),
            referral_count,
        ]
        if reminder_text:
            details.append(reminder_text)
        if is_paid and plan:
            details.append(_profile_copy('subscription', lang, plan=plan))
            details.append(_profile_copy('end', lang, ends_str=ends_str))
        elif is_temporary_active and temporary_days is not None:
            details.append(_profile_copy('trial', lang))
            details.append(_profile_copy('end', lang, ends_str=ends_str))
        text = (
            _profile_copy('header', lang) +
            f"<blockquote>{chr(10).join(details)}</blockquote>"
        )
        return text

    details = [
        _profile_copy('name', lang, full_name=full_name),
        _profile_copy('language', lang, language=language),
        _profile_copy('level', lang, level=level),
        _profile_copy('status', lang, status=status),
        referral_count,
    ]
    if reminder_text:
        details.append(reminder_text)
    if is_paid and plan:
        details.append(_profile_copy('subscription', lang, plan=plan))
        details.append(_profile_copy('end', lang, ends_str=ends_str))
    elif is_temporary_active and temporary_days is not None:
        details.append(_profile_copy('trial', lang))
        details.append(_profile_copy('end', lang, ends_str=ends_str))
    text = (
        _profile_copy('header', lang) +
        f"<blockquote>{chr(10).join(details)}</blockquote>"
    )
    return text


async def _profile_referral_count(session, user) -> int:
    from app.repositories.referral_repo import ReferralRepository

    referral_repo = ReferralRepository(session)
    return await referral_repo.count_by_referrer(user.telegram_id)


APPS_MENU_CALLBACK = "profile_menu:apps"


def apps_button(lang: str) -> InlineKeyboardButton:
    """One button, and the Mini App card behind it does the rest.

    The chooser that used to sit here asked the learner to name their device
    before they had seen anything, and then handed each device off a different
    way. The card in the Mini App profile already carries every client —
    macOS, Windows and Android side by side — and Android is still handed over
    in this chat: pressing it there closes the Mini App and the APK lands in
    the chat the learner came from.
    """

    return InlineKeyboardButton(
        text=t("apps_menu_button", lang),
        web_app=WebAppInfo(
            url=course_v3_miniapp_url(
                lang=lang,
                tab="profile",
                focus_desktop_download=True,
            )
        ),
    )


def apps_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """The same card, for an older profile message that still points here."""

    return InlineKeyboardMarkup(inline_keyboard=[[apps_button(lang)]])


def profile_menu_keyboard(lang: str, user=None) -> InlineKeyboardMarkup:
    labels = bot_locale_map('inline.handlers.commands.profile_menu_keyboard.copy1')
    l = labels.get(lang, labels["ru"])
    rows = [
        [
            subscription_miniapp_button(
                lang,
                source="profile_subscription",
                mode="subscription",
                text=l["subscription"],
            ),
            InlineKeyboardButton(text=l["language"], callback_data="profile_menu:language"),
        ],
        [
            InlineKeyboardButton(text=l["level"], callback_data="profile_menu:level"),
            InlineKeyboardButton(text=t("menu_partner", lang), callback_data="partner:open"),
        ],
        [
            apps_button(lang),
        ],
        [
            # Profil ostidagi tugma kursni BIR bosishda ochadi (oraliq xabar
            # yo'q) — resume=1 orqali foydalanuvchi turgan qismga tushadi.
            InlineKeyboardButton(
                text=t("profile_to_course_button", lang),
                web_app=WebAppInfo(url=course_v3_miniapp_url(lang=lang, resume=True, tab="course")),
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("rich_test"))
async def rich_test_command(message: Message, bot: Bot):
    rich_service = RichMessageService(settings.BOT_TOKEN)
    
    # 1. Vocabulary Test
    vocab_payload = rich_service.build_vocab_rich_message(
        word="学习",
        pinyin="xuéxí",
        translation="O'qish, o'rganish",
        examples=["我喜欢学习汉语 (Men xitoy tilini o'rganishni yoqtiraman)"],
        mistakes="xuéxí ni 'o'qituvchi' deb ishlatmang."
    )
    await message.answer("🧪 <b>Test 1: Vocabulary Rich Message</b>", parse_mode="HTML")
    await rich_service.send_rich_or_fallback(
        bot, message.chat.id, vocab_payload, "Vocabulary Fallback: 学习 (xuéxí) - O'qish"
    )

    # 2. Grammar Test
    grammar_payload = rich_service.build_grammar_rich_message(
        title="'了' (le) qo'shimchasi",
        formula="S + V + 了 + O",
        explanation="Harakat tugallanganini bildiradi.",
        examples=["我吃饭了 (Men ovqat yedim)"],
        common_mistakes="Kelajakdagi harakatlar uchun '了' ishlatmang."
    )
    await message.answer("\n🧪 <b>Test 2: Grammar Rich Message</b>", parse_mode="HTML")
    await rich_service.send_rich_or_fallback(
        bot, message.chat.id, grammar_payload, "Grammar Fallback: '了' (le) - Harakat tugallangan"
    )

    # 3. Quiz Result Test
    quiz_payload = rich_service.build_quiz_result_rich_message(
        score=8,
        total=10,
        weak_points=["Tonlar", "Yozish"],
        wrong_answers=["savol_3", "savol_7"]
    )
    await message.answer("\n🧪 <b>Test 3: Quiz Result Rich Message</b>", parse_mode="HTML")
    await rich_service.send_rich_or_fallback(
        bot, message.chat.id, quiz_payload, "Quiz Result Fallback: 8/10"
    )

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
        t("subscription_miniapp_entry_text", lang),
        reply_markup=subscription_miniapp_keyboard(lang, source="command_subscription", mode="subscription"),
        parse_mode="HTML",
    )



def command_language_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("language_picker_tj", language), callback_data="cmdlang:tj"
                ),
                InlineKeyboardButton(
                    text=t("language_picker_ru", language), callback_data="cmdlang:ru"
                ),
                InlineKeyboardButton(
                    text=t("language_picker_uz", language), callback_data="cmdlang:uz"
                ),
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
        reply_markup=command_language_keyboard(lang),
    )


@router.callback_query(F.data.startswith("cmdlang:"))
async def command_language_callback_handler(callback: CallbackQuery, session):
    if callback.data not in {"cmdlang:uz", "cmdlang:ru", "cmdlang:tj"}:
        await callback.answer()
        return
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



async def command_level_keyboard(user, session, lang: str):
    track = CourseTrackService.track_for_level(getattr(user, "level", None))
    if track == TRACK_HSK30:
        levels = list(await Hsk30FeatureService(session).live_levels())
    else:
        levels = ["beginner", "hsk1", "hsk2", "hsk3", "hsk4"]
    kb = level_keyboard(lang, levels=levels)
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
        reply_markup=await command_level_keyboard(user, session, lang),
    )


@router.callback_query(F.data.startswith("cmdlevel:"))
async def command_level_callback_handler(callback: CallbackQuery, session):
    level = callback.data.split(":", 1)[1]

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    lang = getattr(user, "language", None) or "ru"
    try:
        await CourseTrackService(session).change_level(user, level)
        await session.commit()
    except CourseTrackError:
        await session.rollback()
        messages = bot_locale_map('inline.handlers.commands.command_level_callback_handler.copy1')
        await callback.answer(messages.get(lang, messages["ru"]), show_alert=True)
        return

    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    spec = level_spec(level)
    level_label = (
        f"HSK 3.0 · N{spec.band}"
        if spec and spec.track == TRACK_HSK30
        else (f"HSK {spec.band}" if spec else level)
    )

    if lang == "tj":
        msg = _profile_copy('levelUpdated', lang, level_label=level_label)
    elif lang == "uz":
        msg = _profile_copy('levelUpdated', lang, level_label=level_label)
    else:
        msg = _profile_copy('levelUpdated', lang, level_label=level_label)

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
    contact_url = await get_admin_contact_url(session)

    await message.answer(
        await build_help_text(session, lang),
        reply_markup=help_contact_keyboard(lang, contact_url),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@router.message(Command("draft_test"))
async def draft_test_handler(message: Message):
    chat_id = message.chat.id
    await send_draft_or_fallback(
        message.bot,
        chat_id,
        "Draft test: preparing reply...",
        draft_id=message.message_id,
        source_message=message,
        fallback_mode="qa",
        seed=message.message_id,
    )
    try:
        for preview in (
            "Draft test: analyzing question...",
            "Draft test: preparing examples...",
            "Draft test: finalizing answer...",
        ):
            await asyncio.sleep(1.3)
            await update_draft_or_fallback(message.bot, chat_id, preview)
    finally:
        await finish_draft_if_needed(message.bot, chat_id)

    await message.answer(
        "Draft test complete. Final message was sent through normal sendMessage flow."
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
    now = datetime.now(timezone.utc)
    today = now.date()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
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

    # Tasdiqlangan to'lovlar jami
    result = await session.execute(
        select(func.count()).select_from(Payment).where(Payment.payment_status == "approved")
    )
    total_paid = result.scalar() or 0
    paid_users = (await session.execute(
        select(func.count()).select_from(User).where(
            User.payment_status == "approved",
            User.status == "active",
            User.end_date.is_not(None),
            User.end_date > now,
        )
    )).scalar() or 0
    historical_approved_users = (await session.execute(
        select(func.count()).select_from(User).where(User.payment_status == "approved")
    )).scalar() or 0
    funnel_text = await ConversionFunnelService(session).admin_funnel_text(week_ago=week_ago)
    course_miniapp_text = await CourseMiniAppAdminAnalyticsService(session).admin_text(week_ago=week_ago)
    trial_course_started = (await session.execute(
        select(func.count()).select_from(User).where(User.trial_course_started_at.is_not(None))
    )).scalar() or 0
    trial_course_completed = (await session.execute(
        select(func.count()).select_from(User).where(User.trial_course_completed_at.is_not(None))
    )).scalar() or 0
    trial_quiz_explained = (await session.execute(
        select(func.count()).select_from(User).where(User.trial_quiz_explanation_used_at.is_not(None))
    )).scalar() or 0
    force_sub_checkpoint = (await session.execute(
        select(func.count()).select_from(User).where(User.force_sub_required_at.is_not(None))
    )).scalar() or 0
    checkpoint_completed = (await session.execute(
        select(func.count()).select_from(User).where(
            User.force_sub_required_at.is_not(None),
            User.trial_course_completed_at.is_not(None),
            User.trial_course_completed_at >= User.force_sub_required_at,
        )
    )).scalar() or 0
    trial_paid_after_start = (await session.execute(
        select(func.count(func.distinct(User.id)))
        .select_from(Payment)
        .join(User, or_(Payment.user_id == User.id, and_(Payment.user_id.is_(None), User.telegram_id > 0, User.telegram_id == Payment.user_telegram_id)))
        .where(
            Payment.payment_status == "approved",
            Payment.reviewed_at.is_not(None),
            User.trial_course_started_at.is_not(None),
            Payment.reviewed_at >= User.trial_course_started_at,
        )
    )).scalar() or 0
    trial_revenue_after_start = (await session.execute(
        select(func.sum(Payment.amount))
        .select_from(Payment)
        .join(User, or_(Payment.user_id == User.id, and_(Payment.user_id.is_(None), User.telegram_id > 0, User.telegram_id == Payment.user_telegram_id)))
        .where(
            Payment.payment_status == "approved",
            Payment.reviewed_at.is_not(None),
            User.trial_course_started_at.is_not(None),
            Payment.reviewed_at >= User.trial_course_started_at,
        )
    )).scalar() or 0
    checkpoint_paid_after = (await session.execute(
        select(func.count(func.distinct(User.id)))
        .select_from(Payment)
        .join(User, or_(Payment.user_id == User.id, and_(Payment.user_id.is_(None), User.telegram_id > 0, User.telegram_id == Payment.user_telegram_id)))
        .where(
            Payment.payment_status == "approved",
            Payment.reviewed_at.is_not(None),
            User.force_sub_required_at.is_not(None),
            Payment.reviewed_at >= User.force_sub_required_at,
        )
    )).scalar() or 0
    completed_paid_after = (await session.execute(
        select(func.count(func.distinct(User.id)))
        .select_from(Payment)
        .join(User, or_(Payment.user_id == User.id, and_(Payment.user_id.is_(None), User.telegram_id > 0, User.telegram_id == Payment.user_telegram_id)))
        .where(
            Payment.payment_status == "approved",
            Payment.reviewed_at.is_not(None),
            User.trial_course_completed_at.is_not(None),
            Payment.reviewed_at >= User.trial_course_completed_at,
        )
    )).scalar() or 0
    trial_started_week = (await session.execute(
        select(func.count()).select_from(User).where(User.trial_course_started_at >= week_ago)
    )).scalar() or 0
    trial_completed_week = (await session.execute(
        select(func.count()).select_from(User).where(User.trial_course_completed_at >= week_ago)
    )).scalar() or 0
    trial_paid_week = (await session.execute(
        select(func.count(func.distinct(User.id)))
        .select_from(Payment)
        .join(User, or_(Payment.user_id == User.id, and_(Payment.user_id.is_(None), User.telegram_id > 0, User.telegram_id == Payment.user_telegram_id)))
        .where(
            Payment.payment_status == "approved",
            Payment.reviewed_at >= week_ago,
            User.trial_course_started_at.is_not(None),
            Payment.reviewed_at >= User.trial_course_started_at,
        )
    )).scalar() or 0
    daily_started = (await session.execute(
        select(func.count()).select_from(User).where(User.daily_practice_started_at.is_not(None))
    )).scalar() or 0
    daily_started_today = (await session.execute(
        select(func.count()).select_from(User).where(User.daily_practice_started_at >= today_start)
    )).scalar() or 0
    daily_started_week = (await session.execute(
        select(func.count()).select_from(User).where(User.daily_practice_started_at >= week_ago)
    )).scalar() or 0
    daily_completed = (await session.execute(
        select(func.count()).select_from(User).where(User.daily_practice_completed_at.is_not(None))
    )).scalar() or 0
    daily_completed_today = (await session.execute(
        select(func.count()).select_from(User).where(User.daily_practice_last_day == today)
    )).scalar() or 0
    daily_completed_week = (await session.execute(
        select(func.count()).select_from(User).where(User.daily_practice_completed_at >= week_ago)
    )).scalar() or 0
    daily_d2_return = (await session.execute(
        select(func.count()).select_from(User).where(User.daily_practice_streak >= 2)
    )).scalar() or 0
    daily_completed_course_opened = (await session.execute(
        select(func.count()).select_from(User).where(
            User.daily_practice_completed_at.is_not(None),
            User.trial_course_started_at.is_not(None),
            User.trial_course_started_at >= User.daily_practice_completed_at,
        )
    )).scalar() or 0
    daily_completed_paid = (await session.execute(
        select(func.count(func.distinct(User.id)))
        .select_from(Payment)
        .join(User, or_(Payment.user_id == User.id, and_(Payment.user_id.is_(None), User.telegram_id > 0, User.telegram_id == Payment.user_telegram_id)))
        .where(
            Payment.payment_status == "approved",
            Payment.reviewed_at.is_not(None),
            User.daily_practice_completed_at.is_not(None),
            Payment.reviewed_at >= User.daily_practice_completed_at,
        )
    )).scalar() or 0
    qa_limit_channel_joined = (await session.execute(
        select(func.count()).select_from(User).where(
            User.force_sub_required_at.is_not(None),
            User.last_active_at >= User.force_sub_required_at,
        )
    )).scalar() or 0

    daily_started = (await session.execute(
        select(func.count()).select_from(User).where(User.daily_practice_started_at.is_not(None))
    )).scalar() or 0
    daily_started_today = (await session.execute(
        select(func.count()).select_from(User).where(User.daily_practice_started_at >= today_start)
    )).scalar() or 0
    daily_started_week = (await session.execute(
        select(func.count()).select_from(User).where(User.daily_practice_started_at >= week_ago)
    )).scalar() or 0
    daily_completed = (await session.execute(
        select(func.count()).select_from(User).where(User.daily_practice_completed_at.is_not(None))
    )).scalar() or 0
    daily_completed_today = (await session.execute(
        select(func.count()).select_from(User).where(User.daily_practice_last_day == today)
    )).scalar() or 0
    daily_completed_week = (await session.execute(
        select(func.count()).select_from(User).where(User.daily_practice_completed_at >= week_ago)
    )).scalar() or 0
    daily_d2_return = (await session.execute(
        select(func.count()).select_from(User).where(User.daily_practice_streak >= 2)
    )).scalar() or 0
    daily_completed_course_opened = (await session.execute(
        select(func.count()).select_from(User).where(
            User.daily_practice_completed_at.is_not(None),
            User.trial_course_started_at.is_not(None),
            User.trial_course_started_at >= User.daily_practice_completed_at,
        )
    )).scalar() or 0
    daily_completed_paid = (await session.execute(
        select(func.count(func.distinct(User.id)))
        .select_from(Payment)
        .join(User, or_(Payment.user_id == User.id, and_(Payment.user_id.is_(None), User.telegram_id > 0, User.telegram_id == Payment.user_telegram_id)))
        .where(
            Payment.payment_status == "approved",
            Payment.reviewed_at.is_not(None),
            User.daily_practice_completed_at.is_not(None),
            Payment.reviewed_at >= User.daily_practice_completed_at,
        )
    )).scalar() or 0
    qa_limit_channel_joined = (await session.execute(
        select(func.count()).select_from(User).where(
            User.force_sub_required_at.is_not(None),
            User.last_active_at >= User.force_sub_required_at,
        )
    )).scalar() or 0

    trial = status_counts.get("trial", 0)
    active = status_counts.get("active", 0)
    expired = status_counts.get("expired", 0)
    blocked = status_counts.get("blocked", 0)

    conversion = _pct(paid_users, total)
    engagement = _pct(active_users, total)
    trial_complete_rate = _pct(trial_course_completed, trial_course_started)
    trial_ai_rate = _pct(trial_quiz_explained, trial_course_started)
    trial_paid_rate = _pct(trial_paid_after_start, trial_course_started)
    completed_paid_rate = _pct(completed_paid_after, trial_course_completed)
    checkpoint_complete_rate = _pct(checkpoint_completed, force_sub_checkpoint)
    checkpoint_paid_rate = _pct(checkpoint_paid_after, force_sub_checkpoint)
    daily_complete_rate = _pct(daily_completed, daily_started)
    daily_return_rate = _pct(daily_d2_return, daily_completed)
    daily_course_rate = _pct(daily_completed_course_opened, daily_completed)
    daily_paid_rate = _pct(daily_completed_paid, daily_completed)
    qa_channel_join_rate = _pct(qa_limit_channel_joined, force_sub_checkpoint)

    lang_str = " | ".join(f"{k}: {v}" for k, v in sorted(lang_counts.items()))

    text = (
        f"📊 <b>Admin statistika</b>\n\n"
        f"<b>👥 Foydalanuvchilar:</b>\n"
        f"  Jami: {total}\n"
        f"  Sinov: {trial}\n"
        f"  Faol status: {active}\n"
        f"  To'lovli user: {paid_users}\n"
        f"  Tarixiy tasdiqlangan: {historical_approved_users}\n"
        f"  Tugagan: {expired}\n"
        f"  Bloklangan: {blocked}\n\n"
        f"<b>⚡ Daily 3-min retention:</b>\n"
        f"  Boshladi: {daily_started} | bugun: +{daily_started_today} | 7 kun: +{daily_started_week}\n"
        f"  Tugatdi: {daily_completed} ({daily_complete_rate}%) | bugun: +{daily_completed_today} | 7 kun: +{daily_completed_week}\n"
        f"  D1 → D2 qaytdi: {daily_d2_return} ({daily_return_rate}%)\n"
        f"  Daily → Kurs: {daily_completed_course_opened} ({daily_course_rate}%)\n"
        f"  Daily → Paid: {daily_completed_paid} ({daily_paid_rate}%)\n"
        f"  QA limit → kanal: {force_sub_checkpoint} | joined/continued: {qa_limit_channel_joined} ({qa_channel_join_rate}%)\n\n"
        f"<b>📚 Sinov kurs funnel:</b>\n"
        f"  Dars boshlagan: {trial_course_started} | 7 kun: +{trial_started_week}\n"
        f"  Dars tugatgan: {trial_course_completed} ({trial_complete_rate}%) | 7 kun: +{trial_completed_week}\n"
        f"  AI xato tahlili: {trial_quiz_explained} ({trial_ai_rate}%)\n"
        f"  Kanal checkpoint: {force_sub_checkpoint}\n"
        f"  Checkpoint → tugatdi: {checkpoint_completed} ({checkpoint_complete_rate}%)\n\n"
        f"<b>💰 Sinov → To'lov:</b>\n"
        f"  Trialdan keyin paid: {trial_paid_after_start} ({trial_paid_rate}%) | 7 kun: +{trial_paid_week}\n"
        f"  Completed → paid: {completed_paid_after} ({completed_paid_rate}%)\n"
        f"  Checkpoint → paid: {checkpoint_paid_after} ({checkpoint_paid_rate}%)\n"
        f"  Trialdan keyingi tushum: {int(trial_revenue_after_start):,} so'm\n\n"
        f"{funnel_text}\n\n"
        f"{course_miniapp_text}\n\n"
        f"<b>📈 Konversiya:</b>\n"
        f"  User → Paid: {conversion}%\n"
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
        reply_markup=command_language_keyboard(lang),
    )

@router.callback_query(F.data == APPS_MENU_CALLBACK)
async def profile_menu_apps(callback: CallbackQuery, state: FSMContext, session):
    """Nothing produces this callback any more — an old profile still does.

    The profile keyboard is exactly the kind of message a learner scrolls back
    to weeks later, and the button there is now a Mini App button. This keeps
    the old one working instead of leaving it to spin and do nothing.
    """

    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "ru"
    await _clear_voice_mode(user, session, state)
    await callback.answer()
    # Not `callback.message.answer`: the profile keyboard is exactly the kind
    # of message a learner scrolls back to weeks later, and Telegram stops
    # attaching a message to the callback once it is old enough.
    await callback.bot.send_message(
        reply_chat_id(callback),
        t("apps_menu_text", lang),
        reply_markup=apps_menu_keyboard(lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "profile_menu:level")
async def profile_menu_level(callback: CallbackQuery, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "ru"
    await _clear_voice_mode(user, session, state)
    await callback.answer()
    await callback.message.answer(
        t("choose_level", lang),
        reply_markup=await command_level_keyboard(user, session, lang),
    )

@router.callback_query(F.data == "profile_menu:course")
async def profile_menu_course(callback: CallbackQuery, state: FSMContext, session):
    from app.bot.handlers.course import send_course_miniapp_entry

    await callback.answer()
    await send_course_miniapp_entry(
        session=session,
        telegram_id=callback.from_user.id,
        respond=callback.message.answer,
        state=state,
        source="profile_course",
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
    await send_qa_entry(
        session=session,
        user=user,
        respond=callback.message.answer,
        lang=lang,
    )

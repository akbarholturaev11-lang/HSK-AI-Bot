from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
import json
import logging

from app.repositories.user_repo import UserRepository
from app.services.course_engine_service import (
    CourseEngineService,
    get_next_course_level,
    get_block_no_from_step,
    get_step_order,
    is_block_grammar_step,
    is_block_lesson,
    is_block_quiz_step,
    is_block_vocab_step,
)
from app.services.course_progress_summary_service import CourseProgressSummaryService
from app.services.access_service import AccessService
from app.services.conversion_funnel_service import ConversionFunnelService
from app.services.course_trial_service import CourseTrialService
from app.services.onboarding_tip_service import (
    OnboardingTipService,
    TIP_KEY_COURSE_DIALOGUE,
    TIP_KEY_COURSE_GRAMMAR,
    TIP_KEY_COURSE_VOCAB,
)
from app.services.required_channel_service import RequiredChannelService
from app.bot.utils.i18n import t
from app.bot.keyboards.course import (
    lesson_selection_keyboard, review_choice_keyboard,
    course_intro_keyboard, course_dialogue_keyboard,
    course_grammar_keyboard, course_homework_keyboard,
    course_next_step_keyboard, course_dialogue_n_keyboard,
    next_study_time_inline_keyboard,
    hsk4_part_selection_keyboard, filter_hsk4_lessons_by_part, normalize_hsk4_part,
)
from app.bot.keyboards.subscription import subscription_miniapp_keyboard
from app.bot.keyboards.course_context import (
    course_understood_keyboard,
    course_review_offer_keyboard,
    course_satisfaction_keyboard,
    course_homework_keyboard as _ctx_homework_keyboard,
    course_level_upgrade_keyboard,
    course_next_lesson_keyboard,
)
from app.bot.keyboards.course_miniapp import (
    course_homework_miniapp_keyboard,
    course_quiz_miniapp_keyboard,
    course_study_miniapp_keyboard,
    course_vocab_stroke_order_keyboard,
)

from app.config import COURSE_MODE_ENABLED
from app.bot.utils.course_miniapp import (
    format_miniapp_homework_intro,
    format_miniapp_quiz_intro,
    is_course_miniapp_supported,
)
from app.bot.utils.course_formatter import (
    format_intro, format_vocab, format_dialogue,
    format_grammar, format_exercise, format_step,
)
from app.bot.keyboards.main_menu import course_menu_keyboard, main_menu_keyboard
from app.bot.keyboards.course import course_reminder_timezone_keyboard
from app.bot.middlewares.required_channel import (
    FORCE_SUB_ACTION_OPEN_COURSE,
    FORCE_SUB_ACTION_OPEN_FREE_QA,
    PENDING_FORCE_SUB_ACTION,
    PENDING_FORCE_SUB_PAYLOAD,
)
from app.bot.fsm.onboarding import OnboardingStates, QA_MODE_LEVEL_CHOICE_KEY
from app.bot.keyboards.onboarding import level_keyboard
from app.bot.utils.workflow_message import (
    REMINDER_PANEL_CHAT_ID,
    REMINDER_PANEL_MSG_ID,
    edit_callback_workflow_message,
)
from datetime import datetime, time, timezone


logger = logging.getLogger(__name__)


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
                logger.exception("Failed to edit workflow message; falling back to answer")
        return await self._message.answer(text, **kwargs)


async def show_free_qa_level_choice(
    *,
    respond,
    state: FSMContext,
    lang: str,
) -> None:
    await state.update_data(
        **{
            QA_MODE_LEVEL_CHOICE_KEY: True,
            "pending_voice_transcript": None,
            "pending_voice_message_id": None,
        }
    )
    await state.set_state(OnboardingStates.choosing_level)
    await respond(
        t("choose_level", lang),
        reply_markup=level_keyboard(lang),
    )


def course_miniapp_entry_text(lang: str) -> str:
    texts = {
        "uz": (
            "📚 <b>HSK AI kursi Mini Appga ko‘chdi</b>\n\n"
            "<blockquote>Darslar, so‘zlar, grammatika, quiz va AI Voice bitta joyda.</blockquote>"
        ),
        "ru": (
            "📚 <b>Курс HSK AI переехал в Mini App</b>\n\n"
            "<blockquote>Уроки, слова, грамматика, квиз и AI Voice теперь в одном месте.</blockquote>"
        ),
        "tj": (
            "📚 <b>Курси HSK AI ба Mini App гузашт</b>\n\n"
            "<blockquote>Дарсҳо, калимаҳо, грамматика, quiz ва AI Voice дар як ҷо.</blockquote>"
        ),
    }
    return texts.get(lang, texts["ru"])


async def send_course_miniapp_entry(
    *,
    session,
    telegram_id: int,
    respond,
    state: FSMContext | None = None,
    source: str = "course_miniapp_entry",
    level: str | None = None,
    lesson: int | None = None,
    tab: str | None = None,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    lang = user.language if user and user.language else "ru"

    if user:
        user.learning_mode = "qa"
        user.voice_mode = "none"
        await session.commit()

    if state:
        await state.update_data(pending_voice_transcript=None, pending_voice_message_id=None)

    await respond(
        course_miniapp_entry_text(lang),
        reply_markup=course_study_miniapp_keyboard(
            lang,
            level=level or (getattr(user, "level", None) if user else None),
            lesson=lesson,
            tab=tab,
        ),
        parse_mode="HTML",
    )

    if user:
        await ConversionFunnelService().record(
            event_name="course_cta_seen",
            user=user,
            source=source,
            payload={"level": level or getattr(user, "level", None), "lesson": lesson, "tab": tab},
        )


async def _block_if_course_disabled(callback, session):
    if not COURSE_MODE_ENABLED:
        lang = "ru"
        try:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(callback.from_user.id)
            if user and user.language:
                lang = user.language
        except:
            pass

        msg_map = {
            "uz": "🚧 Kurs rejimi hozircha ishlab chiqilmoqda. Tez orada mavjud bo‘ladi.",
            "ru": "🚧 Режим курса сейчас в разработке. Скоро будет доступен.",
            "tj": "🚧 Реҷаи курс ҳоло дар навсози аст. Ба зудӣ дастрас мешавад.",
        }

        await callback.answer()
        await callback.message.answer(msg_map.get(lang, msg_map["ru"]))
        return True

    if callback.data != "course:back_to_qa":
        user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
        if user and not await _ensure_active_course_access(
            session=session,
            user=user,
            respond=callback.message.answer,
        ):
            await callback.answer()
            return True

    return False


router = Router()


def _course_locked_offer_text(lang: str) -> str:
    free_fallback = {
        "uz": "Obuna olmasangiz ham daily limit bilan savol-javobda davom etishingiz mumkin.",
        "ru": "Даже без подписки можно продолжить в вопрос-ответ с дневным лимитом.",
        "tj": "Бе обуна ҳам метавонед дар савол-ҷавоб бо лимити рӯзона давом диҳед.",
    }.get(lang, "Даже без подписки можно продолжить в вопрос-ответ с дневным лимитом.")
    return (
        f"<b>{t('course_locked_title', lang)}</b>\n\n"
        f"<blockquote>{t('course_locked_text', lang)}</blockquote>\n\n"
        f"{t('subscription_miniapp_entry_text', lang)}\n"
        f"{free_fallback}"
    )


async def _send_course_access_offer(*, respond, lang: str, expired_from_course: bool) -> None:
    if expired_from_course:
        await respond(
            t("course_only_active_users", lang),
            reply_markup=main_menu_keyboard(lang),
            parse_mode="HTML",
        )
        await respond(
            t("subscription_miniapp_entry_text", lang),
            reply_markup=subscription_miniapp_keyboard(
                lang,
                source="course_expired",
                mode="subscription",
                include_free_mode=True,
            ),
            parse_mode="HTML",
        )
        return

    await respond(
        _course_locked_offer_text(lang),
        reply_markup=subscription_miniapp_keyboard(
            lang,
            source="course_locked",
            mode="subscription",
            include_free_mode=True,
        ),
        parse_mode="HTML",
    )


async def _send_trial_locked_offer(*, respond, lang: str) -> None:
    await _send_course_access_offer(
        respond=respond,
        lang=lang,
        expired_from_course=False,
    )


def _trial_course_completed_text(lang: str) -> str:
    texts = {
        "uz": (
            "🎉 <b>Bepul dars tugadi</b>\n\n"
            "<blockquote>Siz kurs rejimini sinab ko'rdingiz: dars, quiz, xato tahlili va mustahkamlash.</blockquote>\n\n"
            "Keyingi darslarni ochish uchun obuna oling.\n"
            "Obuna olmasangiz ham daily limit bilan savol-javobda davom etishingiz mumkin."
        ),
        "ru": (
            "🎉 <b>Бесплатный урок завершён</b>\n\n"
            "<blockquote>Вы попробовали режим курса: урок, quiz, разбор ошибок и закрепление.</blockquote>\n\n"
            "Чтобы открыть следующие уроки, оформите подписку.\n"
            "Даже без подписки можно продолжить в вопрос-ответ с дневным лимитом."
        ),
        "tj": (
            "🎉 <b>Дарси ройгон анҷом шуд</b>\n\n"
            "<blockquote>Шумо реҷаи курсро санҷидед: дарс, quiz, таҳлили хатоҳо ва мустаҳкамкунӣ.</blockquote>\n\n"
            "Барои кушодани дарсҳои навбатӣ обуна гиред.\n"
            "Бе обуна ҳам метавонед дар савол-ҷавоб бо лимити рӯзона давом диҳед."
        ),
    }
    return texts.get(lang, texts["ru"])


async def _send_trial_completed_offer(
    *,
    respond,
    lang: str,
    user=None,
    telegram_id: int | None = None,
    lesson_id: int | None = None,
) -> None:
    await ConversionFunnelService().record(
        event_name="paywall_seen",
        user=user,
        telegram_id=telegram_id,
        source="course_trial_completed",
        lesson_id=lesson_id,
    )
    await respond(
        _trial_course_completed_text(lang),
        reply_markup=subscription_miniapp_keyboard(
            lang,
            source="course_trial_completed",
            mode="subscription",
            include_free_mode=True,
        ),
        parse_mode="HTML",
    )


async def _ensure_trial_lesson_access(*, session, user, lesson, respond) -> bool:
    if not user or not lesson:
        return False

    trial_service = CourseTrialService(session)
    if trial_service.is_paid_user(user):
        return True
    if await trial_service.ensure_trial_lesson(user, lesson.id):
        return True

    lang = user.language if user and user.language else "ru"
    await session.commit()
    await _send_trial_locked_offer(respond=respond, lang=lang)
    return False


async def _guard_current_lesson_trial_access(*, session, user, lesson, respond) -> bool:
    if not await _ensure_trial_lesson_access(
        session=session,
        user=user,
        lesson=lesson,
        respond=respond,
    ):
        await session.commit()
        return False
    return True


async def _maybe_show_force_sub_checkpoint(*, callback: CallbackQuery, session, user, step: str) -> bool:
    trial_service = CourseTrialService(session)
    if not trial_service.should_start_force_sub_at_step(step):
        return False
    if not trial_service.is_free_user(user):
        return False

    await trial_service.mark_force_sub_required(user)
    await session.commit()

    required_service = RequiredChannelService(session)
    missing = await required_service.missing_channels(callback.bot, callback.from_user.id)
    if not missing:
        return False

    lang = user.language if user and user.language else "ru"
    await callback.answer(t("force_sub_required_alert", lang), show_alert=True)
    await callback.message.answer(
        required_service.build_required_text(missing, lang),
        reply_markup=required_service.build_required_keyboard(missing, lang),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    return True


async def _show_required_channel_for_pending_action(
    *,
    callback: CallbackQuery,
    state: FSMContext,
    session,
    user,
    lang: str,
    action: str,
    payload: dict | None = None,
) -> bool:
    required_service = RequiredChannelService(session)
    missing = await required_service.missing_channels(callback.bot, callback.from_user.id)
    if not missing:
        return False

    if user and getattr(user, "force_sub_required_at", None) is None:
        user.force_sub_required_at = datetime.now(timezone.utc)
        await session.flush()

    await state.update_data(
        **{
            PENDING_FORCE_SUB_ACTION: action,
            PENDING_FORCE_SUB_PAYLOAD: payload or {},
        }
    )
    await session.commit()
    await callback.answer(t("force_sub_required_alert", lang), show_alert=True)

    respond = _MessageEditResponder(callback.message)
    await respond(
        required_service.build_required_text(missing, lang),
        reply_markup=required_service.build_required_keyboard(missing, lang),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    return True


async def _ensure_active_course_access(
    *,
    session,
    user,
    respond,
    expired_from_course: bool | None = None,
) -> bool:
    was_in_course = getattr(user, "learning_mode", "qa") == "course"
    access_service = AccessService(session)
    await access_service.ensure_active_course_access(user)

    trial_service = CourseTrialService(session)
    if trial_service.is_paid_user(user) or trial_service.is_free_user(user):
        return True

    await session.commit()
    lang = user.language if user and user.language else "ru"
    await _send_course_access_offer(
        respond=respond,
        lang=lang,
        expired_from_course=was_in_course if expired_from_course is None else expired_from_course,
    )
    return False


def _course_level_candidates(level: str | None) -> tuple[str, ...]:
    normalized = (level or "").strip().lower()
    fallback_map = {
        "beginner": ("hsk1",),
        "hsk1": ("hsk1",),
        "hsk2": ("hsk2", "hsk1"),
        "hsk3": ("hsk3", "hsk2", "hsk1"),
        "hsk4": ("hsk4", "hsk3", "hsk2", "hsk1"),
    }
    return fallback_map.get(normalized, ("hsk1",))


async def _resolve_lessons_for_user_level(engine: CourseEngineService, level: str | None):
    candidates = _course_level_candidates(level)
    for candidate in candidates:
        lessons = await engine.lesson_repo.list_by_level(candidate)
        if lessons:
            return lessons, candidate
    return [], candidates[0]


def filter_unlocked_lessons(lessons: list, progress) -> list:
    unlocked_order = max(1, (getattr(progress, "completed_lessons_count", 0) or 0) + 1)
    return [lesson for lesson in lessons if lesson.lesson_order <= unlocked_order]


def _hsk4_part_label(part: str | None) -> str:
    return "下" if part == "lower" else "上"


def _lesson_selection_markup(lessons: list, resolved_level: str, lang: str):
    if resolved_level == "hsk4":
        return hsk4_part_selection_keyboard()
    return lesson_selection_keyboard(lessons, page=0, lang=lang)


def _course_level_label(level: str | None) -> str:
    normalized = (level or "").strip().lower()
    if normalized.startswith("hsk") and len(normalized) > 3:
        return f"HSK {normalized[3:]}"
    if normalized == "beginner":
        return "HSK 1"
    return (level or "HSK").upper()


def _course_days_since(created_at) -> int:
    if not created_at:
        return 1
    created = created_at
    if not created.tzinfo:
        created = created.replace(tzinfo=timezone.utc)
    return max(1, (datetime.now(timezone.utc) - created).days)


async def _format_level_completion_text(
    *,
    session,
    progress,
    lesson,
    lang: str,
) -> str:
    completed_order = max(
        getattr(progress, "completed_lessons_count", 0) or 0,
        getattr(lesson, "lesson_order", 0) or 0,
    )
    summary = await CourseProgressSummaryService(session).summarize_completed_range(
        progress,
        end_at=completed_order,
    )
    return t(
        "course_level_completed_text",
        lang,
        level=_course_level_label(getattr(lesson, "level", None)),
        lessons=summary["lessons"] or completed_order,
        vocab=summary["vocab"],
        dialogues=summary["dialogues"],
        days=_course_days_since(getattr(progress, "created_at", None)),
    )


async def send_course_completion_prompt(
    *,
    respond,
    engine: CourseEngineService,
    lesson,
    lang: str,
    progress=None,
) -> None:
    next_lesson = await engine.lesson_repo.get_next_lesson(
        level=lesson.level,
        lesson_order=lesson.lesson_order,
    )
    if next_lesson:
        await respond(
            t("course_next_lesson_unlocked", lang),
            reply_markup=course_next_lesson_keyboard(lang),
        )
    else:
        if progress is not None:
            await respond(
                await _format_level_completion_text(
                    session=engine.session,
                    progress=progress,
                    lesson=lesson,
                    lang=lang,
                ),
                parse_mode="HTML",
            )
        else:
            await respond(t("course_completed_title", lang))

        next_level = get_next_course_level(lesson.level)
        next_level_first_lesson = (
            await engine.lesson_repo.get_first_by_level(next_level)
            if next_level
            else None
        )
        if next_level and next_level_first_lesson:
            await respond(
                t(
                    "course_next_level_offer",
                    lang,
                    next_level=_course_level_label(next_level),
                ),
                reply_markup=course_level_upgrade_keyboard(lang),
                parse_mode="HTML",
            )
        else:
            await respond(
                t(
                    "course_no_next_level_available" if next_level else "course_all_levels_completed",
                    lang,
                ),
                parse_mode="HTML",
            )


def _format_homework_text(lang: str, homework_raw) -> str:
    title = t("course_homework_title", lang)

    if not homework_raw:
        return title

    try:
        data = json.loads(homework_raw) if isinstance(homework_raw, str) else homework_raw
    except Exception:
        return f"{title}\n\n{homework_raw}"

    if not isinstance(data, list):
        return f"{title}\n\n{data}"

    lines = [title, ""]
    for i, item in enumerate(data, 1):
        if not isinstance(item, dict):
            lines.append(f"{i}. {item}")
            continue

        instruction = (
            item.get(f"instruction_{lang}")
            or item.get("instruction_uz")
            or item.get("instruction", "")
        )
        direct_text = item.get(lang) or item.get("uz") or ""
        words = item.get("words", [])
        example = item.get("example", "")
        topic = (
            item.get(f"topic_{lang}")
            or item.get("topic_uz")
            or item.get("topic", "")
        )

        if direct_text and not instruction:
            lines.append(f"{i}. {direct_text}")
            lines.append("")
            continue

        lines.append(f"{i}. {instruction}")
        if words:
            lines.append(f"   📌 {' · '.join(words)}")
        if example:
            lines.append(f"   💬 {example}")
        if topic:
            lines.append(f"   🎯 {topic}")
        lines.append("")

    return "\n".join(lines).rstrip()





def get_course_keyboard_for_step(lang: str, step: str):
    if step == "satisfaction_check":
        return course_satisfaction_keyboard(lang)
    if step == "homework":
        return _ctx_homework_keyboard(lang)
    if step == "completed":
        return course_next_lesson_keyboard(lang)
    return course_understood_keyboard(lang, step)

@router.callback_query(F.data.startswith("course:lessons_page:"))
async def course_lessons_page_handler(callback: CallbackQuery, session):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    lang = user.language if user.language else "ru"

    parts = callback.data.split(":")
    try:
        page = int(parts[2])
    except Exception:
        page = 0
    hsk4_part = normalize_hsk4_part(parts[3] if len(parts) > 3 else None)

    lessons, resolved_level = await _resolve_lessons_for_user_level(engine, user.level)
    if resolved_level == "hsk4":
        if not hsk4_part:
            await callback.answer()
            await callback.message.edit_reply_markup(reply_markup=hsk4_part_selection_keyboard())
            return
        part_lessons = filter_hsk4_lessons_by_part(lessons, hsk4_part)
        if not part_lessons:
            await callback.answer(t("course_no_lessons_available", lang), show_alert=True)
            return

    await callback.answer()
    await callback.message.edit_reply_markup(
        reply_markup=lesson_selection_keyboard(
            lessons,
            page=page,
            lang=lang,
            hsk4_part=hsk4_part,
        )
    )


@router.callback_query(F.data.startswith("course:hsk4_part:"))
async def course_hsk4_part_handler(callback: CallbackQuery, session):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    lang = user.language if user.language else "ru"

    hsk4_part = normalize_hsk4_part(callback.data.split(":")[-1])
    if not hsk4_part:
        await callback.answer()
        return

    lessons, resolved_level = await _resolve_lessons_for_user_level(engine, user.level)
    if resolved_level != "hsk4":
        await callback.answer()
        await callback.message.edit_reply_markup(
            reply_markup=lesson_selection_keyboard(lessons, page=0, lang=lang)
        )
        return

    part_lessons = filter_hsk4_lessons_by_part(lessons, hsk4_part)
    if not part_lessons:
        await callback.answer(t("course_no_lessons_available", lang), show_alert=True)
        return

    text = f"HSK4 {_hsk4_part_label(hsk4_part)}. {t('course_choose_lesson', lang)}"

    await callback.answer()
    await callback.message.edit_text(
        text,
        reply_markup=lesson_selection_keyboard(
            lessons,
            page=0,
            lang=lang,
            hsk4_part=hsk4_part,
        ),
    )


@router.callback_query(F.data.startswith("course:pick_lesson:"))
async def course_pick_lesson_handler(callback: CallbackQuery, session):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else (
        callback.from_user.language_code if callback.from_user.language_code in ["ru", "uz", "tj"] else "ru"
    )

    try:
        lesson_id = int(callback.data.split(":")[-1])
    except Exception:
        await callback.answer()
        return

    lesson = await engine.lesson_repo.get_by_id(lesson_id)
    if not lesson:
        await callback.answer()
        await callback.message.answer(t("course_no_lesson_found", lang))
        return
    if user and lesson.level not in _course_level_candidates(user.level):
        await callback.answer(t("course_lesson_not_unlocked", lang), show_alert=True)
        return
    if user and not await _ensure_trial_lesson_access(
        session=session,
        user=user,
        lesson=lesson,
        respond=callback.message.answer,
    ):
        await callback.answer()
        return

    _, _, _, error_key = await engine.pick_lesson(callback.from_user.id, lesson_id)
    if error_key:
        if error_key == "course_lesson_not_unlocked":
            await callback.answer(t(error_key, lang), show_alert=True)
        else:
            await callback.answer()
            await callback.message.answer(t(error_key, lang))
        return
    await ConversionFunnelService().record(
        event_name="lesson_started",
        user=user,
        source="course_pick_lesson",
        lesson_id=lesson.id,
        payload={
            "lesson_order": getattr(lesson, "lesson_order", None),
            "level": getattr(lesson, "level", None),
        },
    )

    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_course_miniapp_entry(
        session=session,
        telegram_id=callback.from_user.id,
        respond=callback.message.answer,
        source="course_pick_lesson",
        level=getattr(lesson, "level", None),
        lesson=getattr(lesson, "lesson_order", None),
    )



@router.callback_query(F.data == "mode:qa")
async def mode_qa_handler(callback: CallbackQuery, state: FSMContext, session):

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    lang = callback.from_user.language_code if callback.from_user.language_code in ["ru", "uz", "tj"] else "ru"

    if not user:
        await callback.answer()
        await callback.message.answer(t("user_not_found", lang))
        return

    lang = user.language if user.language else "ru"
    user.learning_mode = "qa"
    user.voice_mode = "none"
    await state.update_data(pending_voice_transcript=None, pending_voice_message_id=None)
    await session.commit()

    await callback.answer()
    await callback.message.answer(t("trial_started_info", lang))
    await callback.message.answer(t("send_first_message", lang), reply_markup=main_menu_keyboard(lang))


@router.callback_query(F.data == "mode:free_qa")
async def mode_free_qa_handler(callback: CallbackQuery, state: FSMContext, session):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    lang = callback.from_user.language_code if callback.from_user.language_code in ["ru", "uz", "tj"] else "ru"
    if not user:
        await callback.answer()
        await callback.message.answer(t("user_not_found", lang))
        return

    lang = user.language if user.language else "ru"
    if await _show_required_channel_for_pending_action(
        callback=callback,
        state=state,
        session=session,
        user=user,
        lang=lang,
        action=FORCE_SUB_ACTION_OPEN_FREE_QA,
        payload={"source": "mode_free_qa"},
    ):
        return

    await callback.answer()
    await show_free_qa_level_choice(
        respond=_MessageEditResponder(callback.message),
        state=state,
        lang=lang,
    )


@router.callback_query(F.data == "mode:course")
async def course_mode_open_handler(callback: CallbackQuery, state: FSMContext, session):
    if await _block_if_course_disabled(callback, session):
        return

    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "ru"
    if await _show_required_channel_for_pending_action(
        callback=callback,
        state=state,
        session=session,
        user=user,
        lang=lang,
        action=FORCE_SUB_ACTION_OPEN_COURSE,
        payload={"source": "mode_course"},
    ):
        return

    await callback.answer()
    await send_course_miniapp_entry(
        session=session,
        telegram_id=callback.from_user.id,
        respond=_MessageEditResponder(callback.message),
        state=state,
        source="mode_course",
    )


async def activate_free_qa_mode(
    *,
    session,
    telegram_id: int,
    respond,
    state: FSMContext | None = None,
) -> bool:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        await respond(t("user_not_found", "ru"))
        return False

    lang = user.language if user.language else "ru"
    user.learning_mode = "qa"
    user.voice_mode = "none"
    if state:
        await state.update_data(pending_voice_transcript=None, pending_voice_message_id=None)
    await session.commit()
    await respond(
        t("free_mode_info", lang),
        reply_markup=main_menu_keyboard(lang),
        parse_mode="HTML",
    )
    return True




async def run_course_entry_flow(
    *,
    session,
    telegram_id: int,
    respond,
    show_menu: bool = True,
):
    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(telegram_id)
    if not user:
        await respond(t("access_start_first", "ru"))
        return

    lang = user.language if user.language else "ru"

    if not await _ensure_active_course_access(
        session=session,
        user=user,
        respond=respond,
    ):
        return

    user.learning_mode = "course"
    user.voice_mode = "none"
    await session.commit()
    await ConversionFunnelService().record(
        event_name="course_started",
        user=user,
        source="course_entry",
    )

    progress = await engine.progress_repo.get_by_user_id(user.id)
    if not progress:
        progress = await engine.progress_repo.create(
            user_id=user.id,
            level=user.level,
            current_lesson_id=None,
            current_step="intro",
            waiting_for="none",
        )

    current_lesson = None
    if progress.current_lesson_id:
        current_lesson = await engine.lesson_repo.get_by_id(progress.current_lesson_id)
        if current_lesson and not await _ensure_trial_lesson_access(
            session=session,
            user=user,
            lesson=current_lesson,
            respond=respond,
        ):
            return
    else:
        lessons, _ = await _resolve_lessons_for_user_level(engine, user.level)
        if not lessons:
            await respond(t("course_no_lessons_available", lang))
            return
        _, progress, current_lesson, error_key = await engine.pick_lesson(
            telegram_id,
            lessons[0].id,
        )
        if error_key:
            await respond(t(error_key, lang))
            return
        if not await _ensure_trial_lesson_access(
            session=session,
            user=user,
            lesson=current_lesson,
            respond=respond,
        ):
            return

    open_text = {
        "uz": (
            "📚 <b>HSK AI kursi Mini Appga ko‘chdi</b>\n\n"
            "<blockquote>Darslar, so‘zlar, grammatika, quiz va AI Voice bitta joyda.</blockquote>"
        ),
        "ru": (
            "📚 <b>Курс HSK AI переехал в Mini App</b>\n\n"
            "<blockquote>Уроки, слова, грамматика, квиз и AI Voice теперь в одном месте.</blockquote>"
        ),
        "tj": (
            "📚 <b>Курси HSK AI ба Mini App гузашт</b>\n\n"
            "<blockquote>Дарсҳо, калимаҳо, грамматика, quiz ва AI Voice дар як ҷо.</blockquote>"
        ),
    }
    try:
        await respond(
            open_text.get(lang, open_text["ru"]),
            reply_markup=course_study_miniapp_keyboard(
                lang,
                level=getattr(current_lesson, "level", None) or getattr(progress, "level", None) or user.level,
                lesson=getattr(current_lesson, "lesson_order", None),
            ),
            parse_mode="HTML",
        )
        return
    except Exception:
        logger.exception("Failed to open Course Mini App; using legacy course fallback")

    if not progress.current_lesson_id:
        lessons, resolved_level = await _resolve_lessons_for_user_level(engine, user.level)

        if not lessons:
            await respond(t("course_no_lessons_available", lang))
            return

        level_label = resolved_level.upper() if resolved_level else "HSK"
        await respond(
            f"{level_label}. {t('course_choose_lesson', lang)}",
            reply_markup=_lesson_selection_markup(lessons, resolved_level, lang),
        )
        return

    if getattr(progress, "waiting_for", None) == "next_study_time":
        # Avtomatik o'tkazib yuboramiz — foydalanuvchi xohlasa menyu orqali eslatma qo'yadi
        await engine.set_next_study_at(telegram_id, None)
        _, p2, l2, e2 = await engine.get_current_lesson(telegram_id)
        if not e2:
            if getattr(p2, "waiting_for", None) == "review_choice":
                await respond(
                    t("course_review_choice", lang),
                    reply_markup=review_choice_keyboard(lang),
                )
            else:
                await send_course_completion_prompt(
                    respond=respond,
                    engine=engine,
                    lesson=l2,
                    lang=lang,
                    progress=p2,
                )
        return

    trial_service = CourseTrialService(session)
    if (
        not trial_service.is_paid_user(user)
        and getattr(progress, "current_step", None) == "completed"
        and getattr(progress, "homework_status", None) == "completed"
    ):
        lesson = await engine.lesson_repo.get_by_id(progress.current_lesson_id)
        await trial_service.mark_trial_completed(user, getattr(lesson, "id", None))
        await session.commit()
        await _send_trial_completed_offer(
            respond=respond,
            lang=lang,
            user=user,
            telegram_id=telegram_id,
            lesson_id=getattr(lesson, "id", None),
        )
        return

    if (
        getattr(progress, "current_step", None) == "completed"
        and getattr(progress, "homework_status", None) == "completed"
        and getattr(progress, "waiting_for", None) == "review_choice"
    ):
        await respond(
            t("course_review_choice", lang),
            reply_markup=review_choice_keyboard(lang),
        )
        return

    if getattr(progress, "current_step", None) == "completed" and getattr(progress, "homework_status", None) == "completed":
        lesson = await engine.lesson_repo.get_by_id(progress.current_lesson_id)
        if lesson:
            await send_course_completion_prompt(
                respond=respond,
                engine=engine,
                lesson=lesson,
                lang=lang,
                progress=progress,
            )
        else:
            await respond(t("course_completed_title", lang))
        return

    user, progress, lesson, error_key = await engine.continue_course(telegram_id)
    if error_key:
        await respond(t(error_key, lang))
        return

    step = progress.current_step

    # V1 → V2/block migratsiya: eski "vocab"/"dialogue" stepida qolgan foydalanuvchilarni
    # yangi oqimdagi mos stepga ko'chiramiz.
    from app.services.course_engine_service import is_v2_lesson
    if is_v2_lesson(lesson):
        remapped_step = _v2_remap(step, lesson)
        if remapped_step != step:
            step = remapped_step
            await engine.progress_repo.set_current_lesson_and_step(
                progress=progress, lesson_id=lesson.id, step=step, waiting_for="none"
            )
            await session.commit()

    if (step == "exercise" or is_block_quiz_step(step)) and getattr(progress, "waiting_for", "none") not in {"exercise_answer", "quiz_result"}:
        await engine.progress_repo.set_waiting_for(
            progress,
            "quiz_result" if is_course_miniapp_supported(lesson) else "exercise_answer",
        )
        await session.commit()

    if step == "homework":
        if is_course_miniapp_supported(lesson):
            await engine.progress_repo.set_waiting_for(progress, "homework_result")
            await session.commit()
            text = format_miniapp_homework_intro(lang, lesson)
            keyboard = course_homework_miniapp_keyboard(lang, lesson)
        else:
            text = _format_homework_text(lang, lesson.homework_json)
            keyboard = get_course_keyboard_for_step(lang, step)
        await respond(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await _send_step(respond, user, lesson, step, lang, session)

@router.message(F.text == "/course")
async def course_command_handler(message: Message, state: FSMContext, session):
    await state.update_data(pending_voice_transcript=None, pending_voice_message_id=None)

    if not COURSE_MODE_ENABLED:
        lang = "ru"
        try:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(message.from_user.id)
            if user and user.language:
                lang = user.language
        except:
            pass

        msg_map = {
            "uz": "🚧 Kurs rejimi hozircha ishlab chiqilmoqda. Tez orada mavjud bo‘ladi.",
            "ru": "🚧 Режим курса сейчас в разработке. Скоро будет доступен.",
            "tj": "🚧 Реҷаи курс ҳоло дар таҳия аст. Ба зудӣ дастрас мешавад.",
        }

        await message.answer(msg_map.get(lang, msg_map["ru"]))
        return

    await send_course_miniapp_entry(
        session=session,
        telegram_id=message.from_user.id,
        respond=message.answer,
        state=state,
        source="course_command",
    )


@router.callback_query(F.data == "course:back_to_qa")
async def course_back_to_qa_handler(callback: CallbackQuery, state: FSMContext, session):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        await callback.message.answer(t("access_start_first", "ru"))
        return

    user.learning_mode = "qa"
    user.voice_mode = "none"
    await state.update_data(pending_voice_transcript=None, pending_voice_message_id=None)
    await session.commit()

    lang = user.language if user.language else "ru"

    await callback.answer()
    await callback.message.answer(t("send_first_message", lang), reply_markup=main_menu_keyboard(lang))




@router.callback_query(F.data == "course:continue")
async def course_continue_handler(callback: CallbackQuery, state: FSMContext, session):
    if await _block_if_course_disabled(callback, session):
        return

    await callback.answer()
    await send_course_miniapp_entry(
        session=session,
        telegram_id=callback.from_user.id,
        respond=callback.message.answer,
        state=state,
        source="course_continue",
    )




@router.callback_query(F.data == "course:review_yes")
async def course_review_yes_handler(callback: CallbackQuery, session):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    lang = user.language if user.language else "ru"
    progress = await engine.progress_repo.get_by_user_id(user.id)
    if not progress or progress.waiting_for != "review_choice":
        await callback.answer()
        return

    user, progress, lesson, error_key = await engine.get_current_lesson(callback.from_user.id)
    if error_key:
        await callback.answer()
        await callback.message.answer(t(error_key, lang))
        return
    if not await _guard_current_lesson_trial_access(
        session=session,
        user=user,
        lesson=lesson,
        respond=callback.message.answer,
    ):
        await callback.answer()
        return

    review_text = format_step(lesson, lang, "review") or _static_course_missing_text(lang)

    if getattr(progress, "homework_status", None) == "completed":
        await engine.progress_repo.set_waiting_for(progress, "none")
        await session.commit()

        await callback.answer()
        await callback.message.answer(t("course_review", lang))
        await callback.message.answer(review_text)
        await send_course_completion_prompt(
            respond=callback.message.answer,
            engine=engine,
            lesson=lesson,
            lang=lang,
            progress=progress,
        )
        return

    await engine.progress_repo.set_waiting_for(
        progress,
        "homework_result" if is_course_miniapp_supported(lesson) else "homework_submission",
    )
    await session.commit()

    homework_text = (
        format_miniapp_homework_intro(lang, lesson)
        if is_course_miniapp_supported(lesson)
        else _format_homework_text(lang, lesson.homework_json)
    )
    homework_keyboard = (
        course_homework_miniapp_keyboard(lang, lesson)
        if is_course_miniapp_supported(lesson)
        else None
    )

    await callback.answer()
    await callback.message.answer(t("course_review_then_homework", lang))
    await callback.message.answer(review_text)
    await callback.message.answer(homework_text, reply_markup=homework_keyboard)


@router.callback_query(F.data == "course:review_no")
async def course_review_no_handler(callback: CallbackQuery, session):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    lang = user.language if user.language else "ru"

    user, progress, lesson, current_error_key = await engine.get_current_lesson(callback.from_user.id)
    if current_error_key:
        await callback.answer()
        await callback.message.answer(t(current_error_key, lang))
        return
    if not await _guard_current_lesson_trial_access(
        session=session,
        user=user,
        lesson=lesson,
        respond=callback.message.answer,
    ):
        await callback.answer()
        return

    if getattr(progress, "homework_status", None) != "completed":
        await callback.answer()
        await callback.message.answer(t("course_complete_homework_first", lang))
        return

    trial_service = CourseTrialService(session)
    if not trial_service.is_paid_user(user):
        _, _, completed_lesson, completed_error = await engine.complete_current_lesson_once(callback.from_user.id)
        if completed_error:
            await callback.answer()
            await callback.message.answer(t(completed_error, lang))
            return
        await trial_service.mark_trial_completed(user, getattr(completed_lesson, "id", None))
        await session.commit()
        await callback.answer()
        await _send_trial_completed_offer(
            respond=callback.message.answer,
            lang=lang,
            user=user,
            telegram_id=callback.from_user.id,
            lesson_id=getattr(completed_lesson, "id", None),
        )
        return

    user, progress, lesson, next_lesson, error_key = await engine.complete_lesson_and_unlock_next(callback.from_user.id)
    if error_key:
        await callback.answer()
        await callback.message.answer(t(error_key, lang))
        return

    if not next_lesson:
        await callback.answer()
        await send_course_completion_prompt(
            respond=callback.message.answer,
            engine=engine,
            lesson=lesson,
            lang=lang,
            progress=progress,
        )
        return

    await ConversionFunnelService().record(
        event_name="lesson_started",
        user=user,
        source="course_next_lesson",
        lesson_id=next_lesson.id,
        payload={
            "lesson_order": getattr(next_lesson, "lesson_order", None),
            "level": getattr(next_lesson, "level", None),
        },
    )
    text = format_intro(next_lesson, lang)

    await callback.answer()
    await callback.message.answer(t("course_skip_review_next_lesson", lang))
    await callback.message.answer(
        text,
        reply_markup=course_intro_keyboard(lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "course:progress")
async def course_progress_handler(callback: CallbackQuery, session):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        await callback.message.answer(t("access_start_first", "ru"))
        return

    lang = user.language if user.language else "ru"

    user, progress, lesson, error_key = await engine.get_current_lesson(callback.from_user.id)
    if error_key:
        await callback.answer()
        await callback.message.answer(t(error_key, lang))
        return
    if not await _guard_current_lesson_trial_access(
        session=session,
        user=user,
        lesson=lesson,
        respond=callback.message.answer,
    ):
        await callback.answer()
        return

    current_lesson_title = lesson.title if lesson else "—"
    completed_count = getattr(progress, "completed_lessons_count", 0) or 0
    summary = await CourseProgressSummaryService(session).summarize_completed_range(progress)

    days_studying = 1
    if progress.created_at:
        created = progress.created_at
        if not created.tzinfo:
            created = created.replace(tzinfo=timezone.utc)
        days_studying = max(1, (datetime.now(timezone.utc) - created).days)

    await callback.answer()
    await callback.message.answer(
        t("course_progress_full_text", lang,
          lessons=completed_count,
          vocab=summary["vocab"],
          dialogues=summary["dialogues"],
          days=days_studying,
          current=current_lesson_title),
        parse_mode="HTML",
    )



@router.callback_query(F.data == "course:review_last")
async def course_review_last_handler(callback: CallbackQuery, state: FSMContext, session):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        await callback.message.answer(t("access_start_first", "ru"))
        return

    lang = user.language if user.language else "ru"

    user, progress, lesson, error_key = await engine.get_current_lesson(callback.from_user.id)
    if error_key:
        await callback.answer()
        await callback.message.answer(t(error_key, lang))
        return
    if not await _guard_current_lesson_trial_access(
        session=session,
        user=user,
        lesson=lesson,
        respond=callback.message.answer,
    ):
        await callback.answer()
        return

    await callback.answer()
    await send_course_miniapp_entry(
        session=session,
        telegram_id=callback.from_user.id,
        respond=callback.message.answer,
        state=state,
        source="course_review_last",
        level=getattr(lesson, "level", None),
        lesson=getattr(lesson, "lesson_order", None),
    )





@router.callback_query(F.data == "course:satisfied_yes")
async def course_satisfied_yes_handler(callback: CallbackQuery, session):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        await callback.message.answer(t("access_start_first", "ru"))
        return

    lang = user.language if user.language else "ru"

    current_user, _current_progress, current_lesson, current_error = await engine.get_current_lesson(callback.from_user.id)
    if current_error:
        await callback.answer()
        await callback.message.answer(t(current_error, lang))
        return
    if not await _guard_current_lesson_trial_access(
        session=session,
        user=current_user,
        lesson=current_lesson,
        respond=callback.message.answer,
    ):
        await callback.answer()
        return

    user, progress, lesson, error_key = await engine.mark_satisfied_and_go_to_homework(callback.from_user.id)
    if error_key:
        await callback.answer()
        await callback.message.answer(t(error_key, lang))
        return

    await engine.progress_repo.set_waiting_for(
        progress,
        "homework_result" if is_course_miniapp_supported(lesson) else "homework_submission",
    )
    await session.commit()

    if is_course_miniapp_supported(lesson):
        await callback.answer()
        await callback.message.answer(
            format_miniapp_homework_intro(lang, lesson),
            reply_markup=course_homework_miniapp_keyboard(lang, lesson),
            parse_mode="HTML",
        )
        return

    await callback.answer()
    await callback.message.answer(t("course_lesson_homework_intro", lang))
    await callback.message.answer(_format_homework_text(lang, lesson.homework_json))


@router.callback_query(F.data == "course:satisfied_no")
async def course_satisfied_no_handler(callback: CallbackQuery, session):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        await callback.message.answer(t("access_start_first", "ru"))
        return

    lang = user.language if user.language else "ru"

    current_user, _current_progress, current_lesson, current_error = await engine.get_current_lesson(callback.from_user.id)
    if current_error:
        await callback.answer()
        await callback.message.answer(t(current_error, lang))
        return
    if not await _guard_current_lesson_trial_access(
        session=session,
        user=current_user,
        lesson=current_lesson,
        respond=callback.message.answer,
    ):
        await callback.answer()
        return

    user, progress, lesson, error_key = await engine.mark_not_satisfied_and_stay(callback.from_user.id)
    if error_key:
        await callback.answer()
        await callback.message.answer(t(error_key, lang))
        return

    await callback.answer()
    await callback.message.answer(
        t("course_lesson_what_unclear", lang)
    )


@router.callback_query(F.data == "course:show_homework")
async def course_show_homework_handler(callback: CallbackQuery, session):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        await callback.message.answer(t("access_start_first", "ru"))
        return

    lang = user.language if user.language else "ru"

    user, progress, lesson, error_key = await engine.get_current_lesson(callback.from_user.id)
    if error_key:
        await callback.answer()
        await callback.message.answer(t(error_key, lang))
        return
    if not await _guard_current_lesson_trial_access(
        session=session,
        user=user,
        lesson=lesson,
        respond=callback.message.answer,
    ):
        await callback.answer()
        return

    if progress.current_step == "homework" and progress.homework_status != "completed":
        await engine.progress_repo.set_waiting_for(
            progress,
            "homework_result" if is_course_miniapp_supported(lesson) else "homework_submission",
        )
        await session.commit()

    await callback.answer()
    if is_course_miniapp_supported(lesson):
        await callback.message.answer(
            format_miniapp_homework_intro(lang, lesson),
            reply_markup=course_homework_miniapp_keyboard(lang, lesson),
            parse_mode="HTML",
        )
        return

    await callback.message.answer(_format_homework_text(lang, lesson.homework_json))


@router.callback_query(F.data == "course:homework_reread")
async def course_homework_reread_handler(callback: CallbackQuery, session):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        await callback.message.answer(t("access_start_first", "ru"))
        return

    lang = user.language if user.language else "ru"
    user, progress, lesson, error_key = await engine.get_current_lesson(callback.from_user.id)
    if error_key:
        await callback.answer()
        await callback.message.answer(t(error_key, lang))
        return
    if not await _guard_current_lesson_trial_access(
        session=session,
        user=user,
        lesson=lesson,
        respond=callback.message.answer,
    ):
        await callback.answer()
        return

    await engine.progress_repo.set_current_lesson_and_step(
        progress=progress,
        lesson_id=lesson.id,
        step="intro",
        waiting_for="none",
    )
    await session.commit()

    await callback.answer()
    await callback.message.answer(t("course_reread_start_msg", lang))
    await callback.message.answer(
        format_intro(lesson, lang),
        reply_markup=course_intro_keyboard(lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "course:start_next_lesson")
async def course_start_next_lesson_handler(callback: CallbackQuery, session):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        await callback.message.answer(t("access_start_first", "ru"))
        return

    lang = user.language if user.language else "ru"

    user, progress, lesson, current_error_key = await engine.get_current_lesson(callback.from_user.id)
    if current_error_key:
        await callback.answer()
        await callback.message.answer(t(current_error_key, lang))
        return
    if not await _guard_current_lesson_trial_access(
        session=session,
        user=user,
        lesson=lesson,
        respond=callback.message.answer,
    ):
        await callback.answer()
        return

    if progress.homework_status != "completed":
        can_skip_after_low_score = (
            getattr(progress, "current_step", None) == "homework"
            and getattr(progress, "waiting_for", None) == "homework_decision"
        )
        if can_skip_after_low_score:
            await engine.progress_repo.set_homework_status(progress, "completed")
        else:
            await callback.answer()
            await callback.message.answer(t("course_complete_homework_first", lang))
            return

    trial_service = CourseTrialService(session)
    if not trial_service.is_paid_user(user):
        completed_user, completed_progress, completed_lesson, completed_error = await engine.complete_current_lesson_once(
            callback.from_user.id
        )
        if completed_error:
            await callback.answer()
            await callback.message.answer(t(completed_error, lang))
            return
        await trial_service.mark_trial_completed(user, getattr(completed_lesson, "id", None))
        await session.commit()
        await callback.answer()
        await _send_trial_completed_offer(
            respond=callback.message.answer,
            lang=lang,
            user=user,
            telegram_id=callback.from_user.id,
            lesson_id=getattr(completed_lesson, "id", None),
        )
        return

    user, progress, lesson, next_lesson, error_key = await engine.complete_lesson_and_unlock_next(callback.from_user.id)
    if error_key:
        await callback.answer()
        await callback.message.answer(t(error_key, lang))
        return

    if not next_lesson:
        await callback.answer()
        await send_course_completion_prompt(
            respond=callback.message.answer,
            engine=engine,
            lesson=lesson,
            lang=lang,
            progress=progress,
        )
        return

    await ConversionFunnelService().record(
        event_name="lesson_started",
        user=user,
        source="course_next_lesson",
        lesson_id=next_lesson.id,
        payload={
            "lesson_order": getattr(next_lesson, "lesson_order", None),
            "level": getattr(next_lesson, "level", None),
        },
    )
    await callback.answer()
    await send_course_miniapp_entry(
        session=session,
        telegram_id=callback.from_user.id,
        respond=callback.message.answer,
        source="course_next_lesson",
        level=getattr(next_lesson, "level", None),
        lesson=getattr(next_lesson, "lesson_order", None),
    )


@router.callback_query(F.data == "course:level_upgrade_yes")
async def course_level_upgrade_yes_handler(callback: CallbackQuery, session):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        await callback.message.answer(t("access_start_first", "ru"))
        return

    lang = user.language if user.language else "ru"

    if not CourseTrialService(session).is_paid_user(user):
        await callback.answer()
        await _send_trial_locked_offer(respond=callback.message.answer, lang=lang)
        return

    user, progress, _completed_lesson, next_lesson, error_key = await engine.advance_to_next_level(callback.from_user.id)
    if error_key:
        await callback.answer()
        await callback.message.answer(t(error_key, lang))
        return

    await ConversionFunnelService().record(
        event_name="lesson_started",
        user=user,
        source="course_level_upgrade",
        lesson_id=next_lesson.id,
        payload={
            "lesson_order": getattr(next_lesson, "lesson_order", None),
            "level": getattr(next_lesson, "level", None),
        },
    )
    await callback.answer()
    await callback.message.answer(
        t("course_level_upgraded", lang, level=_course_level_label(next_lesson.level)),
        parse_mode="HTML",
    )
    await callback.message.answer(
        format_intro(next_lesson, lang),
        reply_markup=course_intro_keyboard(lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "course:level_upgrade_no")
async def course_level_upgrade_no_handler(callback: CallbackQuery, session):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        await callback.message.answer(t("access_start_first", "ru"))
        return

    lang = user.language if user.language else "ru"

    if not CourseTrialService(session).is_paid_user(user):
        await callback.answer()
        await _send_trial_locked_offer(respond=callback.message.answer, lang=lang)
        return

    _, _progress, lesson, error_key = await engine.complete_current_lesson_once(callback.from_user.id)
    if error_key:
        await callback.answer()
        await callback.message.answer(t(error_key, lang))
        return

    lessons = await engine.lesson_repo.list_by_level(lesson.level)
    await callback.answer()
    await callback.message.answer(
        t("course_level_upgrade_declined", lang, level=_course_level_label(lesson.level)),
        reply_markup=_lesson_selection_markup(lessons, lesson.level, lang),
        parse_mode="HTML",
    )


def _keyboard_for_step(lang: str, step: str, lesson=None):
    """Har qanday step uchun to'g'ri klaviaturani qaytaradi (V1 + V2)."""
    from app.services.course_engine_service import is_v2_lesson as _is_v2
    v2 = lesson is not None and _is_v2(lesson)

    # V2 intro — "Davom etamiz" (vocab_1 ga o'tadi)
    if step == "intro" and v2:
        return course_next_step_keyboard(lang)
    if is_block_vocab_step(step):
        return course_vocab_stroke_order_keyboard(
            lang,
            lesson,
            block_no=get_block_no_from_step(step),
        )
    if is_block_grammar_step(step):
        return course_next_step_keyboard(lang)
    if is_block_quiz_step(step):
        block_no = get_block_no_from_step(step)
        if lesson is not None and is_course_miniapp_supported(lesson):
            return course_quiz_miniapp_keyboard(lang, lesson, block_no=block_no)
        return course_next_step_keyboard(lang)
    # V2 vocab steps — audio + next
    if step in ("vocab_1", "vocab_2"):
        return course_vocab_stroke_order_keyboard(
            lang,
            lesson,
            vocab_page=1 if step == "vocab_1" else 2,
        )
    # V2 dialogue_N steps — audio + next
    if step.startswith("dialogue_"):
        try:
            n = int(step.split("_", 1)[1])
        except (ValueError, IndexError):
            n = 1
        return course_dialogue_n_keyboard(lang, n)
    # grammar — V2 da "Davom etamiz", V1 da "Exercisega o'tamiz"
    if step == "grammar" and v2:
        return course_next_step_keyboard(lang)
    # V1 steps
    if step == "intro":
        return course_intro_keyboard(lang)
    if step == "vocab":
        return course_vocab_stroke_order_keyboard(
            lang,
            lesson,
            next_callback="course:go_dialogue",
        )
    if step == "dialogue":
        return course_dialogue_keyboard(lang)
    if step == "grammar":
        return course_grammar_keyboard(lang)
    # exercise, satisfaction_check, homework, completed — handled by get_course_keyboard_for_step
    return get_course_keyboard_for_step(lang, step)


def _course_tip_key_for_step(step: str) -> str | None:
    step = (step or "").strip()
    if step in {"vocab", "vocab_1", "vocab_2"} or is_block_vocab_step(step):
        return TIP_KEY_COURSE_VOCAB
    if step == "dialogue" or step.startswith("dialogue_"):
        return TIP_KEY_COURSE_DIALOGUE
    if step == "grammar" or is_block_grammar_step(step):
        return TIP_KEY_COURSE_GRAMMAR
    return None


def _bot_from_respond(respond):
    owner = getattr(respond, "__self__", None)
    return getattr(owner, "bot", None)


async def _queue_course_onboarding_tip(session, user, lesson, step: str, lang: str, bot=None) -> None:
    tip_key = _course_tip_key_for_step(step)
    if not tip_key:
        return
    tip_service = OnboardingTipService(session)
    queued = await tip_service.queue_course_tip(
        user=user,
        lesson=lesson,
        step=step,
        tip_key=tip_key,
        lang=lang,
    )
    if queued:
        await session.commit()
        if bot:
            await tip_service.send_due_tips(bot, limit=5)


def _static_course_missing_text(lang: str) -> str:
    messages = {
        "uz": "Bu bo'lim uchun tayyor kurs materiali topilmadi. Dars seed faylini tekshirish kerak.",
        "ru": "Для этого раздела не найден готовый материал курса. Нужно проверить seed-файл урока.",
        "tj": "Барои ин қисм маводи тайёри курс ёфт нашуд. Seed-файли дарсро санҷидан лозим.",
    }
    return messages.get(lang, messages["ru"])


def _v2_remap(step: str, lesson) -> str:
    """V2 dars uchun V1 step nomini V2 ekvivalentiga o'zgartiradi."""
    from app.services.course_engine_service import is_v2_lesson as _is_v2
    if not _is_v2(lesson):
        return step
    if is_block_lesson(lesson):
        if step in {"vocab", "vocab_1", "vocab_2"}:
            order = get_step_order(lesson)
            return order[1] if len(order) > 1 else "intro"
        if step == "dialogue":
            return "dialogue_1"
        return step
    mapping = {"vocab": "vocab_1", "dialogue": "dialogue_1"}
    return mapping.get(step, step)


async def _send_step(respond, user, lesson, step: str, lang: str, session):
    """Step kontentini format qilib yuboradi (V1 va V2 uchun)."""
    if is_block_quiz_step(step) and is_course_miniapp_supported(lesson):
        block_no = get_block_no_from_step(step)
        await respond(
            format_miniapp_quiz_intro(lang, lesson, block_no=block_no),
            reply_markup=course_quiz_miniapp_keyboard(lang, lesson, block_no=block_no),
            parse_mode="HTML",
        )
        return

    if step == "exercise" and is_course_miniapp_supported(lesson):
        await respond(
            format_miniapp_quiz_intro(lang, lesson),
            reply_markup=course_quiz_miniapp_keyboard(lang, lesson),
            parse_mode="HTML",
        )
        return

    text = format_step(lesson, lang, step)
    if text is not None:
        keyboard = _keyboard_for_step(lang, step, lesson)
        await respond(text, reply_markup=keyboard, parse_mode="HTML")
        await _queue_course_onboarding_tip(
            session,
            user,
            lesson,
            step,
            lang,
            bot=_bot_from_respond(respond),
        )
    else:
        keyboard = _keyboard_for_step(lang, step, lesson)
        await respond(_static_course_missing_text(lang), reply_markup=keyboard, parse_mode="HTML")


async def _go_to_step(callback, session, step: str):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    lang = user.language if user.language else "ru"
    user, progress, lesson, error_key = await engine.get_current_lesson(callback.from_user.id)
    if error_key:
        await callback.answer()
        await callback.message.answer(t(error_key, lang))
        return
    if not await _guard_current_lesson_trial_access(
        session=session,
        user=user,
        lesson=lesson,
        respond=callback.message.answer,
    ):
        await callback.answer()
        return

    # V2 dars uchun V1 step nomlarini V2 ga remap qilamiz
    step = _v2_remap(step, lesson)

    if (step == "exercise" or is_block_quiz_step(step)) and is_course_miniapp_supported(lesson):
        waiting_for_val = "quiz_result"
    else:
        waiting_for_val = "exercise_answer" if step == "exercise" else "none"
    await engine.progress_repo.set_current_lesson_and_step(
        progress=progress,
        lesson_id=lesson.id,
        step=step,
        waiting_for=waiting_for_val,
    )
    await session.commit()

    await callback.answer()
    await _send_step(callback.message.answer, user, lesson, step, lang, session)


@router.callback_query(F.data == "course:go_vocab")
async def course_go_vocab(callback: CallbackQuery, session):
    await _go_to_step(callback, session, "vocab")

@router.callback_query(F.data == "course:go_dialogue")
async def course_go_dialogue(callback: CallbackQuery, session):
    await _go_to_step(callback, session, "dialogue")

@router.callback_query(F.data == "course:go_grammar")
async def course_go_grammar(callback: CallbackQuery, session):
    await _go_to_step(callback, session, "grammar")

@router.callback_query(F.data == "course:go_exercise")
async def course_go_exercise(callback: CallbackQuery, session):
    await _go_to_step(callback, session, "exercise")


@router.callback_query(F.data == "course:go_next_step")
async def course_go_next_step(callback: CallbackQuery, session):
    """V2 darslar uchun universal 'Davom etamiz' tugmasi."""
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    lang = user.language if user.language else "ru"

    current_user, _current_progress, current_lesson, current_error = await engine.get_current_lesson(callback.from_user.id)
    if current_error:
        await callback.answer()
        await callback.message.answer(t(current_error, lang))
        return
    if not await _guard_current_lesson_trial_access(
        session=session,
        user=current_user,
        lesson=current_lesson,
        respond=callback.message.answer,
    ):
        await callback.answer()
        return

    user, progress, lesson, error_key = await engine.go_to_next_step(callback.from_user.id)
    if error_key:
        await callback.answer()
        await callback.message.answer(t(error_key, lang))
        return

    step = progress.current_step

    # Exercise/block quiz stepiga o'tganda waiting_for ni yangilaymiz
    if step == "exercise" or is_block_quiz_step(step):
        await engine.progress_repo.set_waiting_for(
            progress,
            "quiz_result" if is_course_miniapp_supported(lesson) else "exercise_answer",
        )
        await session.commit()

    if await _maybe_show_force_sub_checkpoint(
        callback=callback,
        session=session,
        user=user,
        step=step,
    ):
        return

    await callback.answer()
    await _send_step(callback.message.answer, user, lesson, step, lang, session)

@router.callback_query(F.data == "course:repeat_step")
async def course_repeat_step(callback: CallbackQuery, session):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    lang = user.language if user.language else "ru"
    user, progress, lesson, error_key = await engine.get_current_lesson(callback.from_user.id)
    if error_key:
        await callback.answer()
        await callback.message.answer(t(error_key, lang))
        return
    if not await _guard_current_lesson_trial_access(
        session=session,
        user=user,
        lesson=lesson,
        respond=callback.message.answer,
    ):
        await callback.answer()
        return

    step = progress.current_step
    if await _maybe_show_force_sub_checkpoint(
        callback=callback,
        session=session,
        user=user,
        step=step,
    ):
        return

    await callback.answer()
    await _send_step(callback.message.answer, user, lesson, step, lang, session)


async def _finish_study_time_flow(callback: CallbackQuery, session, saved_text: str):
    """Vaqt saqlangandan yoki o'tkazib yuborgandan keyin umumiy tugash oqimi."""
    engine = CourseEngineService(session)
    user_repo = UserRepository(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    lang = (user.language if user and user.language else "ru")

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(saved_text, parse_mode="HTML")

    _, progress, lesson, err = await engine.get_current_lesson(callback.from_user.id)
    if err or not lesson:
        return
    if not await _guard_current_lesson_trial_access(
        session=session,
        user=user,
        lesson=lesson,
        respond=callback.message.answer,
    ):
        return

    trial_service = CourseTrialService(session)
    if not trial_service.is_paid_user(user):
        await trial_service.mark_trial_completed(user, getattr(lesson, "id", None))
        await session.commit()
        await _send_trial_completed_offer(
            respond=callback.message.answer,
            lang=lang,
            user=user,
            telegram_id=callback.from_user.id,
            lesson_id=getattr(lesson, "id", None),
        )
        return

    if getattr(progress, "waiting_for", None) == "review_choice":
        await callback.message.answer(
            t("course_review_choice", lang),
            reply_markup=review_choice_keyboard(lang),
        )
    else:
        await send_course_completion_prompt(
            respond=callback.message.answer,
            engine=engine,
            lesson=lesson,
            lang=lang,
            progress=progress,
        )


@router.callback_query(F.data.startswith("course:study_time:"))
async def course_set_study_time_handler(callback: CallbackQuery, session):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    lang = user.language if user.language else "ru"
    time_str = callback.data.split(":")[-2] + ":" + callback.data.split(":")[-1]  # "09:00"

    # "09:00" → datetime bugun uchun
    try:
        h, m = int(time_str.split(":")[0]), int(time_str.split(":")[1])
        now = datetime.now(timezone.utc)
        next_study_at = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if next_study_at <= now:
            # Agar vaqt o'tib ketgan bo'lsa — ertaga
            from datetime import timedelta
            next_study_at = next_study_at + timedelta(days=1)
    except Exception:
        await callback.answer()
        return

    engine = CourseEngineService(session)
    await engine.set_next_study_at(callback.from_user.id, next_study_at)

    saved_labels = {
        "uz": f"✅ Keyingi dars vaqti saqlandi: <b>{time_str}</b>",
        "ru": f"✅ Время следующего урока сохранено: <b>{time_str}</b>",
        "tj": f"✅ Вақти дарси навбатӣ сабт шуд: <b>{time_str}</b>",
    }
    await callback.answer(f"✅ {time_str}")
    await _finish_study_time_flow(callback, session, saved_labels.get(lang, saved_labels["ru"]))


@router.callback_query(F.data == "course:skip_next_study_time")
async def course_skip_next_study_time_handler(callback: CallbackQuery, session):
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        await callback.message.answer(t("access_start_first", "ru"))
        return

    lang = user.language if user.language else "ru"

    engine = CourseEngineService(session)
    await engine.set_next_study_at(callback.from_user.id, None)

    await callback.answer()
    await _finish_study_time_flow(callback, session, t("course_next_study_time_skipped", lang))


_AUDIO_UNAVAILABLE = {
    "uz": "🔇 Audio hozircha mavjud emas",
    "ru": "🔇 Аудио пока недоступно",
    "tj": "🔇 Аудио ҳоло дастрас нест",
}

# ─── Audio fayl joylash qoidasi ───────────────────────────────────────────────
# Birinchi navbatda dars-spesifik path qidiriladi, keyin level-wide:
#   app/static/audio/{level}/lesson_{NN}/{name}.ogg   ← birinchi
#   app/static/audio/{level}/{name}.ogg               ← fallback
#
# Misol: hsk2/lesson_03/dialogue_1.ogg  yoki  hsk2/dialogue_1.ogg
# ─────────────────────────────────────────────────────────────────────────────
from app.repositories.course_audio_repo import CourseAudioRepository


async def _send_audio_file(callback: CallbackQuery, session, audio_type: str):
    """DB dan file_id topib yuboradi, yo'q bo'lsa foydalanuvchi tilida xabar ko'rsatadi."""
    if await _block_if_course_disabled(callback, session):
        return

    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    lang = (user.language if user and user.language else "ru")
    unavailable = _AUDIO_UNAVAILABLE.get(lang, _AUDIO_UNAVAILABLE["ru"])

    if not user:
        await callback.answer(unavailable, show_alert=True)
        return

    user, progress, lesson, error_key = await engine.get_current_lesson(callback.from_user.id)
    if error_key or not lesson:
        await callback.answer(unavailable, show_alert=True)
        return
    if not await _guard_current_lesson_trial_access(
        session=session,
        user=user,
        lesson=lesson,
        respond=callback.message.answer,
    ):
        await callback.answer()
        return

    level = (lesson.level or "hsk1").lower()
    order = lesson.lesson_order or 1

    audio_repo = CourseAudioRepository(session)
    file_id = await audio_repo.get(level=level, lesson_order=order, audio_type=audio_type)

    await callback.answer()
    if file_id:
        await callback.message.answer_voice(file_id)
    else:
        await callback.message.answer(unavailable)


@router.callback_query(F.data == "course:audio_vocab")
async def course_audio_vocab_handler(callback: CallbackQuery, session):
    await _send_audio_file(callback, session, "vocab")


@router.callback_query(F.data.startswith("course:audio_dialogue:"))
async def course_audio_dialogue_n_handler(callback: CallbackQuery, session):
    try:
        n = int(callback.data.split(":")[-1])
    except (ValueError, IndexError):
        n = 1
    await _send_audio_file(callback, session, f"dialogue_{n}")


# V1 eski handler (eski callback_data uchun)
@router.callback_query(F.data == "course:audio_dialogue")
async def course_audio_dialogue_handler(callback: CallbackQuery, session):
    await _send_audio_file(callback, session, "dialogue_1")


@router.callback_query(F.data.startswith("course:reminder_time:"))
async def course_set_reminder_time_handler(callback: CallbackQuery, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    try:
        hour = int(callback.data.split(":")[-2])
        minute = int(callback.data.split(":")[-1])
        reminder_time = time(hour, minute)
    except (TypeError, ValueError, IndexError):
        await callback.answer()
        return

    engine = CourseEngineService(session)
    progress = await engine.progress_repo.get_by_user_id(user.id)
    if not progress:
        await callback.answer()
        return

    await engine.progress_repo.set_reminder(progress, enabled=True, reminder_time=reminder_time)
    await engine.progress_repo.set_waiting_for(progress, "none")
    await session.commit()
    await callback.answer()
    await edit_callback_workflow_message(
        callback,
        state,
        t("course_reminder_tz_title", user.language or "ru"),
        chat_id_key=REMINDER_PANEL_CHAT_ID,
        message_id_key=REMINDER_PANEL_MSG_ID,
        reply_markup=course_reminder_timezone_keyboard(),
    )


@router.callback_query(F.data == "course:reminder_cancel")
async def course_cancel_reminder_setup_handler(callback: CallbackQuery, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    engine = CourseEngineService(session)
    progress = await engine.progress_repo.get_by_user_id(user.id)
    if progress:
        await engine.progress_repo.set_waiting_for(progress, "none")
        await session.commit()

    await callback.answer()
    await edit_callback_workflow_message(
        callback,
        state,
        t("course_reminder_cancelled", user.language or "ru"),
        chat_id_key=REMINDER_PANEL_CHAT_ID,
        message_id_key=REMINDER_PANEL_MSG_ID,
    )


@router.callback_query(F.data.startswith("course:set_tz:"))
async def course_set_timezone_handler(callback: CallbackQuery, state: FSMContext, session):
    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    lang = user.language if user.language else "ru"

    try:
        tz_offset = int(callback.data.split(":")[-1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    progress = await engine.progress_repo.get_by_user_id(user.id)
    if not progress or not progress.reminder_enabled or not progress.reminder_time:
        await callback.answer()
        return

    progress.reminder_tz_offset = tz_offset
    await session.commit()

    tz_labels = {3: "UTC+3 🇷🇺 Москва", 5: "UTC+5 🇺🇿🇹🇯 Тошкент/Душанбе", 8: "UTC+8 🇨🇳 Пекин"}
    tz_label = tz_labels.get(tz_offset, f"UTC+{tz_offset}")
    time_str = progress.reminder_time.strftime("%H:%M")

    await callback.answer()
    await edit_callback_workflow_message(
        callback,
        state,
        t("course_reminder_tz_saved", lang, time=time_str, tz=tz_label),
        chat_id_key=REMINDER_PANEL_CHAT_ID,
        message_id_key=REMINDER_PANEL_MSG_ID,
    )

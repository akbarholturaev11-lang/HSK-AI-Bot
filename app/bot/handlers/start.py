from aiogram import F, Router
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.repositories.user_repo import UserRepository
from app.services.onboarding_service import (
    ONBOARDING_MODE_CHOICE_MODE,
    OnboardingService,
    onboarding_stage,
)
from app.services.access_service import AccessService
from app.services.course_engine_service import CourseEngineService
from app.services.conversion_funnel_service import ConversionFunnelService
from app.services.daily_practice_service import DailyPracticeService
from app.bot.utils.i18n import t
from app.bot.utils.qa_entry import send_qa_entry
from app.bot.utils.menu_bar import send_menu_bar
from app.bot.keyboards.onboarding import (
    course_mode_entry_keyboard,
    daily_practice_check_keyboard,
    daily_practice_finish_keyboard,
    language_keyboard,
    level_keyboard,
    trial_lesson_selection_keyboard,
)
from app.bot.fsm.onboarding import OnboardingStates, QA_MODE_LEVEL_CHOICE_KEY


router = Router()




def _mode_choice_text(lang: str) -> str:
    texts = {
        "uz": (
            "🎉 <b>Tabriklaymiz! Kurs rejimi ochildi</b>\n\n"
            "<blockquote>Siz uchun tartibli HSK darslari yo‘li ochildi — so‘zlar, "
            "grammatika, quiz va AI Voice bitta ilovada, qadam-baqadam.</blockquote>\n\n"
            "Hoziroq boshlaymizmi?"
        ),
        "ru": (
            "🎉 <b>Поздравляем! Режим курса открыт</b>\n\n"
            "<blockquote>Для вас открыт путь последовательных уроков HSK — слова, "
            "грамматика, квиз и AI Voice в одном приложении, шаг за шагом.</blockquote>\n\n"
            "Начнём прямо сейчас?"
        ),
        "tj": (
            "🎉 <b>Табрик! Реҷаи курс кушода шуд</b>\n\n"
            "<blockquote>Барои шумо роҳи дарсҳои пайдарпайи HSK кушода шуд — калимаҳо, "
            "грамматика, quiz ва AI Voice дар як барнома, қадам ба қадам.</blockquote>\n\n"
            "Ҳозир оғоз мекунем?"
        ),
    }
    return texts.get(lang, texts["ru"])


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


def _lesson_choice_text(lang: str, level: str | None) -> str:
    label = (level or "HSK").upper()
    if label == "BEGINNER":
        label = "HSK1"
    texts = {
        "uz": f"<b>{label} kursi</b>\n\nQaysi darsdan boshlaymiz?",
        "ru": f"<b>Курс {label}</b>\n\nС какого урока начнём?",
        "tj": f"<b>Курси {label}</b>\n\nАз кадом дарс оғоз мекунем?",
    }
    return texts.get(lang, texts["ru"])




async def _start_trial_lesson(
    *,
    callback: CallbackQuery,
    state: FSMContext,
    session,
    lesson_id: int,
    show_menu: bool = False,
) -> None:
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    await _start_lesson_for_user(
        telegram_id=callback.from_user.id,
        respond=callback.message.answer,
        state=state,
        session=session,
        lesson_id=lesson_id,
        source="trial_lesson_pick",
        show_menu=show_menu,
    )


async def _start_lesson_for_user(
    *,
    telegram_id: int,
    respond,
    state: FSMContext | None,
    session,
    lesson_id: int,
    source: str,
    show_menu: bool = False,
) -> bool:
    user_repo = UserRepository(session)
    engine = CourseEngineService(session)

    user = await user_repo.get_by_telegram_id(telegram_id)
    if not user:
        await respond(t("access_start_first", "ru"))
        return False

    lang = user.language if user.language else "ru"
    lesson = await engine.lesson_repo.get_by_id(lesson_id)
    if not lesson or lesson.level not in _course_level_candidates(user.level):
        await respond(t("course_lesson_not_unlocked", lang))
        return False

    user.voice_mode = "none"
    user.expiry_reminder_sent_at = None
    await session.flush()

    if state:
        await state.clear()

    from app.bot.handlers.course import send_course_miniapp_entry

    await send_course_miniapp_entry(
        session=session,
        telegram_id=telegram_id,
        respond=respond,
        state=state,
        source=source,
        level=getattr(lesson, "level", None),
        lesson=getattr(lesson, "lesson_order", None),
    )
    return True


async def _start_first_available_course_lesson(
    *,
    telegram_id: int,
    respond,
    state: FSMContext | None,
    session,
    source: str,
    show_menu: bool = False,
) -> bool:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    lang = user.language if user and user.language else "ru"
    engine = CourseEngineService(session)
    lessons, _ = await _resolve_lessons_for_user_level(engine, user.level if user else None)
    if not lessons:
        await respond(t("course_no_lessons_available", lang))
        return False

    return await _start_lesson_for_user(
        telegram_id=telegram_id,
        respond=respond,
        state=state,
        session=session,
        lesson_id=lessons[0].id,
        source=source,
        show_menu=show_menu,
    )


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    session,
    command: CommandObject,
):
    service = OnboardingService(session)
    first_name = message.from_user.first_name if message.from_user and message.from_user.first_name else "Friend"

    referral_code = command.args.strip() if command and command.args else None

    user, created = await service.get_or_create_user(
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name if message.from_user else None,
        username=message.from_user.username if message.from_user else None,
        referral_code=referral_code,
        bot=message.bot,
    )

    await state.clear()

    stage = onboarding_stage(user)
    if not created and stage == "mode":
        lang = user.language if user and user.language else "ru"
        await message.answer(
            _mode_choice_text(lang),
            reply_markup=course_mode_entry_keyboard(lang),
            parse_mode="HTML",
        )
        return

    if not created and not stage and user.language and user.level:
        if getattr(user, "learning_mode", "qa") == "course":
            from app.bot.handlers.course import send_course_miniapp_entry

            # Kurs kartasi rasm + inline tugma bilan ketadi, unga reply
            # keyboard biriktirib bo'lmaydi. `/start` — userning ochiq
            # harakati, shuning uchun menyu har safar tiklanadi (once=False).
            await send_menu_bar(
                session=session,
                user=user,
                respond=message.answer,
                lang=user.language,
            )
            await send_course_miniapp_entry(
                session=session,
                telegram_id=message.from_user.id,
                respond=message.answer,
                state=state,
                source="start_course_migration",
            )
        else:
            await send_qa_entry(
                session=session,
                user=user,
                respond=message.answer,
                lang=user.language,
            )
        return

    onboarding_msg = await message.answer(
        f"{t('welcome', user.language, name=first_name)}\n\n{t('choose_language', user.language)}",
        reply_markup=language_keyboard(),
    )

    await state.update_data(
        onboarding_message_id=onboarding_msg.message_id,
    )
    await state.set_state(OnboardingStates.choosing_language)


@router.callback_query(OnboardingStates.choosing_language)
async def process_language(callback: CallbackQuery, state: FSMContext, session):
    lang = callback.data.split(":")[1]

    service = OnboardingService(session)

    user, _ = await service.get_or_create_user(
        telegram_id=callback.from_user.id,
        full_name=callback.from_user.full_name if callback.from_user else None,
        username=callback.from_user.username if callback.from_user else None,
    )
    user.language = lang
    user.learning_mode = ONBOARDING_MODE_CHOICE_MODE
    await session.commit()

    await callback.answer()

    data = await state.get_data()
    onboarding_message_id = data.get("onboarding_message_id")

    try:
        if onboarding_message_id:
            await callback.bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=onboarding_message_id,
                text=_mode_choice_text(lang),
                reply_markup=course_mode_entry_keyboard(lang),
                parse_mode="HTML",
            )
    except Exception:
        await callback.message.answer(
            _mode_choice_text(lang),
            reply_markup=course_mode_entry_keyboard(lang),
            parse_mode="HTML",
        )

    await state.clear()




@router.callback_query(OnboardingStates.choosing_level)
async def process_level(callback: CallbackQuery, state: FSMContext, session):
    level = callback.data.split(":")[1]
    data = await state.get_data()
    is_qa_mode_level_choice = bool(data.get(QA_MODE_LEVEL_CHOICE_KEY))

    service = OnboardingService(session)

    user, _ = await service.get_or_create_user(
        telegram_id=callback.from_user.id,
        full_name=callback.from_user.full_name if callback.from_user else None,
        username=callback.from_user.username if callback.from_user else None,
    )
    user.level = level
    user.learning_mode = "qa"
    user.voice_mode = "none"
    user.expiry_reminder_sent_at = None
    await session.commit()

    await callback.answer()
    if is_qa_mode_level_choice:
        lang = user.language if user.language else "ru"
        await state.clear()
        try:
            await callback.message.edit_text(
                t("free_mode_info", lang),
                parse_mode="HTML",
            )
        except Exception:
            await callback.message.answer(
                t("free_mode_info", lang),
                parse_mode="HTML",
            )
        await send_qa_entry(
            session=session,
            user=user,
            respond=callback.message.answer,
            lang=lang,
        )
        return

    try:
        await callback.message.delete()
    except Exception:
        pass

    await _start_first_available_course_lesson(
        telegram_id=callback.from_user.id,
        respond=callback.message.answer,
        state=state,
        session=session,
        source="onboarding_first_lesson",
    )


@router.callback_query(F.data == "daily_practice:start")
async def daily_practice_start(callback: CallbackQuery, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "ru"
    if not user:
        await callback.answer()
        await callback.message.answer(t("access_start_first", lang))
        return

    service = DailyPracticeService(session)
    await service.mark_started(user)
    await session.commit()

    await callback.answer()
    try:
        await callback.message.edit_text(
            service.practice_text(user, lang),
            reply_markup=daily_practice_check_keyboard(lang),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            service.practice_text(user, lang),
            reply_markup=daily_practice_check_keyboard(lang),
            parse_mode="HTML",
        )
    await state.set_state(OnboardingStates.daily_practice)


@router.callback_query(F.data == "daily_practice:complete")
async def daily_practice_complete(callback: CallbackQuery, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "ru"
    if not user:
        await callback.answer()
        await callback.message.answer(t("access_start_first", lang))
        return

    service = DailyPracticeService(session)
    if not getattr(user, "daily_practice_started_at", None):
        await service.mark_started(user)
    await service.mark_completed(user)
    user.learning_mode = "qa"
    user.voice_mode = "none"
    if user.payment_status != "approved" and user.status != "blocked":
        user.status = "trial"
        user.start_date = None
        user.end_date = None
    await session.commit()
    await ConversionFunnelService().record(
        event_name="course_cta_seen",
        user=user,
        source="daily_practice_completion",
    )

    await callback.answer()
    try:
        await callback.message.edit_text(
            service.completion_text(user, lang),
            reply_markup=daily_practice_finish_keyboard(lang),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            service.completion_text(user, lang),
            reply_markup=daily_practice_finish_keyboard(lang),
            parse_mode="HTML",
        )
    await state.clear()


@router.callback_query(F.data == "daily_practice:course")
async def daily_practice_course(callback: CallbackQuery, state: FSMContext, session):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await _start_first_available_course_lesson(
        telegram_id=callback.from_user.id,
        respond=callback.message.answer,
        state=state,
        session=session,
        source="daily_practice_course",
    )


@router.callback_query(OnboardingStates.choosing_trial_lesson, F.data == "trial_lesson:first")
async def process_trial_first_lesson(callback: CallbackQuery, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "ru"
    engine = CourseEngineService(session)
    lessons, _ = await _resolve_lessons_for_user_level(engine, user.level if user else None)
    if not lessons:
        await callback.answer()
        await callback.message.answer(t("course_no_lessons_available", lang))
        return

    await _start_trial_lesson(
        callback=callback,
        state=state,
        session=session,
        lesson_id=lessons[0].id,
    )


@router.callback_query(OnboardingStates.choosing_trial_lesson, F.data == "trial_lesson:choose")
async def process_trial_lesson_choose(callback: CallbackQuery, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "ru"
    engine = CourseEngineService(session)
    lessons, resolved_level = await _resolve_lessons_for_user_level(engine, user.level if user else None)
    if not lessons:
        await callback.answer()
        await callback.message.answer(t("course_no_lessons_available", lang))
        return

    await state.update_data(trial_lesson_level=resolved_level)
    await callback.answer()
    await callback.message.edit_text(
        _lesson_choice_text(lang, resolved_level),
        reply_markup=trial_lesson_selection_keyboard(lessons, page=0, lang=lang),
        parse_mode="HTML",
    )


@router.callback_query(OnboardingStates.choosing_trial_lesson, F.data.startswith("trial_lesson:page:"))
async def process_trial_lesson_page(callback: CallbackQuery, state: FSMContext, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "ru"
    try:
        page = int(callback.data.split(":")[-1])
    except Exception:
        page = 0

    engine = CourseEngineService(session)
    lessons, resolved_level = await _resolve_lessons_for_user_level(engine, user.level if user else None)
    await callback.answer()
    await callback.message.edit_text(
        _lesson_choice_text(lang, resolved_level),
        reply_markup=trial_lesson_selection_keyboard(lessons, page=page, lang=lang),
        parse_mode="HTML",
    )


@router.callback_query(OnboardingStates.choosing_trial_lesson, F.data.startswith("trial_lesson:pick:"))
async def process_trial_lesson_pick(callback: CallbackQuery, state: FSMContext, session):
    try:
        lesson_id = int(callback.data.split(":")[-1])
    except Exception:
        await callback.answer()
        return

    await _start_trial_lesson(
        callback=callback,
        state=state,
        session=session,
        lesson_id=lesson_id,
    )

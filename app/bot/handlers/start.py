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
from app.bot.keyboards.main_menu import course_menu_keyboard, main_menu_keyboard
from app.bot.keyboards.onboarding import (
    course_mode_entry_keyboard,
    daily_practice_check_keyboard,
    daily_practice_entry_keyboard,
    daily_practice_finish_keyboard,
    language_keyboard,
    level_keyboard,
    trial_lesson_choice_keyboard,
    trial_lesson_selection_keyboard,
)
from app.bot.fsm.onboarding import OnboardingStates


router = Router()


_OPTIONAL_CHALLENGE_CONTEXT_RULE = (
    "This mini-challenge is optional. If the user's next message is a clear "
    "attempt, evaluate it kindly and correctly. If there are mistakes, explain "
    "them briefly and show the correct version. If it is correct, praise briefly "
    "and offer one short next optional mini-challenge. If the next message is "
    "not a clear attempt, ignore the challenge and answer the user's actual "
    "message normally. Never pressure the user to complete the challenge."
)


def _challenge_context(base: str) -> str:
    return f"{base} {_OPTIONAL_CHALLENGE_CONTEXT_RULE}"


def _menu_keyboard_for_user(user):
    lang = user.language if user and user.language else "ru"
    if getattr(user, "learning_mode", "qa") == "course":
        return course_menu_keyboard(lang)
    return main_menu_keyboard(lang)


def _mode_choice_text(lang: str) -> str:
    texts = {
        "uz": (
            "<b>Qanday o‘rganishni xohlaysiz?</b>\n\n"
            "📚 <b>Kurs rejimi</b> — tartibli HSK darslari Mini App ichida.\n"
            "🤖 <b>Oddiy rejim</b> — Telegram chatda xitoy tili bo‘yicha savollar."
        ),
        "ru": (
            "<b>Как вы хотите учиться?</b>\n\n"
            "📚 <b>Режим курса</b> — последовательные уроки HSK внутри Mini App.\n"
            "🤖 <b>Обычный режим</b> — вопросы по китайскому языку прямо в Telegram."
        ),
        "tj": (
            "<b>Чӣ тавр мехоҳед омӯзед?</b>\n\n"
            "📚 <b>Реҷаи курс</b> — дарсҳои пайдарпайи HSK дар Mini App.\n"
            "🤖 <b>Реҷаи оддӣ</b> — саволҳои забони чинӣ дар Telegram."
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


async def _send_trial_lesson_choice(callback: CallbackQuery, state: FSMContext, session, *, edit: bool) -> None:
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "ru"
    if user:
        await ConversionFunnelService().record(
            event_name="course_started",
            user=user,
            source=str(callback.data or "trial_lesson_choice"),
        )
    text = _lesson_choice_text(lang, user.level if user else None)
    keyboard = trial_lesson_choice_keyboard(lang)
    if edit:
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            await state.set_state(OnboardingStates.choosing_trial_lesson)
            return
        except Exception:
            pass
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(OnboardingStates.choosing_trial_lesson)


async def _send_daily_practice_entry_message(message: Message, state: FSMContext, session, user=None) -> None:
    if user is None:
        user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    lang = user.language if user and user.language else "ru"
    service = DailyPracticeService(session)
    await message.answer(
        service.entry_text(user, lang),
        reply_markup=daily_practice_entry_keyboard(lang),
        parse_mode="HTML",
    )
    await state.set_state(OnboardingStates.daily_practice)


async def _send_daily_practice_entry_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session,
    *,
    edit: bool,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "ru"
    service = DailyPracticeService(session)
    text = service.entry_text(user, lang)
    keyboard = daily_practice_entry_keyboard(lang)
    if edit:
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            await state.set_state(OnboardingStates.daily_practice)
            return
        except Exception:
            pass
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(OnboardingStates.daily_practice)


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

            await send_course_miniapp_entry(
                session=session,
                telegram_id=message.from_user.id,
                respond=message.answer,
                state=state,
                source="start_course_migration",
            )
        else:
            await message.answer(
                t("send_first_message", user.language),
                reply_markup=main_menu_keyboard(user.language),
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


def _get_demo_lesson(level: str, lang: str) -> tuple:
    """Returns (display_text, ai_context) tuple."""

    challenges = {
        "beginner": {
            "tj": (
                "🎮 <b>Омода-ед? Бозӣ мекунем!</b>\n\n"
                "Ман ба шумо 3 калима медиҳам:\n\n"
                "✨ <b>你好</b> · <b>谢谢</b> · <b>再见</b>\n\n"
                "Агар хоҳед, аз ин калимаҳо як ҷумла созед. Нависед — бот месанҷад; нахоҳед, саволи худро диҳед 😄",
                _challenge_context(
                    "The user just started learning Chinese (beginner level). "
                    "You offered an optional mini-challenge: make a sentence using 你好, 谢谢, 再见. "
                    "Encourage them, correct gently, and explain the words when they attempt it."
                )
            ),
            "uz": (
                "🎮 <b>Tayyor bo'ldingizmi? O'yin boshlanadi!</b>\n\n"
                "Sizga 3 ta so'z beraman:\n\n"
                "✨ <b>你好</b> · <b>谢谢</b> · <b>再见</b>\n\n"
                "Xohlasangiz, shu so'zlardan bitta gap tuzing. Yozsangiz, bot tekshiradi; xohlamasangiz, oddiy savol bering 😄",
                _challenge_context(
                    "The user just started learning Chinese (beginner level). "
                    "You offered an optional mini-challenge: make a sentence using 你好, 谢谢, 再见. "
                    "Encourage them, correct gently, and explain the words when they attempt it."
                )
            ),
            "ru": (
                "🎮 <b>Готовы? Начинаем игру!</b>\n\n"
                "Даю вам 3 слова:\n\n"
                "✨ <b>你好</b> · <b>谢谢</b> · <b>再见</b>\n\n"
                "Если хотите, составьте из них одно предложение. Напишете — бот проверит; не хотите — задайте любой вопрос 😄",
                _challenge_context(
                    "The user just started learning Chinese (beginner level). "
                    "You offered an optional mini-challenge: make a sentence using 你好, 谢谢, 再见. "
                    "Encourage them, correct gently, and explain the words when they attempt it."
                )
            ),
        },
        "hsk1": {
            "tj": (
                "🎯 <b>HSK1 — Мушкилӣ дорад!</b>\n\n"
                "Ин 3 рақамро хонед:\n\n"
                "🔢 <b>三</b> · <b>十</b> · <b>百</b>\n\n"
                "Агар хоҳед, бо рақамҳо як ҷумла бисозед — масалан синнатон ё шумораи чизе. Нависед — месанҷам 🕵️",
                _challenge_context(
                    "The user is HSK1 level. You offered an optional mini-challenge: "
                    "make a sentence using Chinese numbers 三(3), 十(10), 百(100). "
                    "Correct and encourage when they attempt it."
                )
            ),
            "uz": (
                "🎯 <b>HSK1 — Qiyin emas!</b>\n\n"
                "Bu 3 raqamni o'qing:\n\n"
                "🔢 <b>三</b> · <b>十</b> · <b>百</b>\n\n"
                "Xohlasangiz, raqamlar bilan gap tuzing — masalan yoshingiz yoki biror narsa soni. Yozsangiz, tekshiraman 🕵️",
                _challenge_context(
                    "The user is HSK1 level. You offered an optional mini-challenge: "
                    "make a sentence using Chinese numbers 三(3), 十(10), 百(100). "
                    "Correct and encourage when they attempt it."
                )
            ),
            "ru": (
                "🎯 <b>HSK1 — Это несложно!</b>\n\n"
                "Прочитайте эти 3 числа:\n\n"
                "🔢 <b>三</b> · <b>十</b> · <b>百</b>\n\n"
                "Если хотите, составьте предложение с числами — например ваш возраст или количество чего-то. Напишете — проверю 🕵️",
                _challenge_context(
                    "The user is HSK1 level. You offered an optional mini-challenge: "
                    "make a sentence using Chinese numbers 三(3), 十(10), 百(100). "
                    "Correct and encourage when they attempt it."
                )
            ),
        },
        "hsk2": {
            "tj": (
                "🕵️ <b>HSK2 — Сир нигоҳ доред!</b>\n\n"
                "Дар ин ҷумла як иборае пинҳон аст:\n\n"
                "🇨🇳 <b>高兴 · 认识 · 你</b>\n\n"
                "Агар хоҳед, онҳоро дар як ҷумла ҷамъ кунед — шояд ибораи машҳур пайдо шавад. Нависед — месанҷам 😏",
                _challenge_context(
                    "The user is HSK2 level. You offered an optional mini-challenge: "
                    "combine 高兴(happy), 认识(meet/know), 你(you) into a sentence. "
                    "The hidden phrase is 很高兴认识你. Reveal it if they get close, explain it warmly."
                )
            ),
            "uz": (
                "🕵️ <b>HSK2 — Sir saqlang!</b>\n\n"
                "Bu so'zlarda mashhur ibora yashiringan:\n\n"
                "🇨🇳 <b>高兴 · 认识 · 你</b>\n\n"
                "Xohlasangiz, ulardan gap tuzing — nima hosil bo'lishini ko'ramiz. Yozsangiz, tekshiraman 😏",
                _challenge_context(
                    "The user is HSK2 level. You offered an optional mini-challenge: "
                    "combine 高兴(happy), 认识(meet/know), 你(you) into a sentence. "
                    "The hidden phrase is 很高兴认识你. Reveal it if they get close, explain it warmly."
                )
            ),
            "ru": (
                "🕵️ <b>HSK2 — Держите в тайне!</b>\n\n"
                "В этих словах спрятана знаменитая фраза:\n\n"
                "🇨🇳 <b>高兴 · 认识 · 你</b>\n\n"
                "Если хотите, составьте из них предложение — посмотрим, что получится. Напишете — проверю 😏",
                _challenge_context(
                    "The user is HSK2 level. You offered an optional mini-challenge: "
                    "combine 高兴(happy), 认识(meet/know), 你(you) into a sentence. "
                    "The hidden phrase is 很高兴认识你. Reveal it if they get close, explain it warmly."
                )
            ),
        },
        "hsk3": {
            "tj": (
                "🔥 <b>HSK3 — Имтиҳони зудӣ!</b>\n\n"
                "Ин ҷумларо тарҷума кунед:\n\n"
                "🇨🇳 <b>你今天心情怎么样？</b>\n\n"
                "Агар хоҳед, ҷавобро ба хитоӣ нависед. Нависед — ман месанҷам ва беҳтар мекунам 😤",
                _challenge_context(
                    "The user is HSK3 level. You offered an optional mini-challenge: "
                    "translate 你今天心情怎么样 (How are you feeling today?) and answer in Chinese. "
                    "Evaluate their Chinese, correct errors, and praise effort when they attempt it."
                )
            ),
            "uz": (
                "🔥 <b>HSK3 — Tezkor imtihon!</b>\n\n"
                "Bu jumlani tarjima qiling:\n\n"
                "🇨🇳 <b>你今天心情怎么样？</b>\n\n"
                "Xohlasangiz, javobni xitoycha yozing. Yozsangiz, tekshiraman va yaxshilab beraman 😤",
                _challenge_context(
                    "The user is HSK3 level. You offered an optional mini-challenge: "
                    "translate 你今天心情怎么样 (How are you feeling today?) and answer in Chinese. "
                    "Evaluate their Chinese, correct errors, and praise effort when they attempt it."
                )
            ),
            "ru": (
                "🔥 <b>HSK3 — Быстрый тест!</b>\n\n"
                "Переведите это предложение:\n\n"
                "🇨🇳 <b>你今天心情怎么样？</b>\n\n"
                "Если хотите, ответьте по-китайски. Напишете — проверю и улучшу ответ 😤",
                _challenge_context(
                    "The user is HSK3 level. You offered an optional mini-challenge: "
                    "translate 你今天心情怎么样 (How are you feeling today?) and answer in Chinese. "
                    "Evaluate their Chinese, correct errors, and praise effort when they attempt it."
                )
            ),
        },
        "hsk4": {
            "tj": (
                "⚡ <b>HSK4 — Устодро санҷем!</b>\n\n"
                "Ин ибораро дар як ҷумлаи мураккаб истифода баред:\n\n"
                "🇨🇳 <b>虽然...但是...</b>\n\n"
                "Агар хоҳед, онро дар як ҷумла аз ҳаёти худ истифода баред. Нависед — грамматикаро таҳлил мекунам 🎓",
                _challenge_context(
                    "The user is HSK4 level. You offered an optional mini-challenge: "
                    "use the grammar pattern 虽然...但是... (although...but...) in a complex sentence about their life. "
                    "Analyze grammar deeply and suggest improvements when they attempt it."
                )
            ),
            "uz": (
                "⚡ <b>HSK4 — Ustani sinaylik!</b>\n\n"
                "Bu grammatik konstruktsiyani murakkab gapda ishlating:\n\n"
                "🇨🇳 <b>虽然...但是...</b>\n\n"
                "Xohlasangiz, uni o'z hayotingizdan bitta gapda ishlating. Yozsangiz, grammatikasini tahlil qilaman 🎓",
                _challenge_context(
                    "The user is HSK4 level. You offered an optional mini-challenge: "
                    "use the grammar pattern 虽然...但是... (although...but...) in a complex sentence about their life. "
                    "Analyze grammar deeply and suggest improvements when they attempt it."
                )
            ),
            "ru": (
                "⚡ <b>HSK4 — Проверим мастера!</b>\n\n"
                "Используйте эту конструкцию в сложном предложении:\n\n"
                "🇨🇳 <b>虽然...但是...</b>\n\n"
                "Если хотите, используйте её в одном предложении из своей жизни. Напишете — разберу грамматику 🎓",
                _challenge_context(
                    "The user is HSK4 level. You offered an optional mini-challenge: "
                    "use the grammar pattern 虽然...但是... (although...but...) in a complex sentence about their life. "
                    "Analyze grammar deeply and suggest improvements when they attempt it."
                )
            ),
        },
    }

    level_key = level.lower().replace(" ", "").replace("_", "")
    lang_key = lang if lang in ("tj", "uz", "ru") else "ru"

    level_map = {
        "beginner": "beginner", "az0": "beginner",
        "hsk1": "hsk1", "hsk2": "hsk2", "hsk3": "hsk3", "hsk4": "hsk4",
    }
    mapped = level_map.get(level_key, "beginner")
    result = challenges.get(mapped, {}).get(lang_key)
    if result:
        return result
    return ("", "")


@router.callback_query(OnboardingStates.choosing_level)
async def process_level(callback: CallbackQuery, state: FSMContext, session):
    level = callback.data.split(":")[1]

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

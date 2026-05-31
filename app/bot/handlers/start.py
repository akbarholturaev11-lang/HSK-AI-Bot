from datetime import datetime, timezone, timedelta

from aiogram import Router
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.services.onboarding_service import OnboardingService
from app.bot.utils.i18n import t
from app.bot.keyboards.main_menu import course_menu_keyboard, main_menu_keyboard
from app.bot.keyboards.onboarding import language_keyboard, level_keyboard
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


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    session,
    command: CommandObject,
):
    service = OnboardingService(session)
    first_name = message.from_user.first_name if message.from_user and message.from_user.first_name else "Friend"

    referral_code = command.args if command and command.args else None

    user, created = await service.get_or_create_user(
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name if message.from_user else None,
        username=message.from_user.username if message.from_user else None,
        referral_code=referral_code,
        bot=message.bot,
    )

    await state.clear()

    if not created and user.language and user.level:
        await message.answer(
            t("welcome_back", user.language, name=first_name),
            reply_markup=_menu_keyboard_for_user(user),
        )
        return

    onboarding_msg = await message.answer(
        f"{t('welcome', user.language, name=first_name)}\n\n{t('choose_language', user.language)}",
        reply_markup=language_keyboard(),
    )

    await state.update_data(
        onboarding_message_id=onboarding_msg.message_id,
        first_name=first_name,
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
    await session.commit()

    await callback.answer()

    data = await state.get_data()
    onboarding_message_id = data.get("onboarding_message_id")
    first_name = data.get("first_name", "Friend")

    try:
        if onboarding_message_id:
            await callback.bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=onboarding_message_id,
                text=f"{t('welcome', lang, name=first_name)}\n\n{t('choose_level', lang)}",
                reply_markup=level_keyboard(lang),
            )
    except Exception:
        pass

    await state.update_data(lang=lang)
    await state.set_state(OnboardingStates.choosing_level)


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
    now = datetime.now(timezone.utc)
    user.level = level
    user.learning_mode = "qa"
    user.voice_mode = "none"
    user.status = "active"
    user.start_date = now
    user.end_date = now + timedelta(hours=24)
    user.expiry_reminder_sent_at = None
    await session.commit()

    await callback.answer()

    data = await state.get_data()
    onboarding_message_id = data.get("onboarding_message_id")

    user_num = str(user.id)

    try:
        if onboarding_message_id:
            await callback.bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=onboarding_message_id,
            )
    except Exception:
        pass

    await callback.message.answer(
        t("onboarding_special_welcome", user.language, user_num=user_num),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(user.language),
    )

    display_text, ai_context = _get_demo_lesson(level, user.language)

    if display_text:
        await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text=display_text,
            parse_mode="HTML",
        )

    if ai_context:
        from app.repositories.message_repo import MessageRepository
        msg_repo = MessageRepository(session)
        await msg_repo.create(
            user_id=user.id,
            role="system",
            content=ai_context,
            content_type="onboarding_challenge",
        )
        await session.commit()

    await state.clear()

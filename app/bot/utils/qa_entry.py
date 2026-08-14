"""QA (savol-javob) rejimiga kirish xabari.

Ilgari kirishda quruq `send_first_message` ("savolingizni yuboring") chiqardi —
user o'zi savol o'ylab topmasa suhbat boshlanmasdi. Endi bot darajaga mos
bitta mini-savol beradi va o'sha savolni `onboarding_challenge` sifatida
saqlaydi. `qa_service` bu content_type'ni o'qib AI promptiga qo'shadi
(`ONBOARDING_OPTIONAL_CHALLENGE_RULE`), shuning uchun user javob yozsa AI uni
baholaydi va keyingi mini-savolni o'zi taklif qiladi.

Alohida modul: bu helper `start.py`, `course.py`, `commands.py` va
`messages.py` dan chaqiriladi — handler fayllaridan biriga qo'ysak circular
import chiqadi.
"""

from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.utils.i18n import t
from app.repositories.message_repo import MessageRepository
from app.services.daily_practice_service import DailyPracticeService


QA_CHALLENGE_CONTENT_TYPE = "onboarding_challenge"


async def send_qa_entry(
    *,
    session,
    user,
    respond,
    lang: str | None = None,
) -> None:
    """QA rejimi kirish xabarini yuboradi.

    `respond` — `message.answer` yoki `callback.message.answer` kabi coroutine.
    Xatolik bo'lsa oqim to'xtamasin: challenge tayyorlanmasa eski matn chiqadi.
    """
    lang = lang or (getattr(user, "language", None) or "ru")

    challenge = None
    if user is not None:
        # Rotatsiya urug'i: ilgari yuborilgan challenge'lar soni. Kun bo'yicha
        # aylantirsak, bir kunda bir necha marta kirgan user bir xil savolni
        # qayta ko'rardi.
        try:
            seed = await MessageRepository(session).count_by_content_type(
                user_id=user.id,
                content_type=QA_CHALLENGE_CONTENT_TYPE,
            )
        except Exception:
            seed = 0
        try:
            challenge = DailyPracticeService(session).first_challenge(user, lang, seed=seed)
        except Exception:
            challenge = None

    if not challenge:
        await respond(
            t("send_first_message", lang),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    await respond(
        challenge["text"],
        reply_markup=main_menu_keyboard(lang),
        parse_mode="HTML",
    )

    # `role="system"`: `qa_service` oddiy history filtri faqat user/assistant
    # ni oladi, aks holda challenge promptga ikki marta tushardi.
    try:
        await MessageRepository(session).create(
            user_id=user.id,
            role="system",
            content=challenge["context"],
            content_type=QA_CHALLENGE_CONTENT_TYPE,
        )
        await session.commit()
    except Exception:
        pass

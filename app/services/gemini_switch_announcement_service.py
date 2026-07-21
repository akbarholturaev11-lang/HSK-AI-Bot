"""Gemini yoqilganda bir martalik e'lon (limit o'zgardi) xabari.

Mantiq (foydalanuvchi so'rovi bo'yicha):
- Railway env'da `GEMINI_API_KEY` paydo bo'lib, Gemini asosiy provayder bo'lganda,
  bot bir marta HAMMA (bloklamagan) foydalanuvchiga o'z tilida xabar yuboradi:
  chatda matn endi cheksiz/bepul, foto va ovoz kuniga 5 tadan.
- Takrorlanmasligi uchun `bot_settings.gemini_switch_announced` flagi ishlatiladi.
- Scheduler tsiklini bloklamaslik uchun yetkazish alohida background task'da ketadi;
  flag yuborishdan OLDIN o'rnatiladi (qayta ishga tushishda dublikat bo'lmasligi uchun).
"""

import asyncio
import logging

from aiogram import Bot
from sqlalchemy import select

from app.db.models.user import User
from app.db.session import async_session_maker
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.ai_provider import gemini_active
from app.services.bot_block_status_service import BotBlockStatusService

logger = logging.getLogger(__name__)

ANNOUNCED_FLAG_KEY = "gemini_switch_announced"

# Har til uchun e'lon matni (uz/ru/tj). Boshqa tillar uchun tj zaxira.
ANNOUNCEMENT_TEXT = {
    "uz": (
        "<b>🎉 Yaxshi yangilik!</b>\n\n"
        "<blockquote>Endi chatda <b>matn</b> orqali AI bilan xitoy tilini "
        "<b>cheksiz va bepul</b> o'rganishingiz mumkin — kunlik limit yo'q!\n\n"
        "📸 Foto va 🎙 ovozli xabarlar uchun kuniga 5 tadan bepul.\n\n"
        "Hoziroq sinab ko'ring — savolingizni yozing!</blockquote>"
    ),
    "ru": (
        "<b>🎉 Хорошие новости!</b>\n\n"
        "<blockquote>Теперь вы можете изучать китайский с AI в чате "
        "<b>текстом — без лимитов и бесплатно</b>!\n\n"
        "📸 Фото и 🎙 голосовые — по 5 в день бесплатно.\n\n"
        "Попробуйте прямо сейчас — напишите свой вопрос!</blockquote>"
    ),
    "tj": (
        "<b>🎉 Хабари хуш!</b>\n\n"
        "<blockquote>Акнун шумо метавонед забони хитоиро бо AI дар чат "
        "<b>бо матн — бе лимит ва ройгон</b> омӯзед!\n\n"
        "📸 Акс ва 🎙 паёмҳои овозӣ — дар як рӯз 5-тоӣ ройгон.\n\n"
        "Ҳозир санҷед — саволатонро нависед!</blockquote>"
    ),
}


def _text_for_language(language) -> str:
    lang = language if language in ANNOUNCEMENT_TEXT else "tj"
    return ANNOUNCEMENT_TEXT[lang]


async def announce_if_needed(bot: Bot) -> None:
    """Scheduler har tsiklda chaqiradi. Shart bajarilsa yetkazishni bir marta boshlaydi."""
    if not gemini_active():
        return

    async with async_session_maker() as session:
        repo = BotSettingRepository(session)
        if await repo.get_bool(ANNOUNCED_FLAG_KEY, False):
            return
        # Dublikatni oldini olish uchun flag yuborishdan oldin o'rnatiladi.
        await repo.set_bool(ANNOUNCED_FLAG_KEY, True)
        await session.commit()

    logger.info("Gemini switch e'loni boshlandi — foydalanuvchilarga yuborilyapti")
    asyncio.create_task(_deliver_all(bot))


async def _deliver_all(bot: Bot) -> None:
    sent = 0
    try:
        async with async_session_maker() as session:
            result = await session.execute(select(User))
            users = list(result.scalars().all())
            block_service = BotBlockStatusService(session)

            for user in users:
                if getattr(user, "status", "") == "blocked":
                    continue
                try:
                    await bot.send_message(
                        user.telegram_id,
                        _text_for_language(getattr(user, "language", None)),
                        parse_mode="HTML",
                    )
                    sent += 1
                    if BotBlockStatusService.is_bot_blocked(user):
                        await block_service.mark_user_unblocked(user)
                except Exception as exc:  # noqa: BLE001 — bloklagan/o'chirgan userlar kutilgan
                    try:
                        await block_service.handle_send_exception(
                            user.telegram_id, exc, reason="gemini_switch"
                        )
                    except Exception:
                        pass
                await asyncio.sleep(0.05)

            try:
                await session.commit()
            except Exception:
                await session.rollback()
        logger.info("Gemini switch e'loni %s foydalanuvchiga yuborildi", sent)
    except Exception:
        logger.exception("Gemini switch e'lonini yetkazishda xato")

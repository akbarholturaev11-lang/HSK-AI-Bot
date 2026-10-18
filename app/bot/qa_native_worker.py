"""Isolated Telegram approval worker for Universal Sign-In staging QA.

Only handles explicit Telegram /start, native login/link deep links, and
approval/cancel callbacks. No broadcast, payment or lesson schedulers; no
production bot/website/miniapp registrations. Never run in production.
"""
from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from sqlalchemy.engine import make_url

from app.bot.handlers.desktop_auth import router as native_link_router
from app.bot.middlewares.blocked_user import BlockedUserMiddleware
from app.bot.middlewares.db import DBSessionMiddleware
from app.config import settings
from app.db.session import async_session_maker, engine

logger = logging.getLogger(__name__)
QA_DATABASE = "hsk_universal_qa_schema"
QA_SERVICE_DNS = "hsk-universal-qa-db.railway.internal"
QA_FLAG = "HSK_QA_TELEGRAM_WORKER_ENABLED"
PRODUCTION_BOT_USERNAME = "darsi_chini_bot"

qa_start_router = Router(name="qa_native_start")


@qa_start_router.message(CommandStart())
async def qa_start(message: Message) -> None:
    if str(message.chat.type) != "private":
        return
    await message.answer(
        "🧪 <b>HSK AI QA — test bot</b>\n\n"
        "Bu bot faqat test ilovasiga Telegram orqali kirish yoki "
        "Telegram akkauntini ulashni tasdiqlash uchun ishlaydi.\n"
        "Telefoningizda <b>HSK AI QA</b> ilovasidan Telegram kirishni boshlang.\n\n"
        "Bu haqiqiy HSK AI ishlab turgan bot emas.",
        parse_mode="HTML",
    )


def assert_qa_runtime(*, env: dict[str, str], database_url: str, username: str) -> str:
    """Fail closed before making any Telegram API call or database write."""
    if str(env.get("RAILWAY_ENVIRONMENT_NAME", "")).lower() != "staging":
        raise RuntimeError("qa_worker_not_staging")
    if str(env.get(QA_FLAG, "")).lower() != "true":
        raise RuntimeError("qa_worker_disabled")
    expected = username.strip().lstrip("@").lower()
    if not expected or expected == PRODUCTION_BOT_USERNAME:
        raise RuntimeError("qa_worker_bot_username_invalid")
    try:
        url = make_url(database_url)
    except Exception as exc:
        raise RuntimeError("qa_worker_database_invalid") from exc
    if url.database != QA_DATABASE or str(url.host or "").lower() != QA_SERVICE_DNS:
        raise RuntimeError("qa_worker_wrong_database")
    return expected


def create_qa_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(DBSessionMiddleware(async_session_maker))
    dp.callback_query.middleware(DBSessionMiddleware(async_session_maker))
    dp.message.middleware(BlockedUserMiddleware(async_session_maker))
    dp.callback_query.middleware(BlockedUserMiddleware(async_session_maker))
    # These handlers must execute before the generic /start reply.
    dp.include_router(native_link_router)
    dp.include_router(qa_start_router)
    return dp


async def main() -> None:
    expected = assert_qa_runtime(
        env=dict(os.environ), database_url=settings.DATABASE_URL,
        username=settings.BOT_USERNAME,
    )
    if not settings.BOT_TOKEN:
        raise RuntimeError("qa_worker_missing_token")

    bot = Bot(token=settings.BOT_TOKEN,
              default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        actual = await bot.get_me()
        if not actual.is_bot or (actual.username or "").lower() != expected:
            raise RuntimeError("qa_worker_token_username_mismatch")
        webhook = await bot.get_webhook_info()
        # Do not alter a webhook that may belong to a different running service.
        if webhook.url:
            raise RuntimeError("qa_worker_webhook_active")
        dp = create_qa_dispatcher()
        logger.info("QA Telegram approvals worker started for @%s", expected)
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"],
                               close_bot_session=False)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

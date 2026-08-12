"""Bloklangan foydalanuvchi uchun global to'siq.

Admin panelda `status="blocked"` qilingan foydalanuvchi bot bilan umuman
ishlay olmasligi kerak: menyu, komandalar, callback tugmalar va Mini App
tugmalari — hammasi to'xtaydi. Faqat bir marta (cooldown bilan) blok
xabari yuboriladi, keyin bot jim qoladi.

Middleware `DBSessionMiddleware` dan keyin ro'yxatdan o'tadi, shuning uchun
`data["session"]` tayyor bo'ladi va qo'shimcha DB ulanishi ochilmaydi.
"""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from app.bot.utils.i18n import t
from app.repositories.user_repo import UserRepository
from app.services.required_channel_service import is_admin_user
from app.services.support_contact_service import get_admin_contact_html

# Bir foydalanuvchiga blok xabari shu oraliqda faqat bir marta yuboriladi.
# Aks holda user 50 marta tugma bossa 50 ta bir xil xabar keladi.
BLOCK_NOTICE_COOLDOWN_SECONDS = 600

# telegram_id -> oxirgi xabar yuborilgan vaqt (monotonic)
_notice_sent_at: dict[int, float] = {}


def _should_notify(telegram_id: int) -> bool:
    now = time.monotonic()
    last = _notice_sent_at.get(telegram_id)
    if last is not None and (now - last) < BLOCK_NOTICE_COOLDOWN_SECONDS:
        return False
    _notice_sent_at[telegram_id] = now
    # Xotira cheksiz o'smasin: eskirgan yozuvlarni tozalaymiz.
    if len(_notice_sent_at) > 5000:
        cutoff = now - BLOCK_NOTICE_COOLDOWN_SECONDS
        for key in [k for k, v in _notice_sent_at.items() if v < cutoff]:
            _notice_sent_at.pop(key, None)
    return True


def reset_block_notice_state() -> None:
    """Testlar uchun cooldown holatini tozalaydi."""
    _notice_sent_at.clear()


class BlockedUserMiddleware(BaseMiddleware):
    def __init__(self, sessionmaker):
        self.sessionmaker = sessionmaker

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ):
        tg_user = getattr(event, "from_user", None)
        if not tg_user:
            return await handler(event, data)

        # Admin hech qachon bloklanmaydi — aks holda panelga kira olmay qoladi.
        if is_admin_user(tg_user.id):
            return await handler(event, data)

        session = data.get("session")
        if session is None:
            return await handler(event, data)

        user = await UserRepository(session).get_by_telegram_id(tg_user.id)
        if not user or user.status != "blocked":
            return await handler(event, data)

        await self._notify(event, data, user)
        # Handlerga o'tkazmaymiz: komanda, menyu, callback — hammasi to'xtaydi.
        return None

    async def _notify(self, event: Any, data: dict[str, Any], user) -> None:
        if not _should_notify(user.telegram_id):
            # Cooldown ichida: callbackda "soat" aylanib qolmasligi uchun
            # bo'sh javob beramiz, xabar yubormaymiz.
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer()
                except Exception:  # noqa: BLE001
                    pass
            return

        lang = getattr(user, "language", None) or "ru"
        try:
            support_contact = await get_admin_contact_html(data.get("session"), "ADMIN")
        except Exception:  # noqa: BLE001
            support_contact = "ADMIN"
        text = t("access_blocked", lang, support_contact=support_contact)

        try:
            if isinstance(event, CallbackQuery):
                await event.answer()
                if event.message:
                    await event.message.answer(text, parse_mode="HTML")
            elif isinstance(event, Message):
                await event.answer(text, parse_mode="HTML")
        except Exception:  # noqa: BLE001
            # User botni bloklagan yoki chat yopiq — jim o'tamiz.
            pass

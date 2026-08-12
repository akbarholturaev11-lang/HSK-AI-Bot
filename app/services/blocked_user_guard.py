"""Bloklangan foydalanuvchi uchun Mini App API to'sig'i.

`app/main.py` ichida 40 dan ortiq joyda `X-Telegram-Init-Data` alohida
tekshiriladi, yagona choke point yo'q. Shuning uchun blok tekshiruvi bitta
HTTP middleware sifatida qo'yiladi: initData bilan kelgan har qanday
`/api/*` so'rovi bloklangan foydalanuvchidan bo'lsa, 403 qaytariladi.

Har so'rovda DB ga bormaslik uchun qisqa TTL cache ishlatiladi. Admin
bloklaganda/blokdan chiqarganda `invalidate()` chaqiriladi, shuning uchun
cache eskirib qolmaydi.
"""

from __future__ import annotations

import time

from sqlalchemy import select
from starlette.responses import JSONResponse

from app.db.models.user import User
from app.services.support_contact_service import get_admin_contact_url
from app.services.telegram_webapp_auth import extract_verified_webapp_user_id

# Blok holati shu muddat davomida cache'da saqlanadi.
BLOCK_CACHE_TTL_SECONDS = 30

# Guard faqat shu prefiksli yo'llarga ishlaydi. Admin panel API'lari
# `_admin_auth_error()` bilan alohida himoyalangan va bu yerdan chetlatiladi.
GUARDED_PATH_PREFIX = "/api/"
EXEMPT_PATH_PREFIXES = ("/api/admin-miniapp/",)

# telegram_id -> (blocked, saqlangan vaqt)
_cache: dict[int, tuple[bool, float]] = {}


def invalidate(telegram_id: int | None = None) -> None:
    """Blok holati o'zgarganda cache'ni tozalaydi."""
    if telegram_id is None:
        _cache.clear()
    else:
        _cache.pop(int(telegram_id), None)


def _cached(telegram_id: int) -> bool | None:
    entry = _cache.get(telegram_id)
    if not entry:
        return None
    blocked, saved_at = entry
    if (time.monotonic() - saved_at) > BLOCK_CACHE_TTL_SECONDS:
        _cache.pop(telegram_id, None)
        return None
    return blocked


def _store(telegram_id: int, blocked: bool) -> None:
    if len(_cache) > 10000:
        _cache.clear()
    _cache[telegram_id] = (blocked, time.monotonic())


async def is_blocked_telegram_id(session_maker, telegram_id: int) -> bool:
    cached = _cached(telegram_id)
    if cached is not None:
        return cached
    async with session_maker() as session:
        status = (
            await session.execute(
                select(User.status).where(User.telegram_id == telegram_id)
            )
        ).scalar_one_or_none()
    blocked = status == "blocked"
    _store(telegram_id, blocked)
    return blocked


def _init_data_header(scope) -> str:
    for key, value in scope.get("headers") or ():
        if key == b"x-telegram-init-data":
            try:
                return value.decode("latin-1")
            except Exception:  # noqa: BLE001
                return ""
    return ""


class BlockedUserApiMiddleware:
    """Toza ASGI middleware.

    `BaseHTTPMiddleware` ishlatilmaydi: u har bir javobni (jumladan audio va
    static `FileResponse` streaminglarini) o'rab oladi. Bu yerda esa faqat
    `/api/*` yo'llari tekshiriladi, qolgani hech qanday qo'shimcha qatlamsiz
    to'g'ridan-to'g'ri o'tadi.
    """

    def __init__(self, app, *, session_maker, bot_token: str, admin_ids=()):
        self.app = app
        self.session_maker = session_maker
        self.bot_token = bot_token
        self.admin_ids = set(admin_ids or ())

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)

        path = scope.get("path") or ""
        if not path.startswith(GUARDED_PATH_PREFIX) or path.startswith(EXEMPT_PATH_PREFIXES):
            return await self.app(scope, receive, send)

        init_data = _init_data_header(scope)
        if not init_data:
            # initData yo'q so'rovlar o'z endpointidagi auth bilan ishlaydi.
            return await self.app(scope, receive, send)

        try:
            telegram_id = extract_verified_webapp_user_id(init_data, self.bot_token)
        except Exception:  # noqa: BLE001
            telegram_id = None
        if not telegram_id or telegram_id in self.admin_ids:
            return await self.app(scope, receive, send)

        try:
            blocked = await is_blocked_telegram_id(self.session_maker, telegram_id)
        except Exception:  # noqa: BLE001
            # DB xatosi tufayli ishlayotgan userlarni to'xtatib qo'ymaymiz.
            return await self.app(scope, receive, send)

        if not blocked:
            return await self.app(scope, receive, send)

        # Bloklangan user supportga yozа olsin — kontakt linkini javobga qo'shamiz.
        support_url = ""
        try:
            async with self.session_maker() as session:
                support_url = await get_admin_contact_url(session)
        except Exception:  # noqa: BLE001
            support_url = ""

        response = JSONResponse(
            status_code=403,
            content={"ok": False, "error": "user_blocked", "support_url": support_url},
        )
        return await response(scope, receive, send)

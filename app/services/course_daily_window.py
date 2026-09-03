"""Kunlik bepul limit oynasi — bitta joyda.

Ilgari har servis o'zining `_day_start()` ini yozardi va ikkalasi ham UTC
yarim tunga tayanardi. Natijada UTC+5 da yashaydigan o'quvchining limiti
mahalliy soat 05:00 da yangilanardi: kun boshida emas, ertalab.

Bu modul o'sha oynani o'quvchining vaqt mintaqasida hisoblaydi va ikkala
servis ham shu yerdan foydalanadi. Sof funksiyalar: bazaga ham, Android'ga
ham bog'liq emas, shuning uchun soat bo'yicha to'liq test qilinadi.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


# Klientlar yuboradigan qiymat shu oraliqqa qisiladi (UTC-12 .. UTC+14).
MIN_TZ_OFFSET_MINUTES = -720
MAX_TZ_OFFSET_MINUTES = 840


def normalize_offset_minutes(value) -> int:
    """Ishonchsiz manbadan kelgan mintaqa siljishini xavfsiz songa keltiradi."""

    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return 0
    return max(MIN_TZ_OFFSET_MINUTES, min(MAX_TZ_OFFSET_MINUTES, minutes))


def reset_hour_local() -> int:
    """Limit mahalliy vaqt bilan qaysi soatda yangilanadi (env orqali)."""

    try:
        from app.config import settings as _settings

        hour = int(getattr(_settings, "COURSE_DAILY_RESET_HOUR_LOCAL", 0) or 0)
    except Exception:  # noqa: BLE001 — sozlama o'qilmasa yarim tun
        hour = 0
    # Noto'g'ri sozlama limitni butunlay buzmasin.
    return hour if 0 <= hour <= 23 else 0


def day_start(offset_minutes=0, now: datetime | None = None) -> datetime:
    """Joriy 'limit kuni'ning boshlanishi, UTC da qaytadi.

    Siljish 0 va reset soati 0 bo'lganda bu aynan UTC yarim tun — ya'ni
    mintaqasi noma'lum o'quvchi uchun xatti-harakat o'zgarmaydi.
    """
    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    offset = timedelta(minutes=normalize_offset_minutes(offset_minutes))
    local_now = moment + offset
    local_start = local_now.replace(
        hour=reset_hour_local(), minute=0, second=0, microsecond=0
    )
    if local_now < local_start:
        local_start -= timedelta(days=1)
    return local_start - offset


def next_day_reset(offset_minutes=0, now: datetime | None = None) -> datetime:
    """Limit keyingi marta qachon ochilishi, UTC da.

    Server hech qachon formatlangan soat qaytarmaydi — klient buni o'z
    mintaqasida ko'rsatadi.
    """
    return day_start(offset_minutes, now) + timedelta(days=1)


def local_day_key(offset_minutes=0, now: datetime | None = None) -> str:
    """Idempotentlik uchun kun kaliti: o'quvchining mahalliy sanasi."""

    offset = timedelta(minutes=normalize_offset_minutes(offset_minutes))
    return (day_start(offset_minutes, now) + offset).date().isoformat()

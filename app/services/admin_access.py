"""Adminlarni doim cheksiz 'active' obuna holatida ushlab turish yordamchisi.

Admin ID lar (settings.ADMIN_IDS) uchun obuna hech qachon tugamasin: status
"active", to'lov "approved" va end_date uzoq kelajakka (2099) qo'yiladi. Shunda
paywall, kurs, AI limit va admin panelda admin doim faol ko'rinadi.
"""
from datetime import datetime, timezone

from app.config import settings

# Amalda "cheksiz" — obuna hech qachon tugamaydigan uzoq kelajak sanasi.
ADMIN_ACTIVE_UNTIL = datetime(2099, 1, 1, tzinfo=timezone.utc)


def is_admin_user(telegram_id: int | None) -> bool:
    if telegram_id is None:
        return False
    try:
        return int(telegram_id) in settings.admin_id_list
    except (TypeError, ValueError):
        return False


async def ensure_admin_active(session, user) -> bool:
    """Admin foydalanuvchini cheksiz 'active' holatga keltiradi.

    O'zgarish bo'lsa True qaytaradi. Admin bo'lmasa yoki user yo'q bo'lsa —
    hech narsa qilmaydi.
    """
    if not user or not is_admin_user(getattr(user, "telegram_id", None)):
        return False

    changed = False
    if user.status != "active":
        user.status = "active"
        changed = True
    if user.payment_status != "approved":
        user.payment_status = "approved"
        changed = True

    end_date = user.end_date
    if end_date is not None and end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)
    if end_date is None or end_date < ADMIN_ACTIVE_UNTIL:
        user.end_date = ADMIN_ACTIVE_UNTIL
        changed = True
    if user.start_date is None:
        user.start_date = datetime.now(timezone.utc)
        changed = True

    if changed:
        await session.flush()
    return changed

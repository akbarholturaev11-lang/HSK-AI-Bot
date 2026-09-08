"""Foydalanuvchining kirish holati — yagona manba.

Bugun "bu odam nima qila oladi" degan savolga ikki xil predikat javob beradi:
`UserAccessStateService.is_paid()` (tor: faqat tasdiqlangan to'lov) va
`has_unlimited_course_access()` (keng: to'lov + vaqtinchalik kirish). Mini App
kengini, desktop/Android esa torini ishlatadi — shuning uchun referral
mukofotini olgan odam telefonda darsni ochadi, desktopda ocholmaydi.

Bu modul o'sha ikkilikni ikkita ANIQ nomlangan savolga ajratadi:

* `has_full_access(state)` — kontent qulfi uchun. "Bu odamga dars ochiqmi?"
* `is_billing_paid(state)`  — to'lov UI si uchun. "Bu odam obunachimi?"

`UserAccessStateService` o'raladi, almashtirilmaydi: u xom klassifikator
bo'lib qoladi va uning javoblari shu yerda nomlanadi.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.user_access_state_service import (
    UserAccessState,
    UserAccessStateService,
)


class EntitlementState:
    FREE = "FREE"
    TRIAL_ACTIVE = "TRIAL_ACTIVE"
    PRO_ACTIVE = "PRO_ACTIVE"
    TEMP_ACCESS = "TEMP_ACCESS"
    EXPIRED = "EXPIRED"
    BLOCKED = "BLOCKED"


#: Barcha holatlar — konfiguratsiya validatsiyasi shu ro'yxatga tayanadi.
ENTITLEMENT_STATES = (
    EntitlementState.FREE,
    EntitlementState.TRIAL_ACTIVE,
    EntitlementState.PRO_ACTIVE,
    EntitlementState.TEMP_ACCESS,
    EntitlementState.EXPIRED,
    EntitlementState.BLOCKED,
)

#: Kontent ochiq bo'ladigan holatlar. Kurs qulfi FAQAT shu to'plamga qarasin.
FULL_ACCESS_STATES = frozenset(
    {
        EntitlementState.PRO_ACTIVE,
        EntitlementState.TEMP_ACCESS,
        EntitlementState.TRIAL_ACTIVE,
    }
)

#: Eski klassifikator javoblarining yangi nomlari.
_LEGACY_STATE_MAP = {
    UserAccessState.PAID: EntitlementState.PRO_ACTIVE,
    UserAccessState.TEMPORARY_TRIAL: EntitlementState.TEMP_ACCESS,
    UserAccessState.EXPIRED: EntitlementState.EXPIRED,
    UserAccessState.BLOCKED: EntitlementState.BLOCKED,
    # `trial` — bu 7 kunlik Pro trial EMAS, balki eski bot statusi. U hech
    # qachon kontent ochmagan, shuning uchun FREE ga tushadi.
    UserAccessState.TRIAL: EntitlementState.FREE,
    UserAccessState.FREE: EntitlementState.FREE,
    UserAccessState.UNKNOWN: EntitlementState.FREE,
}


def _as_utc(value: datetime | None) -> datetime | None:
    if not value:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def has_active_pro_trial(user, *, now: datetime | None = None) -> bool:
    """7 kunlik Pro triali hozir faolmi.

    Ustunlar 4-bosqichda qo'shiladi (`0077_user_pro_trial`). Ungacha
    `getattr` None qaytaradi va bu funksiya doim False beradi — ya'ni bu modul
    migratsiyadan OLDIN ham xavfsiz ishlaydi.
    """
    if not user:
        return False
    if getattr(user, "pro_trial_revoked_at", None):
        return False
    ends_at = _as_utc(getattr(user, "pro_trial_ends_at", None))
    if not ends_at:
        return False
    return ends_at > (now or datetime.now(timezone.utc))


def resolve_state(user, *, now: datetime | None = None) -> str:
    """Foydalanuvchining hozirgi entitlement holati.

    Tartib ataylab shunday: BLOCKED hamma narsadan ustun; pullik obuna
    trialdan ustun (obunachi trial "sarflab" qo'ymasin); vaqtinchalik kirish
    (referral/otziv bonusi) ham trialdan oldin tekshiriladi, chunki u
    `users.status` ga tayanadi va trial unga umuman tegmaydi.
    """
    now = now or datetime.now(timezone.utc)
    legacy = UserAccessStateService.classify(user, now=now)

    if legacy == UserAccessState.BLOCKED:
        return EntitlementState.BLOCKED
    if legacy == UserAccessState.PAID:
        return EntitlementState.PRO_ACTIVE
    if legacy == UserAccessState.TEMPORARY_TRIAL:
        return EntitlementState.TEMP_ACCESS
    if has_active_pro_trial(user, now=now):
        return EntitlementState.TRIAL_ACTIVE
    return _LEGACY_STATE_MAP.get(legacy, EntitlementState.FREE)


def has_full_access(state: str) -> bool:
    """Kontent qulfi uchun yagona predikat."""
    return state in FULL_ACCESS_STATES


def is_billing_paid(state: str) -> bool:
    """To'lov UI si uchun yagona predikat — trial va bonus bu emas."""
    return state == EntitlementState.PRO_ACTIVE


def access_expires_at(user, state: str, *, now: datetime | None = None) -> datetime | None:
    """Joriy kirish qachon tugaydi (bo'lsa)."""
    if state == EntitlementState.TRIAL_ACTIVE:
        return _as_utc(getattr(user, "pro_trial_ends_at", None))
    if state in (EntitlementState.PRO_ACTIVE, EntitlementState.TEMP_ACCESS):
        return _as_utc(getattr(user, "end_date", None))
    return None

"""Bitta limit qarori — barcha klient uchun bitta shakl.

Bugun bir xil savolga uch xil javob shakli qaytadi. Eng ko'zga tashlanadigani:
Android `practice/gate` 403 da `reset_at` bor, Mini App `daily-gate` 403 da
yo'q — ya'ni telefon "ertaga soat 00:00 da ochiladi" deb ayta oladi, Mini App
esa yo'q. Bu shakl o'sha farqni yopadi.

Paywall matni bu bosqichda RENDER QILINMAYDI — faqat i18n kalitlari uzatiladi.
Sabab: CLAUDE.md har qanday yangi ko'rinadigan matnni uchala tilda talab
qiladi, matn esa 6-bosqichda qo'shiladi. Shunday qilib 1-bosqich umuman
foydalanuvchiga ko'rinadigan matn kiritmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.services.entitlements import actions as A


# --- rad etish sabablari ---------------------------------------------------
REASON_OK = ""
REASON_LIMIT_REACHED = "limit_reached"
REASON_BLOCKED = "blocked"
REASON_FORBIDDEN = "forbidden"
REASON_BUDGET_DEPLETED = "budget_depleted"
REASON_COOLDOWN = "cooldown"

#: Eski xato kodi. Klientlar allaqachon shuni tekshiradi, shuning uchun
#: javobda `error` maydoni sifatida SAQLANADI — aks holda ko'chirish paytida
#: Mini App va Android limit ekranini ko'rsatmay qo'yadi.
LEGACY_LIMIT_ERROR = "free_feature_limit_reached"

_LEGACY_ERRORS = {
    REASON_LIMIT_REACHED: LEGACY_LIMIT_ERROR,
    REASON_BLOCKED: "course_access_blocked",
    REASON_FORBIDDEN: "course_access_blocked",
    REASON_BUDGET_DEPLETED: "ai_budget_depleted",
    REASON_COOLDOWN: "ai_cooldown",
}


@dataclass(frozen=True)
class PaywallHint:
    """Paywall uchun kerak bo'ladigan hamma narsa — matnning O'ZIDAN tashqari."""

    surface: str
    title_key: str
    body_key: str
    cta_key: str
    plan_hint: str
    checkout_allowed: bool

    def as_dict(self) -> dict:
        return {
            "surface": self.surface,
            "title_key": self.title_key,
            "body_key": self.body_key,
            "cta_key": self.cta_key,
            "plan_hint": self.plan_hint,
            "checkout_allowed": self.checkout_allowed,
        }


#: Tavsiya qilinadigan tarif. Bitta CTA — bitta nishon.
RECOMMENDED_PLAN = "3_months"


def paywall_for(action: str, *, checkout_allowed: bool = True) -> PaywallHint:
    surface = A.surface_for(action)
    return PaywallHint(
        surface=surface,
        title_key=f"paywall_{surface}_title",
        body_key=f"paywall_{surface}_body",
        cta_key=f"paywall_{surface}_cta",
        plan_hint=RECOMMENDED_PLAN,
        checkout_allowed=bool(checkout_allowed),
    )


@dataclass(frozen=True)
class LimitDecision:
    allowed: bool
    action: str
    state: str
    limit: int | None
    used: int
    remaining: int | None
    window: str
    reset_at: str | None = None
    reason: str = REASON_OK
    paywall: PaywallHint | None = None
    #: Chaqiruv haqiqatan yozib qo'yildimi (idempotent takrorda False).
    recorded: bool = False
    idempotent: bool = False

    @property
    def unlimited(self) -> bool:
        return self.limit is None

    @property
    def legacy_error(self) -> str:
        return _LEGACY_ERRORS.get(self.reason, "")

    def as_dict(self, *, is_paid: bool | None = None) -> dict:
        """Klientga yuboriladigan shakl.

        `is_paid` — eski maydon: klientlar hozir shuni o'qiydi. Ko'chirish
        tugaguncha u shu yerda qoladi.
        """
        payload = {
            "ok": self.allowed,
            "allowed": self.allowed,
            "action": self.action,
            "state": self.state,
            "limit": self.limit,
            "used": self.used,
            "remaining": self.remaining,
            "window": self.window,
            "reset_at": self.reset_at,
            "unlimited": self.unlimited,
        }
        if is_paid is not None:
            payload["is_paid"] = bool(is_paid)
        if self.recorded:
            payload["recorded"] = True
        if self.idempotent:
            payload["idempotent"] = True
        if not self.allowed:
            payload["reason"] = self.reason
            error = self.legacy_error
            if error:
                payload["error"] = error
            if self.paywall is not None:
                payload["paywall"] = self.paywall.as_dict()
        return payload


def allow(
    *,
    action: str,
    state: str,
    limit: int | None,
    used: int,
    window: str,
    reset_at: datetime | str | None = None,
    recorded: bool = False,
    idempotent: bool = False,
) -> LimitDecision:
    remaining = None if limit is None else max(0, limit - used)
    return LimitDecision(
        allowed=True,
        action=action,
        state=state,
        limit=limit,
        used=used,
        remaining=remaining,
        window=window,
        reset_at=_iso(reset_at),
        reason=REASON_OK,
        paywall=None,
        recorded=recorded,
        idempotent=idempotent,
    )


def refuse(
    *,
    action: str,
    state: str,
    limit: int | None,
    used: int,
    window: str,
    reason: str,
    reset_at: datetime | str | None = None,
    checkout_allowed: bool = True,
) -> LimitDecision:
    return LimitDecision(
        allowed=False,
        action=action,
        state=state,
        limit=limit,
        used=used,
        remaining=0,
        window=window,
        reset_at=_iso(reset_at),
        reason=reason,
        paywall=paywall_for(action, checkout_allowed=checkout_allowed),
    )


def _iso(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()

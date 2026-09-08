"""Klientlarga beriladigan `entitlements` bloki — bitta shakl, to'rtta klient.

Bugun bir xil savolga har klient boshqacha javob oladi: Mini App `/api/v3/map`
da `user.is_paid` ni, desktop `bootstrap` da `access_state` ni, Android esa
`practice/gate` 403 ini o'qiydi. Uchtasi uch xil qoidaga tayanadi.

Bu blok ularning hammasiga bitta javob beradi. Ko'chirish davomida u mavjud
payloadlarga FAQAT QO'SHILADI — hech qanday eski maydon olib tashlanmaydi,
shuning uchun eski klient versiyalari ishlashda davom etadi.

`ads` bo'limi ataylab yo'q: reklama joylari 5-bosqichda quriladi va bu yerda
uydirma qiymat berish — klientga reklama o'chiq deb aytish bilan barobar.
"""

from __future__ import annotations

from datetime import datetime

from app.services.course_access_policy_service import CourseAccessPolicyService
from app.services.entitlements import actions as A
from app.services.entitlements.decision import RECOMMENDED_PLAN
from app.services.entitlements.engine import EntitlementEngine
from app.services.entitlements.limits_config import LimitConfigService
from app.services.entitlements.state import EntitlementState


CONTRACT_VERSION = 1

CLIENT_MINIAPP = "miniapp"
CLIENT_DESKTOP = "desktop"
CLIENT_ANDROID = "android"
CLIENT_BOT = "bot"
CLIENTS = (CLIENT_MINIAPP, CLIENT_DESKTOP, CLIENT_ANDROID, CLIENT_BOT)

#: To'lov qaysi klientda taklif qilinadi.
#:
#: Android `play` build ida obuna CTA si UMUMAN bo'lmasligi kerak (do'kon
#: qoidasi), va bugun buni klient o'zi compile-time bayroq bilan hal qiladi —
#: ya'ni server bu haqda hech narsa bilmaydi. Endi biladi: kanal `play` bo'lsa
#: `checkout_allowed` serverda ham `false` bo'ladi.
_CHECKOUT_BY_CLIENT = {
    CLIENT_MINIAPP: True,
    CLIENT_DESKTOP: True,
    CLIENT_BOT: True,
    CLIENT_ANDROID: False,
}

ANDROID_CHANNEL_DIRECT = "direct"
ANDROID_CHANNEL_PLAY = "play"

#: Tariflar. Uchalasi ham qoladi; `3_months` — tavsiya qilinadigan.
AVAILABLE_PLANS = ("10_days", "1_month", "3_months")


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def checkout_allowed_for(client: str, *, channel: str | None = None) -> bool:
    """Shu klientda to'lov taklif qilinadimi."""
    normalized = str(client or "").strip().lower()
    if normalized == CLIENT_ANDROID:
        # `direct` build Telegramga o'tkazishi mumkin, `play` — yo'q.
        return str(channel or ANDROID_CHANNEL_PLAY).strip().lower() == ANDROID_CHANNEL_DIRECT
    return _CHECKOUT_BY_CLIENT.get(normalized, True)


def trial_block(user, trial_settings: dict, *, state: str) -> dict:
    """7 kunlik Pro trial holati.

    Ustunlar 4-bosqichda qo'shiladi; ungacha `getattr` None qaytaradi va blok
    "trial ishlatilmagan, lekin hali boshlanmagan" deb ko'rinadi.
    """
    used = bool(getattr(user, "trial_used", False))
    active = state == EntitlementState.TRIAL_ACTIVE
    enabled = bool(trial_settings.get("enabled"))

    if not enabled:
        reason = trial_settings.get("disabled_reason") or "trial_disabled"
        eligible = False
    elif used or active:
        reason = "trial_already_used" if used else ""
        eligible = False
    elif state in (EntitlementState.PRO_ACTIVE, EntitlementState.BLOCKED):
        reason = "trial_not_applicable"
        eligible = False
    else:
        reason = ""
        eligible = True

    return {
        "eligible": eligible,
        "active": active,
        "used": used,
        "started_at": _iso(getattr(user, "pro_trial_started_at", None)),
        "ends_at": _iso(getattr(user, "pro_trial_ends_at", None)),
        "days_total": int(trial_settings.get("days") or 0),
        # UI hech qachon "cheksiz" demasin: trial byudjeti cheklangan.
        "ai_budget_capped": True,
        "disabled_reason": reason,
    }


async def build_entitlement_block(
    session,
    user,
    *,
    client: str,
    actions=None,
    channel: str | None = None,
    now: datetime | None = None,
) -> dict:
    """Bitta foydalanuvchi uchun to'liq entitlement bloki."""
    config = await LimitConfigService(session).get_config()
    engine = EntitlementEngine(session, config=config)
    checkout = checkout_allowed_for(client, channel=channel)

    snapshot = await engine.snapshot(user, now=now)
    decisions = await engine.status_map(
        user,
        actions or A.ACTIONS,
        now=now,
        checkout_allowed=checkout,
    )

    policy = await CourseAccessPolicyService(session).get_payload()

    limits = {}
    for action, decision in decisions.items():
        limits[action] = {
            "allowed": decision.allowed,
            "limit": decision.limit,
            "used": decision.used,
            "remaining": decision.remaining,
            "window": decision.window,
            "reset_at": decision.reset_at,
            "unlimited": decision.unlimited,
        }

    return {
        "entitlements": {
            "version": CONTRACT_VERSION,
            "client": str(client or "").strip().lower(),
            "state": snapshot.state,
            "is_paid": snapshot.is_paid,
            "has_full_access": snapshot.full_access,
            "expires_at": _iso(snapshot.expires_at),
            "trial": trial_block(user, config.trial, state=snapshot.state),
            "limits": limits,
            "paywall": {
                "enabled": not snapshot.full_access,
                "checkout_allowed": checkout,
                "plans": list(AVAILABLE_PLANS),
                "recommended": RECOMMENDED_PLAN,
            },
            "policy": {
                "mode": policy.get("mode"),
                "effective_mode": policy.get("effective_mode"),
                "free_until": policy.get("free_until"),
            },
        }
    }


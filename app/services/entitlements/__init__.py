"""Markaziy entitlement/limit dvigateli.

Bu paket "bu foydalanuvchi nima qila oladi va kuniga necha marta" degan
savolga javob beradigan YAGONA joy bo'lishi uchun qurilgan. Bugun bu qarorni
to'qqizta mustaqil servis aytadi va ular bir-biriga qarama-qarshi javob
berishi mumkin (Mini App darsni ochadi, desktop o'sha darsni yopadi).

Modullar:

* `state`         — foydalanuvchi holati (FREE / TRIAL_ACTIVE / PRO_ACTIVE / ...)
* `actions`       — cheklanadigan harakatlar va ularning paywall sirtlari
* `limits_config` — limitlar `bot_settings` dagi JSON sifatida
* `decision`      — bitta qaror obyekti, barcha klient uchun bitta shakl
* `engine`        — mavjud hisoblagichlarni o'raydigan dvigatel
* `contract`      — klientlarga beriladigan `entitlements` bloki

Ko'chirish shadow rejim orqali boradi: dvigatel avval eski qaror bilan yonma-yon
ishlaydi va faqat farqlar nolga tushgach yoqiladi.
"""

from app.services.entitlements.actions import ACTIONS, ACTION_SURFACE
from app.services.entitlements.state import (
    ENTITLEMENT_STATES,
    EntitlementState,
    has_full_access,
    is_billing_paid,
    resolve_state,
)

__all__ = [
    "ACTIONS",
    "ACTION_SURFACE",
    "ENTITLEMENT_STATES",
    "EntitlementState",
    "has_full_access",
    "is_billing_paid",
    "resolve_state",
]

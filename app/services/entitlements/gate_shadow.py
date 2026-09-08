"""Mashq darvozasi uchun shadow solishtiruvi — Mini App va Android uchun bitta.

Ikkala klient bir xil savolni beradi ("bu bo'limni ocha olamanmi") va bir xil
eski yo'ldan o'tadi. Solishtiruv ham bitta bo'lishi kerak, aks holda
hisobotdagi ikki qator ikki xil o'lchovni ko'rsatib qo'yardi.

Bu chaqiruv qaror qabul qilingandan KEYIN turadi va uni hech qachon
o'zgartirmaydi.
"""

from __future__ import annotations

import logging

from app.services.entitlements import actions as A
from app.services.entitlements.engine import EntitlementEngine
from app.services.entitlements.shadow import EntitlementShadowService, LegacyOutcome


logger = logging.getLogger(__name__)


#: Eski bo'lim nomidan yangi action kalitiga.
FEATURE_ACTIONS = {
    "recognition": A.PRACTICE_RECOGNITION,
    "memorize": A.PRACTICE_MEMORIZE,
    "pronunciation": A.PRACTICE_PRONUNCIATION,
    "placement": A.PRACTICE_PLACEMENT,
    "training_test": A.PRACTICE_TRAINING_TEST,
    "mistake_review": A.PRACTICE_MISTAKE_REVIEW,
    "lesson": A.LESSON_START,
}


async def shadow_compare_gate(
    session,
    *,
    user,
    feature: str,
    legacy: dict,
    client: str,
    context: dict | None = None,
) -> None:
    """Dvigatel shu so'rovda nima deyishini hisoblaydi va farqni yozadi."""
    action = FEATURE_ACTIONS.get(str(feature or "").strip().lower())
    if not action or user is None:
        return
    try:
        engine_decision = await EntitlementEngine(session).check(user, action)
        payload = {"feature": feature}
        payload.update(context or {})
        await EntitlementShadowService(session).compare(
            user=user,
            action=action,
            client=client,
            legacy=LegacyOutcome.from_dict(legacy),
            engine=engine_decision,
            context=payload,
        )
    except Exception:  # noqa: BLE001 — kuzatuv jonli so'rovni buzmasin
        logger.exception("Shadow gate comparison failed for %s/%s", client, feature)

"""Dvigatelni eski qaror bilan yonma-yon solishtirish.

Ko'chirishning butun mohiyati shu: dvigatel avval HECH NARSANI o'zgartirmasdan
ishlaydi, uning qarori eski qaror bilan solishtiriladi va farqlar yoziladi.
Faqat farqlar nolga tushgach, harakat bittalab yoqiladi — deploy bilan emas,
sozlama yozuvi bilan, ya'ni orqaga qaytarish bitta tugma.

Ikkita qat'iy qoida:

1. **Shadow hech qachon xatti-harakatni o'zgartira olmaydi.** Solishtiruv
   `try/except` ichida, eski qaror qabul qilingandan KEYIN ishlaydi. Uning
   har qanday xatosi jimgina logga tushadi.
2. **O'z sessiyasida yozadi.** So'rov sessiyasi rollback bo'lsa ham yozuv
   yo'qolmasin — aynan shu naqsh `ConversionFunnelService.record()` da
   ishlatilgan.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.db.models.entitlement_shadow_event import EntitlementShadowEvent
from app.db.session import async_session_maker
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services import course_daily_window
from app.services.entitlements import actions as A


logger = logging.getLogger(__name__)


SHADOW_ROLLOUT_KEY = "entitlement_rollout_v1"

MODE_SHADOW = "shadow"
MODE_ENGINE = "engine"
MODES = frozenset({MODE_SHADOW, MODE_ENGINE})

#: Harakatni yoqish uchun ikkala shart ham bajarilishi kerak.
#:
#: Faqat "nol nomuvofiqlik" yetarli emas: agar o'sha harakatni hech kim
#: ishlatmagan bo'lsa, nol nomuvofiqlik ham nol ma'noni bildiradi.
ROLLOUT_MIN_SAMPLES = 200
ROLLOUT_CLEAN_DAYS = 7


@dataclass(frozen=True)
class LegacyOutcome:
    """Eski yo'l nima dedi — solishtirish uchun eng kichik shakl."""

    allowed: bool
    limit: int | None = None
    used: int | None = None
    remaining: int | None = None

    @classmethod
    def from_dict(cls, payload: dict | None) -> "LegacyOutcome":
        payload = payload or {}
        return cls(
            allowed=bool(payload.get("allowed")),
            limit=_int_or_none(payload.get("limit")),
            used=_int_or_none(payload.get("used")),
            remaining=_int_or_none(payload.get("remaining")),
        )


def _int_or_none(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class EntitlementShadowService:
    def __init__(self, session=None):
        self.session = session

    # --- yoqish/o'chirish sozlamasi ---------------------------------------

    async def get_rollout(self) -> dict:
        if self.session is None:
            return {}
        raw = await BotSettingRepository(self.session).get(SHADOW_ROLLOUT_KEY)
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            logger.warning("Buzilgan entitlement rollout sozlamasi — shadow rejimda qolamiz")
            return {}
        return payload if isinstance(payload, dict) else {}

    async def mode_for(self, action: str, *, client: str | None = None) -> str:
        """Shu harakat uchun dvigatel qaror qabul qiladimi yoki faqat kuzatadimi.

        Default — `shadow`. Ya'ni sozlama yo'q bo'lsa yoki buzilgan bo'lsa,
        xatti-harakat o'zgarmaydi.
        """
        payload = await self.get_rollout()

        clients = payload.get("clients")
        if isinstance(clients, dict) and client:
            value = str(clients.get(client) or "").strip().lower()
            if value == MODE_SHADOW:
                # Klient darajasidagi "shadow" — harakat sozlamasidan ustun.
                return MODE_SHADOW

        actions = payload.get("actions")
        if isinstance(actions, dict):
            value = str(actions.get(action) or "").strip().lower()
            if value in MODES:
                return value

        default = str(payload.get("default") or MODE_SHADOW).strip().lower()
        return default if default in MODES else MODE_SHADOW

    async def save_rollout(
        self,
        payload: dict,
        *,
        updated_by_telegram_id: int | None = None,
    ) -> dict:
        if not isinstance(payload, dict):
            raise ValueError("invalid_entitlement_rollout")

        default = str(payload.get("default") or MODE_SHADOW).strip().lower()
        if default not in MODES:
            raise ValueError("invalid_entitlement_rollout")

        actions = {}
        for action, mode in (payload.get("actions") or {}).items():
            if action not in A.ACTION_SET:
                raise ValueError("invalid_entitlement_rollout")
            normalized = str(mode or "").strip().lower()
            if normalized not in MODES:
                raise ValueError("invalid_entitlement_rollout")
            actions[action] = normalized

        clients = {}
        for client, mode in (payload.get("clients") or {}).items():
            normalized = str(mode or "").strip().lower()
            if normalized not in MODES:
                raise ValueError("invalid_entitlement_rollout")
            clients[str(client).strip().lower()] = normalized

        stored = {
            "version": 1,
            "default": default,
            "actions": actions,
            "clients": clients,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "updated_by_telegram_id": _int_or_none(updated_by_telegram_id),
        }
        await BotSettingRepository(self.session).set(
            SHADOW_ROLLOUT_KEY,
            json.dumps(stored, ensure_ascii=False, separators=(",", ":")),
        )
        return stored

    # --- solishtirish -----------------------------------------------------

    async def compare(
        self,
        *,
        user,
        action: str,
        client: str,
        legacy: LegacyOutcome | dict,
        engine,
        context: dict | None = None,
    ) -> bool:
        """Ikki qarorni solishtiradi va farqni yozadi. Mos kelsa True.

        Hech qachon exception tashlamaydi: bu chaqiruv jonli so'rov ichida,
        eski qaror qabul qilingandan keyin turadi.
        """
        try:
            return await self._compare(
                user=user,
                action=action,
                client=client,
                legacy=legacy
                if isinstance(legacy, LegacyOutcome)
                else LegacyOutcome.from_dict(legacy),
                engine=engine,
                context=context,
            )
        except Exception:  # noqa: BLE001 — kuzatuv hech qachon oqimni buzmasin
            logger.exception("Entitlement shadow comparison failed: %s", action)
            return True

    async def _compare(
        self,
        *,
        user,
        action: str,
        client: str,
        legacy: LegacyOutcome,
        engine,
        context: dict | None,
    ) -> bool:
        telegram_id = _int_or_none(getattr(user, "telegram_id", None))
        if not telegram_id:
            return True

        # Solishtiruvning O'ZAGI — ruxsat berildimi yoki yo'q. Qolgan sonlar
        # tashxis uchun yoziladi, lekin farq deb hisoblanmaydi: masalan eski
        # yo'l `remaining` ni boshqacha yaxlitlashi mumkin va bu foydalanuvchi
        # uchun hech narsani o'zgartirmaydi.
        agree = bool(legacy.allowed) == bool(engine.allowed)

        offset = _int_or_none(context.get("offset_minutes") if context else None) or 0
        day_key = course_daily_window.local_day_key(offset)

        detail = dict(context or {})
        if not agree:
            detail["mismatch"] = {
                "legacy_allowed": legacy.allowed,
                "engine_allowed": engine.allowed,
                "engine_reason": getattr(engine, "reason", ""),
            }

        row = EntitlementShadowEvent(
            telegram_id=telegram_id,
            action=str(action)[:64],
            client=str(client or "")[:16],
            agree=agree,
            legacy_allowed=legacy.allowed,
            legacy_limit=legacy.limit,
            legacy_used=legacy.used,
            legacy_remaining=legacy.remaining,
            engine_allowed=bool(engine.allowed),
            engine_limit=engine.limit,
            engine_used=engine.used,
            engine_remaining=engine.remaining,
            state=str(getattr(engine, "state", ""))[:24] or None,
            detail_json=json.dumps(detail, ensure_ascii=False, default=str)
            if detail
            else None,
            day_key=day_key[:16],
            created_at=datetime.now(timezone.utc),
        )

        try:
            async with async_session_maker() as write_session:
                write_session.add(row)
                await write_session.commit()
        except Exception:
            # Unique kalit: shu kun uchun bu holat allaqachon yozilgan. Bu
            # kutilgan holat, xato emas — jadval hajmi shu bilan cheklanadi.
            logger.debug("Shadow row already recorded today: %s/%s", action, client)

        if not agree:
            logger.info(
                "entitlement_shadow_mismatch action=%s client=%s legacy=%s engine=%s state=%s",
                action,
                client,
                legacy.allowed,
                engine.allowed,
                getattr(engine, "state", ""),
            )
        return agree

    # --- hisobot ----------------------------------------------------------

    async def disagreement_report(self, *, days: int = ROLLOUT_CLEAN_DAYS) -> list[dict]:
        """Har `(action, client)` uchun namuna va nomuvofiqlik soni."""
        if self.session is None:
            return []
        since = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))

        result = await self.session.execute(
            select(
                EntitlementShadowEvent.action,
                EntitlementShadowEvent.client,
                EntitlementShadowEvent.agree,
                func.count(EntitlementShadowEvent.id),
                func.max(EntitlementShadowEvent.created_at),
            )
            .where(EntitlementShadowEvent.created_at >= since)
            .group_by(
                EntitlementShadowEvent.action,
                EntitlementShadowEvent.client,
                EntitlementShadowEvent.agree,
            )
        )

        rows: dict[tuple[str, str], dict] = {}
        for action, client, agree, count, last_at in result.all():
            entry = rows.setdefault(
                (action, client),
                {
                    "action": action,
                    "client": client,
                    "samples": 0,
                    "disagreements": 0,
                    "last_disagreement_at": None,
                },
            )
            entry["samples"] += int(count or 0)
            if not agree:
                entry["disagreements"] += int(count or 0)
                entry["last_disagreement_at"] = (
                    last_at.isoformat() if last_at else None
                )

        report = []
        for entry in rows.values():
            entry["ready_to_enable"] = bool(
                entry["disagreements"] == 0 and entry["samples"] >= ROLLOUT_MIN_SAMPLES
            )
            report.append(entry)
        report.sort(key=lambda item: (-item["disagreements"], item["action"]))
        return report

    async def examples(self, *, action: str, client: str, limit: int = 3) -> list[dict]:
        """Nomuvofiqlik misollari — adminga nima farq qilganini ko'rsatish uchun."""
        if self.session is None:
            return []
        result = await self.session.execute(
            select(EntitlementShadowEvent)
            .where(
                EntitlementShadowEvent.action == action,
                EntitlementShadowEvent.client == client,
                EntitlementShadowEvent.agree.is_(False),
            )
            .order_by(EntitlementShadowEvent.created_at.desc())
            .limit(max(1, min(int(limit), 20)))
        )
        return [
            {
                "telegram_id": row.telegram_id,
                "state": row.state,
                "legacy_allowed": row.legacy_allowed,
                "engine_allowed": row.engine_allowed,
                "legacy_used": row.legacy_used,
                "engine_used": row.engine_used,
                "legacy_limit": row.legacy_limit,
                "engine_limit": row.engine_limit,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in result.scalars().all()
        ]

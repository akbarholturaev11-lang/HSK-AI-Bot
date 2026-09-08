"""7 kunlik Pro trial — emailsiz, foydalanuvchining o'zi boshlaydi.

Email tasdiqlash ataylab YO'Q. Auditoriya Telegram orqali keladi va to'lov
qo'lda (skrinshot + admin tasdig'i) qabul qilinadi; trialdan oldin pochta
so'rash aktivatsiyani keskin tushirardi. Bepul email 10 soniyada ochiladi,
Telegram akkaunt esa SIM talab qiladi — ya'ni `telegram_id` bu yerda emaildan
kuchliroq identifikator.

**Butun modulning eng muhim qoidasi:** `start()` `users.status`,
`users.payment_status`, `users.start_date` va `users.end_date` ga
YOZMAYDI. Sabab — `AccessService._is_same_active_window` referral
mukofotining $2 lik AI byudjetini o'sha ikki sanaga ±5 soniya aniqlik bilan
bog'laydi. Bu ustunlarga har qanday yozuv jonli referral trialining
byudjetini jimgina uzib qo'yardi: foydalanuvchi hech qanday xatosiz AI
kirishini yo'qotardi.

Ikkinchi qoida shundan kelib chiqadi: `AIUsageBudgetService.create_fixed_budget`
avval `expire_active_budgets()` chaqiradi. Shuning uchun faol byudjeti bor
foydalanuvchiga trial BERILMAYDI — u byudjetni o'ldirib yuborardi.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.models.ai_usage import AIUsageBudget
from app.db.models.user import User
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.conversion_funnel_service import ConversionFunnelService
from app.services.entitlements.limits_config import LimitConfigService
from app.services.entitlements.state import EntitlementState, resolve_state


logger = logging.getLogger(__name__)


PRO_TRIAL_PLAN_TYPE = "pro_trial_7_days"

#: Rad etish sabablari — klient ularni ko'rsatadi, shuning uchun barqaror.
REASON_ALREADY_USED = "trial_already_used"
REASON_DISABLED = "trial_disabled"
REASON_NOT_APPLICABLE = "trial_not_applicable"
REASON_ACCOUNT_TOO_NEW = "trial_account_too_new"
REASON_ACTIVE_BUDGET = "trial_conflicts_with_active_access"

#: Trialga loyiq holatlar. Obunachi ham, bloklangan ham emas; vaqtinchalik
#: kirishi bor odam ham emas (uning byudjeti bor).
_ELIGIBLE_STATES = frozenset({EntitlementState.FREE, EntitlementState.EXPIRED})


def _as_utc(value: datetime | None) -> datetime | None:
    if not value:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class ProTrialService:
    def __init__(self, session):
        self.session = session

    # --- loyiqlik ---------------------------------------------------------

    async def eligibility(self, user, *, now: datetime | None = None) -> dict:
        """Bu odam trial ola oladimi va olmasa nima uchun."""
        now = now or datetime.now(timezone.utc)
        trial = (await LimitConfigService(self.session).get_config()).trial

        if not trial.get("enabled"):
            # Kill-switch: fake akkauntlar ko'paysa admin bir bosishda yopadi.
            return self._no(trial.get("disabled_reason") or REASON_DISABLED, trial)

        if user is None:
            return self._no(REASON_NOT_APPLICABLE, trial)

        if bool(getattr(user, "trial_used", False)):
            return self._no(REASON_ALREADY_USED, trial)

        state = resolve_state(user, now=now)
        if state not in _ELIGIBLE_STATES:
            return self._no(REASON_NOT_APPLICABLE, trial)

        min_age_hours = int(trial.get("min_account_age_hours") or 0)
        if min_age_hours:
            created = _as_utc(getattr(user, "created_at", None))
            if not created or created > now - timedelta(hours=min_age_hours):
                return self._no(REASON_ACCOUNT_TOO_NEW, trial)

        if await self._has_active_budget(user):
            return self._no(REASON_ACTIVE_BUDGET, trial)

        return {
            "eligible": True,
            "reason": "",
            "days": int(trial.get("days") or 7),
            "ai_budget_usd": float(trial.get("ai_budget_usd") or 0),
        }

    @staticmethod
    def _no(reason: str, trial: dict) -> dict:
        return {
            "eligible": False,
            "reason": reason,
            "days": int(trial.get("days") or 7),
            "ai_budget_usd": float(trial.get("ai_budget_usd") or 0),
        }

    async def _has_active_budget(self, user) -> bool:
        """Faol AI byudjeti bormi.

        `create_fixed_budget` avval hamma faol byudjetni `expired` qiladi, ya'ni
        trial berish referral mukofotini o'ldirib yuborardi.
        """
        result = await self.session.execute(
            select(AIUsageBudget.id).where(
                AIUsageBudget.user_telegram_id == int(user.telegram_id),
                AIUsageBudget.status == "active",
            )
        )
        return result.scalar_one_or_none() is not None

    # --- boshlash ---------------------------------------------------------

    async def start(
        self,
        user,
        *,
        source: str,
        client: str = "",
        now: datetime | None = None,
    ) -> dict:
        """Trialni boshlaydi. Qaytadi: `{ok, error?, ends_at?, days?}`."""
        now = now or datetime.now(timezone.utc)
        verdict = await self.eligibility(user, now=now)
        if not verdict["eligible"]:
            return {"ok": False, "error": verdict["reason"] or REASON_NOT_APPLICABLE}

        days = verdict["days"]
        ends_at = now + timedelta(days=days)

        # DIQQAT: `status`, `payment_status`, `start_date`, `end_date` ga
        # TEGILMAYDI. Modul docstringidagi sababni o'qing.
        user.trial_used = True
        user.pro_trial_started_at = now
        user.pro_trial_ends_at = ends_at
        user.pro_trial_source = str(source or "")[:32] or None
        user.pro_trial_revoked_at = None
        await self.session.flush()

        budget_usd = verdict["ai_budget_usd"]
        if budget_usd > 0:
            await AIUsageBudgetService(self.session).create_fixed_budget(
                telegram_id=int(user.telegram_id),
                plan_type=PRO_TRIAL_PLAN_TYPE,
                amount=int(budget_usd),
                currency="usd",
                total_budget_usd=budget_usd,
                starts_at=now,
                ends_at=ends_at,
            )

        await ConversionFunnelService().record(
            event_name="trial_started",
            user=user,
            source=source or client or "pro_trial",
            payload={"days": days, "client": client, "budget_usd": budget_usd},
        )
        logger.info(
            "pro_trial_started telegram_id=%s days=%s source=%s",
            getattr(user, "telegram_id", None),
            days,
            source,
        )
        return {"ok": True, "days": days, "ends_at": ends_at.isoformat()}

    # --- tugash -----------------------------------------------------------

    async def expire_due(self, *, limit: int = 500, now: datetime | None = None):
        """Muddati o'tgan triallarni yopadi.

        Hech qanday progress, XP yoki tarix qatoriga TEGILMAYDI: trial tugashi
        foydalanuvchini bepul darajaga tushiradi, uni devorga urmaydi.
        """
        now = now or datetime.now(timezone.utc)
        result = await self.session.execute(
            select(User)
            .where(
                User.pro_trial_ends_at.is_not(None),
                User.pro_trial_ends_at <= now,
                User.pro_trial_revoked_at.is_(None),
            )
            .limit(max(1, int(limit)))
        )
        users = list(result.scalars().all())
        for user in users:
            # `revoked_at` — "bu trial yopilgan" belgisi. `ends_at` o'chirilmaydi,
            # chunki u tarix: qachon va qancha muddat berilgani ko'rinib tursin.
            user.pro_trial_revoked_at = now
            await ConversionFunnelService().record(
                event_name="trial_expired", user=user, source="pro_trial_expiry"
            )
        if users:
            await self.session.flush()
        return len(users), [int(user.telegram_id) for user in users]

    async def revoke(self, user, *, admin_telegram_id: int, reason: str = "") -> bool:
        """Adminning qo'lda yopishi (masalan suiiste'mol aniqlansa)."""
        if not user or not getattr(user, "pro_trial_ends_at", None):
            return False
        if getattr(user, "pro_trial_revoked_at", None):
            return False
        user.pro_trial_revoked_at = datetime.now(timezone.utc)
        await self.session.flush()
        logger.info(
            "pro_trial_revoked telegram_id=%s admin_id=%s reason=%s",
            getattr(user, "telegram_id", None),
            admin_telegram_id,
            reason[:200],
        )
        return True

"""Markaziy limit dvigateli.

Bu dvigatel YANGI hisoblagich yaratmaydi. U bugungi jadvallarni o'qiydi va
yozadi — `course_miniapp_events`, `course_feature_usages`, `messages`,
`users.questions_used` — faqat chegarani boshqa joydan, `LimitConfig` dan
oladi.

Ikkita qat'iy qoida bor:

1. **Dvigatel hech qachon eski yo'ldan KO'PROQ bermaydi.** Bir harakat uchun
   bir nechta eski hisoblagich bo'lsa (masalan `training_test` ham
   `course_feature_usages` da, ham `course_miniapp_events` da sanaladi),
   dvigatel ularning MAKSIMUMINI oladi. Shunda ko'chirish paytida hech kimga
   kutilmagan qo'shimcha slot ochilib qolmaydi.

2. **Yozish o'sha eski jadvalga boradi.** Shuning uchun dvigatel yoqilgandan
   keyin ham, o'chirilgandan keyin ham hisob bir xil joyda qoladi va orqaga
   qaytarish xavfsiz bo'ladi.

Bir istisno bor va uni ochiq aytish kerak: `lesson.start` uchun bugun kunlik
tezlik chegarasi UMUMAN yo'q (darslar pozitsion devor bilan yopiladi). Ya'ni
bu action uchun dvigatel yangi qoida kiritadi va shadow rejimda u ataylab
farq ko'rsatadi. Uni "farqlar nolga tushdi" mezoni bilan emas, alohida qaror
bilan yoqish kerak.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.repositories.message_repo import MessageRepository
from app.services import course_daily_window
from app.services.course_miniapp_access_service import (
    COURSE_FEATURE_KEYS,
    CourseMiniAppAccessService,
)
from app.services.entitlements import actions as A
from app.services.entitlements import decision as D
from app.services.entitlements.limits_config import (
    WINDOW_LIFETIME,
    ActionLimit,
    LimitConfig,
    LimitConfigService,
)
from app.services.entitlements.state import (
    EntitlementState,
    access_expires_at,
    has_full_access,
    is_billing_paid,
    resolve_state,
)


@dataclass(frozen=True)
class AccessSnapshot:
    """Foydalanuvchining kirish holati — bir marta hisoblanadi, ko'p marta ishlatiladi."""

    state: str
    is_paid: bool
    full_access: bool
    expires_at: datetime | None
    offset_minutes: int

    @property
    def reset_at(self) -> datetime:
        return course_daily_window.next_day_reset(self.offset_minutes)


class EntitlementEngine:
    def __init__(self, session, *, config: LimitConfig | None = None):
        self.session = session
        self._config = config
        self._access = CourseMiniAppAccessService(session)
        self._messages = MessageRepository(session)
        self._entitlement_cache: dict[int, dict] = {}

    # --- konfiguratsiya ---------------------------------------------------

    async def config(self) -> LimitConfig:
        if self._config is None:
            self._config = await LimitConfigService(self.session).get_config()
        return self._config

    # --- holat ------------------------------------------------------------

    async def snapshot(self, user, *, now: datetime | None = None) -> AccessSnapshot:
        state = resolve_state(user, now=now)
        offset = 0
        if user is not None:
            offset = await self._access._learner_offset_minutes(user)
        return AccessSnapshot(
            state=state,
            is_paid=is_billing_paid(state),
            full_access=has_full_access(state),
            expires_at=access_expires_at(user, state, now=now),
            offset_minutes=offset,
        )

    # --- hisoblagichlarni o'qish ------------------------------------------

    async def _lifetime_feature_used(self, user, legacy_key: str) -> int:
        """`course_feature_usages` dagi umrbod hisob (eski hisob bilan birga)."""
        if legacy_key not in COURSE_FEATURE_KEYS:
            return 0
        user_id = int(getattr(user, "id", 0) or 0)
        if user_id not in self._entitlement_cache:
            self._entitlement_cache[user_id] = await self._access.get_entitlements(user)
        entry = self._entitlement_cache[user_id].get(legacy_key) or {}
        return int(entry.get("used") or 0)

    async def _event_used(self, user, legacy_key: str, *, lifetime: bool) -> int:
        """`course_miniapp_events` dagi hisob."""
        status = await self._access.daily_status(
            user, legacy_key, lifetime=lifetime, limit_override=0
        )
        return int(status.get("used") or 0)

    async def _ai_used(self, user, action: str) -> int:
        """Bot AI hisoblagichlari — `users` va `messages` da."""
        if action == A.AI_TEXT:
            return int(getattr(user, "questions_used", 0) or 0)
        if action == A.AI_PHOTO:
            return await self._messages.count_user_messages_today(
                user_id=user.id, content_type="image"
            )
        if action == A.AI_VOICE:
            qa = await self._messages.count_user_messages_today(
                user_id=user.id, content_type="voice"
            )
            translator = await self._messages.count_user_messages_today(
                user_id=user.id, content_type="voice_translator"
            )
            return qa + translator
        return 0

    async def used_for(self, user, action: str, rule: ActionLimit) -> int:
        """Shu harakat bugun necha marta ishlatilgan.

        Bir nechta eski hisoblagich bo'lsa maksimumi olinadi — dvigatel eski
        yo'ldan ko'proq bermasligi kerak.
        """
        action = A.normalize(action)
        if action in (A.AI_TEXT, A.AI_PHOTO, A.AI_VOICE):
            return await self._ai_used(user, action)

        legacy_key = A.LEGACY_FEATURE_KEYS.get(action, action)
        lifetime = rule.window == WINDOW_LIFETIME

        counts = [await self._event_used(user, legacy_key, lifetime=lifetime)]
        if legacy_key in COURSE_FEATURE_KEYS:
            counts.append(await self._lifetime_feature_used(user, legacy_key))
        return max(counts)

    # --- qarorlar ---------------------------------------------------------

    def _decide(
        self,
        *,
        action: str,
        snapshot: AccessSnapshot,
        rule: ActionLimit,
        used: int,
        checkout_allowed: bool,
        recorded: bool = False,
        idempotent: bool = False,
    ) -> D.LimitDecision:
        if snapshot.state == EntitlementState.BLOCKED:
            return D.refuse(
                action=action,
                state=snapshot.state,
                limit=rule.limit,
                used=used,
                window=rule.window,
                reason=D.REASON_BLOCKED,
                checkout_allowed=False,
            )
        if rule.unlimited:
            return D.allow(
                action=action,
                state=snapshot.state,
                limit=None,
                used=used,
                window=rule.window,
                recorded=recorded,
                idempotent=idempotent,
            )
        if rule.limit == 0:
            return D.refuse(
                action=action,
                state=snapshot.state,
                limit=0,
                used=used,
                window=rule.window,
                reason=D.REASON_FORBIDDEN,
                checkout_allowed=checkout_allowed,
            )

        reset_at = None if rule.window == WINDOW_LIFETIME else snapshot.reset_at
        if used >= rule.limit:
            return D.refuse(
                action=action,
                state=snapshot.state,
                limit=rule.limit,
                used=used,
                window=rule.window,
                reason=D.REASON_LIMIT_REACHED,
                reset_at=reset_at,
                checkout_allowed=checkout_allowed,
            )
        return D.allow(
            action=action,
            state=snapshot.state,
            limit=rule.limit,
            used=used,
            window=rule.window,
            reset_at=reset_at,
            recorded=recorded,
            idempotent=idempotent,
        )

    async def check(
        self,
        user,
        action: str,
        *,
        now: datetime | None = None,
        checkout_allowed: bool = True,
        snapshot: AccessSnapshot | None = None,
    ) -> D.LimitDecision:
        """Hech narsa yozmasdan qaror. Paywallni oldindan ko'rsatish uchun."""
        action = A.normalize(action)
        snap = snapshot or await self.snapshot(user, now=now)
        rule = (await self.config()).limit_for(snap.state, action)
        used = 0 if rule.unlimited else await self.used_for(user, action, rule)
        return self._decide(
            action=action,
            snapshot=snap,
            rule=rule,
            used=used,
            checkout_allowed=checkout_allowed,
        )

    async def consume(
        self,
        user,
        action: str,
        *,
        ref: str | None = None,
        notify_bot=None,
        now: datetime | None = None,
        checkout_allowed: bool = True,
    ) -> D.LimitDecision:
        """Bitta slotni band qiladi. Limit tugagan bo'lsa yozmaydi."""
        action = A.normalize(action)
        snap = await self.snapshot(user, now=now)
        rule = (await self.config()).limit_for(snap.state, action)

        if snap.state == EntitlementState.BLOCKED or rule.limit == 0:
            return self._decide(
                action=action,
                snapshot=snap,
                rule=rule,
                used=0,
                checkout_allowed=checkout_allowed,
            )
        if rule.unlimited:
            return self._decide(
                action=action,
                snapshot=snap,
                rule=rule,
                used=0,
                checkout_allowed=checkout_allowed,
            )

        # Eski hisoblagich dvigatelnikidan oldinda bo'lsa, yozishdan OLDIN rad
        # etamiz: aks holda dvigatel eski yo'ldan ko'proq berib yuboradi.
        used = await self.used_for(user, action, rule)
        if used >= rule.limit:
            return self._decide(
                action=action,
                snapshot=snap,
                rule=rule,
                used=used,
                checkout_allowed=checkout_allowed,
            )

        legacy_key = A.LEGACY_FEATURE_KEYS.get(action, action)
        result = await self._access.consume_daily_use(
            user,
            feature_key=legacy_key,
            ref=ref,
            lifetime=rule.window == WINDOW_LIFETIME,
            notify_bot=notify_bot,
            limit_override=rule.limit,
        )
        if not result.get("allowed"):
            return self._decide(
                action=action,
                snapshot=snap,
                rule=rule,
                used=rule.limit,
                checkout_allowed=checkout_allowed,
            )

        # Slot BAND QILINDI. Bu yerda `_decide` ni qayta chaqirib bo'lmaydi:
        # oxirgi ruxsat etilgan chaqiruvdan keyin `used == limit` bo'ladi va
        # `_decide` o'sha muvaffaqiyatli chaqiruvning o'zini rad etib qo'yardi.
        idempotent = bool(result.get("idempotent"))
        return D.allow(
            action=action,
            state=snap.state,
            limit=rule.limit,
            used=used if idempotent else used + 1,
            window=rule.window,
            reset_at=None if rule.window == WINDOW_LIFETIME else snap.reset_at,
            recorded=bool(result.get("recorded")),
            idempotent=idempotent,
        )

    async def status_map(
        self,
        user,
        actions=None,
        *,
        now: datetime | None = None,
        checkout_allowed: bool = True,
    ) -> dict[str, D.LimitDecision]:
        """Bir nechta harakat uchun qaror — bitta snapshot bilan."""
        snap = await self.snapshot(user, now=now)
        result: dict[str, D.LimitDecision] = {}
        for action in actions or A.ACTIONS:
            result[action] = await self.check(
                user,
                action,
                snapshot=snap,
                checkout_allowed=checkout_allowed,
            )
        return result

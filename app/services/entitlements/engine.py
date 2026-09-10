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

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from app.db.models.message import Message
from app.db.models.course_feature_usage import CourseFeatureUsage
from app.db.models.voice_practice_session import VoicePracticeSession

from app.repositories.message_repo import MessageRepository
from app.services.conversion_funnel_service import ConversionFunnelService
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


logger = logging.getLogger(__name__)
LIMIT_HIT_ANALYTICS_TIMEOUT_SECONDS = 0.35


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

    #: Eski trial bayroqlari. Ular `course_feature_usages` dan OLDINGI davrdan
    #: qolgan: o'sha paytdagi "bir marta bepul" shu ustunlarga yozilardi. Umrbod
    #: oynada ular hamon sarflangan hisoblanadi, aks holda eski foydalanuvchi
    #: bugun yana bitta bepul urinish olib qolardi.
    _LEGACY_TRIAL_FLAGS = {"lesson": "trial_course_completed_at", "voice": "trial_voice_used_at"}

    async def _lifetime_feature_used(self, user, legacy_key: str) -> int:
        result = await self.session.execute(select(func.count(CourseFeatureUsage.id)).where(
            CourseFeatureUsage.user_id == user.id,
            CourseFeatureUsage.feature_key == legacy_key,
        ))
        flag = self._LEGACY_TRIAL_FLAGS.get(legacy_key)
        legacy = bool(flag and getattr(user, flag, None))
        return max(int(result.scalar() or 0), int(legacy))

    async def used_for(self, user, action: str, rule: ActionLimit) -> int:
        """Read the same account-wide counter on every client and in its configured window."""
        action = A.normalize(action)
        lifetime = rule.window == WINDOW_LIFETIME
        offset = await self._access._learner_offset_minutes(user)
        since = None if lifetime else course_daily_window.day_start(offset)
        if action in (A.AI_TEXT, A.AI_PHOTO, A.AI_VOICE):
            types = {A.AI_TEXT: ("text",), A.AI_PHOTO: ("image",),
                     A.AI_VOICE: ("voice", "voice_translator")}[action]
            query = select(func.count(Message.id)).where(
                Message.user_id == user.id, Message.role == "user",
                Message.content_type.in_(types),
            )
            if since is not None:
                query = query.where(Message.created_at >= since)
            return int((await self.session.execute(query)).scalar() or 0)
        if action == A.SPEAKING_SESSION:
            query = select(func.count(VoicePracticeSession.id)).where(
                VoicePracticeSession.user_telegram_id == user.telegram_id,
                VoicePracticeSession.turn_count > 0,
            )
            if since is not None:
                query = query.where(VoicePracticeSession.started_at >= since)
            used = int((await self.session.execute(query)).scalar() or 0)
            if lifetime:
                used = max(used, await self._lifetime_feature_used(user, "voice"))
            return used
        legacy_key = A.LEGACY_FEATURE_KEYS.get(action, action)
        used = await self._access._daily_used_today(
            user.telegram_id, legacy_key, lifetime=lifetime, offset_minutes=offset
        )
        # Lifetime history must never poison a DAILY rule after a reset.
        if lifetime and legacy_key in COURSE_FEATURE_KEYS:
            used = max(used, await self._lifetime_feature_used(user, legacy_key))
        return used

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

        used = await self.used_for(user, action, rule)
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
            await self._record_limit_hit(user, action)
            return self._decide(
                action=action,
                snapshot=snap,
                rule=rule,
                used=max(used, rule.limit),
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

    async def _record_limit_hit(self, user, action: str) -> None:
        """Limitga urilish — voronkaning eng muhim nuqtasi.

        Kuniga har action uchun BIR MARTA yoziladi: bir foydalanuvchi limitga
        o'n marta urilishi mumkin va o'n qator "limitga urilganlar soni" ni
        buzib ko'rsatardi.

        Chaqiruv qaror qabul qilingandan KEYIN va `try/except` ichida —
        analitika limitni hech qachon buzmasin.
        """
        try:
            telegram_id = int(getattr(user, "telegram_id", 0) or 0)
            if not telegram_id:
                return
            user_id = getattr(user, "id", None)
            # Bu faqat analytics dedupe kaliti. User limit oynasini ko'rsatish
            # uchun profil timezone SELECT qilmaymiz; aks holda limit javobi
            # yana qo'shimcha DB ishiga bog'lanadi.
            day_key = course_daily_window.local_day_key(0)
            source = f"{action}:{day_key}"
            await asyncio.wait_for(
                ConversionFunnelService().record_once(
                    event_name="limit_hit",
                    user_id=user_id,
                    telegram_id=telegram_id,
                    source=source,
                    payload={"action": action},
                ),
                timeout=LIMIT_HIT_ANALYTICS_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning("limit_hit analytics timed out for %s", action)
        except Exception:  # noqa: BLE001 — analitika limitni buzmasin
            logger.debug("limit_hit yozilmadi: %s", action, exc_info=True)

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

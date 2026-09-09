import hashlib
import json
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.models.course_feature_usage import COURSE_FEATURE_KEYS, CourseFeatureUsage
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.user import User
from app.services import course_daily_window
from app.services.limit_notification_service import LimitNotificationService
from app.services.user_access_state_service import UserAccessStateService


logger = logging.getLogger(__name__)

FREE_FEATURE_LIMITS = {feature_key: 1 for feature_key in COURSE_FEATURE_KEYS}
# Legacy/default value kept for native clients and older imports that do not pass
# a level. Course v3 access decisions must use ``free_course_parts_for_level``.
FREE_COURSE_LESSONS_PER_LEVEL = 2

# Bepul chegara HSK DARSLIGI DARSI chegarasiga tushishi kerak: user yarim
# darsda emas, to'liq bir darsni tugatgach limitga urilsin. Har darslik darsi
# bir nechta mini-qismga bo'lingan (`parts_manifest.json`), shuning uchun
# chegara qism SONI emas — birinchi darsning oxirgi qismi (checkpoint).
#
# hsk1/hsk2 shu qoidaga o'tkazildi. hsk3/hsk4 ataylab eski 2 qismlik
# ko'rinishda qoladi: u yerda birinchi dars 6-9 qismdan iborat va to'liq
# ochish bepul kontentni bir necha barobar oshirib yuborardi.
FREE_COURSE_PARTS_BY_LEVEL = {
    "beginner": None,  # None = manifestdan (1-darsning barcha qismlari)
    "hsk1": None,
    "hsk2": None,
    "hsk3": 2,
    "hsk4": 2,
    "hsk4a": 2,
    "hsk4b": 2,
}
_MANIFEST_PATH = "app/static/course_v3_data/parts_manifest.json"
_FIRST_LESSON_PARTS_CACHE: dict[str, int] = {}


def _first_lesson_part_count(level: str) -> int | None:
    """Darajaning BIRINCHI darslik darsi nechta qismdan iboratligi.

    Manifest o'qib bo'lmasa None qaytaradi — chaqiruvchi eski qiymatga
    qaytadi, ya'ni xato holatda bepul kontent KENGAYMAYDI.
    """
    manifest_level = "hsk1" if level == "beginner" else level
    if manifest_level in _FIRST_LESSON_PARTS_CACHE:
        return _FIRST_LESSON_PARTS_CACHE[manifest_level]
    try:
        with open(_MANIFEST_PATH, encoding="utf-8") as handle:
            manifest = json.load(handle)
        lessons = manifest[manifest_level]["lessons"]
        parts = lessons[0]["parts"]
        count = int(max(int(part) for part in parts))
    except (OSError, KeyError, IndexError, TypeError, ValueError):
        return None
    if count <= 0:
        return None
    _FIRST_LESSON_PARTS_CACHE[manifest_level] = count
    return count


def free_course_parts_for_level(level: str | None) -> int:
    """Return the free Course v3 mini-parts for one learner level.

    hsk1/hsk2 (va `beginner`) uchun chegara birinchi HSK darslik darsining
    oxirgi qismi — user to'liq bitta darsni tugatgach limitga tushadi.
    hsk3/hsk4 va noma'lum darajalar eski ikki qismlik ko'rinishda qoladi.
    """
    normalized = str(level or "").strip().lower()
    if normalized not in FREE_COURSE_PARTS_BY_LEVEL:
        return FREE_COURSE_LESSONS_PER_LEVEL
    configured = FREE_COURSE_PARTS_BY_LEVEL[normalized]
    if configured is not None:
        return int(configured)
    return _first_lesson_part_count(normalized) or FREE_COURSE_LESSONS_PER_LEVEL

# Course Mini App "Mashq" bo'limlari — YANGI model:
#   • Har bo'lim UMRDA 1 marta bepul (reklamasiz). Kunlik yangilanish YO'Q
#     (`lifetime=True` bilan hisoblanadi). Bepulni ishlatgach — reklama yoki obuna.
#   • Reklama bilan ochish odatda CHEKSIZ. Faqat AI token sarflaydigan bo'limlarda
#     (`COURSE_AI_PRACTICE_FEATURES`) reklama ham KUNIGA 2 marta cheklanadi
#     (token xarajatini tiyish uchun) — "<feature>_ad" kaliti.
# Hisob server tomonda — user localStorage'ni tozalab aylanib o'tolmaydi.
COURSE_DAILY_FREE_LIMITS = {
    # Bepul: har bo'lim umrda 1 marta (lifetime=True bilan ishlatiladi).
    "recognition": 1,    # Ieroglif tanish
    "memorize": 1,       # Yodlash (ieroglif yozish mashqi)
    "pronunciation": 1,  # Talaffuz mashqi
    "placement": 1,      # Daraja aniqlash testi
    "training_test": 1,  # Test markazi mashqlari
    # Reklama bilan ochish — faqat AI token sarflaydigan bo'limda kuniga 2 marta.
    # Boshqa bo'limlarda reklama cheksiz (bu yerda "<feature>_ad" kaliti yo'q).
    "pronunciation_ad": 2,  # Talaffuz — AI (OpenAI STT), reklama ham 2 marta/kun
}

# AI token sarflaydigan mashq bo'limlari. Faqat bularda reklama ham kunlik
# cheklanadi; qolganlarida reklama cheksiz.
COURSE_AI_PRACTICE_FEATURES = ("pronunciation",)

# Bepul mashq bo'limlari (reklama-ruxsati kalitlaridan ajratilgan holda).
COURSE_DAILY_BASE_FEATURES = (
    "recognition",
    "memorize",
    "pronunciation",
    "placement",
    "training_test",
)
COURSE_DAILY_EVENT_NAME = "practice_daily_used"

# Reklama bilan ochiladigan sessiya klient yuborgan ``ad_supported=true`` yoki
# ``watched_seconds`` ga ishonmaydi. Server urinish boshlanish vaqtini va aniq
# user/ad/feature/access_ref/placement bindingini yozib, so'ng ruxsat beradi.
COURSE_AD_AUTH_EVENT_NAME = "course_ad_viewed"
COURSE_AD_AUTH_EVENT_SOURCE = "course_v3_ad_auth"
COURSE_AD_AUTH_TTL_SECONDS = 15 * 60
COURSE_AD_ATTEMPT_EVENT_NAME = "course_ad_attempt_started"
COURSE_AD_ATTEMPT_EVENT_SOURCE = "course_v3_ad_attempt"
COURSE_AD_ATTEMPT_TTL_SECONDS = 15 * 60
COURSE_AD_AUTH_FEATURES = frozenset((*COURSE_DAILY_BASE_FEATURES, "mistake_review", "lesson"))
COURSE_ACCESS_REF_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{8,48}$")
COURSE_AD_ATTEMPT_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{24,64}$")
COURSE_AD_PLACEMENTS = frozenset(("start", "middle", "end"))
COURSE_AD_LEVELS = frozenset(("hsk1", "hsk2", "hsk3", "hsk4"))
COURSE_AD_MIN_SECONDS = 5
COURSE_AD_MAX_SECONDS = 120


class CourseMiniAppAccessService:
    """Server-side Course Mini App entitlements without changing payment rules."""

    def __init__(self, session):
        self.session = session
        # Bitta so'rov ichida bir xil o'quvchining mintaqasi bir necha marta
        # kerak bo'ladi (status + consume), lekin u o'zgarmaydi.
        self._offset_cache: dict[int, int] = {}

    @staticmethod
    def _as_utc(value):
        if not value:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def is_paid_user(cls, user) -> bool:
        return UserAccessStateService.is_paid(user)

    @classmethod
    def has_unlimited_course_access(cls, user) -> bool:
        """Kurs darslari uchun limitsizlik: obunachi YOKI vaqtinchalik bonus.

        Otziv uchun beriladigan 30 daqiqa `status="active"` qo'yadi, lekin
        `payment_status` ni o'zgartirmaydi — `is_paid_user()` unga `False`
        qaytaradi. Dars gate'i shu sababli bonusni ko'rmasdi.
        """
        return UserAccessStateService.has_unlimited_course_access(user)

    @classmethod
    def is_free_user(cls, user) -> bool:
        return bool(
            user
            and not cls.is_paid_user(user)
            and UserAccessStateService.classify(user) in UserAccessStateService.COURSE_ELIGIBLE_STATES
        )

    @classmethod
    def lesson_requires_premium(cls, level: str | None, lesson_order: int | None = None) -> bool:
        try:
            order = int(lesson_order or 0)
        except (TypeError, ValueError):
            order = 0
        return order > free_course_parts_for_level(level)

    @staticmethod
    def _normalize_feature_key(feature_key: str) -> str:
        normalized = str(feature_key or "").strip().lower()
        if normalized not in COURSE_FEATURE_KEYS:
            raise ValueError(f"Unknown Course Mini App feature: {normalized or '<empty>'}")
        return normalized

    async def get_entitlements(self, user) -> dict[str, dict]:
        result = {}
        for feature in COURSE_FEATURE_KEYS:
            entry = await self.configured_decision(user, feature)
            result[feature] = {**entry, "free_limit": entry.get("limit"),
                               "remaining_free": entry.get("remaining")}
        return result

    async def consume_free_use(self, user, *, feature_key: str, usage_ref: str) -> dict:
        if not str(usage_ref or "").strip():
            raise ValueError("usage_ref is required")
        return await self.configured_decision(user, feature_key, consume=True, ref=usage_ref)

    # ----- Kunlik limitlar (Mashq bo'limlari + reklama darslari) ---------------

    @staticmethod
    def daily_reset_hour_local() -> int:
        """Kunlik limit MAHALLIY vaqt bilan qaysi soatda yangilanadi."""

        return course_daily_window.reset_hour_local()

    async def _learner_offset_minutes(self, user) -> int:
        """O'quvchining vaqt mintaqasi (daqiqada), Mini App profilidan.

        Profil bo'lmasa 0 qaytadi — ya'ni eski UTC oynasi. Mintaqa noma'lum
        bo'lgani uchun hech kimning limiti kutilmaganda siljimaydi.
        """
        user_id = getattr(user, "id", None)
        if user_id is None:
            return 0
        user_id = int(user_id)
        cached = self._offset_cache.get(user_id)
        if cached is not None:
            return cached
        result = await self.session.execute(
            select(CourseMiniAppProfile.timezone_offset_minutes).where(
                CourseMiniAppProfile.user_id == user_id
            )
        )
        offset = course_daily_window.normalize_offset_minutes(result.scalar_one_or_none() or 0)
        self._offset_cache[user_id] = offset
        return offset

    @classmethod
    def _day_start(cls, now: datetime | None = None, *, offset_minutes: int = 0) -> datetime:
        """Joriy 'limit kuni'ning boshlanishi, UTC da.

        Mintaqa 0 va reset soati 0 bo'lganda bu aynan UTC yarim tun — sozlama
        va mintaqa qo'shilishi bilan mintaqasi noma'lum o'quvchi uchun hech
        narsa o'zgarmaydi.
        """
        return course_daily_window.day_start(offset_minutes, now)

    @classmethod
    def next_daily_reset(cls, now: datetime | None = None, *, offset_minutes: int = 0) -> datetime:
        """Kunlik limit keyingi marta qachon ochilishi (UTC).

        Klient buni o'z vaqt mintaqasida ko'rsatadi; server hech qachon
        formatlangan soat qaytarmaydi.
        """
        return course_daily_window.next_day_reset(offset_minutes, now)

    @classmethod
    def _normalize_daily_feature(
        cls,
        feature_key: str,
        *,
        allow_unknown: bool = False,
    ) -> str:
        """Kunlik hisob kalitini tekshiradi.

        ``allow_unknown`` faqat chaqiruvchi limitni O'ZI bergan holatda
        ishlatiladi (`limit_override`). Shunda kalit `COURSE_DAILY_FREE_LIMITS`
        da bo'lmasa ham qabul qilinadi — chunki limit bu dictdan olinmaydi.
        Bu markaziy entitlement dvigateli uchun kerak: u o'z limitini
        sozlamadan oladi, lekin hisobni SHU jadvalda yuritishi shart.
        """
        normalized = str(feature_key or "").strip().lower()
        if normalized in COURSE_DAILY_FREE_LIMITS:
            return normalized
        if allow_unknown and normalized:
            return normalized
        raise ValueError(f"Unknown Course daily feature: {normalized or '<empty>'}")

    @staticmethod
    def normalize_access_ref(access_ref: str) -> str:
        """Validate a client-generated opaque retry key.

        The value is deliberately restricted before it is stored in indexed
        event columns. It is an idempotency key, not an authentication token.
        """

        normalized = str(access_ref or "").strip()
        if not COURSE_ACCESS_REF_PATTERN.fullmatch(normalized):
            raise ValueError("invalid_access_ref")
        return normalized

    @staticmethod
    def _normalize_ad_auth_feature(feature_key: str) -> str:
        normalized = str(feature_key or "").strip().lower()
        if normalized not in COURSE_AD_AUTH_FEATURES:
            raise ValueError(f"Unknown Course ad authorization feature: {normalized or '<empty>'}")
        return normalized

    @classmethod
    def _ad_authorization_session_id(cls, feature_key: str, access_ref: str) -> str:
        feature = cls._normalize_ad_auth_feature(feature_key)
        ref = cls.normalize_access_ref(access_ref)
        return f"{feature}:{ref}"

    @staticmethod
    def _normalize_ad_id(ad_id: int) -> int:
        try:
            normalized = int(ad_id)
        except (TypeError, ValueError):
            normalized = 0
        if normalized <= 0:
            raise ValueError("invalid_ad_id")
        return normalized

    @staticmethod
    def _normalize_ad_placement(placement: str) -> str:
        normalized = str(placement or "").strip().lower()
        if normalized not in COURSE_AD_PLACEMENTS:
            raise ValueError("invalid_ad_placement")
        return normalized

    @staticmethod
    def _normalize_ad_duration(required_seconds: int) -> int:
        try:
            normalized = int(required_seconds)
        except (TypeError, ValueError):
            normalized = COURSE_AD_MIN_SECONDS
        return max(COURSE_AD_MIN_SECONDS, min(COURSE_AD_MAX_SECONDS, normalized))

    @staticmethod
    def _normalize_ad_attempt_token(attempt_token: str) -> str:
        normalized = str(attempt_token or "").strip()
        if not COURSE_AD_ATTEMPT_TOKEN_PATTERN.fullmatch(normalized):
            raise ValueError("invalid_ad_attempt_token")
        return normalized

    @staticmethod
    def _normalize_ad_level(level: str | None) -> str | None:
        normalized = str(level or "").strip().lower()
        if not normalized:
            return None
        if normalized not in COURSE_AD_LEVELS:
            raise ValueError("invalid_ad_level")
        return normalized

    @staticmethod
    def _normalize_ad_lesson_order(lesson_order: int | None) -> int:
        try:
            normalized = int(lesson_order or 0)
        except (TypeError, ValueError):
            normalized = 0
        if normalized < 0 or normalized > 500:
            raise ValueError("invalid_ad_lesson_order")
        return normalized

    @classmethod
    def _ad_attempt_session_id(cls, attempt_token: str) -> str:
        token = cls._normalize_ad_attempt_token(attempt_token)
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return f"ad-attempt:{digest}"

    # `start_ad_attempt`, `validate_ad_attempt` va `record_ad_authorization`
    # OLIB TASHLANDI.
    #
    # Ular reklama ko'rib kirish ochish uchun qurilgan edi: klient `access_ref`
    # o'ylab topardi, server unga bir martalik `attempt_token` berardi, urinish
    # boshlanish vaqtini yozardi va ko'rilgan soniyalarni O'ZI o'lchardi —
    # soxta `watched_seconds` ni tutish uchun. Ustiga har bir maydon
    # (user/ad/feature/access_ref/placement/level/lesson_order) bittalab
    # solishtirilardi.
    #
    # Reklama endi hech narsani ochmaydi — limit tugasa paywall chiqadi —
    # shuning uchun butun tarmoq keraksiz. `verify_ad_authorization` esa
    # ataylab qoldirilgan va qattiq "yo'q" qaytaradi: uning chaqiruv joylari
    # bosqichma-bosqich olib tashlanadi va oradagi vaqtda soxta so'rov hech
    # narsa ocholmasin.


    async def verify_ad_authorization(
        self,
        user,
        *,
        feature_key: str,
        access_ref: str,
        max_age_seconds: int | None = None,
        level: str | None = None,
        lesson_order: int | None = None,
    ) -> dict:
        """Reklama ko'rib kirish ochish OLIB TASHLANDI — doim rad etadi.

        Ilgari bu yerda butun bir token/binding tarmog'i bor edi: klient
        `access_ref` o'ylab topardi, server unga `attempt_token` berardi va
        ko'rilgan soniyalarni O'ZI o'lchardi (soxta `watched_seconds` ni tutish
        uchun). Endi reklama hech narsani ochmaydi — limit tugasa paywall
        chiqadi — shuning uchun butun tarmoq keraksiz.

        Metod ATAYLAB qoldirildi va qattiq "yo'q" qaytaradi: chaqiruv joylari
        bosqichma-bosqich olib tashlanadi va oradagi vaqtda soxta so'rov
        hech narsa ocholmasin.
        """
        return {
            "allowed": False,
            "is_paid": self.is_paid_user(user),
            "error": "ad_unlock_removed",
        }


    async def _daily_used_today(
        self,
        telegram_id: int,
        feature_key: str,
        *,
        lifetime: bool = False,
        offset_minutes: int = 0,
    ) -> int:
        conditions = [
            CourseMiniAppEvent.telegram_id == int(telegram_id),
            CourseMiniAppEvent.event_name == COURSE_DAILY_EVENT_NAME,
            CourseMiniAppEvent.session_id == feature_key,
        ]
        # lifetime=True — kunlik filtr yo'q: umrbod hisob (bir marta bepul uchun).
        if not lifetime:
            conditions.append(
                CourseMiniAppEvent.created_at
                >= self._day_start(offset_minutes=offset_minutes)
            )
        result = await self.session.execute(
            select(func.count(CourseMiniAppEvent.id)).where(*conditions)
        )
        return int(result.scalar_one() or 0)

    @staticmethod
    def action_for_feature(feature_key: str) -> str:
        from app.services.entitlements import actions as A
        mapping = {value: key for key, value in A.LEGACY_FEATURE_KEYS.items()}
        mapping.update({"voice": A.SPEAKING_SESSION, "training_test": A.PRACTICE_TRAINING_TEST})
        if feature_key not in mapping:
            raise ValueError(f"Unknown limit feature: {feature_key}")
        return mapping[feature_key]

    async def configured_decision(self, user, feature_key, *, consume=False, ref=None, notify_bot=None):
        from app.services.entitlements.engine import EntitlementEngine
        from app.services.entitlements.state import resolve_state, EntitlementState
        from app.services.course_access_policy_service import CourseAccessPolicyService
        if resolve_state(user) != EntitlementState.BLOCKED and (await CourseAccessPolicyService(self.session).get_policy()).free_active:
            return {"ok": True, "allowed": True, "is_paid": self.is_paid_user(user),
                    "policy_free": True, "limit": None, "remaining": None, "window": "none"}
        engine = EntitlementEngine(self.session)
        action = self.action_for_feature(feature_key)
        decision = (await engine.consume(user, action, ref=ref, notify_bot=notify_bot)
                    if consume else await engine.check(user, action))
        return decision.as_dict(is_paid=self.is_paid_user(user), language=getattr(user, "language", "ru"))

    async def daily_status(
        self,
        user,
        feature_key: str,
        *,
        lifetime: bool = False,
        limit_override: int | None = None,
    ) -> dict:
        """Bepul holatni qaytaradi (yozmasdan). ``lifetime=True`` bo'lsa — umrbod
        hisob (kunlik yangilanmaydi).

        ``limit_override`` berilsa chegara `COURSE_DAILY_FREE_LIMITS` dan emas,
        chaqiruvchidan olinadi. Berilmasa — bugungi xatti-harakat aynan o'zi.
        """
        if limit_override is None:
            return await self.configured_decision(user, feature_key)
        feature_key = self._normalize_daily_feature(
            feature_key, allow_unknown=limit_override is not None
        )
        limit = (
            int(limit_override)
            if limit_override is not None
            else COURSE_DAILY_FREE_LIMITS[feature_key]
        )
        if self.is_paid_user(user):
            return {"allowed": True, "is_paid": True, "limit": limit, "used": 0, "remaining": None}
        if not self.is_free_user(user):
            return {"allowed": False, "is_paid": False, "limit": limit, "used": limit, "remaining": 0}
        offset = await self._learner_offset_minutes(user)
        used = await self._daily_used_today(
            user.telegram_id, feature_key, lifetime=lifetime, offset_minutes=offset
        )
        return {
            "allowed": used < limit,
            "is_paid": False,
            "limit": limit,
            "used": used,
            "remaining": max(0, limit - used),
        }

    async def consume_daily_use(
        self,
        user,
        *,
        feature_key: str,
        ref: str | None = None,
        lifetime: bool = False,
        notify_bot=None,
        limit_override: int | None = None,
    ) -> dict:
        """Limitdan bitta foydalanishni band qiladi. Limit tugagan bo'lsa
        ``allowed=False`` qaytaradi (paywall ko'rsatish uchun).

        ``lifetime=True`` — umrbod hisob (kunlik yangilanmaydi): "bir marta bepul".

        ``ref`` berilsa — o'sha foydalanish idempotent bo'ladi: bir xil ``ref``
        bilan takroriy chaqiruv (sahifa qayta yuklanishi, tarmoq retry) qo'shimcha
        slot egallamaydi.

        ``limit_override`` berilsa chegara `COURSE_DAILY_FREE_LIMITS` dan emas,
        chaqiruvchidan olinadi (markaziy entitlement dvigateli uchun). Hisob
        baribir SHU jadvalda yuritiladi, ya'ni ikkala yo'l bir xil slotlarni
        sanaydi."""
        if limit_override is None:
            return await self.configured_decision(user, feature_key, consume=True, ref=ref, notify_bot=notify_bot)
        feature_key = self._normalize_daily_feature(
            feature_key, allow_unknown=limit_override is not None
        )
        limit = (
            int(limit_override)
            if limit_override is not None
            else COURSE_DAILY_FREE_LIMITS[feature_key]
        )
        if self.is_paid_user(user):
            return {"allowed": True, "recorded": False, "is_paid": True, "remaining": None}
        if not self.is_free_user(user):
            return {"allowed": False, "recorded": False, "error": "course_access_blocked"}

        locked_result = await self.session.execute(
            select(User).where(User.id == user.id).with_for_update()
        )
        locked_user = locked_result.scalar_one_or_none()
        if not locked_user:
            return {"allowed": False, "recorded": False, "error": "user_not_found"}

        # Kun kaliti o'quvchining MAHALLIY sanasi: bitta mahalliy kun ichida
        # o'zgarmaydi, aks holda idempotent takror ikkinchi slotni yeb qo'yardi.
        offset = await self._learner_offset_minutes(locked_user)
        day_key = "lifetime" if lifetime else course_daily_window.local_day_key(offset)
        clean_ref = str(ref).strip()[:48] if ref is not None else None
        dedupe_key = (
            f"daily:{feature_key}:{day_key}:ref:{clean_ref}"
            if clean_ref
            else None
        )

        used = await self._daily_used_today(
            locked_user.telegram_id, feature_key, lifetime=lifetime, offset_minutes=offset
        )

        if lifetime and feature_key in COURSE_FEATURE_KEYS:
            legacy = await self.session.execute(select(func.count(CourseFeatureUsage.id)).where(
                CourseFeatureUsage.user_id == locked_user.id,
                CourseFeatureUsage.feature_key == feature_key,
            ))
            used = max(used, int(legacy.scalar() or 0))

        # Idempotent ref: shu foydalanish bugun allaqachon hisobga olingan bo'lsa,
        # qo'shimcha slot egallamasdan ruxsat beramiz.
        if dedupe_key:
            existing_result = await self.session.execute(
                select(CourseMiniAppEvent.id).where(
                    CourseMiniAppEvent.telegram_id == int(locked_user.telegram_id),
                    CourseMiniAppEvent.event_name == COURSE_DAILY_EVENT_NAME,
                    CourseMiniAppEvent.dedupe_key == dedupe_key,
                )
            )
            if existing_result.scalar_one_or_none():
                return {
                    "allowed": True,
                    "recorded": False,
                    "is_paid": False,
                    "idempotent": True,
                    "remaining": max(0, limit - used),
                }

        if used >= limit:
            # Umrbod hisobda "ertaga ochiladi" degan narsa YO'Q, shuning
            # uchun reset vaqti faqat kunlik limitda beriladi. Klient
            # bo'sh qiymatda "ertaga" deb yozmasligi kerak.
            reset_at = (
                None if lifetime else self.next_daily_reset(offset_minutes=offset).isoformat()
            )
            # O'quvchi limitga endi urildi. Xabar kuniga bir marta ketadi va
            # yuborilmasa ham limit javobi o'zgarmaydi.
            try:
                await LimitNotificationService(self.session).daily_limit_spent(
                    locked_user,
                    feature_key=feature_key,
                    reset_at=reset_at,
                    lifetime=bool(lifetime),
                    limit=limit,
                    bot=notify_bot,
                )
            except Exception:  # noqa: BLE001 — bildirishnoma limitni buzmasin
                logger.info("Daily limit notice failed", exc_info=True)
            return {
                "allowed": False,
                "recorded": False,
                "is_paid": False,
                "error": "free_feature_limit_reached",
                "reset_at": reset_at,
                "lifetime": bool(lifetime),
            }

        if dedupe_key is None:
            dedupe_key = f"daily:{feature_key}:{day_key}:{used + 1}"
        event = CourseMiniAppEvent(
            user_id=locked_user.id,
            telegram_id=int(locked_user.telegram_id),
            event_name=COURSE_DAILY_EVENT_NAME,
            source="course_v3",
            session_id=feature_key,
            dedupe_key=dedupe_key,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(event)
                await self.session.flush()
        except IntegrityError:
            # Poyga: shu slotni parallel so'rov egalladi — qayta sanab tekshiramiz.
            if dedupe_key and clean_ref:
                duplicate_result = await self.session.execute(
                    select(CourseMiniAppEvent.id).where(
                        CourseMiniAppEvent.telegram_id == int(locked_user.telegram_id),
                        CourseMiniAppEvent.event_name == COURSE_DAILY_EVENT_NAME,
                        CourseMiniAppEvent.dedupe_key == dedupe_key,
                    )
                )
                if duplicate_result.scalar_one_or_none():
                    return {
                        "allowed": True,
                        "recorded": False,
                        "is_paid": False,
                        "idempotent": True,
                        "remaining": max(0, limit - used),
                    }
            # Qayta sanash ham o'quvchining mintaqasi bo'yicha bo'lishi shart:
            # aks holda poyga yo'lida UTC+5 o'quvchi UTC oynasi bilan sanaladi va
            # limiti kun o'rtasida noto'g'ri joyda yangilanadi.
            used_again = await self._daily_used_today(
                locked_user.telegram_id,
                feature_key,
                lifetime=lifetime,
                offset_minutes=offset,
            )
            if used_again >= limit:
                return {
                    "allowed": False,
                    "recorded": False,
                    "is_paid": False,
                    "error": "free_feature_limit_reached",
                }
            raise
        return {
            "allowed": True,
            "recorded": True,
            "is_paid": False,
            "remaining": max(0, limit - used - 1),
        }

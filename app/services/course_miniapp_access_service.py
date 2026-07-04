from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.models.course_feature_usage import COURSE_FEATURE_KEYS, CourseFeatureUsage
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.user import User
from app.db.models.voice_practice_session import VoicePracticeSession
from app.services.user_access_state_service import UserAccessStateService


FREE_FEATURE_LIMITS = {feature_key: 1 for feature_key in COURSE_FEATURE_KEYS}
# Yangi bepul user faqat 1-darsni to'liq bepul o'tadi. 2-dars — obuna oynasi
# (frontend darsning ~yarmida paywall ko'rsatadi), 3-dars va keyingilar — qulf.
# Reklama endi darslarda EMAS, mashq bo'limlarida ishlaydi (pastdagi *_ad limitlar).
FREE_COURSE_LESSONS_PER_LEVEL = 1

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


class CourseMiniAppAccessService:
    """Server-side Course Mini App entitlements without changing payment rules."""

    def __init__(self, session):
        self.session = session

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
        return order > FREE_COURSE_LESSONS_PER_LEVEL

    @staticmethod
    def _normalize_feature_key(feature_key: str) -> str:
        normalized = str(feature_key or "").strip().lower()
        if normalized not in COURSE_FEATURE_KEYS:
            raise ValueError(f"Unknown Course Mini App feature: {normalized or '<empty>'}")
        return normalized

    async def _recorded_counts(self, user_id: int) -> dict[str, int]:
        result = await self.session.execute(
            select(CourseFeatureUsage.feature_key, func.count(CourseFeatureUsage.id))
            .where(CourseFeatureUsage.user_id == user_id)
            .group_by(CourseFeatureUsage.feature_key)
        )
        return {str(feature): int(count or 0) for feature, count in result.all()}

    async def _legacy_counts(self, user) -> dict[str, int]:
        counts = {feature_key: 0 for feature_key in COURSE_FEATURE_KEYS}
        if getattr(user, "trial_course_completed_at", None):
            counts["lesson"] = 1
        if getattr(user, "trial_voice_used_at", None):
            counts["voice"] = 1

        voice_result = await self.session.execute(
            select(func.count(VoicePracticeSession.id)).where(
                VoicePracticeSession.user_telegram_id == user.telegram_id
            )
        )
        if int(voice_result.scalar_one() or 0) > 0:
            counts["voice"] = 1
        return counts

    async def get_entitlements(self, user) -> dict[str, dict]:
        paid = self.is_paid_user(user)
        if paid:
            return {
                feature_key: {
                    "allowed": True,
                    "is_paid": True,
                    "free_limit": FREE_FEATURE_LIMITS[feature_key],
                    "used": 0,
                    "remaining_free": None,
                }
                for feature_key in COURSE_FEATURE_KEYS
            }

        if not self.is_free_user(user):
            return {
                feature_key: {
                    "allowed": False,
                    "is_paid": False,
                    "free_limit": FREE_FEATURE_LIMITS[feature_key],
                    "used": 0,
                    "remaining_free": 0,
                }
                for feature_key in COURSE_FEATURE_KEYS
            }

        recorded = await self._recorded_counts(user.id)
        legacy = await self._legacy_counts(user)
        entitlements = {}
        for feature_key in COURSE_FEATURE_KEYS:
            used = max(int(recorded.get(feature_key, 0)), int(legacy.get(feature_key, 0)))
            limit = FREE_FEATURE_LIMITS[feature_key]
            entitlements[feature_key] = {
                "allowed": used < limit,
                "is_paid": False,
                "free_limit": limit,
                "used": used,
                "remaining_free": max(0, limit - used),
            }
        return entitlements

    async def consume_free_use(self, user, *, feature_key: str, usage_ref: str) -> dict:
        feature_key = self._normalize_feature_key(feature_key)
        usage_ref = str(usage_ref or "").strip()[:120]
        if not usage_ref:
            raise ValueError("usage_ref is required")
        if self.is_paid_user(user):
            return {"allowed": True, "recorded": False, "is_paid": True, "idempotent": False}
        if not self.is_free_user(user):
            return {"allowed": False, "recorded": False, "error": "course_access_blocked"}

        locked_result = await self.session.execute(
            select(User).where(User.id == user.id).with_for_update()
        )
        locked_user = locked_result.scalar_one_or_none()
        if not locked_user:
            return {"allowed": False, "recorded": False, "error": "user_not_found"}

        existing_result = await self.session.execute(
            select(CourseFeatureUsage).where(
                CourseFeatureUsage.user_id == locked_user.id,
                CourseFeatureUsage.feature_key == feature_key,
                CourseFeatureUsage.usage_ref == usage_ref,
            )
        )
        if existing_result.scalar_one_or_none():
            return {"allowed": True, "recorded": False, "is_paid": False, "idempotent": True}

        entitlements = await self.get_entitlements(locked_user)
        if not entitlements[feature_key]["allowed"]:
            return {
                "allowed": False,
                "recorded": False,
                "is_paid": False,
                "error": "free_feature_limit_reached",
            }

        usage = CourseFeatureUsage(
            user_id=locked_user.id,
            feature_key=feature_key,
            usage_ref=usage_ref,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(usage)
                await self.session.flush()
        except IntegrityError:
            duplicate_result = await self.session.execute(
                select(CourseFeatureUsage.id).where(
                    CourseFeatureUsage.user_id == locked_user.id,
                    CourseFeatureUsage.feature_key == feature_key,
                    CourseFeatureUsage.usage_ref == usage_ref,
                )
            )
            if duplicate_result.scalar_one_or_none():
                return {"allowed": True, "recorded": False, "is_paid": False, "idempotent": True}
            raise

        return {"allowed": True, "recorded": True, "is_paid": False, "idempotent": False}

    # ----- Kunlik limitlar (Mashq bo'limlari + reklama darslari) ---------------

    @staticmethod
    def _day_start() -> datetime:
        return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    @classmethod
    def _normalize_daily_feature(cls, feature_key: str) -> str:
        normalized = str(feature_key or "").strip().lower()
        if normalized not in COURSE_DAILY_FREE_LIMITS:
            raise ValueError(f"Unknown Course daily feature: {normalized or '<empty>'}")
        return normalized

    async def _daily_used_today(self, telegram_id: int, feature_key: str, *, lifetime: bool = False) -> int:
        conditions = [
            CourseMiniAppEvent.telegram_id == int(telegram_id),
            CourseMiniAppEvent.event_name == COURSE_DAILY_EVENT_NAME,
            CourseMiniAppEvent.session_id == feature_key,
        ]
        # lifetime=True — kunlik filtr yo'q: umrbod hisob (bir marta bepul uchun).
        if not lifetime:
            conditions.append(CourseMiniAppEvent.created_at >= self._day_start())
        result = await self.session.execute(
            select(func.count(CourseMiniAppEvent.id)).where(*conditions)
        )
        return int(result.scalar_one() or 0)

    async def daily_status(self, user, feature_key: str, *, lifetime: bool = False) -> dict:
        """Bepul holatni qaytaradi (yozmasdan). ``lifetime=True`` bo'lsa — umrbod
        hisob (kunlik yangilanmaydi)."""
        feature_key = self._normalize_daily_feature(feature_key)
        limit = COURSE_DAILY_FREE_LIMITS[feature_key]
        if self.is_paid_user(user):
            return {"allowed": True, "is_paid": True, "limit": limit, "used": 0, "remaining": None}
        if not self.is_free_user(user):
            return {"allowed": False, "is_paid": False, "limit": limit, "used": limit, "remaining": 0}
        used = await self._daily_used_today(user.telegram_id, feature_key, lifetime=lifetime)
        return {
            "allowed": used < limit,
            "is_paid": False,
            "limit": limit,
            "used": used,
            "remaining": max(0, limit - used),
        }

    async def consume_daily_use(
        self, user, *, feature_key: str, ref: str | None = None, lifetime: bool = False
    ) -> dict:
        """Limitdan bitta foydalanishni band qiladi. Limit tugagan bo'lsa
        ``allowed=False`` qaytaradi (paywall ko'rsatish uchun).

        ``lifetime=True`` — umrbod hisob (kunlik yangilanmaydi): "bir marta bepul".

        ``ref`` berilsa — o'sha foydalanish idempotent bo'ladi: bir xil ``ref``
        bilan takroriy chaqiruv (sahifa qayta yuklanishi, tarmoq retry) qo'shimcha
        slot egallamaydi."""
        feature_key = self._normalize_daily_feature(feature_key)
        limit = COURSE_DAILY_FREE_LIMITS[feature_key]
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

        day_key = "lifetime" if lifetime else self._day_start().date().isoformat()
        clean_ref = str(ref).strip()[:48] if ref is not None else None
        dedupe_key = (
            f"daily:{feature_key}:{day_key}:ref:{clean_ref}"
            if clean_ref
            else None
        )

        used = await self._daily_used_today(locked_user.telegram_id, feature_key, lifetime=lifetime)

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
            return {
                "allowed": False,
                "recorded": False,
                "is_paid": False,
                "error": "free_feature_limit_reached",
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
            used_again = await self._daily_used_today(locked_user.telegram_id, feature_key, lifetime=lifetime)
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

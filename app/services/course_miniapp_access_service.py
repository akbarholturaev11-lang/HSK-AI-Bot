import hashlib
import json
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.models.course_feature_usage import COURSE_FEATURE_KEYS, CourseFeatureUsage
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.user import User
from app.db.models.voice_practice_session import VoicePracticeSession
from app.services.user_access_state_service import UserAccessStateService


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
    def daily_reset_hour_utc() -> int:
        """Kunlik limit qaysi UTC soatda yangilanadi (env orqali)."""

        try:
            from app.config import settings as _settings

            hour = int(getattr(_settings, "COURSE_DAILY_RESET_HOUR_UTC", 0) or 0)
        except Exception:  # noqa: BLE001 — sozlama o'qilmasa eski xatti-harakat
            hour = 0
        # Noto'g'ri sozlama limitni butunlay buzmasin.
        return hour if 0 <= hour <= 23 else 0

    @classmethod
    def _day_start(cls, now: datetime | None = None) -> datetime:
        """Joriy 'limit kuni'ning boshlanishi.

        Reset soati 0 bo'lganda bu aynan UTC yarim tun — ya'ni sozlama
        qo'shilishi bilan hech kimning limiti siljimaydi.
        """
        moment = now or datetime.now(timezone.utc)
        hour = cls.daily_reset_hour_utc()
        start = moment.replace(hour=hour, minute=0, second=0, microsecond=0)
        if moment < start:
            start -= timedelta(days=1)
        return start

    @classmethod
    def next_daily_reset(cls, now: datetime | None = None) -> datetime:
        """Kunlik limit keyingi marta qachon ochilishi (UTC).

        Klient buni o'z vaqt mintaqasida ko'rsatadi; server hech qachon
        formatlangan soat qaytarmaydi.
        """
        return cls._day_start(now) + timedelta(days=1)

    @classmethod
    def _normalize_daily_feature(cls, feature_key: str) -> str:
        normalized = str(feature_key or "").strip().lower()
        if normalized not in COURSE_DAILY_FREE_LIMITS:
            raise ValueError(f"Unknown Course daily feature: {normalized or '<empty>'}")
        return normalized

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

    async def start_ad_attempt(
        self,
        user,
        *,
        feature_key: str,
        access_ref: str,
        ad_id: int,
        placement: str,
        required_seconds: int,
        level: str | None = None,
        lesson_order: int | None = None,
    ) -> dict:
        """Issue a one-way-tokenized ad attempt anchored to server time.

        The raw token is returned only to the authenticated browser. The event
        stores its SHA-256 digest together with the exact access binding, so a
        forged ``watched_seconds`` value cannot authorize protected content.
        """

        feature = self._normalize_ad_auth_feature(feature_key)
        ref = self.normalize_access_ref(access_ref)
        normalized_ad_id = self._normalize_ad_id(ad_id)
        normalized_placement = self._normalize_ad_placement(placement)
        duration = self._normalize_ad_duration(required_seconds)
        normalized_level = self._normalize_ad_level(level)
        normalized_lesson_order = self._normalize_ad_lesson_order(lesson_order)
        if feature == "lesson" and (not normalized_level or normalized_lesson_order <= 0):
            raise ValueError("invalid_ad_lesson_binding")
        if not self.is_paid_user(user) and not self.is_free_user(user):
            return {"allowed": False, "error": "course_access_blocked"}

        attempt_token = secrets.token_urlsafe(24)
        session_id = self._ad_attempt_session_id(attempt_token)
        payload = {
            "feature": feature,
            "access_ref": ref,
            "ad_id": normalized_ad_id,
            "placement": normalized_placement,
            "required_seconds": duration,
        }
        if normalized_level:
            payload["level"] = normalized_level
        if normalized_lesson_order:
            payload["lesson_order"] = normalized_lesson_order
        event = CourseMiniAppEvent(
            user_id=user.id,
            telegram_id=int(user.telegram_id),
            event_name=COURSE_AD_ATTEMPT_EVENT_NAME,
            source=COURSE_AD_ATTEMPT_EVENT_SOURCE,
            session_id=session_id,
            dedupe_key=session_id,
            payload_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        )
        try:
            async with self.session.begin_nested():
                self.session.add(event)
                await self.session.flush()
        except IntegrityError as exc:
            # A cryptographic token collision is practically impossible. Fail
            # closed rather than reusing an attempt whose binding is unknown.
            raise RuntimeError("ad_attempt_token_collision") from exc
        return {
            "allowed": True,
            "attempt_token": attempt_token,
            "required_seconds": duration,
            "expires_in": COURSE_AD_ATTEMPT_TTL_SECONDS,
        }

    async def validate_ad_attempt(
        self,
        user,
        *,
        feature_key: str,
        access_ref: str,
        ad_id: int,
        placement: str,
        attempt_token: str,
        level: str | None = None,
        lesson_order: int | None = None,
    ) -> dict:
        """Validate exact binding and elapsed server time for an ad attempt."""

        feature = self._normalize_ad_auth_feature(feature_key)
        ref = self.normalize_access_ref(access_ref)
        normalized_ad_id = self._normalize_ad_id(ad_id)
        normalized_placement = self._normalize_ad_placement(placement)
        normalized_level = self._normalize_ad_level(level)
        normalized_lesson_order = self._normalize_ad_lesson_order(lesson_order)
        if feature == "lesson" and (not normalized_level or normalized_lesson_order <= 0):
            return {"allowed": False, "error": "invalid_ad_attempt"}
        try:
            attempt_session_id = self._ad_attempt_session_id(attempt_token)
        except ValueError:
            return {"allowed": False, "error": "ad_attempt_required"}

        result = await self.session.execute(
            select(CourseMiniAppEvent).where(
                CourseMiniAppEvent.user_id == user.id,
                CourseMiniAppEvent.telegram_id == int(user.telegram_id),
                CourseMiniAppEvent.event_name == COURSE_AD_ATTEMPT_EVENT_NAME,
                CourseMiniAppEvent.source == COURSE_AD_ATTEMPT_EVENT_SOURCE,
                CourseMiniAppEvent.session_id == attempt_session_id,
            )
        )
        event = result.scalar_one_or_none()
        if not event:
            return {"allowed": False, "error": "ad_attempt_required"}
        try:
            payload = json.loads(event.payload_json or "{}")
            required_seconds = self._normalize_ad_duration(payload["required_seconds"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return {"allowed": False, "error": "invalid_ad_attempt"}
        expected = {
            "feature": feature,
            "access_ref": ref,
            "ad_id": normalized_ad_id,
            "placement": normalized_placement,
        }
        actual = {
            "feature": str(payload.get("feature") or ""),
            "access_ref": str(payload.get("access_ref") or ""),
            "ad_id": payload.get("ad_id"),
            "placement": str(payload.get("placement") or ""),
        }
        if normalized_level:
            expected["level"] = normalized_level
            actual["level"] = str(payload.get("level") or "")
        if normalized_lesson_order:
            expected["lesson_order"] = normalized_lesson_order
            actual["lesson_order"] = payload.get("lesson_order")
        try:
            actual["ad_id"] = int(actual["ad_id"])
            if normalized_lesson_order:
                actual["lesson_order"] = int(actual["lesson_order"])
        except (TypeError, ValueError):
            return {"allowed": False, "error": "invalid_ad_attempt"}
        if actual != expected:
            return {"allowed": False, "error": "invalid_ad_attempt"}

        started_at = self._as_utc(event.created_at)
        now = datetime.now(timezone.utc)
        if not started_at:
            return {"allowed": False, "error": "invalid_ad_attempt"}
        elapsed_seconds = (now - started_at).total_seconds()
        if elapsed_seconds > COURSE_AD_ATTEMPT_TTL_SECONDS:
            return {"allowed": False, "error": "ad_attempt_expired"}
        if elapsed_seconds < required_seconds:
            return {
                "allowed": False,
                "error": "ad_attempt_incomplete",
                "retry_after": max(1, required_seconds - int(max(0, elapsed_seconds))),
            }
        return {
            "allowed": True,
            "attempt_id": attempt_session_id,
            "elapsed_seconds": int(elapsed_seconds),
            "required_seconds": required_seconds,
        }

    async def record_ad_authorization(
        self,
        user,
        *,
        feature_key: str,
        access_ref: str,
        ad_id: int,
        placement: str,
        attempt_token: str = "",
        level: str | None = None,
        lesson_order: int | None = None,
    ) -> dict:
        """Record a completed start-ad as a bounded server authorization.

        Call this only after ``CourseAdService.record_view`` returned ``ok``.
        Other placements are analytics-only and never authorize a new session.
        """

        feature = self._normalize_ad_auth_feature(feature_key)
        ref = self.normalize_access_ref(access_ref)
        normalized_level = self._normalize_ad_level(level)
        normalized_lesson_order = self._normalize_ad_lesson_order(lesson_order)
        if feature == "lesson" and (not normalized_level or normalized_lesson_order <= 0):
            return {"allowed": False, "recorded": False, "error": "invalid_ad_lesson_binding"}
        if self.is_paid_user(user):
            return {
                "allowed": True,
                "recorded": False,
                "is_paid": True,
                "access_ref": ref,
            }
        if not self.is_free_user(user):
            return {"allowed": False, "recorded": False, "error": "course_access_blocked"}
        normalized_placement = self._normalize_ad_placement(placement)
        if normalized_placement != "start":
            return {
                "allowed": False,
                "recorded": False,
                "error": "ad_authorization_requires_start_view",
            }
        normalized_ad_id = self._normalize_ad_id(ad_id)
        attempt = await self.validate_ad_attempt(
            user,
            feature_key=feature,
            access_ref=ref,
            ad_id=normalized_ad_id,
            placement=normalized_placement,
            attempt_token=attempt_token,
            level=normalized_level,
            lesson_order=normalized_lesson_order,
        )
        if not attempt.get("allowed"):
            return {"recorded": False, **attempt}

        session_id = self._ad_authorization_session_id(feature, ref)
        dedupe_key = f"ad-auth:{session_id}"
        now = datetime.now(timezone.utc)
        existing_result = await self.session.execute(
            select(CourseMiniAppEvent).where(
                CourseMiniAppEvent.user_id == user.id,
                CourseMiniAppEvent.telegram_id == int(user.telegram_id),
                CourseMiniAppEvent.event_name == COURSE_AD_AUTH_EVENT_NAME,
                CourseMiniAppEvent.source == COURSE_AD_AUTH_EVENT_SOURCE,
                CourseMiniAppEvent.dedupe_key == dedupe_key,
            )
        )
        existing_event = existing_result.scalar_one_or_none()
        if existing_event:
            created_at = self._as_utc(existing_event.created_at)
            cutoff = now - timedelta(seconds=COURSE_AD_AUTH_TTL_SECONDS)
            if created_at is None or created_at < cutoff:
                # A browser can legitimately keep the same sessionStorage ref
                # beyond the authorization TTL. A newly completed ad must renew
                # that exact binding instead of remaining permanently stale.
                existing_event.created_at = now
                existing_event.payload_json = json.dumps(
                    {
                        "feature": feature,
                        "access_ref": ref,
                        "ad_id": normalized_ad_id,
                        "placement": "start",
                        "attempt_id": attempt["attempt_id"],
                        **({"level": normalized_level} if normalized_level else {}),
                        **(
                            {"lesson_order": normalized_lesson_order}
                            if normalized_lesson_order
                            else {}
                        ),
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                await self.session.flush()
                return {
                    "allowed": True,
                    "recorded": True,
                    "refreshed": True,
                    "is_paid": False,
                    "idempotent": False,
                    "access_ref": ref,
                }
            return {
                "allowed": True,
                "recorded": False,
                "is_paid": False,
                "idempotent": True,
                "access_ref": ref,
            }

        event = CourseMiniAppEvent(
            user_id=user.id,
            telegram_id=int(user.telegram_id),
            event_name=COURSE_AD_AUTH_EVENT_NAME,
            source=COURSE_AD_AUTH_EVENT_SOURCE,
            session_id=session_id,
            dedupe_key=dedupe_key,
            payload_json=json.dumps(
                {
                    "feature": feature,
                    "access_ref": ref,
                    "ad_id": normalized_ad_id,
                    "placement": "start",
                    "attempt_id": attempt["attempt_id"],
                    **({"level": normalized_level} if normalized_level else {}),
                    **(
                        {"lesson_order": normalized_lesson_order}
                        if normalized_lesson_order
                        else {}
                    ),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        )
        try:
            async with self.session.begin_nested():
                self.session.add(event)
                await self.session.flush()
        except IntegrityError:
            duplicate_result = await self.session.execute(
                select(CourseMiniAppEvent.id).where(
                    CourseMiniAppEvent.user_id == user.id,
                    CourseMiniAppEvent.telegram_id == int(user.telegram_id),
                    CourseMiniAppEvent.event_name == COURSE_AD_AUTH_EVENT_NAME,
                    CourseMiniAppEvent.source == COURSE_AD_AUTH_EVENT_SOURCE,
                    CourseMiniAppEvent.dedupe_key == dedupe_key,
                )
            )
            if duplicate_result.scalar_one_or_none():
                return {
                    "allowed": True,
                    "recorded": False,
                    "is_paid": False,
                    "idempotent": True,
                    "access_ref": ref,
                }
            raise
        return {
            "allowed": True,
            "recorded": True,
            "is_paid": False,
            "idempotent": False,
            "access_ref": ref,
        }

    async def verify_ad_authorization(
        self,
        user,
        *,
        feature_key: str,
        access_ref: str,
        max_age_seconds: int = COURSE_AD_AUTH_TTL_SECONDS,
        level: str | None = None,
        lesson_order: int | None = None,
    ) -> dict:
        """Verify a recent completed ad bound to this user, feature and ref."""

        feature = self._normalize_ad_auth_feature(feature_key)
        ref = self.normalize_access_ref(access_ref)
        normalized_level = self._normalize_ad_level(level)
        normalized_lesson_order = self._normalize_ad_lesson_order(lesson_order)
        if feature == "lesson" and (not normalized_level or normalized_lesson_order <= 0):
            return {"allowed": False, "is_paid": False, "error": "invalid_ad_authorization"}
        if self.is_paid_user(user):
            return {"allowed": True, "is_paid": True, "access_ref": ref}
        if not self.is_free_user(user):
            return {"allowed": False, "is_paid": False, "error": "course_access_blocked"}
        ttl = max(30, min(7200, int(max_age_seconds or COURSE_AD_AUTH_TTL_SECONDS)))
        select_target = CourseMiniAppEvent if (normalized_level or normalized_lesson_order) else CourseMiniAppEvent.id
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=ttl)
        result = await self.session.execute(
            select(select_target).where(
                CourseMiniAppEvent.user_id == user.id,
                CourseMiniAppEvent.telegram_id == int(user.telegram_id),
                CourseMiniAppEvent.event_name == COURSE_AD_AUTH_EVENT_NAME,
                CourseMiniAppEvent.source == COURSE_AD_AUTH_EVENT_SOURCE,
                CourseMiniAppEvent.session_id == self._ad_authorization_session_id(feature, ref),
                CourseMiniAppEvent.created_at >= cutoff,
            )
        )
        event_or_id = result.scalar_one_or_none()
        if not event_or_id:
            return {
                "allowed": False,
                "is_paid": False,
                "error": "ad_authorization_required",
            }
        if normalized_level or normalized_lesson_order:
            try:
                payload = json.loads(event_or_id.payload_json or "{}")
            except (TypeError, ValueError, json.JSONDecodeError):
                return {"allowed": False, "is_paid": False, "error": "invalid_ad_authorization"}
            if normalized_level and str(payload.get("level") or "") != normalized_level:
                return {"allowed": False, "is_paid": False, "error": "invalid_ad_authorization"}
            if normalized_lesson_order:
                try:
                    stored_lesson_order = int(payload.get("lesson_order") or 0)
                except (TypeError, ValueError):
                    stored_lesson_order = 0
                if stored_lesson_order != normalized_lesson_order:
                    return {
                        "allowed": False,
                        "is_paid": False,
                        "error": "invalid_ad_authorization",
                    }
        return {"allowed": True, "is_paid": False, "access_ref": ref}

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
                # Umrbod hisobda "ertaga ochiladi" degan narsa YO'Q, shuning
                # uchun reset vaqti faqat kunlik limitda beriladi. Klient
                # bo'sh qiymatda "ertaga" deb yozmasligi kerak.
                "reset_at": None if lifetime else self.next_daily_reset().isoformat(),
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

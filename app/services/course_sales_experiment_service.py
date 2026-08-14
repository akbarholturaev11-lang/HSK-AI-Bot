from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.payment import Payment
from app.repositories.bot_setting_repo import BotSettingRepository
from app.repositories.discount_campaign_repo import DiscountCampaignRepository
from app.repositories.payment_repo import PaymentRepository
from app.services.course_access_policy_service import COURSE_ACCESS_MODE_SUBSCRIPTION
from app.services.course_miniapp_access_service import CourseMiniAppAccessService


SALES_EXPERIMENT_ID = "sales_value_v1"
SALES_EXPERIMENT_SETTINGS_KEY = "course_sales_experiment_v1"
SALES_OFFER_ASSIGNED_EVENT = "sales_offer_assigned"
SALES_EXPERIMENT_TRIGGER = "hsk1_first_checkpoint"
SALES_EXPERIMENT_LESSON_ORDER = 3

SALES_EXPERIMENT_MODES = frozenset(("off", "shadow", "ab", "treatment"))
SALES_EXPERIMENT_TREATMENT_PERCENTAGES = frozenset((0, 50, 90, 100))
SALES_EXPERIMENT_CLIENT_EVENTS = frozenset(
    (
        "sales_bridge_seen",
        "sales_bridge_cta",
        "sales_offer_seen",
        "sales_offer_dismissed",
    )
)
SALES_BRIDGE_ACTIONS = frozenset(("unlock_path", "free_preview"))

_ASSIGNMENT_DEDUPE_KEY = f"{SALES_EXPERIMENT_ID}:assigned"
_SPECIAL_ENTRY_SOURCE_MARKERS = (
    "campaign",
    "discount",
    "feedback",
    "promo",
)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_datetime(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return _as_utc(datetime.fromisoformat(raw.replace("Z", "+00:00")))
    except ValueError:
        return None


def _iso(value: datetime | None) -> str | None:
    normalized = _as_utc(value)
    return normalized.isoformat() if normalized else None


def _json_object(value: str | None) -> dict[str, Any]:
    try:
        decoded = json.loads(value or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


@dataclass(frozen=True)
class CourseSalesExperimentSettings:
    mode: str = "off"
    treatment_percent: int = 50
    started_at: datetime | None = None
    saved_at: datetime | None = None
    updated_by_telegram_id: int | None = None

    @classmethod
    def default(cls) -> "CourseSalesExperimentSettings":
        return cls()

    @classmethod
    def from_raw(cls, raw: str | None) -> "CourseSalesExperimentSettings":
        if not raw:
            return cls.default()
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            return cls.default()
        if not isinstance(payload, dict):
            return cls.default()

        mode = str(payload.get("mode") or "").strip().lower()
        try:
            treatment_percent = int(payload.get("treatment_percent"))
        except (TypeError, ValueError):
            return cls.default()
        started_at = _parse_datetime(payload.get("started_at"))
        if (
            mode not in SALES_EXPERIMENT_MODES
            or treatment_percent not in SALES_EXPERIMENT_TREATMENT_PERCENTAGES
            or (mode != "off" and started_at is None)
        ):
            return cls.default()
        try:
            updated_by = int(payload.get("updated_by_telegram_id") or 0) or None
        except (TypeError, ValueError):
            updated_by = None
        return cls(
            mode=mode,
            treatment_percent=treatment_percent,
            started_at=started_at,
            saved_at=_parse_datetime(payload.get("saved_at")),
            updated_by_telegram_id=updated_by,
        )

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        previous: "CourseSalesExperimentSettings | None" = None,
        now: datetime | None = None,
        updated_by_telegram_id: int | None = None,
    ) -> "CourseSalesExperimentSettings":
        if not isinstance(payload, dict):
            raise ValueError("invalid_sales_experiment_settings")
        current = previous or cls.default()
        mode = str(payload.get("mode", current.mode) or "").strip().lower()
        if mode not in SALES_EXPERIMENT_MODES:
            raise ValueError("invalid_sales_experiment_mode")
        try:
            treatment_percent = int(
                payload.get("treatment_percent", current.treatment_percent)
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid_sales_experiment_treatment_percent") from exc
        if treatment_percent not in SALES_EXPERIMENT_TREATMENT_PERCENTAGES:
            raise ValueError("invalid_sales_experiment_treatment_percent")

        saved_at = _as_utc(now) or datetime.now(timezone.utc)
        started_at = current.started_at
        if mode != "off" and started_at is None:
            started_at = saved_at
        try:
            updated_by = int(updated_by_telegram_id or 0) or None
        except (TypeError, ValueError):
            updated_by = None
        return cls(
            mode=mode,
            treatment_percent=treatment_percent,
            started_at=started_at,
            saved_at=saved_at,
            updated_by_telegram_id=updated_by,
        )

    def storage_payload(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "treatment_percent": self.treatment_percent,
            "started_at": _iso(self.started_at),
            "saved_at": _iso(self.saved_at),
            "updated_by_telegram_id": self.updated_by_telegram_id,
        }

    def storage_value(self) -> str:
        return json.dumps(
            self.storage_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def public_payload(self) -> dict[str, Any]:
        payload = self.storage_payload()
        payload["experiment_id"] = SALES_EXPERIMENT_ID
        payload["effective_treatment_percent"] = (
            100 if self.mode == "treatment" else self.treatment_percent
        )
        return payload


@dataclass(frozen=True)
class SalesOfferAssignment:
    arm: str
    bucket: int
    event: CourseMiniAppEvent

    def public_offer(self) -> dict[str, str]:
        return {
            "experiment_id": SALES_EXPERIMENT_ID,
            "arm": self.arm,
            "trigger": SALES_EXPERIMENT_TRIGGER,
        }


class CourseSalesExperimentService:
    """Server-owned sales experiment assignment and trusted event context."""

    def __init__(self, session):
        self.session = session
        self.setting_repo = BotSettingRepository(session)

    @staticmethod
    def assignment_bucket(telegram_id: int) -> int:
        digest = hashlib.sha256(
            f"{SALES_EXPERIMENT_ID}:{int(telegram_id)}".encode("utf-8")
        ).digest()
        return int.from_bytes(digest[:4], "big") % 100

    @staticmethod
    def assignment_arm(*, bucket: int, treatment_percent: int) -> str:
        return "treatment" if int(bucket) < int(treatment_percent) else "control"

    async def get_settings(self) -> CourseSalesExperimentSettings:
        raw = await self.setting_repo.get(SALES_EXPERIMENT_SETTINGS_KEY)
        return CourseSalesExperimentSettings.from_raw(raw)

    async def save_settings(
        self,
        payload: dict[str, Any],
        *,
        now: datetime | None = None,
        updated_by_telegram_id: int | None = None,
    ) -> CourseSalesExperimentSettings:
        current = await self.get_settings()
        settings = CourseSalesExperimentSettings.from_payload(
            payload,
            previous=current,
            now=now,
            updated_by_telegram_id=updated_by_telegram_id,
        )
        await self.setting_repo.set(
            SALES_EXPERIMENT_SETTINGS_KEY,
            settings.storage_value(),
        )
        return settings

    async def resolve_offer(
        self,
        *,
        user,
        level: str,
        access_policy,
        entry_source: str | None = None,
        session_id: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, str] | None:
        """Resolve the map contract and reserve an ITT assignment when active."""
        settings = await self.get_settings()
        if settings.mode == "off":
            return None
        current_time = _as_utc(now) or datetime.now(timezone.utc)
        if not await self._is_eligible(
            user=user,
            level=level,
            access_policy=access_policy,
            entry_source=entry_source,
            settings=settings,
            now=current_time,
        ):
            return None

        if settings.mode == "shadow":
            return {
                "experiment_id": SALES_EXPERIMENT_ID,
                "arm": "control",
                "trigger": SALES_EXPERIMENT_TRIGGER,
            }

        existing = await self._load_assignment(int(user.telegram_id))
        if existing:
            return existing.public_offer()

        bucket = self.assignment_bucket(int(user.telegram_id))
        treatment_percent = (
            100 if settings.mode == "treatment" else settings.treatment_percent
        )
        arm = self.assignment_arm(
            bucket=bucket,
            treatment_percent=treatment_percent,
        )
        assignment = await self._reserve_assignment(
            user=user,
            arm=arm,
            bucket=bucket,
            settings=settings,
            entry_source=entry_source,
            session_id=session_id,
            now=current_time,
        )
        return assignment.public_offer() if assignment else None

    async def trusted_event_context(
        self,
        *,
        user,
        event_name: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return server-authoritative values for one sales client event.

        This method never creates an assignment. A client-provided arm, bucket,
        experiment id, source, level or dedupe key is deliberately ignored.
        """
        normalized_event = str(event_name or "").strip()
        if normalized_event not in SALES_EXPERIMENT_CLIENT_EVENTS:
            return {"ok": False, "error": "sales_offer_event_not_allowed"}
        if not user or not getattr(user, "telegram_id", None):
            return {"ok": False, "error": "sales_offer_user_required"}

        assignment = await self._load_assignment(int(user.telegram_id))
        if not assignment:
            return {"ok": False, "error": "sales_offer_assignment_required"}
        if assignment.arm != "treatment":
            return {"ok": False, "error": "sales_offer_treatment_required"}

        action = None
        if normalized_event == "sales_bridge_cta":
            action = str((payload or {}).get("action") or "").strip().lower()
            if action not in SALES_BRIDGE_ACTIONS:
                return {"ok": False, "error": "sales_offer_action_invalid"}

        trusted_payload = {
            "experiment_id": SALES_EXPERIMENT_ID,
            "arm": assignment.arm,
            "bucket": assignment.bucket,
            "trigger": SALES_EXPERIMENT_TRIGGER,
            "entry_level": str(getattr(user, "level", "") or "").strip().lower()
            or None,
            "language": str(getattr(user, "language", "") or "").strip().lower()
            or None,
        }
        if action:
            trusted_payload["action"] = action
        dedupe_suffix = f":{action}" if action else ""
        return {
            "ok": True,
            "source": SALES_EXPERIMENT_ID,
            "level": "hsk1",
            "lesson_order": SALES_EXPERIMENT_LESSON_ORDER,
            "dedupe_key": f"{SALES_EXPERIMENT_ID}:{normalized_event}{dedupe_suffix}",
            "payload": trusted_payload,
        }

    # Explicit alias for integration call sites that prefer the security term.
    authoritative_event_context = trusted_event_context

    async def _is_eligible(
        self,
        *,
        user,
        level: str,
        access_policy,
        entry_source: str | None,
        settings: CourseSalesExperimentSettings,
        now: datetime,
    ) -> bool:
        if not user or not getattr(user, "telegram_id", None):
            return False
        if str(level or "").strip().lower() not in {"beginner", "hsk1"}:
            return False
        active_mode = str(
            getattr(access_policy, "active_mode", access_policy) or ""
        ).strip().lower()
        if active_mode != COURSE_ACCESS_MODE_SUBSCRIPTION:
            return False
        if CourseMiniAppAccessService.is_paid_user(user):
            return False
        if str(getattr(user, "status", "") or "").strip().lower() == "blocked":
            return False
        if str(getattr(user, "payment_status", "") or "").strip().lower() == "pending":
            return False

        started_at = _as_utc(settings.started_at)
        created_at = _as_utc(getattr(user, "created_at", None))
        if not started_at or not created_at or created_at < started_at:
            return False
        if now < started_at:
            return False
        if self._is_special_entry_source(entry_source):
            return False
        if bool(getattr(user, "discount_eligible", False)):
            return False
        if (
            getattr(user, "discount_offer_started_at", None) is not None
            and not bool(getattr(user, "discount_used", False))
        ):
            return False
        if await PaymentRepository(self.session).has_pending_by_user(
            int(user.telegram_id)
        ):
            return False
        if await self._has_active_campaign(user, now=now):
            return False
        if await self._has_special_checkout(int(user.telegram_id)):
            return False
        return not await self._had_paywall_before(
            int(user.telegram_id),
            started_at=started_at,
        )

    @staticmethod
    def _is_special_entry_source(source: str | None) -> bool:
        normalized = str(source or "").strip().lower()
        return bool(
            normalized
            and any(marker in normalized for marker in _SPECIAL_ENTRY_SOURCE_MARKERS)
        )

    async def _has_special_checkout(self, telegram_id: int) -> bool:
        result = await self.session.execute(
            select(Payment.id)
            .where(
                Payment.user_telegram_id == int(telegram_id),
                Payment.payment_status.in_(("draft", "pending")),
                or_(
                    Payment.discount_campaign_id.is_not(None),
                    Payment.discount_source.notin_(("", "none")),
                ),
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _has_active_campaign(self, user, *, now: datetime) -> bool:
        """Exclude users who can enter a currently active admin discount flow.

        Plan/payment-method targeting is intentionally ignored here: the user
        could select that combination after seeing the experimental offer, so
        keeping them in the cohort would mix campaign lift into sales_value_v1.
        """
        for campaign in await DiscountCampaignRepository(self.session).list_current(now):
            if (
                campaign.target_telegram_id
                and int(campaign.target_telegram_id) != int(user.telegram_id)
            ):
                continue
            audience_checks = (
                (campaign.audience_status, getattr(user, "status", None)),
                (campaign.audience_language, getattr(user, "language", None)),
                (campaign.audience_level, getattr(user, "level", None)),
            )
            if all(
                expected is None
                or str(expected).strip().lower()
                == str(actual or "").strip().lower()
                for expected, actual in audience_checks
            ):
                return True
        return False

    async def _had_paywall_before(
        self,
        telegram_id: int,
        *,
        started_at: datetime,
    ) -> bool:
        result = await self.session.execute(
            select(CourseMiniAppEvent.id)
            .where(
                CourseMiniAppEvent.telegram_id == int(telegram_id),
                CourseMiniAppEvent.event_name == "paywall_seen",
                CourseMiniAppEvent.created_at < started_at,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _load_assignment(self, telegram_id: int) -> SalesOfferAssignment | None:
        result = await self.session.execute(
            select(CourseMiniAppEvent)
            .where(
                CourseMiniAppEvent.telegram_id == int(telegram_id),
                CourseMiniAppEvent.event_name == SALES_OFFER_ASSIGNED_EVENT,
                CourseMiniAppEvent.source == SALES_EXPERIMENT_ID,
                CourseMiniAppEvent.dedupe_key == _ASSIGNMENT_DEDUPE_KEY,
            )
            .order_by(CourseMiniAppEvent.id.desc())
            .limit(1)
        )
        event = result.scalar_one_or_none()
        if not event:
            return None
        payload = _json_object(event.payload_json)
        if payload.get("experiment_id") != SALES_EXPERIMENT_ID:
            return None
        arm = str(payload.get("arm") or "").strip().lower()
        if arm not in {"control", "treatment"}:
            return None
        try:
            bucket = int(payload.get("bucket"))
        except (TypeError, ValueError):
            return None
        if not 0 <= bucket <= 99:
            return None
        return SalesOfferAssignment(arm=arm, bucket=bucket, event=event)

    async def _reserve_assignment(
        self,
        *,
        user,
        arm: str,
        bucket: int,
        settings: CourseSalesExperimentSettings,
        entry_source: str | None,
        session_id: str | None,
        now: datetime,
    ) -> SalesOfferAssignment | None:
        payload = {
            "experiment_id": SALES_EXPERIMENT_ID,
            "arm": arm,
            "bucket": bucket,
            "trigger": SALES_EXPERIMENT_TRIGGER,
            "eligibility_version": "new_unpaid_hsk1_v1",
            "assigned_mode": settings.mode,
            "treatment_percent": (
                100 if settings.mode == "treatment" else settings.treatment_percent
            ),
            "outcome_window_days": 7,
            "experiment_started_at": _iso(settings.started_at),
            "entry_source": str(entry_source or "course_v3").strip()[:40]
            or "course_v3",
        }
        event = CourseMiniAppEvent(
            user_id=getattr(user, "id", None),
            telegram_id=int(user.telegram_id),
            event_name=SALES_OFFER_ASSIGNED_EVENT,
            source=SALES_EXPERIMENT_ID,
            level="hsk1",
            lesson_order=SALES_EXPERIMENT_LESSON_ORDER,
            session_id=str(session_id or "").strip()[:80] or None,
            dedupe_key=_ASSIGNMENT_DEDUPE_KEY,
            payload_json=json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            created_at=now,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(event)
                await self.session.flush()
        except IntegrityError:
            return await self._load_assignment(int(user.telegram_id))
        return SalesOfferAssignment(arm=arm, bucket=bucket, event=event)

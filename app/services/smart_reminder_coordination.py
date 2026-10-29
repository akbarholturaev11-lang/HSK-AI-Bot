"""Read-only source facts and pure category simulation, never delivery authority."""
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
import json

from sqlalchemy import or_, select

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.course_user_notification import CourseUserNotification
from app.db.models.user import User
from app.services.motivation_reminder_service import (
    D1_RECOVERY_ASSIGNED_EVENT, D1_RECOVERY_EXPERIMENT, D1_RECOVERY_HOLDOUT,
)
from app.services.notification_template_service import (
    KEY_D1_RECOVERY, KEY_DAILY_GOAL, KEY_LESSON_UNFINISHED, KEY_OVERTAKEN, KEY_STREAK, KEY_SMART_STUDY,
)
from app.services.smart_reminder_policy import _aware_utc
from app.services.course_levels import content_level
from app.services.smart_reminder_preferences import SmartReminderPreferencesService, _utc


MAX_ASSIGNMENTS = 128
MAX_CONTACTS = 512
LEARNING_CATEGORIES = frozenset({"study", "rank", "weekly"})


def _owner(model, uid, telegram_id):
    canonical = model.user_id == uid
    if type(telegram_id) is int and telegram_id > 0:
        return or_(canonical, model.user_id.is_(None) & (model.telegram_id == telegram_id))
    return canonical  # Never match every NULL-Telegram/native account.


@dataclass(frozen=True)
class D1Scope:
    until: datetime | None = None
    arms: frozenset[str] = frozenset()
    unknown: bool = False

    def reason(self, now):
        if self.unknown:
            return "d1_assignment_unknown"
        if self.until is not None and _aware_utc(now) < self.until:
            return "d1_holdout_active"


async def read_d1_scope(session, user_id, now):
    """Internal read after canonical authorization/User lock; never assigns D1."""
    now = _aware_utc(now)
    with session.no_autoflush:
        telegram_id = await session.scalar(select(User.telegram_id).where(User.id == user_id))
        rows = (await session.execute(select(CourseMiniAppEvent.created_at, CourseMiniAppEvent.payload_json).where(
            _owner(CourseMiniAppEvent, user_id, telegram_id),
            CourseMiniAppEvent.event_name == D1_RECOVERY_ASSIGNED_EVENT,
            CourseMiniAppEvent.source == D1_RECOVERY_EXPERIMENT,
            CourseMiniAppEvent.created_at >= now - D1_RECOVERY_HOLDOUT,
        ).order_by(CourseMiniAppEvent.created_at.desc(), CourseMiniAppEvent.id.desc())
            .limit(MAX_ASSIGNMENTS + 1))).mappings().all()
        until = None
        arms = set()
        unknown = len(rows) > MAX_ASSIGNMENTS
        for row in rows[:MAX_ASSIGNMENTS]:
            assigned = _utc(row["created_at"])
            if assigned > now:
                unknown = True
                continue
            try:
                payload = json.loads(row["payload_json"] or "{}")
                arm = payload.get("arm") if isinstance(payload, dict) else None
            except (ValueError, TypeError):
                arm = None
            if arm not in {"control", "treatment"}:
                unknown = True
            else:
                arms.add(arm)
            end = assigned + D1_RECOVERY_HOLDOUT
            until = max(until, end) if until else end
        return D1Scope(until, frozenset(arms), unknown)


@dataclass(frozen=True)
class CategoryCandidate:
    reference: str
    category: str
    due_at: datetime
    expires_at: datetime
    eligible: bool
    useful: bool | None = None


@dataclass(frozen=True)
class Contact:
    reference: str
    category: str
    at: datetime
    evidence: str  # feed_record / provider_return; neither means shown/read.


@dataclass(frozen=True)
class CoordinationCalibration:
    version: str
    spacing: timedelta
    priority: tuple[str, ...]

    def __post_init__(self):
        if (not isinstance(self.version, str) or not self.version.strip() or
                not isinstance(self.spacing, timedelta) or self.spacing <= timedelta(0) or
                len(self.priority) != 3 or set(self.priority) != LEARNING_CATEGORIES):
            raise ValueError("Explicit version, positive spacing and category order required")


@dataclass(frozen=True)
class CategoryDecision:
    candidate: CategoryCandidate
    disposition: str
    reason: str
    proposed_at: datetime | None = None
    calibration_version: str | None = None
    coverage_limits: tuple[str, ...] = ()
    policy_version: str = field(default="smart-coordination-shadow-v1", init=False)
    requires_recheck: bool = field(default=True, init=False)
    dispatch_allowed: bool = field(default=False, init=False)


def coordinate(candidates, *, now, contacts=(), d1=D1Scope(), calibration=None, coverage_limits=()):
    """Hypothetical slots only. Never consume a counter or change a sender."""
    now = _aware_utc(now)
    unique = {}
    for item in candidates:
        if item.category not in LEARNING_CATEGORIES | {"transactional"} or not item.reference:
            raise ValueError("Known category and stable account-level identity required")
        if _aware_utc(item.due_at) >= _aware_utc(item.expires_at):
            raise ValueError("Explicit positive candidate window required")
        if item.reference in unique and unique[item.reference] != item:
            raise ValueError("Conflicting candidate identity")
        unique[item.reference] = item
    order = {category: n for n, category in enumerate(calibration.priority)} if calibration else {}
    occupied = [_aware_utc(c.at) for c in contacts if c.category in LEARNING_CATEGORIES]
    known = {c.reference for c in contacts if c.category in LEARNING_CATEGORIES}
    results = []
    for item in sorted(unique.values(), key=lambda c:(order.get(c.category, 3), c.due_at, c.reference)):
        def decision(action, reason, at=None):
            return CategoryDecision(item, action, reason, at, calibration.version if calibration else None,
                                    tuple(coverage_limits))
        if item.category == "transactional":
            results.append(decision("external", "transactional_routing_unchanged"))
            continue
        if item.category in {"study", "rank"} and d1.reason(now):
            results.append(decision("suppress", d1.reason(now)))
            continue
        if not item.eligible:
            results.append(decision("suppress", "category_source_ineligible"))
            continue
        if item.reference in known:
            results.append(decision("suppress", "category_already_recorded"))
            continue
        if item.category == "weekly" and item.useful is not True:
            results.append(decision("suppress" if item.useful is False else "defer",
                                    "weekly_no_new_progress" if item.useful is False else "weekly_progress_unknown"))
            continue
        if now >= item.expires_at:
            # Useful weekly identity remains visible even when this proposed
            # window ended; no false delivery cursor or blind later post.
            results.append(decision("defer" if item.category=="weekly" else "suppress", "category_window_expired"))
            continue
        if calibration is None or "contact_window_over_limit" in coverage_limits:
            results.append(decision("defer", "coordination_unconfigured" if calibration is None else "coordination_history_incomplete"))
            continue
        slot = max(now, _aware_utc(item.due_at))
        collided = False
        try:
            for at in sorted(occupied):
                if abs(slot-at) < calibration.spacing:
                    collided = True
                    slot = at + calibration.spacing
        except OverflowError:
            results.append(decision("defer", "coordination_time_out_of_range"))
            continue
        if collided and item.category == "rank":
            results.append(decision("suppress", "rank_collision"))
        elif slot >= item.expires_at:
            results.append(decision("defer", "no_later_valid_window"))
        else:
            occupied.append(slot)
            results.append(decision("defer" if collided else "candidate",
                                    "category_collision" if collided else "shadow_category_candidate", slot))
    return tuple(results)


class CoordinationReader:
    """Authenticated diagnostic projection, with no transport or learning claim."""
    def __init__(self, session):
        self.session = session

    async def compare(self, actor, candidates, *, now, history_since, calibration=None):
        now, since = _aware_utc(now), _aware_utc(history_since)
        if since > now:
            raise ValueError("Explicit observation window required")
        with self.session.no_autoflush:
            pref = await SmartReminderPreferencesService(self.session).read(actor)
            account = (await self.session.execute(select(User.telegram_id, User.status, User.bot_blocked_at, User.level).where(
                User.id == actor.user_id))).mappings().one()
            d1 = await read_d1_scope(self.session, actor.user_id, now)
            profile = await self.session.scalar(select(CourseMiniAppProfile.notifications_enabled).where(
                CourseMiniAppProfile.user_id == actor.user_id))
            progress = (await self.session.execute(select(
                CourseProgress.last_reminder_sent_at, CourseProgress.last_weekly_progress_sent_at,
                CourseProgress.completed_lessons_count, CourseProgress.weekly_progress_baseline_lessons_count, CourseProgress.level,
            ).where(CourseProgress.user_id == actor.user_id))).mappings().one_or_none()
            mapping = {KEY_OVERTAKEN:"rank", **{key:"study" for key in (
                "lesson_time", KEY_SMART_STUDY, KEY_D1_RECOVERY, KEY_DAILY_GOAL, KEY_LESSON_UNFINISHED, KEY_STREAK)}}
            rows = (await self.session.execute(select(CourseUserNotification.id, CourseUserNotification.key,
                CourseUserNotification.dedupe_key, CourseUserNotification.created_at).where(
                    _owner(CourseUserNotification, actor.user_id, account["telegram_id"]),
                    CourseUserNotification.key.in_(mapping),
                    CourseUserNotification.created_at >= since, CourseUserNotification.created_at <= now,
                ).order_by(CourseUserNotification.created_at.desc(), CourseUserNotification.id.desc())
                .limit(MAX_CONTACTS + 1))).mappings().all()
            contacts = [Contact("feed:"+r["key"]+":"+(r["dedupe_key"] or str(r["id"])), mapping[r["key"]],
                                _utc(r["created_at"]), "feed_record") for r in rows[:MAX_CONTACTS] if r["key"] in mapping]
            if progress:
                for key, category in (("last_reminder_sent_at","study"),("last_weekly_progress_sent_at","weekly")):
                    instant = progress[key]
                    if instant is not None and since <= _utc(instant) <= now:
                        contacts.append(Contact("legacy:"+key+":"+_utc(instant).isoformat(), category,
                                                _utc(instant), "provider_return"))
            matching = progress is not None and bool(content_level(account["level"], default="")) and (
                content_level(account["level"], default="") == content_level(progress["level"], default=""))
            valid_counts = matching and all(type(progress[key]) is int and progress[key] >= 0 for key in (
                "completed_lessons_count", "weekly_progress_baseline_lessons_count")) and (
                    progress["weekly_progress_baseline_lessons_count"] <= progress["completed_lessons_count"])
            weekly_useful = (progress["completed_lessons_count"] > progress["weekly_progress_baseline_lessons_count"]
                             if valid_counts else None)
            tg = pref["channels"]["telegram"]
            phone = pref["channels"]["android"]
            study_config = pref["master_enabled"] is not False and (
                (tg["consent"]=="on" and tg["transport_available"]) or
                (phone["this_device_consent"]=="on" and phone["study_os_permission"]=="allowed"))
            legacy_weekly = account["status"]=="active" and bool(account["telegram_id"] and account["telegram_id"]>0) and account["bot_blocked_at"] is None
            adapted = tuple(replace(c, eligible=c.eligible and {
                "study":study_config,"rank":profile is True and tg["transport_available"],"weekly":legacy_weekly,"transactional":True,
            }.get(c.category,False), useful=weekly_useful if c.category=="weekly" else c.useful) for c in candidates)
            limits = ("legacy_contacts_incomplete",) + (("contact_window_over_limit",) if len(rows)>MAX_CONTACTS else ())
            return coordinate(adapted, now=now, contacts=contacts, d1=d1,
                              calibration=calibration, coverage_limits=limits), tuple(contacts), limits

"""Pure, deterministic study-time simulation. Nothing here grants delivery.

The context adapter supplies fresh canonical facts. No scheduler/API consumes
this policy yet; D09 habit confidence is deliberately unconfigured by default.
"""
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


POLICY_VERSION = "smart-shadow-v1"


@dataclass(frozen=True)
class VerifiedStudy:
    reference: str
    activity_type: str
    accepted_at: datetime
    course_day: str
    xp: int


@dataclass(frozen=True)
class HabitCalibration:
    """Explicit simulation input, not owner approval or a production setting."""
    version: str
    minimum_learning_days: int

    def __post_init__(self):
        if not self.version or type(self.minimum_learning_days) is not int or self.minimum_learning_days < 2:
            raise ValueError("Explicit version and multiple learning days required")


@dataclass(frozen=True)
class PolicyContext:
    observed_at: datetime
    level: str
    progress_level: str
    expected_level: str
    completed_parts: int
    total_parts: int
    target_allowed: bool
    foundation_required: bool
    revision: int
    grant_epoch: int
    master_enabled: bool | None
    permitted_channels: tuple[str, ...]
    timezone_name: str | None
    course_day: str | None
    daily_goal_xp: int | None
    plan_completed: bool | None
    studies: tuple[VerifiedStudy, ...] = ()
    coverage_limits: tuple[str, ...] = ()
    time_mode: str = "auto"
    manual_time: time | None = None
    saved_time: time | None = None
    channel_mode: str = "auto"
    preferred_channel: str | None = None
    quiet_start: time | None = None
    quiet_end: time | None = None
    pause_until: datetime | None = None


@dataclass(frozen=True)
class PolicyDecision:
    reason: str
    local_day: str | None
    level: str
    revision: int
    grant_epoch: int
    time_local: time | None
    time_source: str
    time_reason: str
    verified_today_xp: int
    goal_state: str
    plan_completed: bool | None
    coverage_limits: tuple[str, ...]
    target_lesson_order: int | None = None
    scheduled_at: datetime | None = None
    calibration_version: str | None = None
    policy_version: str = field(default=POLICY_VERSION, init=False)
    dispatch_allowed: bool = field(default=False, init=False)

    @property
    def candidate(self):
        return self.reason == "shadow_candidate"


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Policy instants must be timezone-aware")
    return value.astimezone(timezone.utc)


def _quiet(clock: time, start: time | None, end: time | None) -> bool:
    if start is None or end is None:
        return False
    if start == end:
        return True  # Malformed/legacy all-day restriction must not become ON.
    return start <= clock < end if start < end else clock >= start or clock < end


def _personal_time(context, studies, zone, calibration):
    if context.time_mode == "manual_locked":
        return context.manual_time, "manual", "manual_lock"
    if context.time_mode != "auto":
        return None, "unknown", "time_mode_unknown"
    fallback = (context.saved_time, "saved" if context.saved_time else "unknown")
    if calibration is None:
        return *fallback, "habit_threshold_unconfigured"
    if context.coverage_limits:
        return *fallback, "history_coverage_limited"
    # One vote per observed local learning day. Repeated practice/XP cannot
    # outweigh several days. Use an actual observed minute, not hour bins or
    # a linear average that turns 23:59 and 00:01 into noon.
    days = {}
    for study in sorted(studies, key=lambda s: (s.accepted_at, s.reference)):
        local = study.accepted_at.astimezone(zone)
        days.setdefault(local.date(), time(local.hour, local.minute))
    if len(days) < calibration.minimum_learning_days:
        return *fallback, "sparse_learning_days"
    votes = Counter(days.values()).most_common()
    if len(votes) > 1 and votes[0][1] == votes[1][1]:
        return *fallback, "habit_ambiguous"
    if votes[0][1] < calibration.minimum_learning_days:
        return *fallback, "sparse_matching_days"
    return votes[0][0], "habit", "observed_learning_minute"


def evaluate(context: PolicyContext, *, calibration: HabitCalibration | None = None) -> PolicyDecision:
    now = _aware_utc(context.observed_at)
    try:
        zone = ZoneInfo(context.timezone_name) if context.timezone_name else None
    except (ZoneInfoNotFoundError, ValueError):
        zone = None
    local_now = now.astimezone(zone) if zone else None
    local_day = local_now.date().isoformat() if local_now else None
    # Defend the pure boundary against duplicate, future and malformed samples.
    studies = {}
    for study in context.studies:
        accepted = _aware_utc(study.accepted_at)
        if (study.activity_type not in {"lesson", "test", "training"} or
                accepted > now or type(study.xp) is not int or study.xp <= 0):
            continue
        prior = studies.get(study.reference)
        if prior is not None and prior != study:
            raise ValueError("Conflicting verified study reference")
        studies[study.reference] = study
    samples = tuple(studies.values())
    verified_xp = sum(s.xp for s in samples if zone and context.course_day == local_day and
                      s.accepted_at.astimezone(zone).date().isoformat() == local_day and
                      s.course_day == context.course_day)
    goal_met = bool(context.daily_goal_xp and context.daily_goal_xp > 0 and
                    verified_xp >= context.daily_goal_xp)
    clock, source, time_reason = _personal_time(context, samples, zone, calibration) if zone else (
        context.manual_time if context.time_mode == "manual_locked" else context.saved_time,
        "manual" if context.time_mode == "manual_locked" else "saved" if context.saved_time else "unknown",
        "timezone_unknown",
    )

    def result(reason, *, target=None, scheduled=None):
        return PolicyDecision(
            reason=reason, local_day=local_day, level=context.level,
            revision=context.revision, grant_epoch=context.grant_epoch,
            time_local=clock, time_source=source, time_reason=time_reason,
            verified_today_xp=verified_xp, goal_state="met" if goal_met else "not_proven",
            plan_completed=context.plan_completed, coverage_limits=context.coverage_limits,
            target_lesson_order=target, scheduled_at=scheduled,
            calibration_version=calibration.version if calibration else None,
        )

    if context.master_enabled is False:
        return result("master_off")
    if context.channel_mode not in {"auto", "manual_locked"}:
        return result("channel_mode_unknown")
    if context.channel_mode == "manual_locked" and context.preferred_channel not in context.permitted_channels:
        return result("manual_channel_unavailable")
    if not context.permitted_channels:
        return result("consent_or_permission_unavailable")
    if not context.level or context.level != context.progress_level or context.level != context.expected_level:
        return result("course_context_changed")
    if context.pause_until and _aware_utc(context.pause_until) > now:
        return result("paused")
    if zone is None:
        return result("timezone_unknown")
    if context.course_day != local_day:
        return result("course_day_mismatch")
    if goal_met:
        return result("goal_completed")
    if context.plan_completed is True:
        return result("plan_completed")
    if context.total_parts <= 0 or not 0 <= context.completed_parts <= context.total_parts:
        return result("progress_unknown")
    if context.completed_parts == context.total_parts:
        return result("course_completed")
    if context.foundation_required:
        return result("foundation_required")
    if not context.target_allowed:
        return result("target_inaccessible")
    if clock is None:
        return result("personal_time_unknown")
    if ((context.quiet_start is None) != (context.quiet_end is None) or
            _quiet(local_now.time(), context.quiet_start, context.quiet_end) or
            _quiet(clock, context.quiet_start, context.quiet_end)):
        return result("personal_quiet")
    # Refuse gaps/folds rather than silently shifting a user's clock. Durable
    # reservation/travel ownership belongs to 3.3, not this simulation.
    naive = datetime.combine(date.fromisoformat(local_day), clock)
    instants = set()
    for fold in (0, 1):
        instant = naive.replace(tzinfo=zone, fold=fold).astimezone(timezone.utc)
        if instant.astimezone(zone).replace(tzinfo=None) == naive:
            instants.add(instant)
    if len(instants) != 1:
        return result("local_time_nonexistent" if not instants else "local_time_ambiguous")
    scheduled = next(iter(instants))
    if context.pause_until and _aware_utc(context.pause_until) > scheduled:
        return result("paused_at_personal_time")
    if scheduled < now:
        return result("personal_time_passed")
    return result("shadow_candidate", target=context.completed_parts + 1, scheduled=scheduled)

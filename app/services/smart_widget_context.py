"""Platform-neutral passive widget semantics. No auth, SQL, IO or send grant.

The native bridge authenticates the owner; adapters must enforce the envelope
and their local session epoch before rendering. Habit calibration is an
explicit caller input shared with the reminder policy. The authenticated passive
bridge supplies the owner-approved interval preset; no send authority follows.
"""
import json
from datetime import date, datetime, time
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.services.smart_reminder_policy import _aware_utc, _quiet, day_window, evaluate, local_time_instants


VERSION = 1
POLICY_VERSION = "smart-widget-context-v1"


class WidgetContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    version: Literal[1]
    epoch: str

    @field_validator("version", mode="before")
    @classmethod
    def exact_version(cls, value):
        if type(value) is not int or value != VERSION:
            raise ValueError("Unsupported widget context version")
        return value

    @field_validator("epoch")
    @classmethod
    def canonical_epoch(cls, value):
        if str(UUID(value)) != value:
            raise ValueError("Canonical per-link epoch required")
        return value


class WidgetContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    version: Literal[1] = VERSION
    policy_version: Literal["smart-widget-context-v1"] = POLICY_VERSION
    binding: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_epoch: str
    revision: int = Field(ge=0)
    generated_at: AwareDatetime
    valid_until: AwareDatetime
    level: str = Field(pattern=r"^(?:n?hsk)[1-4]$")
    track: Literal["hsk20", "hsk30"]
    local_day: str | None
    timezone_name: str | None
    completed_parts: int | None = Field(ge=0)
    total_parts: int | None = Field(gt=0)
    verified_today_xp: int | None = Field(ge=0)
    goal_xp: int | None = Field(gt=0)
    goal_state: Literal["met", "not_proven", "unknown"]
    plan_completed: bool | None
    time_local: str | None
    time_source: Literal["manual", "saved", "habit", "unknown"]
    time_reason: str
    phase: Literal["neutral", "before_study", "study_time_reached", "completed", "paused", "quiet", "unavailable"]
    reason: str
    action: Literal["course", "continue", "foundation", "none"]
    lesson_order: int | None = Field(gt=0)
    coverage_limits: tuple[str, ...] = ()
    calibration_version: str | None = None
    dispatch_allowed: Literal[False] = False
    action_requires_authorization: Literal[True] = True

    @field_validator("version", mode="before")
    @classmethod
    def exact_version(cls, value):
        return WidgetContextRequest.exact_version(value)

    @field_validator("request_epoch")
    @classmethod
    def canonical_epoch(cls, value):
        return WidgetContextRequest.canonical_epoch(value)

    @field_validator("dispatch_allowed", "action_requires_authorization", mode="before")
    @classmethod
    def exact_boolean(cls, value):
        # Literal[False/True] alone also accepts equal-valued JSON 0/1.
        if type(value) is not bool:
            raise ValueError("Boolean contract flag required")
        return value

    @model_validator(mode="after")
    def coherent(self):
        if self.generated_at >= self.valid_until:
            raise ValueError("Positive validity window required")
        if self.track != ("hsk30" if self.level.startswith("n") else "hsk20"):
            raise ValueError("Course track mismatch")
        if (self.local_day is None) != (self.timezone_name is None):
            raise ValueError("Day and zone binding required together")
        if self.local_day is not None:
            zone = ZoneInfo(self.timezone_name)
            if (date.fromisoformat(self.local_day).isoformat() != self.local_day or
                    self.generated_at.astimezone(zone).date().isoformat() != self.local_day or
                    self.valid_until > day_window(self.timezone_name, self.local_day)[1]):
                raise ValueError("Invalid authoritative day window")
        elif (self.verified_today_xp is not None or self.plan_completed is not None or
              self.goal_state != "unknown" or self.phase not in {"neutral", "unavailable"}):
            raise ValueError("Unknown day cannot assert personal daily state")
        if ((self.completed_parts is None) != (self.total_parts is None) or
                (self.completed_parts is not None and self.completed_parts > self.total_parts)):
            raise ValueError("Invalid course progress")
        if self.time_local is not None:
            clock = time.fromisoformat(self.time_local)
            if len(self.time_local) != 5 or clock.tzinfo or clock.second or clock.microsecond:
                raise ValueError("Minute clock required")
        if (self.time_local is None) != (self.time_source == "unknown"):
            raise ValueError("Time source mismatch")
        if self.action == "continue":
            if (self.completed_parts is None or self.lesson_order != self.completed_parts + 1 or
                    self.lesson_order > self.total_parts or self.phase == "unavailable"):
                raise ValueError("Invalid continuation target")
        elif self.lesson_order is not None:
            raise ValueError("Unexpected lesson target")
        if self.phase in {"before_study", "study_time_reached"} and self.time_local is None:
            raise ValueError("Personal phase requires a real time")
        if self.goal_state == "met" and not (self.goal_xp and self.verified_today_xp is not None and
                                             self.verified_today_xp >= self.goal_xp):
            raise ValueError("Goal completion requires verified learning")
        if self.phase == "completed" and not (self.goal_state == "met" or self.plan_completed is True or
                                               self.completed_parts == self.total_parts and self.total_parts is not None):
            raise ValueError("Completed phase requires completion facts")
        return self


def project_widget(context, *, request, binding, valid_until, calibration=None):
    """A current passive view; notification eligibility never becomes access."""
    now, end = _aware_utc(context.observed_at), _aware_utc(valid_until)
    if end <= now:
        raise ValueError("Authenticated context already expired")
    decision = evaluate(context, calibration=calibration, allow_elapsed_time=True)
    try:
        zone = ZoneInfo(context.timezone_name) if context.timezone_name else None
    except (ZoneInfoNotFoundError, ValueError):
        zone = None
    day = now.astimezone(zone).date().isoformat() if zone else None
    valid_course = bool(context.level and context.level == context.progress_level == context.expected_level and
                        context.total_parts > 0 and 0 <= context.completed_parts <= context.total_parts)
    valid_day = zone is not None and context.course_day == day
    if zone:
        end = min(end, day_window(context.timezone_name, day)[1])
    # Do not retain a semantic phase across any known personal boundary.
    if zone:
        for clock in (decision.time_local, context.quiet_start, context.quiet_end):
            if clock is not None:
                for boundary in local_time_instants(day, clock, zone):
                    if now < boundary:
                        end = min(end, boundary)
    if context.pause_until and now < _aware_utc(context.pause_until):
        end = min(end, _aware_utc(context.pause_until))
    clock = decision.time_local if valid_day else None
    if clock and (clock.second or clock.microsecond or clock.tzinfo):
        clock = None
    values = dict(
        binding=binding, request_epoch=request.epoch, revision=context.revision,
        generated_at=now, valid_until=end, level=context.level,
        track="hsk30" if context.level.startswith("n") else "hsk20",
        local_day=day if zone else None, timezone_name=context.timezone_name if zone else None,
        completed_parts=context.completed_parts if valid_course else None,
        total_parts=context.total_parts if valid_course else None,
        verified_today_xp=decision.verified_today_xp if valid_course and valid_day else None,
        goal_xp=context.daily_goal_xp if valid_course and context.daily_goal_xp and context.daily_goal_xp > 0 else None,
        goal_state=decision.goal_state if valid_course and valid_day else "unknown",
        plan_completed=context.plan_completed if valid_course and valid_day else None,
        time_local=clock.strftime("%H:%M") if clock else None,
        time_source=decision.time_source if clock else "unknown", time_reason=decision.time_reason,
        phase="neutral", reason="personal_time_unknown", action="course", lesson_order=None,
        coverage_limits=context.coverage_limits, calibration_version=decision.calibration_version,
    )
    def result(phase, reason, **extra):
        return WidgetContext(**(values | dict(phase=phase, reason=reason) | extra))
    if not valid_course:
        return result("unavailable", "course_context_changed", action="none")
    if not valid_day:
        return result("neutral", "timezone_unknown" if zone is None else "course_day_mismatch")
    if context.foundation_required:
        return result("neutral", "foundation_required", action="foundation")
    if decision.goal_state == "met" or context.plan_completed is True or context.completed_parts == context.total_parts:
        reason = "goal_completed" if decision.goal_state == "met" else (
            "plan_completed" if context.plan_completed is True else "course_completed")
        return result("completed", reason)
    if context.master_enabled is False:
        return result("neutral", "study_off")
    if context.pause_until and _aware_utc(context.pause_until) > now:
        return result("paused", "personal_pause")
    uncertain_quiet = any(len(local_time_instants(day, boundary, zone)) != 1
                          for boundary in (context.quiet_start, context.quiet_end) if boundary is not None)
    if ((context.quiet_start is None) != (context.quiet_end is None) or
            uncertain_quiet or
            _quiet(now.astimezone(zone).time(), context.quiet_start, context.quiet_end) or
            clock is not None and _quiet(clock, context.quiet_start, context.quiet_end)):
        return result("quiet", "personal_quiet")
    if not context.target_allowed:
        return result("neutral", "target_inaccessible")
    if clock is None:
        return result("neutral", "personal_time_unknown", action="continue", lesson_order=context.completed_parts + 1)
    instants = local_time_instants(day, clock, zone)
    if len(instants) != 1:
        return result("neutral", "local_time_nonexistent" if not instants else "local_time_ambiguous")
    before = now < next(iter(instants))
    return result("before_study" if before else "study_time_reached",
                  "before_personal_time" if before else "personal_time_reached",
                  action="continue", lesson_order=context.completed_parts + 1)


def widget_cache_reason(payload, *, now, binding, epoch, level, local_day, timezone_name,
                        minimum_revision=0, last_generated_at=None):
    """Reference adapter acceptance only. Rejection requires neutral/cleared UI.

    A valid envelope is still not a navigation, content or notification grant.
    The caller supplies CURRENT local bindings, never values read from payload.
    """
    try:
        view = WidgetContext.model_validate_json(json.dumps(payload), strict=True)
    except (ValidationError, ValueError, TypeError, KeyError, ZoneInfoNotFoundError):
        return "widget_context_invalid"
    now = _aware_utc(now)
    if view.binding != binding or view.request_epoch != epoch:
        return "widget_session_changed"
    if (view.level, view.local_day, view.timezone_name) != (level, local_day, timezone_name):
        return "widget_context_changed"
    if (view.revision < minimum_revision or
            last_generated_at is not None and view.generated_at < _aware_utc(last_generated_at)):
        return "widget_context_replayed"
    if view.generated_at > now:
        return "widget_context_future"
    if now >= view.valid_until:
        return "widget_context_expired"
    if timezone_name and now.astimezone(ZoneInfo(timezone_name)).date().isoformat() != local_day:
        return "widget_context_changed"
    return "widget_context_current"

"""Pure cadence/reactivation simulation; no runtime calibration or dispatch.

Positive study receipts establish an observed rhythm. Negative learning
coverage must come from a separately trustworthy, complete source. The legacy
reader cannot assert it. QA calibration values are never product defaults.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from fractions import Fraction
from statistics import median
from zoneinfo import ZoneInfo

from app.services.smart_reminder_policy import (
    PolicyContext, PolicyDecision, _aware_utc, evaluate,
)


@dataclass(frozen=True)
class CadenceCalibration:
    version: str
    minimum_learning_days: int
    abnormal_gap_multiplier: Fraction
    observation_multiplier: Fraction
    backoff_factor: int
    maximum_unsuccessful: int
    weekly_maximum: int

    def __post_init__(self):
        if not isinstance(self.version, str) or not self.version.strip():
            raise ValueError("Explicit simulation version required")
        for value, minimum in ((self.minimum_learning_days, 2), (self.backoff_factor, 2),
                               (self.maximum_unsuccessful, 1), (self.weekly_maximum, 1)):
            if type(value) is not int or value < minimum:
                raise ValueError("Explicit positive integer calibration required")
        if self.weekly_maximum > 7:
            raise ValueError("Weekly maximum cannot exceed the hard one-per-day bound")
        if (not isinstance(self.abnormal_gap_multiplier, Fraction) or self.abnormal_gap_multiplier <= 1 or
                not isinstance(self.observation_multiplier, Fraction) or self.observation_multiplier < 1):
            raise ValueError("Explicit rational gap/observation multipliers required")


@dataclass(frozen=True)
class StudyIntent:
    job_id: str
    user_id: int
    local_day: date
    timezone_name: str
    day_start_utc: datetime
    day_end_utc: datetime
    scheduled_at: datetime
    state: str
    externally_attempted: bool = False
    verified_shown_at: datetime | None = None
    definite_non_display: bool = False


@dataclass(frozen=True)
class CadenceContext:
    user_id: int
    policy: PolicyContext
    history_since: datetime
    intents: tuple[StudyIntent, ...] = ()
    ledger_complete: bool = False
    # Only a trustworthy authoritative outcome feed may assert this boundary.
    # The actual legacy reader always leaves it None, even for an empty query.
    learning_complete_since: datetime | None = None


@dataclass(frozen=True)
class CadenceDecision:
    reason: str
    eligibility: PolicyDecision
    observed_gap_days: Fraction | None = None
    abnormal_inactivity: bool | None = None
    unsuccessful_count: int | None = None
    next_eligible_at: datetime | None = None
    weekly_intents: int | None = None
    calibration_version: str | None = None
    policy_version: str = field(default="smart-cadence-shadow-v1", init=False)
    dispatch_allowed: bool = field(default=False, init=False)

    @property
    def candidate(self):
        return self.reason == "shadow_candidate"


_STATES = frozenset({"shadow", "pending", "claimed", "provider_accepted", "unknown",
                     "cancelled", "expired", "completed"})
_RESERVED = frozenset({"pending", "claimed", "provider_accepted", "unknown"})


def _after_days(instant, days):
    # Round fractional microseconds upward, never shorten a configured interval.
    micros = days * 86400 * 1000000
    rounded = -(-micros.numerator // micros.denominator)
    return instant + timedelta(microseconds=rounded)


def evaluate_cadence(context: CadenceContext, *, calibration: CadenceCalibration | None = None,
                     allow_elapsed_time: bool = False) -> CadenceDecision:
    base = evaluate(context.policy, allow_elapsed_time=allow_elapsed_time)
    gap = abnormal = misses = next_at = weekly = None

    def result(reason):
        return CadenceDecision(reason, base, gap, abnormal, misses, next_at, weekly,
                               calibration.version if calibration else None)

    if not base.candidate:
        return result(base.reason)
    if type(context.user_id) is not int or context.user_id <= 0:
        return result("cadence_owner_unknown")
    now, since = _aware_utc(context.policy.observed_at), _aware_utc(context.history_since)
    if since > now:
        return result("cadence_window_invalid")
    zone = ZoneInfo(context.policy.timezone_name)
    today = date.fromisoformat(base.local_day)
    start = datetime.combine(today, datetime.min.time(), zone).astimezone(now.tzinfo)
    end = datetime.combine(today + timedelta(days=1), datetime.min.time(), zone).astimezone(now.tzinfo)
    jobs = {}
    for job in context.intents:
        if job.user_id != context.user_id:
            return result("cadence_owner_mismatch")
        if job.job_id in jobs and jobs[job.job_id] != job:
            return result("cadence_ledger_conflict")
        jobs[job.job_id] = job
        lower, upper, scheduled = map(_aware_utc, (job.day_start_utc, job.day_end_utc, job.scheduled_at))
        if not job.job_id or job.state not in _STATES or not lower <= scheduled < upper:
            return result("cadence_ledger_invalid")
        if job.verified_shown_at is not None and (
                not job.externally_attempted or not scheduled <= _aware_utc(job.verified_shown_at) <= now):
            return result("cadence_ledger_invalid")
        if job.definite_non_display and (not job.externally_attempted or job.verified_shown_at is not None):
            return result("cadence_ledger_invalid")
        # Existing logical ownership survives OFF, expiry, endpoint and revision
        # changes. This gates NEW intents, not processing the existing job.
        if job.local_day == today or (lower < end and upper > start):
            return result("account_day_already_owned")
    if not context.ledger_complete:
        return result("cadence_ledger_incomplete")
    if calibration is None:
        return result("cadence_calibration_unconfigured")
    week_day = today - timedelta(days=6)
    week_start = datetime.combine(week_day, datetime.min.time(), zone).astimezone(now.tzinfo)
    if since > week_start:
        return result("weekly_budget_window_incomplete")
    week_jobs = [j for j in jobs.values() if week_start <= _aware_utc(j.scheduled_at) < end]
    if any(j.timezone_name != context.policy.timezone_name for j in week_jobs):
        return result("cadence_timezone_changed")
    weekly = sum(1 for j in week_jobs if j.externally_attempted or j.state in _RESERVED)
    if weekly >= calibration.weekly_maximum:
        return result("weekly_study_budget")
    # Receipt identity and original acceptance time win over replay. Never use
    # reward XP, opens, provider acceptance or future events as study.
    studies = {}
    for study in context.policy.studies:
        accepted = _aware_utc(study.accepted_at)
        if (study.activity_type not in {"lesson", "test", "training"} or
                type(study.xp) is not int or study.xp <= 0 or not since <= accepted <= now):
            continue
        # The base evaluator has already rejected conflicting original refs.
        studies[study.reference] = study
    days = sorted({s.accepted_at.astimezone(zone).date() for s in studies.values()})
    if context.policy.coverage_limits:
        return result("cadence_source_coverage_limited")
    if len(days) < calibration.minimum_learning_days:
        return result("sparse_learning_history")
    gap = median([Fraction((right-left).days) for left, right in zip(days, days[1:])])
    # Positive history can describe a rhythm. It cannot prove today's absence
    # or an unsuccessful reminder when legacy signals can undercount learning.
    if context.learning_complete_since is None or _aware_utc(context.learning_complete_since) > since:
        return result("learning_coverage_unknown")
    last_study = max(s.accepted_at for s in studies.values())
    abnormal = Fraction((today-days[-1]).days) > gap * calibration.abnormal_gap_multiplier
    # An unknown actual exposure time cannot be cleared by comparing a newer
    # study with the old *scheduled* time. Late delivery is still uncertain;
    # reconciliation/expiry fencing belongs to the reservation protocol.
    if any(j.externally_attempted and j.verified_shown_at is None and not j.definite_non_display
           for j in jobs.values()):
        return result("delivery_outcome_unknown")
    series = [j for j in jobs.values() if j.verified_shown_at is not None and
              _aware_utc(j.verified_shown_at) >= last_study]
    shown = sorted((_aware_utc(j.verified_shown_at) for j in series))
    if shown and shown[0] < since:
        return result("outcome_window_incomplete")
    try:
        observation_days = gap * calibration.observation_multiplier
        if any(_after_days(instant, observation_days) > now for instant in shown):
            return result("outcome_observation_pending")
        misses = len(shown)
        if misses >= calibration.maximum_unsuccessful:
            return result("reactivation_stopped")
        # Backoff is derived from the learner's own rhythm and actual shown
        # jobs; one alternate attempt never creates another unsuccessful job.
        anchor = shown[-1] if shown else last_study
        interval = gap * calibration.backoff_factor ** misses
        next_at = _after_days(anchor, interval)
    except OverflowError:
        return result("cadence_time_out_of_range")
    if base.scheduled_at < next_at:
        return result("personal_cadence_cooldown")
    return result("shadow_candidate")

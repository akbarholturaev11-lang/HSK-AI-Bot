"""Offline positive-study-time diagnostics. No DB, provider or serving authority."""
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from heapq import nsmallest
import json
import re
from math import atan2, cos, fsum, hypot, pi, sin
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.services.smart_reminder_policy import (
    APPROVED_HABIT_CALIBRATION, POLICY_VERSION, PolicyContext, VerifiedStudy,
    _aware_utc, _study_day_votes, evaluate,
)

VERSION = "smart-offline-time-v1"
FEATURE_VERSION = "smart-clock-features-v1"
MODEL_VERSION = "smart-circular-neighbors-v1"
MAX_ROWS = 4096
MAX_HISTORY = 128
RAW_LIFETIME = timedelta(days=90)
Key = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class OfflineError(ValueError):
    pass


class Snapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    learner_key: Key  # Export-specific salted pseudonym; never a canonical ID.
    platform: Literal["android", "telegram"]
    locale: Literal["uz", "ru", "tj"]
    context: PolicyContext
    history_available_at: Annotated[dict[Key, AwareDatetime | None], Field(max_length=MAX_HISTORY)]
    outcome: VerifiedStudy | None
    outcome_available_at: AwareDatetime | None


class Dataset(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    version: Literal["smart-offline-time-v1"]
    data_kind: Literal["synthetic", "reviewed_snapshot"]
    generated_at: AwareDatetime
    snapshots: Annotated[tuple[Snapshot, ...], Field(max_length=MAX_ROWS)]


@dataclass(frozen=True)
class Sample:
    owner: str
    platform: str
    locale: str
    time_source: str
    observed_at: datetime
    label_available_at: datetime
    features: tuple[float, ...]
    rule_clock: float
    target_clock: float


def _clock(value):
    return value.hour*60 + value.minute + value.second/60 + value.microsecond/60000000


def _phase(minute):
    angle = minute*2*pi/1440
    return sin(angle), cos(angle)


def clock_error(predicted, observed):
    return abs((predicted-observed+720) % 1440-720)


def _sample(row, generated_at, now):
    """Features are finalized before inspecting the held-out outcome."""
    context = row.context
    observed = _aware_utc(context.observed_at)
    if observed > generated_at:
        return None, "future_snapshot"
    if observed <= now-RAW_LIFETIME:
        return None, "expired_snapshot"
    if len(context.studies) > MAX_HISTORY:
        raise OfflineError("offline_history_too_large")
    references = {study.reference for study in context.studies}
    if any(not re.fullmatch(r"[0-9a-f]{64}", ref) for ref in references) or (
            row.outcome is not None and not re.fullmatch(r"[0-9a-f]{64}", row.outcome.reference)):
        raise OfflineError("offline_reference_invalid")
    if references != set(row.history_available_at):
        raise OfflineError("offline_history_binding_invalid")
    for study in context.studies:
        available = row.history_available_at[study.reference]
        accepted = _aware_utc(study.accepted_at)
        if available is None or accepted > available or available > observed:
            return None, "history_not_available_at_decision"
        if accepted <= now-RAW_LIFETIME:
            return None, "expired_history"
    if context.coverage_limits:
        return None, "history_coverage_limited"
    if context.time_mode != "auto":
        return None, "manual_or_unknown_time"
    if any(clock is not None and clock.tzinfo is not None for clock in (
            context.saved_time, context.manual_time, context.quiet_start, context.quiet_end)):
        raise OfflineError("offline_local_clock_invalid")
    if set(context.permitted_channels)-{"android", "telegram"}:
        raise OfflineError("offline_channel_invalid")
    decision = evaluate(context, calibration=APPROVED_HABIT_CALIBRATION, allow_elapsed_time=True)
    if not decision.candidate:
        return None, decision.reason
    zone = ZoneInfo(context.timezone_name)
    recent, extended = _study_day_votes(context, context.studies, zone, APPROVED_HABIT_CALIBRATION)
    days = recent if len(recent) >= APPROVED_HABIT_CALIBRATION.minimum_learning_days else extended
    today = observed.astimezone(zone).date()
    clock = _clock(decision.time_local)
    count = len(days)
    gap = min(90, (today-max(days)).days) if days else 90
    concentration = hypot(fsum(_phase(v)[0] for v in days.values()),
                          fsum(_phase(v)[1] for v in days.values()))/count if count else 0.0
    weekday = today.weekday()*2*pi/7
    features = (*_phase(clock), sin(weekday), cos(weekday), count/90, gap/90, concentration)
    outcome, ready = row.outcome, row.outcome_available_at
    if outcome is None or ready is None:
        return None, "positive_outcome_unobserved"
    accepted = _aware_utc(outcome.accepted_at)
    if (outcome.activity_type not in {"lesson", "test", "training"} or outcome.xp <= 0 or
            outcome.reference in references or not observed < accepted <= ready <= generated_at or
            accepted.astimezone(zone).date() != today or outcome.course_day != today.isoformat()):
        return None, "positive_outcome_unverified"
    return Sample(row.learner_key, row.platform, row.locale, decision.time_source, observed, ready,
                  features, clock, _clock(accepted.astimezone(zone))), None


class CircularNeighbors:
    """Shared nonparametric regressor; retained training records never leave RAM."""
    def __init__(self, samples, neighbors):
        self.samples = tuple(samples)
        self.neighbors = min(neighbors, len(self.samples))

    def predict(self, features):
        if not self.samples:
            return None
        distances = [(fsum((a-b)**2 for a,b in zip(features,s.features)), s.target_clock)
                     for s in self.samples]
        boundary = nsmallest(self.neighbors, (distance for distance,_ in distances))[-1]
        # Include all boundary ties: no owner, row order or target chooses a neighbor.
        angles = [_phase(clock) for distance,clock in distances if distance <= boundary]
        y, x = fsum(a for a,_ in angles), fsum(b for _,b in angles)
        if hypot(y,x) <= 1e-12*len(angles):
            return None
        return (atan2(y,x)*1440/(2*pi)) % 1440


def _metrics(rows, training, minimum_accounts):
    owners = {s.owner for s,_,_,_ in rows}
    trained_owners = {s.owner for s in training}
    status = ("available" if len(owners) >= minimum_accounts and len(trained_owners) >= minimum_accounts
              else "insufficient_coverage")
    result = {"status":status,"observations":len(rows),"accounts":len(owners),
              "training_accounts":len(trained_owners),"rules_mae_minutes":None,
              "model_mae_minutes":None,"model_minus_rules_minutes":None,"model_fallbacks":None}
    if status == "available":
        errors = defaultdict(lambda: [[], []])
        for sample,rule_error,model_error,_ in rows:
            errors[sample.owner][0].append(rule_error)
            errors[sample.owner][1].append(model_error)
        def macro(index):
            return fsum(fsum(pair[index])/len(pair[index]) for pair in errors.values())/len(errors)
        rules, model = macro(0), macro(1)
        result.update(rules_mae_minutes=round(rules,6), model_mae_minutes=round(model,6),
            model_minus_rules_minutes=round(model-rules,6),model_fallbacks=sum(fallback for *_,fallback in rows))
    return result


def evaluate_dataset(dataset, *, cutoff, minimum_accounts, neighbors=5, now):
    """Time-ordered held-out diagnostic only; every readiness/dispatch flag is false."""
    now, cutoff = _aware_utc(now), _aware_utc(cutoff)
    if (type(minimum_accounts) is not int or not 2 <= minimum_accounts <= MAX_ROWS or
            type(neighbors) is not int or not 1 <= neighbors <= 64):
        raise OfflineError("offline_configuration_invalid")
    generated = _aware_utc(dataset.generated_at)
    if not now-RAW_LIFETIME < generated <= now or not now-RAW_LIFETIME < cutoff < generated:
        raise OfflineError("offline_window_invalid")
    excluded, train, test = Counter(), [], []
    owner_days, outcomes, proofs = set(), set(), {}
    for row in dataset.snapshots:
        if len(row.context.studies) > MAX_HISTORY:
            raise OfflineError("offline_history_too_large")
        observations = [(s,row.history_available_at.get(s.reference)) for s in row.context.studies]
        if row.outcome is not None:
            observations.append((row.outcome,row.outcome_available_at))
        for study,available in observations:
            identity = row.learner_key, study.reference
            fact = study.activity_type, _aware_utc(study.accepted_at), study.course_day, study.xp, available
            prior = proofs.get(identity)
            if prior is not None and (prior[:4] != fact[:4] or
                    prior[4] is not None and available is not None and prior[4] != available):
                raise OfflineError("offline_conflicting_proof")
            proofs[identity] = prior if prior is not None and available is None else fact
        observed = _aware_utc(row.context.observed_at)
        try:
            day = observed.astimezone(ZoneInfo(row.context.timezone_name)).date().isoformat()
        except (ValueError, TypeError, KeyError):
            excluded["timezone_unknown"] += 1
            continue
        identity = row.learner_key, day
        if identity in owner_days:
            raise OfflineError("offline_duplicate_account_day")
        owner_days.add(identity)
        if row.outcome is not None:
            identity = row.learner_key, row.outcome.reference
            if identity in outcomes:
                raise OfflineError("offline_duplicate_outcome")
            outcomes.add(identity)
        sample, reason = _sample(row, generated, now)
        if reason:
            excluded[reason] += 1
        elif observed >= cutoff:
            test.append(sample)
        elif sample.label_available_at < cutoff:
            train.append(sample)
        else:
            excluded["training_label_not_available"] += 1
    model = CircularNeighbors(train, neighbors)
    scores = []
    for sample in test:
        prediction = model.predict(sample.features)
        fallback = prediction is None
        prediction = sample.rule_clock if fallback else prediction
        scores.append((sample, clock_error(sample.rule_clock,sample.target_clock),
                       clock_error(prediction,sample.target_clock), fallback))
    overall = _metrics(scores,train,minimum_accounts)
    cohorts = {}
    for dimension,values in (("platform",("android","telegram")),("locale",("uz","ru","tj")),
                             ("time_source",("saved","habit"))):
        cohorts[dimension] = {value:_metrics([r for r in scores if getattr(r[0],dimension)==value],
            [s for s in train if getattr(s,dimension)==value],minimum_accounts) for value in values}
    trained_owners = {s.owner for s in train}
    cohorts["platform_locale"] = {platform+"/"+locale:_metrics(
        [r for r in scores if (r[0].platform,r[0].locale)==(platform,locale)],
        [s for s in train if (s.platform,s.locale)==(platform,locale)],minimum_accounts)
        for platform in ("android","telegram") for locale in ("uz","ru","tj")}
    cohorts["learner_history"] = {name:_metrics([r for r in scores if (r[0].owner in trained_owners)==seen],
        train,minimum_accounts) for name,seen in (("seen",True),("unseen",False))}
    canonical = json.dumps(dataset.model_dump(mode="json"),sort_keys=True,separators=(",",":"))
    return {"version":VERSION,"feature_version":FEATURE_VERSION,"model_version":MODEL_VERSION,
        "baseline_version":POLICY_VERSION,"habit_version":APPROVED_HABIT_CALIBRATION.version,
        "data_kind":dataset.data_kind,"input_sha256":sha256(canonical.encode()).hexdigest(),
        "generated_at":generated.isoformat(),"cutoff":cutoff.isoformat(),"neighbors":neighbors,
        "minimum_group_accounts":minimum_accounts,"training_observations":len(train),
        "test_observations":len(test),"excluded":dict(sorted(excluded.items())),
        "metric":"account_macro_circular_minutes_on_observed_positive_completions",
        "overall":overall,"cohorts":cohorts,"ml_ready":False,"dispatch_allowed":False,
        "learning_benefit":"unavailable_requires_real_baseline_and_registered_experiment"}

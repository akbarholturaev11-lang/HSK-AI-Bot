"""Source-derived analysis; never dispatch authority, causal or display proof.

Capture owns a separate transaction after delivery commits. Optional source
hooks/retention are disabled by default. Retention never deletes source evidence.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import asyncio
import hashlib
import logging
import math

from sqlalchemy import and_, delete, func, or_, select, text, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.models.account_deletion import AccountDeletionRequest
from app.db.models.smart_reminder import SmartReminderAndroidGrant, SmartReminderAttempt, SmartReminderJob
from app.db.models.smart_reminder_analysis import SmartReminderAnalysisEvent, SmartReminderAnalysisMonthly, SmartReminderReservationObservation
from app.db.models.user import User
from app.services.smart_reminder_policy import _aware_utc, day_window
from app.services.smart_reminder_preferences import _utc
from app.services.smart_reminder_shadow_queue import QUEUE_VERSION, ReservationObservation

EVENT = SmartReminderAnalysisEvent.__table__
MONTHLY = SmartReminderAnalysisMonthly.__table__
RESERVATION = SmartReminderReservationObservation.__table__
RAW_RETENTION = timedelta(days=90)  # Owner D21; not operational grant/day/OFF retention.
RETURN_WINDOW = timedelta(hours=24)  # Owner-selected elapsed measurement window, not cadence.
MAX_BATCH = 128  # Bounded work, not product cadence or experiment calibration.
UNAVAILABLE_OUTCOMES = ("verified_shown", "read", "opened", "attributed_server_learning")
logger = logging.getLogger(__name__)

# Reviewed server reasons only. Unknown/new codes require a source review,
# never persist arbitrary job text into analysis.
SHADOW_CADENCE_REASONS = frozenset({
    "shadow_candidate", "cadence_owner_unknown", "cadence_window_invalid", "cadence_owner_mismatch",
    "cadence_ledger_conflict", "cadence_ledger_invalid", "account_day_already_owned", "cadence_ledger_incomplete",
    "cadence_calibration_unconfigured", "weekly_budget_window_incomplete", "cadence_timezone_changed",
    "weekly_study_budget", "cadence_source_coverage_limited", "sparse_learning_history", "learning_coverage_unknown",
    "delivery_outcome_unknown", "outcome_window_incomplete", "outcome_observation_pending", "reactivation_stopped",
    "cadence_time_out_of_range", "personal_cadence_cooldown",
})
SHADOW_REFUSAL_REASONS = frozenset({
    "master_off", "channel_mode_unknown", "manual_channel_unavailable", "consent_or_permission_unavailable",
    "course_context_changed", "paused", "timezone_unknown", "course_day_mismatch", "goal_completed", "plan_completed",
    "progress_unknown", "course_completed", "foundation_required", "target_inaccessible", "personal_time_unknown",
    "personal_quiet", "local_time_nonexistent", "local_time_ambiguous", "paused_at_personal_time", "personal_time_passed",
    "queue_history_incomplete", "shadow_preference_changed", "shadow_context_changed",
    "d1_assignment_unknown", "d1_holdout_active", "study_off", "device_revoked", "session_logout", "refresh_reuse",
    "android_study_capability_lost",
})
RESERVATION_REFUSALS = SHADOW_REFUSAL_REASONS | {"queue_expiry_outside_day", "account_day_already_owned"}
COMMON_GUARD_REASONS = (SHADOW_REFUSAL_REASONS | SHADOW_CADENCE_REASONS | {
    "legacy_contact_unknown", "legacy_study_already_attempted", "routing_held", "routing_review_expired",
}) - {"shadow_candidate"}
TERMINAL_GUARD_REASONS = {
    "android": COMMON_GUARD_REASONS | {"android_job_expired", "android_study_unavailable",
        "personal_quiet_clock_uncertain", "android_expired_before_response", "client_declined_before_post"},
    "telegram": COMMON_GUARD_REASONS | {"telegram_expired", "telegram_content_owner_changed",
        "telegram_content_target_invalid", "telegram_template_disabled", "telegram_template_invalid"},
}
# Missing-calibration is an early native gate, with no terminal source write.
ANDROID_GUARD_CAPTURE = TERMINAL_GUARD_REASONS["android"] - {"cadence_calibration_unconfigured"}


def _shadow_stage(job):
    if (job["selected_channel"] is not None or job["selected_device_id"] is not None or job["lease_token"] is not None):
        return None
    reason, state = job["reason_code"], job["state"]
    if state == "completed" and reason in SHADOW_CADENCE_REASONS:
        return "shadow_candidate" if reason == "shadow_candidate" else "shadow_suppressed"
    if (state == "cancelled" and reason in SHADOW_REFUSAL_REASONS) or (state == "expired" and reason == "shadow_expired"):
        return "shadow_suppressed"


@dataclass(frozen=True)
class AnalysisSourcePage:
    sources: tuple[tuple[int, str], ...]
    has_more: bool


@dataclass(frozen=True)
class TargetLearningEvidence:
    """Partial temporal study/report evidence; never causal or inactivity proof."""
    reason: str
    boundary_at: datetime | None = None
    learned_at: datetime | None = None
    coverage_limits: tuple[str, ...] = (
        "reviewed_learning_sources_only", "independent_open_unavailable",
        "causal_attribution_unavailable", "negative_learning_coverage_unknown",
    )
    reported_open_at: datetime | None = None
    first_study_at: datetime | None = None
    first_study_after_report_at: datetime | None = None
    verified_study_count: int | None = None
    first_active_study_at: datetime | None = None
    first_active_study_after_report_at: datetime | None = None


@dataclass(frozen=True)
class ReturnLearningEvidence:
    """Positive temporal contact evidence; never causal or complete coverage."""
    reason: str
    contact_at: datetime | None = None
    window_end_at: datetime | None = None
    first_study_at: datetime | None = None
    verified_study_count: int | None = None
    window_elapsed: bool | None = None
    coverage_limits: tuple[str, ...] = (
        "reviewed_learning_sources_only", "negative_learning_coverage_unknown",
        "causal_attribution_unavailable", "primary_cohort_metrics_unavailable",
    )


def _event_key(source_id, stage):
    return hashlib.sha256(("smart-analysis-v1:" + source_id + ":" + stage).encode()).hexdigest()


def oldest_month(now):
    """Current UTC month and eleven earlier buckets; never unbounded history."""
    serial = now.year * 12 + now.month - 1 - 11
    year, month = divmod(serial, 12)
    return now.date().replace(year=year, month=month + 1, day=1)


class SmartReminderAnalysisService:
    def __init__(self, sessions, *, clock=None):
        self.sessions = sessions
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def now(self):
        return _aware_utc(self.clock())

    async def target_learning(self, user_id, job_id):
        """Internal partial source projection; never a policy or causal window."""
        return await self._owned_learning(user_id, job_id, return_window=False)

    async def return_learning(self, user_id, job_id):
        """Internal 24-hour positive study projection, independent of tapping."""
        return await self._owned_learning(user_id, job_id, return_window=True)

    async def _owned_learning(self, user_id, job_id, *, return_window):
        unavailable = ReturnLearningEvidence if return_window else TargetLearningEvidence
        if (type(user_id) is not int or user_id <= 0 or not isinstance(job_id, str) or
                not 1 <= len(job_id) <= 36):
            raise ValueError("Owned Smart job identity required")
        async with self.sessions.begin() as session:
            with session.no_autoflush:
                if session.bind.dialect.name == "postgresql":
                    await session.execute(text("SET LOCAL statement_timeout = '5000'"))
                owner = (await session.execute(select(User.id, User.status).where(
                    User.id == user_id).with_for_update())).one_or_none()
                if owner is None or owner.status == "blocked" or await session.scalar(
                        select(AccountDeletionRequest.id).where(AccountDeletionRequest.status == "submitted",
                            or_(AccountDeletionRequest.user_id == user_id,
                                AccountDeletionRequest.active_user_id == user_id)).limit(1)) is not None:
                    return unavailable("learning_owner_unavailable")
                job = (await session.execute(select(SmartReminderJob.__table__).where(
                    SmartReminderJob.user_id == user_id, SmartReminderJob.id == job_id))).mappings().one_or_none()
                if job is None:
                    return unavailable("learning_job_unavailable")
                attempts = (await session.execute(select(SmartReminderAttempt.__table__).where(
                    SmartReminderAttempt.job_id == job_id).order_by(SmartReminderAttempt.id)
                    .limit(MAX_BATCH + 1))).mappings().all()
                grants = (await session.execute(select(SmartReminderAndroidGrant.__table__).where(
                    SmartReminderAndroidGrant.user_id == user_id, SmartReminderAndroidGrant.job_id == job_id)
                    .limit(MAX_BATCH + 1))).mappings().all() if job["selected_channel"] == "android" else []
                reader = self._return_evidence if return_window else self._learning_evidence
                return (await reader(session, job, attempts, grants, self.now()))[0]

    @staticmethod
    def _contact_scope(job, attempts, grants, now):
        """Identical original contact proof for local-day and 24-hour analysis."""
        from app.services.smart_reminder_policy_context import _LESSON_REF
        def unavailable(reason):
            return None, None, {}, reason
        channel = job["selected_channel"]
        if channel not in {"android", "telegram"} or not job["policy_version"].startswith("smart-" + channel + "-v1:"):
            return unavailable("learning_source_unsupported")
        reference = f"v3-part:{job['course_key']}:{job['lesson_order']}:complete"
        if _LESSON_REF.fullmatch(reference) is None:
            return unavailable("learning_target_unavailable")
        try:
            start, end = day_window(job["timezone_name"], job["local_day"].isoformat())
        except (KeyError, TypeError, ValueError):
            return unavailable("learning_window_unavailable")
        if (start != _utc(job["day_start_utc"]) or end != _utc(job["day_end_utc"]) or
                end <= now - RAW_RETENTION or now < start):
            return unavailable("learning_window_unavailable")
        if len(attempts) > MAX_BATCH or len(grants) > MAX_BATCH:
            return unavailable("learning_source_over_limit")
        boundaries = {}
        for attempt in attempts:
            if (attempt["channel"] != channel or attempt["grant_epoch"] != job["grant_epoch"] or
                    attempt["started_at"] is None or attempt["resolved_at"] is None):
                continue
            at, resolved = _utc(attempt["started_at"]), _utc(attempt["resolved_at"])
            if (not now - RAW_RETENTION < at <= resolved <= now or
                    not start <= at < end or
                    not _utc(job["scheduled_at"]) <= at < _utc(job["expires_at"]) or
                    not _utc(job["created_at"]) <= _utc(attempt["prepared_at"]) <= at < _utc(attempt["expires_at"])):
                continue
            if channel == "telegram" and attempt["state"] == "provider_accepted":
                boundaries[attempt["id"]] = at
            elif channel == "android" and attempt["state"] == "client_posted_unverified":
                if any(g["attempt_id"] == attempt["id"] and
                        g["device_id"] == attempt["device_id"] == job["selected_device_id"] and
                        g["policy_version"] == job["policy_version"] and g["grant_epoch"] == job["grant_epoch"] and
                        g["preference_revision"] == job["preference_revision"] and
                        _utc(g["expires_at"]) == _utc(attempt["expires_at"]) and g["receipt_id"] is not None and
                        g["receipt_outcome"] == "client_posted_unverified" and g["received_at"] is not None and
                        at == _utc(g["issued_at"]) <= _utc(g["received_at"]) == resolved for g in grants):
                    boundaries[attempt["id"]] = at
        if not boundaries:
            return unavailable("learning_contact_unconfirmed")
        return start, end, boundaries, None

    async def _learning_evidence(self, session, job, attempts, grants, now):
        """Reuse the same owned, locked source scope for projection and capture."""
        from app.services.smart_reminder_policy_context import read_scored_activity, read_verified_learning
        start, end, boundaries, reason = self._contact_scope(job, attempts, grants, now)
        if reason is not None:
            return TargetLearningEvidence(reason), ()
        channel = job["selected_channel"]
        reference = f"v3-part:{job['course_key']}:{job['lesson_order']}:complete"
        boundary = min(boundaries.values())
        evidence = await read_verified_learning(session, job["user_id"], level=job["course_key"],
            history_since=start, observed_at=min(now, end))
        studies = tuple(sorted((s for s in evidence.studies if boundary < s.accepted_at < end and
            s.accepted_at <= now), key=lambda s: (s.accepted_at, s.reference)))
        keys = {_event_key(aid, "client_reported_open"): at for aid, at in boundaries.items()}
        reports = (await session.execute(select(EVENT.c.event_key, EVENT.c.occurred_at, EVENT.c.expires_at).where(
            EVENT.c.user_id == job["user_id"], EVENT.c.job_id == job["id"], EVENT.c.stage == "client_reported_open",
            EVENT.c.channel == channel, EVENT.c.reason_code == "authenticated_client_report",
            EVENT.c.event_key.in_(tuple(keys)), EVENT.c.occurred_at >= boundary, EVENT.c.occurred_at < end,
            EVENT.c.occurred_at <= now, EVENT.c.expires_at > now).limit(MAX_BATCH))).all()
        valid_reports = [_utc(r.occurred_at) for r in reports if keys[r.event_key] <= _utc(r.occurred_at) and
            _utc(r.expires_at) == _utc(r.occurred_at) + RAW_RETENTION]
        reported = min(valid_reports) if valid_reports else None
        activity = await read_scored_activity(session, job["user_id"], level=job["course_key"],
            history_since=boundary, observed_at=min(now, end))
        active = sorted({s.accepted_at for s in studies} | {
            at for at in activity.times if boundary < at < end and at <= now})
        active_after_report = [at for at in active if reported is not None and at > reported]
        targets = [s.accepted_at for s in studies if s.reference == reference]
        after_report = [s.accepted_at for s in studies if reported is not None and s.accepted_at > reported]
        limits = tuple(sorted(set(TargetLearningEvidence("").coverage_limits) |
            set(evidence.coverage_limits) | set(activity.coverage_limits)))
        return TargetLearningEvidence("verified_target_learning_after_attempt" if targets else
            "target_learning_unavailable", boundary, min(targets) if targets else None, limits,
            reported_open_at=reported, first_study_at=studies[0].accepted_at if studies else None,
            first_study_after_report_at=min(after_report) if after_report else None,
            verified_study_count=len(studies) if studies else None,
            first_active_study_at=active[0] if active else None,
            first_active_study_after_report_at=active_after_report[0] if active_after_report else None), studies

    async def _return_evidence(self, session, job, attempts, grants, now):
        from app.services.smart_reminder_policy_context import read_scored_activity, read_verified_learning
        start, _day_end, boundaries, reason = self._contact_scope(job, attempts, grants, now)
        if reason is not None:
            return ReturnLearningEvidence(reason), ()
        boundary = min(boundaries.values())
        end = boundary + RETURN_WINDOW
        observed = min(now, end)
        learning = await read_verified_learning(session, job["user_id"], level=job["course_key"],
            history_since=start, observed_at=observed, evidence_at=now)
        activity = await read_scored_activity(session, job["user_id"], level=job["course_key"],
            history_since=boundary, observed_at=observed)
        studies = tuple(sorted((s for s in learning.studies if boundary < s.accepted_at <= observed),
            key=lambda s: (s.accepted_at, s.reference)))
        active = sorted({s.accepted_at for s in studies} | {
            at for at in activity.times if boundary < at <= observed})
        limits = tuple(sorted(set(ReturnLearningEvidence("").coverage_limits) |
            set(learning.coverage_limits) | set(activity.coverage_limits)))
        return ReturnLearningEvidence("verified_study_within_24h" if active else "return_learning_unavailable",
            contact_at=boundary, window_end_at=end, first_study_at=active[0] if active else None,
            verified_study_count=len(studies) if studies else None, window_elapsed=now >= end,
            coverage_limits=limits), studies

    @staticmethod
    def _insert(session, table):
        dialect = session.bind.dialect.name
        if dialect not in {"sqlite", "postgresql"}:
            raise RuntimeError("Unsupported Smart analysis dialect")
        return (pg_insert if dialect == "postgresql" else sqlite_insert)(table)

    async def _fact(self, session, job, source_id, stage, at, channel, now, *, reason=None):
        if at is None or channel not in {"none", "telegram", "android"}:
            return 0
        at = _utc(at)
        if not now - RAW_RETENTION < at <= now:
            return 0  # Expired replay cannot resurrect detail or increment totals.
        key = _event_key(source_id, stage)
        inserted = await session.scalar(self._insert(session, EVENT).values(user_id=job["user_id"],
            event_key=key, job_id=job["id"], stage=stage, channel=channel,
            reason_code=reason or "stored_" + stage, occurred_at=at, expires_at=at + RAW_RETENTION)
            .on_conflict_do_nothing(index_elements=["user_id", "event_key"]).returning(EVENT.c.event_key))
        if inserted is None:
            return 0
        month = at.date().replace(day=1)
        await session.execute(self._insert(session, MONTHLY).values(month=month, stage=stage,
            channel=channel, fact_count=1).on_conflict_do_update(index_elements=["month", "stage", "channel"],
                set_={"fact_count": MONTHLY.c.fact_count + 1}))
        return 1

    async def capture_job(self, user_id, job_id):
        """Internal committed-source capture. No client event/outcome input."""
        async with self.sessions.begin() as session:
            with session.no_autoflush:
                owner_row = (await session.execute(select(User.id, User.status).where(
                    User.id == user_id).with_for_update())).one_or_none()
                if owner_row is None:
                    return 0
                owner = owner_row.id
                pending = await session.scalar(select(AccountDeletionRequest.id).where(
                    AccountDeletionRequest.status == "submitted", or_(AccountDeletionRequest.user_id == owner,
                        AccountDeletionRequest.active_user_id == owner)).limit(1))
                if pending is not None:
                    return 0
                job = (await session.execute(select(SmartReminderJob.__table__).where(
                    SmartReminderJob.id == job_id, SmartReminderJob.user_id == owner).with_for_update())).mappings().one_or_none()
                if job is None:
                    return 0
                # Shadow terminal decisions have their own explicit stages;
                # they never become delivery or negative-learning evidence.
                channel = job["selected_channel"]
                shadow = job["policy_version"] == QUEUE_VERSION
                if not shadow and (channel not in {"android", "telegram"} or not job["policy_version"].startswith(
                        "smart-" + channel + "-v1:")):
                    return 0
                attempts = (await session.execute(select(SmartReminderAttempt.__table__).where(
                    SmartReminderAttempt.job_id == job_id).order_by(SmartReminderAttempt.id).with_for_update())).mappings().all()
                if shadow:
                    if not attempts and owner_row.status != "blocked":
                        from app.services.smart_reminder_baseline import enroll_baseline
                        await enroll_baseline(session, owner, self.now(), self._insert)
                    stage = _shadow_stage(job)
                    if attempts or stage is None:
                        return 0
                    return await self._fact(session, job, job_id, stage, job["updated_at"], "none", self.now(),
                        reason=job["reason_code"])
                grants = (await session.execute(select(SmartReminderAndroidGrant.__table__).where(
                    SmartReminderAndroidGrant.job_id == job_id, SmartReminderAndroidGrant.user_id == owner))).mappings().all()
                now = self.now()  # Resample after waiting on the canonical owner.
                count = await self._fact(session, job, job_id, "reserved", job["created_at"],
                    job["selected_channel"] or "none", now)
                if job["state"] in {"cancelled", "expired"}:
                    reason = job["reason_code"] if job["reason_code"] in TERMINAL_GUARD_REASONS[channel] else None
                    count += await self._fact(session, job, job_id, job["state"], job["updated_at"],
                        job["selected_channel"] or "none", now, reason=reason)
                for attempt in attempts:
                    count += await self._fact(session, job, attempt["id"], "in_flight",
                        attempt["started_at"], attempt["channel"], now)
                    stage = {"provider_accepted": "provider_accepted", "unknown": "outcome_unknown",
                        "definite_failure": "definite_failure"}.get(attempt["state"])
                    if attempt["channel"] == "android":
                        grant = next((g for g in grants if g["attempt_id"] == attempt["id"] and
                            g["device_id"] == attempt["device_id"] and g["receipt_id"] is not None), None)
                        if grant is not None:
                            expected = {"client_declined_before_post": "confirmed_not_displayed",
                                "client_posted_unverified": "client_posted_unverified", "client_outcome_unknown": "unknown"}
                            if expected.get(grant["receipt_outcome"]) == attempt["state"]:
                                stage = "outcome_unknown" if attempt["state"] == "unknown" else attempt["state"]
                                count += await self._fact(session, job, attempt["id"], stage,
                                    grant["received_at"], "android", now)
                                continue
                    if stage is not None:
                        count += await self._fact(session, job, attempt["id"], stage,
                            attempt["resolved_at"], attempt["channel"], now)
                if owner_row.status != "blocked":
                    evidence, studies = await self._learning_evidence(session, job, attempts, grants, now)
                    # One positive day per owned job's immutable local-day scope,
                    # not one day per question/attempt/XP. Reports are secondary.
                    for stage, at in (("study_day_after_attempt", evidence.first_active_study_at),
                                      ("study_day_after_report", evidence.first_active_study_after_report_at)):
                        count += await self._fact(session, job, "study-day:" + job_id, stage,
                            at, channel, now, reason="verified_server_activity")
                    for study in studies:
                        source = "study:" + job_id + ":" + study.reference
                        count += await self._fact(session, job, source, "verified_study_after_attempt",
                            study.accepted_at, channel, now, reason="original_server_result")
                        if evidence.reported_open_at is not None and study.accepted_at > evidence.reported_open_at:
                            count += await self._fact(session, job, source, "verified_study_after_report",
                                study.accepted_at, channel, now, reason="original_server_result")
                    returned, units = await self._return_evidence(session, job, attempts, grants, now)
                    count += await self._fact(session, job, "return-contact-v1:" + job_id, "contact_study_24h",
                        returned.first_study_at, channel, now, reason="verified_server_activity_24h")
                    for study in units:
                        # Owner/global canonical identity excludes job/channel:
                        # overlapping contacts cannot count the same unit twice.
                        source = "return-unit-v1:" + str(job["user_id"]) + ":" + study.activity_type + ":" + study.reference
                        count += await self._fact(session, job, source, "study_unit_24h",
                            study.accepted_at, channel, now, reason="original_server_result_24h")
                return count

    async def capture_reservation(self, source):
        """Privileged post-commit reserve observation; never a client event."""
        if (not isinstance(source, ReservationObservation) or type(source.user_id) is not int or source.user_id <= 0 or
                not isinstance(source.event_key, str) or len(source.event_key) != 64 or
                any(c not in "0123456789abcdef" for c in source.event_key) or
                type(source.reason_code) is not str or type(source.stage) is not str or
                not ((source.stage == "shadow_reserved" and source.reason_code == "shadow_reserved") or
                     (source.stage == "shadow_refused" and source.reason_code in RESERVATION_REFUSALS))):
            raise ValueError("Trusted reservation observation required")
        at = _aware_utc(source.observed_at)
        async with self.sessions.begin() as session:
            owner = await session.scalar(select(User.id).where(User.id == source.user_id).with_for_update())
            if owner is None or await session.scalar(select(AccountDeletionRequest.id).where(
                    AccountDeletionRequest.status == "submitted", or_(AccountDeletionRequest.user_id == owner,
                        AccountDeletionRequest.active_user_id == owner)).limit(1)) is not None:
                return 0
            now = self.now()
            if not now - RAW_RETENTION < at <= now:
                return 0
            if source.stage == "shadow_reserved":
                from app.services.smart_reminder_baseline import enroll_baseline
                await enroll_baseline(session, owner, now, self._insert)
            inserted = await session.scalar(self._insert(session, RESERVATION).values(user_id=owner,
                event_key=source.event_key, stage=source.stage, reason_code=source.reason_code,
                occurred_at=at, expires_at=at+RAW_RETENTION).on_conflict_do_nothing(
                    index_elements=["user_id", "event_key"]).returning(RESERVATION.c.event_key))
            if inserted is None:
                return 0
            await session.execute(self._insert(session, MONTHLY).values(month=at.date().replace(day=1),
                stage=source.stage, channel="none", fact_count=1).on_conflict_do_update(
                    index_elements=["month", "stage", "channel"], set_={"fact_count": MONTHLY.c.fact_count+1}))
            return 1

    async def reconciliation_page(self, *, after_job_id=None, limit=128):
        """Read minimal committed-source IDs; close SQL before owner capture.

        Recent child facts qualify even when their parent's reservation expired.
        A completed page/pass is not proof of complete outcome coverage.
        """
        if (type(limit) is not int or not 1 <= limit <= MAX_BATCH or
                (after_job_id is not None and (not isinstance(after_job_id, str) or not 1 <= len(after_job_id) <= 36))):
            raise ValueError("Bounded Smart analysis source page required")
        async with self.sessions.begin() as session:
            if session.bind.dialect.name == "postgresql":
                await session.execute(text("SET TRANSACTION READ ONLY"))
                await session.execute(text("SET LOCAL statement_timeout = '5000'"))
            now = self.now()
            def recent(column):
                return and_(column > now - RAW_RETENTION, column <= now)
            job, attempt, grant = SmartReminderJob, SmartReminderAttempt, SmartReminderAndroidGrant
            reviewed = or_(and_(job.selected_channel == "android", job.policy_version.startswith("smart-android-v1:")),
                and_(job.selected_channel == "telegram", job.policy_version.startswith("smart-telegram-v1:")),
                and_(job.policy_version == QUEUE_VERSION, job.selected_channel.is_(None), job.selected_device_id.is_(None),
                    or_(and_(job.state == "shadow", recent(job.created_at)),
                        and_(job.state.in_(("completed", "cancelled", "expired")), recent(job.updated_at)))))
            fresh_source = or_(recent(job.created_at),
                and_(job.state.in_(("cancelled", "expired")), recent(job.updated_at)),
                and_(job.policy_version == QUEUE_VERSION, job.state == "completed", recent(job.updated_at)),
                select(attempt.id).where(attempt.job_id == job.id,
                    or_(recent(attempt.started_at), recent(attempt.resolved_at))).exists(),
                select(grant.id).where(grant.job_id == job.id, grant.user_id == job.user_id,
                    recent(grant.received_at)).exists())
            query = select(job.user_id, job.id).where(reviewed, fresh_source)
            if after_job_id is not None:
                query = query.where(job.id > after_job_id)
            rows = (await session.execute(query.order_by(job.id).limit(limit + 1))).all()
            return AnalysisSourcePage(tuple((r.user_id, r.id) for r in rows[:limit]), len(rows) > limit)

    async def retention(self, *, execute=False, limit=128):
        """One explicit bounded page; default returns anonymous counts only."""
        if type(execute) is not bool or type(limit) is not int or not 1 <= limit <= MAX_BATCH:
            raise ValueError("Bounded Smart analysis retention limit required")
        async with self.sessions.begin() as session:
            if session.bind.dialect.name == "postgresql":
                if not execute:
                    await session.execute(text("SET TRANSACTION READ ONLY"))
                await session.execute(text("SET LOCAL statement_timeout = '5000'"))
            now = self.now()
            expired = EVENT.c.expires_at <= now
            expired_reservations = RESERVATION.c.expires_at <= now
            old_month = MONTHLY.c.month < oldest_month(now)
            counts = {"expired_raw": await session.scalar(select(func.count()).select_from(EVENT).where(expired)),
                "expired_monthly": await session.scalar(select(func.count()).select_from(MONTHLY).where(old_month)),
                "expired_reservations": await session.scalar(select(func.count()).select_from(RESERVATION).where(expired_reservations)),
                "removed_raw": 0, "removed_reservations": 0, "removed_monthly": 0, "mode": "purge" if execute else "count_only"}
            if execute:
                # Delete only selected expired analysis keys. No source rows,
                # user lock or lock-order inversion with delivery/purge writers.
                keys = select(EVENT.c.user_id, EVENT.c.event_key).where(expired).order_by(
                    EVENT.c.expires_at, EVENT.c.user_id, EVENT.c.event_key).limit(limit)
                months = select(MONTHLY.c.month, MONTHLY.c.stage, MONTHLY.c.channel).where(old_month).order_by(
                    MONTHLY.c.month, MONTHLY.c.stage, MONTHLY.c.channel).limit(limit)
                reservations = select(RESERVATION.c.user_id, RESERVATION.c.event_key).where(expired_reservations).order_by(
                    RESERVATION.c.expires_at, RESERVATION.c.user_id, RESERVATION.c.event_key).limit(limit)
                counts["removed_raw"] = (await session.execute(delete(EVENT).where(
                    tuple_(EVENT.c.user_id, EVENT.c.event_key).in_(keys)))).rowcount
                counts["removed_monthly"] = (await session.execute(delete(MONTHLY).where(
                    tuple_(MONTHLY.c.month, MONTHLY.c.stage, MONTHLY.c.channel).in_(months)))).rowcount
                counts["removed_reservations"] = (await session.execute(delete(RESERVATION).where(
                    tuple_(RESERVATION.c.user_id, RESERVATION.c.event_key).in_(reservations)))).rowcount
            from app.services.smart_reminder_baseline import baseline_retention
            counts.update(await baseline_retention(session, now, execute=execute, limit=limit))
            return counts


class SmartReminderAnalysisObserver:
    """Bounded optional observation; no caller transaction or provider IO."""

    def __init__(self, settings, sessions, *, clock=None, timeout=2, interval=60, batch=128):
        if (any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0
                for v in (timeout, interval)) or type(batch) is not int or not 1 <= batch <= MAX_BATCH):
            raise ValueError("Positive bounded analysis worker settings required")
        self.settings = settings
        self.service = SmartReminderAnalysisService(sessions, clock=clock)
        from app.services.smart_reminder_baseline import SmartReminderBaselineService
        self.baseline = SmartReminderBaselineService(sessions, clock=clock)
        self.timeout, self.interval, self.batch = timeout, interval, batch
        self._reconcile_after = None  # Restart safely rescans the durable sources.
        self._baseline_after = None

    @property
    def enabled(self):
        return getattr(self.settings, "SMART_REMINDER_ANALYSIS_ENABLED", False) is True

    async def capture_job(self, user_id, job_id):
        if not self.enabled:
            return None
        try:
            return await asyncio.wait_for(self.service.capture_job(user_id, job_id), timeout=self.timeout)
        except Exception:
            # No exception/SQL/actor/credential content; missing capture is not
            # a measured zero. Cancellation remains cancellation.
            logger.warning("Smart analysis capture unavailable")
            return None

    async def capture_reservation(self, source):
        if not self.enabled:
            return None
        try:
            return await asyncio.wait_for(self.service.capture_reservation(source), timeout=self.timeout)
        except Exception:
            logger.warning("Smart reservation analysis unavailable")
            return None

    async def tick(self):
        if not self.enabled:
            return None
        return await asyncio.wait_for(self.service.retention(execute=True, limit=self.batch), timeout=self.timeout)

    async def run_retention(self):
        while self.enabled:
            try:
                await self.tick()
            except Exception:
                logger.warning("Smart analysis retention unavailable")
            await asyncio.sleep(self.interval)

    async def reconcile_tick(self):
        if not self.enabled:
            return None
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.timeout
        page = await asyncio.wait_for(self.service.reconciliation_page(
            after_job_id=self._reconcile_after, limit=self.batch), timeout=self.timeout)
        examined = inserted = unavailable = 0
        for user_id, job_id in page.sources:
            remaining = deadline - loop.time()
            if not self.enabled or remaining <= 0:
                break
            try:
                inserted += await asyncio.wait_for(self.service.capture_job(user_id, job_id), timeout=remaining)
            except Exception:
                logger.warning("Smart analysis reconciliation capture unavailable")
                unavailable += 1
            # A locked/failed owner must not starve later jobs. A later pass
            # retries it; capture's source-stage key makes all replay safe.
            self._reconcile_after = job_id
            examined += 1
        finished = examined == len(page.sources) and not page.has_more
        if finished:
            self._reconcile_after = None
        return {"examined": examined, "inserted_facts": inserted,
                "unavailable": unavailable, "pass_finished": finished}

    async def run_reconciliation(self):
        while self.enabled:
            try:
                await self.reconcile_tick()
            except Exception:
                logger.warning("Smart analysis reconciliation unavailable")
            try:
                await self.baseline_tick()
            except Exception:
                logger.warning("Smart baseline aggregation unavailable")
            await asyncio.sleep(self.interval)

    async def baseline_tick(self):
        if not self.enabled:
            return None
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.timeout
        owners, has_more = await asyncio.wait_for(self.baseline.aggregation_page(
            after_user_id=self._baseline_after, limit=self.batch), timeout=self.timeout)
        examined = updated = unavailable = 0
        for user_id in owners:
            remaining = deadline - loop.time()
            if not self.enabled or remaining <= 0:
                break
            try:
                updated += await asyncio.wait_for(self.baseline.observe_member(user_id), timeout=remaining)
            except Exception:
                logger.warning("Smart baseline observation unavailable")
                unavailable += 1
            self._baseline_after = user_id
            examined += 1
        finished = examined == len(owners) and not has_more
        if finished:
            self._baseline_after = None
        return {"examined": examined, "updated_observations": updated,
                "unavailable": unavailable, "pass_finished": finished}

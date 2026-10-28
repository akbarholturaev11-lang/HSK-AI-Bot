"""Internal, read-only adapter for the unused Smart shadow policy.

Call inside a caller-owned transaction with an already verified P1 actor.
No public route, background job, consent import, plan initialization or send.
The observation window is explicit; missing receipts never prove inactivity.
"""
import json
import re
from datetime import datetime, time, timezone
from types import SimpleNamespace

from sqlalchemy import func, or_, select

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.smart_reminder import SmartReminderAttempt, SmartReminderJob, SmartReminderPreference
from app.db.models.user import User
from app.services.course_daily_window import local_day_key
from app.services.course_levels import content_level
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService
from app.services.course_today_service import CourseTodayService
from app.services.course_v3_parts import total_parts
from app.services.daily_plan_service import DailyPlanService, TASK_CONTINUE_LESSON, plan_key
from app.services.entitlements.lesson_access import LessonAccessService
from app.services.learning_signals import LEARNING_ACTIVITY_TYPES, LearningSignals
from app.services.smart_reminder_policy import PolicyContext, VerifiedStudy
from app.services.smart_reminder_cadence import CadenceContext, StudyIntent
from app.services.smart_reminder_preferences import SmartReminderPreferencesService


# Work bound only; not a confidence, inactivity or data-retention threshold.
MAX_POLICY_ROWS = 512
TERMINAL_EVENTS = ("lesson_completed", "test_completed", "training_completed")
_LESSON_REF = re.compile(r"v3-part:((?:n?hsk)[1-4]):([1-9][0-9]*):complete\Z")


def _utc(value):
    # SQL UTC columns lose tzinfo on SQLite, unlike PostgreSQL.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _clock(value):
    return time.fromisoformat(value) if value is not None else None


def verified_studies(*, user_id, level, completed_parts, xp_rows, event_rows):
    """Corroborate server result receipts, preserving original XP identity/time.

    Only current-course lesson/practice sources are covered here. Best-effort
    telemetry and deterministic practice-session dedupe can undercount study;
    the caller must not turn an empty result into an inactivity finding.
    """
    events = [e for e in event_rows if e["user_id"] == user_id and e["level"] == level]
    lesson_orders = {e["lesson_order"] for e in events if e["event_name"] == "lesson_completed"}
    practice = set()
    for event in events:
        if event["event_name"] not in {"test_completed", "training_completed"}:
            continue
        try:
            payload = json.loads(event["payload_json"] or "{}")
            if (not isinstance(payload, dict) or type(payload.get("total")) is not int or
                    payload["total"] <= 0 or type(payload.get("score")) is not int or
                    not 0 <= payload["score"] <= payload["total"]):
                continue
        except (ValueError, TypeError):
            continue
        practice.add((event["event_name"], event["session_id"]))
    verified = {}
    limits = set()
    for row in xp_rows:
        if row["user_id"] != user_id or row["activity_type"] not in LEARNING_ACTIVITY_TYPES:
            continue
        kind, ref = row["activity_type"], row["activity_ref"]
        proven = False
        if kind == "lesson":
            match = _LESSON_REF.fullmatch(ref)
            proven = bool(match and match[1] == level and
                          0 < int(match[2]) <= completed_parts and int(match[2]) in lesson_orders)
        elif kind in {"test", "training"}:
            proven = ref.endswith(":completed") and (kind + "_completed", ref[:-10]) in practice
        else:
            limits.add("unsupported_study_type")
        if not proven or type(row["xp"]) is not int or row["xp"] <= 0:
            limits.add("uncorroborated_study")
            continue
        verified[ref] = VerifiedStudy(ref, kind, _utc(row["created_at"]),
                                     row["activity_date"].isoformat(), row["xp"])
    return tuple(verified.values()), tuple(sorted(limits))


class SmartReminderPolicyContextService:
    def __init__(self, session):
        self.session = session

    async def load_cadence(self, actor, *, observed_at: datetime, history_since: datetime, expected_level: str):
        """Read new-intent budget/outcomes; legacy negative coverage is unknown.

        Call under the same verified-actor/caller-owned transaction as `load`.
        Correlated aggregates avoid loading attempts, endpoint IDs or tokens.
        No public complete-coverage override is provided.
        """
        with self.session.no_autoflush:
            policy = await self.load(actor, observed_at=observed_at, history_since=history_since,
                                     expected_level=expected_level)
            external_fact = or_(SmartReminderAttempt.started_at.is_not(None), SmartReminderAttempt.state.in_(
                ("in_flight", "provider_accepted", "client_posted_unverified", "verified_shown", "unknown")))
            external = select(SmartReminderAttempt.id).where(
                SmartReminderAttempt.job_id == SmartReminderJob.id, external_fact).exists()
            ambiguous = select(SmartReminderAttempt.id).where(
                SmartReminderAttempt.job_id == SmartReminderJob.id, external_fact,
                SmartReminderAttempt.state.not_in(("definite_failure", "confirmed_not_displayed")),
            ).exists()
            shown = select(func.min(SmartReminderAttempt.resolved_at)).where(
                SmartReminderAttempt.job_id == SmartReminderJob.id,
                SmartReminderAttempt.state == "verified_shown",
                SmartReminderAttempt.started_at.is_not(None),
                SmartReminderAttempt.started_at <= SmartReminderAttempt.resolved_at,
                SmartReminderAttempt.resolved_at <= _utc(observed_at),
            ).correlate(SmartReminderJob).scalar_subquery()
            rows = (await self.session.execute(select(
                SmartReminderJob.id, SmartReminderJob.user_id, SmartReminderJob.local_day,
                SmartReminderJob.timezone_name, SmartReminderJob.day_start_utc, SmartReminderJob.day_end_utc,
                SmartReminderJob.scheduled_at, SmartReminderJob.state,
                external.label("external"), ambiguous.label("ambiguous"), shown.label("shown_at"),
            ).where(SmartReminderJob.user_id == actor.user_id, SmartReminderJob.category == "study",
                    SmartReminderJob.day_end_utc > _utc(history_since))
                .order_by(SmartReminderJob.day_start_utc.desc(), SmartReminderJob.id)
                .limit(MAX_POLICY_ROWS + 1))).mappings().all()
            intents = tuple(StudyIntent(
                job_id=row["id"], user_id=row["user_id"], local_day=row["local_day"],
                timezone_name=row["timezone_name"], day_start_utc=_utc(row["day_start_utc"]),
                day_end_utc=_utc(row["day_end_utc"]), scheduled_at=_utc(row["scheduled_at"]), state=row["state"],
                externally_attempted=bool(row["external"] or row["state"] in {"provider_accepted", "unknown"}),
                verified_shown_at=_utc(row["shown_at"]) if row["shown_at"] else None,
                definite_non_display=bool(row["external"] and not row["ambiguous"] and row["shown_at"] is None
                                           and row["state"] not in {"provider_accepted", "unknown"}),
            ) for row in rows[:MAX_POLICY_ROWS])
            return CadenceContext(
                user_id=actor.user_id, policy=policy, history_since=_utc(history_since), intents=intents,
                ledger_complete=len(rows) <= MAX_POLICY_ROWS,
                learning_complete_since=None,  # Best-effort/replayed legacy activity is not complete coverage.
            )

    async def load(self, actor, *, observed_at: datetime, history_since: datetime, expected_level: str):
        """Fresh account facts under P1's user lock, with zero writes/commit.

        This returns a simulation input, not a transferable auth or send grant.
        `expected_level` refuses stale course work; window bounds are explicit.
        """
        if (observed_at.tzinfo is None or history_since.tzinfo is None or
                history_since > observed_at):
            raise ValueError("An explicit aware observation window is required")
        now, since = _utc(observed_at), _utc(history_since)
        with self.session.no_autoflush:
            pref = await SmartReminderPreferencesService(self.session).read(actor)
            uid = actor.user_id
            # Fresh column projections avoid stale ORM progress/account state.
            columns = ("id", "telegram_id", "level", "language", "status", "payment_status",
                       "end_date", "payment_preview_payment_id", "pro_trial_ends_at", "pro_trial_revoked_at")
            row = (await self.session.execute(select(*(getattr(User, k) for k in columns)).where(
                User.id == uid))).mappings().one()
            user = SimpleNamespace(**row)
            level = content_level(user.level, default="")
            progress = (await self.session.execute(select(
                CourseProgress.level, CourseProgress.completed_lessons_count,
            ).where(CourseProgress.user_id == uid))).mappings().one_or_none()
            profile_row = (await self.session.execute(select(
                CourseMiniAppProfile.daily_goal_xp, CourseMiniAppProfile.daily_minutes,
                CourseMiniAppProfile.timezone_offset_minutes, CourseMiniAppProfile.daily_plan_key,
                CourseMiniAppProfile.daily_plan_json,
            ).where(CourseMiniAppProfile.user_id == uid))).mappings().one_or_none()
            profile = SimpleNamespace(**profile_row) if profile_row else None
            epoch = await self.session.scalar(select(SmartReminderPreference.grant_epoch).where(
                SmartReminderPreference.user_id == uid))
            xp_rows = (await self.session.execute(select(
                CourseXpEvent.__table__,
            ).where(CourseXpEvent.user_id == uid, CourseXpEvent.created_at >= since,
                    CourseXpEvent.created_at <= now,
                    CourseXpEvent.activity_type.in_(LEARNING_ACTIVITY_TYPES))
                .order_by(CourseXpEvent.created_at.desc(), CourseXpEvent.id.desc())
                .limit(MAX_POLICY_ROWS + 1))).mappings().all()
            event_rows = (await self.session.execute(select(
                CourseMiniAppEvent.user_id, CourseMiniAppEvent.level, CourseMiniAppEvent.event_name,
                CourseMiniAppEvent.lesson_order, CourseMiniAppEvent.session_id, CourseMiniAppEvent.payload_json,
            ).where(CourseMiniAppEvent.user_id == uid, CourseMiniAppEvent.level == level,
                    CourseMiniAppEvent.event_name.in_(TERMINAL_EVENTS),
                    CourseMiniAppEvent.created_at >= since, CourseMiniAppEvent.created_at <= now)
                .order_by(CourseMiniAppEvent.created_at.desc(), CourseMiniAppEvent.id.desc())
                .limit(MAX_POLICY_ROWS + 1))).mappings().all()
            completed = progress["completed_lessons_count"] if progress else 0
            studies, coverage = verified_studies(
                user_id=uid, level=level, completed_parts=completed,
                xp_rows=xp_rows[:MAX_POLICY_ROWS], event_rows=event_rows[:MAX_POLICY_ROWS])
            if len(xp_rows) > MAX_POLICY_ROWS or len(event_rows) > MAX_POLICY_ROWS:
                coverage = tuple(sorted(set(coverage) | {"observation_window_over_limit"}))
            course_day = local_day_key(profile.timezone_offset_minutes, now=now) if profile else None
            daily_goal = CourseMiniAppProfileService.resolve_daily_goal_xp(profile) if profile else None
            plan_completed = None
            if profile:
                tasks = CourseTodayService._stored_tasks(profile, plan_key(level=level, local_day=course_day))
                # Never silently discard a corrupt stored task and call the
                # remaining subset a complete plan. No new plan is built.
                valid_tasks = bool(tasks) and all(isinstance(t, dict) and (
                    t.get("t") != TASK_CONTINUE_LESSON or (
                        re.fullmatch(r"part:[1-9][0-9]*", str(t.get("ref") or "")) is not None and
                        int(t["ref"][5:]) <= total_parts(level))) for t in tasks)
                if valid_tasks:
                    today = tuple(s for s in studies if s.course_day == course_day)
                    signals = LearningSignals(
                        level=level, goal="", daily_minutes=profile.daily_minutes,
                        preferred_focus=None, plan_size=len(tasks), daily_goal_xp=daily_goal,
                        completed_parts=completed, current_part=completed + 1, total_parts=total_parts(level),
                        local_day=course_day, today_xp=sum(s.xp for s in today), streak=0, mistakes_total=0,
                        done_refs_today=frozenset(s.reference for s in today),
                        done_types_today=frozenset(s.activity_type for s in today),
                    )
                    hydrated = DailyPlanService.hydrate(tasks, signals)
                    if hydrated["total"] == len(tasks):
                        plan_completed = hydrated["complete"]
            target_allowed = False
            foundation_required = False
            total = total_parts(level)
            progress_level = content_level(progress["level"], default="") if progress else ""
            if level and level == progress_level and 0 <= completed < total:
                if user.level == "beginner":
                    foundation = await CourseMiniAppProfileService(self.session).foundation_status(user)
                    foundation_required = foundation["required"] and not foundation["completed"]
                if not foundation_required:
                    access = await LessonAccessService(self.session).status(
                        user, level=level, lesson_order=completed + 1, completed=completed, consume=False)
                    target_allowed = access["allowed"] is True
            channels = []
            tg, android = pref["channels"]["telegram"], pref["channels"]["android"]
            if tg["consent"] == "on" and tg["transport_available"]:
                channels.append("telegram")
            # Actor-scoped permission only. Do not infer another install's OS
            # state, claim capability, token delivery or fleet fencing.
            if (actor.kind == "android" and android["this_device_consent"] == "on" and
                    android["study_os_permission"] == "allowed"):
                channels.append("android")
            return PolicyContext(
                observed_at=now, level=level, progress_level=progress_level,
                expected_level=content_level(expected_level, default=""), completed_parts=completed,
                total_parts=total, target_allowed=target_allowed, foundation_required=foundation_required,
                revision=pref["revision"], grant_epoch=epoch or 0,
                master_enabled=pref["master_enabled"], permitted_channels=tuple(channels),
                timezone_name=pref["timezone_name"], course_day=course_day,
                daily_goal_xp=daily_goal, plan_completed=plan_completed, studies=studies, coverage_limits=coverage,
                time_mode=pref["time_mode"], manual_time=_clock(pref["manual_time_local"]),
                saved_time=_clock(pref["legacy_time_local"]), channel_mode=pref["channel_mode"],
                preferred_channel=pref["preferred_channel"], quiet_start=_clock(pref["quiet_start"]),
                quiet_end=_clock(pref["quiet_end"]),
                pause_until=datetime.fromisoformat(pref["pause_until"]) if pref["pause_until"] else None,
            )

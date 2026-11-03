"""Internal, read-only adapter for the unused Smart shadow policy.

Call inside a caller-owned transaction with an already verified P1 actor.
No public route, background job, consent import, plan initialization or send.
The observation window is explicit; missing receipts never prove inactivity.
"""
import json
import re
from dataclasses import dataclass
from datetime import datetime, time, timezone
from types import SimpleNamespace

from sqlalchemy import and_, func, or_, select

from app.db.models.course_attempts import CourseAttempt
from app.db.models.course_lessons import CourseLesson
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.smart_reminder import SmartReminderAttempt, SmartReminderJob, SmartReminderPreference
from app.db.models.user import User
from app.db.models.voice_practice_session import VoicePracticeSession
from app.services.course_daily_window import local_day_key
from app.services.course_levels import content_level, legacy_content_levels, hsk30_content_levels
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService
from app.services.course_today_service import CourseTodayService
from app.services.course_v3_parts import total_parts
from app.services.daily_plan_service import DailyPlanService, TASK_CONTINUE_LESSON, plan_key
from app.services.entitlements.lesson_access import LessonAccessService
from app.services.learning_signals import LEARNING_ACTIVITY_TYPES, LearningSignals
from app.services.smart_reminder_policy import PolicyContext, VerifiedStudy, _aware_utc
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


@dataclass(frozen=True)
class VerifiedLearningEvidence:
    studies: tuple[VerifiedStudy, ...] = ()
    coverage_limits: tuple[str, ...] = ("lesson_and_practice_sources_only",)


@dataclass(frozen=True)
class ScoredActivityEvidence:
    times: tuple[datetime, ...] = ()
    coverage_limits: tuple[str, ...] = (
        "reviewed_server_activity_sources_only", "repeat_practice_and_partial_voice_unavailable",
    )


def _scored_pair(payload, key):
    correct, total = payload.get(key), payload.get("total")
    return (type(correct) is int and type(total) is int and
            0 <= correct <= total and 0 < total <= 1000)


async def read_scored_activity(session, user_id, *, level, history_since, observed_at):
    """Analysis-only positive study evidence; never complete/negative coverage.

    Reviewed scoring and nonempty completed voice need no fresh XP or passing
    score. No answers, transcripts, IDs or scores leave this bounded reader.
    """
    since, now = _aware_utc(history_since), _aware_utc(observed_at)
    if since > now:
        raise ValueError("Study history must not begin in the future")
    levels = (level,) if level is not None else (*legacy_content_levels(), *hsk30_content_levels())
    limits = set(ScoredActivityEvidence().coverage_limits)
    events = (await session.execute(select(
        CourseMiniAppEvent.event_name, CourseMiniAppEvent.source, CourseMiniAppEvent.session_id,
        CourseMiniAppEvent.dedupe_key, CourseMiniAppEvent.payload_json, CourseMiniAppEvent.created_at,
        CourseMiniAppEvent.lesson_order, CourseMiniAppEvent.level, CourseLesson.level.label("lesson_level"),
        CourseLesson.lesson_order.label("bound_order"),
    ).outerjoin(CourseLesson, CourseLesson.id == CourseMiniAppEvent.lesson_id).where(
        CourseMiniAppEvent.user_id == user_id, CourseMiniAppEvent.level.in_(levels),
        or_(and_(CourseMiniAppEvent.event_name == "section_attempt_scored",
                 CourseMiniAppEvent.source == "course_miniapp"),
            and_(CourseMiniAppEvent.event_name == "test_completed",
                 CourseMiniAppEvent.source == "course_hsk_exam"),
            and_(CourseMiniAppEvent.event_name.in_(("test_completed", "training_completed")),
                 CourseMiniAppEvent.source == "course_miniapp")),
        CourseMiniAppEvent.created_at >= since, CourseMiniAppEvent.created_at <= now,
        func.length(CourseMiniAppEvent.payload_json) <= 8000,
    ).order_by(CourseMiniAppEvent.created_at, CourseMiniAppEvent.id).limit(MAX_POLICY_ROWS + 1))).mappings().all()
    times = set()
    if len(events) > MAX_POLICY_ROWS:
        limits.add("scored_events_over_limit")
    else:
        for event in events:
            try:
                payload = json.loads(event["payload_json"] or "{}")
                if not isinstance(payload, dict):
                    continue
                event_level = event["level"]
                if event["event_name"] == "section_attempt_scored":
                    section, dedupe = payload.get("section_key"), event["dedupe_key"]
                    if (event["lesson_level"] != event_level or type(event["bound_order"]) is not int or
                            event["bound_order"] <= 0 or event["bound_order"] != event["lesson_order"] or
                            not isinstance(section, str) or not 1 <= len(section) <= 128 or
                            not isinstance(dedupe, str) or re.fullmatch(r"section-attempt:[0-9a-f]{32}", dedupe) is None or
                            not _scored_pair(payload, "correct")):
                        continue
                elif event["source"] == "course_hsk_exam":
                    sid = event["session_id"]
                    if (not isinstance(sid, str) or re.fullmatch(
                            rf"hsk-exam:{user_id}:{re.escape(event_level)}:v[1-9][0-9]*:[0-9a-f]{{24}}", sid) is None or
                            event["dedupe_key"] != sid + ":completed" or not _scored_pair(payload, "score") or
                            type(payload.get("material_version")) is not int or payload["material_version"] <= 0 or
                            not isinstance(payload.get("material_id"), str) or not payload["material_id"]):
                        continue
                else:
                    # Shared Mini App/Android/Desktop writer, protocol v1.
                    # This is its retained completion time, never a fresh
                    # repeat-attempt time or another completed-unit award.
                    mode, skill = payload.get("mode"), payload.get("skill")
                    if (mode not in {"mock", "placement", "training"} or
                            event_level not in {"hsk1", "hsk2", "hsk3", "hsk4"} or
                            event["event_name"] != ("training_completed" if mode == "training" else "test_completed") or
                            not _scored_pair(payload, "score")):
                        continue
                    if ((mode == "training" and skill not in {"listening", "writing", "characters", "pronunciation", "pinyin"}) or
                            (mode != "training" and skill != "")):
                        continue
                    feature = "placement" if mode == "placement" else "training_test"
                    scope = skill if mode == "training" else event_level
                    if (event["session_id"] != f"practice:{user_id}:{feature}:{mode}:{scope}:v1" or
                            event["dedupe_key"] != f"practice:{feature}:completed"):
                        continue
                times.add(_utc(event["created_at"]))
            except (ValueError, TypeError):
                continue
    quizzes = (await session.execute(select(CourseAttempt.created_at, CourseAttempt.answers_json)
        .join(CourseLesson, CourseLesson.id == CourseAttempt.lesson_id).where(
            CourseAttempt.user_id == user_id, CourseAttempt.attempt_type == "quiz",
            CourseLesson.level.in_(levels), CourseLesson.lesson_order > 0,
            CourseAttempt.created_at >= since, CourseAttempt.created_at <= now,
            func.length(CourseAttempt.answers_json) <= 65536,
        ).order_by(CourseAttempt.created_at, CourseAttempt.id).limit(MAX_POLICY_ROWS + 1))).all()
    if len(quizzes) > MAX_POLICY_ROWS:
        limits.add("scored_quizzes_over_limit")
    else:
        for quiz in quizzes:
            try:
                payload = json.loads(quiz.answers_json)
                if (isinstance(payload, dict) and payload.get("source") == "miniapp_server_graded" and
                        _scored_pair(payload, "score")):
                    times.add(_utc(quiz.created_at))
            except (ValueError, TypeError):
                continue
    # Read no conversation content. Requiring the whole session inside the
    # window prevents an old conversation's later closure becoming new study.
    voices = (await session.execute(select(
        VoicePracticeSession.id, VoicePracticeSession.turn_count, VoicePracticeSession.ended_at,
    ).where(
        VoicePracticeSession.user_id == user_id,
        VoicePracticeSession.level.in_(levels),
        VoicePracticeSession.level.in_(("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")),
        VoicePracticeSession.mode.in_(("turn", "live")), VoicePracticeSession.status == "completed",
        VoicePracticeSession.turn_count > 0, VoicePracticeSession.started_at >= since,
        VoicePracticeSession.ended_at >= VoicePracticeSession.started_at,
        VoicePracticeSession.ended_at <= now,
    ).order_by(VoicePracticeSession.ended_at, VoicePracticeSession.id).limit(MAX_POLICY_ROWS + 1))).all()
    if len(voices) > MAX_POLICY_ROWS:
        limits.add("completed_voice_over_limit")
    else:
        for voice in voices:
            if (isinstance(voice.id, str) and re.fullmatch(
                    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", voice.id) and
                    type(voice.turn_count) is int and voice.turn_count > 0):
                times.add(_utc(voice.ended_at))
    return ScoredActivityEvidence(tuple(sorted(times)), tuple(sorted(limits)))


async def read_verified_learning(session, user_id, *, level, history_since, observed_at, evidence_at=None):
    """Bounded original account results for analysis, never inactivity/policy.

    Terminal events are server-only. Their reviewed producer/mode/result and
    canonical XP/progress must agree; a generic open or reward is insufficient.
    An explicit later evidence_at can corroborate original in-window XP with
    a late server receipt. It never moves the result cutoff or original time.
    """
    since, now = _aware_utc(history_since), _aware_utc(observed_at)
    if since > now:
        raise ValueError("Learning history must not begin in the future")
    receipt_cutoff = now if evidence_at is None else _aware_utc(evidence_at)
    if receipt_cutoff < now:
        raise ValueError("Learning proof cannot precede the result cutoff")
    progress = (await session.execute(select(CourseProgress.level, CourseProgress.completed_lessons_count)
        .where(CourseProgress.user_id == user_id))).mappings().one_or_none()
    completed = progress["completed_lessons_count"] if progress and progress["level"] == level else 0
    xp = (await session.execute(select(CourseXpEvent.__table__).where(CourseXpEvent.user_id == user_id,
        CourseXpEvent.activity_type.in_(("lesson", "test", "training")), CourseXpEvent.created_at >= since,
        CourseXpEvent.created_at <= now).order_by(CourseXpEvent.created_at.desc(), CourseXpEvent.id.desc())
        .limit(MAX_POLICY_ROWS + 1))).mappings().all()
    lesson_sources = ("course_v3", "android_course", "desktop_course")
    events = (await session.execute(select(CourseMiniAppEvent.__table__).where(
        CourseMiniAppEvent.user_id == user_id, CourseMiniAppEvent.level == level,
        CourseMiniAppEvent.event_name.in_(TERMINAL_EVENTS),
        CourseMiniAppEvent.source.in_((*lesson_sources, "course_miniapp")),
        CourseMiniAppEvent.created_at >= since, CourseMiniAppEvent.created_at <= receipt_cutoff)
        .order_by(CourseMiniAppEvent.created_at.desc(), CourseMiniAppEvent.id.desc())
        .limit(MAX_POLICY_ROWS + 1))).mappings().all()
    limits = {"lesson_and_practice_sources_only"}
    if len(xp) > MAX_POLICY_ROWS or len(events) > MAX_POLICY_ROWS:
        return VerifiedLearningEvidence(coverage_limits=tuple(sorted(limits | {"learning_history_over_limit"})))
    return corroborate_learning(user_id, level=level, completed=completed, xp=xp, events=events)


def corroborate_learning(user_id, *, level, completed, xp, events):
    """Shared strict server-receipt validator; SQL/auth/window stay with callers."""
    lesson_sources = ("course_v3", "android_course", "desktop_course")
    limits = {"lesson_and_practice_sources_only"}
    events = [e for e in events if e["user_id"] == user_id and e["level"] == level]
    originals = {r["activity_ref"]: r for r in xp}
    trusted = []
    for event in events:
        try:
            payload = json.loads(event["payload_json"] or "{}")
            if not isinstance(payload, dict):
                continue
            if event["event_name"] == "lesson_completed":
                ref = f"v3-part:{level}:{event['lesson_order']}:complete"
                original = originals.get(ref)
                if (event["source"] not in lesson_sources or original is None or
                        _utc(event["created_at"]) < _utc(original["created_at"])):
                    continue
                if event["source"] == "course_v3":
                    if type(payload.get("lesson_order")) is not int or payload["lesson_order"] != event["lesson_order"]:
                        continue
                else:
                    result = payload.get("result", {})
                    game = result.get("gamification", {})
                    device = payload.get("device_id")
                    if (not isinstance(device, str) or not 1 <= len(device) <= 36 or
                            result.get("ok") is not True or result.get("duplicate") is True or
                            type(result.get("completed_lesson")) is not int or
                            result["completed_lesson"] != event["lesson_order"] or
                            game.get("duplicate") is not False or type(game.get("awarded_xp")) is not int or
                            game["awarded_xp"] != original["xp"]):
                        continue
            else:
                mode, sid = payload.get("mode"), event["session_id"]
                if (event["source"] != "course_miniapp" or mode not in {"mock", "placement", "training"} or
                        event["event_name"] != ("training_completed" if mode == "training" else "test_completed") or
                        not isinstance(sid, str)):
                    continue
                parts = sid.split(":")
                if (len(parts) != 6 or parts[:4] != ["practice", str(user_id),
                        "placement" if mode == "placement" else "training_test", mode] or
                        not parts[4] or re.fullmatch(r"v[1-9][0-9]*", parts[5]) is None):
                    continue
            trusted.append(event)
        except (ValueError, TypeError, AttributeError):
            continue
    studies, missing = verified_studies(user_id=user_id, level=level, completed_parts=completed,
        xp_rows=xp, event_rows=trusted)
    return VerifiedLearningEvidence(studies, tuple(sorted(limits | set(missing))))


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

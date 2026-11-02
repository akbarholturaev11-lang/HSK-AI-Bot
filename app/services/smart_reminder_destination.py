"""D06 destination proposals only: no producer, cohort, grant or provider IO."""
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import json

from sqlalchemy import func, select

from app.db.models.android_push import AndroidPushToken
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.smart_reminder import SmartReminderCapability, SmartReminderConsent, SmartReminderPreference
from app.services.smart_reminder_policy import _aware_utc
from app.services.smart_reminder_policy_context import MAX_POLICY_ROWS, _LESSON_REF, verified_studies
from app.services.smart_reminder_preferences import SmartReminderError, SmartReminderPreferencesService, _state, _utc
from app.services.smart_reminder_shadow_queue import ATTEMPT, JOB, QUEUE_VERSION

MAX_DESTINATIONS = 128  # Work bound only, not a learning/confidence threshold.
VERSION = "smart-destination-v1"


@dataclass(frozen=True)
class Destination:
    user_id: int
    channel: str
    device_id: str | None = None
    valid_until: datetime | None = None
    last_active_at: datetime | None = None

    @property
    def key(self):
        return self.channel, self.device_id or ""


@dataclass(frozen=True)
class DestinationStudy:
    """Privileged verified learning and endpoint binding, never client input."""
    user_id: int
    reference: str
    channel: str
    device_id: str | None
    accepted_at: datetime
    activity_type: str = "lesson"

    @property
    def key(self):
        return self.channel, self.device_id or ""


@dataclass(frozen=True)
class DestinationEvidence:
    studies: tuple[DestinationStudy, ...] = ()
    limits: tuple[str, ...] = ()


@dataclass(frozen=True)
class DestinationChoice:
    reason: str
    channel: str | None = None
    device_id: str | None = None
    valid_until: datetime | None = None
    observed_results: int | None = None
    coverage_limits: tuple[str, ...] = ()
    job_id: str | None = None
    preference_revision: int | None = None
    grant_epoch: int | None = None
    policy_version: str = field(default=VERSION, init=False)
    dispatch_allowed: bool = field(default=False, init=False)


def choose_destination(*, user_id, destinations, evidence, observed_at, history_since,
                       master_enabled=None, channel_mode="auto", preferred_channel=None):
    now, since = _aware_utc(observed_at), _aware_utc(history_since)
    if since > now:
        raise ValueError("Destination history must not begin in the future")
    if master_enabled is False:
        return DestinationChoice("master_off")
    if channel_mode not in {"auto", "manual_locked"}:
        return DestinationChoice("channel_mode_unknown")
    if len(destinations) > MAX_DESTINATIONS:
        return DestinationChoice("destination_inventory_over_limit")
    candidates = {}
    for endpoint in destinations:
        if (not isinstance(endpoint, Destination) or type(endpoint.user_id) is not int or endpoint.user_id != user_id or
                type(endpoint.channel) is not str or endpoint.channel not in {"android", "telegram"} or
                (endpoint.channel == "android" and (not isinstance(endpoint.device_id, str) or
                    not endpoint.device_id or endpoint.valid_until is None)) or
                (endpoint.channel == "telegram" and endpoint.device_id is not None) or
                (endpoint.valid_until is not None and _aware_utc(endpoint.valid_until) <= now)):
            continue
        if channel_mode == "manual_locked" and endpoint.channel != preferred_channel:
            continue
        if endpoint.key in candidates and endpoint != candidates[endpoint.key]:
            return DestinationChoice("destination_snapshot_conflict")
        candidates[endpoint.key] = endpoint
    if not candidates:
        return DestinationChoice("manual_channel_unavailable" if channel_mode == "manual_locked" else "no_eligible_destination")
    if len(candidates) == 1:
        endpoint = next(iter(candidates.values()))
        return DestinationChoice("single_eligible_destination", endpoint.channel, endpoint.device_id, endpoint.valid_until)
    if not isinstance(evidence, DestinationEvidence):
        raise ValueError("Trusted destination evidence required")
    limits = set(evidence.limits)
    studies, conflicting = {}, set()
    if len(evidence.studies) > MAX_POLICY_ROWS:
        limits.add("destination_history_over_limit")
    else:
        for study in evidence.studies:
            if (not isinstance(study, DestinationStudy) or type(study.user_id) is not int or study.user_id != user_id or
                    not isinstance(study.reference, str) or not study.reference or
                    not isinstance(study.channel, str) or (study.device_id is not None and not isinstance(study.device_id, str)) or
                    type(study.activity_type) is not str or study.activity_type not in {"lesson", "test", "training"} or
                    not since <= _aware_utc(study.accepted_at) <= now):
                continue
            prior = studies.get(study.reference)
            if prior is not None and prior != study:
                conflicting.add(study.reference)
            studies[study.reference] = study
    if conflicting:
        limits.add("destination_attribution_conflict")
    votes = {key: [] for key in candidates}
    for reference, study in studies.items():
        if reference not in conflicting and study.key in votes:
            votes[study.key].append(_aware_utc(study.accepted_at))
    floor = datetime.min.replace(tzinfo=timezone.utc)
    def rank(endpoint):
        active = _aware_utc(endpoint.last_active_at) if endpoint.last_active_at is not None else floor
        return len(votes[endpoint.key]), max(votes[endpoint.key], default=floor), active if active <= now else floor
    ranked = sorted(candidates.values(), key=lambda e: e.key)
    ranked.sort(key=rank, reverse=True)  # Stable identity breaks otherwise exact ties.
    endpoint = ranked[0]
    count = len(votes[endpoint.key])
    reason = "observed_study_preference" if count else "recent_reachable_destination_fallback"
    return DestinationChoice(reason, endpoint.channel, endpoint.device_id, endpoint.valid_until,
        count if count else None, tuple(sorted(limits)))


async def read_native_lesson_destinations(session, user_id, *, level, history_since, observed_at):
    """Existing original XP + native producer metadata; no new personal store."""
    progress = (await session.execute(select(CourseProgress.level, CourseProgress.completed_lessons_count)
        .where(CourseProgress.user_id == user_id))).mappings().one_or_none()
    completed = progress["completed_lessons_count"] if progress and progress["level"] == level else 0
    xp = (await session.execute(select(CourseXpEvent.__table__).where(CourseXpEvent.user_id == user_id,
        CourseXpEvent.activity_type == "lesson", CourseXpEvent.created_at >= history_since,
        CourseXpEvent.created_at <= observed_at).order_by(CourseXpEvent.created_at.desc(), CourseXpEvent.id.desc())
        .limit(MAX_POLICY_ROWS + 1))).mappings().all()
    events = (await session.execute(select(CourseMiniAppEvent.user_id, CourseMiniAppEvent.source,
        CourseMiniAppEvent.level, CourseMiniAppEvent.event_name, CourseMiniAppEvent.lesson_order,
        CourseMiniAppEvent.session_id, CourseMiniAppEvent.payload_json, CourseMiniAppEvent.created_at)
        .where(CourseMiniAppEvent.user_id == user_id, CourseMiniAppEvent.level == level,
            CourseMiniAppEvent.event_name == "lesson_completed", CourseMiniAppEvent.source == "android_course",
            CourseMiniAppEvent.created_at >= history_since, CourseMiniAppEvent.created_at <= observed_at)
        .order_by(CourseMiniAppEvent.created_at.desc(), CourseMiniAppEvent.id.desc()).limit(MAX_POLICY_ROWS + 1))).mappings().all()
    limits = {"native_android_lesson_attribution_only"}
    if len(xp) > MAX_POLICY_ROWS or len(events) > MAX_POLICY_ROWS:
        return DestinationEvidence(limits=tuple(sorted(limits | {"destination_history_over_limit"})))
    verified, coverage = verified_studies(user_id=user_id, level=level, completed_parts=completed,
        xp_rows=xp, event_rows=events)
    limits.update(coverage)
    originals = {s.reference: s for s in verified}
    amounts = {r["activity_ref"]: r["xp"] for r in xp}
    studies = []
    for event in events:
        ref = f"v3-part:{level}:{event['lesson_order']}:complete"
        original = originals.get(ref)
        if original is None or _LESSON_REF.fullmatch(ref) is None or _utc(event["created_at"]) < original.accepted_at:
            continue
        try:
            payload = json.loads(event["payload_json"] or "{}")
            result = payload.get("result", {})
            gamification = result.get("gamification", {})
            device = payload.get("device_id")
            if (not isinstance(device, str) or not device or len(device) > 36 or result.get("ok") is not True or
                    result.get("duplicate") is True or type(result.get("completed_lesson")) is not int or
                    result["completed_lesson"] != event["lesson_order"] or gamification.get("duplicate") is not False or
                    type(gamification.get("awarded_xp")) is not int or gamification["awarded_xp"] != amounts[ref]):
                continue
        except (ValueError, TypeError, AttributeError):
            continue
        studies.append(DestinationStudy(user_id, ref, "android", device, original.accepted_at))
    return DestinationEvidence(tuple(studies), tuple(sorted(limits)))


class SmartReminderDestinationService:
    def __init__(self, session, *, clock=None, study_reader=read_native_lesson_destinations):
        self.session, self.study_reader = session, study_reader
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    async def select(self, actor, *, job_id, history_since):
        since = _aware_utc(history_since)
        with self.session.no_autoflush:
            pref = await SmartReminderPreferencesService(self.session).read(actor)
            job = (await self.session.execute(select(JOB).where(JOB.c.user_id == actor.user_id,
                JOB.c.id == job_id).with_for_update())).mappings().one_or_none()
            if job is None:
                raise SmartReminderError("smart_job_not_found", 404)
            def refused(reason):
                return DestinationChoice(reason, job_id=job_id, preference_revision=pref["revision"], grant_epoch=job["grant_epoch"])
            now = _aware_utc(self.clock())
            if since > now:
                raise ValueError("Destination history must not begin in the future")
            if job["state"] != "shadow" or job["policy_version"] != QUEUE_VERSION or job["selected_channel"] is not None:
                return refused("destination_intent_frozen")
            if job["lease_token"] is not None or await self.session.scalar(select(ATTEMPT.c.id).where(ATTEMPT.c.job_id == job_id).limit(1)):
                return refused("destination_intent_already_attempted")
            epoch = await self.session.scalar(select(SmartReminderPreference.grant_epoch).where(SmartReminderPreference.user_id == actor.user_id))
            if job["preference_revision"] != pref["revision"] or job["grant_epoch"] != (epoch or 0):
                return refused("destination_context_changed")
            if not _utc(job["day_start_utc"]) <= now < min(_utc(job["day_end_utc"]), _utc(job["expires_at"])):
                return refused("destination_window_unavailable")
            if pref["master_enabled"] is False:
                return refused("master_off")
            consents = (await self.session.execute(select(SmartReminderConsent.__table__).where(
                SmartReminderConsent.user_id == actor.user_id).limit(4 * MAX_DESTINATIONS + 1))).mappings().all()
            if len(consents) > 4 * MAX_DESTINATIONS:
                return refused("destination_inventory_over_limit")
            sessions = select(DesktopSession.device_id, func.max(DesktopSession.expires_at).label("session_until")).where(
                DesktopSession.revoked_at.is_(None), DesktopSession.expires_at > now,
                DesktopSession.device_id.in_(select(DesktopDevice.id).where(
                    DesktopDevice.user_id == actor.user_id, DesktopDevice.platform == "android"))
                ).group_by(DesktopSession.device_id).subquery()
            cap = SmartReminderCapability
            devices = (await self.session.execute(select(DesktopDevice.id, DesktopDevice.last_seen_at,
                cap.observed_at, cap.expires_at, sessions.c.session_until).join(cap, (cap.device_id == DesktopDevice.id) &
                    (cap.user_id == DesktopDevice.user_id)).join(AndroidPushToken, AndroidPushToken.device_id == DesktopDevice.id)
                .join(sessions, sessions.c.device_id == DesktopDevice.id).where(DesktopDevice.user_id == actor.user_id,
                    DesktopDevice.platform == "android", DesktopDevice.revoked_at.is_(None),
                    cap.protocol_version == 1, cap.autonomous_study_disabled.is_(True), cap.study_notifications_allowed.is_(True),
                    cap.observed_at <= now, cap.expires_at > now, func.length(func.trim(AndroidPushToken.token)) > 0,
                    AndroidPushToken.timezone_name == job["timezone_name"]).order_by(DesktopDevice.id)
                .limit(MAX_DESTINATIONS + 1))).mappings().all()
            if len(devices) > MAX_DESTINATIONS:
                return refused("destination_inventory_over_limit")
            until = _utc(job["expires_at"])
            if actor.access_expires_at is not None:
                until = min(until, _aware_utc(actor.access_expires_at))
            destinations = []
            telegram = pref["channels"]["telegram"]
            if telegram["consent"] == "on" and telegram["transport_available"]:
                destinations.append(Destination(actor.user_id, "telegram", valid_until=until))
            for device in devices:
                if _state([r for r in consents if r["channel"] == "android" and r["device_id"] == device["id"]],
                          "intent:android:" + device["id"]) != "on":
                    continue
                active = [_utc(v) for v in (device["last_seen_at"], device["observed_at"]) if v is not None and _utc(v) <= now]
                destinations.append(Destination(actor.user_id, "android", device["id"],
                    min(until, _utc(device["expires_at"]), _utc(device["session_until"])), max(active, default=None)))
            permitted = [d for d in destinations if pref["channel_mode"] != "manual_locked" or d.channel == pref["preferred_channel"]]
            evidence = (await self.study_reader(self.session, actor.user_id, level=job["course_key"],
                history_since=since, observed_at=now) if len(permitted) > 1 else DestinationEvidence())
            choice = choose_destination(user_id=actor.user_id, destinations=destinations, evidence=evidence,
                observed_at=_aware_utc(self.clock()), history_since=since, master_enabled=pref["master_enabled"],
                channel_mode=pref["channel_mode"], preferred_channel=pref["preferred_channel"])
            return replace(choice, job_id=job_id, preference_revision=pref["revision"], grant_epoch=epoch or 0)

"""Automatic four-stage Smart Reminder rollout with server-side admission.

Accounts are split into four stable cohorts by canonical account ID. Each stage
opens one more cohort after 48 observed healthy hours. Inside an open cohort the
admission step moves an account from the legacy study senders to Smart:

1. hold: the sticky routing row vetoes every server legacy study sender;
2. drain: wait 24 hours so already started legacy work cannot double today;
3. review: an evidence-bound automatic review enables the existing Smart path.

Admission never creates consent. It admits only accounts whose existing Smart
preference already allows a channel and whose Android inventory is fenced. A
bot-only learner without a Smart zone receives a fixed zone derived from the
legacy reminder offset it already uses. A
Smart-capable release (1.7.29/60 and newer) asks the server before any local
post and stops posting for a held account; an active device on an older APK
can still post its own local reminder, so such accounts stay on the legacy
senders.

Rollout state holds no learner identifiers. Systemic failures pause the rollout
and turn the existing Smart template OFF; an Admin PWA re-enable restarts it at
stage one.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import json
import logging
import time as monotonic

from sqlalchemy import and_, func, or_, select, update

from app.db.models.course_progress import CourseProgress
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.notification_template import NotificationTemplate
from app.db.models.smart_reminder import SmartReminderPreference, SmartReminderRollout, SmartReminderRouting
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.notification_template_service import KEY_SMART_STUDY


logger = logging.getLogger(__name__)

COHORT_COUNT = 4
STAGE_DURATION = timedelta(hours=48)
LEGACY_DRAIN = timedelta(hours=24)
REVIEW_TTL = timedelta(days=7)
RENEW_BEFORE = timedelta(days=2)
MIN_REVIEW_WINDOW = timedelta(minutes=2)
URGENT_WINDOW = timedelta(minutes=30)
HEALTH_INTERVAL = 300  # Seconds between attempt-ledger health reads per replica.
UNKNOWN_MIN = 5
UNKNOWN_SHARE = (3, 10)  # Pause at or above 30% unknown/failed started attempts.
STALE_IN_FLIGHT = timedelta(minutes=10)
EXCEPTION_LIMIT = 3
EXCEPTION_WINDOW = 3600
TIMEOUT_LIMIT = 3
ADMISSION_VERSION = "smart-auto-admission-v1"
ERROR_CODES = frozenset({
    "runtime_exception", "tick_timeout", "provider_unknown", "provider_failure",
    "native_unknown", "monitor_stale",
})
RUNNING = frozenset({"active", "complete"})


def cohort_for_user(user_id: int) -> int:
    """Stable 0..3 bucket without persisting or exposing account identifiers."""
    if type(user_id) is not int or user_id < 1:
        raise ValueError("Positive account id required")
    digest = hashlib.sha256(f"hsk-smart-reminder-rollout-v1:{user_id}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % COHORT_COUNT


@lru_cache(maxsize=8)
def _parse_early(raw: str) -> frozenset:
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() and int(part) > 0:
            ids.add(int(part))
    return frozenset(ids)


def early_accounts() -> frozenset:
    from app.config import settings
    return _parse_early(str(getattr(settings, "SMART_REMINDER_EARLY_USER_IDS", "") or ""))


def rollout_cohort(user_id: int) -> int:
    """Owner test accounts in SMART_REMINDER_EARLY_USER_IDS join stage one.

    This only moves their cohort; consent, Android fence, drain, pause and
    every send guard are unchanged.
    """
    return 0 if user_id in early_accounts() else cohort_for_user(user_id)


def cohort_open(user_id: int, stage: int, status: str = "active") -> bool:
    return status == "complete" or (stage >= 1 and rollout_cohort(user_id) < stage)


def legacy_zone(offset):
    """Fixed IANA zone for the legacy whole-hour reminder offset (UTC+5 → Etc/GMT-5).

    The legacy reminder already runs on this fixed offset; Uzbekistan,
    Tajikistan and Russia keep no daylight-saving time. A real browser zone
    later replaces it (the Mini App treats ``Etc/GMT`` zones as provisional).
    """
    if type(offset) is not int or not -12 <= offset <= 14:
        return None
    return "Etc/GMT" if offset == 0 else f"Etc/GMT{-offset:+d}"


def _utc(value):
    if value is None:
        return None
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value).astimezone(timezone.utc)


def _now(value):
    if value.tzinfo is None:
        raise ValueError("Timezone-aware rollout clock required")
    return value.astimezone(timezone.utc)


def _max_heartbeat_age(interval: int, timeout: int) -> timedelta:
    return timedelta(seconds=max(120, interval * 3, timeout * 2))


async def _state(session, *, lock=False, create=True):
    statement = select(SmartReminderRollout).where(SmartReminderRollout.id == 1).execution_options(
        populate_existing=True)
    state = await session.scalar(statement.with_for_update() if lock else statement)
    if state is None:
        if not create:
            return None
        state = SmartReminderRollout(id=1, generation=0, stage=0, status="waiting")
        session.add(state)
        await session.flush()
    return state


async def _disable_template(session, now):
    row = await session.scalar(select(NotificationTemplate).where(
        NotificationTemplate.key == KEY_SMART_STUDY).with_for_update())
    if row is None:
        session.add(NotificationTemplate(key=KEY_SMART_STUDY, enabled=False, media_type="none",
            created_at=now, updated_at=now))
    else:
        row.enabled = False
        row.updated_at = now
    await session.flush()


def _start(state, now):
    # A restart follows the operator's review, so the old stop reason clears;
    # the generation and attempt ledger keep the history.
    state.generation += 1
    state.stage = 1
    state.status = "active"
    state.stage_started_at = now
    state.heartbeat_at = now
    state.error_code = None
    state.error_at = None
    state.updated_at = now


def _stop(state, code, now):
    state.status = "paused"
    state.error_code = code
    state.error_at = now
    state.updated_at = now


async def _unhealthy(session, since, now):
    """Systemic delivery failure share since the stage started.

    Per-learner refusals are not provider faults: a Telegram account that
    blocked the bot, or an expired PWA subscription (definite failure). An
    Android attempt stays in flight until its receipt, so only a Telegram
    send stuck in flight counts as an unknown outcome.
    """
    from app.services.smart_reminder_shadow_queue import ATTEMPT, JOB
    started = await session.scalar(select(func.count()).select_from(ATTEMPT).where(
        ATTEMPT.c.started_at >= since, ATTEMPT.c.started_at <= now))
    if not started:
        return False
    bad = await session.scalar(select(func.count()).select_from(
        ATTEMPT.join(JOB, JOB.c.id == ATTEMPT.c.job_id).join(User, User.id == JOB.c.user_id)).where(
        ATTEMPT.c.started_at >= since, ATTEMPT.c.started_at <= now,
        or_(ATTEMPT.c.state == "unknown",
            and_(ATTEMPT.c.state == "in_flight", ATTEMPT.c.channel == "telegram",
                 ATTEMPT.c.started_at <= now - STALE_IN_FLIGHT)),
        or_(ATTEMPT.c.channel != "telegram", User.bot_blocked_at.is_(None))))
    return bad >= UNKNOWN_MIN and bad * UNKNOWN_SHARE[1] >= started * UNKNOWN_SHARE[0]


class SmartReminderRolloutService:
    def __init__(self, sessions, *, clock=None, interval=60, timeout=30):
        if interval <= 0 or timeout <= 0:
            raise ValueError("Positive rollout monitor intervals required")
        self.sessions = sessions
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.interval, self.timeout = interval, timeout
        self._health_at = None
        self._exceptions = []
        self._timeouts = 0

    def _fresh(self, state, now):
        last = _utc(state.heartbeat_at or state.stage_started_at)
        return last is not None and now - last <= _max_heartbeat_age(self.interval, self.timeout)

    async def heartbeat(self):
        """Start or restart stage one, advance after 48 observed hours, or pause."""
        now = _now(self.clock())
        async with self.sessions.begin() as session:
            # Same lock order as the Admin PWA editor and final send gates.
            await BotSettingRepository(session).lock_key("notification_template:" + KEY_SMART_STUDY)
            enabled = await session.scalar(select(NotificationTemplate.enabled).where(
                NotificationTemplate.key == KEY_SMART_STUDY))
            enabled = True if enabled is None else bool(enabled)
            state = await _state(session, lock=True)
            if not enabled:
                if state.status in RUNNING:
                    state.status = "paused"
                    state.updated_at = now
                return 0
            if state.status in {"waiting", "paused"}:
                # A pause always disables the template; enabled again means an
                # operator restarted it, so observation begins at stage one.
                _start(state, now)
                return state.stage
            if state.status not in RUNNING:
                return 0
            if not self._fresh(state, now):
                # Unobserved time (deploy, crash) never counts toward a stage.
                last = _utc(state.heartbeat_at or state.stage_started_at) or now
                if state.stage_started_at is not None:
                    state.stage_started_at = _utc(state.stage_started_at) + (now - last)
            check = monotonic.monotonic()
            if self._health_at is None or check - self._health_at >= HEALTH_INTERVAL:
                self._health_at = check
                since = _utc(state.stage_started_at) or now
                if await _unhealthy(session, since, now):
                    _stop(state, "provider_unknown", now)
                    await _disable_template(session, now)
                    logger.error("Smart rollout paused: provider_unknown")
                    return 0
            if state.status == "active" and now - _utc(state.stage_started_at) >= STAGE_DURATION:
                if state.stage < COHORT_COUNT:
                    state.stage += 1
                else:
                    state.status = "complete"
                state.stage_started_at = now
            state.heartbeat_at = now
            state.updated_at = now
            return state.stage

    async def allowed(self, session, user_id: int, *, now=None) -> bool:
        """Fresh final-boundary check; callers hold the Smart template read lock."""
        state = await _state(session, create=False)
        current = _now(now or self.clock())
        if state is None or state.status not in RUNNING or state.stage < 1 or not self._fresh(state, current):
            return False
        return cohort_open(user_id, state.stage, state.status)

    async def snapshot(self, session, *, now=None):
        state = await _state(session, create=False)
        if state is None:
            return {"generation": 0, "stage": 0, "cohort_count": COHORT_COUNT,
                "status": "waiting", "next_stage_at": None, "heartbeat_at": None,
                "error_at": None, "error_code": None}
        current = _now(now or self.clock())
        stale = state.status in RUNNING and not self._fresh(state, current)
        next_stage = None
        if state.status == "active" and state.stage_started_at is not None and not stale:
            next_stage = (_utc(state.stage_started_at) + STAGE_DURATION).isoformat()
        return {
            "generation": state.generation,
            "stage": state.stage,
            "cohort_count": COHORT_COUNT,
            "status": "paused" if stale else state.status,
            "next_stage_at": next_stage,
            "heartbeat_at": _utc(state.heartbeat_at).isoformat() if state.heartbeat_at else None,
            "error_at": _utc(state.error_at).isoformat() if state.error_at else None,
            "error_code": state.error_code,
        }

    async def fail_stop(self, code: str):
        if code not in ERROR_CODES:
            raise ValueError("Unknown rollout error code")
        now = _now(self.clock())
        async with self.sessions.begin() as session:
            await BotSettingRepository(session).lock_key("notification_template:" + KEY_SMART_STUDY)
            state = await _state(session, lock=True)
            if state.status in RUNNING:
                _stop(state, code, now)
                await _disable_template(session, now)
                logger.error("Smart rollout paused: %s", code)

    async def account_failed(self):
        """Pause after repeated unexpected per-account exceptions in one hour."""
        check = monotonic.monotonic()
        self._exceptions = [at for at in self._exceptions if check - at < EXCEPTION_WINDOW] + [check]
        if len(self._exceptions) >= EXCEPTION_LIMIT:
            self._exceptions = []
            await self.fail_stop("runtime_exception")

    async def tick_finished(self, *, timed_out):
        self._timeouts = self._timeouts + 1 if timed_out else 0
        if self._timeouts >= TIMEOUT_LIMIT:
            self._timeouts = 0
            await self.fail_stop("tick_timeout")


async def restart_after_admin_enable(session, *, now):
    """Called only for a signed Admin PWA OFF -> ON transition."""
    state = await _state(session, lock=True)
    _start(state, _now(now))
    await session.flush()


async def pause_after_admin_disable(session, *, now):
    state = await _state(session, lock=True)
    if state.status in RUNNING:
        state.status = "paused"
        state.updated_at = _now(now)
        await session.flush()


async def rollout_cohort_open(session, user_id, *, now=None):
    """Read-only gate for exposure that is not a send (browser zone setup)."""
    return await SmartReminderRolloutService(None).allowed(session, user_id, now=now)


@dataclass(frozen=True)
class _Facts:
    path: str | None
    routing: dict | None
    revision: int
    epoch: int
    inventory: str | None
    fence_until: datetime | None
    active_job: bool
    derived_zone: str | None = None


class SmartReminderAdmissionService:
    """Bounded automatic hold, drain and review for accounts in open cohorts."""

    def __init__(self, sessions, *, clock=None, telegram_ready=False, android_ready=False, batch=16,
                 cursors=None):
        if type(batch) is not int or not 1 <= batch <= 128:
            raise ValueError("Bounded admission batch required")
        self.sessions = sessions
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.telegram_ready, self.android_ready = telegram_ready, android_ready
        self.batch = batch
        # The runtime keeps cursors across ticks so pages rotate over everyone.
        self.cursors = cursors if cursors is not None else {}

    def _now(self):
        return _now(self.clock())

    async def step(self, stage, status="active"):
        if stage < 1 or not (self.telegram_ready or self.android_ready):
            return ()
        results = []
        for user_id in await self._candidates(stage, status):
            try:
                results.append(await self.admit(user_id))
            except ValueError:
                # Includes SmartReminderError: a concurrent change or a guard
                # refusal for this account only. The next pass reads it again.
                results.append("admission_refused")
        return tuple(results)

    async def _page(self, query, column, cursor):
        async with self.sessions() as session:
            rows = (await session.scalars(query.where(column > cursor).order_by(column)
                .limit(self.batch * COHORT_COUNT))).all()
            if not rows and cursor:
                rows = (await session.scalars(query.order_by(column).limit(self.batch * COHORT_COUNT))).all()
        return list(rows)

    async def _candidates(self, stage, status):
        pref, routing = SmartReminderPreference, SmartReminderRouting
        fresh = (select(pref.user_id).join(User, User.id == pref.user_id).where(
            pref.timezone_name.is_not(None), or_(pref.master_enabled.is_(None), pref.master_enabled.is_(True)),
            ~select(routing.user_id).where(routing.user_id == pref.user_id).exists()))
        routed = select(routing.user_id)
        # Bot-only learners with the legacy lesson reminder ON have no Smart
        # zone yet; admission derives it from their saved reminder offset.
        legacy = (select(CourseProgress.user_id).join(User, User.id == CourseProgress.user_id)
            .outerjoin(pref, pref.user_id == CourseProgress.user_id).where(
            CourseProgress.reminder_enabled.is_(True), User.telegram_id > 0, User.bot_blocked_at.is_(None),
            pref.timezone_name.is_(None), or_(pref.master_enabled.is_(None), pref.master_enabled.is_(True)),
            ~select(routing.user_id).where(routing.user_id == CourseProgress.user_id).exists()))
        now = self._now()
        chosen = []
        async with self.sessions() as session:
            # Android reviews last only as long as the device capability (about
            # one access token), so expiring or lapsed reviews come before the
            # rotation: the soonest-expiring first, long-lapsed rows last.
            urgent = (await session.scalars(select(routing.user_id).where(
                routing.verified_until <= now + URGENT_WINDOW)
                .order_by(routing.verified_until.desc(), routing.user_id).limit(self.batch * COHORT_COUNT))).all()
        chosen.extend([user_id for user_id in urgent if cohort_open(user_id, stage, status)][:self.batch])
        for name, query, column in (("new", fresh, pref.user_id), ("legacy", legacy, CourseProgress.user_id),
                                    ("routed", routed, routing.user_id)):
            rows = await self._page(query, column, self.cursors.get(name, 0))
            selected = [user_id for user_id in rows if cohort_open(user_id, stage, status)][:self.batch]
            self.cursors[name] = (selected[-1] if len(selected) == self.batch else rows[-1]) if rows else 0
            chosen.extend(user_id for user_id in selected if user_id not in chosen)
        return chosen

    async def _actors(self, user_id):
        from app.services.smart_reminder_preferences import SmartReminderActor
        now = self._now()
        async with self.sessions() as session:
            account = (await session.execute(select(User.telegram_id, User.bot_blocked_at).where(
                User.id == user_id))).mappings().one_or_none()
            native = (await session.execute(select(DesktopDevice.id, DesktopSession.id.label("session_id")).join(
                DesktopSession, DesktopSession.device_id == DesktopDevice.id).where(
                DesktopDevice.user_id == user_id, DesktopDevice.platform == "android",
                DesktopDevice.revoked_at.is_(None), DesktopSession.revoked_at.is_(None),
                DesktopSession.expires_at > now).order_by(
                DesktopSession.expires_at.desc(), DesktopSession.id).limit(1))).mappings().one_or_none()
        telegram = None
        if account and type(account["telegram_id"]) is int and account["telegram_id"] > 0 and account["bot_blocked_at"] is None:
            telegram = SmartReminderActor(user_id, "telegram_bot", telegram_id=account["telegram_id"])
        android = SmartReminderActor(user_id, "android", device_id=native["id"],
            session_id=native["session_id"]) if native else None
        return telegram, android

    async def _facts(self, user_id, telegram, android):
        from app.services.smart_reminder_preferences import SmartReminderPreferencesService
        from app.services.smart_reminder_shadow_queue import JOB
        from app.services.smart_reminder_telegram import ROUTING, _android_inventory
        now = self._now()
        async with self.sessions.begin() as session:
            pref = await SmartReminderPreferencesService(session).read(android or telegram)
            row = (await session.execute(select(ROUTING).where(ROUTING.c.user_id == user_id)
                .with_for_update())).mappings().one_or_none()
            epoch = await session.scalar(select(SmartReminderPreference.grant_epoch).where(
                SmartReminderPreference.user_id == user_id)) or 0
            # Telegram ownership: a Smart-capable release stops its own local
            # posting once held. Native posting needs a fresh capability.
            inventory, owner_until = await _android_inventory(session, user_id, now, native=False)
            _, native_until = await _android_inventory(session, user_id, now, native=True)
            active = await session.scalar(select(JOB.c.id).where(JOB.c.user_id == user_id,
                JOB.c.state.in_(("shadow", "pending", "claimed"))).limit(1)) is not None
            offset = await session.scalar(select(CourseProgress.reminder_tz_offset).where(
                CourseProgress.user_id == user_id))
        window = now + MIN_REVIEW_WINDOW
        locked = pref["channel_mode"] == "manual_locked"
        open_ = pref["master_enabled"] is not False and inventory is not None
        telegram_ok = (open_ and telegram is not None and self.telegram_ready and owner_until is None and
            pref["channels"]["telegram"]["consent"] == "on" and pref["channels"]["telegram"]["transport_available"] and
            (not locked or pref["preferred_channel"] in {"telegram", "pwa"}))
        path, fence_until, derived = None, None, None
        if open_ and pref["timezone_name"]:
            if (android is not None and self.android_ready and native_until is not None and
                    native_until > window and pref["channels"]["android"]["this_device_consent"] == "on" and
                    (not locked or pref["preferred_channel"] == "android")):
                path, fence_until = "android", native_until
            elif telegram_ok:
                path = "telegram"
        elif telegram_ok and row is None and pref["time_mode"] == "auto":
            derived = legacy_zone(offset)
        return _Facts(path, dict(row) if row else None, pref["revision"], epoch, inventory, fence_until, active,
            derived)

    async def admit(self, user_id):
        """Advance one account by at most one admission step."""
        from app.services.smart_reminder_telegram import SmartReminderRoutingService, _android_binding, _binding
        telegram, android = await self._actors(user_id)
        if telegram is None and android is None:
            return "actor_unavailable"
        facts = await self._facts(user_id, telegram, android)
        if facts.path is None and facts.derived_zone is not None:
            await self._derive_zone(telegram, facts.revision, facts.derived_zone)
            facts = await self._facts(user_id, telegram, android)
        if facts.path is None:
            return "not_eligible"
        actor = android if facts.path == "android" else telegram
        routing = SmartReminderRoutingService(self.sessions, clock=self.clock)
        row = facts.routing
        if row is None:
            await routing.hold(actor, expected_generation=0)
            await self._quiesced(user_id)
            return "held"
        now = self._now()
        quiesced = _utc(row.get("quiesced_at") or row["held_at"])
        if row.get("quiesced_at") is None:
            # Keep the first veto time before any re-hold moves held_at.
            await self._quiesced(user_id)
        if now - quiesced < LEGACY_DRAIN:
            return "draining"
        binding = _android_binding(actor) if facts.path == "android" else _binding(actor)
        target = "held" if facts.path == "android" else "telegram"
        verified = row["verified_at"] is not None
        owner = row["state"] == target and row["telegram_binding"] == binding
        generation = row["generation"]
        if verified and owner:
            remaining = _utc(row["verified_until"]) - now
            current = (row["preference_revision"] == facts.revision and row["grant_epoch"] == facts.epoch and
                row["inventory_sha256"] == facts.inventory)
            # A review capped by the Android capability fence cannot be extended
            # until the device reports again; renewing it would change nothing.
            capped = facts.fence_until is not None and _utc(row["verified_until"]) >= facts.fence_until
            if current and (remaining > RENEW_BEFORE or capped and remaining > MIN_REVIEW_WINDOW):
                return "current"
            review = self._review(user_id, generation, facts, quiesced)
            if review is None:
                return "fence_too_short"
            # Same owner: refresh re-attests in place and cancels no work.
            await routing.refresh(actor, review)
            return "reviewed"
        if verified and facts.active_job and _utc(row["verified_until"]) > now + MIN_REVIEW_WINDOW:
            # A new owner needs a re-hold, which cancels unattempted work.
            return "renewal_deferred"
        # An unreviewed hold is always state 'held'; activation picks the state.
        reusable = (not verified and row["state"] == "held" and row["telegram_binding"] == binding and
            row["preference_revision"] == facts.revision and row["grant_epoch"] == facts.epoch and
            row["inventory_sha256"] == facts.inventory)
        if not reusable:
            generation = await routing.hold(actor, expected_generation=generation)
            facts = await self._facts(user_id, telegram, android)
            if facts.path != ("android" if actor.kind == "android" else "telegram"):
                return "admission_changed"
        review = self._review(user_id, generation, facts, quiesced)
        if review is None:
            return "fence_too_short"
        if facts.path == "android":
            await routing.review_android(actor, review)
        else:
            await routing.activate(actor, review)
        return "reviewed" if verified else "admitted"

    def _review(self, user_id, generation, facts, quiesced):
        from app.services.smart_reminder_telegram import RoutingReview
        now = self._now()
        until = now + REVIEW_TTL
        if facts.fence_until is not None:
            until = min(until, facts.fence_until)
        if until - now < MIN_REVIEW_WINDOW:
            return None
        evidence = hashlib.sha256(json.dumps({
            "version": ADMISSION_VERSION, "user_id": user_id, "generation": generation,
            "path": facts.path, "quiesced_at": quiesced.isoformat(), "inventory": facts.inventory,
            "revision": facts.revision, "epoch": facts.epoch, "verified_at": now.isoformat(),
        }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        # The automatic drain is the quiesce/reconcile evidence: every server
        # legacy study sender honours the sticky routing veto, and the Android
        # inventory fence excludes devices that could still post locally.
        return RoutingReview(user_id=user_id, generation=generation, verified_at=now, verified_until=until,
            evidence_sha256=evidence, legacy_quiesced=True, legacy_outcomes_reconciled=True,
            other_study_fenced=True)

    async def _derive_zone(self, telegram, revision, zone):
        """Timezone only, through the journaled preference writer; no consent."""
        from uuid import uuid4
        from app.services.smart_reminder_preferences import SmartReminderPatch, SmartReminderPreferencesService
        async with self.sessions.begin() as session:
            await SmartReminderPreferencesService(session).patch(telegram, SmartReminderPatch(
                request_id=str(uuid4()), expected_revision=revision, timezone_name=zone))

    async def _quiesced(self, user_id):
        now = self._now()
        async with self.sessions.begin() as session:
            await session.execute(update(SmartReminderRouting).where(
                SmartReminderRouting.user_id == user_id, SmartReminderRouting.quiesced_at.is_(None)).values(
                quiesced_at=func.coalesce(SmartReminderRouting.held_at, now)))

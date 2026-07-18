from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.utils.course_miniapp import course_study_miniapp_url
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.user import User
from app.services.bot_block_status_service import BotBlockStatusService
from app.services.course_gamification_service import CourseGamificationService
from app.services.notification_template_service import (
    CAPTION_MAX,
    KEY_DAILY_GOAL,
    KEY_D1_RECOVERY,
    KEY_LESSON_UNFINISHED,
    KEY_OVERTAKEN,
    KEY_STREAK,
    NotificationTemplateService,
)

# On-disk root for admin-uploaded reminder media (see /uploads/notifications route).
MEDIA_ROOT = "app/static/uploads/notifications"

# Fallback when a profile has no saved timezone. Saved Mini App offsets come
# from the user's device and must be respected, including real UTC (0).
DEFAULT_OFFSET_MIN = 5 * 60  # UTC+5

# Evening window (local time) during which "daily goal" / "streak" reminders fire.
GOAL_WINDOW_START_MIN = 20 * 60  # 20:00
GOAL_WINDOW_END_MIN = 21 * 60 + 30  # 21:30
LESSON_UNFINISHED_SENT_EVENT = "motivation_lesson_unfinished_sent"
D1_RECOVERY_EXPERIMENT = "d1_recovery_v1"
D1_RECOVERY_ASSIGNED_EVENT = "d1_recovery_assigned"
D1_RECOVERY_SENT_EVENT = "d1_recovery_sent"
D1_RECOVERY_FAILED_EVENT = "d1_recovery_send_failed"
D1_RECOVERY_MIN_IDLE = timedelta(hours=24)
D1_RECOVERY_MAX_IDLE = timedelta(hours=36)
D1_RECOVERY_HOLDOUT = timedelta(hours=48)
D1_RECOVERY_LOOKBACK = timedelta(days=5)
D1_RECOVERY_ONBOARDING_MAX_AGE = timedelta(days=3)
D1_RECOVERY_SAFE_START_MIN = 9 * 60
D1_RECOVERY_SAFE_END_MIN = 21 * 60 + 30
D1_RECOVERY_SYSTEM_EVENTS = {
    LESSON_UNFINISHED_SENT_EVENT,
    D1_RECOVERY_ASSIGNED_EVENT,
    D1_RECOVERY_SENT_EVENT,
    D1_RECOVERY_FAILED_EVENT,
}
D1_RECOVERY_STATE_EVENTS = {
    "onboarding_completed",
    "lesson_started",
    "lesson_completed",
    "book_lesson_completed",
    "miniapp_opened",
    *D1_RECOVERY_SYSTEM_EVENTS,
}
DAILY_GOAL_ACTIVITY_TYPES = ("lesson", "book_lesson")


def _canonical_band(level: str | None) -> str:
    n = (level or "").strip().lower()
    if n in ("hsk1", "hsk2", "hsk3", "hsk4"):
        return n
    if n == "beginner":
        return "hsk1"
    return "hsk1"


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _d1_recovery_arm(telegram_id: int) -> tuple[str, int]:
    digest = hashlib.sha256(f"{D1_RECOVERY_EXPERIMENT}:{int(telegram_id)}".encode()).digest()
    bucket = int.from_bytes(digest[:4], "big") % 100
    return ("treatment" if bucket < 50 else "control", bucket)


def _event_payload(raw: str | None) -> dict:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _d1_recovery_states(
    events: list[CourseMiniAppEvent],
    *,
    now: datetime,
    last_activity_by_user: dict[int, datetime] | None = None,
) -> dict[int, dict]:
    by_user: dict[int, list[CourseMiniAppEvent]] = {}
    for event in events:
        if event.telegram_id:
            by_user.setdefault(int(event.telegram_id), []).append(event)

    states: dict[int, dict] = {}
    for telegram_id, user_events in by_user.items():
        user_events.sort(key=lambda item: _as_utc(item.created_at) or datetime.min.replace(tzinfo=timezone.utc))
        assignments = [
            event
            for event in user_events
            if event.event_name == D1_RECOVERY_ASSIGNED_EVENT
            and event.source == D1_RECOVERY_EXPERIMENT
        ]
        if assignments:
            assigned = assignments[-1]
            payload = _event_payload(assigned.payload_json)
            states[telegram_id] = {
                "assignment": assigned,
                "assigned_at": _as_utc(assigned.created_at),
                "arm": payload.get("arm") or _d1_recovery_arm(telegram_id)[0],
                "started": assigned,
                "last_activity_at": None,
            }
            continue

        onboarding = next(
            (event for event in reversed(user_events) if event.event_name == "onboarding_completed"),
            None,
        )
        onboarding_at = _as_utc(getattr(onboarding, "created_at", None))
        if not onboarding_at or now - onboarding_at > D1_RECOVERY_ONBOARDING_MAX_AGE:
            continue

        starts = [
            event
            for event in user_events
            if event.event_name == "lesson_started"
            and int(event.lesson_order or 0) == 1
            and (_as_utc(event.created_at) or now) >= onboarding_at
        ]
        if not starts:
            continue
        started = starts[0]
        started_at = _as_utc(started.created_at)
        if not started_at or started_at > onboarding_at + timedelta(hours=24):
            continue

        if any(
            event.event_name == LESSON_UNFINISHED_SENT_EVENT
            and (_as_utc(event.created_at) or now) >= started_at
            for event in user_events
        ):
            continue
        def completed_started_lesson(event: CourseMiniAppEvent) -> bool:
            if event.event_name not in {"lesson_completed", "book_lesson_completed"}:
                return False
            if (_as_utc(event.created_at) or now) < started_at:
                return False
            id_matches = (
                started.lesson_id is not None
                and event.lesson_id is not None
                and int(event.lesson_id) == int(started.lesson_id)
            )
            order_matches = (
                bool(started.level and event.level)
                and str(event.level).lower() == str(started.level).lower()
                and event.lesson_order is not None
                and started.lesson_order is not None
                and int(event.lesson_order) == int(started.lesson_order)
            )
            return id_matches or order_matches

        if any(completed_started_lesson(event) for event in user_events):
            continue

        returned = any(
            (_as_utc(event.created_at) or now) > started_at
            and event.event_name in {"miniapp_opened", "lesson_started"}
            and event.session_id
            and started.session_id
            and event.session_id != started.session_id
            for event in user_events
        )
        if returned:
            continue
        aggregated_last_activity = _as_utc(
            (last_activity_by_user or {}).get(telegram_id)
        )
        if aggregated_last_activity and aggregated_last_activity >= started_at:
            last_activity_at = aggregated_last_activity
        else:
            activity_times = [
                _as_utc(event.created_at)
                for event in user_events
                if (_as_utc(event.created_at) or now) >= started_at
                and event.event_name not in D1_RECOVERY_SYSTEM_EVENTS
            ]
            last_activity_at = max(
                (value for value in activity_times if value),
                default=started_at,
            )
        states[telegram_id] = {
            "assignment": None,
            "assigned_at": None,
            "arm": None,
            "started": started,
            "last_activity_at": last_activity_at,
        }
    return states


def _button(
    lang: str,
    *,
    level: str | None = None,
    lesson: int | None = None,
    source: str = "motivation_reminder",
    autostart: bool = False,
):
    # Tugma to'g'ridan-to'g'ri foydalanuvchining joriy darsiga olib boradi
    # (xarita emas). Dars aniqlanmasa, kurs xaritasi ochiladi.
    if source == D1_RECOVERY_EXPERIMENT:
        labels = {
            "uz": "▶️ Darsga qaytish",
            "ru": "▶️ Вернуться к уроку",
            "tj": "▶️ Ба дарс баргаштан",
        }
    elif lesson and lesson > 1:
        labels = {
            "uz": f"▶️ Davom etish · {lesson}-dars",
            "ru": f"▶️ Продолжить · урок {lesson}",
            "tj": f"▶️ Идома · дарси {lesson}",
        }
    else:
        labels = {
            "uz": "▶️ Darsni davom ettirish",
            "ru": "▶️ Продолжить урок",
            "tj": "▶️ Идомаи дарс",
        }
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=labels.get(lang, labels["ru"]),
                    web_app=WebAppInfo(
                        url=course_study_miniapp_url(
                            lang=lang,
                            level=level,
                            lesson=lesson,
                            tab="course",
                            source=source,
                            autostart=autostart,
                        )
                    ),
                )
            ]
        ]
    )


class MotivationReminderService:
    """Sends motivational reminders for rating, unfinished lessons, goals and streaks.

    All reminders are gated to at most once per user per local day and pull their
    text/media from admin-editable templates. Triggers are computed from real
    Mini App data (XP leaderboard, last_activity_date, current_streak).
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.templates = NotificationTemplateService(session)

    @staticmethod
    def _local_now(offset_minutes: int, now: datetime) -> datetime:
        return now + timedelta(minutes=max(-720, min(840, int(offset_minutes or 0))))

    @staticmethod
    def _profile_offset(profile) -> int:
        raw = getattr(profile, "timezone_offset_minutes", None)
        if raw is None:
            raw = DEFAULT_OFFSET_MIN
        try:
            offset = int(raw)
        except (TypeError, ValueError):
            offset = DEFAULT_OFFSET_MIN
        return max(-720, min(840, offset))

    @staticmethod
    def _xp_gap_to_above(above_weekly_xp: int, my_weekly_xp: int) -> int:
        return max(1, int(above_weekly_xp or 0) - int(my_weekly_xp or 0))

    @staticmethod
    def _local_day_bounds_utc(local_day: date, offset_minutes: int) -> tuple[datetime, datetime]:
        offset = timedelta(minutes=max(-720, min(840, int(offset_minutes or 0))))
        day_start = datetime.combine(local_day, datetime.min.time(), tzinfo=timezone.utc) - offset
        return day_start, day_start + timedelta(days=1)

    @staticmethod
    def _lesson_label(event: CourseMiniAppEvent, lang: str) -> str:
        level = (getattr(event, "level", "") or "").strip().upper()
        order = getattr(event, "lesson_order", None)
        try:
            lesson_no = int(order) if order else None
        except (TypeError, ValueError):
            lesson_no = None
        if level and lesson_no:
            if lang == "uz":
                return f"{level} {lesson_no}-dars"
            if lang == "tj":
                return f"{level} дарси {lesson_no}"
            return f"{level} урок {lesson_no}"
        fallbacks = {
            "uz": "Boshlangan dars",
            "ru": "Начатый урок",
            "tj": "Дарси оғозшуда",
        }
        return fallbacks.get(lang, fallbacks["ru"])

    async def _load_d1_recovery_states(
        self,
        telegram_ids: list[int],
        now: datetime,
    ) -> dict[int, dict]:
        ids = tuple({int(value) for value in telegram_ids if value})
        if not ids:
            return {}

        candidate_rows = (
            await self.session.execute(
                select(CourseMiniAppEvent.telegram_id)
                .where(
                    CourseMiniAppEvent.telegram_id.in_(ids),
                    or_(
                        and_(
                            CourseMiniAppEvent.event_name == "onboarding_completed",
                            CourseMiniAppEvent.created_at
                            >= now - D1_RECOVERY_ONBOARDING_MAX_AGE,
                        ),
                        and_(
                            CourseMiniAppEvent.event_name == D1_RECOVERY_ASSIGNED_EVENT,
                            CourseMiniAppEvent.source == D1_RECOVERY_EXPERIMENT,
                            CourseMiniAppEvent.created_at >= now - D1_RECOVERY_LOOKBACK,
                        ),
                    ),
                )
                .distinct()
            )
        ).all()
        candidate_ids = tuple(
            {int(row.telegram_id) for row in candidate_rows if row.telegram_id}
        )
        if not candidate_ids:
            return {}

        events = (
            await self.session.execute(
                select(CourseMiniAppEvent).where(
                    CourseMiniAppEvent.telegram_id.in_(candidate_ids),
                    CourseMiniAppEvent.created_at >= now - D1_RECOVERY_LOOKBACK,
                    CourseMiniAppEvent.event_name.in_(D1_RECOVERY_STATE_EVENTS),
                )
            )
        ).scalars().all()
        activity_rows = (
            await self.session.execute(
                select(
                    CourseMiniAppEvent.telegram_id,
                    func.max(CourseMiniAppEvent.created_at).label("last_activity_at"),
                )
                .where(
                    CourseMiniAppEvent.telegram_id.in_(candidate_ids),
                    CourseMiniAppEvent.created_at >= now - D1_RECOVERY_LOOKBACK,
                    CourseMiniAppEvent.event_name.notin_(D1_RECOVERY_SYSTEM_EVENTS),
                )
                .group_by(CourseMiniAppEvent.telegram_id)
            )
        ).all()
        return _d1_recovery_states(
            list(events),
            now=now,
            last_activity_by_user={
                int(row.telegram_id): row.last_activity_at
                for row in activity_rows
                if row.telegram_id and row.last_activity_at
            },
        )

    @staticmethod
    def _d1_payload(*, arm: str, bucket: int) -> dict:
        return {
            "experiment_id": D1_RECOVERY_EXPERIMENT,
            "arm": arm,
            "bucket": bucket,
            "eligibility_version": "first_lesson_no_return_v1",
            "outcome_window_hours": 48,
        }

    def _d1_event(
        self,
        *,
        user: User,
        started: CourseMiniAppEvent,
        event_name: str,
        stage: str,
        now: datetime,
        payload: dict,
    ) -> CourseMiniAppEvent:
        event = CourseMiniAppEvent(
            user_id=int(user.id),
            telegram_id=int(user.telegram_id),
            event_name=event_name,
            source=D1_RECOVERY_EXPERIMENT,
            level=started.level,
            lesson_id=started.lesson_id,
            lesson_order=started.lesson_order,
            session_id=started.session_id,
            dedupe_key=f"{D1_RECOVERY_EXPERIMENT}:{stage}",
            payload_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            created_at=now,
        )
        self.session.add(event)
        return event

    async def _reserve_d1_assignment(
        self,
        *,
        user: User,
        started: CourseMiniAppEvent,
        now: datetime,
        arm: str,
        bucket: int,
    ) -> bool:
        payload = self._d1_payload(arm=arm, bucket=bucket)
        payload.update(
            {
                "started_at": (_as_utc(started.created_at) or now).isoformat(),
                "target_level": started.level,
                "target_lesson": started.lesson_order,
            }
        )
        try:
            async with self.session.begin_nested():
                self._d1_event(
                    user=user,
                    started=started,
                    event_name=D1_RECOVERY_ASSIGNED_EVENT,
                    stage="assigned",
                    now=now,
                    payload=payload,
                )
                await self.session.flush()
            await self.session.commit()
            return True
        except IntegrityError:
            return False

    async def _handle_d1_recovery(
        self,
        *,
        bot: Bot,
        user: User,
        lang: str,
        local_now: datetime,
        now: datetime,
        state: dict | None,
    ) -> str | None:
        if not state:
            return None
        assigned_at = _as_utc(state.get("assigned_at"))
        if assigned_at:
            return "d1_holdout_active" if now < assigned_at + D1_RECOVERY_HOLDOUT else None

        started = state.get("started")
        last_activity_at = _as_utc(state.get("last_activity_at"))
        if not started or not last_activity_at:
            return None
        idle = now - last_activity_at
        if idle < D1_RECOVERY_MIN_IDLE:
            return "d1_waiting"
        if idle > D1_RECOVERY_MAX_IDLE:
            return None
        local_minute = local_now.hour * 60 + local_now.minute
        if not D1_RECOVERY_SAFE_START_MIN <= local_minute <= D1_RECOVERY_SAFE_END_MIN:
            return "d1_waiting_safe_hour"

        # Admin template toggle is the experiment kill switch. Check it before
        # assigning either arm so disabled treatment cannot pollute the ITT cohort
        # or suppress normal reminders for 48 hours.
        resolved = await self.templates.resolve(KEY_D1_RECOVERY, lang)
        if not resolved:
            return None

        arm, bucket = _d1_recovery_arm(int(user.telegram_id))
        if not await self._reserve_d1_assignment(
            user=user,
            started=started,
            now=now,
            arm=arm,
            bucket=bucket,
        ):
            return "d1_already_assigned"
        if arm == "control":
            return "d1_control_assigned"

        base_payload = self._d1_payload(arm=arm, bucket=bucket)
        sent = await self._send(
            bot,
            user,
            resolved,
            lang,
            {"lesson": self._lesson_label(started, lang)},
            target_level=started.level,
            target_lesson=started.lesson_order,
            source=D1_RECOVERY_EXPERIMENT,
            autostart=True,
        )
        if sent:
            sent_payload = {
                **base_payload,
                "template_key": KEY_D1_RECOVERY,
                "target_level": started.level,
                "target_lesson": started.lesson_order,
            }
            self._d1_event(
                user=user,
                started=started,
                event_name=D1_RECOVERY_SENT_EVENT,
                stage="sent",
                now=now,
                payload=sent_payload,
            )
            status = "d1_treatment_sent"
        else:
            failed_payload = {**base_payload, "error_kind": "telegram_or_media", "retryable": False}
            self._d1_event(
                user=user,
                started=started,
                event_name=D1_RECOVERY_FAILED_EVENT,
                stage="send_failed",
                now=now,
                payload=failed_payload,
            )
            status = "d1_treatment_failed"
        await self.session.commit()
        return status

    async def send_due_reminders(self, bot: Bot) -> None:
        now = datetime.now(timezone.utc)

        # One query: recently active, reachable users that have a Mini App profile.
        # Course Mini App reminders are a learning loop, not a paid-only feature:
        # trial/free/expired users can still use the limited course surfaces.
        rows = (
            await self.session.execute(
                select(CourseMiniAppProfile, User)
                .join(User, CourseMiniAppProfile.user_id == User.id)
                .where(User.status != "blocked")
                .where(User.last_active_at >= now - timedelta(days=14))
                .where(
                    or_(
                        User.bot_blocked_at.is_(None),
                        User.bot_unblocked_at >= User.bot_blocked_at,
                    )
                )
            )
        ).all()
        if not rows:
            return

        d1_states = await self._load_d1_recovery_states(
            [int(user.telegram_id) for _profile, user in rows],
            now,
        )

        offsets_by_user = {
            int(profile.user_id): self._profile_offset(profile)
            for profile, _ in rows
        }

        # Weekly XP per user for the current week (drives league ranking).
        weekly_xp: dict[int, int] = {}
        days = {
            CourseGamificationService._local_day(offset, now)
            for offset in offsets_by_user.values()
        }
        week_starts = {CourseGamificationService._week_start(d) for d in days}
        if week_starts:
            wx_rows = (
                await self.session.execute(
                    select(
                        CourseXpEvent.user_id,
                        func.sum(CourseXpEvent.xp),
                    )
                    .where(CourseXpEvent.week_start.in_(week_starts))
                    .group_by(CourseXpEvent.user_id)
                )
            ).all()
            weekly_xp = {int(uid): int(xp or 0) for uid, xp in wx_rows}

        # Build per-league ranking (weekly_xp desc, xp_total desc) to detect overtakes.
        league_members: dict[str, list[tuple[CourseMiniAppProfile, User, int]]] = {}
        for profile, user in rows:
            league = CourseGamificationService.league_for_xp(profile.xp_total)
            league_members.setdefault(league, []).append(
                (profile, user, weekly_xp.get(int(profile.user_id), 0))
            )
        ranks: dict[int, tuple[int, list]] = {}
        for members in league_members.values():
            members.sort(
                key=lambda item: (
                    -int(item[2] or 0),
                    -int(item[0].xp_total or 0),
                    int(item[1].id or 0),
                )
            )
            for index, (profile, _user, _wx) in enumerate(members, 1):
                ranks[int(profile.user_id)] = (index, members)

        changed = False
        # Diagnostic funnel: counts why each profile was reached or skipped so the
        # production logs explain "not everyone gets it". Printed once per cycle.
        stats: dict[str, int] = {}

        def bump(key: str) -> None:
            stats[key] = stats.get(key, 0) + 1

        stats["considered"] = len(rows)
        for profile, user in rows:
            # Master switch: the user turned notifications off in the Mini App.
            if not getattr(profile, "notifications_enabled", True):
                bump("skip_notifications_off")
                continue
            lang = user.language if user.language in ("uz", "ru", "tj") else "ru"
            offset = offsets_by_user.get(int(profile.user_id), DEFAULT_OFFSET_MIN)
            local_now = self._local_now(offset, now)
            local_day = local_now.date()

            d1_status = await self._handle_d1_recovery(
                bot=bot,
                user=user,
                lang=lang,
                local_now=local_now,
                now=now,
                state=d1_states.get(int(user.telegram_id)),
            )
            if d1_status:
                bump(d1_status)
                continue

            current_rank, members = ranks.get(int(profile.user_id), (0, []))

            # 1) Overtaken in the rating (rank got worse since last check).
            if current_rank and await self._maybe_overtaken(
                bot, profile, user, lang, current_rank, members, local_day
            ):
                bump("sent_overtaken")
                changed = True
                profile.last_known_rank = current_rank
                continue
            if current_rank:
                if profile.last_known_rank != current_rank:
                    profile.last_known_rank = current_rank
                    changed = True

            # 2/3/4) Evening goal/streak reminders — only if the daily lesson goal is not done.
            now_min = local_now.hour * 60 + local_now.minute
            if not (GOAL_WINDOW_START_MIN <= now_min <= GOAL_WINDOW_END_MIN):
                bump("skip_outside_evening_window")
                continue

            day_start, day_end = self._local_day_bounds_utc(local_day, offset)
            if await self._daily_goal_completed_today(
                user, local_day, day_start, day_end
            ):
                bump("skip_daily_goal_done")
                continue

            minutes = int(profile.daily_minutes or 10)
            unfinished_lesson = await self._unfinished_lesson_today(user, day_start, day_end)
            if unfinished_lesson is not None:
                resolved = await self.templates.resolve(KEY_LESSON_UNFINISHED, lang)
                if not resolved:
                    bump("skip_template_disabled_lesson_unfinished")
                elif await self._send(
                    bot,
                    user,
                    resolved,
                    lang,
                    {
                        "lesson": self._lesson_label(unfinished_lesson, lang),
                        "minutes": minutes,
                    },
                    target_level=unfinished_lesson.level,
                    target_lesson=unfinished_lesson.lesson_order,
                ):
                    bump("sent_lesson_unfinished")
                    self._mark_unfinished_lesson_sent(user, unfinished_lesson, local_day)
                    changed = True
                else:
                    bump("send_failed_lesson_unfinished")
                continue

            streak = int(profile.current_streak or 0)
            has_live_streak = streak >= 1 and profile.last_activity_date == local_day - timedelta(days=1)

            if has_live_streak:
                if profile.motivation_streak_date == local_day:
                    bump("skip_streak_already_sent_today")
                    continue
                resolved = await self.templates.resolve(KEY_STREAK, lang)
                if not resolved:
                    bump("skip_template_disabled_streak")
                elif await self._send(
                    bot, user, resolved, lang, {"streak": streak}
                ):
                    bump("sent_streak")
                    profile.motivation_streak_date = local_day
                    changed = True
                else:
                    bump("send_failed_streak")
            else:
                if profile.motivation_goal_date == local_day:
                    bump("skip_goal_already_sent_today")
                    continue
                resolved = await self.templates.resolve(KEY_DAILY_GOAL, lang)
                if not resolved:
                    bump("skip_template_disabled_daily_goal")
                elif await self._send(
                    bot, user, resolved, lang, {"minutes": minutes}
                ):
                    bump("sent_daily_goal")
                    profile.motivation_goal_date = local_day
                    changed = True
                else:
                    bump("send_failed_daily_goal")

        print("MotivationReminderService funnel:", stats)
        if changed:
            await self.session.commit()

    async def _daily_goal_completed_today(
        self,
        user: User,
        local_day: date,
        day_start: datetime,
        day_end: datetime,
    ) -> bool:
        xp_done = (
            await self.session.execute(
                select(CourseXpEvent.id)
                .where(
                    CourseXpEvent.user_id == int(user.id),
                    CourseXpEvent.activity_date == local_day,
                    CourseXpEvent.activity_type.in_(DAILY_GOAL_ACTIVITY_TYPES),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if xp_done:
            return True
        event_done = (
            await self.session.execute(
                select(CourseMiniAppEvent.id)
                .where(
                    CourseMiniAppEvent.telegram_id == int(user.telegram_id),
                    CourseMiniAppEvent.event_name.in_(("lesson_completed", "book_lesson_completed")),
                    CourseMiniAppEvent.created_at >= day_start,
                    CourseMiniAppEvent.created_at < day_end,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        return bool(event_done)

    async def _unfinished_lesson_today(
        self,
        user: User,
        day_start: datetime,
        day_end: datetime,
    ) -> CourseMiniAppEvent | None:
        started = (
            await self.session.execute(
                select(CourseMiniAppEvent)
                .where(
                    CourseMiniAppEvent.telegram_id == int(user.telegram_id),
                    CourseMiniAppEvent.event_name == "lesson_started",
                    CourseMiniAppEvent.created_at >= day_start,
                    CourseMiniAppEvent.created_at < day_end,
                )
                .order_by(CourseMiniAppEvent.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if started is None:
            return None

        already_sent = (
            await self.session.execute(
                select(CourseMiniAppEvent.id)
                .where(
                    CourseMiniAppEvent.telegram_id == int(user.telegram_id),
                    CourseMiniAppEvent.event_name == LESSON_UNFINISHED_SENT_EVENT,
                    CourseMiniAppEvent.created_at >= day_start,
                    CourseMiniAppEvent.created_at < day_end,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if already_sent:
            return None

        conditions = [
            CourseMiniAppEvent.telegram_id == int(user.telegram_id),
            CourseMiniAppEvent.event_name.in_(("lesson_completed", "book_lesson_completed")),
            CourseMiniAppEvent.created_at >= started.created_at,
        ]
        if started.lesson_id is not None:
            conditions.append(CourseMiniAppEvent.lesson_id == int(started.lesson_id))
        elif started.level and started.lesson_order is not None:
            conditions.extend(
                [
                    CourseMiniAppEvent.level == started.level,
                    CourseMiniAppEvent.lesson_order == int(started.lesson_order),
                ]
            )

        completed_after_start = (
            await self.session.execute(
                select(CourseMiniAppEvent.id).where(*conditions).limit(1)
            )
        ).scalar_one_or_none()
        if completed_after_start:
            return None
        return started

    def _mark_unfinished_lesson_sent(
        self,
        user: User,
        started: CourseMiniAppEvent,
        local_day: date,
    ) -> None:
        ref = started.lesson_id or (
            f"{started.level}:{started.lesson_order}"
            if started.level and started.lesson_order is not None
            else "unknown"
        )
        self.session.add(
            CourseMiniAppEvent(
                user_id=int(user.id),
                telegram_id=int(user.telegram_id),
                event_name=LESSON_UNFINISHED_SENT_EVENT,
                source="motivation_reminder",
                level=started.level,
                lesson_id=started.lesson_id,
                lesson_order=started.lesson_order,
                dedupe_key=f"{local_day.isoformat()}:{ref}",
            )
        )

    async def _maybe_overtaken(
        self, bot, profile, user, lang, current_rank, members, local_day
    ) -> bool:
        prev_rank = profile.last_known_rank
        # Only notify when we have a baseline and the user actually dropped.
        if prev_rank is None or current_rank <= prev_rank or current_rank <= 1:
            return False
        if profile.motivation_overtaken_date == local_day:
            return False
        # Person now directly above the user.
        above_profile, above_user, above_wx = members[current_rank - 2]
        name = (above_user.full_name or "").strip() or (
            f"@{above_user.username}" if above_user.username else "Bir o'quvchi"
        )
        my_wx = members[current_rank - 1][2]
        xp_gap = self._xp_gap_to_above(above_wx, my_wx)
        league = CourseGamificationService.league_for_xp(profile.xp_total)
        resolved = await self.templates.resolve(KEY_OVERTAKEN, lang)
        if not resolved:
            return False
        if await self._send(
            bot,
            user,
            resolved,
            lang,
            {"name": name[:40], "league": league, "rank": current_rank, "xp_gap": xp_gap},
        ):
            profile.motivation_overtaken_date = local_day
            return True
        return False

    async def _lesson_deeplink_target(self, user: User) -> tuple[str | None, int | None]:
        """Foydalanuvchining joriy darsi = tugallangan darslar + 1 (Mini App bilan bir xil)."""
        try:
            from app.repositories.course_progress_repo import CourseProgressRepository

            level = _canonical_band(getattr(user, "level", None))
            progress = await CourseProgressRepository(self.session).get_by_user_id(user.id)
            completed = int(getattr(progress, "completed_lessons_count", 0) or 0) if progress else 0
            return level, completed + 1
        except Exception:
            return None, None

    async def _send(
        self,
        bot: Bot,
        user: User,
        resolved: dict,
        lang: str,
        fields: dict,
        *,
        target_level: str | None = None,
        target_lesson: int | None = None,
        source: str = "motivation_reminder",
        autostart: bool = False,
    ) -> bool:
        try:
            text = resolved["text"].format(**fields)
        except (KeyError, IndexError, ValueError):
            text = resolved["text"]
        media_type = resolved.get("media_type") or "none"
        media_path = resolved.get("media_path")
        level, lesson = target_level, target_lesson
        if not level or not lesson:
            level, lesson = await self._lesson_deeplink_target(user)
        markup = _button(
            lang,
            level=level,
            lesson=lesson,
            source=source,
            autostart=autostart,
        )
        try:
            if media_type in ("photo", "video") and media_path:
                import os

                full_path = os.path.join(MEDIA_ROOT, media_path)
                if os.path.exists(full_path):
                    caption = text[:CAPTION_MAX]
                    media = FSInputFile(full_path)
                    if media_type == "photo":
                        await bot.send_photo(user.telegram_id, media, caption=caption, reply_markup=markup, parse_mode="HTML")
                    else:
                        await bot.send_video(user.telegram_id, media, caption=caption, reply_markup=markup, parse_mode="HTML")
                    return True
            await bot.send_message(
                user.telegram_id, text, reply_markup=markup, parse_mode="HTML"
            )
            return True
        except Exception as exc:  # noqa: BLE001 - blocked/deleted users are expected
            print(f"MotivationReminderService: failed to notify {user.telegram_id}: {exc}")
            await BotBlockStatusService(self.session).handle_send_exception(
                user.telegram_id, exc, reason="motivation_reminder"
            )
            return False

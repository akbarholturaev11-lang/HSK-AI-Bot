from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy import func, select
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
DAILY_GOAL_ACTIVITY_TYPES = ("lesson", "book_lesson")


def _button(lang: str):
    labels = {
        "uz": "📚 Mini Appda davom ettirish",
        "ru": "📚 Продолжить в Mini App",
        "tj": "📚 Дар Mini App идома додан",
    }
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=labels.get(lang, labels["ru"]),
                    web_app=WebAppInfo(url=course_study_miniapp_url(lang=lang)),
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

    async def send_due_reminders(self, bot: Bot) -> None:
        now = datetime.now(timezone.utc)

        # One query: all non-blocked users that have a Mini App profile.
        # Course Mini App reminders are a learning loop, not a paid-only feature:
        # trial/free/expired users can still use the limited course surfaces.
        rows = (
            await self.session.execute(
                select(CourseMiniAppProfile, User)
                .join(User, CourseMiniAppProfile.user_id == User.id)
                .where(User.status != "blocked")
            )
        ).all()
        if not rows:
            return

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
        for profile, user in rows:
            # Master switch: the user turned notifications off in the Mini App.
            if not getattr(profile, "notifications_enabled", True):
                continue
            lang = user.language if user.language in ("uz", "ru", "tj") else "ru"
            offset = offsets_by_user.get(int(profile.user_id), DEFAULT_OFFSET_MIN)
            local_now = self._local_now(offset, now)
            local_day = local_now.date()

            current_rank, members = ranks.get(int(profile.user_id), (0, []))

            # 1) Overtaken in the rating (rank got worse since last check).
            if current_rank and await self._maybe_overtaken(
                bot, profile, user, lang, current_rank, members, local_day
            ):
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
                continue

            day_start, day_end = self._local_day_bounds_utc(local_day, offset)
            if await self._daily_goal_completed_today(
                user, local_day, day_start, day_end
            ):
                continue

            minutes = int(profile.daily_minutes or 10)
            unfinished_lesson = await self._unfinished_lesson_today(user, day_start, day_end)
            if unfinished_lesson is not None:
                resolved = await self.templates.resolve(KEY_LESSON_UNFINISHED, lang)
                if resolved and await self._send(
                    bot,
                    user,
                    resolved,
                    lang,
                    {
                        "lesson": self._lesson_label(unfinished_lesson, lang),
                        "minutes": minutes,
                    },
                ):
                    self._mark_unfinished_lesson_sent(user, unfinished_lesson, local_day)
                    changed = True
                continue

            streak = int(profile.current_streak or 0)
            has_live_streak = streak >= 1 and profile.last_activity_date == local_day - timedelta(days=1)

            if has_live_streak:
                if profile.motivation_streak_date == local_day:
                    continue
                resolved = await self.templates.resolve(KEY_STREAK, lang)
                if resolved and await self._send(
                    bot, user, resolved, lang, {"streak": streak}
                ):
                    profile.motivation_streak_date = local_day
                    changed = True
            else:
                if profile.motivation_goal_date == local_day:
                    continue
                resolved = await self.templates.resolve(KEY_DAILY_GOAL, lang)
                if resolved and await self._send(
                    bot, user, resolved, lang, {"minutes": minutes}
                ):
                    profile.motivation_goal_date = local_day
                    changed = True

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

    async def _send(self, bot: Bot, user: User, resolved: dict, lang: str, fields: dict) -> bool:
        try:
            text = resolved["text"].format(**fields)
        except (KeyError, IndexError, ValueError):
            text = resolved["text"]
        media_type = resolved.get("media_type") or "none"
        media_path = resolved.get("media_path")
        markup = _button(lang)
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

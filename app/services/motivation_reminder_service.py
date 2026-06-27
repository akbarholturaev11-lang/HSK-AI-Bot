from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from aiogram import Bot
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.user import User
from app.services.course_gamification_service import CourseGamificationService
from app.services.notification_template_service import (
    CAPTION_MAX,
    KEY_DAILY_GOAL,
    KEY_OVERTAKEN,
    KEY_STREAK,
    NotificationTemplateService,
)

# On-disk root for admin-uploaded reminder media (see /uploads/notifications route).
MEDIA_ROOT = "app/static/uploads/notifications"

# Evening window (local time) during which "daily goal" / "streak" reminders fire.
GOAL_WINDOW_START_MIN = 20 * 60  # 20:00
GOAL_WINDOW_END_MIN = 21 * 60 + 30  # 21:30


def _button(lang: str):
    labels = {
        "uz": "📖 Darsni davom ettirish",
        "ru": "📖 Продолжить урок",
        "tj": "📖 Идома додани дарс",
    }
    builder = InlineKeyboardBuilder()
    builder.button(text=labels.get(lang, labels["ru"]), callback_data="course:continue")
    return builder.as_markup()


class MotivationReminderService:
    """Sends the three motivational reminders (overtaken / daily goal / streak).

    All three are gated to at most once per user per local day and pull their
    text/media from admin-editable templates. Triggers are computed from real
    Mini App data (XP leaderboard, last_activity_date, current_streak).
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.templates = NotificationTemplateService(session)

    @staticmethod
    def _local_now(offset_minutes: int, now: datetime) -> datetime:
        return now + timedelta(minutes=max(-720, min(840, int(offset_minutes or 0))))

    async def send_due_reminders(self, bot: Bot) -> None:
        now = datetime.now(timezone.utc)
        week_start_by_day: dict[date, date] = {}

        # One query: all active users that have a Mini App profile.
        rows = (
            await self.session.execute(
                select(CourseMiniAppProfile, User)
                .join(User, CourseMiniAppProfile.user_id == User.id)
                .where(User.status == "active")
            )
        ).all()
        if not rows:
            return

        # Weekly XP per user for the current week (drives league ranking).
        weekly_xp: dict[int, int] = {}
        days = {
            CourseGamificationService._local_day(p.timezone_offset_minutes, now)
            for p, _ in rows
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
            members.sort(key=lambda item: (item[2], int(item[0].xp_total or 0)), reverse=True)
            for index, (profile, _user, _wx) in enumerate(members, 1):
                ranks[int(profile.user_id)] = (index, members)

        changed = False
        for profile, user in rows:
            lang = user.language if user.language in ("uz", "ru", "tj") else "ru"
            offset = profile.timezone_offset_minutes
            local_now = self._local_now(offset, now)
            local_day = local_now.date()
            studied_today = profile.last_activity_date == local_day

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

            # 2/3) Evening goal/streak reminders — only if not studied today.
            now_min = local_now.hour * 60 + local_now.minute
            if studied_today or not (GOAL_WINDOW_START_MIN <= now_min <= GOAL_WINDOW_END_MIN):
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
                minutes = int(profile.daily_minutes or 10)
                resolved = await self.templates.resolve(KEY_DAILY_GOAL, lang)
                if resolved and await self._send(
                    bot, user, resolved, lang, {"minutes": minutes}
                ):
                    profile.motivation_goal_date = local_day
                    changed = True

        if changed:
            await self.session.commit()

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
        xp_gap = max(0, int(above_wx) - int(my_wx))
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
            return False

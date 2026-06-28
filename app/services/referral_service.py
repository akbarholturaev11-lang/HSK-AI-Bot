from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy import func, select

from app.bot.utils.i18n import t
from app.config import settings
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.referral import Referral
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.repositories.referral_repo import ReferralRepository
from app.services.ai_usage_budget_service import AIUsageBudgetService, REFERRAL_TRIAL_PLAN_TYPE
from app.services.course_gamification_service import CourseGamificationService
from app.services.course_miniapp_access_service import CourseMiniAppAccessService
from app.services.referral_notify_service import ReferralNotifyService
from app.services.subscription_progress_service import SubscriptionProgressService


REFERRAL_TRIAL_REQUIRED_ACTIVE = 5
REFERRAL_TRIAL_ACCESS_DAYS = 3
REFERRAL_TRIAL_AI_BUDGET_USD = 2.0


class ReferralService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.referral_repo = ReferralRepository(session)
        self.referral_notify_service = ReferralNotifyService()
        self.subscription_progress_service = SubscriptionProgressService(session)

    def _as_utc(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    async def _ensure_trial_counter_started_at(
        self,
        referrer,
        fallback: Optional[datetime] = None,
    ) -> datetime:
        started_at = referrer.referral_trial_count_started_at
        if started_at:
            return started_at

        started_at = fallback or datetime.now(timezone.utc)
        referrer.referral_trial_count_started_at = started_at
        await self.session.flush()
        return started_at

    async def get_trial_activation_progress(self, referrer) -> int:
        if not referrer:
            return 0

        started_at = await self._ensure_trial_counter_started_at(referrer)
        count = await self.referral_repo.count_active_since(
            referrer_telegram_id=referrer.telegram_id,
            started_at=started_at,
        )
        return min(count, REFERRAL_TRIAL_REQUIRED_ACTIVE)

    async def build_trial_progress_text(self, referrer) -> tuple[str, str]:
        await self.user_repo.ensure_referral_code(referrer)
        active_count = await self.get_trial_activation_progress(referrer)
        joined_count = await self.referral_repo.count_by_referrer(referrer.telegram_id)
        referral_link = f"https://t.me/{settings.BOT_USERNAME}?start={referrer.referral_code}"
        lang = referrer.language if referrer.language else "ru"
        return lang, t(
            "referral_invite_text",
            lang,
            link=referral_link,
            joined_count=joined_count,
            count=active_count,
            required=REFERRAL_TRIAL_REQUIRED_ACTIVE,
            days=REFERRAL_TRIAL_ACCESS_DAYS,
        )

    async def list_miniapp_referrals(
        self,
        referrer,
        *,
        timezone_offset_minutes: int | None = None,
        limit: int = 100,
    ) -> list[dict]:
        if not referrer:
            return []

        offset = max(-720, min(840, int(timezone_offset_minutes or 0)))
        day = CourseGamificationService._local_day(offset)
        week_start = CourseGamificationService._week_start(day)
        weekly = (
            select(
                CourseXpEvent.user_id.label("user_id"),
                func.sum(CourseXpEvent.xp).label("weekly_xp"),
            )
            .where(CourseXpEvent.week_start == week_start)
            .group_by(CourseXpEvent.user_id)
            .subquery()
        )
        max_items = max(1, min(200, int(limit or 100)))
        result = await self.session.execute(
            select(
                Referral.status,
                Referral.created_at,
                Referral.activated_at,
                User.id,
                User.telegram_id,
                User.full_name,
                User.username,
                User.status,
                User.payment_status,
                User.end_date,
                CourseMiniAppProfile.xp_total,
                CourseProgress.level,
                CourseProgress.completed_lessons_count,
                func.coalesce(weekly.c.weekly_xp, 0),
            )
            .join(User, User.telegram_id == Referral.invited_user_telegram_id)
            .outerjoin(CourseMiniAppProfile, CourseMiniAppProfile.user_id == User.id)
            .outerjoin(CourseProgress, CourseProgress.user_id == User.id)
            .outerjoin(weekly, weekly.c.user_id == User.id)
            .where(Referral.referrer_telegram_id == referrer.telegram_id)
            .order_by(Referral.created_at.desc(), User.id.asc())
            .limit(max_items)
        )

        items = []
        for index, (
            ref_status,
            created_at,
            activated_at,
            user_id,
            telegram_id,
            full_name,
            username,
            status,
            payment_status,
            end_date,
            xp_total,
            course_level,
            completed_lessons_count,
            weekly_xp,
        ) in enumerate(result.all(), 1):
            items.append(
                {
                    "rank": index,
                    "name": str(full_name or username or "HSK Student").strip()[:40],
                    "telegram_id": int(telegram_id) if telegram_id else None,
                    "username": str(username or "").strip().lstrip("@")[:32],
                    "status": str(ref_status or "pending"),
                    "joined_at": created_at.isoformat() if created_at else "",
                    "activated_at": activated_at.isoformat() if activated_at else "",
                    "xp": int(weekly_xp or 0),
                    "league_points": int(weekly_xp or 0),
                    "total_xp": int(xp_total or 0),
                    "course_level": str(course_level or "").strip()[:32],
                    "completed_lessons": int(completed_lessons_count or 0),
                    "is_paid": CourseMiniAppAccessService.is_paid_user(
                        SimpleNamespace(status=status, payment_status=payment_status, end_date=end_date)
                    ),
                    "is_current_user": False,
                    "user_id": int(user_id),
                }
            )
        return items

    async def remember_trial_progress_message(
        self,
        referrer,
        chat_id: int,
        message_id: int,
    ) -> None:
        await self.user_repo.set_referral_trial_progress_message(
            referrer,
            chat_id=chat_id,
            message_id=message_id,
        )
        await self.session.commit()

    async def update_trial_progress_message(self, bot: Bot, referrer) -> None:
        chat_id = getattr(referrer, "referral_trial_progress_chat_id", None)
        message_id = getattr(referrer, "referral_trial_progress_message_id", None)
        if not chat_id or not message_id:
            return

        _, text = await self.build_trial_progress_text(referrer)
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                disable_web_page_preview=True,
                parse_mode="HTML",
            )
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc).lower():
                return
            await self.user_repo.clear_referral_trial_progress_message(referrer)
        except TelegramForbiddenError:
            await self.user_repo.clear_referral_trial_progress_message(referrer)
        except Exception:
            return
        await self.session.commit()

    async def _grant_trial_access_if_ready(
        self,
        referrer,
        activated_at: Optional[datetime],
    ) -> bool:
        if not referrer:
            return False

        if referrer.payment_status == "approved":
            return False

        started_at = await self._ensure_trial_counter_started_at(
            referrer,
            fallback=activated_at,
        )
        active_count = await self.referral_repo.count_active_since(
            referrer_telegram_id=referrer.telegram_id,
            started_at=started_at,
        )
        if active_count < REFERRAL_TRIAL_REQUIRED_ACTIVE:
            return False

        now = datetime.now(timezone.utc)
        reward_end = now + timedelta(days=REFERRAL_TRIAL_ACCESS_DAYS)
        current_end = self._as_utc(referrer.end_date) if referrer.end_date else None
        if referrer.status == "active" and current_end and current_end > reward_end:
            reward_end = current_end

        referrer.status = "active"
        referrer.start_date = now
        referrer.end_date = reward_end
        referrer.questions_used = 0
        referrer.last_limit_reset_at = now
        referrer.daily_limit_offer_sent_at = None
        referrer.expiry_reminder_sent_at = None
        referrer.selected_plan_type = None
        referrer.pending_checkout_msg_id = None
        referrer.referral_trial_count_started_at = reward_end

        await AIUsageBudgetService(self.session).create_fixed_budget(
            telegram_id=referrer.telegram_id,
            plan_type=REFERRAL_TRIAL_PLAN_TYPE,
            amount=int(REFERRAL_TRIAL_AI_BUDGET_USD),
            currency="usd",
            total_budget_usd=REFERRAL_TRIAL_AI_BUDGET_USD,
            starts_at=now,
            ends_at=reward_end,
        )

        await self.session.flush()
        return True

    async def attach_referral_if_needed(
        self,
        invited_user_telegram_id: int,
        referral_code: Optional[str],
        bot: Optional[Bot] = None,
    ) -> None:
        if not referral_code:
            return

        invited_user = await self.user_repo.get_by_telegram_id(invited_user_telegram_id)
        if not invited_user:
            return

        if invited_user.referred_by_telegram_id:
            existing_referral = await self.referral_repo.get_by_invited_user_telegram_id(
                invited_user_telegram_id
            )
            if (
                existing_referral
                and existing_referral.status != "active"
                and int(getattr(invited_user, "questions_used", 0) or 0) >= 2
            ):
                await self.activate_referral_if_eligible(
                    bot=bot,
                    invited_user_telegram_id=invited_user_telegram_id,
                )
            return

        referrer = await self.user_repo.get_by_referral_code(referral_code)
        if not referrer:
            return

        if referrer.telegram_id == invited_user_telegram_id:
            return

        existing_referral = await self.referral_repo.get_by_invited_user_telegram_id(
            invited_user_telegram_id
        )
        if existing_referral:
            if (
                existing_referral.referrer_telegram_id == referrer.telegram_id
                and existing_referral.status != "active"
                and int(getattr(invited_user, "questions_used", 0) or 0) >= 2
            ):
                await self.activate_referral_if_eligible(
                    bot=bot,
                    invited_user_telegram_id=invited_user_telegram_id,
                )
            return

        await self.user_repo.set_referred_by(invited_user, referrer.telegram_id)
        await self.referral_repo.create(
            referrer_telegram_id=referrer.telegram_id,
            invited_user_telegram_id=invited_user_telegram_id,
        )
        await self.session.commit()
        if int(getattr(invited_user, "questions_used", 0) or 0) >= 2:
            await self.activate_referral_if_eligible(
                bot=bot,
                invited_user_telegram_id=invited_user_telegram_id,
            )
            return
        if bot:
            await self.update_trial_progress_message(bot, referrer)

    async def activate_referral_if_eligible(
        self,
        bot: Optional[Bot],
        invited_user_telegram_id: int,
    ) -> None:
        referral = await self.referral_repo.get_by_invited_user_telegram_id(
            invited_user_telegram_id,
            for_update=True,
        )
        if not referral:
            return

        if referral.status == "active":
            return

        invited_user = await self.user_repo.get_by_telegram_id(invited_user_telegram_id)
        if not invited_user:
            return

        if invited_user.questions_used < 2:
            return

        await self.referral_repo.activate(referral)

        referrer = await self.user_repo.get_by_telegram_id_for_update(
            referral.referrer_telegram_id
        )
        if not referrer:
            await self.session.commit()
            return

        bonus_given_now = False

        if not referral.bonus_granted:
            await self.user_repo.add_bonus_questions(referrer, 5)
            referral.bonus_granted = True
            bonus_given_now = True

        if (
            referrer.discount_offer_started_at
            and referral.activated_at
            and referral.activated_at >= referrer.discount_offer_started_at
            and not referral.counts_for_discount
        ):
            await self.user_repo.increment_discount_referral_count(referrer, 1)
            referral.counts_for_discount = True

        trial_activation_progress = await self.get_trial_activation_progress(referrer)
        trial_access_unlocked = await self._grant_trial_access_if_ready(
            referrer=referrer,
            activated_at=referral.activated_at,
        )

        await self.session.commit()
        if not bot:
            return

        await self.update_trial_progress_message(bot, referrer)

        if bonus_given_now and not referrer.discount_progress_message_id:
            await self.referral_notify_service.notify_bonus_received(
                bot=bot,
                referrer_user=referrer,
                count=trial_activation_progress,
                required=REFERRAL_TRIAL_REQUIRED_ACTIVE,
            )
        if trial_access_unlocked:
            await self.referral_notify_service.notify_trial_access_unlocked(
                bot=bot,
                referrer_user=referrer,
                days=REFERRAL_TRIAL_ACCESS_DAYS,
            )

        await self.subscription_progress_service.update_discount_progress_message(
            bot=bot,
            referrer_user=referrer,
        )

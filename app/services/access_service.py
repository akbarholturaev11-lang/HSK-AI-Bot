from datetime import datetime, timedelta, timezone
from typing import Tuple

from sqlalchemy import select

from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.repositories.message_repo import MessageRepository
from app.repositories.payment_repo import PaymentRepository
from app.services.ai_usage_budget_service import AIUsageBudgetService, REFERRAL_TRIAL_PLAN_TYPE

class AccessService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.message_repo = MessageRepository(session)
        self.payment_repo = PaymentRepository(session)

    def _as_utc(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _is_date_expired(self, dt) -> bool:
        if not dt:
            return False
        now = datetime.now(timezone.utc)
        if isinstance(dt, datetime):
            return self._as_utc(dt) <= now
        return dt < now.date()

    async def _downgrade_expired_user(self, user) -> None:
        user.status = "trial"
        user.end_date = None
        if getattr(user, "learning_mode", "qa") == "course":
            user.learning_mode = "qa"
            user.voice_mode = "none"
        await self.session.flush()

    def _is_paid_user(self, user) -> bool:
        return user.payment_status == "approved"

    def is_paid_user(self, user) -> bool:
        return bool(user) and self._is_paid_user(user)

    def trial_voice_used_today(self, user) -> bool:
        used_at = getattr(user, "trial_voice_used_at", None)
        if not used_at:
            return False
        return self._as_utc(used_at).date() == datetime.now(timezone.utc).date()

    def can_use_trial_voice(self, user) -> bool:
        return (
            user is not None
            and getattr(user, "status", "") == "trial"
            and not self.trial_voice_used_today(user)
        )

    async def mark_trial_voice_used(self, user) -> None:
        user.trial_voice_used_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def ensure_active_course_access(self, user) -> bool:
        if not user:
            return False

        if user.status == "active" and self._is_date_expired(user.end_date):
            await self._downgrade_expired_user(user)

        if user.status == "active":
            return True

        if user.status == "trial":
            return True

        if getattr(user, "learning_mode", "qa") == "course":
            user.learning_mode = "qa"
            user.voice_mode = "none"
            await self.session.flush()

        return False

    def _is_same_active_window(self, user, budget) -> bool:
        if not getattr(user, "start_date", None) or not getattr(user, "end_date", None):
            return False
        if not getattr(budget, "starts_at", None) or not getattr(budget, "ends_at", None):
            return False

        user_start = self._as_utc(user.start_date)
        user_end = self._as_utc(user.end_date)
        budget_start = self._as_utc(budget.starts_at)
        budget_end = self._as_utc(budget.ends_at)

        return (
            abs((user_start - budget_start).total_seconds()) <= 5
            and abs((user_end - budget_end).total_seconds()) <= 5
        )

    async def _get_current_referral_trial_budget(self, budget_service: AIUsageBudgetService, user):
        budget = await budget_service.get_latest_budget(
            user.telegram_id,
            plan_type=REFERRAL_TRIAL_PLAN_TYPE,
        )
        if budget and self._is_same_active_window(user, budget):
            return budget
        return None

    async def downgrade_non_paid_active_if_budget_depleted(self, telegram_id: int) -> bool:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user or user.status != "active" or self._is_paid_user(user):
            return False

        budget_service = AIUsageBudgetService(self.session)
        budget = await budget_service.get_active_budget(telegram_id)
        if not budget:
            budget = await self._get_current_referral_trial_budget(budget_service, user)
        if not budget:
            return False
        if budget.status == "active" and not budget_service.is_total_budget_depleted(budget):
            return False

        if budget.status == "active":
            await budget_service.expire_budget(budget)
        await self._downgrade_expired_user(user)
        return True

    async def _can_use_non_paid_active_budget(self, user) -> Tuple[bool, str, bool, bool]:
        budget_service = AIUsageBudgetService(self.session)
        budget = await budget_service.get_active_budget(user.telegram_id)
        if not budget:
            budget = await self._get_current_referral_trial_budget(budget_service, user)
            if not budget:
                return False, "", False, False

        if budget_service.is_total_budget_depleted(budget):
            if budget.status == "active":
                await budget_service.expire_budget(budget)
            await self._downgrade_expired_user(user)
            return False, "", True, True

        budget_access = await budget_service.can_use_ai(user.telegram_id)
        if not budget_access.allowed:
            if budget_access.budget_depleted:
                await self._downgrade_expired_user(user)
                return False, "", True, True
            return False, budget_access.message_key, False, True

        return True, "", False, True

    async def _can_use_daily_text_limit(self, user) -> Tuple[bool, str]:
        now = datetime.now(timezone.utc)

        if user.last_limit_reset_at is None or now - user.last_limit_reset_at >= timedelta(days=1):
            user.questions_used = 0
            user.last_limit_reset_at = now
            await self.user_repo.session.commit()

        if user.questions_used >= user.question_limit:
            bonus_balance = self.user_repo.get_bonus_balance(user)
            if bonus_balance <= 0:
                if not await self.user_repo.was_daily_limit_offer_sent_today(user):
                    await self.user_repo.mark_daily_limit_offer_sent(user)
                return False, "access_daily_limit_reached"

        return True, ""

    async def _can_use_ai_budget(self, telegram_id: int) -> Tuple[bool, str]:
        budget_access = await AIUsageBudgetService(self.session).can_use_ai(telegram_id)
        if not budget_access.allowed:
            return False, budget_access.message_key
        return True, ""

    async def _can_use_daily_image_limit(self, user) -> Tuple[bool, str]:
        now = datetime.now(timezone.utc)

        if not user.last_limit_reset_at:
            user.last_limit_reset_at = now
            user.questions_used = 0
        elif now - user.last_limit_reset_at >= timedelta(days=1):
            user.last_limit_reset_at = now
            user.questions_used = 0

        today_image_count = await self.message_repo.count_user_messages_today(
            user_id=user.id,
            content_type="image",
        )
        if today_image_count >= 2:
            return False, "access_daily_image_limit_reached"

        return True, ""

    async def downgrade_expired_active_users(self) -> tuple[int, list[int]]:
        result = await self.session.execute(
            select(User).where(
                User.status == "active",
                User.end_date.is_not(None),
            )
        )
        users = list(result.scalars().all())
        changed = 0
        ejected_course_telegram_ids = []

        for user in users:
            if not self._is_date_expired(user.end_date):
                continue
            was_in_course = getattr(user, "learning_mode", "qa") == "course"
            await self._downgrade_expired_user(user)
            if was_in_course:
                ejected_course_telegram_ids.append(user.telegram_id)
            changed += 1

        if changed:
            await self.session.commit()

        return changed, ejected_course_telegram_ids

    async def can_use_text_ai(
        self,
        telegram_id: int,
        *,
        enforce_daily_limit: bool = True,
    ) -> Tuple[bool, str]:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return False, "access_start_first"

        if user.status == "blocked":
            return False, "access_blocked"

        if user.status != "active":
            has_pending_payment = await self.payment_repo.has_pending_by_user(telegram_id)
            if has_pending_payment:
                return False, "access_payment_pending_review"

        if user.status == "active":
            if self._is_date_expired(user.end_date):
                await self._downgrade_expired_user(user)
                # falls through to trial logic below
            else:
                if not self._is_paid_user(user):
                    can_use, message_key, downgraded, uses_budget = await self._can_use_non_paid_active_budget(user)
                    if uses_budget and not downgraded:
                        return can_use, message_key
                    if not uses_budget:
                        if not enforce_daily_limit:
                            return True, ""
                        return await self._can_use_daily_text_limit(user)
                else:
                    return await self._can_use_ai_budget(telegram_id)

        if user.status == "expired":
            await self._downgrade_expired_user(user)
            # falls through to trial logic below

        if user.status == "trial":
            if not enforce_daily_limit:
                return True, ""
            return await self._can_use_daily_text_limit(user)

        return False, "access_start_first"

    async def can_use_image_ai(self, telegram_id: int) -> Tuple[bool, str]:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return False, "access_start_first"

        if user.status == "blocked":
            return False, "access_blocked"

        if user.status != "active":
            has_pending_payment = await self.payment_repo.has_pending_by_user(telegram_id)
            if has_pending_payment:
                return False, "access_payment_pending_review"

        if user.status == "active":
            if self._is_date_expired(user.end_date):
                await self._downgrade_expired_user(user)
                # falls through to trial logic below
            else:
                if not self._is_paid_user(user):
                    can_use, message_key, downgraded, uses_budget = await self._can_use_non_paid_active_budget(user)
                    if uses_budget and not downgraded:
                        return can_use, message_key
                    if not uses_budget:
                        return await self._can_use_daily_image_limit(user)
                else:
                    return await self._can_use_ai_budget(telegram_id)

        if user.status == "expired":
            await self._downgrade_expired_user(user)
            # falls through to trial logic below

        if user.status == "trial":
            return await self._can_use_daily_image_limit(user)

        return False, "access_start_first"

    async def consume_one_question(
        self,
        telegram_id: int,
        *,
        consume_daily_limit: bool = True,
    ) -> None:
        if not consume_daily_limit:
            return

        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return

        if user.status == "trial":

            now = datetime.now(timezone.utc)

            if not user.last_limit_reset_at:
                user.last_limit_reset_at = now
                user.questions_used = 0
            elif now - user.last_limit_reset_at >= timedelta(days=1):
                user.last_limit_reset_at = now
                user.questions_used = 0

            if user.questions_used >= user.question_limit:
                bonus = self.user_repo.get_bonus_balance(user)
                if bonus > 0:
                    await self.user_repo.consume_bonus_question(user)
                else:
                    return

        user.questions_used += 1
        await self.session.flush()

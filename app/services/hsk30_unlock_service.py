from __future__ import annotations

from datetime import datetime, timezone

from app.repositories.bot_setting_repo import BotSettingRepository
from app.repositories.course_track_state_repo import CourseTrackStateRepository
from app.services.course_levels import TRACK_HSK30
from app.services.hsk30_feature_service import Hsk30FeatureService
from app.services.subscription_currency_service import SubscriptionCurrencyService
from app.services.user_access_state_service import UserAccessStateService


HSK30_UNLOCK_PLAN_TYPE = "hsk30_unlock"
HSK30_UNLOCK_PRICE_KEY = "hsk30_unlock_price_tjs"
DEFAULT_HSK30_UNLOCK_PRICE_TJS = 10
MIN_HSK30_UNLOCK_PRICE_TJS = 1
MAX_HSK30_UNLOCK_PRICE_TJS = 10_000


class Hsk30UnlockService:
    def __init__(self, session):
        self.session = session
        self.setting_repo = BotSettingRepository(session)
        self.state_repo = CourseTrackStateRepository(session)
        self.currency = SubscriptionCurrencyService(session)
        self.feature = Hsk30FeatureService(session)

    async def price_tjs(self) -> int:
        raw = await self.setting_repo.get(HSK30_UNLOCK_PRICE_KEY)
        try:
            value = int(str(raw).strip()) if raw is not None else DEFAULT_HSK30_UNLOCK_PRICE_TJS
        except (TypeError, ValueError):
            value = DEFAULT_HSK30_UNLOCK_PRICE_TJS
        if not MIN_HSK30_UNLOCK_PRICE_TJS <= value <= MAX_HSK30_UNLOCK_PRICE_TJS:
            return DEFAULT_HSK30_UNLOCK_PRICE_TJS
        return value

    async def set_price_tjs(self, amount: int) -> int:
        amount = int(amount)
        if not MIN_HSK30_UNLOCK_PRICE_TJS <= amount <= MAX_HSK30_UNLOCK_PRICE_TJS:
            raise ValueError("invalid_hsk30_unlock_price")
        await self.setting_repo.set(HSK30_UNLOCK_PRICE_KEY, str(amount))
        return amount

    async def is_permanently_unlocked(self, user) -> bool:
        if not user:
            return False
        row = await self.state_repo.get(int(user.id), TRACK_HSK30)
        return bool(row and row.unlocked_at)

    async def payment_eligibility(self, user) -> dict:
        feature_enabled = await self.feature.is_enabled()
        permanently_unlocked = await self.is_permanently_unlocked(user)
        paid_access = UserAccessStateService.is_paid(user)

        if not feature_enabled:
            reason = "hsk30_disabled"
            allowed = False
        elif permanently_unlocked:
            reason = "hsk30_already_unlocked"
            allowed = False
        elif paid_access:
            reason = "hsk30_subscription_active"
            allowed = False
        else:
            reason = "payment_required"
            allowed = True

        return {
            "allowed": allowed,
            "reason": reason,
            "feature_enabled": feature_enabled,
            "paid_access": paid_access,
            "permanently_unlocked": permanently_unlocked,
            "price_tjs": await self.price_tjs(),
        }

    async def quote(self, *, card_country: str | None = None) -> dict:
        amount = await self.price_tjs()
        local = await self.currency.quote_card_amount(amount, card_country)
        return {
            "plan_type": HSK30_UNLOCK_PLAN_TYPE,
            "base_amount": amount,
            "base_currency": "TJS",
            "pay_amount": local.amount,
            "pay_currency": local.currency,
            "card_country": local.country,
            "exchange_rate": local.exchange_rate,
            "exchange_rate_source": local.source,
            "one_time": True,
            "permanent": True,
            "discount_applied": False,
            "discount_percent": 0,
            "discount_source": "none",
        }

    async def grant(self, *, user, payment) -> bool:
        if not user or not payment:
            return False
        if str(getattr(payment, "plan_type", "") or "") != HSK30_UNLOCK_PLAN_TYPE:
            return False
        if str(getattr(payment, "payment_status", "") or "") != "approved":
            return False
        if int(getattr(payment, "user_telegram_id", 0) or 0) != int(
            getattr(user, "telegram_id", 0) or 0
        ):
            return False

        row = await self.state_repo.get(
            int(user.id),
            TRACK_HSK30,
            for_update=True,
        )
        if row is None:
            row = await self.state_repo.create(
                user_id=int(user.id),
                track=TRACK_HSK30,
                level="nhsk1",
                completed_lessons_count=0,
            )

        if row.unlocked_at is None:
            row.unlocked_at = datetime.now(timezone.utc)
        if row.unlock_payment_id is None:
            row.unlock_payment_id = int(payment.id)
        await self.session.flush()
        return True

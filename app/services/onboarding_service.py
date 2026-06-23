from typing import Optional, Tuple

from aiogram import Bot
from sqlalchemy.exc import IntegrityError

from app.repositories.user_repo import UserRepository
from app.db.models.user import User
from app.services.referral_service import ReferralService
from app.services.partner_service import PARTNER_LINK_PREFIX, PartnerService


ONBOARDING_LANGUAGE_MODE = "onboard_lang"
ONBOARDING_MODE_CHOICE_MODE = "onboard_mode"


def onboarding_stage(user: User | None) -> Optional[str]:
    if not user:
        return None
    mode = getattr(user, "learning_mode", None)
    if mode == ONBOARDING_LANGUAGE_MODE:
        return "language"
    if mode == ONBOARDING_MODE_CHOICE_MODE:
        return "mode"
    return None


def can_attach_start_referral(user: User | None) -> bool:
    if not user:
        return False
    if onboarding_stage(user):
        return True
    if getattr(user, "referred_by_telegram_id", None):
        return False
    if getattr(user, "payment_status", None) == "approved":
        return False
    return True


class OnboardingService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.referral_service = ReferralService(session)

    async def _attach_referral_if_needed(
        self,
        *,
        telegram_id: int,
        referral_code: Optional[str],
        bot: Optional[Bot] = None,
    ) -> None:
        if referral_code and referral_code.startswith(PARTNER_LINK_PREFIX):
            await PartnerService(self.session).attach_referral_if_needed(
                invited_user_telegram_id=telegram_id,
                referral_code=referral_code,
            )
            return

        await self.referral_service.attach_referral_if_needed(
            invited_user_telegram_id=telegram_id,
            referral_code=referral_code,
            bot=bot,
        )

    async def get_or_create_user(
        self,
        telegram_id: int,
        full_name: Optional[str] = None,
        username: Optional[str] = None,
        referral_code: Optional[str] = None,
        bot: Optional[Bot] = None,
    ) -> Tuple[User, bool]:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if user:
            changed = False
            if full_name and user.full_name != full_name:
                user.full_name = full_name
                changed = True
            if username and user.username != username:
                user.username = username
                changed = True
            if changed:
                await self.session.flush()
            if referral_code and can_attach_start_referral(user):
                await self._attach_referral_if_needed(
                    telegram_id=telegram_id,
                    referral_code=referral_code,
                    bot=bot,
                )
                await self.session.commit()
            return user, False

        try:
            user = await self.user_repo.create(
                telegram_id=telegram_id,
                full_name=full_name,
                username=username,
                language="tj",
                level="beginner",
                learning_mode=ONBOARDING_LANGUAGE_MODE,
            )
        except IntegrityError:
            await self.session.rollback()
            user = await self.user_repo.get_by_telegram_id(telegram_id)
            return user, False

        await self._attach_referral_if_needed(
            telegram_id=telegram_id,
            referral_code=referral_code,
            bot=bot,
        )
        await self.session.commit()

        user = await self.user_repo.get_by_telegram_id(telegram_id)
        return user, True

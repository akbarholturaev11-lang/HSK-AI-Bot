from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.bot.utils.i18n import t
from app.config import settings
from app.repositories.user_repo import UserRepository
from app.services.referral_service import (
    REFERRAL_TRIAL_ACCESS_DAYS,
    REFERRAL_TRIAL_REQUIRED_ACTIVE,
    ReferralService,
)


router = Router()


@router.callback_query(F.data == "referral:invite")
async def referral_invite_handler(callback: CallbackQuery, session):
    user_repo = UserRepository(session)
    referral_service = ReferralService(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    if not user:
        await callback.answer()
        return

    await user_repo.ensure_referral_code(user)
    trial_count = await referral_service.get_trial_activation_progress(user)
    await session.commit()

    referral_link = f"https://t.me/{settings.BOT_USERNAME}?start={user.referral_code}"

    lang = user.language if user.language else "ru"
    text = t(
        "referral_invite_text",
        lang,
        link=referral_link,
        count=trial_count,
        required=REFERRAL_TRIAL_REQUIRED_ACTIVE,
        days=REFERRAL_TRIAL_ACCESS_DAYS,
    )

    await callback.answer()
    await callback.message.answer(text, disable_web_page_preview=True, parse_mode="HTML")

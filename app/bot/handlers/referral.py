from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.repositories.user_repo import UserRepository
from app.services.referral_service import ReferralService


router = Router()


async def _build_referral_invite_text(session, user) -> tuple[str, str]:
    referral_service = ReferralService(session)
    text = await referral_service.build_trial_progress_text(user)
    await session.commit()
    return text


@router.callback_query(F.data == "referral:invite")
async def referral_invite_handler(callback: CallbackQuery, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)

    if not user:
        await callback.answer()
        return

    _, text = await _build_referral_invite_text(session, user)

    await callback.answer()
    sent = await callback.message.answer(
        text,
        disable_web_page_preview=True,
        parse_mode="HTML",
    )
    await ReferralService(session).remember_trial_progress_message(
        user,
        chat_id=sent.chat.id,
        message_id=sent.message_id,
    )

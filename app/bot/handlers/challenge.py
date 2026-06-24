from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.services.course_challenge_service import CourseChallengeService

router = Router()


@router.callback_query(F.data.startswith("challenge:"))
async def challenge_callback(callback: CallbackQuery, session):
    parts = str(callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer("Noto'g'ri belashuv tugmasi", show_alert=True)
        return
    _, action, raw_id = parts
    try:
        challenge_id = int(raw_id)
    except ValueError:
        await callback.answer("Belashuv topilmadi", show_alert=True)
        return
    if action not in {"accept", "reject"}:
        await callback.answer("Noto'g'ri amal", show_alert=True)
        return

    result = await CourseChallengeService(session).respond(
        int(callback.from_user.id),
        challenge_id,
        action,
        bot=callback.bot,
    )
    await session.commit()
    if not result.get("ok"):
        await callback.answer("Belashuv allaqachon yopilgan yoki topilmadi", show_alert=True)
        return
    text = "Belashuv qabul qilindi. Mini App profilidan boshlang." if action == "accept" else "Belashuv rad qilindi."
    await callback.answer(text, show_alert=True)

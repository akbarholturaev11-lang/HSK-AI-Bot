from aiogram import Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.types import ChatMemberUpdated

from app.db.session import async_session_maker
from app.repositories.user_repo import UserRepository
from app.services.bot_block_status_service import BotBlockStatusService


router = Router()


@router.my_chat_member()
async def track_private_bot_membership(update: ChatMemberUpdated) -> None:
    """Track explicit private-chat bot block/unblock transitions from Telegram."""
    if update.chat.type != ChatType.PRIVATE:
        return

    new_status = update.new_chat_member.status
    if new_status not in {ChatMemberStatus.KICKED, ChatMemberStatus.MEMBER}:
        return

    telegram_id = int(update.chat.id)
    async with async_session_maker() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            return

        blocks = BotBlockStatusService(session)
        if new_status == ChatMemberStatus.KICKED:
            await blocks.mark_user_blocked(
                user,
                reason="my_chat_member_blocked",
                checked_at=update.date,
            )
        else:
            await blocks.mark_user_unblocked(
                user,
                reason="my_chat_member_unblocked",
                checked_at=update.date,
            )

        await session.commit()

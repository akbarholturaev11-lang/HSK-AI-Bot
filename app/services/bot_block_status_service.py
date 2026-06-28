import asyncio
from datetime import datetime, timedelta, timezone

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy import or_, select

from app.config import settings
from app.db.models.user import User


class BotBlockStatusService:
    """Tracks users who blocked the Telegram bot without messaging them."""

    CHECK_INTERVAL = timedelta(days=1)

    def __init__(self, session):
        self.session = session

    @staticmethod
    def is_bot_blocked(user) -> bool:
        blocked_at = getattr(user, "bot_blocked_at", None)
        if not blocked_at:
            return False
        unblocked_at = getattr(user, "bot_unblocked_at", None)
        return not unblocked_at or unblocked_at < blocked_at

    async def mark_user_blocked(
        self,
        user,
        *,
        reason: str = "telegram_forbidden",
        checked_at: datetime | None = None,
    ) -> None:
        now = checked_at or datetime.now(timezone.utc)
        user.bot_blocked_at = now
        user.last_bot_block_check_at = now
        user.bot_block_reason = str(reason or "telegram_forbidden")[:120]
        await self.session.flush()

    async def mark_user_unblocked(
        self,
        user,
        *,
        checked_at: datetime | None = None,
    ) -> None:
        now = checked_at or datetime.now(timezone.utc)
        if self.is_bot_blocked(user):
            user.bot_unblocked_at = now
        user.last_bot_block_check_at = now
        await self.session.flush()

    async def mark_telegram_id_unblocked(self, telegram_id: int) -> bool:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            return False
        await self.mark_user_unblocked(user)
        return True

    async def handle_send_exception(self, telegram_id: int, exc: Exception, *, reason: str = "send_failed") -> bool:
        if not isinstance(exc, TelegramForbiddenError):
            return False
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            return False
        await self.mark_user_blocked(user, reason=reason)
        return True

    async def scan_due_users(self, bot, *, limit: int = 100, pause_seconds: float = 0.03) -> int:
        now = datetime.now(timezone.utc)
        cutoff = now - self.CHECK_INTERVAL
        query = (
            select(User)
            .where(
                or_(
                    User.last_bot_block_check_at.is_(None),
                    User.last_bot_block_check_at < cutoff,
                )
            )
            .order_by(User.last_bot_block_check_at.asc(), User.id.asc())
            .limit(max(1, int(limit or 1)))
        )
        admin_ids = settings.admin_id_list
        if admin_ids:
            query = query.where(User.telegram_id.notin_(admin_ids))

        result = await self.session.execute(query)
        users = list(result.scalars().all())
        checked = 0

        for user in users:
            try:
                await bot.get_chat(user.telegram_id)
            except TelegramForbiddenError:
                await self.mark_user_blocked(user, reason="daily_get_chat_forbidden", checked_at=now)
            except TelegramBadRequest:
                user.last_bot_block_check_at = now
                await self.session.flush()
            except Exception:
                continue
            else:
                await self.mark_user_unblocked(user, checked_at=now)
            checked += 1
            if pause_seconds:
                await asyncio.sleep(pause_seconds)

        if checked:
            await self.session.commit()
        return checked

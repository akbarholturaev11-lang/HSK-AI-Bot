import asyncio
from datetime import datetime, timedelta, timezone

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy import or_, select

from app.config import settings
from app.db.models.user import User
from app.db.models.bot_reachability_event import BotReachabilityEvent
from app.db.models.bot_outbound_event import BotOutboundEvent


class BotBlockStatusService:
    """Tracks whether Telegram can currently deliver bot messages to a user.

    `bot_blocked_at` is the first confirmed/detected time of the CURRENT
    unreachable episode. Repeated failed sends must not move that timestamp or
    replace the original detection source; otherwise churn attribution becomes
    meaningless. A later confirmed unblock closes the episode.
    """

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

        # Preserve the first timestamp/source inside one block episode.
        # If the user was previously unblocked, this starts a NEW episode.
        if not self.is_bot_blocked(user):
            source = str(reason or "telegram_forbidden")[:120]
            user.bot_blocked_at = now
            user.bot_block_reason = source
            self.session.add(
                BotReachabilityEvent(
                    user_id=getattr(user, "id", None),
                    telegram_id=int(user.telegram_id),
                    event_type="blocked",
                    source=source,
                    created_at=now,
                )
            )

        user.last_bot_block_check_at = now
        await self.session.flush()

    async def mark_user_unblocked(
        self,
        user,
        *,
        reason: str = "confirmed_reachable",
        checked_at: datetime | None = None,
    ) -> None:
        now = checked_at or datetime.now(timezone.utc)
        if self.is_bot_blocked(user):
            source = str(reason or "confirmed_reachable")[:120]
            user.bot_unblocked_at = now
            self.session.add(
                BotReachabilityEvent(
                    user_id=getattr(user, "id", None),
                    telegram_id=int(user.telegram_id),
                    event_type="unblocked",
                    source=source,
                    created_at=now,
                )
            )
        user.last_bot_block_check_at = now
        await self.session.flush()

    async def mark_user_reachable(
        self,
        user,
        *,
        reason: str = "delivery_success",
        checked_at: datetime | None = None,
    ) -> None:
        """A successful Telegram delivery is proof the bot is not blocked."""
        await self.mark_user_unblocked(user, reason=reason, checked_at=checked_at)

    async def mark_telegram_id_unblocked(self, telegram_id: int) -> bool:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            return False
        await self.mark_user_unblocked(user)
        return True

    async def handle_send_success(
        self,
        user,
        *,
        reason: str = "delivery_success",
        sent_at: datetime | None = None,
    ) -> None:
        if not user:
            return
        now = sent_at or datetime.now(timezone.utc)
        source = str(reason or "delivery_success")[:120]
        self.session.add(
            BotOutboundEvent(
                user_id=getattr(user, "id", None),
                telegram_id=int(user.telegram_id),
                source=source,
                status="sent",
                created_at=now,
            )
        )
        if self.is_bot_blocked(user):
            await self.mark_user_reachable(user, reason="delivery_success", checked_at=now)
        else:
            user.last_bot_block_check_at = now
            await self.session.flush()

    async def handle_send_exception(
        self,
        telegram_id: int,
        exc: Exception,
        *,
        reason: str = "send_failed",
    ) -> bool:
        # Only TelegramForbiddenError is reachability evidence. Timeouts,
        # rate limits and generic BadRequest must never inflate "bot blocked".
        if not isinstance(exc, TelegramForbiddenError):
            return False
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            return False
        now = datetime.now(timezone.utc)
        source = str(reason or "send_failed")[:120]
        self.session.add(
            BotOutboundEvent(
                user_id=getattr(user, "id", None),
                telegram_id=int(user.telegram_id),
                source=source,
                status="forbidden",
                created_at=now,
            )
        )
        await self.mark_user_blocked(user, reason=source, checked_at=now)
        return True

    async def scan_due_users(self, bot, *, limit: int = 100, pause_seconds: float = 0.03) -> int:
        """Legacy diagnostics only.

        Production block/unblock state is now driven by Telegram
        `my_chat_member` updates plus failed/successful real deliveries.
        This method remains for tests/manual diagnostics, but the scheduler no
        longer uses it.
        """
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
                await self.mark_user_blocked(
                    user,
                    reason="diagnostic_get_chat_forbidden",
                    checked_at=now,
                )
            except TelegramBadRequest:
                user.last_bot_block_check_at = now
                await self.session.flush()
            except Exception:
                continue
            else:
                # getChat success does NOT prove unblocked.
                user.last_bot_block_check_at = now
                await self.session.flush()
            checked += 1
            if pause_seconds:
                await asyncio.sleep(pause_seconds)

        if checked:
            await self.session.commit()
        return checked

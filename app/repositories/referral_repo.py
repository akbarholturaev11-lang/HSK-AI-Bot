from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import and_, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.referral import Referral
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.account_identity import account_user_id, actual_telegram_id


def referral_owner_clause(role: str, actor):
    """Canonical ownership wins; a NULL Telegram ID never identifies anyone."""
    canonical = getattr(Referral, f"{role}_user_id")
    telegram = getattr(Referral, "invited_user_telegram_id" if role == "invited" else "referrer_telegram_id")
    uid, tid = account_user_id(actor), actual_telegram_id(actor)
    legacy = and_(canonical.is_(None), telegram == tid) if tid else false()
    return or_(canonical == uid, legacy) if uid is not None else legacy


def referral_user_join(role: str):
    canonical = getattr(Referral, f"{role}_user_id")
    telegram = getattr(Referral, "invited_user_telegram_id" if role == "invited" else "referrer_telegram_id")
    return or_(User.id == canonical, and_(canonical.is_(None), telegram > 0, telegram == User.telegram_id))


class ReferralRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _actor(self, actor):
        user = await UserRepository(self.session).get_by_actor(actor)
        return user if user is not None else actor

    async def _owner(self, role, actor):
        return referral_owner_clause(role, await self._actor(actor))

    async def get_referrer(self, referral, *, lock=False):
        if referral.referrer_user_id is not None:
            predicate = User.id == referral.referrer_user_id
        elif referral.referrer_telegram_id and int(referral.referrer_telegram_id) > 0:
            predicate = User.telegram_id == referral.referrer_telegram_id
        else:
            return None
        query = select(User).where(predicate)
        if lock:
            # Reward only changes non-key fields. NO KEY UPDATE serializes
            # concurrent rewards while remaining compatible with the FK key
            # shares held by successful native Message/Assistant inserts.
            query = query.with_for_update(key_share=True).execution_options(populate_existing=True)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_by_invited_user_telegram_id(self, invited_user_telegram_id, *, for_update=False) -> Optional[Referral]:
        query = select(Referral).where(await self._owner("invited", invited_user_telegram_id))
        if for_update:
            query = query.with_for_update().execution_options(populate_existing=True)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def create(self, referrer_telegram_id, invited_user_telegram_id, discount_platform="unknown") -> Referral:
        referrer = await self._actor(referrer_telegram_id)
        invited = await self._actor(invited_user_telegram_id)
        if account_user_id(referrer) is None or account_user_id(invited) is None:
            raise ValueError("Referral requires two persisted accounts")
        referral = Referral(
            referrer_user_id=account_user_id(referrer), invited_user_id=account_user_id(invited),
            referrer_telegram_id=actual_telegram_id(referrer), invited_user_telegram_id=actual_telegram_id(invited),
            status="pending", bonus_granted=False, counts_for_discount=False,
            discount_platform=discount_platform, created_at=datetime.now(timezone.utc),
        )
        self.session.add(referral)
        await self.session.flush()
        return referral

    async def activate(self, referral: Referral) -> Referral:
        referral.status = "active"
        referral.activated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return referral

    async def list_active_after_datetime(self, referrer_telegram_id, started_at: datetime) -> List[Referral]:
        result = await self.session.execute(select(Referral).where(
            await self._owner("referrer", referrer_telegram_id), Referral.status == "active",
            Referral.activated_at.is_not(None), Referral.activated_at >= started_at,
        ).order_by(Referral.activated_at.asc()))
        return list(result.scalars().all())

    async def count_by_referrer(self, referrer_telegram_id) -> int:
        return await self.session.scalar(select(func.count()).select_from(Referral).where(
            await self._owner("referrer", referrer_telegram_id))) or 0

    async def count_active_since(self, referrer_telegram_id, started_at: datetime) -> int:
        return await self.session.scalar(select(func.count()).select_from(Referral).where(
            await self._owner("referrer", referrer_telegram_id), Referral.status == "active",
            Referral.activated_at.is_not(None), Referral.activated_at >= started_at,
        )) or 0

    async def count_discount_qualified_since(self, referrer_telegram_id, started_at: datetime) -> int:
        return await self.session.scalar(select(func.count()).select_from(Referral).where(
            await self._owner("referrer", referrer_telegram_id), Referral.discount_qualified_at.is_not(None),
            Referral.discount_qualified_at >= started_at,
        )) or 0

    async def get_by_pair(self, referrer_telegram_id, invited_user_telegram_id):
        return (await self.session.execute(select(Referral).where(
            await self._owner("referrer", referrer_telegram_id),
            await self._owner("invited", invited_user_telegram_id),
        ))).scalar_one_or_none()

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import and_, false, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.payment import Payment
from app.db.models.user import User
from app.services.account_identity import actual_telegram_id, owner_clause


_UNSET = object()


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def resolve_owner(self, actor, *, lock: bool = False) -> Optional[User]:
        """A User names its canonical account; an integer is only a real TG ID.

        Checkout must lock before its pending-payment check and retain that
        transaction through create/receipt submission. create reuses the lock.
        """
        if hasattr(actor, "id") and hasattr(actor, "telegram_id"):
            uid = getattr(actor, "id", None)
            if uid is None or int(uid) <= 0:
                return None
            query = select(User).where(User.id == int(uid))
        else:
            telegram_id = actual_telegram_id(actor)
            if telegram_id is None:
                return None
            query = select(User).where(User.telegram_id == telegram_id)
        if lock:
            query = query.with_for_update()
        result = await self.session.execute(query.execution_options(populate_existing=True))
        return result.scalar_one_or_none()

    async def get_owner(self, payment: Payment, *, lock: bool = False) -> Optional[User]:
        """Resolve trusted payment ownership without reassigning retained facts."""
        if payment.user_id is not None:
            query = select(User).where(User.id == payment.user_id)
            if lock:
                query = query.with_for_update()
            result = await self.session.execute(query.execution_options(populate_existing=True))
            return result.scalar_one_or_none()
        return await self.resolve_owner(payment.user_telegram_id, lock=lock)

    @staticmethod
    def is_owned_by(payment: Payment, user: User) -> bool:
        if not user or not payment:
            return False
        if payment.user_id is not None:
            return payment.user_id == user.id
        telegram_id = actual_telegram_id(user)
        return telegram_id is not None and actual_telegram_id(payment.user_telegram_id) == telegram_id

    async def _owner_filter(self, actor):
        user = await self.resolve_owner(actor)
        if user is not None:
            return owner_clause(Payment, user)
        if not hasattr(actor, "id"):
            telegram_id = actual_telegram_id(actor)
            if telegram_id is not None:
                return and_(Payment.user_id.is_(None), Payment.user_telegram_id == telegram_id)
        return false()

    async def create(
        self,
        user_telegram_id: int | User,
        plan_type: str,
        amount: int,
        currency: str = "somoni",
        screenshot_file_id: Optional[str] = None,
        payment_status: str = "pending",
        payment_method: Optional[str] = None,
        base_amount: Optional[int] = None,
        discount_source: str = "none",
        discount_percent: int = 0,
        discount_campaign_id: Optional[int] = None,
        discount_title: Optional[str] = None,
        discount_details: Optional[str] = None,
        card_country: Optional[str] = None,
        local_amount: Optional[str] = None,
        local_currency: Optional[str] = None,
        exchange_rate: Optional[str] = None,
        source: str = "telegram_bot",
    ) -> Payment:
        user = await self.resolve_owner(user_telegram_id, lock=True)
        if user is None:
            raise ValueError("payment_owner_not_found")
        payment = Payment(
            user_id=user.id,
            user_telegram_id=actual_telegram_id(user),
            plan_type=plan_type,
            payment_method=payment_method,
            source=source,
            base_amount=base_amount,
            amount=amount,
            currency=currency,
            payment_status=payment_status,
            screenshot_file_id=screenshot_file_id,
            discount_source=discount_source,
            discount_percent=discount_percent,
            discount_campaign_id=discount_campaign_id,
            discount_title=discount_title,
            discount_details=discount_details,
            card_country=card_country,
            local_amount=local_amount,
            local_currency=local_currency,
            exchange_rate=exchange_rate,
            submitted_at=datetime.now(timezone.utc),
        )
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_by_id(self, payment_id: int, *, actor=_UNSET) -> Optional[Payment]:
        query = select(Payment).where(Payment.id == payment_id)
        if actor is not _UNSET:
            query = query.where(await self._owner_filter(actor))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_draft_by_user(
        self,
        user_telegram_id: int | User,
    ) -> Optional[Payment]:
        result = await self.session.execute(
            select(Payment)
            .where(await self._owner_filter(user_telegram_id))
            .where(Payment.payment_status == "draft")
            .order_by(Payment.submitted_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_checkout(
        self,
        payment: Payment,
        *,
        plan_type: str,
        amount: int,
        currency: str,
        payment_method: Optional[str],
        base_amount: Optional[int],
        payment_status: Optional[str] = None,
        screenshot_file_id: Optional[str] = None,
        discount_source: str = "none",
        discount_percent: int = 0,
        discount_campaign_id: Optional[int] = None,
        discount_title: Optional[str] = None,
        discount_details: Optional[str] = None,
        card_country: Optional[str] = None,
        local_amount: Optional[str] = None,
        local_currency: Optional[str] = None,
        exchange_rate: Optional[str] = None,
        actor=_UNSET,
    ) -> bool:
        if payment_status is not None and payment_status not in {"draft", "pending"}:
            raise ValueError("payment_status_invalid")
        values = dict(
            plan_type=plan_type, payment_method=payment_method,
            base_amount=base_amount, amount=amount, currency=currency,
            discount_source=discount_source, discount_percent=discount_percent,
            discount_campaign_id=discount_campaign_id, discount_title=discount_title,
            discount_details=discount_details, card_country=card_country,
            local_amount=local_amount, local_currency=local_currency,
            exchange_rate=exchange_rate, submitted_at=datetime.now(timezone.utc),
        )
        if payment_status:
            values["payment_status"] = payment_status
        if screenshot_file_id:
            values["screenshot_file_id"] = screenshot_file_id
        statement = update(Payment).where(
            Payment.id == payment.id, Payment.payment_status.in_(("draft", "pending"))
        )
        if actor is not _UNSET:
            statement = statement.where(await self._owner_filter(actor))
        result = await self.session.execute(statement.values(**values).returning(Payment.id)
            .execution_options(synchronize_session="fetch"))
        await self.session.flush()
        return result.scalar_one_or_none() is not None

    async def get_latest_pending_by_user(
        self,
        user_telegram_id: int | User,
    ) -> Optional[Payment]:
        result = await self.session.execute(
            select(Payment)
            .where(await self._owner_filter(user_telegram_id))
            .where(Payment.payment_status == "pending")
            .order_by(Payment.submitted_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_pending_by_user_and_plan(
        self,
        user_telegram_id: int | User,
        plan_type: str,
    ) -> Optional[Payment]:
        result = await self.session.execute(
            select(Payment)
            .where(await self._owner_filter(user_telegram_id))
            .where(Payment.payment_status == "pending")
            .where(Payment.plan_type == plan_type)
            .order_by(Payment.submitted_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def has_rejected_by_user_and_plan(
        self,
        user_telegram_id: int | User,
        plan_type: str,
    ) -> bool:
        result = await self.session.execute(
            select(Payment.id)
            .where(await self._owner_filter(user_telegram_id))
            .where(Payment.plan_type == plan_type)
            .where(Payment.payment_status == "rejected")
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def has_pending_by_user(
        self,
        user_telegram_id: int | User,
    ) -> bool:
        result = await self.session.execute(
            select(Payment.id)
            .where(await self._owner_filter(user_telegram_id))
            .where(Payment.payment_status == "pending")
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def list_by_user(
        self,
        user_telegram_id: int | User,
        limit: int = 20,
    ) -> List[Payment]:
        result = await self.session.execute(
            select(Payment)
            .where(await self._owner_filter(user_telegram_id))
            .order_by(Payment.submitted_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_screenshot(
        self,
        payment: Payment,
        screenshot_file_id: str,
        *, actor=_UNSET,
    ) -> bool:
        statement = update(Payment).where(
            Payment.id == payment.id, Payment.payment_status.in_(("draft", "pending"))
        )
        if actor is not _UNSET:
            statement = statement.where(await self._owner_filter(actor))
        result = await self.session.execute(statement.values(
            screenshot_file_id=screenshot_file_id, payment_status="pending",
            submitted_at=datetime.now(timezone.utc),
        ).returning(Payment.id).execution_options(synchronize_session="fetch"))
        await self.session.flush()
        return result.scalar_one_or_none() is not None

    async def approve(
        self,
        payment: Payment,
        admin_comment: Optional[str] = None,
        *, actor=_UNSET,
    ) -> bool:
        statement = (
            update(Payment)
            .where(Payment.id == payment.id)
            .where(Payment.payment_status == "pending")
        )
        if actor is not _UNSET:
            statement = statement.where(await self._owner_filter(actor))
        result = await self.session.execute(
            statement
            .values(
                payment_status="approved",
                admin_comment=admin_comment,
                reviewed_at=datetime.now(timezone.utc),
            )
            .returning(Payment.id)
            .execution_options(synchronize_session="fetch")
        )
        await self.session.flush()
        return result.scalar_one_or_none() is not None

    async def reject(
        self,
        payment: Payment,
        admin_comment: Optional[str] = None,
        *, actor=_UNSET,
    ) -> bool:
        statement = (
            update(Payment)
            .where(Payment.id == payment.id)
            .where(Payment.payment_status == "pending")
        )
        if actor is not _UNSET:
            statement = statement.where(await self._owner_filter(actor))
        result = await self.session.execute(
            statement
            .values(
                payment_status="rejected",
                admin_comment=admin_comment,
                reviewed_at=datetime.now(timezone.utc),
            )
            .returning(Payment.id)
            .execution_options(synchronize_session="fetch")
        )
        await self.session.flush()
        return result.scalar_one_or_none() is not None

    async def count_pending(self) -> int:
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).where(Payment.payment_status == "pending")
        )
        return result.scalar() or 0

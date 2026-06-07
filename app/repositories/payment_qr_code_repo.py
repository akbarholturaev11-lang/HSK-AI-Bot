from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.payment_qr_code import PaymentQrCode


class PaymentQrCodeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(
        self,
        *,
        scope: str,
        payment_method: str,
        plan_type: str,
        amount: int,
        currency: str,
    ) -> Optional[PaymentQrCode]:
        result = await self.session.execute(
            select(PaymentQrCode).where(
                PaymentQrCode.scope == scope,
                PaymentQrCode.payment_method == payment_method,
                PaymentQrCode.plan_type == plan_type,
                PaymentQrCode.amount == amount,
                PaymentQrCode.currency == currency,
            )
        )
        return result.scalar_one_or_none()

    async def set_qr_code(
        self,
        *,
        scope: str,
        payment_method: str,
        plan_type: str,
        amount: int,
        currency: str,
        file_id: str,
        created_by_telegram_id: int | None = None,
    ) -> PaymentQrCode:
        qr_code = await self.get(
            scope=scope,
            payment_method=payment_method,
            plan_type=plan_type,
            amount=amount,
            currency=currency,
        )
        if qr_code:
            qr_code.file_id = file_id
            qr_code.created_by_telegram_id = created_by_telegram_id
        else:
            qr_code = PaymentQrCode(
                scope=scope,
                payment_method=payment_method,
                plan_type=plan_type,
                amount=amount,
                currency=currency,
                file_id=file_id,
                created_by_telegram_id=created_by_telegram_id,
            )
            self.session.add(qr_code)
        await self.session.flush()
        return qr_code

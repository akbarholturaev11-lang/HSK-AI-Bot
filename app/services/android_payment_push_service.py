"""Payment-decision wrapper around the shared Android FCM transport.

The database remains the source of truth. FCM carries only a device-bound
status hint; Android verifies the payment under the current authenticated
session before showing a notification.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.config import settings
from app.db.models.android_push import AndroidPushToken
from app.db.models.desktop import DesktopDevice
from app.services.android_push_service import AndroidPushService


logger = logging.getLogger(__name__)


class AndroidPaymentPushService(AndroidPushService):
    async def _send_one(
        self,
        *,
        token: str,
        device_id: str,
        payment_id: int,
        status: str,
    ) -> bool:
        result = await self.send_token(
            token=token,
            device_id=device_id,
            data={
                "kind": "payment_decision",
                "device_id": device_id,
                "payment_id": payment_id,
                "status": status,
            },
            ttl_seconds=86400,
        )
        return result.accepted

    async def notify(self, *, telegram_id: int, payment_id: int, status: str) -> None:
        if status not in {"approved", "rejected"} or not self.configured:
            return
        rows = (
            await self.session.execute(
                select(AndroidPushToken.token, AndroidPushToken.device_id)
                .join(DesktopDevice, AndroidPushToken.device_id == DesktopDevice.id)
                .where(
                    DesktopDevice.telegram_id == telegram_id,
                    DesktopDevice.platform == "android",
                    DesktopDevice.revoked_at.is_(None),
                )
            )
        ).all()
        for token, device_id in rows:
            try:
                sent = await self._send_one(
                    token=token,
                    device_id=device_id,
                    payment_id=payment_id,
                    status=status,
                )
                if not sent:
                    logger.warning(
                        "Android payment push refused for payment %s",
                        payment_id,
                    )
            except Exception:
                # Payment has already committed. A transport failure must not
                # undo it or suppress the independent Telegram notification.
                logger.exception(
                    "Android payment push failed for payment %s",
                    payment_id,
                )

"""Best-effort device delivery after a committed payment decision.

The database remains the source of truth. FCM carries only a device-bound
status hint; the Android app refreshes access from the API after a tap.
"""

from __future__ import annotations

import asyncio
import json
import logging

import google.auth
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account
import httpx
from sqlalchemy import select

from app.config import settings
from app.db.models.android_push import AndroidPushToken
from app.db.models.desktop import DesktopDevice


logger = logging.getLogger(__name__)
FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


class AndroidPaymentPushService:
    def __init__(self, session, settings_obj=settings):
        self.session = session
        self.settings = settings_obj

    @property
    def configured(self) -> bool:
        return bool(str(getattr(self.settings, "ANDROID_FCM_PROJECT_ID", "") or "").strip())

    async def register(self, *, device: DesktopDevice, token: str) -> None:
        if device.platform != "android" or device.revoked_at is not None:
            raise ValueError("android_device_required")
        # The FCM token identifies one installation. Rotation replaces its old
        # value; account switching cannot leave it attached to another device.
        existing = (
            await self.session.execute(
                select(AndroidPushToken).where(AndroidPushToken.token == token)
            )
        ).scalar_one_or_none()
        if existing and existing.device_id != device.id:
            await self.session.delete(existing)
            await self.session.flush()
        by_device = await self.session.get(AndroidPushToken, device.id)
        if by_device:
            by_device.token = token
        else:
            self.session.add(AndroidPushToken(device_id=device.id, token=token))
        await self.session.commit()

    async def unregister(self, *, device: DesktopDevice) -> None:
        row = await self.session.get(AndroidPushToken, device.id)
        if row:
            await self.session.delete(row)
            await self.session.commit()

    def _credentials(self):
        raw = str(getattr(self.settings, "ANDROID_FCM_SERVICE_ACCOUNT_JSON", "") or "").strip()
        if raw:
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(raw), scopes=[FCM_SCOPE]
            )
        else:
            credentials, _ = google.auth.default(scopes=[FCM_SCOPE])
        return credentials

    async def _send_one(self, *, token: str, device_id: str, payment_id: int, status: str) -> bool:
        credentials = await asyncio.to_thread(self._credentials)
        await asyncio.to_thread(credentials.refresh, GoogleAuthRequest())
        project_id = str(self.settings.ANDROID_FCM_PROJECT_ID).strip()
        payload = {
            "message": {
                "token": token,
                "data": {
                    "kind": "payment_decision",
                    "device_id": device_id,
                    "payment_id": str(payment_id),
                    "status": status,
                },
                "android": {"priority": "HIGH", "ttl": "86400s"},
            }
        }
        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.post(
                f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send",
                headers={"Authorization": f"Bearer {credentials.token}"},
                json=payload,
            )
        return response.is_success

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
                    token=token, device_id=device_id, payment_id=payment_id, status=status
                )
                if not sent:
                    logger.warning("Android payment push refused for payment %s", payment_id)
            except Exception:
                # Payment has already committed. A transport failure must not
                # undo it or suppress the independent Telegram notification.
                logger.exception("Android payment push failed for payment %s", payment_id)

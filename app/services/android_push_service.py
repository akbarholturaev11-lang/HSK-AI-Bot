"""Shared Firebase Cloud Messaging transport for authenticated Android devices.

FCM is a transport, never the source of truth. Payloads are small data-only
hints; Android re-checks account/release/course state before showing anything
that can affect the user.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from typing import Mapping

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


@dataclass(frozen=True)
class AndroidPushResult:
    accepted: bool
    stale_token: bool = False


class AndroidPushService:
    """Owns Android FCM token lifecycle and generic data-only delivery."""

    def __init__(self, session, settings_obj=settings):
        self.session = session
        self.settings = settings_obj

    @property
    def configured(self) -> bool:
        return bool(str(getattr(self.settings, "ANDROID_FCM_PROJECT_ID", "") or "").strip())

    async def register(self, *, device: DesktopDevice, token: str) -> None:
        if device.platform != "android" or device.revoked_at is not None:
            raise ValueError("android_device_required")
        existing = (
            await self.session.execute(
                select(AndroidPushToken).where(AndroidPushToken.token == token)
            )
        ).scalar_one_or_none()
        if existing and existing.device_id != device.id:
            await self.session.delete(existing)
            await self.session.flush()

        now = datetime.now(timezone.utc)
        by_device = await self.session.get(AndroidPushToken, device.id)
        if by_device:
            by_device.token = token
            by_device.updated_at = now
        else:
            self.session.add(
                AndroidPushToken(
                    device_id=device.id,
                    token=token,
                    registered_at=now,
                    updated_at=now,
                )
            )
        await self.session.commit()

    async def unregister(self, *, device: DesktopDevice) -> None:
        row = await self.session.get(AndroidPushToken, device.id)
        if row:
            await self.session.delete(row)
            await self.session.commit()

    async def update_preferences(
        self,
        *,
        device: DesktopDevice,
        study_reminders_enabled: bool,
        timezone_name: str,
    ) -> None:
        """Update device push preferences when this install has a registered token.

        No token means there is nowhere to push yet, so this is intentionally a
        no-op. Android re-sends preferences immediately after token registration.
        """
        row = await self.session.get(AndroidPushToken, device.id)
        if row is None:
            return
        row.study_reminders_enabled = bool(study_reminders_enabled)
        row.timezone_name = timezone_name
        row.updated_at = datetime.now(timezone.utc)
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

    @staticmethod
    def _payload_data(data: Mapping[str, object]) -> dict[str, str]:
        result: dict[str, str] = {}
        for key, value in data.items():
            name = str(key).strip()
            if not name or value is None:
                continue
            result[name] = str(value)
        if "kind" not in result:
            raise ValueError("android_push_kind_required")
        return result

    @staticmethod
    def _is_stale_token(response: httpx.Response) -> bool:
        if response.status_code == 404:
            return True
        try:
            body = response.json()
        except Exception:
            return False
        error = body.get("error") if isinstance(body, dict) else None
        details = error.get("details", []) if isinstance(error, dict) else []
        for detail in details if isinstance(details, list) else []:
            if isinstance(detail, dict) and detail.get("errorCode") == "UNREGISTERED":
                return True
        return False

    async def _drop_token(self, *, device_id: str, token: str) -> None:
        row = await self.session.get(AndroidPushToken, device_id)
        if row is not None and row.token == token:
            await self.session.delete(row)
            await self.session.commit()

    async def send_token(
        self,
        *,
        token: str,
        device_id: str,
        data: Mapping[str, object],
        ttl_seconds: int = 86400,
    ) -> AndroidPushResult:
        if not self.configured:
            return AndroidPushResult(False)
        credentials = await asyncio.to_thread(self._credentials)
        await asyncio.to_thread(credentials.refresh, GoogleAuthRequest())
        project_id = str(self.settings.ANDROID_FCM_PROJECT_ID).strip()
        payload = {
            "message": {
                "token": token,
                "data": self._payload_data(data),
                "android": {
                    "priority": "HIGH",
                    "ttl": f"{max(0, int(ttl_seconds))}s",
                },
            }
        }
        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.post(
                f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send",
                headers={"Authorization": f"Bearer {credentials.token}"},
                json=payload,
            )
        if response.is_success:
            return AndroidPushResult(True)
        stale = self._is_stale_token(response)
        if stale:
            await self._drop_token(device_id=device_id, token=token)
        logger.warning(
            "Android FCM refused kind=%s device=%s status=%s stale=%s",
            payload["message"]["data"].get("kind"),
            device_id,
            response.status_code,
            stale,
        )
        return AndroidPushResult(False, stale_token=stale)

    async def send_to_user(
        self,
        *,
        telegram_id: int,
        data: Mapping[str, object],
        ttl_seconds: int = 86400,
    ) -> int:
        """Best-effort fan-out to every current Android device for one account."""
        if not self.configured:
            return 0
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
        accepted = 0
        for token, device_id in rows:
            try:
                result = await self.send_token(
                    token=token,
                    device_id=device_id,
                    data=data,
                    ttl_seconds=ttl_seconds,
                )
                accepted += int(result.accepted)
            except Exception:
                logger.exception(
                    "Android push failed kind=%s device=%s",
                    data.get("kind"),
                    device_id,
                )
        return accepted
